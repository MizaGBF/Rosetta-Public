from __future__ import annotations
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Ban Component
# ----------------------------------------------------------------------------------------------------------------
# Manage Banned users
# ----------------------------------------------------------------------------------------------------------------

class Ban():
    # ban flags (binary number)
    OWNER   : int = 0b00000001
    SPARK   : int = 0b00000010
    PROFILE : int = 0b00000100
    USE_BOT : int = 0b10000000

    def __init__(self : Ban, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    def init(self : Ban) -> None:
        pass

    """set()
    Ban an user for different bot functions. Also update existing bans
    
    Parameters
    ----------
    uid: User discord id
    flag: Bit Mask
    """
    def set(self : Ban, uid : str, flag : int) -> None:
        if not isinstance(uid, str):
            raise TypeError("User ID isn't a string.")
        if not self.check(uid, flag): # if not banned for that flag
            # set ban flag
            self.bot.data.save['ban'][uid] = self.bot.data.save['ban'].get(uid, 0) ^ flag
            self.bot.data.pending = True

    """unset()
    Unban an user
    
    Parameters
    ----------
    uid: User discord id
    flag: Bit Mask. Optional (If not present or None, all bans will be lifted)
    """
    def unset(self : Ban, uid : str, flag : int|None = None) -> None:
        if not isinstance(uid, str):
            raise TypeError("User ID isn't a string.")
        if uid in self.bot.data.save['ban']: # if user in ban list
            if flag is None: # total unban
                self.bot.data.save['ban'].pop(uid)
            elif self.check(uid, flag): # if user is banned for that flag, unban
                self.bot.data.save['ban'][uid] -= flag
            if self.bot.data.save['ban'][uid] == 0: # if user is totally unbanned, remove from list
                self.bot.data.save['ban'].pop(uid)
            self.bot.data.pending = True

    """check()
    Return if the user is banned or not
    
    Parameters
    ----------
    uid: User discord id
    flag: Bit Mask to compare
    
    Returns
    ----------
    bool: True if banned, False if not
    """
    def check(self : Ban, uid : str, mask : int) -> bool:
        if not isinstance(uid, str):
            raise TypeError("User ID isn't a string.")
        # apply mask to user flag to check if banned
        return ((self.bot.data.save['ban'].get(uid, 0) & mask) == mask)

    """get()
    Return the user bitmask
    
    Parameters
    ----------
    uid: User discord id
    
    Returns
    ----------
    int: Bitmask
    """
    def get(self : Ban, uid : str) -> int:
        if not isinstance(uid, str):
            raise TypeError("User ID isn't a string.")
        # simply return the user ban value
        return self.bot.data.save['ban'].get(uid, 0)