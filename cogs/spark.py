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
    COLOR : int = 0xeba834
    TOP_LIMIT = 15
    NICKNAME_REGEX = re.compile("(\(\d+\/\d{3}\))")
    # Expected monthly roll gain
    # Roughly estimated from https://docs.google.com/spreadsheets/d/17FxHgTDdKIcIb6IHvLSq6JgG1CqRFoFs7vSPKBy7VKc/edit?gid=1662801985#gid=1662801985
    MONTHLY_MAX = [90, 90, 170, 90, 90, 85, 100, 250, 100, 90, 80, 180]
    MONTHLY_MIN = [80, 70, 130, 80, 70, 75, 80, 200, 80, 50, 70, 130]
    # Days per month (as floats)
    MONTHLY_DAY = [31.0, 28.25, 31.0, 30.0, 31.0, 30.0, 31.0, 31.0, 30.0, 31.0, 30.0, 31.0]

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot

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
        if member is None: member = inter.author # set member to interaction author if not set
        aid = str(member.id) # get member id
        try:
            # get the member roll count
            if aid in self.bot.data.save['spark']:
                s = self.bot.data.save['spark'][aid] # s is the spark data: [crystals, singles, tens, modified timestamp]
                if s[0] < 0 or s[1] < 0 or s[2] < 0 or s[3] < 0: # check for negative numbers
                    raise Exception('Negative numbers')
                r = (s[0] / 300) + s[1] + s[2] * 10 + s[3] # calculate roll
                fr = math.floor(r) # round it
                timestamp = s[4] # timestamp of when it was modified
            else: # no data, we set it to 0
                r = 0
                fr = 0
                s = None
                timestamp = None

            # Estimate next spark from timestamp
            t_max, t_min, expected, now = self._estimate(r, timestamp)
            # Roll count text
            title = "{} has {} roll".format(member.display_name, fr)
            if fr != 1: title += "s" # plural if the count is different from 1
            # Sending
            if s is None:
                await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':member.display_avatar}, description="Update your rolls with the `/spark set` command", footer="Next spark between {} and {} from 0 rolls".format(t_max.strftime("%y/%m/%d"), t_min.strftime("%y/%m/%d")), color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':member.display_avatar}, description="**{} {} {} {} {} {} {}**\n*Expecting {} to {} rolls in {}*".format(self.bot.emote.get("crystal"), s[0], self.bot.emote.get("singledraw"), s[1], self.bot.emote.get("tendraw"), s[2], ("" if s[3] == 0 else "{} {}".format(self.bot.emote.get("shrimp"), s[3])),expected[0], expected[1], now.strftime("%B")), footer="Next spark between {} and {}".format(t_max.strftime("%y/%m/%d"), t_min.strftime("%y/%m/%d")), timestamp=timestamp, color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[SPARK] 'seeRoll' error:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Critical Error", description="I warned my owner", color=self.COLOR, footer=str(e)))

    """set_callback()
    CustomModal callback
    """
    async def set_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        try:
            # Retrieve user entries
            crystal = int(inter.text_values['crystal'])
            single = int(inter.text_values['single'])
            ten = int(inter.text_values['ten'])
            shrimp = int(inter.text_values['shrimp'])
            # Check validity
            if crystal < 0 or single < 0 or ten < 0 or shrimp < 0:
                raise Exception('Negative Number Error')
            if crystal >= 600000:
                raise Exception('Big Number Error')
            # User id
            aid = str(inter.author.id)
            # If total equals 0, just remove data to save space
            if crystal + single + ten + shrimp == 0: 
                if aid in self.bot.data.save['spark']:
                    self.bot.data.save['spark'].pop(aid)
            else: # else, add data for this user
                self.bot.data.save['spark'][aid] = [crystal, single, ten, shrimp, self.bot.util.UTC()]
            self.bot.data.pending = True
            # Call see roll to display the result
            await self._seeroll(inter, inter.author)
        except Exception as e:
            await inter.response.send_message(embed=self.bot.embed(title="Error", description="Your entered an invalid number.", footer=str(e), color=self.COLOR), ephemeral=True)

    @spark.sub_command()
    async def set(self, inter: disnake.GuildCommandInteraction) -> None:
        """Set your roll count"""
        data = self.bot.data.save['spark'].get(str(inter.author.id), [0, 0, 0, 0, None])
        await self.bot.singleton.make_and_send_modal(inter, "spark_set-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Set your Spark Data", self.set_callback, [
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
        - t_max: Earliest time for a spark
        - t_min: Max time for a spark
        - expected: Expected number of rolls during the start month
        - now: start time (set to current time if timestamp is None)
    """
    def _estimate(self, r : int, timestamp : Optional[datetime]) -> tuple:
        # from january to december

        # Get the current day
        if timestamp is None: # If no given timestamp, use today date
            now = self.bot.util.UTC().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        else:
            now = timestamp.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        # Timestamps (low and high)
        t_max = now
        t_min = now
        # Rolls (low and high) modulo 300
        r_max = r % 300
        r_min = r_max
        # Expected rolls (low and high) for the current month
        expected = [self.MONTHLY_MIN[now.month-1], self.MONTHLY_MAX[now.month-1]]
        # Loop until both r_min and r_max reach 300
        while r_max < 300 or r_min < 300:
            # For both min and max, we increase the respective timestamp by one day
            # and increase the roll count by the monthly gain / number of days in that month
            # and repeat until we reach 300
            if r_max < 300:
                m = (t_max.month-1) % 12
                r_max += self.MONTHLY_MAX[m] / self.MONTHLY_DAY[m]
                t_max += timedelta(days=1)
            if r_min < 300:
                m = (t_min.month-1) % 12
                r_min += self.MONTHLY_MIN[m] / self.MONTHLY_DAY[m]
                t_min += timedelta(days=1)
        return t_max, t_min, expected, now

    @spark.sub_command()
    async def see(self, inter: disnake.GuildCommandInteraction, member : disnake.Member = None) -> None:
        """Post your (or the target) roll count"""
        await self._seeroll(inter, member)

    @spark.sub_command()
    async def zero(self, inter: disnake.GuildCommandInteraction, day_difference: int = commands.Param(description="Add a number of days to today date", ge=0, default=0)) -> None:
        """Post a spark estimation based on today date"""
        try:
            await inter.response.defer(ephemeral=True)
            t_max, t_min, expected, now = self._estimate(0, self.bot.util.UTC().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=day_difference))
            # roll count text
            await inter.edit_original_message(embed=self.bot.embed(title='{} Spark estimation from {} rolls at {}'.format(self.bot.emote.get("crystal"), day_difference, now.strftime("%y/%m/%d")), description="Next spark between {} and {}\n*Expecting {} to {} rolls in {}*".format(t_max.strftime("%y/%m/%d"), t_min.strftime("%y/%m/%d"), expected[0], expected[1], now.strftime("%B")), color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Critical Error", description="I warned my owner", color=self.COLOR, footer=str(e)))
            self.bot.logger.pushError("[SPARK] In 'spark zero' command:", e)

    @spark.sub_command()
    async def nickname(self, inter: disnake.GuildCommandInteraction) -> None:
        """Update your nickname with your number of rolls""" 
        await inter.response.defer(ephemeral=True)
        aid = str(inter.author.id) # author id as a string
        # do various permission checks
        if not inter.channel.permissions_for(inter.me).manage_nicknames:
            await inter.edit_original_message(embed=self.bot.embed(title="I lack the Manage Nickname permission for this feature", color=self.COLOR))
        elif inter.channel.permissions_for(inter.me).administrator:
            await inter.edit_original_message(embed=self.bot.embed(title="Sorry, administrator nicknames can't be edited", color=self.COLOR))
        elif inter.guild.owner_id == inter.author.id:
            await inter.edit_original_message(embed=self.bot.embed(title="Sorry, server owner nicknames can't be edited", color=self.COLOR))
        elif aid not in self.bot.data.save['spark']:
            await inter.edit_original_message(embed=self.bot.embed(title="No data in memory, please set your roll count first", color=self.COLOR))
        else: # all good it seems
            # retrieve and calculate user spark
            s = self.bot.data.save['spark'][aid]
            r = (s[0] / 300) + s[1] + s[2] * 10 + s[3]
            fr = math.floor(r)
            mr = 300
            while mr < fr:
                mr += 300
            # search with a regex if the roll count is already in the user nickname and remove it
            n = self.NICKNAME_REGEX.sub('({}/{})'.format(fr, mr), inter.author.display_name)
            m = await inter.guild.get_or_fetch_member(inter.author.id) # fetch the author member object in the guild
            if n == inter.author.display_name: # if name has no rolls, add it
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
    """
    async def _ranking(self, inter: disnake.GuildCommandInteraction, guild : disnake.Guild) -> None:
        ranking = {}
        for iid, s in self.bot.data.save['spark'].items(): # go over the spark data
            if self.bot.ban.check(iid, self.bot.ban.SPARK): # if user is banned, skip
                continue
            m = await guild.get_or_fetch_member(int(iid)) # try to fetch user in given guild
            if m is not None: # user IS in the guild
                if s[0] < 0 or s[1] < 0 or s[2] < 0 or s[3] < 0: # check for negative numbers
                    continue
                r = (s[0] / 300) + s[1] + s[2] * 10 + s[3] # calculate roll
                if r > 1800: # skip user if over 6 sparks
                    continue
                ranking[iid] = r # add user to ranking
        if len(ranking) == 0: # no one in the ranking, skip
            return None, None, None
        ar = -1 # author position in the ranking
        i = 0
        emotes = {0:self.bot.emote.get('SSR'), 1:self.bot.emote.get('SR'), 2:self.bot.emote.get('R')} # emotes used for the top 3
        msgs = []
        # go over sorted ranking (in reverse order by roll count
        for key, value in sorted(ranking.items(), key = itemgetter(1), reverse = True):
            if i < self.TOP_LIMIT: # add to list if under top limit constant
                fr = math.floor(value) # round value
                msgs.append("**#{:<2}{} {}** with {} roll".format(i+1, emotes.pop(i, "▫️"), (await guild.get_or_fetch_member(int(key))).display_name, fr))
                if fr != 1:
                    msgs.append("s")
                msgs.append("\n")
            if key == str(inter.author.id): # if this user is the author, set ar
                ar = i
                if i >= self.TOP_LIMIT: break # if we're over the limit, we can stop looping now, more is pointless
            i += 1
            if i >= 100: # stop at 100 users
                break
        return "".join(msgs), ar

    @spark.sub_command()
    async def ranking(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the ranking of everyone saving for a spark in the server"""
        try:
            await inter.response.defer()
            guild = inter.author.guild
            msg, ar = await self._ranking(inter, guild) # get ranking text
            if msg is None:
                await inter.edit_original_message(embed=self.bot.embed(title="The ranking of this server is empty", color=self.COLOR))
                return
            # Add user position in the ranking if known
            if ar >= self.TOP_LIMIT: footer = "You are ranked #{}".format(ar+1)
            else: footer = ""
            # get icon url if it exists
            try: icon = guild.icon.url
            except: icon = None
            # send message
            await inter.edit_original_message(embed=self.bot.embed(title="{} Spark ranking of {}".format(self.bot.emote.get('crown'), guild.name), color=self.COLOR, description=msg, footer=footer, thumbnail=icon))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Sorry, something went wrong :bow:", footer=str(e), color=self.COLOR))
            self.bot.logger.pushError("[SPARK] In 'spark ranking' command:", e)
        await self.bot.channel.clean(inter, 40)

    @commands.user_command(name="GBF Spark")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 40, commands.BucketType.user)
    @commands.max_concurrency(4, commands.BucketType.default)
    async def seespark(self, inter: disnake.UserCommandInteraction, member: disnake.Member) -> None:
        """Post the user roll count"""
        await self._seeroll(inter, member)