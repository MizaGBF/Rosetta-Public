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
    # shortcut to these constants
    CRITICAL = logging.CRITICAL
    ERROR = logging.ERROR
    WARNING = logging.WARNING
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    NOTSET = logging.NOTSET
    # Embed colors for those log levels
    COLORS = {
        CRITICAL : 0x6e0412,
        ERROR : 0xff0022,
        WARNING : 0xff8c00,
        INFO : 0x3eba25,
        DEBUG : 0xc7e046
    }
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot
        debug = bot.debug_mode or bot.test_mode # check if the bot isn't in normal mode
        logging.basicConfig(level=logging.INFO)
        self.logger = None # logging object
        if not self.bot.test_mode: # we still create loggers in debug mode
            self.logger = logging.getLogger('Rosetta')
            self.logger.setLevel(logging.NOTSET)
            discord_logger = logging.getLogger('disnake')
            discord_logger.setLevel(logging.WARNING)
            if not debug: # plus rotary files in normal mode
                self.logger.addHandler(RotatingFileHandler(filename="rosetta.log", encoding='utf-8', mode='w', maxBytes=51200, backupCount=1))
                discord_logger.addHandler(RotatingFileHandler(filename="disnake.log", encoding='utf-8', mode='w', maxBytes=51200, backupCount=1))
            # we disable these logs
            for log_name in ['oauth2client', 'oauth2client.transport', 'oauth2client.client', 'oauth2client.crypt']:
                l = logging.getLogger(log_name)
                l.setLevel(logging.ERROR)

    def init(self) -> None:
        pass

    """color()
    Return an embed color according to the given level
    
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
                if len(self.bot.data.save['log']) > 0: # if messages are waiting in the queue
                    logs = self.bot.data.save['log'] # get them out
                    self.bot.data.save['log'] = [] # and clear
                    self.bot.data.pending = True
                    # for each message
                    for msg in logs:
                        if len(msg[1]) > 4000: # if too long, truncate
                            msg[1] = msg[1][:4000] + "...\n*Too long, check rosetta.log for details*"
                        # send the message to the debug channel
                        await self.bot.send('debug', embed=self.bot.embed(title="Rosetta Log", description="### " + msg[1], footer=("Occured {} times".format(msg[2]) if msg[2] > 1 else ''), timestamp=msg[0], color=self.color(msg[3])))
                    logs = None # set to None to discard, for garbage collection
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
        if send_to_discord: # if this flag is on
            if len(self.bot.data.save['log']) > 0 and self.bot.data.save['log'][-1][1] == msg: # if the last message in the log is the same
                self.bot.data.save['log'][-1][2] += 1 # we simply increase its occurence counter
            else: # else we add it to the queue
                self.bot.data.save['log'].append([now, msg, 1, level])
            self.bot.data.pending = True
        # push the message to the logger
        try:
            self.logger.log(level, now.strftime("%Y-%m-%d %H:%M:%S | ") + msg)
        except: # use this if the logger isn't set yet
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
        if 'Session is closed' in str(exception): # Don't send these errors to discord
            send_to_discord = False
        if exception is not None: # add full exception traceback to message
            self.push(msg + "\n" + self.bot.pexc(exception), send_to_discord, level)
        else: # simply push the message to the queue
            self.push(msg, send_to_discord, level)