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
        self.announcements = []
        self.tweets = []
        self.tweets_spam = []
        self.auto_publish = []

    def init(self) -> None:
        self.cache = {}
        self.update_announcement_channels()

    """update_announcement_channels()
    Update announcement channel lists
    """
    def update_announcement_channels(self) -> None:
        self.announcements = []
        self.auto_publish = []
        self.tweets = []
        self.tweets_spam = []
        for k, v in self.bot.data.save.get('announcement', {}).items():
            self.announcements.append(v[0])
            if v[1]: self.tweets.append(v[0])
            if v[2]: self.tweets_spam.append(v[0])
            if v[3]: self.auto_publish.append(v[0])

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
            c = self.bot.get_channel(self.bot.data.config['ids'][id_key])
            if c is not None: self.cache[name] = c
        except:
            self.bot.logger.pushError("[CHANNEL] Invalid key: {}".format(id_key))

    """setID()
    Register a channel with a name
    
    Parameters
    ----------
    name: Channel name
    cid: Channel id
    """
    def setID(self, name : str, cid : int) -> None:
        try:
            c = self.bot.get_channel(cid)
            if c is not None: self.cache[name] = c
        except:
            self.bot.logger.pushError("[CHANNEL] Invalid ID: {}".format(cid))

    """setMultiple()
    Register multiple channels
    
    Parameters
    ----------
    channel_list: List of pair [name, id_key or id]
    """
    def setMultiple(self, channel_list: list) -> None:
        for c in channel_list:
            if len(c) == 2 and isinstance(c[0], str):
                if isinstance(c[1], str): self.set(c[0], c[1])
                elif isinstance(c[1], int): self.setID(c[0], c[1])

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