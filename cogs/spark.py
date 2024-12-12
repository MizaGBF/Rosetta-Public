import disnake
from disnake.ext import commands
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from datetime import datetime, timedelta
import math
from operator import itemgetter
import re

# ----------------------------------------------------------------------------------------------------------------
# Spark Cog
# ----------------------------------------------------------------------------------------------------------------
# Register and estimate people GBF Spark status
# ----------------------------------------------------------------------------------------------------------------

class Sparking(commands.Cog):
    """Track your Granblue Spark."""
    COLOR = 0xeba834
    NICKNAME_REGEX = re.compile("(\(\d+\/\d{3}\))")
    MONTHLY_MIN = [90, 90, 170, 90, 90, 85, 100, 250, 100, 90, 80, 180]
    MONTHLY_MAX = [80, 70, 130, 80, 70, 75, 80, 200, 80, 50, 70, 130]
    MONTHLY_DAY = [31.0, 28.25, 31.0, 30.0, 31.0, 30.0, 31.0, 31.0, 30.0, 31.0, 30.0, 31.0]

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 10, commands.BucketType.user)
    @commands.max_concurrency(4, commands.BucketType.default)
    async def spark(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    """_seeroll()
    Display the user roll count
    
    Parameters
    --------
    inter: Command or modal interaction
    member: A disnake.Member object
    ephemeral: Boolean to display or not the result to everyone
    """
    async def _seeroll(self, inter: disnake.GuildCommandInteraction, member: disnake.Member, ephemeral : bool = True) -> None:
        await inter.response.defer(ephemeral=ephemeral)
        if member is None: member = inter.author
        aid = str(member.id)
        try:
            # get the roll count
            if aid in self.bot.data.save['spark']:
                s = self.bot.data.save['spark'][aid]
                if s[0] < 0 or s[1] < 0 or s[2] < 0 or s[3] < 0:
                    raise Exception('Negative numbers')
                r = (s[0] / 300) + s[1] + s[2] * 10 + s[3]
                fr = math.floor(r)
                timestamp = s[4]
            else:
                r = 0
                fr = 0
                s = None
                timestamp = None

            t_min, t_max, expected, now = self._estimate(r, timestamp)
            # roll count text
            title = "{} has {} roll".format(member.display_name, fr)
            if fr != 1: title += "s"
            # sending
            if s is None:
                await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':member.display_avatar}, description="Update your rolls with the `/spark set` command", footer="Next spark between {} and {} from 0 rolls".format(t_min.strftime("%y/%m/%d"), t_max.strftime("%y/%m/%d")), color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':member.display_avatar}, description="**{} {} {} {} {} {} {}**\n*Expecting {} to {} rolls in {}*".format(self.bot.emote.get("crystal"), s[0], self.bot.emote.get("singledraw"), s[1], self.bot.emote.get("tendraw"), s[2], ("" if s[3] == 0 else "{} {}".format(self.bot.emote.get("shrimp"), s[3])),expected[0], expected[1], now.strftime("%B")), footer="Next spark between {} and {}".format(t_min.strftime("%y/%m/%d"), t_max.strftime("%y/%m/%d")), timestamp=timestamp, color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[SPARK] 'seeRoll' error:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Critical Error", description="I warned my owner", color=self.COLOR, footer=str(e)))

    """set_callback()
    CustomModal callback
    """
    async def set_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        try:
            crystal = int(inter.text_values['crystal'])
            single = int(inter.text_values['single'])
            ten = int(inter.text_values['ten'])
            shrimp = int(inter.text_values['shrimp'])
            if crystal < 0 or single < 0 or ten < 0 or shrimp < 0:
                raise Exception('Negative Number Error')
            if crystal >= 600000:
                raise Exception('Big Number Error')
            aid = str(inter.author.id)
            if crystal + single + ten + shrimp == 0: 
                if aid in self.bot.data.save['spark']:
                    self.bot.data.save['spark'].pop(aid)
            else:
                self.bot.data.save['spark'][aid] = [crystal, single, ten, shrimp, self.bot.util.UTC()]
            self.bot.data.pending = True
            await self._seeroll(inter, inter.author)
        except Exception as e:
            await inter.response.send_message(embed=self.bot.embed(title="Error", description="Your entered an invalid number.", footer=str(e), color=self.COLOR), ephemeral=True)

    @spark.sub_command()
    async def set(self, inter: disnake.GuildCommandInteraction) -> None:
        """Set your roll count"""
        data = self.bot.data.save['spark'].get(str(inter.author.id), [0, 0, 0, 0, None])
        await self.bot.util.send_modal(inter, "spark_set-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Set your Spark Data", self.set_callback, [
            disnake.ui.TextInput(
                label="Crystal",
                placeholder="Your crystal amount",
                custom_id="crystal",
                style=disnake.TextInputStyle.short,
                value=str(data[0]),
                min_length=1,
                max_length=6,
                required=True
            ),
            disnake.ui.TextInput(
                label="Single Draw Ticket",
                placeholder="Your single draw ticket amount",
                custom_id="single",
                style=disnake.TextInputStyle.short,
                value=str(data[1]),
                min_length=1,
                max_length=3,
                required=True
            ),
            disnake.ui.TextInput(
                label="Ten Draw Ticket",
                placeholder="Your ten draw ticket amount",
                custom_id="ten",
                style=disnake.TextInputStyle.short,
                value=str(data[2]),
                min_length=1,
                max_length=2,
                required=True
            ),
            disnake.ui.TextInput(
                label="Shrimp",
                placeholder="Your shrimp amount",
                custom_id="shrimp",
                style=disnake.TextInputStyle.short,
                value=str(data[3]),
                min_length=1,
                max_length=3,
                required=True
            )
        ])

    """_estimate()
    Calculate a spark estimation (using my personal stats)
    
    Parameters
    ----------
    r: Current number of rolls
    timestamp: start time, can be None
    
    Returns
    --------
    tuple: Containing:
        - t_min: Earliest time for a spark
        - t_max: Max time for a spark
        - expected: Expected number of rolls during the start month
        - now: start time (set to current time if timestamp is None)
    """
    def _estimate(self, r : int, timestamp : Optional[datetime]) -> tuple:
        # from january to december

        # get current day
        if timestamp is None: now = self.bot.util.UTC().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else: now = timestamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        t_min = now
        t_max = now
        r_min = r % 300
        r_max = r_min
        expected = [self.MONTHLY_MAX[now.month-1], self.MONTHLY_MIN[now.month-1]]
        while r_min < 300 or r_max < 300: # increase the date until we reach the 300 target for both estimation
            if r_min < 300:
                m = (t_min.month-1) % 12
                r_min += self.MONTHLY_MIN[m] / self.MONTHLY_DAY[m]
                t_min += timedelta(days=1)
            if r_max < 300:
                m = (t_max.month-1) % 12
                r_max += self.MONTHLY_MAX[m] / self.MONTHLY_DAY[m]
                t_max += timedelta(days=1)
        return t_min, t_max, expected, now

    @spark.sub_command()
    async def see(self, inter: disnake.GuildCommandInteraction, member : disnake.Member = None) -> None:
        """Post your (or the target) roll count"""
        await self._seeroll(inter, member)

    @spark.sub_command()
    async def zero(self, inter: disnake.GuildCommandInteraction, day_difference: int = commands.Param(description="Add a number of days to today date", ge=0, default=0)) -> None:
        """Post a spark estimation based on today date"""
        try:
            await inter.response.defer(ephemeral=True)
            t_min, t_max, expected, now = self._estimate(0, self.bot.util.UTC().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_difference))
            # roll count text
            await inter.edit_original_message(embed=self.bot.embed(title='{} Spark estimation from {} rolls at {}'.format(self.bot.emote.get("crystal"), day_difference, now.strftime("%y/%m/%d")), description="Next spark between {} and {}\n*Expecting {} to {} rolls in {}*".format(t_min.strftime("%y/%m/%d"), t_max.strftime("%y/%m/%d"), expected[0], expected[1], now.strftime("%B")), color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Critical Error", description="I warned my owner", color=self.COLOR, footer=str(e)))
            self.bot.logger.pushError("[SPARK] In 'spark zero' command:", e)

    @spark.sub_command()
    async def nickname(self, inter: disnake.GuildCommandInteraction) -> None:
        """Update your nickname with your number of rolls""" 
        await inter.response.defer(ephemeral=True)
        aid = str(inter.author.id)
        if not inter.channel.permissions_for(inter.me).manage_nicknames:
            await inter.edit_original_message(embed=self.bot.embed(title="I lack the Manage Nickname permission for this feature", color=self.COLOR))
        elif inter.channel.permissions_for(inter.me).administrator:
            await inter.edit_original_message(embed=self.bot.embed(title="Sorry, administrator nicknames can't be edited", color=self.COLOR))
        elif inter.guild.owner_id == inter.author.id:
            await inter.edit_original_message(embed=self.bot.embed(title="Sorry, server owner nicknames can't be edited", color=self.COLOR))
        elif aid not in self.bot.data.save['spark']:
            await inter.edit_original_message(embed=self.bot.embed(title="No data in memory, please set your roll count first", color=self.COLOR))
        else:
            s = self.bot.data.save['spark'][aid]
            r = (s[0] / 300) + s[1] + s[2] * 10 + s[3]
            fr = math.floor(r)
            mr = 300
            while mr < fr:
                mr += 300
            n = self.NICKNAME_REGEX.sub('({}/{})'.format(fr, mr), inter.author.display_name)
            m = await inter.guild.get_or_fetch_member(inter.author.id)
            if n == inter.author.display_name:
                await m.edit(nick=inter.author.display_name + ' ({}/{})'.format(fr, mr))
            else:
                await m.edit(nick=n)
            await inter.edit_original_message(embed=self.bot.embed(title="Your nickname has been updated", color=self.COLOR))

    """_ranking()
    Retrieve the spark data of this server users and rank them
    
    Parameters
    ----------
    inter: Command interaction
    guild: Target guild
    
    Returns
    --------
    tuple: Containing:
        - msg: String containing the ranking
        - ar: Integer, Author ranking
        - top: Integer, Top limit
    """
    async def _ranking(self, inter: disnake.GuildCommandInteraction, guild) -> None:
        ranking = {}
        for iid, s in self.bot.data.save['spark'].items():
            if self.bot.ban.check(iid, self.bot.ban.SPARK):
                continue
            m = await guild.get_or_fetch_member(int(iid))
            if m is not None:
                if s[0] < 0 or s[1] < 0 or s[2] < 0 or s[3] < 0:
                    continue
                r = (s[0] / 300) + s[1] + s[2] * 10 + s[3]
                if r > 1800:
                    continue
                ranking[iid] = r
        if len(ranking) == 0:
            return None, None, None
        ar = -1
        i = 0
        emotes = {0:self.bot.emote.get('SSR'), 1:self.bot.emote.get('SR'), 2:self.bot.emote.get('R')}
        msgs = []
        top = 15
        for key, value in sorted(ranking.items(), key = itemgetter(1), reverse = True):
            if i < top:
                fr = math.floor(value)
                msgs.append("**#{:<2}{} {}** with {} roll".format(i+1, emotes.pop(i, "▫️"), (await guild.get_or_fetch_member(int(key))).display_name, fr))
                if fr != 1:
                    msgs.append("s")
                msgs.append("\n")
            if key == str(inter.author.id):
                ar = i
                if i >= top: break
            i += 1
            if i >= 100:
                break
        return "".join(msgs), ar, top

    @spark.sub_command()
    async def ranking(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the ranking of everyone saving for a spark in the server"""
        try:
            await inter.response.defer()
            guild = inter.author.guild
            msg, ar, top = await self._ranking(inter, guild)
            if msg is None:
                await inter.edit_original_message(embed=self.bot.embed(title="The ranking of this server is empty", color=self.COLOR))
                return
            if ar >= top: footer = "You are ranked #{}".format(ar+1)
            elif ar == -1: footer = "You aren't ranked ▫️ You need at least one roll to be ranked"
            else: footer = ""
            try: icon = guild.icon.url
            except: icon = None
            await inter.edit_original_message(embed=self.bot.embed(title="{} Spark ranking of {}".format(self.bot.emote.get('crown'), guild.name), color=self.COLOR, description=msg, footer=footer, thumbnail=icon))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Sorry, something went wrong :bow:", footer=str(e), color=self.COLOR))
            self.bot.logger.pushError("[SPARK] In 'spark ranking' command:", e)
        await self.bot.util.clean(inter, 40)

    @commands.user_command(name="GBF Spark")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 40, commands.BucketType.user)
    @commands.max_concurrency(4, commands.BucketType.default)
    async def seespark(self, inter: disnake.UserCommandInteraction, member: disnake.Member) -> None:
        """Post the user roll count"""
        await self._seeroll(inter, member)