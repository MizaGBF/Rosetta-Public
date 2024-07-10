from importlib import import_module
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import os
import re

# configuration variables
DEBUG_SERVER_ID = None # the bot server
CREW_SERVER_ID = None # my crew server

def loadCogFile(bot : 'DiscordBot', p : str, f : str, r : re.Pattern, relative : str = "", package = Optional[str], silent : bool = False) -> bool:
    try:
        with open(p, mode='r', encoding='utf-8') as py:
            all = r.findall(str(py.read())) # search all matches
            for group in all:
                try:
                    module_name = f[:-3] # equal to filename without .py
                    class_name = group # the cog Class name

                    module = import_module(relative + module_name, package=package) # import
                    _class = getattr(module, class_name) # make
                    bot.add_cog(_class(bot)) # instantiate and add to the bot
                    return True
                except Exception as e:
                    if not silent:
                        bot.logger.pushError("[COG] Exception in file {}:".format(p), e)
                    return False
    except Exception as e2:
        if not silent:
            bot.logger.pushError("[COG] Exception in file {}:".format(p), e2)
    return False

def load(bot : 'DiscordBot') -> tuple: # load all cogs in the 'cog' folder
    # set global id
    global DEBUG_SERVER_ID
    try: # try to set debug server id for modules needing it
        DEBUG_SERVER_ID = bot.data.config['ids']['debug_server']
    except:
        bot.logger.push("[WARNING] 'debug_server' ID not set in 'config.json'", level=bot.logger.WARNING)
        DEBUG_SERVER_ID = None
    global CREW_SERVER_ID
    CREW_SERVER_ID = bot.data.config['ids'].get('you_server', None)
    # start loading
    r = re.compile("^class ([a-zA-Z0-9_]*)\\(commands\\.Cog\\):", re.MULTILINE) # to search the name class
    count = 0 # number of attempt at loading cogs
    failed = 0 # number of loading failed (ignore debug and test cogs)
    for f in os.listdir('cogs/'): # list all files
        p = os.path.join('cogs/', f)
        if f not in ['__init__.py'] and f.endswith('.py') and os.path.isfile(p): # search for valid python file
            if loadCogFile(bot, p, f, r, relative=".", package='cogs'): count += 1
            else: failed += 1
    # optional dev files
    if loadCogFile(bot, "test.py", "test.py", r, silent=('debug' not in bot.data.config)): count += 1
    return count, failed # return attempts