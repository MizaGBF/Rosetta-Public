from __future__ import annotations
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.util import JSON
    from components.network import RequestResult
import asyncio
import os

# ----------------------------------------------------------------------
# Emote Component
# ----------------------------------------------------------------------
# Register and retrieve custom emotes via keywords set in config.json
# For ease of use, set those emotes in the bot debug server
# ----------------------------------------------------------------------


class Emote():
    __slots__ = ("bot", "app_emojis", "unicode_emoji")

    def __init__(self : Emote, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.app_emojis : dict[str, disnake.Emoji] = {}
        self.unicode_emoji : dict[int, int|None] = {}

    def init(self : Emote) -> None:
        pass

    """init_request()
    Used to initialize unicode_emoji with a list of unicode emojis.
    It's used by isValid.
    Called once, after the bot boot.
    """
    async def init_request(self : Emote) -> None:
        # get a list of valid unicode emojis
        data : RequestResult = await self.bot.net.request('http://www.unicode.org/Public/emoji/1.0//emoji-data.txt')
        if data is None:
            self.bot.logger.pushError("[Emoji] Couldn't retrieve the list of unicode Emojis")
        else:
            try:
                # parse file
                data : list[str] = data.decode('utf-8').split('\n')
                d : str
                for d in data:
                    if d.startswith('#'):
                        continue
                    stripped : str = d.split(';', 1)[0].strip()
                    if stripped == "":
                        continue
                    dat : list[str] = stripped.split(' ')
                    # add emoji to dict
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
    def get(self : Emote, key : str) -> str|disnake.Emoji:
        return self.app_emojis.get(key, key)

    """isValid()
    Return True if the given string is an emoji the bot has access to.

    Parameters
    ----------
    emoji: Any string

    Returns
    --------
    bool: True if it's an emoji, False otherwise
    """
    def isValid(self : Emote, emoji : str) -> bool:
        if len(emoji) > 5 and emoji.startswith('<a:') and emoji.endswith('>'):
            # emoji is an animated emoji
            return self.bot.get_emoji(int(emoji[3:-1].split(':')[-1])) is not None
        elif len(emoji) > 4 and emoji.startswith('<:') and emoji.endswith('>'):
            # emoji is a non animated emoji
            return self.bot.get_emoji(int(emoji[2:-1].split(':')[-1])) is not None
        elif len(emoji) > 3 and emoji.startswith(':') and emoji.endswith(':') and ' ' not in emoji:
            # emoji is a standard :emoji:
            return True
        elif len(emoji) > 1 and ord(emoji[0]) in self.unicode_emoji:
            # emoji is an unicode emoji
            return True
        return False

    """get_all_app_emojis()
    Placeholder for get_all_app_emojis from the upcoming disnake 2.10+.
    Return the list of application emojis.

    Returns
    --------
    dict: The list of application emojis. Return none if error.
    """
    async def get_all_app_emojis(self : Emote) -> JSON|None:
        return await self.bot.http.request(
            disnake.http.Route(
                'GET',
                '/applications/{app_id}/emojis',
                app_id=self.bot.user.id
            )
        )

    """create_app_emoji()
    Placeholder for create_app_emoji from the upcoming disnake 2.10+.
    Create a new application emoji.

    Parameters
    --------
    name: String, must be alphanumeric and at least 2 in length
    image: Bytes, image data. Max 128x128 pixels.
    """
    async def create_app_emoji(self : Emote, name : str, image : bytes) -> None:
        await self.bot.http.request(
            disnake.http.Route(
                'POST',
                '/applications/{app_id}/emojis',
                app_id=self.bot.user.id,
                json={'name':name, 'image':await disnake.utils._assetbytes_to_base64_data(image)}
            )
        )

    """delete_app_emoji()
    Placeholder for delete_app_emoji from the upcoming disnake 2.10+.
    Create a new application emoji.

    Parameters
    --------
    name: String, must be alphanumeric and at least 2 in length
    image: Bytes, image data. Max 128x128 pixels.
    """
    async def delete_app_emoji(self : Emote, emoji_id : int) -> None:
        await self.bot.http.request(
            disnake.http.Route(
                'DELETE',
                '/applications/{app_id}/emojis/{emoji_id}',
                app_id=self.bot.user.id,
                emoji_id=emoji_id
            )
        )

    """create_emoji_in_cache_from()
    Placeholder until the upcoming disnake 2.10+.
    Create a new emoji from an application emoji data and put it in our cache.

    Parameters
    --------
    name: String, emoji name (matching the file name without extension)
    data: Dictionary, the emoji data
    """
    def create_emoji_in_cache_from(self : Emote, name : str, data : JSON) -> None:
        # note: Use the debug server as placeholder for the guild
        self.app_emojis[name] = disnake.Emoji(
            guild=self.bot.get_guild(self.bot.data.config['ids']['debug_server']),
            state=self.bot._connection,
            data=data
        )

    """load_app_emojis()
    Coroutine to load applicaiton emojis and add new/missing ones if any is found in assets/emojis
    """
    async def load_app_emojis(self : Emote) -> None:
        try:
            # list files in the assets/emojis folder
            emote_file_table : dict[str, str] = {
                f.split('.', 1)[0].ljust(2, '_') : f
                for f in next(os.walk("assets/emojis"), (None, None, []))[2]
            }
            # get the list of app emojis already set
            existing : JSON|None = await self.get_all_app_emojis()
            deleted : int = 0
            item : JSON
            for item in existing['items']: # and remove the ones already uploaded from emote_file_table
                if item['name'] not in emote_file_table:
                    await self.delete_app_emoji(item['id'])
                    deleted += 1
                else:
                    emote_file_table.pop(item['name'], None)
            if deleted > 0:
                self.bot.logger.push("[LOAD EMOJI] {} unused application emojis have been deleted.".format(deleted))
            # if we have files remaining to be uploaded in emote_file_table...
            if len(emote_file_table) > 0:
                self.bot.logger.push(
                    (
                        "[LOAD EMOJI] {} file(s) in the 'assets/emojis' folder not uploaded...\n"
                        "Uploading...\n(Expected time: {}s)"
                    ).format(len(emote_file_table), int(len(emote_file_table) * 1.3))
                )
                try:
                    k : str
                    v : str
                    for k, v in emote_file_table.items(): # for each of them
                        with open("assets/emojis/" + v, mode="rb") as f: # read the file
                            await self.create_app_emoji(k, f.read()) # and create an app emoji with it
                            await asyncio.sleep(1)
                    self.bot.logger.push("[LOAD EMOJI] Done.\nEmojis have been uploaded")
                except Exception as e:
                    self.bot.logger.pushError("[LOAD EMOJI] upload_app_emojis Error for {}:".format(v), e)
                    self.bot.logger.push("[LOAD EMOJI] An error occured.\nThe upload process has been aborted.")
                # get new updated list
                existing = await self.get_all_app_emojis()
        except Exception as xe:
            self.bot.logger.pushError("[LOAD EMOJI] upload_app_emojis Unexpected error in section A:", xe)
            self.bot.logger.push("[LOAD EMOJI] An unexpected error occured.\nThe upload process has been aborted.")
        # now initializing app emoji list
        try:
            for item in existing['items']: # for each emoji item
                name : str = item['name']
                if len(name) == 2 and name.endswith('_'):
                    name = name[0]
                self.create_emoji_in_cache_from(name, item) # set our custom cache with this emoji
        except Exception as e:
            self.bot.logger.pushError("[LOAD EMOJI] upload_app_emojis Unexpected error in section B:", e)
            self.bot.logger.push("[LOAD EMOJI] An unexpected error occured.\nThe upload process has been aborted.")
