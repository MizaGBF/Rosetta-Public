from typing import Union, Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Ban Component
# ----------------------------------------------------------------------------------------------------------------
# Manage Banned users
# ----------------------------------------------------------------------------------------------------------------

class Ban():
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def init(self) -> None:
        pass

    # ban flags
    OWNER   = 0b00000001
    SPARK   = 0b00000010
    PROFILE = 0b00000100
    USE_BOT = 0b10000000

    """set()
    Ban an user for different bot functions. Also update existing bans
    
    Parameters
    ----------
    uid: User discord id
    flag: Bit Mask
    """
    def set(self, uid : Union[int, str], flag : int) -> None:
        if not self.check(uid, flag):
            self.bot.data.save['ban'][str(uid)] = self.bot.data.save['ban'].get(str(uid), 0) ^ flag
            self.bot.data.pending = True

    """unset()
    Unban an user
    
    Parameters
    ----------
    uid: User discord id
    """
    def unset(self, uid : Union[int, str], flag : Optional[int] = None) -> None:
        if str(uid) in self.bot.data.save['ban']:
            if flag is None: self.bot.data.save['ban'].pop(str(uid))
            elif self.check(uid, flag): self.bot.data.save['ban'][str(uid)] -= flag
            if self.bot.data.save['ban'][str(uid)] == 0:
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
        return self.bot.data.save['ban'].get(str(uid), 0)