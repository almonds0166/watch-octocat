# watch-octocat

GitHub can work together with Discord to help keep you up-to-date on your repos commits [using Webhooks](https://gist.github.com/eslachance/40ac1c8232a5a019b43ee3f588d637ad). However, this method only works on repos you own. Sometimes I want to keep up-to-date on a repository I don't own. If there's a simpler way than how I've done it here, feel free to chastise.

## How it looks

<p align="center">
   <img alt="(image of what a usual commit looks like)" src="https://i.imgur.com/clG67cm.png">
</p>

Note, this format is a different design than the usual GitHub Webhooks you can set up for the repositories you own. The design was not meant to be a perfect replicate but rather a decent one in its own right.

## Setup

Go into `config.py` and write what repos you want to watch and where you want to send them:

```python
WATCH = {
   ("owner", "repo"): "discord webhook url", # first repo
   ("owner", "repo"): "discord webhook url", # second
   ... # etc.
}
```

Then run `watch-octocat.py` with Python 3.6 or above.

Add your username and [a personal access token](https://help.github.com/en/github/authenticating-to-github/creating-a-personal-access-token-for-the-command-line) to reduce your [rate limit](https://developer.github.com/v3/#rate-limiting) for GitHub's API.

## Notes

There are likely still bugs I need to sort out. (Sorrynotsorry)