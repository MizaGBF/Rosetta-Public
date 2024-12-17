from typing import Union, Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Ban Component
# ----------------------------------------------------------------------------------------------------------------
# Manage Banned users
# ----------------------------------------------------------------------------------------------------------------

class Ban():
    # ban flags (binary number)
    OWNER   = 0b00000001
    SPARK   = 0b00000010
    PROFILE = 0b00000100
    USE_BOT = 0b10000000

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def init(self) -> None:
        pass

    """set()
    Ban an user for different bot functions. Also update existing bans
    
    Parameters
    ----------
    uid: User discord id
    flag: Bit Mask
    """
    def set(self, uid : Union[int, str], flag : int) -> None:
        if not self.check(uid, flag): # if not banned for that flag
            # set ban flag
            self.bot.data.save['ban'][str(uid)] = self.bot.data.save['ban'].get(str(uid), 0) ^ flag
            self.bot.data.pending = True

    """unset()
    Unban an user
    
    Parameters
    ----------
    uid: User discord id
    flag: Bit Mask. Optional (If not present or None, all bans will be lifted)
    """
    def unset(self, uid : Union[int, str], flag : Optional[int] = None) -> None:
        if str(uid) in self.bot.data.save['ban']: # if user in ban list
            if flag is None: # total unban
                self.bot.data.save['ban'].pop(str(uid))
            elif self.check(uid, flag): # if user is banned for that flag, unban
                self.bot.data.save['ban'][str(uid)] -= flag
            if self.bot.data.save['ban'][str(uid)] == 0: # if user is totally unbanned, remove from list
                self.bot.data.save['ban'].pop(str(uid))
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
    def check(self, uid : Union[int, str], mask : int) -> bool:
        # apply mask to user flag to check if banned
        return ((self.bot.data.save['ban'].get(str(uid), 0) & mask) == mask)

    """get()
    Return the user bitmask
    
    Parameters
    ----------
    uid: User discord id
    
    Returns
    ----------
    int: Bitmask
    """
    def get(self, uid : Union[int, str]) -> int:
        # simply return the user ban value
        return self.bot.data.save['ban'].get(str(uid), 0)