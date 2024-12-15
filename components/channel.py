import disnake
from typing import TYPE_CHECKING
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