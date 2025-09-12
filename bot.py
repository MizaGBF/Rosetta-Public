from __future__ import annotations
from components.data import Data
from components.drive import Drive
from components.util import Util
from components.singleton import Singleton
from components.network import Network
from components.pinboard import Pinboard
from components.emote import Emote
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
from typing import Callable, Any
import asyncio
import time
import signal
import os
import traceback


# Main Bot Class (overload commands.Bot)
class DiscordBot(commands.InteractionBot):
    VERSION : str = "12.5.0" # bot version
    CHANGELOG : list[str] = [ # changelog lines
        (
            "Please use `/bug_report`, open an [issue]"
            "(https://github.com/MizaGBF/Rosetta-Public) or check the"
            "[help](https://mizagbf.github.io/discordbot.html) if you have a problem."
        ),
        "**v12.0.0** - Reworked: `/gbf wiki`, `/mod cleanup`, `/mod announcement`, `/mod pinboard`.",
        "**v12.0.5** - Removed `/gbf check brand`.",
        "**v12.0.6** - Added support for 4% banners in the Gacha Simulator.",
        "**v12.0.7** - Added event links to `/gbf schedule`.",
        "**v12.0.10** - Added `/gw rosetta`.",
        "**v12.1.2** - Improved `/gbf maintenance`.",
        "**v12.2.1** - Updated `/db` commands with new schedule.",
        "**v12.3.1** - Command `/gbf leechlist` moved to `/gbfg leechlist`.",
    ]

    __slots__ = (
        "running", "debug_mode", "test_mode", "booted", "tasks", "reaction_hooks", "cogn",
        # components
        "ban", "channel", "data", "drive", "emote", "file", "gacha", "logger", "network",
        "pinboard", "ranking", "singleton", "sql", "util"
    )

    def __init__(self : DiscordBot, test_mode : bool = False, debug_mode : bool = False) -> None:
        self.running : bool = True # is False when the bot is shutting down
        self.debug_mode : bool = debug_mode # indicate if we are running the debug version of the bot
        self.test_mode : bool = test_mode # indicate if we are running the test version of the bot
        self.booted : bool = False # goes up to True after the first on_ready event
        self.tasks : dict[str, asyncio.Task] = {} # contain our user tasks
        self.reaction_hooks : dict[str, Callable] = {} # for on_raw_reaction_add, see related function
        self.cogn : int = 0 # number of cog loaded

        # components
        try:
            self.singleton  : Singleton = Singleton(self)
            self.util : Util = Util(self)
            self.logger : Logger = Logger(self)
            self.logger.push("[BOOT] Logger started up. Loading components...", send_to_discord=False)
            if self.debug_mode:
                self.logger.push("[INFO] The bot is running in DEBUG mode.", send_to_discord=False)
            self.data : Data = Data(self)
            try:
                self.drive : Drive = Drive(self)
            except OSError:
                self.logger.push(
                    "[BOOT] Please setup your Google account 'service-secrets.json' to use the bot.",
                    send_to_discord=False,
                    level=self.logger.CRITICAL
                )
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(4)
            except Exception:
                self.logger.push(
                    "[BOOT] Failed to initialize the Drive component",
                    send_to_discord=False,
                    level=self.logger.CRITICAL
                )
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(5)
            self.net : Network = Network(self)
            self.pinboard : Pinboard = Pinboard(self)
            self.emote : Emote = Emote(self)
            self.channel : Channel = Channel(self)
            self.file : File = File(self)
            self.sql : SQL = SQL(self)
            self.ranking : Ranking = Ranking(self)
            self.ban : Ban = Ban(self)
            self.gacha : Gacha = Gacha(self)
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
            self.logger.push(
                "[BOOT] Failed to load the config file. Please check if it exists or if its content is correct.",
                send_to_discord=False,
                level=self.logger.CRITICAL
            )
            self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
            time.sleep(500)
            os._exit(1)
        if not test_mode:
            self.logger.push("[BOOT] Downloading the save file...", send_to_discord=False)
            i : int
            for i in range(0, 50): # try multiple times in case google drive is unresponsive
                if self.drive.load() is True:
                    break # attempt to download the save file
                elif i == 49:
                    self.logger.push(
                        "[BOOT] Couldn't access Google Drive and load the save file",
                        send_to_discord=False,
                        level=self.logger.CRITICAL
                    )
                    self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                    time.sleep(500)
                    os._exit(3)
                time.sleep(20) # wait 20 sec
            self.logger.push("[BOOT] Reading the save file...", send_to_discord=False)
            if not self.data.loadData():
                self.logger.push(
                    "[BOOT] Couldn't load save.json, it's either invalid or corrupted",
                    send_to_discord=False,
                    level=self.logger.CRITICAL
                )
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False)
                time.sleep(500)
                os._exit(2) # load the save file
        else:
            self.data.save = self.data.checkData(self.data.save) # dummy data

        # initialize remaining components
        try:
            self.logger.push("[BOOT] Initializing remaining components...", send_to_discord=False)
            self.singleton.init()
            self.util.init()
            self.net.init()
            self.pinboard.init()
            self.emote.init()
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
            intents : disnake.Intents = disnake.Intents.default()
            intents.message_content = True
            # intents.messages = True # uncomment this line to enable message intents

            # constructor
            self.logger.push(
                "[BOOT] Initializing disnake.InteractionBot with Intent flags: 0b{:b}".format(intents.value),
                send_to_discord=False
            )
            super().__init__(
                max_messages=None,
                intents=intents,
                command_sync_flags=commands.CommandSyncFlags.default()
            )
            self.add_app_command_check(
                self.global_check,
                slash_commands=True,
                user_commands=True,
                message_commands=True
            )
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
    Test function, to verify the cogs are loading properly.
    Called when using -test.
    """
    def test_bot(self : DiscordBot) -> None:
        failed : int
        self.cogn, failed = cogs.load(self)
        if failed > 0:
            self.logger.pushError("{} / {} cog(s) failed to load".format(failed, self.cogn), send_to_discord=False)
        else:
            self.logger.push("OK", send_to_discord=False)

    """start_bot()
    Main Bot Loop.
    Called when using -remove or -run.

    Parameters
    --------
    no_cogs: Boolean, set to True to not load the cogs. Used by -remove.
    """
    def start_bot(self : DiscordBot, no_cogs : bool = False) -> None:
        if no_cogs:
            self.cogn = 0
            failed : int = 0
        else:
            self.logger.push("[MAIN] Loading cogs...", send_to_discord=False)
            self.cogn, failed = cogs.load(self) # load cogs
        if failed > 0: # return if a cog failed to load
            self.logger.push(
                "[MAIN] {} / {} cog(s) failed to load".format(failed, self.cogn),
                send_to_discord=False,
                level=self.logger.CRITICAL
            )
            time.sleep(36000)
            return
        else:
            self.logger.push("[MAIN] All cogs loaded", send_to_discord=False)
        # graceful exit setup
        graceful_exit = self.loop.create_task(self.exit_gracefully()) # make a task
        s : signal.SIGNALS
        for s in (signal.SIGTERM, signal.SIGINT):
            try: # unix
                self.loop.add_signal_handler(s, graceful_exit.cancel) # call cancel when the signals are called
            except: # windows
                # windows doesn't support add_signal_handler on python 3.11
                signal.signal(s, self._exit_gracefully_internal)
        self.logger.push("[MAIN] v{} starting up...".format(self.VERSION), send_to_discord=False)
        # main loop
        while self.running:
            try:
                self.loop.run_until_complete(self.run_bot()) # run the bot
            except KeyboardInterrupt: # such as Ctrl+C
                self.logger.push("[MAIN] Keyboard Interrupt, shutting down...", send_to_discord=False)
                self.running = False
            except Exception as e: # handle exceptions here to avoid the bot dying
                if str(e).startswith("429 Too Many Requests"): # ignore the rate limit error
                    time.sleep(100) # just wait for a bit to settle  down
                else:
                    self.logger.pushError("[MAIN] A critical error occured:", e)
                if self.data.pending: # save if anything weird happened (if needed)
                    self.data.saveData()
        # exit
        if self.data.pending:
            self.data.saveData()

    """run_bot()
    Followup from start_bot().
    Initialize the aiohttp clients and the unicode emoji list.
    """
    async def run_bot(self : DiscordBot) -> None:
        async with self.net.init_clients():
            await self.emote.init_request()
            await self.start(self.data.config['tokens']['discord'])

    """exit_gracefully()
    Coroutine triggered when SIGTERM or SIGINT is received, to close the bot
    """
    async def exit_gracefully(self : DiscordBot) -> None:
        try:
            while self.running: # we wait until we receive the signal
                await asyncio.sleep(10000)
        except asyncio.CancelledError:
            await self.close()
            self._exit_gracefully_internal() # call exit process

    """_exit_gracefully_internal()
    Routine to exit gracefully. Called by exit_gracefully() if using
    loop.add_signal_handler(), else directly by signal.signal().
    Note: Calling exit_gracefully.cancel() in this function makes
    Python 3.11 crash on Windows, hence the roundabout way.

    Parameters
    ----------
    signum: Integer (Optional), the signal number
    frame: Frame (Optional), the stack
    """
    def _exit_gracefully_internal(self : DiscordBot, signum : Any = None, frame : Any = None) -> None:
        self.running = False
        if self.data.pending and not self.debug_mode: # save if needed and not in debug mode
            self.data.autosaving = False
            count : int = 0
            while count < 3: # attempt 3 times in case of failures
                if self.data.saveData():
                    self.logger.push(
                        "[EXIT] Auto-saving successful",
                        send_to_discord=False
                    )
                    break
                else:
                    self.logger.pushError(
                        "[EXIT] Auto-saving failed (try {}/3)".format(count + 1),
                        send_to_discord=False
                    )
                    time.sleep(2)
                count += 1
        self.logger.push("[EXIT] Exited gracefully", send_to_discord=False)
        os._exit(0)

    """isProduction()
    Return True if the bot is NOT in debug and test modes

    Returns
    --------
    bool: True if valid, False if debug or test mode
    """
    def isProduction(self : DiscordBot) -> bool:
        return not self.debug_mode and not self.test_mode

    """isServer()
    Check if the interaction is matching the given config.json ID identifier
    (server identifier must be set in config.json beforehand)

    Parameters
    ----------
    inter: Command interaction
    id_string: Server identifier in config.json

    Returns
    --------
    bool: True if matched, False if not
    """
    def isServer(self : DiscordBot, inter : disnake.ApplicationCommandInteraction, id_string : str) -> bool:
        return inter.guild.id == self.data.config['ids'].get(id_string, -1)

    """isChannel()
    Check if the interaction is matching the given config.json ID identifier
    (channel identifier must be set in config.json beforehand)

    Parameters
    ----------
    inter: Command interaction
    id_string: Channel identifier in config.json

    Returns
    --------
    bool: True if matched, False if not
    """
    def isChannel(self : DiscordBot, inter : disnake.ApplicationCommandInteraction, id_string : str) -> bool:
        return inter.channel.id == self.data.config['ids'].get(id_string, -1)

    """isMod()
    Check if the interaction author has the manage message permission

    Parameters
    ----------
    inter: Command interaction

    Returns
    --------
    bool: True if it does, False if not
    """
    def isMod(self : DiscordBot, inter : disnake.ApplicationCommandInteraction) -> bool:
        return (
            inter.guild is not None
            and (
                inter.author.guild_permissions.manage_messages
                or inter.author.id == self.owner.id
            )
        )

    """isOwner()
    Check if the interaction author is the bot owner

    Parameters
    ----------
    inter: Command interaction

    Returns
    --------
    bool: True if it does, False if not
    """
    def isOwner(self : DiscordBot, inter : disnake.ApplicationCommandInteraction) -> bool:
        return inter.author.id == self.owner.id

    """send()
    Send a message to a registered channel.
    The channel must be registered with the Channel component,
        using set, setID or setMultiple.
    See on_ready() for some channels registered by default.

    Parameters
    ----------
    channel_name: Channel name identifier
    msg: Text message
    embed: Discord Embed
    file: Discord File
    components : A list of Modal v2 components
    publish: Boolean. Try to publish the message if set to True.
        Auto publish must be enabled on the channel

    Returns
    --------
    disnake.Message: The sent message or None if error
    """
    async def send(
        self : DiscordBot,
        channel_name : str,
        *,
        msg : str = None,
        embed : disnake.Embed = None,
        file : disnake.File = None,
        view : disnake.ui.View = None,
        components : list[disnake.ui.UIComponent]|None = None,
        publish : bool = False
    ) -> disnake.Message|None:
        try:
            c : disnake.Channel = self.channel.get(channel_name) # retrieve channel from component
            # send to channel and retrieve resulting message
            message : disnake.Message|None = await c.send(msg, embed=embed, file=file, view=view, components=components)
            try:
                if publish is True and c.is_news() and self.channel.can_publish(c.id):
                    # publish if enabled and possible
                    await message.publish()
            except:
                pass
            return message # return message for future use
        except Exception as e:
            # error handling
            if embed is not None:
                msg = (
                    "[SEND] Failed to send a message to '{}'\n"
                    "**Embed Title Start**: `{}`\n"
                    "**Embed Description Start**: `{}`"
                ).format(
                    channel_name,
                    str(embed.title)[:100],
                    str(embed.description)[:100]
                )
            else:
                msg = "[SEND] Failed to send a message to '{}':".format(channel_name)
            self.logger.pushError(msg, e)
            # logger component has a mechanic in place so there is
            # no infinite loop of error being triggered by attempting
            # to send error messages with this function
            return None

    """sendMulti()
    Send a message to multiple registered channels.
    It's send() in a loop, to sum it up.

    Parameters
    ----------
    channel_names: List of Channel name identifiers
    msg: Text message
    embed: Discord Embed
    file: Discord File
    components : A list of Modal v2 components
    publish: Boolean. Try to publish the message if set to True

    Returns
    --------
    list: A list of the successfully sent messages
    """
    async def sendMulti(
        self : DiscordBot,
        channel_names : list[str],
        *,
        msg : str = None,
        embed : disnake.Embed = None,
        file : disnake.File = None,
        components : list[disnake.ui.UIComponent]|None = None,
        publish : bool = False
    ) -> list:
        r : list[disnake.Message] = [] # resulting message
        err : list[str] = [] # errors
        ex : Exception = None # latest exception
        c : str
        for c in channel_names:
            try:
                r.append(await self.send(c, msg=msg, embed=embed, file=file, components=components, publish=publish))
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
    async def changeAvatar(self : DiscordBot, filename : str) -> bool:
        try:
            with open("assets/avatars/" + filename, mode="rb") as f: # read file
                await self.user.edit(avatar=f.read()) # and upload bot user
            return True
        except Exception as e:
            self.logger.pushError("[MAIN] 'changeAvatar' failed", e)
            return False

    """on_ready()
    Event. Called on connection
    """
    async def on_ready(self : DiscordBot) -> None:
        if not self.booted:
            # this flag is used to not show this function content again
            # in case of an untimely disconnection
            self.booted = True
            # Register our used channels for the send function
            self.channel.setMultiple([['debug', 'debug_channel'], ['image', 'image_upload']])
            # Send Ready message
            await self.send(
                'debug',
                embed=self.embed(
                    title="{} is Ready".format(self.user.display_name),
                    description=self.util.statusString(),
                    thumbnail=self.user.display_avatar,
                    timestamp=self.util.UTC()
                )
            )
            self.logger.push("[MAIN] Rosetta is ready", send_to_discord=False)
            # Start the tasks
            self.startTasks()
            # Wait a second to be sure they are registered
            await asyncio.sleep(1)
            msgs : list[str] = []
            task : str
            for task in self.tasks:
                msgs.append("- {}\n".format(task))
            # Send task list to discord
            if len(msgs) > 0:
                self.logger.push("[MAIN] {} Tasks started\n{}".format(len(self.tasks), "".join(msgs)))
            # Update app emojis
            await self.emote.load_app_emojis()

    """embed()
    Create a disnake.Embed object

    Parameters
    ----------
    **options: disnake.Embed options
        supported: title, description, url, color, fields
            (and name, value and inline for each field),
            inline, thumbnail, footer, image, timestamp,
            author (dict containing name, url and icon_url)

    Returns
    --------
    disnake.Embed: The created embed
    """
    def embed(self : DiscordBot, **options : dict[str, Any]) -> disnake.Embed:
        embed : disnake.Embed = disnake.Embed(
            title=options.get('title', ""),
            description=options.pop('description', ""),
            url=options.pop('url', ""),
            color=options.pop('color', 16777215)
        )
        fields : list[dict[str, str]] = options.pop('fields', [])
        inline : bool = options.pop('inline', False)
        field : dict[str, str]
        for field in fields:
            embed.add_field(
                name=field.get('name'),
                value=field.get('value'),
                inline=field.pop('inline', inline)
            )
        if options.get('thumbnail', None) not in (None, ''):
            embed.set_thumbnail(url=options['thumbnail'])
        if options.get('footer', None) is not None:
            embed.set_footer(
                text=options['footer'],
                icon_url=options.get('footer_url', None)
            )
        if options.get('image', None) not in (None, ''):
            embed.set_image(url=options['image'])
        if options.get('timestamp', None) is not None:
            embed.timestamp = options['timestamp']
        if 'author' in options and 'name' in options['author']:
            embed.set_author(
                name=options['author'].pop('name', ""),
                url=options['author'].pop('url', None),
                icon_url=options['author'].pop('icon_url', None)
            )
        return embed

    """render()
    Create a disnake.ui.Container and return it in a list,
    to be used with the send components parameter

    Parameters
    ----------
    body: List of components to add in the container
    title: String, add the text in a disnake.ui.Section
    thumbnail: String, add a thumbnail in a disnake.ui.Section
    url: String, make the disnake.ui.Section title clickable
    description: String, add a disnake.ui.TextDisplay
    footer: Boolean, add a footer similar to embeds
    color: Integer, set the container accent color

    Returns
    --------
    container: List containing the container
    """
    def render(
        self : DiscordBot,
        *,
        body : list[disnake.ui.UIComponent] = [],
        title : str|None = None,
        thumbnail : str|None = None,
        url : str|None = None,
        description : str|None = None,
        footer : bool = True,
        color : int = 16777215
    ) -> list[disnake.ui.Container]:
        components : list[disnake.ui.UIComponent] = []
        if title is not None or thumbnail is not None or url is not None:
            if title is not None:
                if url is not None:
                    title = "## [{}]({})".format(title, url)
                else:
                    title = "## " + title
            else:
                if url is not None:
                    title = "## [Link]({})".format(url)
                else:
                    title = ""
            accessory = disnake.ui.Thumbnail(thumbnail) if thumbnail is not None else None
            components.append(disnake.ui.Section(title, accessory=accessory))
            components.append(disnake.ui.Separator())
        if description is not None:
            components.append(disnake.ui.TextDisplay(description))
        components.extend(body)
        if footer:
            components.append(disnake.ui.Separator(divider=False))
            components.append(disnake.ui.TextDisplay(self.util.timestamp()))
        return [disnake.ui.Container(*components, accent_colour=disnake.Colour(color))]

    """pexc()
    Convert an exception to a string with the full traceback.
    Used for debugging exceptions.

    Parameters
    ----------
    exception: The error

    Returns
    --------
    unknown: The string, else the exception parameter if an error occured
    """
    def pexc(self : DiscordBot, exception : Exception) -> str|Exception: # format an exception
        try:
            return "".join(traceback.format_exception(type(exception), exception, exception.__traceback__))
        except:
            return exception

    """runTask()
    Start a new bot task (cancel any previous one with the same name)

    Parameters
    ----------
    name: Task identifier
    coro: The coroutine to be called
    """
    def runTask(self : DiscordBot, name : str, func : Callable) -> None:
        self.cancelTask(name)
        self.tasks[name] = self.loop.create_task(func())
        self.logger.push("[MAIN] Task '{}' started".format(name), send_to_discord=False)

    """cancelTask()
    Stop a bot task, if it exists for the given name.

    Parameters
    ----------
    name: Task identifier
    """
    def cancelTask(self : DiscordBot, name : str) -> None:
        if name in self.tasks:
            try:
                self.tasks[name].cancel()
                self.tasks.pop(name, None)
                self.logger.push("[MAIN] Task '{}' cancelled".format(name), send_to_discord=False)
            except:
                pass

    """startTasks()
    Start all tasks from each cogs (if any), along with the logger
    Note: In test mode, only the log is started
    """
    def startTasks(self : DiscordBot) -> None:
        # start component tasks
        components : list[Any] = [
            self.ban, self.channel, self.data, self.drive,
            self.emote, self.file, self.gacha, self.logger,
            self.net, self.pinboard, self.ranking, self.singleton,
            self.sql, self.util
        ]
        cmp : Any
        for cmp in components:
            try:
                cmp.startTasks()
            except:
                pass
        # start cog tasks
        c : commands.Cog
        for c in self.cogs:
            try:
                self.get_cog(c).startTasks()
            except:
                pass

    """on_guild_join()
    Event.
    Notify the owner in the debug channel when the bot join a guild.

    Parameters
    ----------
    guild: Discord Guild
    """
    async def on_guild_join(self : DiscordBot, guild : disnake.Guild) -> None:
        try:
            await self.send(
                'debug',
                embed=self.embed(
                    title=guild.name + " added me",
                    description=(
                        "**ID** ▫️ `{}`\n"
                        "**Owner** ▫️ `{}`\n"
                        "**Text Channels** ▫️ {}\n"
                        "**Voice Channels** ▫️ {}\n"
                        "**Members** ▫️ {}\n"
                        "**Roles** ▫️ {}\n"
                        "**Emojis** ▫️ {}\n"
                        "**Boosted** ▫️ {}\n"
                        "**Boost Tier** ▫️ {}"
                    ).format(
                        guild.id,
                        guild.owner_id,
                        len(guild.text_channels),
                        len(guild.voice_channels),
                        guild.member_count,
                        len(guild.roles),
                        len(guild.emojis),
                        guild.premium_subscription_count,
                        guild.premium_tier
                    ),
                    thumbnail=guild.icon,
                    timestamp=guild.created_at
                )
            )
        except Exception as e:
            self.logger.pushError("[EVENT] on_guild_join Error:", e)

    """global_check()
    Called whenever a command is used.
    Check if the command is authorized to run.

    Parameters
    ----------
    inter: Command interaction

    Returns
    --------
    bool: True if the command can be processed, False if not
    """
    async def global_check(
        self : DiscordBot,
        inter : disnake.ApplicationCommandInteraction|disnake.GuildCommandInteraction
    ) -> bool:
        try:
            if not self.running:
                return False # do nothing if the bot is stopped/stopping
            if self.ban.check(str(inter.author.id), self.ban.USE_BOT):
                # check if user is banned
                return False
            if inter.guild is not None:
                # i.e. the bot is present in the guild
                gid : str = str(inter.guild.id)
                if self.ban.check(str(inter.author.id), self.ban.USE_BOT):
                    # check if the author is banned
                    return False
                elif (gid in self.data.save['banned_guilds']
                        or self.ban.check(str(inter.guild.owner_id), self.ban.OWNER)):
                    # check if the guild or guild owner is banned
                    await inter.guild.leave() # leave the server if it is
                    return False
                elif not inter.channel.permissions_for(inter.me).send_messages:
                    # check if the bot has the permission to send messages
                    return False
            return True
        except Exception as e:
            self.logger.pushError("[MAIN] global_check Error:", e)
            return False

    """application_error_handling()
    Common function for the various on_error events.

    Parameters
    ----------
    inter: Command interaction
    error: Exception
    """
    async def application_error_handling(
        self : DiscordBot,
        inter : disnake.ApplicationCommandInteraction|disnake.GuildCommandInteraction,
        error : Exception
    ) -> None:
        try:
            msg : str = str(error)
            embed : disnake.Embed
            if not inter.response.is_done(): # defer if not deferred
                try:
                    await inter.response.defer(ephemeral=True)
                except:
                    pass
            if msg[:20] == 'You are on cooldown.':
                # command is on cooldown
                embed = self.embed(
                    title="Command Cooldown Error",
                    description="{} ".format(self.emote.get('time')) + msg.replace(
                        'You are on cooldown.', 'This command is on cooldown.'
                    ),
                    timestamp=self.util.UTC()
                )
            elif msg[:39] == 'Too many people are using this command.':
                # command is overused
                embed = self.embed(
                    title="Command Concurrency Error",
                    description=(
                        '{} Too many people are using this command,'
                        'try again later'
                    ).format(self.emote.get('time')),
                    timestamp=self.util.UTC()
                )
            elif ('check functions for command' in msg
                    or 'NotFound: 404 Not Found (error code: 10062): Unknown interaction' in msg
                    or 'NotFound: 404 Not Found' in msg):
                # various errors caused by bad permissions or lag
                return # we just ignore those
            elif ('required argument that is missing' in msg
                    or 'Converting to "int" failed for parameter' in msg):
                embed = self.embed(
                    title="Command Argument Error",
                    description="A required parameter is missing.",
                    timestamp=self.util.UTC()
                )
            elif (msg[:8] == 'Member "'
                    or msg[:9] == 'Command "'
                    or 'Command raised an exception: Forbidden: 403' in msg):
                embed = self.embed(
                    title="Command Permission Error",
                    description="It seems you can't use this command here",
                    timestamp=self.util.UTC()
                )
            elif '503 Service Unavailable' in msg:
                embed = self.embed(
                    title="HTTP Discord Error",
                    description="Discord might be having troubles.\nIf the issue persists, wait patiently.",
                    timestamp=self.util.UTC()
                )
            elif '401 Unauthorized' in msg:
                embed = self.embed(
                    title="HTTP Discord Error",
                    description="The Bot might be unresponsive or laggy.\nWait a bit and try again.",
                    timestamp=self.util.UTC()
                )
            else:
                msg = self.pexc(error).replace(
                    '*', '\\*'
                ).split(
                    'The above exception was the direct cause of the following exception', 1
                )[0]
                if len(msg) > 4000:
                    msg = msg[:4000] + "...\n*Too long, check rosetta.log for details*"
                await self.send(
                    'debug',
                    embed=self.embed(
                        title="⚠ Error caused by {}".format(inter.author),
                        description=msg,
                        thumbnail=inter.author.display_avatar,
                        fields=[
                            {"name":"Options", "value":'`{}`'.format(inter.options)},
                            {"name":"Server", "value":inter.guild.name if inter.guild is not None else "Direct Message"}
                        ],
                        footer='{}'.format(inter.author.id),
                        timestamp=self.util.UTC()
                    )
                )
                embed = self.embed(
                    title="Command Error",
                    description=(
                        "An unexpected error occured. My owner has been notified.\n"
                        "Use {} if you have additional informations to provide"
                    ).format(self.util.command2mention('bug_report')),
                    timestamp=self.util.UTC()
                )
            # attempt to send embed to command author
            try:
                if inter.response.is_done(): # try to send using the existing interaction
                    await inter.edit_original_message(embed=embed)
                else:
                    await inter.response.send_message(embed=embed, ephemeral=True)
            except:
                try:
                    await inter.channel.send(inter.author.mention, embed=embed) # send in the channel instead
                except:
                    # last resort, send in dm
                    try:
                        embed.set_footer(
                            text=(
                                "You received this in your DM because I failed to post"
                                " in the channel (because of lags or permissions)"
                            ),
                            icon_url=None
                        )
                        await inter.author.send(embed=embed)
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
    async def on_slash_command_error(
        self : DiscordBot,
        inter : disnake.ApplicationCommandInteraction|disnake.GuildCommandInteraction,
        error : Exception
    ) -> None:
        await self.application_error_handling(inter, error)

    """on_user_command_error()
    Event. Called when an user command raise an uncaught error

    Parameters
    ----------
    inter: Command interaction
    error: Exception
    """
    async def on_user_command_error(
        self : DiscordBot,
        inter : disnake.ApplicationCommandInteraction|disnake.GuildCommandInteraction,
        error : Exception
    ) -> None:
        await self.application_error_handling(inter, error)

    """on_message_command_error()
    Event. Called when a message command raise an uncaught error

    Parameters
    ----------
    inter: Command interaction
    error: Exception
    """
    async def on_message_command_error(
        self : DiscordBot,
        inter : disnake.ApplicationCommandInteraction|disnake.GuildCommandInteraction,
        error : Exception
    ) -> None:
        await self.application_error_handling(inter, error)

    """on_raw_reaction_add()
    Event. Called when a new reaction is added by an user.
    Go through the registered reaction_hooks and call them.
    If one return True, stop.

    A reaction hook must be a coroutine taking a disnake.RawReactionActionEvent as a parameter and returning a bool.
    See pin() in components/pinboard.py for an example.

    Parameters
    ----------
    payload: Raw payload
    """
    async def on_raw_reaction_add(self : DiscordBot, payload : disnake.RawReactionActionEvent) -> None:
        name : str
        coroutine : Callable
        for name, coroutine in self.reaction_hooks.items():
            if await coroutine(payload):
                return


# entry point / main function
if __name__ == "__main__":
    import sys
    import argparse
    # Get python file name
    prog_name : str
    try:
        prog_name = sys.argv[0].replace('\\', '/').split('/')[-1]
    except:
        prog_name = "bot.py" # fallback to default
    # Set Argument Parser
    parser : argparse.ArgumentParser = argparse.ArgumentParser(
        prog=prog_name,
        description='Rosetta v{}: https://github.com/MizaGBF/Rosetta-Public'.format(DiscordBot.VERSION)
    )
    parser.add_argument(
        '-r', '--run',
        help="run Rosetta.",
        action='store_const', const=True, default=False, metavar=''
    )
    parser.add_argument(
        '-d', '--debug',
        help=(
            "set Rosetta to the Debug mode ('config_test.json' will be loaded, "
            "some operations such as saving will be disabled)."
        ),
        action='store_const', const=True, default=False, metavar=''
    )
    parser.add_argument(
        '-t', '--test',
        help="attempt to boot Rosetta and load the command cogs, in Debug mode.",
        action='store_const', const=True, default=False, metavar=''
    )
    parser.add_argument(
        '-c', '--clean',
        help="desync Guild slash commands (to remove commands from a Debug mode instance, from all server).",
        action='store_const', const=True, default=False, metavar=''
    )
    parser.add_argument(
        '-g', '--generatehelp', nargs='?',
        help="generate the discordbot.html help file (the destination PATH can be set).",
        const=".", metavar='PATH'
    )
    args : argparse.Namespace = parser.parse_args()
    # Check flags/variables
    if args.clean:
        DiscordBot(debug_mode=args.debug).start_bot(no_cogs=True)
    elif args.test:
        DiscordBot(debug_mode=True).test_bot()
    elif args.generatehelp is not None:
        cogs.generateHelp(DiscordBot.VERSION, args.generatehelp)
    elif args.run:
        DiscordBot(debug_mode=args.debug).start_bot()
    else:
        parser.print_help()
