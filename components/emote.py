import disnake
from typing import Union, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Emote Component
# ----------------------------------------------------------------------------------------------------------------
# Register and retrieve custom emotes via keywords set in config.json
# For ease of use, set those emotes in the bot debug server
# ----------------------------------------------------------------------------------------------------------------

class Emote():
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.cache = {}
        self.unicode_emoji = {}

    def init(self) -> None:
        pass

    async def init_request(self) -> None:
        # get list of valid unicode emojis
        data = await self.bot.net.request('http://www.unicode.org/Public/emoji/1.0//emoji-data.txt', no_base_headers=True)
        if data is None:
            self.bot.logger.pushError("[Emoji] Couldn't retrieve the list of unicode Emojis")
        else:
            data = data.decode('utf-8').split('\n')
            for l in data:
                if l.startswith('#'): continue
                dat = l.split(';', 1)[0].strip()
                if dat == "": continue
                dat = dat.split(' ')
                if len(dat) == 2:
                    self.unicode_emoji[int(dat[0], 16)] = int(dat[1], 16)
                elif len(dat) == 1:
                    self.unicode_emoji[int(dat[0], 16)] = None

    """get()
    Retrieve an Emojii using its id set in config.json
    The Emoji is also cached for future uses
    
    Parameters
    ----------
    key: Emote key set in config.json
    
    Returns
    --------
    unknown: Discord Emoji if success, empty string if error, key if not found
    """
    def get(self, key : str) -> Union[str, disnake.Emoji]:
        if key in self.cache:
            return self.cache[key]
        elif key in self.bot.data.config['emotes']:
            try:
                e = self.bot.get_emoji(self.bot.data.config['emotes'][key]) # ids are defined in config.json
                if e is not None:
                    self.cache[key] = e
                    return e
                return ""
            except:
                return ""
        return key

    """isValid()
    Return True if the string is an emoji the bot has access to
    
    Parameters
    ----------
    emoji: Any string
    
    Returns
    --------
    bool: True if it's an emoji, False otherwise
    """
    def isValid(self, emoji : str) -> bool:
        if len(emoji) > 5 and emoji.startswith('<a:') and emoji.endswith('>'):
            return self.bot.get_emoji(int(emoji[3:-1].split(':')[-1])) is not None
        elif len(emoji) > 4 and emoji.startswith('<:') and emoji.endswith('>'):
            return self.bot.get_emoji(int(emoji[2:-1].split(':')[-1])) is not None
        elif len(emoji) > 3 and emoji.startswith(':') and emoji.endswith(':') and ' ' not in emoji:
            return True
        elif len(emoji) > 1 and ord(emoji[0]) in self.unicode_emoji:
            return True
        return False