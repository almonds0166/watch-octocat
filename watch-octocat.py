#!/usr/bin/env python3.7

# (use Python 3.6 or above)

import config

import asyncio
import requests
from datetime import datetime, timedelta
import time

# Endpoints

# get list of commits:
GET_COMMITS = "https://api.github.com/repos/{owner}/{repo}/commits"

# get specific commit, including the list of file changes:
GET_COMMIT  = "https://api.github.com/repos/{owner}/{repo}/commits/{sha}"

# requests settings

USER_AGENT = "WatchOctocatBot/0.0" # instead of requests's User-Agent
TIME_ZONE  = "Etc/UTC"

HEADERS    = {
   "User-Agent": USER_AGENT,
   "Time-Zone": TIME_ZONE
}

AUTH = None
if config.USERNAME and config.PERSONAL_ACCESS_TOKEN:
   AUTH = (config.USERNAME, config.PERSONAL_ACCESS_TOKEN)

REQUESTS_SETTINGS = {
   "headers": HEADERS,
   "auth": AUTH
}

# Initialize hash table that will remember the time since we last checked each repository
# Note, O(1) space complexity per each repository watched
TABLE = {}

def now(offset=0):
   """
   Returns the current UTC time, minus the specified offset in minutes, in ISO
   8601 format.
   """
   t = datetime.utcnow().replace(microsecond=0) - timedelta(minutes=offset)
   return t.isoformat() + "Z"

def oops(response, api_name, status_url):
   """
   Routine to handle when the GitHub or Discord API is down.
   """
   status_name = requests.status_codes._codes[response.status_code][0]
   try:
      json = response.json()
   except ValueError:
      json = "n/a"
   msg = (
      f"___\n"
      f"Oops! Something went wrong with the {api_name} API.\n"
      f"Response code: {response.status_code} ({status_name})\n"
      f"JSON received: {json}\n"
      f"Check GitHub status here: {status_url}\n"
      f"Blocking for {config.API_DOWN_WAIT} seconds before trying again...\n"
   )
   print(msg)
   time.sleep(config.API_DOWN_WAIT)

def get_request(endpoint, params=None):
   """
   GETs data from the GitHub API, handles errors.
   """
   r = requests.get(endpoint, params=params, **REQUESTS_SETTINGS) # can be simplified in Python 3.8 using the walrus operator
   while r.status_code != 200:
      oops(r, "GitHub", "https://www.githubstatus.com/")
      r = requests.get(endpoint, params=params, **REQUESTS_SETTINGS)
   return r

def post_webhook(params, url):
   """
   POSTs JSON data to a Discord Webhook URL, handles errors.

   See here for info on Discord Webhooks:
   https://birdie0.github.io/discord-webhooks-guide/discord_webhook.html
   """
   r = requests.post(url, json=params, **REQUESTS_SETTINGS)
   while r.status_code != 204:
      oops(r, "Discord", "https://status.discordapp.com/")
      r = requests.post(url, json=params, **REQUESTS_SETTINGS)
   return r

def check_repo(owner, repo, verbose=config.VERBOSE):
   """
   Checks if there are any new commits to be processed at owner/repo. Returns a
   list of JSON dictionaries to be POSTed over as a Discord Webhook.

   See here for info on this GitHub API:
   https://developer.github.com/v3/repos/commits/
   """
   repository = {
      "owner": owner,
      "repo": repo
   }

   key = f"{owner}/{repo}"

   if verbose:
      print("checking:", key)

   if not key in TABLE:
      TABLE[key] = now(config.STARTUP_OFFSET)

   endpoint = GET_COMMITS.format(**repository)
   r = get_request(endpoint, params={"since": TABLE[key]})
   TABLE[key] = now() # update hash table

   webhooks = []
   for commit in r.json():
      endpoint = GET_COMMIT.format(**repository, sha=commit["sha"])
      commit = get_request(endpoint).json()
      webhooks.append(repo_to_params(key, commit))

   return webhooks

def repo_to_params(repository, commit, verbose=config.VERBOSE):
   """
   Converts a JSON dictionary representing a GitHub commit into a JSON
   dictionary able to be POSTed to a Discord Webhook URL.
   """
   sha        = commit["sha"]
   html_url   = commit["html_url"]

   # Code author
   author     = commit["commit"]["author"]["name"]
   login      = commit["author"]["login"]
   author_url = commit["author"]["html_url"]

   if author == login:
      author = f"[{login}]({author_url})"
   else:
      author = f"{author} ([{login}]({author_url}))"

   # List of affected files
   changelist = []
   for file in commit["files"][:config.TRUNCATE_AT]:
      changelist.append(
         "> **{status}**: `{filename}`".format(**file)
      )
      changes   = file["changes"]
      if changes > 2:
         additions = file["additions"]
         deletions = file["deletions"]
         additions = f"{additions} addition" + ("s" if additions != 1 else "")
         deletions = f"{deletions} deletion" + ("s" if deletions != 1 else "")
         if file["additions"] and file["deletions"]:
            deltas = f"{additions}, {deletions}"
         elif file["additions"]: # zero deletions
            deltas = f"{additions}"
         else: # zero additions
            deltas = f"{deletions}"
         changelist[-1] += f" ({deltas})"

   if len(commit["files"]) > config.TRUNCATE_AT:
      changelist.append("> ...")

   changelist = "\n".join(changelist)

   # Hash, code author, and commit message
   message = commit["commit"]["message"]
   message = (
      f"[`{sha[:7]}`]({html_url}) by {author}\n"
      "```\n"
      f"{message}"
      "```\n"
   )

   # Webhook
   params = {
      "content": changelist,
      "username": repository,
      "avatar_url": commit["author"]["avatar_url"],
      "embeds": [{
         "description": message,
         "color": 7506394 # blurple
      }]
   }

   if verbose:
      print(params) # consider using pprint

   return params

async def subscribe(owner, repo, webhook_url):
   """
   An async routine that watches the specified repository and posts to the
   given Webhook URL.
   """
   while True:
      for webhook in check_repo(owner, repo):

         post_webhook(webhook, webhook_url)
         time.sleep(config.POST_COOLDOWN) # block
         await asyncio.sleep(0)

      time.sleep(config.CYCLE_COOLDOWN) # block
      await asyncio.sleep(0)

# main

if __name__ == "__main__":
   tasks = []
   for key, value in config.WATCH.items():
      owner, repo = key
      webhook_url = value
      tasks.append(
         subscribe(owner, repo, webhook_url)
      )
   tasks = asyncio.gather(*tasks)
   loop = asyncio.get_event_loop()
   try:
      loop.run_until_complete(tasks)
   except KeyboardInterrupt:
      # Thanks to ntninja on StackOverflow for the graceful shutdown code below
      # https://stackoverflow.com/a/42097478 (2017)
      print("^C")
      def shutdown_exception_handler(loop, context):
         if "exception" not in context \
         or not isinstance(context["exception"], asyncio.CancelledError):
            loop.default_exception_handler(context)
      loop.set_exception_handler(shutdown_exception_handler)
      tasks = asyncio.gather(*asyncio.Task.all_tasks(loop=loop), loop=loop, return_exceptions=True)
      tasks.add_done_callback(lambda t: loop.stop())
      tasks.cancel()
      while not tasks.done() and not loop.is_closed():
         loop.run_forever()
   finally:
      loop.close()
