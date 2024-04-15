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
from typing import Optional, Union, Callable
import asyncio
import time
import signal
import sys
import os
import traceback

# Main Bot Class (overload commands.Bot)
class DiscordBot(commands.InteractionBot):
    def __init__(self, test_mode : bool = False, debug_mode : bool = False) -> None:
        self.version = "11.3.1" # bot version
        self.changelog = [ # changelog lines
            "Please use `/bug_report`, open an [issue](https://github.com/MizaGBF/Rosetta-Public) or check the [help](https://mizagbf.github.io/discordbot.html) if you have a problem.",
            "**v11.0.12** - Added `/mod server toggle_vxtwitter`.",
            "**v11.0.14** - Rosetta will now update its avatar depending on the time of the year.",
            "**v11.1.0** - Removed the Twitter component and all associated features. Rest in peace.",
            "**v11.1.1** - Added a daily automatic update for `/gbf schedule`.",
            "**v11.1.2** - Improved `/gbf schedule`.",
            "**v11.1.5** - Improved Dread Barrage commands to take into account variable schedule lengths.",
            "**v11.1.7** - Removed `/gbf utility critical`, it's becoming unmaintainable. `/roll roulette` updated with the Birthday Zone.",
            "**v11.1.9** - `/roll` command group updated with the new classic gachas.",
            "**v11.2.0** - `/gw utility` commands have been reworked. Same thing for `/db token` and `/db box`.",
            "**v11.2.1** - Removed `/poll`, now Discord has it built-in.",
            "**v11.3.0** - Added `/gw player stats`",
            "**v11.3.1** - Changed `/gw player stats` to `/gw stats player` and added `/gw stats crew`. Both commands have been improved.",
        ]
        self.running = True # is False when the bot is shutting down
        self.debug_mode = debug_mode # indicate if we are running the debug version of the bot
        self.test_mode = test_mode # indicate if we are running the test version of the bot
        self.booted = False # goes up to True after the first on_ready event
        self.tasks = {} # contain our user tasks
        self.cogn = 0 # number of cog loaded
        
        # components
        self.util = Util(self)
        self.logger = Logger(self)
        self.data = Data(self)
        try: self.drive = Drive(self)
        except Exception as e:
            if "No such file or directory: 'service-secrets.json'" in str(e):
                self.logger.push("[BOOT] Please setup your Google account 'service-secrets.json' to use the bot.", send_to_discord=False, level=self.logger.CRITICAL)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False, level=self.logger.INFO)
                time.sleep(500)
                os._exit(4)
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
        
        # initialize important components
        self.logger.init()
        self.data.init()
        self.drive.init()
        
        # loading data
        self.logger.push("[BOOT] Loading the config file...", send_to_discord=False)
        if not self.data.loadConfig():
            self.logger.push("[BOOT] Failed to load the config file. Please check if it exists or if its content is correct.", send_to_discord=False, level=self.logger.CRITICAL)
            self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False, level=self.logger.INFO)
            time.sleep(500)
            os._exit(1)
        if not test_mode:
            self.logger.push("[BOOT] Downloading the save file...", send_to_discord=False)
            for i in range(0, 50): # try multiple times in case google drive is unresponsive
                if self.drive.load() is True:
                    break # attempt to download the save file
                elif i == 49:
                    self.logger.push("[BOOT] Couldn't access Google Drive and load the save file", send_to_discord=False, level=self.logger.CRITICAL)
                    self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False, level=self.logger.INFO)
                    time.sleep(500)
                    os._exit(3)
                time.sleep(20) # wait 20 sec
            self.logger.push("[BOOT] Reading the save file...", send_to_discord=False)
            if not self.data.loadData():
                self.logger.push("[BOOT] Couldn't load save.json, it's either invalid or corrupted", send_to_discord=False, level=self.logger.CRITICAL)
                self.logger.push("[BOOT] Exiting in 500 seconds...", send_to_discord=False, level=self.logger.INFO)
                time.sleep(500)
                os._exit(2) # load the save file
        else:
            self.data.save = self.data.checkData(self.data.save) # dummy data
        
        # initialize remaining components
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

        # init base class
        intents = disnake.Intents.default()
        #intents.messages = True
        intents.message_content = True
        super().__init__(max_messages=None, intents=intents, command_sync_flags=commands.CommandSyncFlags.default())
        self.add_app_command_check(self.global_check, slash_commands=True, user_commands=True, message_commands=True)
        self.logger.push("[BOOT] Initialization complete", send_to_discord=False)

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
        try: # unix
            for s in [signal.SIGTERM, signal.SIGINT]:
                self.loop.add_signal_handler(s, graceful_exit.cancel)
        except: # windows
            signal.signal(s, graceful_exit.cancel)
        self.logger.push("[MAIN] v{} starting up...".format(self.version), send_to_discord=False)
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

    """run_bot()
    Followup from start_bot(). Switch to asyncio and initialize the aiohttp client
    """
    async def run_bot(self) -> None:
        async with self.net.init_client():
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
            self.running = False
            if self.data.pending:
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
            await self.close()
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
    def isAuthorized(self, inter : disnake.ApplicationCommandInteraction) -> bool:
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
            with open("assets/" + filename, mode="rb") as f:
                await self.user.edit(avatar=f.read())
            return True
        except Exception as e:
            self.logger.pushError("[MAIN] 'changeAvatar' failed", e)
            return False

    """on_ready()
    Event. Called on connection
    """
    async def on_ready(self) -> None: # called when the bot starts
        if not self.booted:
            # set our used channels for the send function
            self.channel.setMultiple([['debug', 'debug_channel'], ['image', 'image_upload'], ['debug_update', 'debug_update']])
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
            if msg.startswith('You are on cooldown.'):
                embed = self.embed(title="Command Cooldown Error", description=msg.replace('You are on cooldown.', 'This command is on cooldown.'), timestamp=self.util.UTC())
            elif msg.startswith('Too many people are using this command.'):
                embed=self.embed(title="Command Concurrency Error", description='Too many people are using this command, try again later', timestamp=self.util.UTC())
            elif msg.find('check functions for command') != -1 or msg.find('NotFound: 404 Not Found (error code: 10062): Unknown interaction') != -1 or msg.find('NotFound: 404 Not Found (error code: 10008): Unknown Message') != -1:
                return
            elif msg.find('required argument that is missing') != -1 or msg.startswith('Converting to "int" failed for parameter'):
                embed=self.embed(title="Command Argument Error", description="A required parameter is missing.", timestamp=self.util.UTC())
            elif msg.find('Member "') == 0 or msg.find('Command "') == 0 or msg.startswith('Command raised an exception: Forbidden: 403'):
                embed=self.embed(title="Command Permission Error", description="It seems you can't use this command here", timestamp=self.util.UTC())
            else:
                msg = self.pexc(error).replace('*', '\*').split('The above exception was the direct cause of the following exception')[0]
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
                    link = link.split('?')[0].replace('https://twitter.com/', 'https://vxtwitter.com/').replace('https://x.com/', 'https://vxtwitter.com/')
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
    else:
        print("Usage: python bot.py [options]")
        print("")
        print("# Start Parameters (mutually exclusive, in order of priority):")
        print("-remove: Used to desync Guild slash commands (use to remove a test bot commands).")
        print("-test: Run the bot in test mode (to check if the cogs are loading).")
        print("-run: Run the bot")
        print("")
        print("# Others Parameters:")
        print("-debug: Put the bot in debug mode (config_test.json will be used, test.py Cog will be loaded, some operations such as saving will be impossible).")