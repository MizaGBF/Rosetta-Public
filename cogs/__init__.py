from __future__ import annotations
from importlib import import_module
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from disnake.ext import commands
import os
import ast

# configuration variables
DEBUG_SERVER_ID : int|None = None # the bot server
CREW_SERVER_ID : int|None = None # my crew server
# Note: In global scope to be usable during initialization

"""get_cogs_from_ast()
Find command Cogs from processing a Python abstract syntax grammar tree.

Parameters
----------
tree: The ast tree.

Returns
----------
list: A list of class definition
"""
def get_cogs_from_ast(tree : ast.Module) -> list[ast.ClassDef]:
    classes : list[ast.ClassDef] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef):
            base : ast.Attribute
            for base in node.bases:
                if base.attr == "Cog":
                    classes.append(node)
    return classes

"""loadCogFile()
Called by load() below.
Attempt to load a .py file and add it to the bot as a Command Cog.
Note: More than one cog per file is untested/unsupported.

Parameters
----------
bot: DiscordBot instance
path_filename: String, file path
filename: String, merely the filename
regex: Regex pattern to use to detect the Cog class name
relative: Optional string (default is an empty string), relative import path
package: Optional string, the package/folder the cog is part of
silent: Boolean (default is false). Doesn't log error messages if true.

Returns
--------
bool: True if loaded, False if not
"""
def loadCogFile(bot : DiscordBot, path_filename : str, filename : str, relative : str = "", package = str|None, silent : bool = False) -> tuple[int, int]:
    try:
        loadattempt : int = 0
        failed : int = 0
        with open(path_filename, mode='r', encoding='utf-8') as py:
            # check for BOM
            if ord(py.read(1)) != 65279:
                py.seek(0)
            tree : ast.Module = ast.parse(py.read())
            classes : list[ast.ClassDef] = get_cogs_from_ast(tree)
            for node in classes:
                try:
                    loadattempt += 1
                    module_name : str = filename[:-3]
                    _class : commands.cog.CogMeta = getattr(import_module(relative + module_name, package=package), node.name)
                    bot.add_cog(_class(bot))
                except Exception as e2:
                    bot.logger.pushError("[COG] Failed to instantiate class {}:".format(node.name), e2, send_to_discord=not silent)
                    failed += 1
            return loadattempt, failed
    except Exception as e:
        if 'No such file or directory:' in str(e):
            bot.logger.pushError("[COG] {} is missing and will be ignored.\nIgnore this message if it's intended.".format(path_filename), send_to_discord=not silent and filename != "test.py", level=bot.logger.WARNING)
        else:
            bot.logger.pushError("[COG] Exception in file {}:".format(path_filename), e, send_to_discord=not silent)
        return 1, 1

"""load()
Called on the bot startup.
Set the global server ID (for slash command guild_ids parameter).
And attempt to load and add all cogs in the cogs folder, along with the special optional cog test.py.

Parameters
----------
bot: DiscordBot instance

Returns
--------
tuple: Tuple containing the number of loaded cogs and the number of failed loadings
"""
def load(bot : DiscordBot) -> tuple[int, int]: # load all cogs in the 'cog' folder
    # Silent flag
    silent : bool = ('debug' not in bot.data.config)
    # Set the global ids
    global DEBUG_SERVER_ID
    try: # try to set debug server id for modules needing it
        DEBUG_SERVER_ID = bot.data.config['ids']['debug_server']
    except:
        bot.logger.push("[WARNING] 'debug_server' ID not set in 'config.json'", send_to_discord=not silent, level=bot.logger.WARNING)
        DEBUG_SERVER_ID = None
    global CREW_SERVER_ID
    CREW_SERVER_ID = bot.data.config['ids'].get('you_server', None)
    # Start the loading
    count : int = 0 # number of attempt at loading cogs
    failed : int = 0 # number of loading failed (ignore debug and test cogs)
    # List all files
    result : tuple[int, int]
    filename : str
    for filename in os.listdir('cogs/'):
        path_filename = os.path.join('cogs/', filename) # create path
        if filename not in ['__init__.py'] and filename.endswith('.py') and os.path.isfile(path_filename): # search for valid python files
            result = loadCogFile(bot, path_filename, filename, relative=".", package='cogs')
            count += result[0]
            failed += result[1]
    # Optional dev files
    result = loadCogFile(bot, "test.py", "test.py", silent=silent) # doesn't increase failed in case of errors
    # Return results
    return count, failed