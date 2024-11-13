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
    COLOR = 0x5e17e3

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def startTasks(self) -> None:
        self.bot.runTask('reminder', self.remindertask)

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
            c = self.bot.util.JST() + timedelta(seconds=30)
            for k, v in list(self.bot.data.save['reminders'].items()):
                for i, r in enumerate(v):
                    if c > r[0]:
                        if k not in send: send[k] = []
                        send[k].append(r[1][:1900])
                        self.bot.data.save['reminders'][k].pop(i)
                        self.bot.data.pending = True
                        await asyncio.sleep(0)
                if len(v) == 0:
                    self.bot.data.save['reminders'].pop(k)
                    self.bot.data.pending = True
                    await asyncio.sleep(0)
            return send
        except:
            return {}

    """remindertask()
    Bot Task managing the reminders set by the users
    """
    async def remindertask(self) -> None:
        while True:
            if not self.bot.running: return
            try:
                messages = await self.checkReminders()
                for mid in messages:
                    if int(mid) == self.bot.user.id: # bot reminders
                        for m in messages[mid]:
                            await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(title="Reminder", description=m, timestamp=self.bot.util.UTC(), thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png", color=self.COLOR), publish=True)
                    else:
                        u = await self.bot.get_or_fetch_user(int(mid))
                        for m in messages[mid]:
                            try:
                                await u.send(embed=self.bot.embed(title="Reminder", description=m))
                            except Exception as e:
                                self.bot.logger.pushError("[TASK] 'remindertask' Task Error:\nUser: {}\nReminder: {}".format(u.name, m), e)
                                break
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'remindertask' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'remindertask' Task Error:", e)
                await asyncio.sleep(200)
            await asyncio.sleep(50)

    """addBotReminder()
    Internal use only, add server wide reminders
    
    Parameters
    --------
    date: Date at which the reminder is fired
    msg: String, reminder content
    """
    def addBotReminder(self, date : datetime, msg : str):
        if str(self.bot.user.id) not in self.bot.data.save['reminders']:
            self.bot.data.save['reminders'][str(self.bot.user.id)] = []
        for m in self.bot.data.save['reminders'][str(self.bot.user.id)]:
            if m[0] == date and m[1] == msg:
                return
        self.bot.data.save['reminders'][str(self.bot.user.id)].append([date, msg])
        self.bot.data.pending = True

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def remind(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    async def _add(self, inter : disnake.GuildCommandInteraction, delta : timedelta, msg : str):
        aid = str(inter.author.id)
        if aid not in self.bot.data.save['reminders']:
            self.bot.data.save['reminders'][aid] = []
        if len(self.bot.data.save['reminders'][aid]) >= 8 and inter.author.id != self.bot.owner.id:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Sorry, I'm limited to 8 reminders per user 🙇", color=self.COLOR))
            return
        now = self.bot.util.UTC().replace(microsecond=0)
        target = now + timedelta(seconds=32400) + delta # keep JST
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
            d = date - now
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid date: `{}`".format(e), color=self.COLOR))
            return
        await self._add(inter, d, msg)

    @remind.sub_command()
    async def birthday(self, inter: disnake.GuildCommandInteraction, msg : str = commands.Param(description="Content of the reminder"), day : int = commands.Param(description="UTC Timezone", ge=1, le=31), month : int = commands.Param(description="UTC Timezone", ge=1, le=12)) -> None:
        """Remind you of something at the specified time (±30 seconds precision)"""
        await inter.response.defer(ephemeral=True)
        try:
            now = self.bot.util.UTC().replace(microsecond=0)
            date = now.replace(month=month, day=day, hour=0, minute=0, second=0, microsecond=0)
            if date < now: date = date.replace(year=date.year+1)
            d = date - now
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid date: `{}`".format(e), color=self.COLOR))
            return
        await self._add(inter, d, "Happy Birthday:\n" + msg)

    @remind.sub_command(name="list")
    async def remindlist(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post your current list of reminders"""
        await inter.response.defer(ephemeral=True)
        aid = str(inter.author.id)
        if aid not in self.bot.data.save['reminders'] or len(self.bot.data.save['reminders'][aid]) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="You don't have any reminders", color=self.COLOR))
        else:
            embed = disnake.Embed(title="{}'s Reminder List".format(inter.author.display_name), color=self.COLOR)
            embed.set_thumbnail(url=inter.author.display_avatar)
            for i, v in enumerate(self.bot.data.save['reminders'][aid]):
                embed.add_field(name="#{} ▫️ {}".format(i, self.bot.util.time(v[0], style=['d','t'], removejst=True)), value=v[1], inline=False)
            await inter.edit_original_message(embed=embed)

    @remind.sub_command(name="remove")
    async def reminddel(self, inter: disnake.GuildCommandInteraction, rid : int = commands.Param(description="Number of the reminder to delete")) -> None:
        """Delete one of your reminders"""
        await inter.response.defer(ephemeral=True)
        aid = str(inter.author.id)
        if aid not in self.bot.data.save['reminders'] or len(self.bot.data.save['reminders'][aid]) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="You don't have any reminders", color=self.COLOR))
        else:
            if rid < 0 or rid >= len(self.bot.data.save['reminders'][aid]):
                await inter.edit_original_message(embed=self.bot.embed(title="Reminder Error", description="Invalid id `{}`".format(rid), color=self.COLOR))
            else:
                self.bot.data.save['reminders'][aid].pop(rid)
                if len(self.bot.data.save['reminders'][aid]) == 0:
                    self.bot.data.save['reminders'].pop(aid)
                self.bot.data.pending = True
                await inter.edit_original_message(embed=self.bot.embed(title="The Reminder has been deleted", color=self.COLOR))