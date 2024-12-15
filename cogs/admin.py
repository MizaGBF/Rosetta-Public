import disnake
from disnake.ext import commands
import asyncio
from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from cogs import DEBUG_SERVER_ID
from datetime import datetime, timedelta
import random
import os
import json
from io import StringIO
from contextlib import redirect_stdout
import time

# ----------------------------------------------------------------------------------------------------------------
# Admin Cog
# ----------------------------------------------------------------------------------------------------------------
# Tools for the Bot Owner
# ----------------------------------------------------------------------------------------------------------------

class Admin(commands.Cog):
    """Owner only."""
    if DEBUG_SERVER_ID is None: guild_ids = []
    else: guild_ids = [DEBUG_SERVER_ID]
    COLOR = 0x7a1472

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def startTasks(self) -> None:
        self.bot.runTask('owner:status', self.status)
        self.bot.runTask('data:maintenance', self.bot.data.maintenance)

    """status()
    Bot Task managing the autosave and update of the bot status
    """
    async def status(self) -> None: # background task changing the bot status and calling autosave()
        await self.bot.change_presence(status=disnake.Status.online, activity=disnake.activity.Game(name="I rebooted in the last 30 minutes"))
        num = 0
        while True:
            try:
                await asyncio.sleep(1800) # 30 min sleep
                num = (num + 1) % 4
                if num == 0: # status change every two hours and refresh GBF account at the same time
                    await self.bot.change_presence(status=disnake.Status.online, activity=disnake.activity.Game(name=random.choice(self.bot.data.config['games'])))
                    await self.bot.net.refresh_account()
                # autosave every 30 min
                if self.bot.data.pending and self.bot.running:
                    await self.bot.data.autosave()
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'status' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'owner:status' Task Error:", e)


    """_shutdown()
    Shutdown the bot
    """
    def _shutdown(self) -> None:
        self.bot.logger.push("[OWNER] Reboot triggered", send_to_discord=False)
        # force save first
        if self.bot.data.pending:
            self.bot.data.autosaving = False
            count = 0
            while count < 3:
                if self.bot.data.saveData():
                    self.bot.logger.push("[EXIT] Auto-saving successful", send_to_discord=False)
                    break
                else:
                    self.bot.logger.pushError("[EXIT] Auto-saving failed (try {}/3)".format(count+1), send_to_discord=False)
                    time.sleep(2)
        # disable the bot
        self.bot.running = False
        try: self.bot.loop.close()
        except: pass
        # and quit (with code 0. Will cause a reboot when used with Watchtower or similar setups)
        os._exit(0)

    """isOwner()
    Command decorator, to check if the command is used by the bot owner
    
    Returns
    --------
    command check
    """
    def isOwner() -> Callable:
        async def predicate(inter : disnake.ApplicationCommandInteraction) -> None:
            if inter.bot.isOwner(inter):
                return True
            else:
                await inter.response.send_message(embed=inter.bot.embed(title="Error", description="You lack the permission to use this command"), ephemeral=True)
                return False
        return commands.check(predicate)

    """guildList()
    Output the server list of the bot in the debug channel
    """
    async def guildList(self) -> None: # list all guilds the bot is in and send it in the debug channel
        msgs = []
        length = 0
        # iterate over guilds
        for s in self.bot.guilds:
            # add to output message
            msgs.append("**{}** `{}`owned by `{}`\n".format(s.name, s.id, s.owner_id))
            length += len(msgs[-1])
            # send if msg length is too high
            if length > 1800:
                await self.bot.send('debug', embed=self.bot.embed(title=self.bot.user.name, description="".join(msgs), thumbnail=self.bot.user.display_avatar, color=self.COLOR))
                msgs = []
                length = 0
        # send remaining
        if len(msgs) > 0:
            await self.bot.send('debug', embed=self.bot.embed(title=self.bot.user.name, description="".join(msgs), thumbnail=self.bot.user.display_avatar, color=self.COLOR))
        # send banned guild list
        if len(self.bot.data.save['banned_guilds']) > 0:
            msg = "Banned Guilds are `" + "` `".join(str(x) for x in self.bot.data.save['banned_guilds']) + "`\n"
            await self.bot.send('debug', embed=self.bot.embed(title=self.bot.user.name, description=msg, thumbnail=self.bot.user.display_avatar, color=self.COLOR))

    @commands.slash_command(name="owner", guild_ids=guild_ids)
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @isOwner()
    async def _owner(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group (Owner Only)"""
        pass

    @_owner.sub_command_group()
    async def utility(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    """exec_callback()
    CustomModal callback
    """
    async def exec_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        try:
            await inter.response.defer()
            # redirect stdout to get the result in discord
            f = StringIO()
            with redirect_stdout(f):
                exec(inter.text_values['code']) # exec the code
            # send result to discord
            await inter.edit_original_message(embed=self.bot.embed(title="Exec", description="Ran `{}` with success\nOutput:\n```\n{}\n```".format(inter.text_values['code'], f.getvalue()[:3500]), color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Exec Error", description="Ran `{}`\nException\n{}".format(inter.text_values['code'], e), color=self.COLOR))

    @utility.sub_command()
    async def exec(self, inter: disnake.GuildCommandInteraction) -> None:
        """Execute code at run time (Owner Only)"""
        await self.bot.util.send_modal(inter, "exec-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Execute Code", self.exec_callback, [
                disnake.ui.TextInput(
                    label="Code",
                    placeholder="Code",
                    custom_id="code",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=1,
                    max_length=2000,
                    required=True
                )
            ]
        )

    """answer_callback()
    CustomModal callback
    """
    async def answer_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        try:
            await inter.response.defer(ephemeral=True)
            # fetch targeted user to respond to
            target = await self.bot.get_or_fetch_user(int(inter.text_values['user']))
            # send them a dm
            await target.send(embed=self.bot.embed(title="Answer to your Bug Report ▫️ " + inter.text_values['title'], description=inter.text_values['description'], image=inter.text_values['image'], color=self.COLOR))
            await inter.edit_original_message(embed=self.bot.embed(title="Information", description='Answer sent with success', color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description='The following error occured:\n{}'.format(e), color=self.COLOR))

    @utility.sub_command()
    async def answer(self, inter: disnake.GuildCommandInteraction) -> None:
        """Answer a bug report (Owner Only)"""
        await self.bot.util.send_modal(inter, "bug_answer-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Answer a Bug Report", self.answer_callback, [
            disnake.ui.TextInput(
                label="User ID",
                placeholder="Bug Report author ID",
                custom_id="user",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=20,
                required=True
            ),
            disnake.ui.TextInput(
                label="Subject",
                placeholder="Title of your issue",
                custom_id="title",
                style=disnake.TextInputStyle.short,
                min_length=1,
                max_length=140,
                required=True
            ),
            disnake.ui.TextInput(
                label="Description",
                placeholder="Write your issue / feedback.",
                custom_id="description",
                style=disnake.TextInputStyle.paragraph,
                min_length=1,
                max_length=2000,
                required=True
            ),
            disnake.ui.TextInput(
                label="Image",
                placeholder="URL",
                custom_id="image",
                style=disnake.TextInputStyle.short,
                min_length=0,
                max_length=300,
                required=False
            )
        ])

    @utility.sub_command()
    async def leave(self, inter: disnake.GuildCommandInteraction, gid : str = commands.Param()) -> None:
        """Make the bot leave a server (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            toleave = self.bot.get_guild(int(gid)) # retrieve guild
            await toleave.leave() # and leave
            await inter.edit_original_message(embed=self.bot.embed(title="Server left", color=self.COLOR))
            await self.guildList() # print guild list
        except Exception as e:
            self.bot.logger.pushError("[OWNER] In 'owner utility leave' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="An unexpected error occured", color=self.COLOR))

    """approximate_account()
    A (sort of) Divide and Conquer algorithm to approximate the total number of GBF accounts.
    An account existing at the given ID means too low. An account not found means too high.
    It's a recursive function (up to 30).
    
    Parameters
    --------
    step: Integer, increase to the current ID. Process stops under 10.
    current: Integer, current ID
    count: Integer, step count, limited to 30
    
    Returns
    --------
    integer: Best ID found, or None
    """
    async def approximate_account(self, step : int, current : int, count : int = 0) -> int:
        if count >= 30 or step <= 10: # if we passed 30 calls or our last step was under 10
            return current
        # request ID equals to current + step
        data = await self.bot.net.requestGBF("/profile/content/index/{}".format(current+step), expect_JSON=True)
        match data:
            case "Maintenance": # game is down, quit
                return None
            case None: # account doesn't exist
                return await self.approximate_account(step//2, current, count+1) # reduce step by half.
            case _: # account exists
                return await self.approximate_account(int(step*1.4), current+step, count+1) # increases step by 40%. Use current existing account as next reference point.

    @utility.sub_command()
    async def playerbase(self, inter: disnake.GuildCommandInteraction) -> None:
        """Get an approximation of the number of accounts on Granblue Fantasy (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if not await self.bot.net.gbf_available(): # check if the game is up
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))
        else:
            if 'totalplayer' not in self.bot.data.save['gbfdata']: # init data at 38900000 players
                self.bot.data.save['gbfdata'].get('totalplayer', 38900000)
            # call approximate_account and wait the result
            result = await self.approximate_account(100000, self.bot.data.save['gbfdata'].get('totalplayer', 38900000))
            if result is None: # If None, game is down
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))
            else:
                self.bot.data.save['gbfdata']['totalplayer'] = result # update save with the result
                self.bot.data.pending = True
                # send the result
                await inter.edit_original_message(embed=self.bot.embed(title="Granblue Fantasy ▫️ Playerbase", description="Total playerbase estimated around **{:,}** accounts *(±10)*".format((result//10)*10), timestamp=self.bot.util.UTC(), color=self.COLOR))

    @_owner.sub_command_group()
    async def ban(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @ban.sub_command()
    async def server(self, inter: disnake.GuildCommandInteraction, guild_id : str = commands.Param()) -> None:
        """Command to leave and ban a server (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            gid = int(guild_id)
            try: # get and leave server (if it hasn't yet)
                toleave = self.bot.get_guild(gid)
                await toleave.leave()
            except:
                pass
            if guild_id not in self.bot.data.save['banned_guilds']: # add to ban list
                self.bot.data.save['banned_guilds'].append(guild_id)
                self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Banned server", color=self.COLOR))
            await self.guildList()
        except Exception as e:
            self.bot.logger.pushError("[OWNER] In 'owner ban server' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="An unexpected error occured", color=self.COLOR))

    @ban.sub_command()
    async def owner(self, inter: disnake.GuildCommandInteraction, guild_id : str = commands.Param()) -> None:
        """Command to ban a server owner and leave all its servers (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            self.bot.ban.set(guild_id, self.bot.ban.OWNER) # set ban flag to owner
            for g in self.bot.guilds: # check all guilds
                try:
                    if str(g.owner.id) == guild_id: # leave if the owner matches
                        await g.leave()
                except:
                    pass
            await inter.edit_original_message(embed=self.bot.embed(title="Banned server owner", color=self.COLOR))
            await self.guildList()
        except Exception as e:
            self.bot.logger.pushError("[OWNER] In 'owner ban owner' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="An unexpected error occured", color=self.COLOR))

    @ban.sub_command()
    async def checkid(self, inter: disnake.GuildCommandInteraction, user_id : str = commands.Param()) -> None:
        """ID Based Check if an user has a ban registered in the bot (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        msgs = []
        if self.bot.ban.check(user_id, self.bot.ban.OWNER): msgs.append("Banned from having the bot in its own servers\n")
        if self.bot.ban.check(user_id, self.bot.ban.SPARK): msgs.append("Banned from appearing in {}\n".format(self.bot.util.command2mention('spark ranking')))
        if self.bot.ban.check(user_id, self.bot.ban.PROFILE): msgs.append("Banned from using {}\n".format(self.bot.util.command2mention('gbf profile set')))
        if self.bot.ban.check(user_id, self.bot.ban.USE_BOT): msgs.append("Banned from using the bot\n")
        if len(msgs) == 0: msgs = ["No Bans set for this user"]
        await inter.edit_original_message(embed=self.bot.embed(title="User {}".format(user_id), description="".join(msgs), color=self.COLOR))

    @ban.sub_command()
    async def all(self, inter: disnake.GuildCommandInteraction, user_id : str = commands.Param()) -> None:
        """Ban an user from using the bot (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.set(user_id, self.bot.ban.USE_BOT)
        await inter.edit_original_message(embed=self.bot.embed(title="Banned user", color=self.COLOR))

    @ban.sub_command()
    async def profile(self, inter: disnake.GuildCommandInteraction, user_id : str = commands.Param()) -> None:
        """ID based Ban for /gbf profile (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.set(user_id, self.bot.ban.PROFILE)
        await inter.edit_original_message(embed=self.bot.embed(title="Banned user for profile", color=self.COLOR))

    @ban.sub_command()
    async def rollid(self, inter: disnake.GuildCommandInteraction, user_id : str = commands.Param()) -> None:
        """ID based Ban for /spark ranking (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.set(user_id, self.bot.ban.SPARK)
        await inter.edit_original_message(embed=self.bot.embed(title="Banned user for roll ranking", color=self.COLOR))

    @_owner.sub_command_group()
    async def unban(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @unban.sub_command(name="all")
    async def _all(self, inter: disnake.GuildCommandInteraction, user_id : str = commands.Param()) -> None:
        """Unban an user from using the bot (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.unset(user_id, self.bot.ban.USE_BOT)
        await inter.edit_original_message(embed=self.bot.embed(title="Unbanned user", color=self.COLOR))

    @unban.sub_command(name="profile")
    async def _profile(self, inter: disnake.GuildCommandInteraction, user_id : str = commands.Param()) -> None:
        """ID based Unban for /gbf profile (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.unset(user_id, self.bot.ban.PROFILE)
        await inter.edit_original_message(embed=self.bot.embed(title="Unbanned user for profile", color=self.COLOR))

    @unban.sub_command()
    async def roll(self, inter: disnake.GuildCommandInteraction, user_id : str = commands.Param()) -> None:
        """Unban an user from all the roll ranking (Owner Only)
        Ask me for an unban (to avoid abuses)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.unset(user_id, self.bot.ban.SPARK)
        await inter.edit_original_message(embed=self.bot.embed(title="Unbanned user for roll ranking", color=self.COLOR))

    @_owner.sub_command_group(name="bot")
    async def _bot(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @_bot.sub_command()
    async def invite(self, inter: disnake.GuildCommandInteraction) -> None:
        """Get the invite link (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        # return a bot invite link
        # careful with it, be sure to enable the invitations on the dev portal if it's off
        await inter.edit_original_message(embed=self.bot.embed(title=inter.guild.me.name, description="[Invite](https://discord.com/api/oauth2/authorize?client_id={}&permissions=1644905889015&scope=bot%20applications.commands)".format(self.bot.user.id), thumbnail=inter.guild.me.display_avatar, timestamp=self.bot.util.UTC(), color=self.COLOR))

    @_bot.sub_command()
    async def guilds(self, inter: disnake.GuildCommandInteraction) -> None:
        """List all servers (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        await self.guildList()
        await inter.edit_original_message(embed=self.bot.embed(title="Done", color=self.COLOR))

    @_bot.sub_command()
    async def reboot(self, inter: disnake.GuildCommandInteraction) -> None:
        """Shutdown the bot to make it reboot (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="Rebooting...", color=self.COLOR))
        self._shutdown() # Note: Assume a Watchtower or other similar system is in place. Else, the bot will just shutdown.

    @_bot.sub_command()
    async def avatar(self, inter: disnake.GuildCommandInteraction, filename : str = commands.Param(description="Filename of the asset to use")) -> None:
        """Change Rosetta's profile picture (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if await self.bot.changeAvatar(filename): # the avatar must be in assets/avatars
            await inter.edit_original_message(embed=self.bot.embed(title="Success", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Failed", color=self.COLOR))

    """notify_callback()
    CustomModal callback
    """
    async def notify_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        try:
            await inter.response.defer(ephemeral=True)
            # build/format the message to send
            msg = inter.text_values['message'].split('`')
            for i in range(1, len(msg), 2):
                msg[i] = self.bot.util.command2mention(msg[i])
                if not msg[i].startswith('<'): msg[i] = '`' + msg[i] + '`'
            msg = ''.join(msg).replace('\\n', '\n')
            # send to all channels
            await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(title="Rosetta Notification", description=msg, image=inter.text_values['image'], color=self.COLOR))
            await inter.edit_original_message(embed=self.bot.embed(title="The message has been sent", color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description='The following error occured:\n{}'.format(e), color=self.COLOR))

    @_bot.sub_command()
    async def notify(self, inter: disnake.GuildCommandInteraction) -> None:
        """Send a message to all announcement channels (Owner Only)"""
        await self.bot.util.send_modal(inter, "notify-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Notify Users", self.notify_callback, [
                disnake.ui.TextInput(
                    label="Message",
                    placeholder="Message",
                    custom_id="message",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=1,
                    max_length=3500,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="Image",
                    placeholder="URL",
                    custom_id="image",
                    style=disnake.TextInputStyle.short,
                    min_length=0,
                    max_length=300,
                    required=False
                )
            ]
        )

    @_owner.sub_command_group()
    async def data(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @data.sub_command()
    async def save(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command to make a snapshot of the bot's settings (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.data.autosave(True)
        await inter.edit_original_message(embed=self.bot.embed(title="Saved", color=self.COLOR))

    @data.sub_command()
    async def load(self, inter: disnake.GuildCommandInteraction, drive : int = commands.Param(description="Add 1 to use the file from the drive", default=0)) -> None:
        """Command to reload the bot save data (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if drive != 0: # download the save file from the drive.
            if self.bot.drive.load() is False:
                await inter.edit_original_message("Failed to retrieve save.json on the Google Drive")
                return
        # load the save file
        if self.bot.data.loadData():
            try: self.bot.get_cog('YouCrew').setBuffTask(True) # reload gw buff task
            except: pass
            self.bot.data.pending = False
            await self.bot.send('debug', embed=self.bot.embed(title=inter.me.name, description="save.json reloaded", color=self.COLOR))
        else:
            await self.bot.send('debug', embed=self.bot.embed(title=inter.me.name, description="save.json loading failed", color=self.COLOR))
        await inter.edit_original_message(embed=self.bot.embed(title="The command finished running", color=self.COLOR))

    @data.sub_command()
    async def get(self, inter: disnake.GuildCommandInteraction, filename: str = commands.Param(description="Path to a local file")) -> None:
        """Retrieve a bot file remotely (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            # open the file and read it
            with open(filename, 'rb') as infile:
                with self.bot.file.discord(infile) as df:
                    await self.bot.send('debug', file=df) # send the file to the debug channel
            await inter.edit_original_message(embed=self.bot.embed(title="File sent to the debug channel", color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[OWNER] In 'owner bot getfile' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="An unexpected error occured", color=self.COLOR))

    @data.sub_command()
    async def clearprofile(self, inter: disnake.GuildCommandInteraction, gbf_id : int = commands.Param(description="A valid GBF Profile ID", ge=0)) -> None:
        """Unlink a GBF id from an user ID (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        # retrieve the user
        user_id = self.bot.get_cog('GranblueFantasy').searchprofile(gbf_id)
        if user_id is None: # not found
            await inter.edit_original_message(embed=self.bot.embed(title="Clear Profile Error", description="ID not found", color=self.COLOR))
        else:
            try:
                del self.bot.data.save['gbfids'][user_id] # unlock the accounts
                self.bot.data.pending = True
            except:
                pass
            await inter.edit_original_message(embed=self.bot.embed(title="Clear Profile", description='User `{}` has been removed'.format(user_id), color=self.COLOR))

    @_owner.sub_command_group()
    async def maintenance(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @maintenance.sub_command(name="set")
    async def maintset(self, inter: disnake.GuildCommandInteraction, day : int = commands.Param(ge=1, le=31), month : int = commands.Param(ge=1, le=12), hour : int = commands.Param(ge=0, le=23), duration : int = commands.Param(ge=0)) -> None:
        """Set a maintenance date (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            self.bot.data.save['maintenance']['time'] = datetime.now().replace(month=month, day=day, hour=hour, minute=0, second=0, microsecond=0)
            self.bot.data.save['maintenance']['duration'] = duration
            self.bot.data.save['maintenance']['state'] = True
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Maintenance set", color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[OWNER] In 'owner maintenance set' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="An unexpected error occured", color=self.COLOR))

    @maintenance.sub_command(name="del")
    async def maintdel(self, inter: disnake.GuildCommandInteraction) -> None:
        """Delete the maintenance date (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.data.save['maintenance'] = {"state" : False, "time" : None, "duration" : 0}
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Maintenance deleted", color=self.COLOR))

    @_owner.sub_command_group()
    async def stream(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    """streamset_callback()
    CustomModal callback
    """
    async def streamset_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        if self.bot.data.save['stream'] is None: # init data if not set
            self.bot.data.save['stream'] = {'title':'', 'content':'', 'time':None}
        self.bot.data.save['stream']['title'] = inter.text_values.get('title', '')
        self.bot.data.save['stream']['content'] = inter.text_values.get('content', '')
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Stream Settings", description="Stream command sets to\n`{}`\n`{}`".format(self.bot.data.save['stream']['title'], self.bot.data.save['stream']['content']), color=self.COLOR))

    @stream.sub_command(name="set")
    async def streamset(self, inter: disnake.GuildCommandInteraction) -> None:
        """Set the stream command text (Owner Only)"""
        if self.bot.data.save['stream'] is None:
            data = {'title':' ', 'content':' ', 'time':None}
        else:
            data = {'title':self.bot.data.save['stream']['title'], 'content':self.bot.data.save['stream']['content'], 'time':self.bot.data.save['stream']['time']}
        await self.bot.util.send_modal(inter, "set_stream-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Set a GBF Stream", self.streamset_callback, [
            disnake.ui.TextInput(
                label="Title",
                placeholder="Event / Stream title",
                value=data['title'],
                custom_id="title",
                style=disnake.TextInputStyle.short,
                min_length=0,
                max_length=1024,
                required=True
            ),
            disnake.ui.TextInput(
                label="Description",
                placeholder="Event / Stream description",
                value=data['content'],
                custom_id="content",
                style=disnake.TextInputStyle.paragraph,
                min_length=0,
                max_length=1024,
                required=False
            )
        ])

    @stream.sub_command()
    async def time(self, inter: disnake.GuildCommandInteraction, day : int = commands.Param(ge=1, le=31), month : int = commands.Param(ge=1, le=12), year : int = commands.Param(ge=2021), hour : int = commands.Param(ge=0, le=23)) -> None:
        """Set the stream time (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            if self.bot.data.save['stream'] is None: # the stream MUST be set beforehand
                await inter.edit_original_message(embed=self.bot.embed(title="Stream Error", description="No Stream set.\nSet one first with {}.".format(self.bot.util.command2mention("owner stream set")), color=self.COLOR))
            else: # set the time value
                self.bot.data.save['stream']['time'] = datetime.now().replace(year=year, month=month, day=day, hour=hour, minute=0, second=0, microsecond=0)
                self.bot.data.pending = True
                await inter.edit_original_message(embed=self.bot.embed(title="Stream time set", color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[OWNER] In 'owner stream time' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="An unexpected error occured", color=self.COLOR))

    @stream.sub_command()
    async def clear(self, inter: disnake.GuildCommandInteraction) -> None:
        """Clear the stream command text (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.data.save['stream'] = None
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Stream cleared", color=self.COLOR))

    @_owner.sub_command_group()
    async def schedule(self, inter: disnake.GuildCommandInteraction):
        pass

    """scheduleset_callback()
    CustomModal callback
    """
    async def scheduleset_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        try:
            # the data must be a valid json object
            data = json.loads(inter.text_values['schedule'])
            if not isinstance(data, dict): raise Exception("Schedule data isn't a dictionnary")
            # go over the pairs
            for k, v in data.items():
                if not isinstance(v, list): raise Exception("Value of '{}' isn't a list".format(k))
                elif len(v) not in [1, 2]: raise Exception("Value of '{}' has an invalid length".format(k))
                else:
                    for e in v:
                        if not isinstance(e, int): raise Exception("One value of '{}' isn't an integer".format(k))
            # ok, set the data
            self.bot.data.save['schedule'] = data
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Schedule set", description="New Schedule:\n`{}`".format(self.bot.data.save['schedule']), color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Schedule error", description="Invalid data\n`{}`\nException: `{}`".format(inter.text_values['schedule'], e), color=self.COLOR))

    @schedule.sub_command(name="set")
    async def scheduleset(self, inter: disnake.GuildCommandInteraction) -> None:
        """Set the GBF schedule (Owner Only)"""
        await self.bot.util.send_modal(inter, "set_schedule-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Set the GBF Schedule", self.scheduleset_callback, [
            disnake.ui.TextInput(
                label="Schedule String",
                placeholder="{}",
                custom_id="schedule",
                value=json.dumps(self.bot.data.save['schedule']),
                style=disnake.TextInputStyle.paragraph,
                min_length=1,
                max_length=1024,
                required=True
            )
        ])

    @schedule.sub_command(name="update")
    async def scheduleupdate(self, inter: disnake.GuildCommandInteraction) -> None:
        """Force an automatic GBF schedule update (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.data.update_schedule()
        await inter.edit_original_message(embed=self.bot.embed(title="Schedule Update", description="Process finished", color=self.COLOR))

    @schedule.sub_command(name="add")
    async def scheduleadd(self, inter: disnake.GuildCommandInteraction, name : str = commands.Param(description="Entry name"), start : str = commands.Param(description="Start date (DD/MM/YY format)"), start_hour : int = commands.Param(description="Start Hour UTC (Default is 8)", default=17, ge=0, le=23), end : str = commands.Param(description="End date (DD/MM/YY format)", default=""), end_hour : int = commands.Param(description="Ending Hour UTC (Default is 8)", default=17, ge=0, le=23)) -> None:
        """Add or modify an entry (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        try:
            # timestamps contains the start timestamp and (optionally) the end timestamp
            timestamps = [int(datetime.strptime(start, '%d/%m/%y').replace(hour=start_hour, minute=0, second=0).timestamp())]
            if end != "":
                timestamps.append(int(datetime.strptime(end, '%d/%m/%y').replace(hour=end_hour, minute=0, second=0).timestamp()))
                if timestamps[1] <= timestamps[0]: raise Exception("Event Ending timestamp is lesser than the Starting timestamp")
            self.bot.data.save['schedule'][name] = timestamps
            await inter.edit_original_message(embed=self.bot.embed(title="Schedule Update", description="Entry added", color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Schedule Update", description="Error, did you set the date in the proper format (DD/MM/YY)?\nException:\n`{}`".format(self.bot.pexc(e)), color=self.COLOR))

    @_owner.sub_command_group()
    async def account(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @account.sub_command()
    async def see(self, inter: disnake.GuildCommandInteraction) -> None:
        """List the GBF account details used by Rosetta (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if not self.bot.net.has_account():
            await inter.edit_original_message(embed=self.bot.embed(title="GBF Account status", description="No accounts set", color=self.COLOR))
        else:
            # make a request to check the validity (if GBF is available)
            if await self.bot.net.gbf_available():
                r = await self.bot.net.requestGBF("user/user_id/1", expect_JSON=True)
            else:
                r = {}
            # retrieve data
            acc = self.bot.net.get_account()
            if r is None or not self.bot.net.is_account_valid():
                await inter.edit_original_message(embed=self.bot.embed(title="GBF Account status", description="Account is down or GBF is unavailable\nUser ID: `{}`\nCookie: `{}`\nUser-Agent: `{}`".format(acc['id'], acc['ck'], acc['ua']) , color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="GBF Account status", description="Account is up\nUser ID: `{}`\nCookie: `{}`\nUser-Agent: `{}`".format(acc['id'], acc['ck'], acc['ua']), color=self.COLOR))

    @account.sub_command()
    async def set(self, inter: disnake.GuildCommandInteraction, uid : int = commands.Param(default=0), ck : str = commands.Param(default=""), ua : str = commands.Param(default="")) -> None:
        """Set the GBF account used by Rosetta (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if uid < 1:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid parameter {}".format(uid), color=self.COLOR))
            return
        if ck == "":
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid parameter {}".format(ck), color=self.COLOR))
            return
        if ua == "":
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid parameter {}".format(ua), color=self.COLOR))
            return
        self.bot.net.set_account(uid, ck, ua)
        await inter.edit_original_message(embed=self.bot.embed(title="Account set", color=self.COLOR))

    @account.sub_command(name="clear")
    async def accclear(self, inter: disnake.GuildCommandInteraction) -> None:
        """Clear the GBF account used by Rosetta (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.net.clear_account()
        await inter.edit_original_message(embed=self.bot.embed(title="Account cleared", color=self.COLOR))

    @account.sub_command()
    async def edit(self, inter: disnake.GuildCommandInteraction, uid : int = commands.Param(description="User ID", ge=-1, default=-1), ck : str = commands.Param(description="Cookie", default=""), ua : str = commands.Param(description="User-Agent", default="")) -> None:
        """Edit the GBF account used by Rosetta (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if not self.bot.net.has_account():
            await inter.edit_original_message(embed=self.bot.embed(title="No account set", description="Use {} instead.".format(self.bot.util.command2mention('owner account set')), color=self.COLOR))
        else:
            if uid < 0: uid = None
            if ck == "": ck = None
            if ua == "": ua = None
            if uid is None and ck is None and ua is None:
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="You didn't set any valid value.\nNothing has been modified.", color=self.COLOR))
            elif not self.bot.net.edit_account(uid=uid, ck=ck, ua=ua):
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="A parameter is invalid.", color=self.COLOR))
            else:
                acc = self.bot.net.get_account()
                await inter.edit_original_message(embed=self.bot.embed(title="Account Updated", description="UID: `{}`\nCK: `{}`\nUA: `{}`".format(acc['id'], acc['ck'], acc['ua']), color=self.COLOR))

    @_owner.sub_command_group()
    async def db(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @db.sub_command(name="set")
    async def dbset(self, inter: disnake.GuildCommandInteraction, db_id : int = commands.Param(description="Dread Barrage ID", ge=0, le=999), element : str = commands.Param(description="Dread Barrage Element Advantage", autocomplete=['fire', 'water', 'earth', 'wind', 'light', 'dark']), day : int = commands.Param(description="Dread Barrage Start Day", ge=1, le=31), month : int = commands.Param(description="Dread Barrage Start Month", ge=1, le=12), year : int = commands.Param(description="Dread Barrage Start Year", ge=2021), extra_days : int = commands.Param(description="Number of days to increase the event duration (0 - 2)", ge=0, le=2, default=0)) -> None:
        """Set the Valiant date (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            # init data
            self.bot.data.save['dread'] = {}
            self.bot.data.save['dread']['state'] = False
            self.bot.data.save['dread']['id'] = db_id
            self.bot.data.save['dread']['element'] = element.lower()
            # build the calendar
            self.bot.data.save['dread']['dates'] = {}
            self.bot.data.save['dread']['dates']["Day 1"] = self.bot.util.UTC().replace(year=year, month=month, day=day, hour=19, minute=0, second=0, microsecond=0)
            self.bot.data.save['dread']['dates']["Day 2"] = self.bot.data.save['dread']['dates']["Day 1"] + timedelta(days=1)
            self.bot.data.save['dread']['dates']["Day 3"] = self.bot.data.save['dread']['dates']["Day 2"] + timedelta(days=1)
            self.bot.data.save['dread']['dates']["NM135"] = self.bot.data.save['dread']['dates']["Day 3"]
            self.bot.data.save['dread']['dates']["Day 4"] = self.bot.data.save['dread']['dates']["Day 3"] + timedelta(days=1)
            self.bot.data.save['dread']['dates']["Day 5"] = self.bot.data.save['dread']['dates']["Day 4"] + timedelta(days=1)
            self.bot.data.save['dread']['dates']["NM175"] = self.bot.data.save['dread']['dates']["Day 5"]
            self.bot.data.save['dread']['dates']["Day 6"] = self.bot.data.save['dread']['dates']["Day 5"] + timedelta(days=1)
            last = 6
            for i in range(0, extra_days):
                self.bot.data.save['dread']['dates']["Day {}".format(7+i)] = self.bot.data.save['dread']['dates']["Day {}".format(6+i)] + timedelta(days=1)
                last = 7 + i
            self.bot.data.save['dread']['dates']["End"] = self.bot.data.save['dread']['dates']["Day {}".format(last)] + timedelta(days=1)
            # set the valiant state to true
            self.bot.data.save['dread']['state'] = True
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="{} Dread Barrage Mode".format(self.bot.emote.get('gw')), description="Set to : **{:%m/%d %H:%M}**".format(self.bot.data.save['dread']['dates']["Day 1"]), color=self.COLOR))
        except Exception as e:
            self.bot.data.save['dread']['dates'] = {}
            self.bot.data.save['dread']['buffs'] = []
            self.bot.data.save['dread']['state'] = False
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", footer=str(e), color=self.COLOR))
            self.bot.logger.pushError("[OWNER] In 'owner db set' command:", e)

    @db.sub_command()
    async def disable(self, inter: disnake.GuildCommandInteraction) -> None:
        """Disable the Dread Barrage mode, but doesn't delete the settings (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.data.save['dread']['state'] = False
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="DB disabled", color=self.COLOR))

    @db.sub_command()
    async def enable(self, inter: disnake.GuildCommandInteraction) -> None:
        """Enable the Dread Barrage mode (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if self.bot.data.save['dread']['state'] is True:
            await inter.edit_original_message(embed=self.bot.embed(title="{} Dread Barrage Mode".format(self.bot.emote.get('gw')), description="Already enabled", color=self.COLOR))
        elif len(self.bot.data.save['dread']['dates']) == 8:
            self.bot.data.save['dread']['state'] = True
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="DB enabled", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="No Dread Barrage available in my memory", color=self.COLOR))

    @_owner.sub_command_group()
    async def gw(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @gw.sub_command()
    async def reloaddb(self, inter: disnake.GuildCommandInteraction) -> None:
        """Download GW.sql (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        # force download GW databases
        vers = await self.bot.ranking.getGWDB(force_download = True)
        # make a message showing each DB state
        msgs = []
        for i in [0, 1]:
            msgs.append("**{}** ▫️ ".format('GW_old.sql' if (i == 0) else 'GW.sql'))
            if vers[i] is None:
                msgs.append("Not loaded")
            else:
                if vers[i].gw is not None: msgs.append('GW{}'.format(vers[i].gw))
                if vers[i].ver is not None: msgs.append(' (version {}) '.format(vers[i].ver))
                if vers[i].timestamp is not None: msgs.append(' (at `{}`) '.format(vers[i].timestamp))
            msgs.append("\n")
        await inter.edit_original_message(embed=self.bot.embed(title="Guild War Databases", description=''.join(msgs), timestamp=self.bot.util.UTC(), color=self.COLOR))

    @gw.sub_command()
    async def forceupdategbfg(self, inter: disnake.GuildCommandInteraction) -> None:
        """Force an update of the GW /gbfg/ Data (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        # send to update
        await (self.bot.get_cog('GuildWar').updateGBFGData(True))
        await inter.edit_original_message(embed=self.bot.embed(title="/gbfg/ update finished", color=self.COLOR))

    @gw.sub_command(name="disable")
    async def disable__(self, inter: disnake.GuildCommandInteraction) -> None:
        """Disable the GW mode, without deleting settings (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        try: self.bot.get_cog('YouCrew').setBuffTask(False)
        except: pass
        self.bot.data.save['gw']['state'] = False
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="GW disabled", color=self.COLOR))

    @gw.sub_command(name="enable")
    async def enable__(self, inter: disnake.GuildCommandInteraction) -> None:
        """Enable the GW mode. Settings must exist (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if self.bot.data.save['gw']['state'] is True:
            await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War Mode".format(self.bot.emote.get('gw')), description="Already enabled", color=self.COLOR))
        elif len(self.bot.data.save['gw'].get('dates', {})) > 0:
            self.bot.data.save['gw']['state'] = True
            self.bot.data.pending = True
            try: self.bot.get_cog('YouCrew').setBuffTask(True)
            except: pass
            await inter.edit_original_message(embed=self.bot.embed(title="GW enabled", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="No Guild War available in my memory", color=self.COLOR))

    @gw.sub_command()
    async def cleartracker(self, inter: disnake.GuildCommandInteraction) -> None:
        """Clear the GW match tracker (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.data.save['youtracker'] = None
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Tracker cleared", color=self.COLOR))

    @gw.sub_command()
    async def forceupdateranking(self, inter: disnake.GuildCommandInteraction) -> None:
        """Force the retrieval of the GW ranking. For debugging (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if self.bot.data.save['gw']['state']:
            current_time = self.bot.util.JST()
            await self.bot.ranking.retrieve_ranking(current_time.replace(minute=20 * (current_time.minute // 20), second=1, microsecond=0), force=True)
            await inter.edit_original_message(embed=self.bot.embed(title="Done", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="GW isn't running", color=self.COLOR))

    @gw.sub_command(name="set")
    async def gwset(self, inter: disnake.GuildCommandInteraction, gw_id : int = commands.Param(description="Guild War ID", ge=0, le=999), element : str = commands.Param(description="Guild War Element Advantage", autocomplete=['fire', 'water', 'earth', 'wind', 'light', 'dark']), day : int = commands.Param(description="Guild War Start Day", ge=1, le=31), month : int = commands.Param(description="Guild War Start Month", ge=1, le=12), year : int = commands.Param(description="Guild War Start Year", ge=2021)) -> None:
        """Set the GW date (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            # stop the task
            try: self.bot.get_cog('YouCrew').setBuffTask(False)
            except: pass
            # init the data
            self.bot.data.save['gw'] = {}
            self.bot.data.save['gw']['state'] = False
            self.bot.data.save['gw']['id'] = gw_id
            self.bot.data.save['gw']['ranking'] = None
            self.bot.data.save['gw']['element'] = element.lower()
            # build the calendar
            self.bot.data.save['gw']['dates'] = {}
            self.bot.data.save['gw']['dates']["Preliminaries"] = self.bot.util.UTC().replace(year=year, month=month, day=day, hour=19, minute=0, second=0, microsecond=0)
            self.bot.data.save['gw']['dates']["Interlude"] = self.bot.data.save['gw']['dates']["Preliminaries"] + timedelta(days=1, seconds=43200) # +36h
            self.bot.data.save['gw']['dates']["Day 1"] = self.bot.data.save['gw']['dates']["Interlude"] + timedelta(days=1) # +24h
            self.bot.data.save['gw']['dates']["Day 2"] = self.bot.data.save['gw']['dates']["Day 1"] + timedelta(days=1) # +24h
            self.bot.data.save['gw']['dates']["Day 3"] = self.bot.data.save['gw']['dates']["Day 2"] + timedelta(days=1) # +24h
            self.bot.data.save['gw']['dates']["Day 4"] = self.bot.data.save['gw']['dates']["Day 3"] + timedelta(days=1) # +24h
            self.bot.data.save['gw']['dates']["Day 5"] = self.bot.data.save['gw']['dates']["Day 4"] + timedelta(days=1) # +24h
            self.bot.data.save['gw']['dates']["End"] = self.bot.data.save['gw']['dates']["Day 5"] + timedelta(seconds=61200) # +17h
            # build the buff list for (You)
            self.bot.data.save['gw']['buffs'] = []
            # Data format: Date, ATK/DEF buff bool, FO buff bool, warning bool, double buff bool
            # Prelims all
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(seconds=7200-300), True, True, True, True]) # warning, double
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(seconds=7200), True, True, False, True])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(seconds=43200-300), True, False, True, False]) # warning
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(seconds=43200), True, False, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(seconds=43200+3600-300), False, True, True, False]) # warning
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(seconds=43200+3600), False, True, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(days=1, seconds=10800-300), True, True, True, False]) # warning
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Preliminaries"]+timedelta(days=1, seconds=10800), True, True, False, False])
            # Interlude
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Interlude"]-timedelta(seconds=300), True, False, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Interlude"], True, False, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Interlude"]+timedelta(seconds=3600-300), False, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Interlude"]+timedelta(seconds=3600), False, True, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Interlude"]+timedelta(seconds=54000-300), True, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Interlude"]+timedelta(seconds=54000), True, True, False, False])
            # Day 1
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 1"]-timedelta(seconds=300), True, False, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 1"], True, False, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 1"]+timedelta(seconds=3600-300), False, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 1"]+timedelta(seconds=3600), False, True, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 1"]+timedelta(seconds=54000-300), True, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 1"]+timedelta(seconds=54000), True, True, False, False])
            # Day 2
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 2"]-timedelta(seconds=300), True, False, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 2"], True, False, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 2"]+timedelta(seconds=3600-300), False, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 2"]+timedelta(seconds=3600), False, True, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 2"]+timedelta(seconds=54000-300), True, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 2"]+timedelta(seconds=54000), True, True, False, False])
            # Day 3
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 3"]-timedelta(seconds=300), True, False, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 3"], True, False, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 3"]+timedelta(seconds=3600-300), False, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 3"]+timedelta(seconds=3600), False, True, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 3"]+timedelta(seconds=54000-300), True, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 3"]+timedelta(seconds=54000), True, True, False, False])
            # Day 4
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 4"]-timedelta(seconds=300), True, False, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 4"], True, False, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 4"]+timedelta(seconds=3600-300), False, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 4"]+timedelta(seconds=3600), False, True, False, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 4"]+timedelta(seconds=54000-300), True, True, True, False])
            self.bot.data.save['gw']['buffs'].append([self.bot.data.save['gw']['dates']["Day 4"]+timedelta(seconds=54000), True, True, False, False])
            # set the gw state to true
            self.bot.data.save['gw']['state'] = True
            # set the gw state to true
            self.bot.data.save['gw']['skip'] = False
            self.bot.data.pending = True
            await asyncio.sleep(0)
            # start the buff task
            try: self.bot.get_cog('YouCrew').setBuffTask(True)
            except: pass
            await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War Mode".format(self.bot.emote.get('gw')), description="Set to : **{:%m/%d %H:%M}**".format(self.bot.data.save['gw']['dates']["Preliminaries"]), color=self.COLOR))
        except Exception as e:
            try: self.bot.get_cog('YouCrew').setBuffTask(False)
            except: pass
            self.bot.data.save['gw']['dates'] = {}
            self.bot.data.save['gw']['buffs'] = []
            self.bot.data.save['gw']['state'] = False
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", footer=str(e), color=self.COLOR))
            self.bot.logger.pushError("[OWNER] In 'owner gw set' command:", e)

    @gw.sub_command()
    async def movepreliminaries(self, inter: disnake.GuildCommandInteraction, delta_prelim_hour : int = commands.Param(description="Number of hours to add to prelims", ge=1, le=999), delta_interlude_hour : int = commands.Param(description="Number of hours to add to interlude", ge=0, le=999, default=0)) -> None:
        """Move the preliminaries and shorten the interlude (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        # Note: This function is intended in case the schedule was shortened because of a server crash.
        if self.bot.data.save['gw']['state']:
            if self.bot.data.save['gw']['dates']["Day 1"] == self.bot.data.save['gw']['dates']["Interlude"]:
                await inter.edit_original_message(embed=self.bot.embed(title="The move is already affective", color=self.COLOR))
            else:
                self.bot.data.save['gw']['dates']["Preliminaries"] += timedelta(seconds=delta_prelim_hour*3600)
                self.bot.data.save['gw']['dates']["Interlude"] += timedelta(seconds=delta_interlude_hour*3600)
                while True:
                    if self.bot.data.save['gw']['buffs'][0] < self.bot.data.save['gw']['dates']["Preliminaries"]:
                        self.bot.data.save['gw']['buffs'].pop(0)
                self.bot.data.pending = True
                await inter.edit_original_message(embed=self.bot.embed(title="Done", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="GW isn't running", color=self.COLOR))

    @_owner.sub_command_group()
    async def buff(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @buff.sub_command()
    async def check(self, inter: disnake.GuildCommandInteraction) -> None:
        """List the GW buff list for (You). For debugging (Owner Only)"""
        try:
            await inter.response.defer(ephemeral=True)
            msgs = []
            for b in self.bot.data.save['gw']['buffs']:
                msgs.append('{0:%m/%d %H:%M}: '.format(b[0]))
                if b[1]: msgs.append('[Normal Buffs] ')
                if b[2]: msgs.append('[FO Buffs] ')
                if b[3]: msgs.append('[Warning] ')
                if b[4]: msgs.append('[Double duration] ')
                msgs.append('\n')
            await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War (You) Buff debug check".format(self.bot.emote.get('gw')), description=''.join(msgs), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error, buffs aren't set.", color=self.COLOR))

    @buff.sub_command()
    async def newtask(self, inter: disnake.GuildCommandInteraction) -> None:
        """Start a new checkGWBuff() task (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        try: self.bot.get_cog('YouCrew').setBuffTask(True)
        except: pass
        await inter.edit_original_message(embed=self.bot.embed(title="The Task (re)started", color=self.COLOR))

    @buff.sub_command()
    async def skip(self, inter: disnake.GuildCommandInteraction) -> None:
        """The bot will skip the next GW buff call (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if not self.bot.data.save['gw']['skip']:
            self.bot.data.save['gw']['skip'] = True # simply set the flag, the task handles the rest
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Next buffs will be skipped", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="The next set of buffs is already beind skipped", color=self.COLOR))

    @buff.sub_command()
    async def cancel(self, inter: disnake.GuildCommandInteraction) -> None:
        """Cancel the GW buff call skipping (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if self.bot.data.save['gw']['skip']:
            self.bot.data.save['gw']['skip'] = False # reset the flag
            self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Skip cancelled", color=self.COLOR))

    @_owner.sub_command_group()
    async def gacha(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @gacha.sub_command(name="clear")
    async def cleargacha(self, inter: disnake.GuildCommandInteraction) -> None:
        """Clear the current gacha data (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.data.save['gbfdata'].pop('gacha', None) # simply delete the gacha data
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Gacha data cleared", color=self.COLOR))

    @gacha.sub_command()
    async def roulette(self, inter: disnake.GuildCommandInteraction, guaranteddate : int = commands.Param(description="Date of the guaranted roll day (YYMMDD format)", ge=240101, le=500101, default=240100), forced3pc : int = commands.Param(description="1 to force real rate during guaranted roll day", ge=-1, le=1, default=-1), forcedroll : int = commands.Param(description="Number of guaranted roll", ge=-1, le=300, default=-1), forcedsuper : int = commands.Param(description="1 to add Super Mukku to guaranted roll day", ge=-1, le=1, default=-1), enable200 : int = commands.Param(description="1 to add 200 rolls on the wheel", ge=-1, le=1, default=-1), janken : int = commands.Param(description="1 to enable Janken mode", ge=-1, le=1, default=-1), maxjanken : int = commands.Param(description="Maximum number of janken", ge=0, le=10, default=0), doublemukku : int = commands.Param(description="1 to enable double Mukku", ge=-1, le=1, default=-1), realist : int = commands.Param(description="1 to allow realist mode", ge=-1, le=1, default=-1), birthday : int = commands.Param(description="1 to add the birthday zone on the wheel", ge=-1, le=1, default=-1)) -> None:
        """Set the roulette settings. Don't pass parameters to see settings. (Owner Only)"""
        await inter.response.defer(ephemeral=True)
        if 'roulette' not in self.bot.data.save['gbfdata']: # init data if it doesn't exist
            self.bot.data.save['gbfdata']['roulette'] = {}
        msgs = []
        if guaranteddate > 240100: # set the date (if valid)
            try:
                self.bot.util.JST().replace(year=2000+guaranteddate//10000, month=(guaranteddate//100)%100, day=guaranteddate%100, hour=5, minute=0, second=0, microsecond=0)
                self.bot.data.save['gbfdata']['roulette']['year'] = guaranteddate//10000
                self.bot.data.save['gbfdata']['roulette']['month'] = (guaranteddate//100)%100
                self.bot.data.save['gbfdata']['roulette']['day'] = guaranteddate%100
                self.bot.data.pending = True
            except:
                msgs.append("**Error**: Invalid date `{}`\n\n".format(guaranteddate))
        # set each setting one by one, and build the output message
        msgs.append("- Guaranted roll start date: `{}{}{}`\n".format(str(self.bot.data.save['gbfdata']['roulette'].get('year', 24)).zfill(2), str(self.bot.data.save['gbfdata']['roulette'].get('month', 1)).zfill(2), str(self.bot.data.save['gbfdata']['roulette'].get('day', 1)).zfill(2)))
        if forced3pc != -1:
            self.bot.data.save['gbfdata']['roulette']['forced3%'] = (forced3pc == 1)
            self.bot.data.pending = True
        msgs.append("- Guaranted roll real rate: {}\n".format("**Enabled**" if self.bot.data.save['gbfdata']['roulette'].get('forced3%', True) else "Disabled"))
        if forcedroll != -1:
            self.bot.data.save['gbfdata']['roulette']['forcedroll'] = forcedroll
            self.bot.data.pending = True
        msgs.append("- Number of Guaranted rolls: `{}`\n".format(self.bot.data.save['gbfdata']['roulette'].get('forcedroll', 100)))
        if forcedsuper != -1:
            self.bot.data.save['gbfdata']['roulette']['forcedsuper'] = (forcedsuper == 1)
            self.bot.data.pending = True
        msgs.append("- Super Mukku: {}\n".format("**Enabled**" if self.bot.data.save['gbfdata']['roulette'].get('forcedsuper', True) else "Disabled"))
        if enable200 != -1:
            self.bot.data.save['gbfdata']['roulette']['enable200'] = (enable200 == 1)
            self.bot.data.pending = True
        msgs.append("- 200 rolls on Wheel: {}\n".format("**Enabled**" if self.bot.data.save['gbfdata']['roulette'].get('enable200', False) else "Disabled"))
        if janken != -1:
            self.bot.data.save['gbfdata']['roulette']['enablejanken'] = (janken == 1)
            self.bot.data.pending = True
        msgs.append("- Janken mode: {}\n".format("**Enabled**" if self.bot.data.save['gbfdata']['roulette'].get('enablejanken', False) else "Disabled"))
        if maxjanken != 0:
            self.bot.data.save['gbfdata']['roulette']['maxjanken'] = maxjanken
            self.bot.data.pending = True
        msgs.append("- Max number of Janken: `{}`\n".format(self.bot.data.save['gbfdata']['roulette'].get('maxjanken', 1)))
        if doublemukku != -1:
            self.bot.data.save['gbfdata']['roulette']['doublemukku'] = (doublemukku == 1)
            self.bot.data.pending = True
        msgs.append("- Double Mukku: {}\n".format("**Enabled**" if self.bot.data.save['gbfdata']['roulette'].get('doublemukku', False) else "Disabled"))
        if realist != -1:
            self.bot.data.save['gbfdata']['roulette']['realist'] = (realist == 1)
            self.bot.data.pending = True
        msgs.append("- Realist mode: {}\n".format("**Enabled**" if self.bot.data.save['gbfdata']['roulette'].get('realist', False) else "Disabled"))
        if birthday != -1:
            self.bot.data.save['gbfdata']['roulette']['birthday'] = (birthday == 1)
            self.bot.data.pending = True
        msgs.append("- Birthday Zone on Wheel: {}\n".format("**Enabled**" if self.bot.data.save['gbfdata']['roulette'].get('birthday', False) else "Disabled"))
        # send the message
        await inter.edit_original_message(embed=self.bot.embed(title="Roulette Simulator settings", description="".join(msgs), color=self.COLOR))