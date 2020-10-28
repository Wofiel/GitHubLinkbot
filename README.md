# GitHub Linkbot

## Purpose

For linking GitHub Issues, PRs and Commits into Discord.

## How to use

The formatting that the bot responds to tries to follow those of the [GitHub Docs](https://docs.github.com/en/free-pro-team@latest/github/writing-on-github/autolinked-references-and-urls#issues-and-pull-requests) this includes:

| Link type                         | Format                                   |
| --------------------------------- |------------------------------------------|
| Issues/Pull Requests              | #26                                      |
| Specific repo issue/pull requests | jlord/sheetsee.js#26                     |
| Commit SHA (40 char)              | a5c3785ed8d6a35868bc169f07e40e889087fd2e |
| Username@short SHA                | jlord@a5c3785                            |
| Username/repo@short SHA           | jlord/sheetsee.js@a5c3785                |

## How to setup

### Environment variables

#### Github
1. Create a [GitHub Personal Access Token](https://github.com/settings/tokens) for use with the GitHub API.
1. Create an environment variable named `GHAT` and set it to the created token.

#### Discord
1. Create a [Discord Application](https://discord.com/developers/applications)
1. Create a Bot to obtain a bot token
1. Create an environment variable named `DISCORD_TOKEN` and set it to the created token

### Setup `config.ini`

#### Needed configurations

```
[default_repository]
username = {YOUR_GITHUB_USERNAME}
repository = {YOUR_GITHUB_REPO}

[configuration]
string_length = {max length for descriptions, eg. 200}
max_embeds = {maximum number of embeds to attach, eg. 5}
```

#### Optional configurations

##### Per-channel repo overrides

These overrides will replace the default repository for a channel, so unspecified issue/PR numbers and commits will link to those issues, rather than the `default_repository` set in the config.
This can be formatted in repo only or username/repo format.

```
[channel_overrides]
channel_name={SECOND_GITHUB_REPO}
channel_name_two={SECOND_GITHUB_USERNAME}/{SECOND_GITHUB_REPO}
```

## Run
`python ghlb.py`