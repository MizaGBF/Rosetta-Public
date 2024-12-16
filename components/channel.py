import disnake
import asyncio
from typing import Union, Optional, Any, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Channel Component
# ----------------------------------------------------------------------------------------------------------------
# This component lets you register channels with a keyword to be later used by the send() function of the bot
# ----------------------------------------------------------------------------------------------------------------

class Channel():
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.cache = {}
        self.announcements = [] # channels to send announcement to
        self.auto_publish = [] # channels to auto publish

    def init(self) -> None:
        self.cache = {}
        self.update_announcement_channels()

    """update_announcement_channels()
    Update announcement channel lists
    """
    def update_announcement_channels(self) -> None:
        # reset containers
        self.announcements = []
        self.auto_publish = []
        # loop over settings
        for v in self.bot.data.save.get('announcement', {}).values():
            self.announcements.append(v[0]) # add channel to announcements
            if v[1]: # auto publish flag is up
                self.auto_publish.append(v[0]) # so add to auto_publish too

    """can_publish()
    Check if the channel id is in auto_publish
    
    Parameters
    ----------
    channel_id: The channel id
    
    Returns
    ----------
    bool: True if it is, False otherwise
    """
    def can_publish(self, channel_id : int) -> bool:
        return (channel_id in self.auto_publish)

    """set()
    Register a channel with a name
    
    Parameters
    ----------
    name: Channel name
    id_key: Channel name in config.json
    """
    def set(self, name : str, id_key : str) -> None:
        try:
            if name in self.cache:
                raise Exception("Name already used")
            c = self.bot.get_channel(self.bot.data.config['ids'][id_key]) # retrieve channel for given config.json id
            if c is None:
                raise Exception("Channel not found")
            self.cache[name] = c # add to cache if it exists
            self.bot.logger.push("[CHANNEL] Channel '{}' registered".format(name), send_to_discord=False)
        except Exception as e:
            self.bot.logger.pushError("[CHANNEL] Couldn't register Channel '{}' using key '{}'".format(name, id_key), e)

    """setID()
    Register a channel with a name
    
    Parameters
    ----------
    name: Channel name
    cid: Channel id
    """
    def setID(self, name : str, cid : int) -> None:
        try:
            if name in self.cache:
                raise Exception("Name already used")
            c = self.bot.get_channel(cid) # retrieve channel for given id
            if c is None:
                raise Exception("Channel not found")
            self.cache[name] = c # add to cache if it exists
            self.bot.logger.push("[CHANNEL] Channel '{}' registered".format(name), send_to_discord=False)
        except Exception as e:
            self.bot.logger.pushError("[CHANNEL] Couldn't register Channel '{}' using ID '{}'".format(name, cid), e)

    """setMultiple()
    Register multiple channels
    
    Parameters
    ----------
    channel_list: List of pair [name, id_key or id]
    """
    def setMultiple(self, channel_list: list) -> None:
        for c in channel_list:
            if len(c) == 2 and isinstance(c[0], str): # iterate over list and call corresponding set function
                if isinstance(c[1], str):
                    self.set(c[0], c[1])
                elif isinstance(c[1], int):
                    self.setID(c[0], c[1])

    """has()
    Get a registered channel
    
    Parameters
    ----------
    name: Channel name. Can also pass directly a Channel ID if the channel isn't registered.
    
    Returns
    ----------
    bool: True if the channel name is cached
    """
    def has(self, name : str) -> bool:
        return (name in self.cache)

    """get()
    Get a registered channel
    
    Parameters
    ----------
    name: Channel name. Can also pass directly a Channel ID if the channel isn't registered.
    
    Returns
    ----------
    discord.Channel: Discord Channel, None if error
    """
    def get(self, name : str) -> disnake.abc.Messageable:
        return self.cache.get(name, self.bot.get_channel(name))

    """clean()
    Delete a bot command message after X amount of time depending on the
    The lyria emote will be used to replace the message.
    
    Parameters
    ----------
    target: A Disnake Context and Message OR a Disnake Interaction
    delay: Time in second before deletion
    all: if True, the message will be deleted, if False, the message is deleted it it was posted in an unauthorized channel
    """
    async def clean(self, target : Union[disnake.Message, disnake.ApplicationCommandInteraction], delay : Optional[Union[int, float]] = None, all : bool = False) -> None:
        try:
            match target:
                case disnake.ApplicationCommandInteraction()|disnake.ModalInteraction(): # interactions
                    if all or self.interaction_must_be_cleaned(target): # cleanup check
                        if delay is not None:
                            await asyncio.sleep(delay) # delete message after delay
                        # edit message with lyria emote
                        await target.edit_original_message(content=str(self.bot.emote.get('lyria')), embed=None, view=None, attachments=[])
                case disnake.Message(): # message
                    if all or not self.interaction_must_be_cleaned(target): # cleanup check
                        if delay is not None:
                            await asyncio.sleep(delay) # delete message after delay
                        # edit message with lyria emote
                        await target.edit(content=str(self.bot.emote.get('lyria')), embed=None, view=None, attachments=[])
        except Exception as e:
            if "Unknown Message" not in str(e):
                self.bot.logger.pushError("[UTIL] 'clean' error:", e)
            return False

    """interaction_must_be_cleaned()
    Take an interaction (or similar) and determine if cleanup must be invoked based on server settings
    
    Parameters
    ----------
    inter: Interaction or also Command context, message...
    
    Returns
    --------
    bool: True if if must be cleaned up, False if not
    """
    def interaction_must_be_cleaned(self, inter : Any) -> bool:
        if inter is None:
            return False
        settings = self.get_cleanup_settings(str(inter.guild.id))
        if settings[0] and inter.channel.id not in settings[1]:
            return True
        return False

    """toggle_cleanup()
    Toggle the server cleanup settings
    
    Parameters
    ----------
    gid: String, guild id
    """
    def toggle_cleanup(self, gid : str) -> None:
        if gid not in self.bot.data.save['cleanup']:
            self.bot.data.save['cleanup'][gid] = [False, []]
        else:
            self.bot.data.save['cleanup'][gid][0] = not self.bot.data.save['cleanup'][gid][0]
        self.bot.data.pending = True

    """reset_cleanup()
    Reset the server cleanup settings
    
    Parameters
    ----------
    gid: String, guild id
    """
    def reset_cleanup(self, gid : str) -> None:
        if gid in self.bot.data.save['cleanup']:
            self.bot.data.save['cleanup'].pop(gid)
            self.bot.data.pending = True

    """toggle_cleanup_channel()
    Toggle this server channel exception for the auto cleanup
    
    Parameters
    ----------
    gid: String, guild id
    cid: Integer, channel id
    """
    def toggle_cleanup_channel(self, gid : str, cid : int) -> None:
        if gid not in self.bot.data.save['cleanup']:
            self.bot.data.save['cleanup'][gid] = [True, [cid]]
            self.bot.data.pending = True
        elif cid not in self.bot.data.save['cleanup'][gid][1]:
            self.bot.data.save['cleanup'][gid][1].append(cid)
            self.bot.data.pending = True
        else:
            i = 0
            while i < len(self.bot.data.save['cleanup'][gid][1]):
                if self.bot.data.save['cleanup'][gid][1][i] == cid:
                    self.bot.data.save['cleanup'][gid][1].pop(i)
                    self.bot.data.pending = True
                else:
                    i += 1

    """clean_cleanup_data()
    Clean unused cleanup settings
    """
    def clean_cleanup_data(self) -> None:
        guild_ids = set([str(g.id) for g in self.bot.guilds])
        for gid in list(self.bot.data.save['cleanup'].keys()):
            if gid not in guild_ids or (not self.bot.data.save['cleanup'][gid][0] and len(self.bot.data.save['cleanup'][gid][1]) == 0):
                self.bot.data.save['cleanup'].pop(gid)
                self.bot.data.pending = True

    """get_cleanup_settings()
    Return the server cleanup settings
    
    Parameters
    ----------
    gid: String, guild id
    
    Returns
    ----------
    list: Containing Enable flag (bool) and the list of excluded channels (list[int])
    """
    def get_cleanup_settings(self, gid : str) -> list:
        return self.bot.data.save['cleanup'].get(gid, [False, []])

    """render_cleanup_settings()
    Output the server cleanup settings
    
    Parameters
    --------
    inter: A command interaction. Must have been deferred beforehand.
    """
    async def render_cleanup_settings(self, inter : disnake.GuildCommandInteraction, color : int) -> None:
        gid = str(inter.guild.id)
        settings = self.get_cleanup_settings(gid)
        descs = ["- Status ▫️ "]
        descs.append("**Enabled**" if settings[0] else "**Disabled**")
        descs.append("\nTo toggle this setting: ")
        descs.append(self.bot.util.command2mention('mod cleanup toggle'))
        if len(settings[1]) > 0:
            descs.append("\n- Excluded channels:\n")
            i = 0
            while i < len(settings[1]):
                ch = inter.guild.get_channel(settings[1][i])
                if ch is None: # deleted channel?
                    settings[1].pop(i)
                    self.bot.data.pending = True
                else:
                    descs.append("[#{}](https://discord.com/channels/{}/{}) ".format(ch.name, inter.guild.id, ch.id))
                    i += 1
        descs.append("\nTo toggle a channel exception: ")
        descs.append(self.bot.util.command2mention('mod cleanup channel'))
        descs.append(" in the channel.")
        await inter.edit_original_message(embed=self.bot.embed(title="{} Auto Cleanup settings".format(self.bot.emote.get('lyria')), description="".join(descs), footer=inter.guild.name + " ▫️ " + gid, color=color))