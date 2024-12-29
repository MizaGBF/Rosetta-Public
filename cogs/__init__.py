from __future__ import annotations
from importlib import import_module
import disnake
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from disnake.ext import commands
import os
import ast

# configuration variables
DEBUG_SERVER_ID : int|None = None # the bot server
CREW_SERVER_ID : int|None = None # my crew server
# Note: In global scope to be usable during initialization

"""loadCogFile()
Called by load() below.
Attempt to load a .py file and add it to the bot as a Command Cog.
Note: More than one cog per file is untested/unsupported.

Parameters
----------
bot: DiscordBot instance
path_filename: String, file path
filename: String, merely the filename
relative: Optional string (default is an empty string), relative import path
package: Optional string, the package/folder the cog is part of
silent: Boolean (default is false). Doesn't log error messages if true.

Returns
--------
bool: True if loaded, False if not
"""
def loadCogFile(bot : DiscordBot, path_filename : str, filename : str, relative : str = "", package : str|None = None, silent : bool = False) -> tuple[int, int]:
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
    if result[0] == 1 and result[1] == 0:
        count += 1
    # Return results
    return count, failed


"""get_commands()
Read the member functions of a Cog to extract the command infos

Parameters
----------
_class: The Cog class
file_lines: List of strings. The content of the .py file, line by line (needed to find User and Message command descriptions).

Returns
----------
list: The list of command data dicts
"""
def get_commands(_class : commands.cog.CogMeta, file_lines : list[str]) -> list[dict[str, Any]]:
    cog_commands : list[dict[str, Any]] = []
    member : Any
    for member in _class.__dict__.values():
        if isinstance(member, (staticmethod, classmethod)):
            member = member.__func__
        if callable(member):
            d : dict[str, Any] = member.__dict__
            if 'docstring' in d:
                docstring : str = d['docstring']['description']
                if not docstring.startswith("Command Group") and not docstring.endswith("(Owner Only)"):
                    command_def : dict[str, Any] = {"name":"/"+d['qualified_name'], "type":0, "description":docstring, "parameters":[]}
                    if 'option' in d:
                        option : disnake.Option
                        for option in d['option'].options:
                            command_def["parameters"].append({"name":option.name, "description":option.description, "type":"("+str(option.type).replace('OptionType.', '').capitalize()+")", "required":option.required})
                    # add data
                    cog_commands.append(command_def)
            elif 'body' in d: # User and Message commands
                if isinstance(d['body'], disnake.app_commands.UserCommand) or isinstance(d['body'], disnake.app_commands.MessageCommand):
                    ctype : int = 1 if isinstance(d['body'], disnake.app_commands.UserCommand) else 2
                    # detect description
                    i : int = 0
                    j : int
                    description : str = ""
                    while i < len(file_lines) and description == "": # find where the function start
                        if d['qualified_name'] in file_lines[i]:
                            # check the next few lines for the description
                            for j in range(i+1, min(i+5, len(file_lines))):
                                split : list[str] = file_lines[j].split('"""')
                                if len(split) == 3:
                                    description = split[1]
                                    break
                        i += 1
                    # add data
                    cog_commands.append({"name":d['qualified_name'], "type":ctype, "description":description, "parameters":[]})
    return cog_commands

"""get_cogs_from_ast()
Find command Cogs by processing a Python abstract syntax grammar tree.

Parameters
----------
tree: The ast tree to process

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

"""getCommandList()
Load a .py file and extract the cogs and their commands.

Parameters
----------
bot: DiscordBot instance
path_filename: String, file path
filename: String, merely the filename
relative: Optional string (default is an empty string), relative import path
package: Optional string, the package/folder the cog is part of

Returns
----------
list: The list of cog data dicts
"""
def getCommandList(path_filename : str, filename : str, relative : str = "", package : str|None = None) -> list[dict[str, Any]] :
    cogs : list[dict[str, Any]] = []
    with open(path_filename, mode='r', encoding='utf-8') as py:
        # check for BOM
        if ord(py.read(1)) != 65279:
            py.seek(0)
        # read file
        file_content : str = py.read()
        # parse the file
        tree : ast.Module = ast.parse(file_content)
        # extract the cog classes
        classes : list[ast.ClassDef] = get_cogs_from_ast(tree)
        node : ast.ClassDef
        for node in classes:
            # filename without .py
            module_name : str = filename[:-3]
            # get class type
            _class : commands.cog.CogMeta = getattr(import_module(relative + module_name, package=package), node.name)
            # set color
            color : int = 0x615d5d # default Color
            try: color = _class.COLOR
            except: pass
            # append
            cogs.append({"name":node.name, "color":hex(color).replace("0x", "").zfill(6), "commands":get_commands(_class, file_content.split('\n'))})
    return cogs

"""writeHTMLHelp()
Finalize the generation of discordbot.html

