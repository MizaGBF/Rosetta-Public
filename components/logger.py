import asyncio
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import logging
from logging.handlers import RotatingFileHandler

# ----------------------------------------------------------------------------------------------------------------
# Logger Component
# ----------------------------------------------------------------------------------------------------------------
# Store error messages and send them to Discord
# ----------------------------------------------------------------------------------------------------------------

class Logger():
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    NOTSET = logging.NOTSET
    COLORS = {
        CRITICAL : 0x6e0412,
        ERROR : 0xff0022,
        WARNING : 0xff8c00,
        INFO : 0x3eba25,
        DEBUG : 0xc7e046
    }
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.debug = bot.debug_mode or bot.test_mode
        logging.basicConfig(level=logging.INFO)
        self.logger = None
        if not self.bot.test_mode:
            self.logger = logging.getLogger('Rosetta')
            self.logger.setLevel(logging.NOTSET)
            discord_logger = logging.getLogger('disnake')
            discord_logger.setLevel(logging.WARNING)
            if not self.debug:
                self.logger.addHandler(RotatingFileHandler(filename="rosetta.log", encoding='utf-8', mode='w', maxBytes=51200, backupCount=1))
                discord_logger.addHandler(RotatingFileHandler(filename="disnake.log", encoding='utf-8', mode='w', maxBytes=51200, backupCount=1))
            for log_name in ['oauth2client', 'oauth2client.transport', 'oauth2client.client', 'oauth2client.crypt', 'httpx']:
                l = logging.getLogger(log_name)
                l.setLevel(logging.ERROR)

    def init(self) -> None:
        pass

    """color()
    Set the embed color according to the level
    
    Parameters
    ----------
    level: Integer
    """
    def color(self, level : int) -> None:
        return self.COLORS.get(level, 0x000000)

    """process()
    Read through the stack and send the errors to the debug channel
    """
    async def process(self) -> None:
        while True:
            try:
                await asyncio.sleep(2)
                if len(self.bot.data.save['log']) > 0:
                    logs = self.bot.data.save['log']
                    self.bot.data.save['log'] = []
                    self.bot.data.pending = True
                    for msg in logs:
                        if len(msg[1]) > 4000:
                            msg[1] = msg[1][:4000] + "...\n*Too long, check rosetta.log for details*"
                        await self.bot.send('debug', embed=self.bot.embed(title="Rosetta Log", description="### " + msg[1], footer=("Occured {} times".format(msg[2]) if msg[2] > 1 else ''), timestamp=msg[0], color=self.color(msg[3])))
                    logs = None # discard
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'bot:log' Task Cancelled")
                await asyncio.sleep(30)
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'bot:log' Task Error:", e)
                return

    """push()
    Push a message to the log stack.
    If the message is identical to the previous one, it increases its occurence stack instead
    
    Parameters
    ----------
    msg: A string
    send_to_discord: If true, it will be stored in the save data to be processed later
    level: Integer, logging level used by log()
    """
    def push(self, msg : str, send_to_discord : bool = True, level : int = logging.INFO) -> None:
        now = self.bot.util.UTC()
        if send_to_discord:
            if len(self.bot.data.save['log']) > 0 and self.bot.data.save['log'][-1][1] == msg:
                self.bot.data.save['log'][-1][2] += 1
            else:
                self.bot.data.save['log'].append([now, msg, 1, level])
            self.bot.data.pending = True
        try:
            self.logger.log(level, now.strftime("%Y-%m-%d %H:%M:%S | ") + msg)
        except:
            logging.log(level, now.strftime("%Y-%m-%d %H:%M:%S | ") + msg)

    """pushError()
    Wrapper around push() to send an exception
    
    Parameters
    ----------
    msg: A string
    exception: An exception
    send_to_discord: If true, it will be stored in the save data to be processed later
    level: Integer, logging level used by log()
    """
    def pushError(self, msg : str, exception : Optional[Exception] = None, send_to_discord : bool = True, level : int = logging.ERROR) -> None:
        if 'Session is closed' in str(exception):
            send_to_discord = False
        if exception is not None:
            self.push(msg + "\n" + self.bot.pexc(exception), send_to_discord, level)
        else:
            self.push(msg, send_to_discord, level)