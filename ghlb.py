import os
import re
import datetime
import queue
from enum import Enum

from config import Config

import discord
from dotenv import load_dotenv
from github import Github

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
g = Github(os.getenv('GHAT'))

class UrlType(Enum):
    PULL = 1
    ISSUE = 2
    COMMIT = 3

class GithubLinkBot(discord.Client):
    async def on_ready(self):
        self.config = Config("config.ini")
        self.queued_responses = queue.Queue(self.config.MAX_EMBEDS)
        print(f'{client.user} has connected to Discord!')

    async def on_message(self, message):
        if message.author == client.user:
            return

        if message.author.bot:
            return

        # TODO: Should we ignore strings that are in code blocks?
        scanner = re.Scanner([
            (r"(?:([^/\s]+/[^/\s]+)#(\d+))", lambda scanner, token: self.username_repo_and_issue_or_pull_number(token)),
            (r"(#(\d+))", lambda scanner, token: self.issue_or_pull_number(token, message.channel)),
            (r"[A-Za-z0-9]+/[A-Za-z0-9\.\-]+@(\s*([A-Fa-f0-9]{7,40}))", lambda scanner, token: self.username_repo_at_sha(token)),
            (r"[A-Za-z0-9]+@(\s*([A-Fa-f0-9]{7,40}))", lambda scanner, token: self.username_at_sha(token, message.channel)),
            (r"(\s*([A-Fa-f0-9]{40}))", lambda scanner, token: self.commit_sha(token, message.channel)),
            (r".", lambda scanner, token: None),
        ])
        
        try:
            scanner.scan(message.content)
        except queue.Full:
            pass

        collated_responses = []
        while not self.queued_responses.empty():
            collated_responses.append(self.queued_responses.get())

        non_empty_responses = list(filter(None, collated_responses))

        embeds = []
        if len(non_empty_responses) > 0:
            embeds = self.create_embeds(non_empty_responses, self.config.MAX_EMBEDS)

        for embed in embeds:
            await message.channel.send(embed=embed)

    def create_embeds(self, messages, max_embeds):
        embed = []
        for message in messages:
            # this allows it to be set to -1 to allow unlimited
            if len(embed) == max_embeds:
                break
            response = message["response"]
            if message["link_type"] is UrlType.PULL or message["link_type"] is UrlType.ISSUE:
                sub_embed=discord.Embed(
                                title=f'#{response.number}: {response.title}',
                                url=response.html_url,
                                description=f'{response.body[:self.config.STRING_LENGTH]}' + ("..." if len(response.body) > self.config.STRING_LENGTH else ""),
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
                    description = description[:self.config.STRING_LENGTH] + ("..." if len(response.body) > self.config.STRING_LENGTH else "")
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

    def get_valid_issue_or_pull(self, username, repo, post_id):
        repo_object = g.get_repo(f'{username}/{repo}')
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

    def issue_or_pull_number(self, token, channel):
        post_id = int(token.replace('#',''))
        username,repo = self.get_channel_overrides(channel)

        title,link_type,obj_response = self.get_valid_issue_or_pull(username, repo, post_id)
        
        if title is not None:
            response = { "link_type":link_type, "response":obj_response }
            return self.queued_responses.put(response, block=False)

    def username_repo_and_issue_or_pull_number(self, token):
        username,repo,post_id = re.split('/|#',token)
        title,link_type,obj_response = self.get_valid_issue_or_pull(username, repo, post_id)

        if title is not None:
            response = { "link_type":link_type, "response":obj_response }
            return self.queued_responses.put(response, block=False)

    def get_commit(self, username, repo, sha):
        try:
            commit = g.get_repo(f'{username}/{repo}').get_commit(sha=sha)
            if commit is not None:
                response = { "link_type":UrlType.COMMIT, "response":commit }
                return self.queued_responses.put(response, block=False)
        except Exception as e:
            print(e)
            return

    def commit_sha(self, token, channel):
        username,repo = self.get_channel_overrides(channel)
        return self.get_commit(username, repo, token)

    def username_at_sha(self, token, channel):
        username,sha = token.split("@")
        _,repo = self.get_channel_overrides(channel)
        return self.get_commit(username, repo, sha)

    def username_repo_at_sha(self, token):
        username,repo,sha = re.split('/|@',token)
        return self.get_commit(username, repo, sha)

    def get_channel_overrides(self, channel):
        # use defaults as fallback
        return self.config.CHANNEL_OVERRIDES.get(channel.name, (self.config.USERNAME, self.config.REPOSITORY))

client = GithubLinkBot()
client.run(TOKEN)