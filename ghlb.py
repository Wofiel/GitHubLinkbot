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
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')
GITHUB_TOKEN = os.getenv('GHAT')
g = Github(GITHUB_TOKEN)

class UrlType(Enum):
    PULL = 1
    ISSUE = 2
    COMMIT = 3

class GithubLinkBot(discord.Client):
    async def on_ready(self):
        self.config = Config("config.ini")
        self.queued_responses = queue.Queue(self.config.MAX_EMBEDS)
        
        self.check_channel_permissions()
        self.webhooks_allowed = False
        await self.check_webhooks()

        self.responded_messages = {}
        print(f'{client.user} has connected to Discord!')

    def check_channel_permissions(self):
        # single guild currently
        guilds = client.guilds
        current_guild = guilds[0]
        for channel in set(self.config.CFG_ALLOWED_CHANNELS).intersection(self.config.CFG_BLOCKED_CHANNELS):
            print(f'WARNING: Channel {channel} appears in both ALLOW and BLOCK lists. BLOCK lists have priority.')
       
        if self.config.ALLOW_ALL_CHANNELS:
            self.config.ALLOWED_CHANNELS = [channel for channel in current_guild.text_channels if channel.name not in self.config.CFG_BLOCKED_CHANNELS]
        else:
            self.config.ALLOWED_CHANNELS = [channel for channel in current_guild.text_channels if channel.name in self.config.CFG_ALLOWED_CHANNELS]

    # REQUIRES manage_webhooks PERMISSION!
    async def check_webhooks(self):
        self.webhooks = {}
        for channel in self.config.ALLOWED_CHANNELS:
            try:
                hooks = await channel.webhooks()
                if len(hooks) > 0:
                    for hook in hooks:
                        if hook.user == client.user:
                            self.webhooks[channel] = hook
                else:
                    self.webhooks[channel] = await channel.create_webhook(name='GitHubLinkBot', reason="GitHubLinkBot")
                    print(f'Created new WebHook for channel: {channel}')
                self.webhooks_allowed = True
            except discord.Forbidden:
                print(f'ERROR: Bot does not have manage_webhooks permission in {channel}!')

    async def on_message(self, message):
        if message.author == client.user:
            return

        if message.author.bot:
            return

        if message.channel not in self.config.ALLOWED_CHANNELS:
            return

        responses = self.generate_responses_for_triggers(message)

        embeds = []
        if len(responses) > 0:
            embeds = self.create_embeds(responses, self.config.MAX_EMBEDS)
            await self.send_message_with_embeds(embeds, message)

    async def on_message_edit(self, before, after):
        if before.content == after.content:
            return

        if before in self.responded_messages.keys():
            previous_response = self.responded_messages[before]

            responses = self.generate_responses_for_triggers(after)
            if len(responses) == 0:
                await previous_response.delete()
                del self.responded_messages[before]
                return
            
            embeds = []
            if len(responses) > 0:
                embeds = self.create_embeds(responses, self.config.MAX_EMBEDS)
            
            # for now just fully wipe them
            if type(previous_response) == discord.webhook.WebhookMessage:
                # can edit multiple embeds
                # don't bother to going to regular Message
                await previous_response.edit(embeds=embeds)

            if type(previous_response) == discord.message.Message:
                # 1 -> n = delete and make WebhookMessage
                if len(responses) > 1 and self.webhooks_allowed == True:
                    # delete previous Message to post new WebhookMessage
                    await previous_response.delete()
                    await self.send_message_with_embeds(embeds, after)
                elif len(responses) == 1:
                    await previous_response.edit(embed=embeds[0])

        else:
            responses = self.generate_responses_for_triggers(after)
            embeds = []
            if len(responses) > 0:
                embeds = self.create_embeds(responses, self.config.MAX_EMBEDS)

            await self.send_message_with_embeds(embeds, after)

    async def on_message_delete(self, message):
        if message in self.responded_messages.keys():
            response = self.responded_messages[message]
            await response.delete()
            del self.responded_messages[message]

    def generate_responses_for_triggers(self, message):
        # TODO: Should we ignore strings that are in code blocks?
        scanner = re.Scanner([
            (r"(?:([^/\s]+/[^/\s]+)#(\d+))", lambda scanner, token: self.username_repo_and_issue_or_pull_number(token)),
            (r"(?:([^/\s]+)#(\d+))", lambda scanner, token: self.repo_and_issue_or_pull_number(token)),
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
        return non_empty_responses

    async def send_message_with_embeds(self, embeds, message_responded_to):
        # If we have a single embed, we use message and use reply functionality, if we have multiple we use webhooks
        # This will complicate some parts like editing, but I like the idea of more completeness.
        reply = None
        if len(embeds) == 1 or self.webhooks_allowed == False:
            reply = await message_responded_to.channel.send(embed=embeds[0], reference=message_responded_to, mention_author=False)
        else:
            # Instead of sending a message like would be sensible, make a WebHook for NO reason (API limitations of Discord)
            reply = await self.webhooks[message_responded_to.channel].send(embeds=embeds, wait=True)

        self.responded_messages[message_responded_to] = reply

        self.prune_cached_responses_if_necessary()

    def prune_cached_responses_if_necessary(self):
        # Python dictionaries are now inserted in order, so now if we are over the limit, we can simply remove the first
        while len(self.responded_messages.keys()) > self.config.MAX_CACHED_MESSAGES:
            message_keys_as_list = list(self.responded_messages.keys())
            del self.responded_messages[message_keys_as_list[0]]

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

    def repo_and_issue_or_pull_number(self, token):
        repo,post_id = re.split('/|#',token)
        title,link_type,obj_response = self.get_valid_issue_or_pull(self.config.USERNAME, repo, post_id)

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
client.run(DISCORD_TOKEN)
