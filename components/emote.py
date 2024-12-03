import disnake
from typing import Union, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import asyncio
import os

# ----------------------------------------------------------------------------------------------------------------
# Emote Component
# ----------------------------------------------------------------------------------------------------------------
# Register and retrieve custom emotes via keywords set in config.json
# For ease of use, set those emotes in the bot debug server
# ----------------------------------------------------------------------------------------------------------------

class Emote():
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.app_emojis = {}
        self.unicode_emoji = {}

    def init(self) -> None:
        pass

    async def init_request(self) -> None:
        # get list of valid unicode emojis
        data = await self.bot.net.request('http://www.unicode.org/Public/emoji/1.0//emoji-data.txt')
        if data is None:
            self.bot.logger.pushError("[Emoji] Couldn't retrieve the list of unicode Emojis")
        else:
            try:
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
            except Exception as e:
                self.bot.logger.pushError("[Emoji] init error:", e)

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
        return self.app_emojis.get(key, key)

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

    async def load_app_emojis(self) -> None:
        emote_file_table = {f.split('.', 1)[0].ljust(2, '_') : f for f in next(os.walk("assets/emojis"), (None, None, []))[2]}
        # NOTE: Once disnake 2.10 is out, replace by get_all_app_emojis
        existing = await self.bot.http.request(disnake.http.Route('GET', '/applications/{app_id}/emojis', app_id=self.bot.user.id))
        for item in existing['items']:
            emote_file_table.pop(item['name'], None)
        if len(emote_file_table) > 0:
            self.bot.logger.push("[UPLOAD EMOJI] {} file(s) in the 'assets/emojis' folder not uploaded...\nUploading...\n(Expected time: {}s)".format(len(emote_file_table), int(len(emote_file_table)*1.1)))
            try:
                for k, v in emote_file_table.items():
                    with open("assets/emojis/" + v, mode="rb") as f:
                        # NOTE: Once disnake 2.10 is out, replace by create_app_emoji
                        await self.bot.http.request(disnake.http.Route('POST', '/applications/{app_id}/emojis', app_id=self.bot.user.id), json={'name': k, 'image':await disnake.utils._assetbytes_to_base64_data(f.read())})
                        await asyncio.sleep(1)
                self.bot.logger.push("[UPLOAD EMOJI] Done.\nEmojis have been uploaded")
            except Exception as e:
                self.bot.logger.pushError("[UPLOAD EMOJI] upload_app_emojis Error for {}".format(v), e)
                self.bot.logger.push("[UPLOAD EMOJI] An error occured.\nThe upload process has been aborted.")
            # get new updated list
            # NOTE: Once disnake 2.10 is out, replace by get_all_app_emojis
            existing = await self.bot.http.request(disnake.http.Route('GET', '/applications/{app_id}/emojis', app_id=self.bot.user.id))
        # initializing app emoji list
        for item in existing['items']:
            name = item['name']
            if len(name) == 2 and name.endswith('_'):
                name = name[0]
            # NOTE: Once disnake 2.10 is out, replace by get_emoji or equivalent
            em = disnake.Emoji(guild=self.bot.get_guild(self.bot.data.config['ids']['debug_server']), state=self.bot._connection, data=item)
            em._from_data(item)
            self.app_emojis[name] = em