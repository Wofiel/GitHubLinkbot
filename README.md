# GitHub Linkbot

## Purpose

For linking GitHub Issues, PRs and Commits into Discord.

## How to use

The formatting that the bot responds to tries to follow those of the [GitHub Docs](https://docs.github.com/en/free-pro-team@latest/github/writing-on-github/autolinked-references-and-urls#issues-and-pull-requests) this includes:

| Link type                              | Format                                   |
| -------------------------------------- |------------------------------------------|
| Issues/Pull Requests                   | #26                                      |
| Specific repo issue/pull requests      | sheetsee.js#26                           |
| Specific user/repo issue/pull requests | jlord/sheetsee.js#26                     |
| Commit SHA (40 char)                   | a5c3785ed8d6a35868bc169f07e40e889087fd2e |
| Username@short SHA                     | jlord@a5c3785                            |
| Username/repo@short SHA                | jlord/sheetsee.js@a5c3785                |

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

#### Required configurations

```
[default_repository]
username={YOUR_GITHUB_USERNAME}
repository={YOUR_GITHUB_REPO}
```

#### Optional configurations

##### General configuration

Configuration for embeds.

- `string_length` Maximum length for descriptions, eg. 200
- `max_embeds` Maximum number of embeds to attach, eg. 5
- `allow_all_channels` Whether posting is allowed in all channels, eg. yes or no
- `allowed_channel_list` Comma-separated list of channels that explicitly allow being posted on eg. general,development
- `blocked_channel_list` Comma-separated list of channels that explicitly do not allow being posted on. Blocks have higher priority than allows if listed in both. eg. github,netlify
- `max_cached_messages` Max responses to cache to watch for edits/deletes, eg. 100

Defaults:

```
[configuration]
string_length=200
max_embeds=5
allow_all_channels=no
max_cached_messages=100
```

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
