from __future__ import annotations
import disnake
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.util import JSON
from views.url_button import UrlButton

# ----------------------------------------------------------------------------------------------------------------
# Pinboard Component
# ----------------------------------------------------------------------------------------------------------------
# Enable the pinboard system ("extra pinned messages") in specific server
# ----------------------------------------------------------------------------------------------------------------

class Pinboard():
    COLOR : int = 0xf20252
    def __init__(self : Pinboard, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.bot.reaction_hooks['pinboard'] = self.pin # hook pin function
        self.cache : list[int] = [] # store pinned messages until reboot

    def init(self : Pinboard) -> None:
        pass

    """pin()
    Check the payload received from on_raw_reaction_add() and if it triggers a pin
    
    Parameters
    ----------
    payload: Raw Message Payload
    
    Returns
    --------
    bool: True if success, False if failure
    """
    async def pin(self : Pinboard, payload : disnake.RawReactionActionEvent) -> bool:
        try:
            idx : str|None = None # guild id
            origin_channel : disnake.Channel|None = self.bot.get_channel(payload.channel_id)
            origin_channel_name : str = origin_channel.name
            # do additional check to determine channel id and name
            channel_id : int
            if isinstance(origin_channel, disnake.Thread):
                try:
                    c : disnake.Channel = origin_channel.parent
                    if not isinstance(c, disnake.ForumChannel):
                        raise Exception()
                    channel_id = c.id
                    origin_channel_name = c.name
                except:
                    channel_id = payload.channel_id
            else:
                channel_id = payload.channel_id
            # check if the pinboard is enabled for that guild and channel
            s : str
            for s in self.bot.data.save['pinboard']:
                if channel_id in self.bot.data.save['pinboard'][s]['tracked']:
                    if self.is_enabled(s) and self.bot.data.save['pinboard'][s]['output'] is not None:
                        idx = s # note the guild id string
                        break
            # not found, return False
            if idx is None:
                return False
            # retrieve the message
            message : disnake.Message|None = await origin_channel.fetch_message(payload.message_id)
            # if the message has been cached, it has already been pinned recently, so we return False
            if message.id in self.cache:
                return False
            # retrieve the message reactions
            reactions : list[disnake.Reaction] = message.reactions
            # get Rosetta user profile in this guild
            me : disnake.Member = message.guild.me
            count : int = 0
            reaction : disnake.Reaction
            for reaction in reactions: # iterate over reactions and look for the one matching the emji setting 
                if str(reaction.emoji) == self.bot.data.save['pinboard'][idx]['emoji']:
                    users : list[disnake.User] = await reaction.users().flatten() # get who reacted with that emoji
                    count : int = len(users) # get the number of user which reacted
                    # plus other infos
                    guild : disnake.Guild = message.guild # the guild we're in
                    content : str = message.content # the message content
                    # variables
                    isMod : bool = False
                    count : int = 0
                    # if the bot already reacted, the message has already been pinned, so we return False
                    if me in users:
                        return False
                    # else, we check each user
                    u : disnake.User
                    for u in users:
                        if self.bot.data.save['pinboard'][idx]['mod_bypass']: # if the mod bypass is enabled
                            m : disnake.Member = await guild.get_or_fetch_member(u.id) # and that user is deemed to be a moderator
                            if m.guild_permissions.manage_messages: 
                                isMod = True # raise isMod flag and stop the loop here
                                break
                            else: # else, increase the count
                                count += 1
                        else: # else, increase the count
                            count += 1
                    # if the mod check didn't pass OR the threshold hasn't been reached, we return False
                    if not isMod and count < self.bot.data.save['pinboard'][idx]['threshold']:
                        return False

                    # check if the message has been cached (again, in case of concurency issues)
                    if message.id in self.cache:
                        return False
                    # Add the message id to the cache
                    self.cache.append(message.id)
                    # Clean old cache entries if needed
                    if len(self.cache) > 20:
                        self.cache = self.cache.pop(0) # limited to 20 entries
                    
                    # Rosetta now react on this message with the setting emoji
                    await message.add_reaction(self.bot.data.save['pinboard'][idx]['emoji'])

                    # Prepare the pin
                    try:
                        user : disnake.Member = await message.guild.get_or_fetch_member(message.author.id) # get the full user to get their full name
                        if user is None: # in case of issues, fallback to message.author
                            message.author
                        # prepare a dict we'll convert to a disnake.Embed
                        embed_dict : JSON = {}
                        embed_dict['color'] = self.COLOR
                        embed_dict['footer'] = {'text':"#{}".format(origin_channel_name), 'url':None} # channel name
                        embed_dict['title'] = user.display_name + " - @" + str(message.author) # user name and handle
                        # add message content in description
                        if len(content) > 0: 
                            if len(content) > 1900: # if the message is too big
                                embed_dict['description'] = content[:1900] + "...\n\n" # truncate
                            else:
                                embed_dict['description'] = content + "\n\n"
                        else:
                            embed_dict['description'] = ""
                        # add user avatar
                        embed_dict['thumbnail'] = {'url':str(user.display_avatar)}
                        # prepare fields
                        embed_dict['fields'] = []
                        # check if the message got attachments
                        if message.attachments:
                            file : disnake.Attachment
                            for file in message.attachments: # check attached files
                                if file.is_spoiler(): # file is a spoiler, simply put the url
                                    embed_dict['fields'].append({'inline': True, 'name':'Attachment', 'value':f'[{file.filename}]({file.url})'})
                                elif file.url.lower().split("?", 1)[0].endswith(('.png', '.jpeg', '.jpg', '.gif', '.webp', 'jpg:thumb', 'jpg:small', 'jpg:medium', 'jpg:large', 'jpg:orig', 'png:thumb', 'png:small', 'png:medium', 'png:large', 'png:orig')) and 'image' not in embed_dict: # file is an image...
                                    embed_dict['image'] = {'url':file.url} # so set it directly as the embed image
                                else: # else put it simply as an url
                                    embed_dict['fields'].append({'inline': True, 'name':'Attachment', 'value':f'[{file.filename}]({file.url})'})
                        # search for image url if we haven't set one yet
                        if 'image' not in embed_dict:
                            s : int = content.find("http://")
                            if s == -1:
                                s = content.find("https://")
                            if s != -1:
                                # iterate over possible extensions
                                ext : str
                                e : int = -1
                                for ext in ['.png', '.jpeg', '.jpg', '.gif', '.webp', 'jpg:thumb', 'jpg:small', 'jpg:medium', 'jpg:large', 'jpg:orig', 'png:thumb', 'png:small', 'png:medium', 'png:large', 'png:orig']:
                                    e = content.find(ext, s)
                                    if e != -1:
                                        e += len(ext)
                                        break
                                # if we found one, set it as the image url
                                if e!= -1 and content.find(' ', s, e) == -1:
                                    embed_dict['image'] = {'url':content[s:e]}
                        # finally check the message embeds
                        if len(message.embeds) > 0: # we will ONLY check the first embed
                            if message.embeds[0].description is not None and len(message.embeds[0].description) > 0: # if it got stuff in its description, we add it in a field
                                if len(message.embeds[0].description) > 1000: # truncate if too big
                                    embed_dict['fields'] = [{'inline': True, 'name':'Content', 'value':message.embeds[0].description[:1000] + '\n...'}] + embed_dict['fields']
                                else:
                                    embed_dict['fields'] = [{'inline': True, 'name':'Content', 'value':message.embeds[0].description}] + embed_dict['fields']
                            # add the embed image if we haven't set one
                            if 'image' not in embed_dict and message.embeds[0].image.url is not None:
                                embed_dict['image'] = {'url':message.embeds[0].image.url}
                            # and next...
                            if message.embeds[0].title is not None and len(message.embeds[0].title) > 0: # update our embed title field using this embed title
                                embed_dict['title'] += " ▫️ " + message.embeds[0].title
                            elif message.embeds[0].author is not None and message.embeds[0].author.name is not None: # or its author field
                                embed_dict['title'] += " ▫️ " + message.embeds[0].author.name
                        # add link to original message using a view
                        view : UrlButton = UrlButton(self.bot, [('Original Message', 'https://discordapp.com/channels/{}/{}/{}'.format(message.guild.id, message.channel.id, message.id))])
                        # Fix: remove image from dict if it's set to None
                        if 'image' in embed_dict and embed_dict['image'] is None:
                            embed_dict.pop('image')
                        # Create the embedd
                        embed : disnake.Embed = disnake.Embed.from_dict(embed_dict)
                        # Set the timestamp to the message timestamp
                        embed.timestamp=message.created_at
                        # Get channel
                        ch : disnake.Channel|None = self.bot.get_channel(self.bot.data.save['pinboard'][idx]['output'])
                        # And send!
                        await ch.send(embed=embed, view=view)
                        return True
                    except Exception as x:
                        if 'Missing Access' in str(x) or 'Missing Permissions' in str(x): # in case of missing permissions
                            try:
                                c : disnake.Channel|None = await self.bot.get_channel(message.channel_id) # post in the original message channel to inform people, if possible
                                await c.send(embed=self.bot.embed(title="Pinboard error", description="Note to the moderators: I'm not permitted to post in the pinboard channel"))
                            except:
                                pass
                        else:
                            self.bot.logger.pushError("[PINBOARD] 'pin' error, guild `{}`:".format(message.guild.id), x)
                        return False
        except Exception as e:
            self.bot.logger.pushError("[PINBOARD] 'pin' error:", e)
        return False

    """clean_data()
    Clean unused data
    """
    async def clean_data(self : Pinboard) -> bool:
        guild_ids : list[str] = set([str(g.id) for g in self.bot.guilds])
        count : int = 0
        await asyncio.sleep(1)
        gid : str
        for gid in list(self.bot.data.save['pinboard'].keys()):
            if gid not in guild_ids: # the bot left the guild
                self.bot.data.save['pinboard'].pop(gid)
                count += 1
            else:
                i : int = 0
                while i < len(self.bot.data.save['pinboard'][gid]['tracked']): # remove deleted channels from data
                    if self.bot.get_channel(self.bot.data.save['pinboard'][gid]['tracked'][i]) is None:
                        self.bot.data.save['pinboard'][gid]['tracked'].pop(i)
                        count += 1
                    else:
                        i += 1
                if self.bot.data.save['pinboard'][gid]['output'] is not None and self.bot.get_channel(self.bot.data.save['pinboard'][gid]['output']) is None: # remove data if empty
                    self.bot.data.save['pinboard'][gid]['output'] = None
                    count += 1
        if count > 0:
            self.bot.data.pending = True

    """is_enabled()
    Return True if the pinboard is enabled
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    
    Returns
    ----------
    bool: True if enabled, False otherwise
    """
    def is_enabled(self : Pinboard, server_id : str) -> bool:
        return server_id in self.bot.data.save['pinboard'] and 'disabled' not in self.bot.data.save['pinboard'][server_id]

    """reset()
    Reset the settings for a guild
    
    Parameters
    ----------
    inter : A valid disnake.GuildCommandInteraction. Must be deferred beforehand.
    color: Integer, embed color to use.
    """
    async def reset(self : Pinboard, inter : disnake.GuildCommandInteraction, color : int) -> None:
        server_id : str = str(inter.guild.id)
        # Check pinboard state
        if server_id in self.bot.data.save['pinboard']:
            self.bot.data.save['pinboard'].pop(server_id)
            msg = "The pinboard has been reset and is disabled"
        else:
            msg = "No pinboard data for this server"
        await self.render(inter, color, msg)

    """toggle()
    Toggle the system for a guild, if it exists
    
    Parameters
    ----------
    inter : A valid disnake.GuildCommandInteraction. Must be deferred beforehand.
    color: Integer, embed color to use.
    """
    async def toggle(self : Pinboard, inter : disnake.GuildCommandInteraction, color : int) -> None:
        server_id : str = str(inter.guild.id)
        # Check pinboard state
        msg : str
        if self.initialize(server_id):
            msg = "The pinboard is enabled"
        elif 'disabled' in self.bot.data.save['pinboard'][server_id]:
            self.bot.data.save['pinboard'][server_id].pop('disabled')
            self.bot.data.pending = True
            msg = "The pinboard is enabled"
        else:
            self.bot.data.save['pinboard'][server_id]['disabled'] = None
            self.bot.data.pending = True
            msg = "The pinboard is disabled"
        await self.render(inter, color, msg)

    """get()
    Retrieve the settings for a guild
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    
    Returns
    ----------
    dict: Stored settings, None if unavailable
    """
    def get(self : Pinboard, server_id : str) -> dict:
        return self.bot.data.save['pinboard'].get(server_id, None)

    """initialize()
    Initialize pinboard data for a guild if it doesn't exist
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    
    Returns
    ----------
    bool: True if data has been initialized, False otherwise
    """
    def initialize(self : Pinboard, server_id : str) -> bool:
        if server_id not in self.bot.data.save['pinboard']:
            self.bot.data.save['pinboard'][server_id] = {'tracked' : [], 'emoji': '⭐', 'mod_bypass':False, 'threshold':3, 'output': None}
            self.bot.data.pending = True
            return True
        return False

    """set()
    Set updated settings for a guild, if it exists
    
    Parameters
    ----------
    inter : A valid disnake.GuildCommandInteraction. Must be deferred beforehand.
    color: Integer, embed color to use.
    options: dict, settings to update
    """
    async def set(self : Pinboard, inter : disnake.GuildCommandInteraction, color : int, options : dict) -> None:
        server_id : str = str(inter.guild.id)
        msgs : list[str] = []
        error : str = ""
        # Initialize data
        self.initialize(server_id)
        # Update values
        if 'tracked' in options:
            self.bot.data.save['pinboard'][server_id]['tracked'] = options['tracked']
            msgs.append("Tracked Channels")
        if 'emoji' in options:
            self.bot.data.save['pinboard'][server_id]['emoji'] = options['emoji']
            msgs.append("Emoji")
        if 'mod_bypass' in options:
            self.bot.data.save['pinboard'][server_id]['mod_bypass'] = options['mod_bypass']
            msgs.append("Mod Bypass")
        if 'threshold' in options:
            self.bot.data.save['pinboard'][server_id]['threshold'] = options['threshold']
            msgs.append("Threshold")
        if options.get('set_output', False):
            if isinstance(inter.channel, disnake.TextChannel):
                self.bot.data.save['pinboard'][server_id]['output'] = inter.channel.id
                msgs.append("Output Channel")
            else:
                error = ":warning: The output channel can only be set to a Text channel"
        if len(msgs) > 0:
            msgs = ["**Modified:** ", ", ".join(msgs)]
            self.bot.data.pending = True
        if error != "":
            if len(msgs) > 0:
                msgs.append("\n")
            msgs.append(error)
        await self.render(inter, color, "".join(msgs))

    """track_toggle()
    Toggle given channel tracking for a guild
    
    Parameters
    ----------
    inter : A valid disnake.GuildCommandInteraction. Must be deferred beforehand.
    color: Integer, embed color to use.
    """
    async def track_toggle(self : Pinboard, inter : disnake.GuildCommandInteraction, color : int):
        server_id : str = str(inter.guild.id)
        channel_id : str = inter.channel.id
        msg : str = "An unexpected error occured, nothing changed"
        # Initialize data
        self.initialize(server_id)
        # Search for channel
        found : bool = False
        i : int = 0
        while i < len(self.bot.data.save['pinboard'][server_id]['tracked']):
            if self.bot.data.save['pinboard'][server_id]['tracked'][i] == channel_id: # channel is set as to be tracked
                found = True
                self.bot.data.save['pinboard'][server_id]['tracked'].pop(i) # untrack
                self.bot.data.pending = True
                msg = "This channel isn't tracked anymore"
            else:
                i += 1 # keep iterating in case multiple copies of the same channel id is in the list
        if not found:
            # channel isn't set, so we attempt to track
            # check the channel type
            if isinstance(inter.channel, disnake.TextChannel):
                self.bot.data.save['pinboard'][server_id]['tracked'].append(channel_id) 
                self.bot.data.pending = True
                msg = "This channel is now tracked"
            elif isinstance(inter.channel, disnake.Thread): # only allow tracking threads from forums
                try:
                    if not isinstance(inter.channel.parent, disnake.ForumChannel):
                        raise Exception()
                    self.bot.data.save['pinboard'][server_id]['tracked'].append(channel_id) 
                    self.bot.data.pending = True
                    msg = "This channel is now tracked"
                except:
                    msg = "This type of channel **can't** be tracked"
            else:
                msg = "This type of channel **can't** be tracked"
        await self.render(inter, color, msg)

    """render()
    Output settings to an interaction
    
    Parameters
    ----------
    inter : Interaction, must have been deferred beforehand
    color: Embed color value
    msg: Optional message to add in the description
    """
    async def render(self : Pinboard, inter : disnake.Interaction, color : int, msg : str = None) -> None:
        if inter.guild is None:
            await inter.edit_original_message(embed=self.bot.embed(title="Pinboard settings", description="This command is only usable in a server.", color=color))
            return
        fields : dict[str, str|bool] = []
        settings = self.bot.pinboard.get(str(inter.guild.id))
        if settings is None:
            fields.append({
                'name':'Information',
                'value': '**Pinboard not set for this server**\nCheck the `/mod pinboard` command group to start.',
                'inline': True
            })
        else:
            # tracked
            fields.append({
                'name':'Tracked channels',
                'value': '',
                'inline': True
            })
            updated_tracked : list[int] = []
            # tracked channels
            for cid in settings['tracked']:
                c : disnake.Channel|None = inter.guild.get_channel(int(cid))
                if c is None:
                    pass
                else:
                    updated_tracked.append(int(cid))
                    fields[-1]['value'] += '`#{}`\n'.format(c.name)
                    if len(fields[-1]['value']) > 950:
                        fields.append({
                            'name':'Tracked channels',
                            'value': '',
                            'inline': True
                        })
            if len(updated_tracked) != settings['tracked']:
                settings['tracked'] = updated_tracked
                self.bot.data.pending = True
            if fields[-1]['value'] == '':
                if len(fields) > 1:
                    fields.pop()
                else:
                    fields[-1]['value'] = "**None**"
            # emoji used
            fields.append({
                'name':'Used Emoji',
                'value': settings['emoji'],
                'inline': True
            })
            # threshold
            fields.append({
                'name':'Emoji Threshold',
                'value': str(settings['threshold']),
                'inline': True
            })
            # mod bypass
            fields.append({
                'name':'Mods bypass the threshold',
                'value': 'Enabled' if settings['mod_bypass'] else 'Disabled',
                'inline': True
            })
            # output
            fields.append({
                'name':'Output Channel',
                'value': '**Not Set**',
                'inline': True
            })
            if settings['output'] is not None:
                c : disnake.Channel|None = inter.guild.get_channel(int(settings['output']))
                if c is None:
                    settings['output'] = None
                    self.bot.data.pending = True
                else:
                    fields[-1]['value'] = '[#{}](https://discord.com/channels/{}/{})'.format(c.name, inter.guild.id, c.id)
            #disabled
            if 'disabled' in settings:
                fields.append({
                    'name':'Warning',
                    'value': '**Pinboard is currently disabled**',
                    'inline': True
                })
        icon : str|None
        try: icon = inter.guild.icon.url
        except: icon = None
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s Pinboard settings".format(inter.guild.name), 'icon_url':icon}, description=msg, fields=fields, inline=True, color=color))