Parameters
----------
version: Rosetta VERSION string
path: String, the path to write the file tobytes
cogs: The list of cog data dicts
"""
def writeHTMLHelp(version : str, path : str, cogs : list[dict[str, Any]]) -> None:
    # The filter buttons (Only all is in by default)
    filters : str = '\t\t\t<button class="btn active" onclick="filterSelection(\'all\')" style="background: #050505;">All</button>\n'
    # containers will contain the commands
    containers : str = ""
    # used for command type blocks, for their color and text
    cmd_color_type = ['7e9ccc', '77bf85', 'cc83b1']
    cmd_type = ['Slash Command', 'User Command', 'Message Command']
    # total number of command on the list added
    total_count = 0
    cog : dict[str, Any]
    for cog in cogs:
        # if the cog has commands
        if len(cog["commands"]) > 0:
            # add the cog filter button
            filters += '\t\t\t<button class="btn" onclick="filterSelection(\'{}\')" style="background: #{};">{}</button>\n'.format(cog["name"].lower(), cog["color"], cog["name"])
            # iterate the commands
            command : dict[str, Any]
            for command in cog["commands"]:
                total_count += 1 # increase counter
                # add command block and name
                containers += '\t\t\t<li class="command {}"'.format(cog["name"].lower()) # class 
                # add auto copy on click for slash commands
                if command["type"] == 0:
                    containers += 'onclick="copyCommand(\'{}\')"'.format(command["name"])
                # add the rest
                containers += '>\n\t\t\t\t<div class="command-name"><span style="display: inline-block;background: #{};padding: 5px;text-shadow: 2px 2px 2px rgba(0,0,0,0.75);">{}</span>&nbsp;<span style="display: inline-block;background: #{};padding: 3px;text-shadow: 2px 2px 2px rgba(0,0,0,0.5); font-size: 14px;">{}</span>&nbsp;&nbsp;{}'.format(cog["color"], cog["name"], cmd_color_type[command['type']], cmd_type[command['type']], command["name"])
                # add description
                if command["description"] != "":
                    containers += '</div>\n\t\t\t\t<div class="command-description"><b>Description :</b>&nbsp;{}'.format(command["description"].replace('(Mod Only)', '<b>(Mod Only)</b>').replace('((You) Mod Only)', '<b>((You) Mod Only)</b>').replace('((You) Server Only)', '<b>((You) Server Only)</b>').replace('(NSFW channels Only)', '<b>(NSFW channels Only)</b>'))
                    if len(command['description']) >= 100:
                        print("Warning: Command", command['name'], "description is too long.")
                else:
                    print("Warning: Command", command['name'], "has no description.")
                # add parameters
                if len(command["parameters"]) > 0:
                    containers += '</div>\n\t\t\t\t<div class="command-use"><b>Parameters :</b><br>'
                    for param in command["parameters"]:
                        if not param["required"]:
                            containers += "<b>(Optional)</b>&nbsp;"
                        containers += param["name"] + " " + param["type"]
                        if param["description"] != "":
                            containers += "&nbsp;:&nbsp;" + param["description"]
                        containers += "<br>"
                # close block
                containers += '\n\t\t\t\t</div>\n\t\t\t</li>\n'
            print(len(cog["commands"]), "slash commands in:", cog["name"])
    
    # loading assets/unformated_help.html
    BASE_HTML : str
    try:
        with open("assets/unformated_help.html", "r", encoding="utf-8") as f:
            BASE_HTML = f.read()
    except:
        print("Failed to read 'assets/unformated_help.html', process aborted.")
        return
    # write the result to my github page folder
    print("Writing to", path, "...")
    try:
        with open(path, "w", encoding="utf-8") as f:
            # insert the strings we created into unformated_help.html to create our file
            f.write(BASE_HTML.replace("VERSION_STRING", version).replace("FILTER_STRINGS", filters).replace("COMMAND_STRING", "{} commands".format(total_count)).replace("COMMAND_LIST", containers))
            print("Done")
    except:
        print("An error occured, failed to write to", path)
        return

"""generateHelp()
Start the process of generating discordbot.html.
Example: https://mizagbf.github.io/discordbot.html

Parameters
----------
version: The Rosetta VERSION string
path: The output path
"""
def generateHelp(version : str, path : str = ".") -> None:
    try:
        # set path
        if path == ".":
            path = "discordbot.html"
        elif os.path.isdir(path):
            if not path.endswith('/') and not path.endswith('\\'):
                path += "/"
            path += "discordbot.html"
        print("The HTML Help file will be written to:", path)
        print("Reading Cog files...")
        cogs : list[dict[str, Any]] = []
        filename : str
        for filename in os.listdir('cogs/'):
            path_filename : str = os.path.join('cogs/', filename) # create path
            if filename not in ['__init__.py'] and filename.endswith('.py') and os.path.isfile(path_filename): # search for valid python files
                cogs.extend(getCommandList(path_filename, filename, relative=".", package='cogs'))
        # Writing the HTML
        writeHTMLHelp(version, path, cogs)
    except Exception as e:
        print("An exception occured, the process has been aborted.")
        print("Exception:", e)