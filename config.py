
# List of repositories to watch
# ("owner", "repo"): "Discord Webhook url"

WATCH = {
   ("owner", "repo"): "discord webhook url"
}

# add your own token for reduced rate-limiting
# see here for more info: https://developer.github.com/v3/#rate-limiting
# consider using environment variables (os.environ)
USERNAME              = ""
PERSONAL_ACCESS_TOKEN = ""

# Tweaks

CYCLE_COOLDOWN = 60 # sleep for n seconds after every check cycle
POST_COOLDOWN  = 2 # sleep for n seconds between POST requests (to prevent spamming)

API_DOWN_WAIT  = 300 # if the GitHub or Discord APIs seem down, wait n seconds before trying again

STARTUP_OFFSET = 15 # number of minutes before script startup to consider a commit "new"
TRUNCATE_AT    = 10 # number of files to display in the changelist before truncation

VERBOSE        = False # print Webhooks to standard output before POSTing, and other debug info