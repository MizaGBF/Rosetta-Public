from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler

# ----------------------------------------------------------------------
# Logger Component
# ----------------------------------------------------------------------
# Store error messages and send them to Discord
# ----------------------------------------------------------------------


class Logger():
    # shortcut to these constants
    CRITICAL : int = logging.CRITICAL
    ERROR : int = logging.ERROR
    WARNING : int = logging.WARNING
    INFO : int = logging.INFO
    DEBUG : int = logging.DEBUG
    NOTSET : int = logging.NOTSET
    # Embed colors for those log levels
    COLORS : dict[int, int] = {
        CRITICAL : 0x6e0412,
        ERROR : 0xff0022,
        WARNING : 0xff8c00,
        INFO : 0x3eba25,
        DEBUG : 0xc7e046
    }

    __slots__ = ("bot", "discord_queue", "__logger__")

    def __init__(self : Logger, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.discord_queue : list[list[datetime|str|int]] = []
        debug : bool = bot.debug_mode or bot.test_mode # check if the bot isn't in normal mode
        logging.basicConfig(level=logging.INFO)
        self.__logger__ : logging.Logger|None = None # logging object
        if not self.bot.test_mode: # we still create loggers in debug mode
            self.__logger__ = logging.getLogger('Rosetta')
            self.__logger__.setLevel(logging.NOTSET)
            discord_logger : logging.Logger = logging.getLogger('disnake')
            discord_logger.setLevel(logging.WARNING)
            if not debug: # plus rotary files in normal mode
                self.__logger__.addHandler(
                    RotatingFileHandler(
                        filename="rosetta.log",
                        encoding='utf-8',
                        mode='w',
                        maxBytes=51200,
                        backupCount=1
                    )
                )
                discord_logger.addHandler(
                    RotatingFileHandler(
                        filename="disnake.log",
                        encoding='utf-8',
                        mode='w',
                        maxBytes=51200,
                        backupCount=1
                    )
                )
            # we disable these logs
            for log_name in ('oauth2client', 'oauth2client.transport', 'oauth2client.client', 'oauth2client.crypt'):
                l : logging.Logger = logging.getLogger(log_name)
                l.setLevel(logging.ERROR)

    def init(self : Logger) -> None:
        pass

    def startTasks(self : Logger) -> None:
        self.bot.runTask('logger:process', self.process)

    """color()
    Return an embed color according to the given level

    Parameters
    ----------
    level: Integer

    Returns
    ----------
    int: Color
    """
    def color(self : Logger, level : int) -> int:
        return self.COLORS.get(level, 0x000000)

    """process()
    Read through the stack and send the errors to the debug channel
    """
    async def process(self : Logger) -> None:
        while True:
            try:
                await asyncio.sleep(2)
                if len(self.discord_queue) > 0: # if messages are waiting in the queue
                    # for each message
                    msg : list[datetime|str|int]
                    for msg in self.discord_queue:
                        if len(msg[1]) > 4000: # if too long, truncate
                            msg[1] = msg[1][:4000] + "...\n*Too long, check rosetta.log for details*"
                        # send the message to the debug channel
                        await self.bot.send(
                            'debug',
                            embed=self.bot.embed(
                                title="Rosetta Log",
                                description="### " + msg[1],
                                footer=(f"Occured {msg[2]} times" if msg[2] > 1 else ''),
                                timestamp=msg[0],
                                color=self.color(msg[3])
                            )
                        )
                    self.discord_queue = [] # and clear
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
    def push(self : Logger, msg : str, send_to_discord : bool = True, level : int = logging.INFO) -> None:
        now : datetime = self.bot.util.UTC()
        if send_to_discord: # if this flag is on
            # if the last message in the log is the same
            if len(self.discord_queue) > 0 and self.discord_queue[-1][1] == msg:
                self.discord_queue[-1][2] += 1 # we simply increase its occurence counter
            else: # else we add it to the queue
                self.discord_queue.append([now, msg, 1, level])
        # push the message to the logger
        try:
            self.__logger__.log(level, now.strftime("%Y-%m-%d %H:%M:%S | ") + msg)
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
    def pushError(
        self : Logger,
        msg : str,
        exception : Exception|None = None,
        send_to_discord : bool = True,
        level : int = logging.ERROR
    ) -> None:
        if 'Session is closed' in str(exception): # Don't send these errors to discord
            send_to_discord = False
        if exception is not None: # add full exception traceback to message
            self.push(msg + "\n" + self.bot.pexc(exception), send_to_discord, level)
        else: # simply push the message to the queue
            self.push(msg, send_to_discord, level)
