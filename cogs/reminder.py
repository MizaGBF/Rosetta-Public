import disnake
from disnake.ext import commands
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from datetime import datetime, timedelta

# ----------------------------------------------------------------------------------------------------------------
# Reminder Cog
# ----------------------------------------------------------------------------------------------------------------
# Let users setup and manage "reminders" for later
# ----------------------------------------------------------------------------------------------------------------

class Reminder(commands.Cog):
    """Set Reminders."""
    COLOR : int = 0x5e17e3
    REMINDER_LIMIT = 8

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot

    def startTasks(self) -> None:
        self.bot.runTask('reminder:task', self.remindertask)

    """checkReminders()
    Check the reminders ready to send.
    Update the save datas if the reminders are set in the old format.
    
    Returns
    --------
    dict: Reminders to send
    """
    async def checkReminders(self) -> dict:
        try:
            send = {}
            c = self.bot.util.JST() + timedelta(seconds=30) # current time, half a minute ahead to account for network delays and such (better remind early than late)
            for k, v in list(self.bot.data.save['reminders'].items()): # iterate over (user , reminder) pairs
                for i, r in enumerate(v): # iterate over the reminders
                    if c >= r[0]: # check if c (current time) is greater or equal than the r[0] (targeted date)
                        if k not in send: # create array of message to send for that user if not created
                            send[k] = []
                        send[k].append(r[1][:1900]) # add reminder to list of messages to send (limited to 1900 characters)
                        self.bot.data.save['reminders'][k].pop(i) # remove reminder
                        self.bot.data.pending = True
                        await asyncio.sleep(0)
                if len(v) == 0: # if reminder list of that user is empty
                    self.bot.data.save['reminders'].pop(k) # remove
                    self.bot.data.pending = True
                    await asyncio.sleep(0)
            return send # return dict of reminders to send
        except:
            return {}

    """remindertask()
    Bot Task managing the reminders set by the users
    """
    async def remindertask(self) -> None:
        while True:
            if not self.bot.running:
                return
            try:
                messages = await self.checkReminders() # obtain the messages to send, if any
                for mid in messages: # for each user id
                    if int(mid) == self.bot.user.id: # this is the bot, so we're dealing with bot reminders
                        for m in messages[mid]: # send each reminders to every announcement channels
                            await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(title="Reminder", description=m, timestamp=self.bot.util.UTC(), thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png", color=self.COLOR), publish=True)
                    else: # this is a normal user
                        u = await self.bot.get_or_fetch_user(int(mid)) # retrieve it
                        for m in messages[mid]: # send each message to their dm
                            try:
                                await u.send(embed=self.bot.embed(title="Reminder", description=m))
                            except Exception as e:
                                self.bot.logger.pushError("[TASK] 'reminder:task' Task Error:\nUser: {}\nReminder: {}".format(u.name, m), e)
                                break
                await asyncio.sleep(50) # wait 50s before checking again
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'reminder:task' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'reminder:task' Task Error:", e)
                await asyncio.sleep(200)

    """addBotReminder()
    Internal use only, add server wide reminders
    
    Parameters
    --------
    date: Date at which the reminder is fired
    msg: String, reminder content
    """
    def addBotReminder(self, date : datetime, msg : str):
        if str(self.bot.user.id) not in self.bot.data.save['reminders']: # add list for the bot user
            self.bot.data.save['reminders'][str(self.bot.user.id)] = []
        for m in self.bot.data.save['reminders'][str(self.bot.user.id)]: # check if the message already exists (to not add a dupe)
            if m[0] == date and m[1] == msg:
                return
        self.bot.data.save['reminders'][str(self.bot.user.id)].append([date, msg]) # add it
        self.bot.data.pending = True

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def remind(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    """_add()
    Subroutine to add a reminder to memory
    
    Parameters
    ----------
    inter: A disnake.GuildCommandInteraction interaction object
    delta: timedelta to desired reminder date
    msg: String, the reminder message
    """
    async def _add(self, inter : disnake.GuildCommandInteraction, delta : timedelta, msg : str):
        aid = str(inter.author.id)
        if aid not in self.bot.data.save['reminders']: # Add reminder list for this user
            self.bot.data.save['reminders'][aid] = []
        # Check if the user reached its reminder limit
        if len(self.bot.data.save['reminders'][aid]) >= self.REMINDER_LIMIT and inter.author.id != self.bot.owner.id: # Owner isn't limited
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Sorry, I'm limited to 8 reminders per user 🙇", color=self.COLOR))
            return
        now = self.bot.util.JST(delay=False).replace(microsecond=0) # we keep dates in JST as most of the bot uses it
        target = now + delta
        if target - now >= timedelta(days=500):
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="You can't set a reminder further than 500 days in the  future", color=self.COLOR))
            return
        elif msg == "":
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Tell me what I'm supposed to remind you 🤔", color=self.COLOR))
            return
        elif len(msg) > 400:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Reminders are limited to 400 characters", color=self.COLOR))
            return
        try:
            self.bot.data.save['reminders'][aid].append([target, msg])
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="The Reminder has been added", color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", footer="I have no clues about what went wrong", color=self.COLOR))

    @remind.sub_command()
    async def add(self, inter: disnake.GuildCommandInteraction, duration : str = commands.Param(description="Format: XdXhXmXs"), msg : str = commands.Param(description="Content of the reminder")) -> None:
        """Remind you of something at the specified time (±30 seconds precision)"""
        await inter.response.defer(ephemeral=True)
        try:
            d = self.bot.util.str2delta(duration)
            if d is None: raise Exception()
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid duration string `{}`, format is `NdNhNm`".format(duration), color=self.COLOR))
            return
        await self._add(inter, d, msg)

    @remind.sub_command()
    async def event(self, inter: disnake.GuildCommandInteraction, msg : str = commands.Param(description="Content of the reminder"), day : int = commands.Param(description="UTC Timezone", ge=1, le=31), month : int = commands.Param(description="UTC Timezone", ge=1, le=12), year : int = commands.Param(description="UTC Timezone", ge=2022), hour : int = commands.Param(description="UTC Timezone", ge=0, le=23), minute : int = commands.Param(description="UTC Timezone", ge=0, le=59)) -> None:
        """Remind you of something at the specified time (±30 seconds precision)"""
        await inter.response.defer(ephemeral=True)
        try:
            now = self.bot.util.UTC().replace(microsecond=0)
            date = now.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if date <= now: raise Exception("The date you set is in the past")
            d = date - now # calculate delta between now and desired date
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid date: `{}`".format(e), color=self.COLOR))
            return
        await self._add(inter, d, msg)

    @remind.sub_command()
    async def birthday(self, inter: disnake.GuildCommandInteraction, msg : str = commands.Param(description="Content of the reminder"), day : int = commands.Param(description="UTC Timezone", ge=1, le=31), month : int = commands.Param(description="UTC Timezone", ge=1, le=12)) -> None:
        """Remind you of something at the next specified date (±30 seconds precision)"""
        await inter.response.defer(ephemeral=True)
        try:
            now = self.bot.util.UTC().replace(microsecond=0)
            date = now.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
            if date < now: date = date.replace(year=date.year+1)
            d = date - now # calculate delta between now and desired date
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid date: `{}`".format(e), color=self.COLOR))
            return
        await self._add(inter, d, "Happy Birthday:\n" + msg)

    @remind.sub_command(name="list")
    async def remindlist(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post your current list of reminders"""
        await inter.response.defer(ephemeral=True)
        aid = str(inter.author.id)
        if aid not in self.bot.data.save['reminders'] or len(self.bot.data.save['reminders'][aid]) == 0: # no reminder for this user
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="You don't have any reminders", color=self.COLOR))
        else:
            embed = disnake.Embed(title="{}'s Reminder List".format(inter.author.display_name), color=self.COLOR)
            embed.set_thumbnail(url=inter.author.display_avatar)
            for i, v in enumerate(self.bot.data.save['reminders'][aid]): # list all reminders
                if i >= 25: # field limit
                    break
                embed.add_field(name="#{} ▫️ {}".format(i, self.bot.util.time(v[0], style=['d','t'], removejst=True)), value=v[1], inline=False)
            await inter.edit_original_message(embed=embed)

    @remind.sub_command(name="remove")
    async def reminddel(self, inter: disnake.GuildCommandInteraction, rid : int = commands.Param(description="Number of the reminder to delete", ge=0)) -> None:
        """Delete one of your reminders"""
        await inter.response.defer(ephemeral=True)
        aid = str(inter.author.id)
        if aid not in self.bot.data.save['reminders'] or len(self.bot.data.save['reminders'][aid]) == 0: # no reminder for this user
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="You don't have any reminders", color=self.COLOR))
        else:
            if rid < 0 or rid >= len(self.bot.data.save['reminders'][aid]): # check if given reminder index is valid
                await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid id `{}`".format(rid), color=self.COLOR))
            else:
                self.bot.data.save['reminders'][aid].pop(rid) # remove the reminder
                if len(self.bot.data.save['reminders'][aid]) == 0: # remove user list if empty
                    self.bot.data.save['reminders'].pop(aid)
                self.bot.data.pending = True
                await inter.edit_original_message(embed=self.bot.embed(title="The Reminder has been deleted", color=self.COLOR))