import os
import re
import datetime
from enum import Enum

import discord
from dotenv import load_dotenv
from github import Github

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

USERNAME = "zmkfirmware"
REPOSITORY = "zmk"

client = discord.Client()
g = Github(os.getenv('GHAT'))

STRING_LENGTH = 200

class UrlType(Enum):
    PULL = 1
    ISSUE = 2
    COMMIT = 3

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.author.bot:
        return

    scanner = re.Scanner([
        (r"(?:([^/\s]+/[^/\s]+)#(\d+))", lambda scanner, token: username_repo_and_issue_or_pull_number(token)),
        (r"(#(\d+))", lambda scanner, token: issue_or_pull_number(token)),
        (r"[A-Za-z0-9]+/[A-Za-z0-9\.\-]+@(\s*([A-Fa-f0-9]{7,40}))", lambda scanner, token: username_repo_at_sha(token)),
        (r"[A-Za-z0-9]+@(\s*([A-Fa-f0-9]{7,40}))", lambda scanner, token: username_at_sha(token)),
        (r"(\s*([A-Fa-f0-9]{40}))", lambda scanner, token: commit_sha(token)),
        (r".", lambda scanner, token: None),
    ])

    collated_responses = scanner.scan(message.content)
    non_empty_responses = list(filter(None, collated_responses[0]))

    embeds = []
    if len(non_empty_responses) > 0:    
        embeds = create_embeds(non_empty_responses)

    for embed in embeds:
        await message.channel.send(embed=embed)

def create_embeds(messages):
    embed = []
    for message in messages:
        response = message["response"]
        if message["link_type"] is UrlType.PULL or message["link_type"] is UrlType.ISSUE:
            sub_embed=discord.Embed(
                            title=f'#{response.number}: {response.title}',
                            url=response.html_url,
                            description=f'{response.body[:STRING_LENGTH]}' + ("..." if len(response.body) > STRING_LENGTH else ""),
                            color=int(f'0x{response.labels[0].color}',16) if response.labels else discord.Color.default(),
                            timestamp=response.created_at,
                            )
            sub_embed.set_author(
                            name=response.user.login,
                            url=response.user.html_url,
                            icon_url=response.user.avatar_url,
                            )

        elif message["link_type"] is UrlType.COMMIT:
            # GitHub formats these just with \n\n between the two in the single commit message
            if "\n\n" in response.commit.message:
                title,description = response.commit.message.split("\n\n", 1)
                # cap description length if necessary
                description = description[:STRING_LENGTH] + ("..." if len(response.body) > STRING_LENGTH else "")
            else:
                title=response.commit.message
                description=None

            sub_embed=discord.Embed(
                                title=title,
                                description=description,
                                url=response.html_url,
                                timestamp=response.commit.author.date,
                                )
            
            # try rawData["author"] first as it will have a GitHub login, not just a committer name
            if response._rawData["author"] is not None:
                sub_embed.set_author(
                            name=response._rawData["author"]["login"],
                            url=response._rawData["author"]["html_url"],
                            icon_url=response._rawData["author"]["avatar_url"],
                            )
            else:
                sub_embed.set_author(
                            name=response._rawData["commit"]["author"]["name"],
                            )

        embed.append(sub_embed)

    return embed

def get_valid_issue_or_pull(username, repo, post_id):
    repo_object = g.get_repo(f'{USERNAME}/{REPOSITORY}')
    response = None

    try:
        response = repo_object.get_issue(number=int(post_id))
        gh_link_type = UrlType.ISSUE
    except Exception:
        pass

    try:
        response = repo_object.get_pull(number=int(post_id))
        gh_link_type = UrlType.PULL
    except Exception:
        pass

    if response is not None:
        return response.title,gh_link_type,response
    else:
        return None,None,None

def issue_or_pull_number(token):
    post_id = int(token.replace('#',''))
    title,link_type,obj_response = get_valid_issue_or_pull(USERNAME, REPOSITORY, post_id)
    
    if title is not None:
        response = { "link_type":link_type, "response":obj_response }
        return response

def username_repo_and_issue_or_pull_number(token):
    username,repo,post_id = re.split('/|#',token)
    title,link_type,obj_response = get_valid_issue_or_pull(username, repo, post_id)

    if title is not None:
        response = { "link_type":link_type, "response":obj_response }
        return response

def get_commit(username, repo, sha):
    try:
        commit = g.get_repo(f'{username}/{repo}').get_commit(sha=sha)
        if commit is not None:
            response = { "link_type":UrlType.COMMIT, "response":commit }
            return response
    except Exception as e:
        print(e)
        return

def commit_sha(token):
    return get_commit(USERNAME, REPOSITORY, token)

def username_at_sha(token):
    username,sha = token.split("@")
    return get_commit(username, REPOSITORY, sha)

def username_repo_at_sha(token):
    username,repo,sha = re.split('/|@',token)
    return get_commit(username, repo, sha)

client.run(TOKEN)
