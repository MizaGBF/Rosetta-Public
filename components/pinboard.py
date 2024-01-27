import disnake
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from views.url_button import UrlButton

# ----------------------------------------------------------------------------------------------------------------
# Pinboard Component
# ----------------------------------------------------------------------------------------------------------------
# Enable the pinboard system ("extra pinned messages") in specific server
# ----------------------------------------------------------------------------------------------------------------

class Pinboard():
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.cache = [] # store pinned messages until reboot

    def init(self) -> None:
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
    async def pin(self, payload : disnake.RawReactionActionEvent) -> bool:
        try:
            idx = None
            origin_channel = self.bot.get_channel(payload.channel_id)
            origin_channel_name = origin_channel.name
            if isinstance(origin_channel, disnake.Thread):
                try:
                    c = origin_channel.parent
                    if not isinstance(c, disnake.ForumChannel): raise Exception()
                    channel_id = c.id
                    origin_channel_name = c.name
                except:
                    channel_id = payload.channel_id
            else:
                channel_id = payload.channel_id
            for s in self.bot.data.save['pinboard']:
                if channel_id in self.bot.data.save['pinboard'][s]['tracked']:
                    if self.is_enabled(s) and self.bot.data.save['pinboard'][s]['output'] is not None:
                        idx = s
                        break
            if idx is None:
                return False
            message = await origin_channel.fetch_message(payload.message_id)
            if message.id in self.cache: return False
            reactions = message.reactions
        except Exception as e:
            self.bot.logger.pushError("[PINBOARD] 'pin' error:", e)
            return False
        me = message.guild.me
        count = 0
        for reaction in reactions:
            if str(reaction.emoji) == self.bot.data.save['pinboard'][idx]['emoji']:
                users = await reaction.users().flatten()
                count = len(users)
                guild = message.guild
                content = message.content
                isMod = False
                count = 0
                if me in users: return False
                for u in users:
                    if self.bot.data.save['pinboard'][idx]['mod_bypass']: # mod check
                        m = await guild.get_or_fetch_member(u.id)
                        if m.guild_permissions.manage_messages: 
                            isMod = True
                            break
                        else:
                            count += 1
                    else:
                        count += 1
                if not isMod and count < self.bot.data.save['pinboard'][idx]['threshold']:
                    return False

                if message.id in self.cache: return False # anti dupe safety
                self.cache.append(message.id)
                if len(self.cache) > 20: self.cache = self.cache.pop(0) # limited to 20 entries
                await message.add_reaction(self.bot.data.save['pinboard'][idx]['emoji'])

                try:
                    embed_dict = {}
                    embed_dict['color'] = 0xf20252
                    embed_dict['footer'] = {'text':"#{}".format(origin_channel_name), 'url':None}
                    embed_dict['title'] = message.author.display_name + " - @" + str(message.author)
                    if len(content) > 0: 
                        if len(content) > 1900: embed_dict['description'] = content[:1900] + "...\n\n"
                        else: embed_dict['description'] = content + "\n\n"
                    else: embed_dict['description'] = ""
                    embed_dict['thumbnail'] = {'url':str(message.author.display_avatar)}
                    embed_dict['fields'] = []
                    # for attachments
                    if message.attachments:
                        for file in message.attachments:
                            if file.is_spoiler():
                                embed_dict['fields'].append({'inline': True, 'name':'Attachment', 'value':f'[{file.filename}]({file.url})'})
                            elif file.url.lower().split("?")[0].endswith(('.png', '.jpeg', '.jpg', '.gif', '.webp', 'jpg:thumb', 'jpg:small', 'jpg:medium', 'jpg:large', 'jpg:orig', 'png:thumb', 'png:small', 'png:medium', 'png:large', 'png:orig')) and 'image' not in embed_dict:
                                embed_dict['image'] = {'url':file.url}
                            else:
                                embed_dict['fields'].append({'inline': True, 'name':'Attachment', 'value':f'[{file.filename}]({file.url})'})
                    # search for image url if no attachment
                    if 'image' not in embed_dict:
                        s = content.find("http://")
                        if s == -1: s = content.find("https://")
                        if s != -1:
                            for ext in ['.png', '.jpeg', '.jpg', '.gif', '.webp', 'jpg:thumb', 'jpg:small', 'jpg:medium', 'jpg:large', 'jpg:orig', 'png:thumb', 'png:small', 'png:medium', 'png:large', 'png:orig']:
                                e = content.find(ext, s)
                                if e != -1:
                                    e += len(ext)
                                    break
                            if e!= -1 and content.find(' ', s, e) == -1:
                                embed_dict['image'] = {'url':content[s:e]}
                    # check embed
                    if len(message.embeds) > 0:
                        if message.embeds[0].description is not None and len(message.embeds[0].description) > 0:
                            if len(message.embeds[0].description) > 1000:
                                embed_dict['fields'] = [{'inline': True, 'name':'Content', 'value':message.embeds[0].description[:1000] + '\n...'}] + embed_dict['fields']
                            else:
                                embed_dict['fields'] = [{'inline': True, 'name':'Content', 'value':message.embeds[0].description}] + embed_dict['fields']
                        if 'image' not in embed_dict and message.embeds[0].image.url is not None: embed_dict['image'] = {'url':message.embeds[0].image.url}
                        if message.embeds[0].title is not None and len(message.embeds[0].title) > 0: embed_dict['title'] += " ▫️ " + message.embeds[0].title
                        elif message.embeds[0].author is not None and message.embeds[0].author.name is not None: embed_dict['title'] += " ▫️ " + message.embeds[0].author.name
                    # add link via a view
                    view = UrlButton(self.bot, [('Original Message', 'https://discordapp.com/channels/{}/{}/{}'.format(message.guild.id, message.channel.id, message.id))])
                    if 'image' in embed_dict and embed_dict['image'] is None:
                        embed_dict.pop('image')
                    embed = disnake.Embed.from_dict(embed_dict)
                    embed.timestamp=message.created_at
                    ch = self.bot.get_channel(self.bot.data.save['pinboard'][idx]['output'])
                    await ch.send(embed=embed, view=view)
                    return True
                except Exception as x:
                    if 'Missing Access' in str(x) or 'Missing Permissions' in str(x):
                        try:
                            c = await self.bot.get_channel(message.channel_id)
                            await c.send(mbed=self.bot.embed(title="Pinboard error", description="Note to the moderators: I'm not permitted to post in the pinboard channel"))
                        except:
                            pass
                    else:
                        self.bot.logger.pushError("[PINBOARD] 'pin' error, guild `{}`:".format(message.guild.id), x)
                    return False
        return False

    """is_enabled()
    Return True if the pinboard is enabled
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    
    Returns
    ----------
    bool
    """
    def is_enabled(self, server_id : str) -> bool:
        return server_id in self.bot.data.save['pinboard'] and 'disabled' not in self.bot.data.save['pinboard'][server_id]

    """enable()
    Enable the system for a guild, if it exists
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    """
    def enable(self, server_id : str) -> None:
        if server_id in self.bot.data.save['pinboard']:
            if 'disabled' in self.bot.data.save['pinboard'][server_id]:
                self.bot.data.save['pinboard'][server_id].pop('disabled')
            self.bot.data.pending = True

    """disable()
    Disable the system for a guild, if it exists
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    """
    def disable(self, server_id : str) -> None:
        if server_id in self.bot.data.save['pinboard']:
            if 'disabled' not in self.bot.data.save['pinboard'][server_id]:
                self.bot.data.save['pinboard'][server_id]['disabled'] = None
            self.bot.data.pending = True

    """get()
    Retrieve the settings for a guild
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    
    Returns
    ----------
    dict: Stored settings, None if unavailable
    """
    def get(self, server_id : str) -> dict:
        return self.bot.data.save['pinboard'].get(server_id, None)

    """initialize()
    Initialize pinboard data for a guild if it doesn't exist
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    """
    def initialize(self, server_id : str) -> None:
        if server_id not in self.bot.data.save['pinboard']:
            self.bot.data.save['pinboard'][server_id] = {'tracked' : [], 'emoji': '⭐', 'mod_bypass':False, 'threshold':3, 'output': None}
            self.bot.data.pending = True

    """set()
    Set updated settings for a guild, if it exists
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    options: dict, settings to update
    """
    def set(self, server_id : str, **options : dict) -> None:
        if server_id in self.bot.data.save['pinboard']:
            self.bot.data.save['pinboard'][server_id]['tracked'] = options.get('tracked', self.bot.data.save['pinboard'][server_id]['tracked'])
            self.bot.data.save['pinboard'][server_id]['emoji'] = options.get('emoji', self.bot.data.save['pinboard'][server_id]['emoji'])
            self.bot.data.save['pinboard'][server_id]['mod_bypass'] = options.get('mod_bypass', self.bot.data.save['pinboard'][server_id]['mod_bypass'])
            self.bot.data.save['pinboard'][server_id]['threshold'] = options.get('threshold', self.bot.data.save['pinboard'][server_id]['threshold'])
            self.bot.data.save['pinboard'][server_id]['output'] = options.get('output', self.bot.data.save['pinboard'][server_id]['output'])
            self.bot.data.pending = True

    """track_toggle()
    Set updated settings for a guild, if it exists
    
    Parameters
    ----------
    server_id: Guild ID, in string format
    channel_id: Channel ID, as an integer
    
    Returns
    ----------
    value: None if nothing changed, False if removed, True if added
    """
    def track_toggle(self, server_id : str, channel_id : int) -> Optional[bool]:
        found = None
        if server_id in self.bot.data.save['pinboard']:
            found = False
            i = 0
            while i < len(self.bot.data.save['pinboard'][server_id]['tracked']):
                if self.bot.data.save['pinboard'][server_id]['tracked'][i] == channel_id:
                    found = True
                    self.bot.data.save['pinboard'][server_id]['tracked'].pop(i)
                    self.bot.data.pending = True
                else:
                    i += 1
            if not found:
                self.bot.data.save['pinboard'][server_id]['tracked'].append(channel_id)
                self.bot.data.pending = True
        return not found

    """display()
    Output settings to an interaction
    
    Parameters
    ----------
    inter: Interaction, must have been deferred beforehand
    color: Embed color value
    msg: Optional message to add in the description
    """
    async def display(self, inter : disnake.Interaction, color : int, msg : str = None) -> None:
        fields = []
        settings = self.bot.pinboard.get(str(inter.guild.id))
        if settings is None:
            fields.append({
                'name':'Information',
                'value': '**Pinboard not set for this server**',
                'inline': True
            })
        else:
            # tracked
            fields.append({
                'name':'Tracked channels',
                'value': '',
                'inline': True
            })
            updated_tracked = []
            for cid in settings['tracked']:
                c = inter.guild.get_channel(int(cid))
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
                self.bot.pinboard.set(str(inter.guild.id), tracked=updated_tracked)
            if fields[-1]['value'] == '':
                if len(fields) > 1:
                    fields.pop()
                else:
                    fields[-1]['value'] = "**None**"
            # emoji
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
                c = inter.guild.get_channel(int(settings['output']))
                if c is None:
                    self.bot.pinboard.set(str(inter.guild.id), output=None)
                else:
                    fields[-1]['value'] = '[#{}](https://discord.com/channels/{}/{})'.format(c.name, inter.guild.id, c.id)
            #disabled
            if 'disabled' in settings:
                fields.append({
                    'name':'Warning',
                    'value': '**Pinboard is currently disabled on this server**',
                    'inline': True
                })
        try: icon = inter.guild.icon.url
        except: icon = None
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s Pinboard settings".format(inter.guild.name), 'icon_url':icon}, description=msg, fields=fields, inline=True, color=color))