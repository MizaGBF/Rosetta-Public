from __future__ import annotations
import disnake
from disnake.ext import commands
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    # Type Aliases
    import types
    CleanupSetting : types.GenericAlias = list[bool|list[int]]
    AnnouncementSetting : types.GenericAlias = list[int|bool]

# ----------------------------------------------------------------------------------------------------------------
# Channel Component
# ----------------------------------------------------------------------------------------------------------------
# This component lets you register channels with a keyword to be later used by the send() function of the bot
# It also manages settings related to channels (auto message cleanup, announcement channel...)
# ----------------------------------------------------------------------------------------------------------------

class Channel():
    def __init__(self : Channel, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.cache : dict[str, disnake.abc.Messageable] = {}
        self.announcements : list[int] = [] # channels to send announcement to
        self.auto_publish : list[int] = [] # channels to auto publish

    def init(self : Channel) -> None:
        self.cache = {}
        self.update_announcement_channels()

    """update_announcement_channels()
    Update announcement channel lists
    """
    def update_announcement_channels(self : Channel) -> None:
        # reset containers
        self.announcements = []
        self.auto_publish = []
        # loop over settings
        for v in self.bot.data.save.get('announcement', {}).values():
            if v[0] > 0: # valid id
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
    def can_publish(self : Channel, channel_id : int) -> bool:
        return (channel_id in self.auto_publish)

    """set()
    Register a channel with a name
    
    Parameters
    ----------
    name: Channel name
    id_key: Channel name in config.json
    """
    def set(self : Channel, name : str, id_key : str) -> None:
        try:
            if name in self.cache:
                raise Exception("Name already used")
            c : disnake.Channel|None = self.bot.get_channel(self.bot.data.config['ids'][id_key]) # retrieve channel for given config.json id
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
    def setID(self : Channel, name : str, cid : int) -> None:
        try:
            if name in self.cache:
                raise Exception("Name already used")
            c : disnake.Channel|None = self.bot.get_channel(cid) # retrieve channel for given id
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
    def setMultiple(self : Channel, channel_list: list[str|int]) -> None:
        c : str|int
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
    def has(self : Channel, name : str) -> bool:
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
    def get(self : Channel, name : str) -> disnake.abc.Messageable:
        return self.cache.get(name, self.bot.get_channel(name))

    """clean_data()
    Clean unused cleanup and announcement settings
    """
    async def clean_data(self : Channel) -> None:
        guild_ids : set[str] = set([str(g.id) for g in self.bot.guilds])
        await asyncio.sleep(1)
        # Note: data is removed if the bot left the guild or if the data is empty
        gid : str
        # cleanup
        for gid in list(self.bot.data.save['cleanup'].keys()):
            if gid not in guild_ids or (not self.bot.data.save['cleanup'][gid][0] and len(self.bot.data.save['cleanup'][gid][1]) == 0):
                self.bot.data.save['cleanup'].pop(gid)
                self.bot.data.pending = True
        # announcement
        for gid in list(self.save['announcement'].keys()):
            if gid not in guild_ids or (self.bot.get_channel(self.save['announcement'][gid][0]) is None and not self.save['announcement'][gid][1]):
                self.save['announcement'].pop(gid)
                self.bot.data.pending = True
        # update announcement channels
        self.bot.channel.update_announcement_channels()

    """clean()
    Delete a bot command message after X amount of time depending on the
    The lyria emote will be used to replace the message.
    
    Parameters
    ----------
    target: A Disnake Context and Message OR a Disnake Interaction
    delay: Time in second before deletion
    all: if True, the message will be deleted, if False, the message is deleted it it was posted in an unauthorized channel
    """
    async def clean(self : Channel, target : disnake.Message|disnake.ApplicationCommandInteraction, delay : int|float|None = None, all : bool = False) -> None:
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
    Take an interaction (or similar) and determine if cleanup must be invoked based on server settings.
    Will always return False when invoked in DMs.
    
    Parameters
    ----------
    inter : Interaction or also Command context, message...
    
    Returns
    --------
    bool: True if if must be cleaned up, False if not
    """
    def interaction_must_be_cleaned(self : Channel, inter : disnake.Interaction|disnake.Message|commands.Context) -> bool:
        if inter is None or inter.guild is None:
            return False
        settings : CleanupSetting = self.get_cleanup_settings(str(inter.guild.id))
        if settings[0] and inter.channel.id not in settings[1]:
            return True
        return False

    """toggle_cleanup()
    Toggle the server cleanup settings
    
    Parameters
    ----------
    gid: String, guild id
    """
    def toggle_cleanup(self : Channel, gid : str) -> None:
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
    def reset_cleanup(self : Channel, gid : str) -> None:
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
    def toggle_cleanup_channel(self : Channel, gid : str, cid : int) -> None:
        if gid not in self.bot.data.save['cleanup']:
            self.bot.data.save['cleanup'][gid] = [True, [cid]]
            self.bot.data.pending = True
        elif cid not in self.bot.data.save['cleanup'][gid][1]:
            self.bot.data.save['cleanup'][gid][1].append(cid)
            self.bot.data.pending = True
        else:
            i : int = 0
            while i < len(self.bot.data.save['cleanup'][gid][1]):
                if self.bot.data.save['cleanup'][gid][1][i] == cid:
                    self.bot.data.save['cleanup'][gid][1].pop(i)
                    self.bot.data.pending = True
                else:
                    i += 1

    """get_cleanup_settings()
    Return the server cleanup settings
    
    Parameters
    ----------
    gid: String, guild id
    
    Returns
    ----------
    list: Containing Enable flag (bool) and the list of excluded channels (list[int])
    """
    def get_cleanup_settings(self : Channel, gid : str) -> CleanupSetting:
        return self.bot.data.save['cleanup'].get(gid, [False, []])

    """render_cleanup_settings()
    Output the server cleanup settings
    
    Parameters
    --------
    inter : A command interaction. Must have been deferred beforehand.
    color: Integer, embed color to use.
    """
    async def render_cleanup_settings(self : Channel, inter : disnake.GuildCommandInteraction, color : int) -> None:
        gid : str = str(inter.guild.id)
        settings : CleanupSetting = self.get_cleanup_settings(gid)
        descs : list[str] = ["- Status ▫️ "]
        descs.append("**Enabled**" if settings[0] else "**Disabled**")
        descs.append("\nTo toggle this setting: ")
        descs.append(self.bot.util.command2mention('mod cleanup toggle'))
        if len(settings[1]) > 0:
            descs.append("\n- Excluded channels:\n")
            i : int = 0
            while i < len(settings[1]):
                ch : disnake.Channel|None = inter.guild.get_channel(settings[1][i])
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

    """get_announcement_settings()
    Return the server announcement settings
    
    Parameters
    ----------
    gid: String, guild id
    
    Returns
    ----------
    list: Containing the announcement channel id (int) and the auto publish flag (bool)
    """
    def get_announcement_settings(self : Channel, gid : str) -> AnnouncementSetting:
        return self.bot.data.save['announcement'].get(gid, [-1, False])

    """toggle_announcement()
    Toggle this server announcement setting for the given channel
    
    Parameters
    ----------
    gid: String, guild id
    cid: Integer, channel id
    """
    def toggle_announcement_channel(self : Channel, gid : str, cid : int) -> None:
        if gid not in self.bot.data.save['announcement']:
            self.bot.data.save['announcement'][gid] = [cid, False]
            self.bot.data.pending = True
        elif cid != self.bot.data.save['announcement'][gid][0]:
            self.bot.data.save['announcement'][gid][0] = cid
            self.bot.data.pending = True
        else:
            self.bot.data.save['announcement'][gid][0] = -1
            self.bot.data.pending = True
        # update announcement channels
        self.update_announcement_channels()

    """toggle_announcement_publish()
    Toggle this server announcement auto-publish setting
    
    Parameters
    ----------
    gid: String, guild id
    """
    def toggle_announcement_publish(self : Channel, gid : str) -> None:
        if gid not in self.bot.data.save['announcement']:
            self.bot.data.save['announcement'][gid] = [-1, True]
            self.bot.data.pending = True
        else:
            self.bot.data.save['announcement'][gid][1] = not self.bot.data.save['announcement'][gid][1]
            self.bot.data.pending = True
        # update announcement channels
        self.update_announcement_channels()

    """render_announcement_settings()
    Output the server announcement settings
    
    Parameters
    --------
    inter : A command interaction. Must have been deferred beforehand.
    color: Integer, embed color to use.
    """
    async def render_announcement_settings(self : Channel, inter : disnake.GuildCommandInteraction, color : int) -> None:
        gid : str = str(inter.guild.id)
        settings : AnnouncementSetting = self.get_announcement_settings(gid)
        c : disnake.Channel|None = self.bot.get_channel(settings[0])
        descs : list[str] = ["- Status ▫️ "]
        descs.append("**Enabled**" if c is not None else "**Disabled**")
        if c is None:
            descs.append("\nTo enable, use in the desired channel: ")
        else:
            descs.append("\n- Announcements are sent to [#{}](https://discord.com/channels/{}/{})\nTo set another or disable this one: ".format(c.name, inter.guild.id, c.id))
        descs.append(self.bot.util.command2mention("mod announcement channel"))
        descs.append("\n- Auto-Publish ▫️ ")
        descs.append("**Enabled**" if settings[1] else "**Disabled**")
        descs.append("\nTo toggle, use: ")
        descs.append(self.bot.util.command2mention("mod announcement publish"))
        descs.append("\n*The channel must be a News channel for it to take effect*")
        await inter.edit_original_message(embed=self.bot.embed(title="Announcement settings", description="".join(descs), footer=inter.guild.name + " ▫️ " + gid, color=color))