from __future__ import annotations
import disnake
from disnake.ext import commands
import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    # Type Aliases
    type ReminderData = list[datetime|str]
    type ReminderList = list[ReminderData]

# ----------------------------------------------------------------------------------------------------------------
# Reminder Cog
# ----------------------------------------------------------------------------------------------------------------
# Let users setup and manage "reminders" for later
# ----------------------------------------------------------------------------------------------------------------

class Reminder(commands.Cog):
    """Set Reminders."""
    COLOR : int = 0x5e17e3
    REMINDER_LIMIT : int = 8

    def __init__(self : Reminder, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    def startTasks(self : Reminder) -> None:
        if self.bot.isProduction():
            self.bot.runTask('reminder:task', self.remindertask)

    """checkReminders()
    Check the reminders ready to send.
    Update the save datas if the reminders are set in the old format.
    
    Returns
    --------
    dict: Reminders to send
    """
    async def checkReminders(self : Reminder) -> dict[str, str]:
        try:
            send : dict[str, str] = {}
            c : datetime = self.bot.util.JST() + timedelta(seconds=30) # current time, half a minute ahead to account for network delays and such (better remind early than late)
            k : str
            v : list[ReminderList]
            for k, v in list(self.bot.data.save['reminders'].items()): # iterate over (user , reminder) pairs
                i : int
                r : ReminderList
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
    async def remindertask(self : Reminder) -> None:
        while True:
            if not self.bot.running:
                return
            try:
                messages : dict[str, str] = await self.checkReminders() # obtain the messages to send, if any
                mid : str
                for mid in messages: # for each user id
                    if int(mid) == self.bot.user.id: # this is the bot, so we're dealing with bot reminders
                        for m in messages[mid]: # send each reminders to every announcement channels
                            await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(title="Reminder", description=m, timestamp=self.bot.util.UTC(), thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png", color=self.COLOR), publish=True)
                    else: # this is a normal user
                        u : disnake.User|None = await self.bot.get_or_fetch_user(int(mid)) # retrieve it
                        m : str
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
    def addBotReminder(self : Reminder, date : datetime, msg : str):
        if str(self.bot.user.id) not in self.bot.data.save['reminders']: # add list for the bot user
            self.bot.data.save['reminders'][str(self.bot.user.id)] = []
        for m in self.bot.data.save['reminders'][str(self.bot.user.id)]: # check if the message already exists (to not add a dupe)
            if m[0] == date and m[1] == msg:
                return
        self.bot.data.save['reminders'][str(self.bot.user.id)].append([date, msg]) # add it
        self.bot.data.pending = True

    """render()
    Display the interaction author's reminder list
    
    Parameters
    --------
    inter: A deferred disnake.ApplicationCommandInteraction
    description: String, the embed description. The reminder count will be appended to it.
    """
    async def render(self : Reminder, inter : disnake.ApplicationCommandInteraction, description : str) -> None:
        aid : str = str(inter.author.id)
        # set description
        append : str
        if aid not in self.bot.data.save['reminders']:
            append = "0 / {} reminders".format(self.REMINDER_LIMIT)
        elif len(self.bot.data.save['reminders'][aid]) >= self.REMINDER_LIMIT:
            append = "**{}** / {} reminders".format(len(self.bot.data.save['reminders'][aid]), self.REMINDER_LIMIT)
        else:
            append = "{} / {} reminders".format(len(self.bot.data.save['reminders'][aid]), self.REMINDER_LIMIT)
        if description != "" and not description.endswith('\n'):
            description += "\n" + append
        else:
            description += append
        # display list
        if aid not in self.bot.data.save['reminders'] or len(self.bot.data.save['reminders'][aid]) == 0: # no reminder for this user
            await inter.edit_original_message(embed=self.bot.embed(title="{}'s reminder list".format(inter.author.display_name), description=description, color=self.COLOR))
        else:
            embed : disnake.Embed = disnake.Embed(title="{}'s reminder list".format(inter.author.display_name).format(inter.author.display_name), description=description, color=self.COLOR)
            embed.set_thumbnail(url=inter.author.display_avatar)
            i : int
            v : ReminderList
            for i, v in enumerate(self.bot.data.save['reminders'][aid]): # list all reminders
                if i >= 25: # field limit
                    break
                embed.add_field(name="#{} ▫️ {}".format(i, self.bot.util.time(v[0], style=['d','t'], removejst=True)), value=v[1], inline=False)
            await inter.edit_original_message(embed=embed)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def remind(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    """_add()
    Subroutine to add a reminder to memory
    
    Parameters
    ----------
    inter: A disnake.ApplicationCommandInteraction interaction object
    delta: timedelta to desired reminder date
    msg: String, the reminder message
    """
    async def _add(self : Reminder, inter : disnake.ApplicationCommandInteraction, delta : timedelta, msg : str):
        aid : str = str(inter.author.id)
        if aid not in self.bot.data.save['reminders']: # Add reminder list for this user
            self.bot.data.save['reminders'][aid] = []
        # Check if the user reached its reminder limit
        description : str
        if len(self.bot.data.save['reminders'][aid]) >= self.REMINDER_LIMIT and inter.author.id != self.bot.owner.id: # Owner isn't limited
            description = "Error, you've reached the **limit**"
        else:
            now : datetime = self.bot.util.JST(delay=False).replace(microsecond=0) # we keep dates in JST as most of the bot uses it
            target : datetime = now + delta
            if target - now >= timedelta(days=500):
                description = "Error, you can't set a reminder **further than 500 days** in the  future"
                return
            elif msg == "":
                description = "Error, your reminder message is empty"
            elif len(msg) > 400:
                description = "Error, reminder messages are limited to 400 characters"
            else:
                try:
                    self.bot.data.save['reminders'][aid].append([target, msg])
                    self.bot.data.pending = True
                    description = "The Reminder has been added"
                except:
                    description = "An unexpected error occured"
        await self.render(inter, description)

    @remind.sub_command()
    async def add(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, duration : str = commands.Param(description="Format: XdXhXmXs"), msg : str = commands.Param(description="Content of the reminder")) -> None:
        """Remind you of something at the specified time (±30 seconds precision)"""
        await inter.response.defer(ephemeral=True)
        try:
            d : timedelta = self.bot.util.str2delta(duration)
            if d is None: raise Exception()
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid duration string `{}`, format is `NdNhNm`".format(duration), color=self.COLOR))
            return
        await self._add(inter, d, msg)

    @remind.sub_command()
    async def event(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, msg : str = commands.Param(description="Content of the reminder"), day : int = commands.Param(description="UTC Timezone", ge=1, le=31), month : int = commands.Param(description="UTC Timezone", ge=1, le=12), year : int = commands.Param(description="UTC Timezone", ge=2022), hour : int = commands.Param(description="UTC Timezone", ge=0, le=23), minute : int = commands.Param(description="UTC Timezone", ge=0, le=59)) -> None:
        """Remind you of something at the specified time (±30 seconds precision)"""
        await inter.response.defer(ephemeral=True)
        try:
            now : datetime = self.bot.util.UTC().replace(microsecond=0)
            date : datetime = now.replace(year=year, month=month, day=day, hour=hour, minute=minute, second=0, microsecond=0)
            if date <= now:
                raise Exception("The date you set is in the past")
            d : timedelta = date - now # calculate delta between now and desired date
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid date: `{}`".format(e), color=self.COLOR))
            return
        await self._add(inter, d, msg)

    @remind.sub_command()
    async def birthday(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, msg : str = commands.Param(description="Content of the reminder"), day : int = commands.Param(description="UTC Timezone", ge=1, le=31), month : int = commands.Param(description="UTC Timezone", ge=1, le=12)) -> None:
        """Remind you of something at the next specified date (±30 seconds precision)"""
        await inter.response.defer(ephemeral=True)
        try:
            now : datetime = self.bot.util.UTC().replace(microsecond=0)
            date : datetime = now.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
            if date < now:
                date = date.replace(year=date.year+1)
            d : timedelta = date - now # calculate delta between now and desired date
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid date: `{}`".format(e), color=self.COLOR))
            return
        await self._add(inter, d, "Happy Birthday:\n" + msg)

    @remind.sub_command(name="list")
    async def remindlist(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post your current list of reminders"""
        await inter.response.defer(ephemeral=True)
        await self.render(inter, "")

    @remind.sub_command(name="remove")
    async def reminddel(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, rid : int = commands.Param(description="Number of the reminder to delete", ge=0)) -> None:
        """Delete one of your reminders"""
        await inter.response.defer(ephemeral=True)
        aid: str  = str(inter.author.id)
        description : str
        if aid not in self.bot.data.save['reminders'] or len(self.bot.data.save['reminders'][aid]) == 0: # no reminder for this user
            description = "Error, you don't have any reminders"
        else:
            if rid < 0 or rid >= len(self.bot.data.save['reminders'][aid]): # check if given reminder index is valid
                description = "Error, Invalid id `{}`".format(rid)
            else:
                self.bot.data.save['reminders'][aid].pop(rid) # remove the reminder
                if len(self.bot.data.save['reminders'][aid]) == 0: # remove user list if empty
                    self.bot.data.save['reminders'].pop(aid)
                self.bot.data.pending = True
                description = "The Reminder has been deleted"
        await self.render(inter, description)