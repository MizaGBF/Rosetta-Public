from components.data import Data
from components.drive import Drive
from components.util import Util
from components.network import Network
from components.pinboard import Pinboard
from components.emote import Emote
from components.calc import Calc
from components.channel import Channel
from components.file import File
from components.sql import SQL
from components.ranking import Ranking
from components.ban import Ban
from components.gacha import Gacha
from components.logger import Logger
import cogs

import disnake
from disnake.ext import commands
from typing import Any, Optional, Union, Callable
import asyncio
import time
import signal
import sys
import os
import json
import traceback

# Main Bot Class (overload commands.Bot)
class DiscordBot(commands.InteractionBot):
    VERSION = "11.10.1" # bot version
    CHANGELOG = [ # changelog lines
        "Please use `/bug_report`, open an [issue](https://github.com/MizaGBF/Rosetta-Public) or check the [help](https://mizagbf.github.io/discordbot.html) if you have a problem.",
        "**v11.7.2** - Extra Drops timer added to `/gbf info` and `/gbf schedule`.",
        "**v11.8.2** - `/gw utility` commands updated with the new Nightmare, using **Placeholder** values for now.",
        "**v11.8.3** - Moved `/gbf check crystal` to `/gbf campaign crystal`. Added `/gbf campaign element`.",
        "**v11.8.4** - Moved `/gw utility nm` to `/gw nm hp90_95`. Added `/gw nm hp100`.",
        "**v11.8.5** - Updated `/guide defense`.",
        "**v11.9.1** - Updated some `/gw` commands. Added `/gw utility clump`.",
        "**v11.9.2** - Removed `/gw stats` commands. The website gbfteamraid.fun seems to be dead.",
        "**v11.9.3** - Revamped `/gw utility` commands. `/gw utility clump` has been merged into `/gw utility meat`.",
        "**v11.10.0** - Fixed a bug in `/reminder` commands and added automatic reminders. Make sure your server receives Bot Announcements.",
    ]
    EMOJI_INIT_NONE = 0
    EMOJI_INIT_RUNNING = 1
    EMOJI_INIT_ERROR = -1
    
    def __init__(self, test_mode : bool = False, debug_mode : bool = False) -> None:
        self.running = True # is False when the bot is shutting down
        self.debug_mode = debug_mode # indicate if we are running the debug version of the bot
        self.test_mode = test_mode # indicate if we are running the test version of the bot
        self.emoji_initialization = self.EMOJI_INIT_NONE # set by init_emoji()
        self.emoji_initialization_content = None # set by init_emoji()
        self.booted = False # goes up to True after the first on_ready event
        self.tasks = {} # contain our user tasks
        self.cogn = 0 # number of cog loaded
        
        # components
        try:
            self.util = Util(self)
            self.logger = Logger(self)
            self.logger.push("[BOOT] Logger started up. Loading components...", send_to_discord=False)
            self.data = Data(self)
            try:
                self.drive = Drive(self)
            except OSError:
                self.logger.push("[BOOT] Please setup your Google account 'service-secrets.json' to use the bot.", send_to_discord=False, level=self.logger.CRITICAL)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(4)
            except Exception:
                self.logger.push("[BOOT] Failed to initialize the Drive component", send_to_discord=False, level=self.logger.CRITICAL)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(5)
            self.net = Network(self)
            self.pinboard = Pinboard(self)
            self.emote = Emote(self)
            self.calc = Calc(self)
            self.channel = Channel(self)
            self.file = File(self)
            self.sql = SQL(self)
            self.ranking = Ranking(self)
            self.ban = Ban(self)
            self.gacha = Gacha(self)
            self.logger.push("[BOOT] Components loaded", send_to_discord=False)
        
            # initialize important components
            self.logger.push("[BOOT] Initializing important components...", send_to_discord=False)
            self.logger.init()
            self.data.init()
            self.drive.init()
            self.logger.push("[BOOT] Important components initialized", send_to_discord=False)
        except Exception as ce:
            try:
                self.logger.pushError("[BOOT] A component failed:", ce, send_to_discord=False)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(5)
            except:
                pass
        
        # loading data
        self.logger.push("[BOOT] Loading the config file...", send_to_discord=False)
        if not self.data.loadConfig():
            self.logger.push("[BOOT] Failed to load the config file. Please check if it exists or if its content is correct.", send_to_discord=False, level=self.logger.CRITICAL)
            self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
            time.sleep(500)
            os._exit(1)
        if not test_mode:
            self.logger.push("[BOOT] Downloading the save file...", send_to_discord=False)
            for i in range(0, 50): # try multiple times in case google drive is unresponsive
                if self.drive.load() is True:
                    break # attempt to download the save file
                elif i == 49:
                    self.logger.push("[BOOT] Couldn't access Google Drive and load the save file", send_to_discord=False, level=self.logger.CRITICAL)
                    self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                    time.sleep(500)
                    os._exit(3)
                time.sleep(20) # wait 20 sec
            self.logger.push("[BOOT] Reading the save file...", send_to_discord=False)
            if not self.data.loadData():
                self.logger.push("[BOOT] Couldn't load save.json, it's either invalid or corrupted", send_to_discord=False, level=self.logger.CRITICAL)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(2) # load the save file
        else:
            self.data.save = self.data.checkData(self.data.save) # dummy data
        
        # initialize remaining components
        try:
            self.logger.push("[BOOT] Initializing remaining components...", send_to_discord=False)
            self.util.init()
            self.net.init()
            self.pinboard.init()
            self.emote.init()
            self.calc.init()
            self.channel.init()
            self.file.init()
            self.sql.init()
            self.ranking.init()
            self.ban.init()
            self.gacha.init()
            self.logger.push("[BOOT] Remaining components initialized", send_to_discord=False)
        except Exception as ce:
            try:
                self.logger.pushError("[BOOT] A component failed:", ce, send_to_discord=False)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(5)
            except:
                pass

        # init base bot class
        try:
            # Intents
            intents = disnake.Intents.default()
            intents.message_content = True
            #intents.messages = True # uncomment this line to enable message intents
        
            # constructor
            self.logger.push("[BOOT] Initializing disnake.InteractionBot with Intent flags: 0b{:b}".format(intents.value), send_to_discord=False)
            super().__init__(max_messages=None, intents=intents, command_sync_flags=commands.CommandSyncFlags.default())
            self.add_app_command_check(self.global_check, slash_commands=True, user_commands=True, message_commands=True)
            self.logger.push("[BOOT] Initialization complete", send_to_discord=False)
        except Exception as ce:
            try:
                self.logger.pushError("[BOOT] Initialization failed:", ce, send_to_discord=False)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(6)
            except:
                pass

    """test_bot()
    Test function, to verify the cogs load properly
    """
    def test_bot(self) -> None:
        self.cogn, failed = cogs.load(self)
        if failed > 0:
            self.logger.pushError("{} cog(s) / {} failed to load".format(failed, self.cogn), send_to_discord=False)
        else:
            self.logger.push("OK", send_to_discord=False)

    """start_bot()
    Main Bot Loop
    
    Parameters
    --------
    no_cogs: Boolean, set to True to not load the cogs
    """
    def start_bot(self, no_cogs : bool = False) -> None:
        if no_cogs:
            self.cogn = 0
            failed = 0
        else:
            self.logger.push("[MAIN] Loading cogs...", send_to_discord=False)
            self.cogn, failed = cogs.load(self) # load cogs
        if failed > 0:
            self.logger.push("[MAIN] {} cog(s) / {} failed to load".format(failed, self.cogn), send_to_discord=False, level=self.logger.CRITICAL)
            time.sleep(36000)
            return
        else:
            self.logger.push("[MAIN] All cogs loaded", send_to_discord=False)
        # graceful exit setup
        graceful_exit = self.loop.create_task(self.exit_gracefully())
        for s in [signal.SIGTERM, signal.SIGINT]:
            try: # unix
                self.loop.add_signal_handler(s, graceful_exit.cancel)
            except: # windows
                signal.signal(s, self._exit_gracefully_internal)
        self.logger.push("[MAIN] v{} starting up...".format(self.VERSION), send_to_discord=False)
        # main loop
        while self.running:
            try:
                self.loop.run_until_complete(self.run_bot()) # start the bot
            except KeyboardInterrupt:
                self.logger.push("[MAIN] Keyboard Interrupt, shutting down...", send_to_discord=False)
                self.running = False
            except Exception as e: # handle exceptions here to avoid the bot dying
                if str(e).startswith("429 Too Many Requests"): # ignore the rate limit error
                    time.sleep(100)
                else:
                    self.logger.pushError("[MAIN] A critical error occured:", e)
                if self.data.pending: # save if anything weird happened (if needed)
                    self.data.saveData()
        if self.data.pending:
            self.data.saveData()

    """init_emoji()
    Init the emojis ID in config.json. See the README for more infos.
    """
    def init_emoji(self) -> None:
        # laod cogs to not delete integrations
        self.logger.push("[MAIN] Loading cogs...", send_to_discord=False)
        self.cogn, failed = cogs.load(self) # load cogs
        if failed > 0:
            self.logger.push("[MAIN] {} cog(s) / {} failed to load".format(failed, self.cogn), send_to_discord=False, level=self.logger.CRITICAL)
            return
        else:
            self.logger.push("[MAIN] All cogs loaded", send_to_discord=False)
        # emoji initialization
        try:
            self.emoji_initialization = self.EMOJI_INIT_RUNNING
            filenames = next(os.walk("assets/emojis"), (None, None, []))[2]
            self.logger.push("[INIT EMOJI] {} file(s) in the 'assets/emojis' folder".format(len(filenames)), send_to_discord=False)
            table = self.data.config['emotes'].copy()
            for k in table:
                table[k] = None
            self.logger.push("[INIT EMOJI] {} emoji(s) expected in 'config.json'".format(len(table)), send_to_discord=False)
            if len(filenames) != len(table):
                self.logger.push("[INIT EMOJI] Numbers of file and emoji don't match", send_to_discord=False, level=self.logger.WARNING)
            self.logger.push("[INIT EMOJI] Checking correspondances...", send_to_discord=False)
            normal = 0
            animated = 0
            for k in filenames:
                v = k.rpartition('.')
                if v[0] in table:
                    pass
                elif v[0].lower() in table:
                    v[0] = v[0].lower()
                elif v[0].upper() in table:
                    v[0] = v[0].upper()
                elif v[0].capitalize() in table:
                    v[0] = v[0].capitalize()
                else:
                    self.logger.push("[INIT EMOJI] '{}' doesn't seem to match any key in 'config.json'".format(k), send_to_discord=False, level=self.logger.ERROR)
                    raise Exception("Unknown emoji " + k)
                table[v[0]] = ''.join(v)
                if v[2].lower() == 'gif': animated += 1
                else: normal += 1
            self.logger.push("[INIT EMOJI] Check finished", send_to_discord=False)
            self.logger.push("[INIT EMOJI] {} normal emoji(s) and {} animated emoji(s)".format(normal, animated), send_to_discord=False)
            self.logger.push("[INIT EMOJI] Connecting to Discord...", send_to_discord=False)
            self.emoji_initialization_content = [table, normal, animated]
            try:
                self.loop.run_until_complete(self.start(self.data.config['tokens']['discord']))
            except:
                pass
            self.logger.push("[INIT EMOJI] Disconnected from Discord", send_to_discord=False)
            if self.emoji_initialization == self.EMOJI_INIT_ERROR:
                raise Exception("emoji_initialization error flag is set")
            self.logger.push("[INIT EMOJI] Initialization is over", send_to_discord=False)
            self.logger.push("[INIT EMOJI] Type 'confirm' to confirm the changes to config.json", send_to_discord=False)
            self.logger.push("[INIT EMOJI] Type 'cancel' to cancel", send_to_discord=False)
            while True:
                i = input().lower()
                if i == 'confirm':
                    i = True
                    break
                elif i == 'cancel':
                    i = False
                    break
                else:
                    self.logger.push("[INIT EMOJI] Invalid answer", send_to_discord=False)
                    self.logger.push("[INIT EMOJI] Type 'confirm' or 'cancel' to continue.", send_to_discord=False)
            if i:
                self.logger.push("[INIT EMOJI] Loading config.json...", send_to_discord=False)
                with open('config.json', mode="r", encoding="utf-8") as f:
                    filecontent = f.read()
                self.logger.push("[INIT EMOJI] Creating backup...", send_to_discord=False)
                with open('config.bak.json', mode="w", encoding="utf-8") as f:
                    f.write(filecontent)
                self.logger.push("[INIT EMOJI] Loading JSON...", send_to_discord=False)
                data = json.loads(filecontent)
                self.logger.push("[INIT EMOJI] Applying changes...", send_to_discord=False)
                data['emotes'] = self.emoji_initialization_content[0]
                self.logger.push("[INIT EMOJI] Saving config.json...", send_to_discord=False)
                with open('config.json', mode="w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                self.logger.push("[INIT EMOJI] Emoji Initialization complete", send_to_discord=False)
            else:
                self.logger.push("[INIT EMOJI] Initialization has been cancelled", send_to_discord=False)
                self.logger.push("[INIT EMOJI] Changes won't be saved", send_to_discord=False)
                self.logger.push("[INIT EMOJI] Note: The uploaded Emojis won't be deleted. It's recommended to do it yourself.", send_to_discord=False)
        except Exception as e:
            self.logger.pushError("[INIT EMOJI] init_emoji Error", e, send_to_discord=False)
            self.logger.push("[INIT EMOJI] Initialization is aborted...", send_to_discord=False, level=self.logger.CRITICAL)

    """run_bot()
    Followup from start_bot(). Switch to asyncio and initialize the aiohttp client
    """
    async def run_bot(self) -> None:
        async with self.net.init_clients():
            await self.emote.init_request()
            await self.start(self.data.config['tokens']['discord'])

    """exit_gracefully()
    Coroutine triggered when SIGTERM is received, to close the bot
    """
    async def exit_gracefully(self) -> None: # graceful exit (when SIGTERM is received)
        try:
            while self.running: # we wait until we receive the signal
                await asyncio.sleep(10000)
        except asyncio.CancelledError:
            await self.close()
            self._exit_gracefully_internal()

    """_exit_gracefully_internal()
    Routine to exit gracefully. Called by exit_gracefully() if using loop.add_signal_handler(), else directly by signal.signal().
    Note: Calling exit_gracefully.cancel() in this function makes Python crash on Windows, hence the roundabout way.
    
    Parameters
    ----------
    signum: Integer (Optional), the signal number
    frame: Frame (Optional), the stack
    """
    def _exit_gracefully_internal(self, signum = None, frame = None) -> None:
        self.running = False
        if self.data.pending and not self.debug_mode:
            self.data.autosaving = False
            count = 0
            while count < 3:
                if self.data.saveData():
                    self.logger.push("[EXIT] Auto-saving successful", send_to_discord=False)
                    break
                else:
                    self.logger.pushError("[EXIT] Auto-saving failed (try {}/3)".format(count+1), send_to_discord=False)
                    time.sleep(2)
                count += 1
        self.logger.push("[EXIT] Exited gracefully", send_to_discord=False)
        os._exit(0)

    """isAuthorized()
    Check if the channel is set as Authorized by the auto clean up system.
    
    Parameters
    ----------
    inter: Command context, message or interaction
    
    Returns
    --------
    bool: True if authorized, False if not
    """
    def isAuthorized(self, inter : Any) -> bool:
        if inter is None: return False
        gid = str(inter.guild.id)
        if gid in self.data.save['permitted']: # if id is found, it means the check is enabled
            if inter.channel.id in self.data.save['permitted'][gid]:
                return True # permitted
            return False # not permitted
        return True # default

    """isServer()
    Check if the interaction is matching this server (server must be set in config.json)
    
    Parameters
    ----------
    inter: Command interaction
    id_string: Server identifier in config.json
    
    Returns
    --------
    bool: True if matched, False if not
    """
    def isServer(self, inter : disnake.ApplicationCommandInteraction, id_string : str) -> bool:
        if inter.guild.id == self.data.config['ids'].get(id_string, -1):
            return True
        return False

    """isChannel()
    Check if the interaction is matching this channel (channel must be set in config.json)
    
    Parameters
    ----------
    inter: Command interaction
    id_string: Channel identifier in config.json
    
    Returns
    --------
    bool: True if matched, False if not
    """
    def isChannel(self, inter : disnake.ApplicationCommandInteraction, id_string : str) -> bool:
        if inter.channel.id == self.data.config['ids'].get(id_string, -1):
            return True
        return False

    """isMod()
    Check if the interaction author has the manage message permission
    
    Parameters
    ----------
    inter: Command interaction
    
    Returns
    --------
    bool: True if it does, False if not
    """
    def isMod(self, inter : disnake.ApplicationCommandInteraction) -> bool:
        if inter.author.guild_permissions.manage_messages or inter.author.id == self.owner.id:
            return True
        return False

    """isOwner()
    Check if the interaction author is the owner (id must be set in config.json)
    
    Parameters
    ----------
    inter: Command interaction
    
    Returns
    --------
    bool: True if it does, False if not
    """
    def isOwner(self, inter : disnake.ApplicationCommandInteraction) -> bool:
        if inter.author.id == self.owner.id:
            return True
        return False

    """send()
    Send a message to a registered channel (must be set in config.json)
    
    Parameters
    ----------
    channel_name: Channel name identifier
    msg: Text message
    embed: Discord Embed
    file: Discord File
    publish: Boolean. Try to publish the message if set to True. Auto publish must be enabled on the channel
    
    Returns
    --------
    disnake.Message: The sent message or None if error
    """
    async def send(self, channel_name : str, msg : str = "", embed : disnake.Embed = None, file : disnake.File = None, view : disnake.ui.View = None, publish : bool = False) -> Optional[disnake.Message]: # send something to a registered channel
        try:
            c = self.channel.get(channel_name)
            message = await c.send(msg, embed=embed, file=file, view=view)
            try:
                if publish is True and c.is_news() and self.channel.can_publish(c.id):
                    await message.publish()
            except:
                pass
            return message
        except Exception as e:
            if embed is not None:
                message = "[SEND] Failed to send a message to '{}'\n**Embed Title Start**: `{}`\n**Embed Description Start**: `{}`".format(channel_name, str(embed.title)[:100], str(embed.description)[:100])
            else:
                message = "[SEND] Failed to send a message to '{}':".format(channel_name)
            self.logger.pushError(message, e)
            return None

    """sendMulti()
    Send a message to multiple registered channel (must be set in config.json)
    
    Parameters
    ----------
    channel_names: List of Channel name identifiers
    msg: Text message
    embed: Discord Embed
    file: Discord File
    publish: Boolean. Try to publish the message if set to True
    
    Returns
    --------
    list: A list of the successfully sent messages
    """
    async def sendMulti(self, channel_names : list, msg : str = "", embed : disnake.Embed = None, file : disnake.File = None, publish : bool = False) -> list: # send to multiple registered channel at the same time
        r = []
        err = []
        ex = None
        for c in channel_names:
            try:
                r.append(await self.send(c, msg, embed, file, None, publish))
            except Exception as e:
                ex = e
                err.append(c)
        if ex is not None:
            self.logger.pushError("[SEND] Failed to send messages to following channels: {}".format(err), ex)
        return r

    """changeAvatar()
    Change the bot avatar with a file present in the assets folder
    
    Parameters
    ----------
    filename: File name with extension
    
    Returns
    --------
    bool: True if success, False if not
    """
    async def changeAvatar(self, filename : str) -> bool:
        try:
            with open("assets/avatars/" + filename, mode="rb") as f:
                await self.user.edit(avatar=f.read())
            return True
        except Exception as e:
            self.logger.pushError("[MAIN] 'changeAvatar' failed", e)
            return False

    """on_ready()
    Event. Called on connection
    """
    async def on_ready(self) -> None: # called when the bot starts
        if self.emoji_initialization == self.EMOJI_INIT_RUNNING: # init_emoji() sequence
            try:
                uploaded = []
                self.emoji_initialization = self.EMOJI_INIT_NONE
                guild = self.get_guild(self.data.config['ids']['debug_server'])
                normal_limit = guild.emoji_limit
                animated_limit = guild.emoji_limit
                self.logger.push("[INIT_EMOJI] Checking for free emoji slots...", send_to_discord=False)
                for e in guild.emojis:
                    if e.animated: animated_limit -= 1
                    else: normal_limit -= 1
                self.logger.push("[INIT_EMOJI] {} free normal emoji slots for {} required".format(normal_limit, self.emoji_initialization_content[1]), send_to_discord=False)
                self.logger.push("[INIT_EMOJI] {} free animated emoji slots for {} required".format(animated_limit, self.emoji_initialization_content[2]), send_to_discord=False)
                if self.emoji_initialization_content[1] > normal_limit or self.emoji_initialization_content[2] > animated_limit:
                    self.logger.push("[INIT_EMOJI] Not enough emoji slots, please make space and try again", send_to_discord=False, level=self.logger.ERROR)
                    self.emoji_initialization = self.EMOJI_INIT_ERROR
                else:
                    self.logger.push("[INIT_EMOJI] Uploading emojis...", send_to_discord=False)
                    for k, v in self.emoji_initialization_content[0].items():
                        with open("assets/emojis/" + v, mode="rb") as f:
                            emoji = await guild.create_custom_emoji(name=k.ljust(2, '_'), image=f.read())
                        self.emoji_initialization_content[0][k] = emoji.id
                        uploaded.append(emoji)
                        await asyncio.sleep(0.2) # for rate limit
                    self.logger.push("[INIT_EMOJI] Upload complete", send_to_discord=False)
            except Exception as e:
                self.emoji_initialization = self.EMOJI_INIT_ERROR
                self.logger.pushError("[INIT_EMOJI] on_ready Error", e, send_to_discord=False)
                if len(uploaded) > 0:
                    self.logger.push("[INIT_EMOJI] Attempting to cleaning up uploaded emojis...", send_to_discord=False)
                    for emoji in uploaded:
                        try: await guild.delete_emoji(emoji)
                        except: pass
            # disconnect
            self.logger.push("[INIT_EMOJI] Disconnecting from Discord...", send_to_discord=False)
            await self.http.close() # note: self.close() crashes Python 3.11 on windows
        elif not self.booted: # normal boot sequence
            # set our used channels for the send function
            self.channel.setMultiple([['debug', 'debug_channel'], ['image', 'image_upload']])
            await self.send('debug', embed=self.embed(title="{} is Ready".format(self.user.display_name), description=self.util.statusString(), thumbnail=self.user.display_avatar, timestamp=self.util.UTC()))
            # check guilds and start the tasks
            self.booted = True
            self.logger.push("[MAIN] Rosetta is ready", send_to_discord=False)
            self.startTasks()
            await asyncio.sleep(1)
            msg = ""
            for t in self.tasks:
                msg += "- {}\n".format(t)
            if msg != "":
                self.logger.push("[MAIN] {} Tasks started\n{}".format(len(self.tasks), msg))

    """embed()
    Create a disnake.Embed object
    
    Parameters
    ----------
    **options: disnake.Embed options

    Returns
    --------
    disnake.Embed: The created embed
    """
    def embed(self, **options : dict) -> disnake.Embed:
        embed = disnake.Embed(title=options.get('title', ""), description=options.pop('description', ""), url=options.pop('url', ""), color=options.pop('color', 16777215))
        fields = options.pop('fields', [])
        inline = options.pop('inline', False)
        for f in fields:
            embed.add_field(name=f.get('name'), value=f.get('value'), inline=f.pop('inline', inline))
        if options.get('thumbnail', None) not in [None, '']:
            embed.set_thumbnail(url=options['thumbnail'])
        if options.get('footer', None) is not None:
            embed.set_footer(text=options['footer'], icon_url=options.get('footer_url', None))
        if options.get('image', None) not in [None, '']:
            embed.set_image(url=options['image'])
        if options.get('timestamp', None) is not None:
            embed.timestamp=options['timestamp']
        if 'author' in options and 'name' in options['author']:
            embed.set_author(name=options['author'].pop('name', ""), url=options['author'].pop('url', None), icon_url=options['author'].pop('icon_url', None))
        return embed

    """pexc()
    Convert an exception to a string with the full traceback
    
    Parameters
    ----------
    exception: The error
    
    Returns
    --------
    unknown: The string, else the exception parameter if an error occured
    """
    def pexc(self, exception : Exception) -> Union[str, Exception]: # format an exception
        try:
            return "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        except:
            return exception

    """runTask()
    Start a new bot task (cancel any previous one with the same name
    
    Parameters
    ----------
    name: Task identifier
    coro: The coroutine to be called
    """
    def runTask(self, name : str, func : Callable) -> None:
        self.cancelTask(name)
        self.tasks[name] = self.loop.create_task(func())
        self.logger.push("[MAIN] Task '{}' started".format(name), send_to_discord=False)

    """cancelTask()
    Stop a bot task
    
    Parameters
    ----------
    name: Task identifier
    """
    def cancelTask(self, name : str) -> None:
        if name in self.tasks:
            try:
                self.tasks[name].cancel()
                self.logger.push("[MAIN] Task '{}' cancelled".format(name), send_to_discord=False)
            except:
                pass

    """startTasks()
    Start all tasks from each cogs (if any)
    """
    def startTasks(self) -> None:
        if self.debug_mode or self.test_mode:
            self.runTask('log', self.logger.process)
        else:
            for c in self.cogs:
                try: self.get_cog(c).startTasks()
                except: pass

    """on_guild_join()
    Event. Called when the bot join a guild
    
    Parameters
    ----------
    guild: Discord Guild
    """
    async def on_guild_join(self, guild : disnake.Guild) -> None:
        try:
             await self.send('debug', embed=self.embed(title=guild.name + " added me", description="**ID** ▫️ `{}`\n**Owner** ▫️ `{}`\n**Text Channels** ▫️ {}\n**Voice Channels** ▫️ {}\n**Members** ▫️ {}\n**Roles** ▫️ {}\n**Emojis** ▫️ {}\n**Boosted** ▫️ {}\n**Boost Tier** ▫️ {}".format(guild.id, guild.owner_id, len(guild.text_channels), len(guild.voice_channels), guild.member_count, len(guild.roles), len(guild.emojis), guild.premium_subscription_count, guild.premium_tier), thumbnail=guild.icon, timestamp=guild.created_at))
        except Exception as e:
            self.logger.pushError("[EVENT] on_guild_join Error:", e)

    """global_check()
    Check if the command is authorized to run. Called whenever a command is used.
    
    Parameters
    ----------
    inter: Command context or interaction
    
    Returns
    --------
    bool: True if the command can be processed, False if not
    """
    async def global_check(self, inter : disnake.ApplicationCommandInteraction) -> bool:
        if not self.running: return False # do nothing if the bot is stopped
        if inter.guild is None or isinstance(inter.channel, disnake.PartialMessageable): # if none or channel is PartialMessageable, the command has been sent via a direct message
            return False # so we ignore
        try:
            gid = str(inter.guild.id)
            if self.ban.check(inter.author.id, self.ban.USE_BOT):
                return False
            elif gid in self.data.save['banned_guilds'] or self.ban.check(inter.guild.owner_id, self.ban.OWNER): # ban check
                await inter.guild.leave() # leave the server if banned
                return False
            elif not inter.channel.permissions_for(inter.me).send_messages:
                return False
            return True
        except Exception as e:
            self.logger.pushError("[MAIN] global_check Error:", e)
            return False

    """application_error_handling()
    Common function for on_error events.
    
    Parameters
    ----------
    inter: Command interaction
    error: Exception
    """
    async def application_error_handling(self, inter : disnake.ApplicationCommandInteraction, error : Exception) -> None:
        try:
            msg = str(error)
            if not inter.response.is_done():
                try: await inter.response.defer(ephemeral=True)
                except: pass
            if msg[:20] == 'You are on cooldown.':
                embed = self.embed(title="Command Cooldown Error", description="{} ".format(self.emote.get('time')) + msg.replace('You are on cooldown.', 'This command is on cooldown.'), timestamp=self.util.UTC())
            elif msg[:39] == 'Too many people are using this command.':
                embed=self.embed(title="Command Concurrency Error", description='{} Too many people are using this command, try again later'.format(self.emote.get('time')), timestamp=self.util.UTC())
            elif 'check functions for command' in msg or 'NotFound: 404 Not Found (error code: 10062): Unknown interaction' in msg or 'NotFound: 404 Not Found' in msg:
                return
            elif 'required argument that is missing' in msg or 'Converting to "int" failed for parameter' in msg:
                embed=self.embed(title="Command Argument Error", description="A required parameter is missing.", timestamp=self.util.UTC())
            elif msg[:8] == 'Member "' or msg[:9] == 'Command "' or 'Command raised an exception: Forbidden: 403' in msg:
                embed=self.embed(title="Command Permission Error", description="It seems you can't use this command here", timestamp=self.util.UTC())
            elif '503 Service Unavailable' in msg:
                embed=self.embed(title="HTTP Discord Error", description="Discord might be having troubles.\nIf the issue persists, wait patiently.", timestamp=self.util.UTC())
            elif '401 Unauthorized' in msg:
                embed=self.embed(title="HTTP Discord Error", description="The Bot might be unresponsive or laggy.\nWait a bit and try again.", timestamp=self.util.UTC())
            else:
                msg = self.pexc(error).replace('*', '\*').split('The above exception was the direct cause of the following exception', 1)[0]
                if len(msg) > 4000:
                    msg = msg[:4000] + "...\n*Too long, check rosetta.log for details*"
                await self.send('debug', embed=self.embed(title="⚠ Error caused by {}".format(inter.author), description=msg, thumbnail=inter.author.display_avatar, fields=[{"name":"Options", "value":'`{}`'.format(inter.options)}, {"name":"Server", "value":inter.author.guild.name}], footer='{}'.format(inter.author.id), timestamp=self.util.UTC()))
                embed=self.embed(title="Command Error", description="An unexpected error occured. My owner has been notified.\nUse {} if you have additional informations to provide".format(self.util.command2mention('bug_report')), timestamp=self.util.UTC())
            try:
                if inter.response.is_done(): # try to send using the existing interaction
                    await inter.edit_original_message(embed=embed)
                else:
                    await inter.response.send_message(embed=embed, ephemeral=True)
            except:
                try:
                    await inter.channel.send(inter.author.mention, embed=embed) # send in the channel
                except:
                    try:
                        embed.set_footer(text="You received this in your DM because I failed to post in the channel (because of lags or permissions)", icon_url=None)
                        await inter.author.send(embed=embed) # send in dm (last try)
                    except:
                        pass
        except Exception as e:
            self.logger.pushError("[ERROR] application_error_handling Error:", e)

    """on_slash_command_error()
    Event. Called when a slash command raise an uncaught error
    
    Parameters
    ----------
    inter: Command interaction
    error: Exception
    """
    async def on_slash_command_error(self, inter : disnake.ApplicationCommandInteraction, error : Exception) -> None:
        await self.application_error_handling(inter, error)

    """on_user_command_error()
    Event. Called when an user command raise an uncaught error
    
    Parameters
    ----------
    inter: Command interaction
    error: Exception
    """
    async def on_user_command_error(self, inter : disnake.ApplicationCommandInteraction, error : Exception) -> None:
        await self.application_error_handling(inter, error)

    """on_message_command_error()
    Event. Called when a message command raise an uncaught error
    
    Parameters
    ----------
    inter: Command interaction
    error: Exception
    """
    async def on_message_command_error(self, inter : disnake.ApplicationCommandInteraction, error : Exception) -> None:
        await self.application_error_handling(inter, error)

    """on_raw_reaction_add()
    Event. Called when a new reaction is added by an user, for the pinboard system
    
    Parameters
    ----------
    payload: Raw payload
    """
    async def on_raw_reaction_add(self, payload : disnake.RawReactionActionEvent) -> None:
        await self.pinboard.pin(payload)

    """on_message()
    Event. Called when a new message is posted.
    Replace twitter links with vxtwitter links.
    
    Parameters
    ----------
    message: a Disnake message
    """
    async def on_message(self, message : disnake.Message) -> None:
        try:
            if message.guild.me.id != message.author.id and self.data.save['vxtwitter'].get(str(message.guild.id), False) and ('https://twitter.com/' in message.content or 'https://x.com/' in message.content): # if not posted by Rosetta and guild setting enabled and got twitter link
                if len(message.embeds) == 0:
                    await asyncio.sleep(3) # wait
                    message = await message.channel.fetch_message(message.id)
                for embed in message.embeds: # don't do anything if twitter embed exists
                    d = embed.to_dict()
                    if d.get('footer', {}).get('text', '') == 'Twitter' and 'twitter.com' in d.get('url', '') and 'video' not in d.get('image', {}).get('url', ''):
                        return
                b = 0
                already_posted = set()
                while True:
                    # search url starting from character #b
                    a = message.content.find('https://twitter.com/', b)
                    if a == -1: a = message.content.find('https://x.com/', b)
                    if a == -1: return # not found, stop
                    # search a stopping point
                    b = message.content.find(' ', a+10)
                    if b == -1: link = message.content[a:]
                    else: link = message.content[a:b]
                    # modify link
                    link = link.split('?', 1)[0].replace('https://twitter.com/', 'https://vxtwitter.com/').replace('https://x.com/', 'https://vxtwitter.com/')
                    if '/status/' in link and link not in already_posted: # if not found previously in the same message
                        await message.reply(link) # reply with
                        already_posted.add(link)
                    if b == -1: return
        except:
            pass

if __name__ == "__main__":
    if '-remove' in sys.argv:
        bot = DiscordBot(debug_mode=True)
        bot.start_bot(no_cogs=True)
    elif '-test' in sys.argv:
        bot = DiscordBot(test_mode=True, debug_mode=('-debug' in sys.argv))
        bot.test_bot()
    elif '-run' in sys.argv:
        bot = DiscordBot(debug_mode=('-debug' in sys.argv))
        bot.start_bot()
    elif '-emoji' in sys.argv:
        bot = DiscordBot()
        bot.init_emoji()
    else:
        print("Usage: python bot.py [options]")
        print("")
        print("# Start Parameters (mutually exclusive, in order of priority):")
        print("-remove: Used to desync Guild slash commands (use to remove a test bot commands).")
        print("-test: Run the bot in test mode (to check if the cogs are loading).")
        print("-run: Run the bot.")
        print("-emoji: Init the emoji in config.json and the corresponding debug server.")
        print("")
        print("# Others Parameters:")
        print("-debug: Put the bot in debug mode (config_test.json will be used, test.py Cog will be loaded, some operations such as saving will be impossible).")