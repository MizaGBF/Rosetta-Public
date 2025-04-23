from __future__ import annotations
import disnake
from disnake.ext import commands
import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.network import RequestResult
    from components.singleton import Score
    from components.ranking import GWDBSearchResult, GWDBList
    from views.page import PageResult, PageResultList
    # Type Aliases
    type PlayerData = dict[str, str|int|None]
    type CrewData = dict[str, str|datetime|bool|list[PlayerData]]
    type ScheduleDay = tuple[str, str, str]
    type ScheduleList = list[ScheduleDay]
    type PlayerData = dict[str, int|str|float|Score|None]
    type PlayerList = list[PlayerData]
    type CrewParameter = datetime|bool|str|int|float|PlayerList|None
    type CrewData = dict[str, CrewParameter]
    type GBFGData = dict[str, list[str|int|list[str|int]]]
    type PlayerEntry = tuple[str, str, int|None, str, int|None]
    type PlayerRanking = list[PlayerEntry]
from views import BaseView
from views.page import Page, PageRanking
import random
import math
from bs4 import BeautifulSoup
from bs4 import element as bs4element
import html
from urllib.parse import unquote
import statistics

# ----------------------------------------------------------------------
# Guild War Cog
# ----------------------------------------------------------------------
# Commands related to Unite and Fight and Granblue Fantasy Crews
# ----------------------------------------------------------------------


class GuildWar(commands.Cog):
    """Unite & Fight and Crew commands."""
    COLOR : int = 0xff0000
    FIGHTS : dict[str, dict[str, float|int]] = {
        "EX": {
            "token":56.0, "rally_token":3.84,
            "AP":30, "clump_drop":0, "meat_cost":0,
            "clump_cost":0, "honor":64000, "hp":20000000
        },
        "EX+": {
            "token":66.0, "rally_token":7.56,
            "AP":30, "clump_drop":0, "meat_cost":0,
            "clump_cost":0, "honor":126000, "hp":35000000
        },
        "NM90": {
            "token":83.0, "rally_token":18.3,
            "AP":30, "clump_drop":1.3, "meat_cost":5,
            "clump_cost":0, "honor":305000, "hp":50000000
        },
        "NM95": {
            "token":111.0, "rally_token":54.6,
            "AP":40, "clump_drop":1.4, "meat_cost":10,
            "clump_cost":0, "honor":910000, "hp":131250000
        },
        "NM100": {
            "token":168.0, "rally_token":159.0,
            "AP":50, "clump_drop":1.6, "meat_cost":20,
            "clump_cost":0, "honor":2650000, "hp":288750000
        },
        "NM150": {
            "token":257.0, "rally_token":246.0,
            "AP":50, "clump_drop":1.8, "meat_cost":20,
            "clump_cost":0, "honor":4100000, "hp":288750000
        },
        "NM200": {
            "token":338.0, "rally_token":800.98,
            "AP":50, "clump_drop":2, "meat_cost":20,
            "clump_cost":0, "honor":13350000, "hp":577500000
        },
        "NM250": {
            "token":433.0, "rally_token":2122.6,
            "AP":50, "clump_drop":0, "meat_cost":0,
            "clump_cost":20, "honor":49500000, "hp":1530375000
        }
    }
    MEAT_PER_BATTLE_AVG : int = 21 # EX+ meat drop
    BOX_COST : tuple[int|None, int] = [
        (1, 1600),
        (4, 2400),
        (45, 2000),
        (80, 10000),
        (None, 15000)
    ]
    DAYS_W_INTER : list[str] = ['Interlude', 'Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5']

    def __init__(self : GuildWar, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.day_list : ScheduleList|None = None
        self.crewcache : CrewData = {}

    """buildDayList()
    Generate the day list used by the gw command

    Returns
    --------
    list: List of lists containing: The day string, the day key and the next day key
    """
    def buildDayList(self : GuildWar) -> ScheduleList: # used by the gw schedule command
        if self.day_list is None:
            self.day_list = [
                ("{} Automatic BAN Execution".format(self.bot.emote.get('kmr')), "BW", ""), # a joke, for memes
                ("{} Preliminaries".format(self.bot.emote.get('gold')), "Preliminaries", "Interlude"),
                ("{} Interlude".format(self.bot.emote.get('wood')), "Interlude", "Day 1"),
                ("{} Day 1".format(self.bot.emote.get('1')), "Day 1", "Day 2"),
                ("{} Day 2".format(self.bot.emote.get('2')), "Day 2", "Day 3"),
                ("{} Day 3".format(self.bot.emote.get('3')), "Day 3", "Day 4"),
                ("{} Day 4".format(self.bot.emote.get('4')), "Day 4", "Day 5"),
                ("{} Final Rally".format(self.bot.emote.get('red')), "Day 5", "End")
            ]
        return self.day_list

    """isGWRunning()
    Check the GW state and returns if the GW is on going.
    Clear the data if it ended.

    Returns
    --------
    bool: True if it's running, False if it's not
    """
    def isGWRunning(self : GuildWar) -> bool:
        if self.bot.data.save['gw']['state'] is True:
            current_time : datetime = self.bot.util.JST()
            if current_time < self.bot.data.save['gw']['dates']["Preliminaries"]: # not started
                return False
            elif current_time >= self.bot.data.save['gw']['dates']["End"]: # ended
                self.bot.data.save['gw']['state'] = False
                self.bot.data.save['gw']['dates'] = {}
                try:
                    self.bot.get_cog('YouCrew').setBuffTask(False)
                except:
                    pass
                self.bot.data.pending = True
                return False
            else: # running
                return True
        else:
            return False

    """escape()
    Proper markdown escape for player names

    Parameters
    ----------
    s: String to escape
    lite: If True, less escapes are applied

    Returns
    --------
    str: Escaped string
    """
    def escape(self : GuildWar, s : str, lite : bool = False) -> str:
        # add the RLO character before
        x : str = html.unescape(s)
        if lite:
            return '\u202d' + x.replace(
                '\\', '\\\\'
            ).replace(
                '`', '\\`'
            )
        else:
            return '\u202d' + x.replace(
                '\\', '\\\\'
            ).replace(
                '`', '\''
            ).replace(
                '*', '\\*'
            ).replace(
                '_', '\\_'
            ).replace(
                '{', '\\{'
            ).replace(
                '}', '\\}'
            ).replace(
                '[', ''
            ).replace(
                ']', ''
            ).replace(
                '(', '\\('
            ).replace(
                ')', '\\)'
            ).replace(
                '#', '\\#'
            ).replace(
                '+', '\\+'
            ).replace(
                '-', '\\-'
            ).replace(
                '.', '\\.'
            ).replace(
                '!', '\\!'
            ).replace(
                '|', '\\|'
            )

    """htmlescape()
    Escape special characters into html notation (used for crew and player names)

    Parameters
    ----------
    s: String to escape

    Returns
    --------
    str: Escaped string
    """
    def htmlescape(self : GuildWar, s : str) -> str:
        return s.replace(
            "&", "&amp;"
        ).replace(
            "<", "&lt;"
        ).replace(
            ">", "&gt;"
        ).replace(
            '"', "&quot;"
        ).replace(
            '\'', "&#039;"
        )

    """dayCheck()
    Check if we are in the specified GW day

    Parameters
    ----------
    current: Current time, JST
    day: Day to compare to
    final_day: If True, check for the final GW day (it's shorter)

    Returns
    --------
    bool: True if successful, False if not
    """
    def dayCheck(self : GuildWar, current : datetime, day : datetime, final_day : bool = False) -> bool:
        d : timedelta = day - current
        if current < day and (final_day or d >= timedelta(seconds=25200)):
            return True
        return False

    """getGWState()
    Return the state of the Unite & Fight event

    Returns
    --------
    str: Unite & Fight state
    """
    def getGWState(self : GuildWar) -> str:
        if self.bot.data.save['gw']['state'] is True:
            current_time : datetime = self.bot.util.JST()
            d : timedelta
            msg : str
            if current_time < self.bot.data.save['gw']['dates']["Preliminaries"]: # not started
                d = self.bot.data.save['gw']['dates']["Preliminaries"] - current_time
                return "{} Guild War starts in **{}**".format(self.bot.emote.get('gw'), self.bot.util.delta2str(d, 2))
            elif current_time >= self.bot.data.save['gw']['dates']["End"]: # ended
                # clear data
                self.bot.data.save['gw']['state'] = False
                self.bot.data.save['gw']['dates'] = {}
                try:
                    self.bot.get_cog('YouCrew').setBuffTask(False)
                except:
                    pass
                self.bot.data.save['youtracker'] = None
                self.bot.data.pending = True
                return ""
            elif current_time > self.bot.data.save['gw']['dates']["Day 5"]: # Day 5 is now the final rally
                d = self.bot.data.save['gw']['dates']["End"] - current_time
                return "{} Final Rally is on going\n{} Guild War ends in **{}**".format(
                    self.bot.emote.get('mark_a'),
                    self.bot.emote.get('time'),
                    self.bot.util.delta2str(d)
                )
            elif current_time > self.bot.data.save['gw']['dates']["Day 1"]: # If in between day 1 included and day 5
                i : int
                for i in range(1, len(self.bot.ranking.REVERSE_DAYS)): # Loop from day 4 to 1
                    if current_time > self.bot.data.save['gw']['dates'][self.bot.ranking.REVERSE_DAYS[i]]:
                        # if over this day date
                        d = self.bot.data.save['gw']['dates'][self.bot.ranking.REVERSE_DAYS[i - 1]] - current_time
                        # calculate if this day match ended and the end to next day
                        if d < timedelta(seconds=25200):
                            msg = "{} {} ended".format(self.bot.emote.get('mark_a'), self.bot.ranking.REVERSE_DAYS[i])
                        else:
                            msg = "{} GW {} is on going (Time left: **{}**)".format(
                                self.bot.emote.get('mark_a'),
                                self.bot.ranking.REVERSE_DAYS[i],
                                self.bot.util.delta2str(
                                    self.bot.data.save['gw']['dates'][self.bot.ranking.REVERSE_DAYS[i]]
                                    + timedelta(seconds=61200) - current_time
                                )
                            )
                        if i == 1:
                            return "{}\n{} {} starts in **{}**".format(
                                msg,
                                self.bot.emote.get('time'),
                                self.bot.ranking.REVERSE_DAYS[i - 1].replace('Day 5', 'Final Rally'),
                                self.bot.util.delta2str(d)
                            )
                        else:
                            return "{}\n{} {} starts in **{}**".format(
                                msg,
                                self.bot.emote.get('time'),
                                self.bot.ranking.REVERSE_DAYS[i - 1],
                                self.bot.util.delta2str(d)
                            )
            elif current_time > self.bot.data.save['gw']['dates']["Interlude"]: # interlude is on going
                d = self.bot.data.save['gw']['dates']["Day 1"] - current_time
                return "{} Interlude is on going\n{} Day 1 starts in **{}**".format(
                    self.bot.emote.get('mark_a'),
                    self.bot.emote.get('time'),
                    self.bot.util.delta2str(d)
                )
            elif current_time > self.bot.data.save['gw']['dates']["Preliminaries"]: # prelim on going
                d = self.bot.data.save['gw']['dates']['Interlude'] - current_time
                if d < timedelta(seconds=25200):
                    msg = "{} Preliminaries ended".format(self.bot.emote.get('mark_a'))
                else:
                    msg = "{} Preliminaries are on going (Time left: **{}**)".format(
                        self.bot.emote.get('mark_a'),
                        self.bot.util.delta2str(
                            self.bot.data.save['gw']['dates']["Preliminaries"]
                            + timedelta(seconds=104400) - current_time,
                            2
                        )
                    )
                return "{}\n{} Interlude starts in **{}**".format(
                    msg,
                    self.bot.emote.get('time'),
                    self.bot.util.delta2str(d, 2)
                )
            else:
                return ""
        else:
            return ""

    """getGWTimeLeft()
    Return the time left until the next unite & fight day.
    Similar to getGWState except we return the time remaining to the next GW day.

    Parameters
    --------
    current_time: Optional datetime

    Returns
    --------
    timedelta: Time left or None if error
    """
    def getGWTimeLeft(self : GuildWar, current_time : datetime|None = None) -> timedelta|None:
        if self.bot.data.save['gw']['state'] is False:
            return None
        if current_time is None:
            current_time = self.bot.util.JST()
        if (current_time < self.bot.data.save['gw']['dates']["Preliminaries"]
                or current_time >= self.bot.data.save['gw']['dates']["Day 5"]):
            return None
        elif current_time > self.bot.data.save['gw']['dates']["Day 1"]:
            for i in range(1, len(self.bot.ranking.REVERSE_DAYS)): # loop to not copy paste this 5 more times
                if current_time > self.bot.data.save['gw']['dates'][self.bot.ranking.REVERSE_DAYS[i]]:
                    if (self.bot.data.save['gw']['dates'][self.bot.ranking.REVERSE_DAYS[i - 1]]
                            - current_time < timedelta(seconds=25200)):
                        return None
                    return (
                        self.bot.data.save['gw']['dates'][self.bot.ranking.REVERSE_DAYS[i]]
                        + timedelta(seconds=61200)
                        - current_time
                    )
            return None
        elif current_time > self.bot.data.save['gw']['dates']["Interlude"]:
            return self.bot.data.save['gw']['dates']["Day 1"] - current_time
        elif current_time > self.bot.data.save['gw']['dates']["Preliminaries"]:
            if self.bot.data.save['gw']['dates']["Interlude"] - current_time < timedelta(seconds=25200):
                return None
            return self.bot.data.save['gw']['dates']["Preliminaries"] + timedelta(seconds=104400) - current_time
        return None

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 20, commands.BucketType.user)
    @commands.max_concurrency(16, commands.BucketType.default)
    async def gw(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @gw.sub_command()
    async def time(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the GW schedule"""
        await inter.response.defer()
        if self.bot.data.save['gw']['state'] is True: # read gw data and make a schedule
            try:
                current_time = self.bot.util.JST()
                em : str = self.bot.util.formatElement(self.bot.data.save['gw']['element'])
                # element (to add in the title)
                title : str = "{} **Guild War {}** {} **{}**\n".format(
                    self.bot.emote.get('gw'),
                    self.bot.data.save['gw']['id'],
                    em,
                    self.bot.util.time(current_time, removejst=True)
                )
                description : list[str] = []
                day_list : ScheduleList = self.buildDayList() # retrieve list
                if current_time < self.bot.data.save['gw']['dates']["End"]:
                    day : ScheduleDay
                    for day in day_list:
                        if day[1] == "BW": # banwave joke
                            d : timedelta = (
                                self.bot.data.save['gw']['dates']["Preliminaries"]
                                - timedelta(days=random.randint(1, 4))
                            )
                            if current_time < d and random.randint(1, 8) == 1:
                                # randomly appear, 12.5% of the time,if we're at least 1 to 4 days before GW
                                description.append(day[0] + " **{}**\n".format(self.bot.util.time(d, removejst=True)))
                        else: # simply add days if they are upcoming or on going
                            if (self.dayCheck(
                                    current_time, self.bot.data.save['gw']['dates'][day[2]],
                                    day[1] == "Day 5"
                            ) or (day[1] == "Interlude"
                                    and self.dayCheck(
                                        current_time,
                                        self.bot.data.save['gw']['dates'][day[2]]
                                        + timedelta(seconds=25200),
                                        False))):
                                description.append(
                                    day[0] + ": **{}**\n".format(
                                        self.bot.util.time(
                                            self.bot.data.save['gw']['dates'][day[1]],
                                            removejst=True
                                        )
                                    )
                                )
                else:
                    # clear data if not on going
                    self.bot.data.save['gw']['state'] = False
                    self.bot.data.save['gw']['dates'] = {}
                    try:
                        self.bot.get_cog('YouCrew').setBuffTask(False)
                    except:
                        pass
                    self.bot.data.save['youtracker'] = None
                    self.bot.data.pending = True
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="{} **Guild War**".format(
                                self.bot.emote.get(
                                    'gw'
                                )
                            ),
                            description="Not available",
                            color=self.COLOR
                        )
                    )
                    await self.bot.channel.clean(inter, 40)
                    return
                # add additional infos
                try:
                    description.append(self.getGWState())
                except:
                    pass

                try:
                    description.append('\n' + self.bot.get_cog('YouCrew').getNextBuff(inter))
                except:
                    pass

                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title=title,
                        description=''.join(description),
                        color=self.COLOR
                    )
                )
            except Exception as e:
                self.bot.logger.pushError("[GW] In 'gw time' command:", e)
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description="An unexpected error occured",
                        color=self.COLOR
                    )
                )
        else:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} **Guild War**".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="Not available",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)

    @gw.sub_command(name="ranking")
    async def gwranking(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Retrieve the current GW ranking"""
        try:
            await inter.response.defer()
            if (self.bot.data.save['gw']['state'] is False
                    or self.bot.util.JST() < self.bot.data.save['gw']['dates']["Preliminaries"]
                    or self.bot.data.save['gw']['ranking'] is None):
                await inter.edit_original_message(embed=self.bot.embed(title="Ranking unavailable", color=self.COLOR))
            else:
                fields : list[dict[str, str|list]] = [
                    {
                        'name':'**Crew Ranking**',
                        'value':[]
                    },
                    {
                        'name':'**Player Ranking**',
                        'value':[]
                    }
                ]
                x : int
                for x in (0, 1): # crew then player
                    rank : str
                    for rank in self.bot.data.save['gw']['ranking'][x]: # go over each entry
                        # different display depending on if the ranking is lesser than 1000,
                        # a non-round number (example, 2500 for 2.5k) or above 1000
                        if int(rank) < 1000:
                            fields[x]['value'].append(
                                "**#{:}** - {:,}".format(
                                    rank,
                                    self.bot.data.save['gw']['ranking'][x][rank]
                                )
                            )
                        elif int(rank) % 1000 != 0:
                            fields[x]['value'].append(
                                "**#{:,}.{:,}K** - {:,}".format(
                                    int(rank) // 1000,
                                    (int(rank) % 1000) // 100,
                                    self.bot.data.save['gw']['ranking'][x][rank]
                                )
                            )
                        else:
                            fields[x]['value'].append(
                                "**#{:,}K** - {:,}".format(
                                    int(rank) // 1000,
                                    self.bot.data.save['gw']['ranking'][x][rank]
                                )
                            )
                        # add speed
                        if (rank in self.bot.data.save['gw']['ranking'][2 + x]
                                and self.bot.data.save['gw']['ranking'][2 + x][rank] != 0):
                            fields[x]['value'].append(
                                " - {}/min".format(
                                    self.bot.util.valToStr(self.bot.data.save['gw']['ranking'][2 + x][rank])
                                )
                            )
                        fields[x]['value'].append("\n")
                    if len(fields[x]['value']) == 0: # no valid data check
                        fields[x]['value'] = 'Unavailable'
                    else:
                        fields[x]['value'] = "".join(fields[x]['value'])
                em : str = self.bot.util.formatElement(self.bot.data.save['gw']['element']) # gw element
                d : timedelta = self.bot.util.JST() - self.bot.data.save['gw']['ranking'][4] # time elapsed
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="{} **Guild War {}** {}".format(
                            self.bot.emote.get('gw'),
                            self.bot.data.save['gw']['id'],
                            em
                        ),
                        description="Updated: **{}** ago".format(
                            self.bot.util.delta2str(
                                d,
                                0
                            )
                        ),
                        fields=fields,
                        footer="Update on minute 5, 25 and 45",
                        timestamp=self.bot.util.UTC(),
                        inline=True,
                        color=self.COLOR
                    )
                )
        except Exception as e:
            self.bot.logger.pushError("[GW] In 'gw ranking' command:", e)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An unexpected error occured",
                    color=self.COLOR
                )
            )

    @gw.sub_command()
    async def estimation(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Estimatation of the GW ranking cutoffs"""
        await inter.response.defer()
        current_time : datetime = self.bot.util.JST()
        if (self.bot.data.save['gw']['state'] is False
                or current_time < self.bot.data.save['gw']['dates']["Preliminaries"]
                or current_time >= (self.bot.data.save['gw']['dates']["Day 5"] - timedelta(seconds=25200))
                or self.bot.data.save['gw']['ranking'] is None
                or 'estimation' not in self.bot.data.save['gw']):
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Estimation unavailable",
                    description="",
                    color=self.COLOR
                )
            )
        else:
            update_time : datetime = self.bot.data.save['gw']['ranking'][4]
            elapsed_seconds : int = int(
                (
                    update_time
                    - self.bot.data.save['gw']['dates']['Preliminaries']
                ).total_seconds()
            )
            if elapsed_seconds < 1200: # too early, estimation starts at least 20min after the start of prelims
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Estimation unavailable",
                        description="Try again in a little while",
                        color=self.COLOR
                    )
                )
            else:
                try:
                    i : int
                    # calculate our index in estimation table based on current time
                    index : int = (elapsed_seconds - 1200) // 1200
                    # Note: The ranking updates every 20min and the wiki table is pretty much
                    # a big array of scores for every 20 minutes updates.
                    mods : list[dict[str, float]] = [{}, {}] # modifier container
                    rank : str
                    for i in (0, 1): # crew, player
                        for rank in self.bot.data.save['gw']['ranking'][i]: # for each current store stored
                            try:
                                if rank not in self.bot.data.save['gw']['estimation'][i]:
                                    # check if rank exists in the wiki data, else continue
                                    continue
                                # calculate the multiplier between today and last gw data from the wiki
                                mods[i][rank] = (
                                    self.bot.data.save['gw']['ranking'][i][rank]
                                    / self.bot.data.save['gw']['estimation'][i][rank][index]
                                )
                            except:
                                pass
                    embeds : list[disnake.Embed] = []
                    final : int
                    for final in (0, 1): # current day end, gw end
                        # get the final value of the day/gw (depending on final)
                        # Note: current_time_left is the time left to the target_index
                        # while target_index is the index of the final value in the wiki table
                        target_index : int = -1
                        current_time_left : timedelta
                        if final == 1 or update_time >= self.bot.data.save['gw']['dates']['Day 4']: # final day or end
                            current_time_left = (
                                self.bot.data.save['gw']['dates']['Day 5']
                                - timedelta(seconds=25200)
                                - current_time
                            )
                            target_index = -1
                        else: # other days
                            d : str
                            for d in self.DAYS_W_INTER :
                                if update_time < self.bot.data.save['gw']['dates'][d]:
                                    current_time_left = self.bot.data.save['gw']['dates'][d] - current_time
                                    target_index = (
                                        (
                                            int((
                                                self.bot.data.save['gw']['dates'][d]
                                                - self.bot.data.save['gw']['dates']['Preliminaries']
                                            ).total_seconds())
                                            - 1200
                                        )
                                        // 1200
                                    )
                                    break
                        fields : list[dict[str, str|list]] = [
                            {
                                'name':'**Crew Ranking**',
                                'value':[]
                            },
                            {
                                'name':'**Player Ranking**',
                                'value':[]
                            }
                        ]
                        for i in (0, 1): # crew, player
                            for rank in mods[i]: # for each rank we have a mod for
                                # different display depending on if the ranking is lesser than 1000,
                                # a non-round number (example, 2500 for 2.5k) or above 1000
                                if int(rank) < 1000:
                                    fields[i]['value'].append("**#{}** ▫️ ".format(rank))
                                elif int(rank) % 1000 != 0:
                                    fields[i]['value'].append(
                                        "**#{}.{}K** ▫️ ".format(
                                            int(rank) // 1000,
                                            (int(rank) % 1000) // 100
                                        )
                                    )
                                else:
                                    fields[i]['value'].append("**#{}K** ▫️ ".format(int(rank) // 1000))
                                # applu the multiplier to the final value to have a projection
                                try:
                                    fields[i]['value'].append(
                                        "{} (".format(
                                            self.bot.util.valToStr(
                                                (
                                                    self.bot.data.save['gw']['estimation'][i][rank][target_index]
                                                    * mods[i][rank]
                                                ),
                                                2
                                            )
                                        )
                                    )
                                    # add % to text
                                    mod : float = mods[i][rank] - 1
                                    if mod > 0:
                                        fields[i]['value'].append("+")
                                    fields[i]['value'].append("{:.1f}%)\n".format(mod * 100))
                                except:
                                    pass
                            if len(fields[i]['value']) == 0: # no data check
                                fields[i]['value'] = "Unavailable"
                            else:
                                fields[i]['value'] = "".join(fields[i]['value'])
                        msgs : list[str]
                        if current_time_left.total_seconds() < 0:
                            # check or negative time (shouldn't happen)
                            msgs = []
                        else:
                            # add time remaining
                            timestring : str
                            if current_time_left.days > 0:
                                timestring = self.bot.util.delta2str(current_time_left, 2)
                            else:
                                timestring = self.bot.util.delta2str(current_time_left, 1)
                            if target_index == -1:
                                msgs = ["Time left: **{}** ▫️ ".format(timestring)]
                            else:
                                msgs = ["Next Day: **{}** ▫️ ".format(timestring)]
                        # add time elapsed since last update
                        msgs.append(
                            "Updated: **{}** ago\n".format(
                                self.bot.util.delta2str(
                                    current_time - update_time,
                                    0
                                )
                            )
                        )
                        # finalize embed for this day
                        title : str
                        if target_index == -1:
                            msgs.append("**Ending** ")
                            title = "Ending Estimation"
                        else:
                            msgs.append("**Today** ")
                            title = "Today Estimation"
                        msgs.append("projection, always **take it with a grain of salt**")
                        embeds.append(
                            self.bot.embed(
                                title="{} **Guild War {} {} {}**".format(
                                    self.bot.emote.get('gw'),
                                    self.bot.data.save['gw']['id'],
                                    self.bot.util.formatElement(self.bot.data.save['gw']['element']),
                                    title
                                ),
                                description="".join(msgs),
                                fields=fields,
                                footer="https://gbf.wiki/User:Neofaucheur/Unite_and_Fight_Data",
                                timestamp=self.bot.util.UTC(),
                                inline=True,
                                color=self.COLOR
                            )
                        )
                        if target_index == -1:
                            break
                    if len(embeds) == 0:
                        await inter.edit_original_message(
                            embed=self.bot.embed(
                                title="Estimation unavailable",
                                description="",
                                color=self.COLOR
                            )
                        )
                    elif len(embeds) > 1:
                        view : Page = Page(self.bot, owner_id=inter.author.id, embeds=embeds, timeout=100)
                        await inter.edit_original_message(embed=embeds[0], view=view)
                        view.message = await inter.original_message()
                    else:
                        await inter.edit_original_message(embed=embeds[0])
                except Exception as e:
                    self.bot.logger.pushError("[GW] In 'estimation' command:", e)
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="Estimation unavailable",
                            description="",
                            color=self.COLOR
                        )
                    )

    """getCrewSummary()
    Get a GBF crew summary (what you see on the main page of a crew)

    Parameters
    ----------
    cid: Crew id

    Returns
    --------
    dict: Crew data, empty if error or invalid
    """
    async def getCrewSummary(self : GuildWar, cid : int) -> CrewData:
        res : RequestResult = await self.bot.net.requestGBF(
            "guild_main/content/detail/{}".format(cid),
            expect_JSON=True
        )
        if res is not None:
            soup : BeautifulSoup = BeautifulSoup(unquote(res['data']), 'html.parser')
            try:
                summary : bs4element.ResultSet = soup.find_all(
                    "div",
                    class_="prt-status-summary"
                )[0].findChildren(
                    "div",
                    class_="prt-status-value",
                    recursive=True
                )
                return {
                    'count':int(summary[0].string), # member count
                    'average':int(summary[1].string), # avg rank
                    'online':int(summary[2].string) # last online
                }
            except:
                pass
        return {}

    """clearCrewCache()
    Clear the GBF crew cache
    """
    async def clearCrewCache(self : GuildWar) -> None:
        self.crewcache = {}

    """getCrewData()
    Get a GBF crew data, including its player list if public

    Parameters
    ----------
    target: String, can be a crew id or a crew name registered in config.json
    mode: Integer: 0=all, 1=main page data only, 2=main page and summary

    Returns
    --------
    dict: Crew data, None if error
    """
    async def getCrewData(self : GuildWar, target : str, mode : int = 0) -> CrewData|None:
        if not await self.bot.net.gbf_available(): # check for maintenance
            return {'error':'Game is in maintenance'}
        # check if known id
        tid : str|int = self.bot.ranking.allconfigcrews.get(target, target)
        gwdata : None|GWDBSearchResult = None
        # check id validityy
        try:
            tid = int(tid)
        except:
            if tid == "":
                return {
                    'error':(
                        "Please input the ID or the name of the crew\n"
                        "Only some crews are registered, please input an ID instead\n"
                        "You can try {} to search for a specific crew"
                    ).format(self.bot.util.command2mention('gw find crew'))
                }
            else:
                gwdata = await self.bot.ranking.searchGWDB(tid, 11) # use ranking to try to find this crew by name
                if len(gwdata[1]) == 1:
                    tid = gwdata[1][0].id
                else:
                    return {
                        'error':(
                            "Invalid name `{}`\n"
                            "Only some crews are registered, please input an ID instead\n"
                            "You can try {} to search for a specific crew"
                        ).format(tid, self.bot.util.command2mention('gw find crew'))
                    }
        if tid < 0 or tid >= 10000000:
            return {'error':'Out of range ID'}
        # retrieve data
        crew : CrewData
        if tid in self.crewcache: # check if cached
            crew = self.crewcache[tid]
        else:
            crew = {'scores':[], 'id':tid}
            i : int
            for i in range(0, 4):
                # for each page (page 0 being the crew page, 1 to 3 being the crew page
                if i > 0 and mode > 0:
                    break
                get : RequestResult = await self.requestCrew(tid, i)
                if get is None:
                    if i == 0: # if error on page 0, the crew doesn't exist
                        return {'error':'Crew not found or Service unavailable'}
                    elif i == 1: # if error on page 1, the crew is private
                        crew['private'] = True
                    break
                else:
                    # store the data
                    if i == 0:
                        crew['timestamp'] = self.bot.util.UTC()
                        crew['footer'] = ""
                        crew['private'] = False # in preparation
                        crew['name'] = html.unescape(get['guild_name'])
                        crew['rank'] = get['guild_rank']
                        crew['ship'] = (
                            "https://prd-game-a-granbluefantasy.akamaized.net/"
                            "assets_en/img/sp/guild/thumb/top/{}.png"
                        ).format(get['ship_img'])
                        crew['ship_element'] = {
                            "10001":"wind",
                            "20001":"fire",
                            "30001":"water",
                            "40001":"earth",
                            "50001":"light",
                            "60001":"dark"
                        }.get(get['ship_img'].split('_', 1)[0], 'gw')
                        crew['leader'] = html.unescape(get['leader_name'])
                        crew['leader_id'] = get['leader_user_id']
                        crew['donator'] = html.unescape(get['most_donated_name'])
                        crew['donator_id'] = get['most_donated_id']
                        crew['donator_amount'] = get['most_donated_lupi']
                        crew['message'] = html.unescape(get['introduction'])
                        crew['player'] = []
                    else:
                        p : dict[str, str|int|float|list|dict|None]
                        for p in get['list']:
                            crew['player'].append(
                                {
                                    'id':p['id'],
                                    'name':html.unescape(p['name']),
                                    'level':p['level'],
                                    'is_leader':p['is_leader'],
                                    'member_position':p['member_position'],
                                    'honor':None
                                }
                            ) # honor is a placeholder
            if len(crew['player']) == 0:
                crew['private'] = True
            self.crewcache[tid] = crew
        if mode == 1: # main page data only, simply return
            return crew
        # get summary
        data : CrewData = await self.getCrewSummary(tid)
        k : str
        v : CrewParameter
        for k, v in data.items():
            crew[k] = v
        if mode > 0: # main page + summary, return
            return crew
        # get the up to date gw scores
        crew['scores'] = []
        if gwdata is None:
            # we perform an ID search, but only if no other search has been already performed
            gwdata = await self.bot.ranking.searchGWDB(tid, 12)
        n : int
        for n in range(0, 2): # add scores
            try:
                if gwdata[n][0].ranking is None or gwdata[n][0].day != 4:
                    crew['scores'].append(
                        "{} GW**{}** | {} | **{:,}** pts".format(
                            self.bot.emote.get('gw'),
                            gwdata[n][0].gw,
                            ('Total Day {}'.format(gwdata[n][0].day) if gwdata[n][0].day > 0 else 'Total Prelim.'),
                            gwdata[n][0].current
                        )
                    )
                else:
                    crew['scores'].append(
                        "{} GW**{}** | #**{}** | **{:,}** pts".format(
                            self.bot.emote.get('gw'),
                            gwdata[n][0].gw,
                            gwdata[n][0].ranking,
                            gwdata[n][0].current
                        )
                    )
                if gwdata[n][0].top_speed is not None:
                    crew['scores'][-1] += " | Top **{}/m.**".format(self.bot.util.valToStr(gwdata[n][0].top_speed, 2))
                if gwdata[n][0].current_speed is not None and gwdata[n][0].current_speed > 0:
                    crew['scores'][-1] += " | Last **{}/m.**".format(
                        self.bot.util.valToStr(gwdata[n][0].current_speed, 2)
                    )
            except:
                pass
        return crew

    """processCrewData()
    Process the crew data into strings for a disnake.Embed

    Parameters
    ----------
    crew: Crew data
    mode: Integer (0 = auto, 1 = player ranks, 2 = player GW contributions)

    Returns
    --------
    tuple: Containing:
        - title: Embed title (Crew name, number of player, average rank, number online)
        - description: Embed description (Crew message, Crew leaders, GW contributions)
        - fields: Embed fields (Player list)
        - footer: Embed footer (message indicating the crew is in cache, only for public crew)
        - players: Sorted Player list
    """
    async def processCrewData(
        self : GuildWar,
        crew : dict,
        mode : int = 0
    ) -> tuple[str, str, list[dict[str, str]], str, PlayerList]:
        i : int
        j : int
        # Generate Embed Title
        title : list[str] = ["\u202d"]
        title.append(str(self.bot.emote.get(crew['ship_element'])))
        title.append(" **")
        title.append(self.bot.util.shortenName(crew['name']))
        title.append("**")
        if 'count' in crew:
            title.append("▫️")
            title.append(str(crew['count']))
            title.append("/30")
        if 'average' in crew:
            title.append("▫️Rank ")
            title.append(str(crew['average']))
        if 'online' in crew:
            title.append("▫️")
            title.append(str(crew['online']))
            title.append(" online")
        # Generate Embed Description and Fields
        description : list[str] = ["💬 `{}`".format(self.escape(crew['message'], True))]
        footer : str = ""
        fields : list[dict[str, str|list]] = []

        # append GW scores if any
        s : Score
        for s in crew['scores']:
            description.append("\n{}".format(s))
        await asyncio.sleep(0)

        players : PlayerList = []
        if crew['private']:
            description.append(
                '\n{} [{}](https://game.granbluefantasy.jp/#profile/{}) ▫️ *Crew is private*'.format(
                    self.bot.emote.get('captain'),
                    crew['leader'],
                    crew['leader_id']
                )
            )
        else:
            footer = "Public crew members updated daily"
            # get GW data
            gwstate : bool
            match mode:
                case 2: gwstate = True
                case 1: gwstate = False
                case _: gwstate = self.isGWRunning()
            players = crew['player'].copy()
            gwid : int|None = None
            if gwstate:
                total : int = 0
                unranked : int = 0
                medians : list[int] = []
                # retrieve player honor
                player_list : dict[str, PlayerData] = {player['id'] : player for player in players}
                data : GWDBSearchResult|None = await self.bot.ranking.searchGWDB(
                    "(" + ",".join(list(player_list)) + ")",
                    4
                )
                await asyncio.sleep(0)
                # check data
                if data is not None and data[1] is not None:
                    honor : Score
                    for honor in data[1]: # add
                        if gwid is None:
                            gwid = honor.gw
                        total += honor.current
                        medians.append(honor.current)
                        player_list[str(honor.id)]['honor'] = honor.current
                        unranked += 1
                unranked = len(players) - unranked
                for i in range(unranked):
                    medians.append(0)
                # sorting
                for i in range(0, len(players)):
                    if i > 0 and players[i]['honor'] is not None:
                        for j in range(0, i):
                            if players[j]['honor'] is None or players[i]['honor'] > players[j]['honor']:
                                players[i], players[j] = players[j], players[i]
                # generate crew GW health indicator and stats
                if gwid and len(players) - unranked > 0:
                    average : int = total // (len(players) - unranked)
                    median : int = statistics.median(medians)
                    health : str
                    if median > average * 1.1:
                        health = ':sparkling_heart:'
                    elif median > average * 0.95:
                        health = ':heart:'
                    elif median > average * 0.75:
                        health = ':mending_heart:'
                    elif median > average * 0.5:
                        health = ':warning:'
                    elif median > average * 0.25:
                        health = ':put_litter_in_its_place:'
                    else:
                        health = ':skull_crossbones:'
                    description.append(
                        "\n{} GW**{}** | Player Sum **{}** | Avg. **{}**".format(
                            health,
                            gwid,
                            self.bot.util.valToStr(total, 2),
                            self.bot.util.valToStr(average, 2)
                        )
                    )
                    if median > 0:
                        description.append(" | Med. **{}**".format(self.bot.util.valToStr(median, 2)))
                    if unranked > 0:
                        description.append(" | **{}** n/a".format(unranked))
            # create the fields to contain players
            i = 0
            p : PlayerData
            for p in players:
                if i % 10 == 0:
                    fields.append(
                        {
                            'name':'Page {}'.format(self.bot.emote.get('{}'.format(len(fields) + 1))),
                            'value':[]}
                    )
                    await asyncio.sleep(0)
                i += 1
                r : str
                match p['member_position']: # player role
                    case "1": r = "captain"
                    case "2": r = "foace"
                    case "3": r = "atkace"
                    case "4": r = "deface"
                    case _: r = "ensign"
                fields[-1]['value'].append(str(self.bot.emote.get(r)))
                fields[-1]['value'].append(" [")
                fields[-1]['value'].append(self.escape(self.bot.util.shortenName(p['name'])))
                if len(fields[-1]['value'][-1]) > 6:
                    # to be sure to not hit field value limit, limit player names to 6 characters
                    fields[-1]['value'][-1] = fields[-1]['value'][-1][:6] + "…"
                fields[-1]['value'].append("](https://game.granbluefantasy.jp/#profile/")
                fields[-1]['value'].append(str(p['id']))
                fields[-1]['value'].append(")")
                if gwstate:
                    fields[-1]['value'].append(" - {}".format(self.bot.util.valToStr(p['honor'], 2)))
                else:
                    fields[-1]['value'].append(" - r**{}**".format(p['level']))
                fields[-1]['value'].append("\n")
        field : dict[str, str|list]
        for field in fields:
            field['value'] = "".join(field['value'])
        return ''.join(title), ''.join(description), fields, footer, players

    """_crew_sub()
    Used by /gw crew and the PageRanking view

    Parameters
    ----------
    inter: Command interaction, must be deferred beforehand
    crew_id: Crew id string (can be name, value, etc)
    mode: Integer, 0 for auto, 1 for member rank, 2 for member honor
    view: Optional view
    color: Optional embed color

    Returns
    bool: True if success, False otherwise
    """
    async def _crew_sub(
        self : GuildWar,
        inter : disnake.ApplicationCommandInteraction,
        crew_id : str,
        mode : int,
        view : BaseView|None = None
    ) -> bool:
        # retrieve crew data
        crew : CrewData = await self.getCrewData(crew_id, 0)
        if 'error' in crew: # print the error if any
            if len(crew['error']) > 0:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Crew Error",
                        description=crew['error'],
                        color=self.COLOR
                    ),
                    view=view
                )
            return True
        # process data into usable strings
        title : str
        description : str
        fields : list[dict[str, str]]
        footer : str
        players : PlayerList
        title, description, fields, footer, players = await self.processCrewData(crew, mode)
        # prepare embed
        embed : disnake.Embed = self.bot.embed(
            title=title,
            description=description,
            fields=fields,
            inline=True,
            url="https://game.granbluefantasy.jp/#guild/detail/{}".format(
                crew['id']
            ),
            footer=footer,
            timestamp=crew['timestamp'],
            color=self.COLOR
        )
        self_view : bool = False
        if view is None and not crew.get('private', False):
            self_view = True
            embed.footer.text += " ▫️ Buttons expire in 100 seconds"
            search_results : PageResultList = []
            i : int
            p : PlayerData
            for i, p in enumerate(players):
                if (i % 10) == 0:
                    search_results.append([])
                search_results[-1].append((p['id'], self.escape(p['name'])))
            embeds : list[disnake.Embed] = [
                embed for i in range(len(search_results))
            ]
            view : PageRanking = PageRanking(
                self.bot,
                owner_id=inter.author.id,
                embeds=embeds,
                search_results=search_results,
                color=self.COLOR,
                stype=False,
                timeout=100,
                enable_timeout_cleanup=True
            )
        await inter.edit_original_message(embed=embed, view=view)
        if self_view:
            view.message = await inter.original_message()
            return False
        return True

    @gw.sub_command(name="crew")
    async def _crew(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        crew_id : str = commands.Param(description="Crew ID"),
        mode : int = commands.Param(
            description="Mode (0=Auto, 1=Rank, 2=Honor)",
            ge=0,
            le=2,
            default=0
        )
    ) -> None:
        """Get a crew profile"""
        await inter.response.defer()
        try:
            if await self._crew_sub(inter, crew_id, mode):
                await self.bot.channel.clean(inter, 60)
        except Exception as e:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="A critical error occured, wait for a fix or use {}  if the error persists".format(
                        self.bot.util.command2mention('bug_report')
                    ),
                    color=self.COLOR
                )
            )
            self.bot.logger.pushError("[GW] In 'gw crew' command (Parameter: `{}`):".format(crew_id), e)
            await self.bot.channel.clean(inter, 60)

    """requestCrew()
    Get a crew page data

    Parameters
    ------
    cid: Crew ID
    page: Crew page (0 = crew main page, 1~3 = crew member pages)

    Returns
    ----------
    dict: Resulting data, None if error
    """
    async def requestCrew(self : GuildWar, cid : int, page : int) -> RequestResult: # get crew data
        if page == 0:
            return await self.bot.net.requestGBF("guild_other/guild_info/{}".format(cid), expect_JSON=True)
        else:
            return await self.bot.net.requestGBF("guild_other/member_list/{}/{}".format(page, cid), expect_JSON=True)

    @gw.sub_command()
    async def lead(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        id_crew_1 : str = commands.Param(description="First crew ID"),
        id_crew_2 : str = commands.Param(description="Second crew ID")
    ) -> None:
        """Search two crew current scores and compare them"""
        await inter.response.defer()
        day : int|None = self.bot.ranking.getCurrentGWDayID()
        if day is None or (day % 10) <= 1:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} **Guild War**".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="Unavailable",
                    color=self.COLOR
                )
            )
            return
        if day >= 10:
            day = day % 10
        msgs : list[str] = []
        lead_flag : bool = True
        lead_speed_flag : bool = True
        lead : int|None = None
        lead_speed : int|None = None
        desc : list[str] = []
        sid : str
        cid : str|int
        for sid in (id_crew_1, id_crew_2):
            if sid.lower() in self.bot.ranking.allconfigcrews:
                cid = self.bot.ranking.allconfigcrews[sid.lower()]
            else:
                try:
                    cid = int(sid)
                except:
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="{} **Guild War**".format(
                                self.bot.emote.get('gw')
                            ),
                            description="Invalid ID `{}`".format(sid),
                            color=self.COLOR
                        )
                    )
                    return

            data : GWDBSearchResult|None = await self.bot.ranking.searchGWDB(str(cid), 12)
            if data is None:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="{} **Guild War**".format(
                            self.bot.emote.get(
                                'gw'
                            )
                        ),
                        description="Unavailable",
                        color=self.COLOR
                    )
                )
                return
            else:
                timestamp : datetime
                if len(desc) == 0 and data[2][1] is not None:
                    timestamp = data[2][1].timestamp
                    if timestamp is not None:
                        desc.append(
                            "Updated: **{}** ago\n".format(
                                self.bot.util.delta2str(
                                    self.bot.util.JST() - timestamp,
                                    0
                                )
                            )
                        )
                if data[1] is None:
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="{} **Guild War**".format(
                                self.bot.emote.get(
                                    'gw'
                                )
                            ),
                            description="No data available for `{}` the current GW".format(sid),
                            color=self.COLOR
                        )
                    )
                    return
                result : GWDBList = data[1]
                gwnum : str = ''
                if len(result) == 0:
                    msgs.append("Crew [{}](https://game.granbluefantasy.jp/#guild/detail/{}) not found\n".format(
                        sid,
                        cid
                    ))
                    lead = None
                    lead_flag = False
                else:
                    gwnum = result[0].gw
                    msgs.append("[{:}](https://game.granbluefantasy.jp/#guild/detail/{:}) ▫️ {:,}".format(
                        result[0].name,
                        cid,
                        result[0].current_day
                    ))
                    if result[0].current_speed is not None and result[0].top_speed is not None:
                        msgs.append(
                            " ▫️ +{}/m. ▫️ Top {}/m.\n".format(
                                self.bot.util.valToStr(result[0].current_speed),
                                self.bot.util.valToStr(result[0].top_speed)
                            )
                        )
                        if timestamp is not None and day - 1 > 0 and day - 1 < 5:
                            if (timestamp < self.bot.data.save['gw']['dates']['Day ' + str(day)]
                                    - timedelta(seconds=25200)):
                                current_time_left : timedelta = (
                                    self.bot.data.save['gw']['dates']['Day ' + str(day)]
                                    - timedelta(seconds=25200)
                                    - timestamp
                                )
                                current_estimation : int = (
                                    result[0].current_day
                                    + result[0].current_speed
                                    * current_time_left.seconds // 60
                                )
                                top_estimation : int = (
                                    result[0].current_day
                                    + result[0].top_speed
                                    * current_time_left.seconds // 60
                                )
                                msgs.append(
                                    "**Estimation** ▫️ Now {} ▫️ Top {}\n".format(
                                        self.bot.util.valToStr(current_estimation, 3),
                                        self.bot.util.valToStr(top_estimation, 3)
                                    )
                                )
                        if lead_speed is None:
                            lead_speed = result[0].current_speed
                        else:
                            lead_speed -= result[0].current_speed
                    else:
                        msgs.append("\n")
                        lead_speed_flag = False
                    if lead_flag:
                        if lead is None:
                            lead = result[0].current_day
                        else:
                            lead -= result[0].current_day
        if lead_flag and lead != 0:
            if lead < 0:
                lead = -lead
                if lead_speed_flag:
                    lead_speed = -lead_speed
            msgs.append("\n**Difference** ▫️ {:,}".format(lead))
            if lead_speed_flag and lead_speed != 0:
                msgs.append(" ▫️ ")
                if lead_speed > 0:
                    msgs.append("+")
                msgs.append("{}/m.\n".format(self.bot.util.valToStr(lead_speed, 3)))
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="{} **Guild War {} ▫️ Day {}**".format(
                    self.bot.emote.get('gw'),
                    gwnum,
                    day - 1
                ),
                description="".join(desc + msgs),
                timestamp=self.bot.util.UTC(),
                color=self.COLOR
            )
        )

    """updateGBFGData()
    Store the /gbfg/ crew data for later use by playerranking and danchoranking

    Parameters
    ------
    force_update: If True, update all crews

    Returns
    ----------
    dict: Content of self.bot.data.save['gw']['gbfgdata']
    """
    async def updateGBFGData(self : GuildWar, force_update : bool = False) -> GBFGData|None:
        if not self.isGWRunning():
            return None
        if 'gbfgdata' not in self.bot.data.save['gw'] or force_update:
            self.bot.data.save['gw']['gbfgdata'] = {}
            self.bot.data.pending = True
        c : str
        for c in self.bot.ranking.gbfgcrews_id:
            if (c in self.bot.data.save['gw']['gbfgdata']
                    and len(self.bot.data.save['gw']['gbfgdata'][c][3]) > 0
                    and not force_update):
                continue
            crew : CrewData = await self.getCrewData(c, 0)
            if 'error' in crew or crew['private']:
                crew = await self.getCrewData(c, 1)
                if str(c) not in self.bot.data.save['gw']['gbfgdata']:
                    self.bot.data.save['gw']['gbfgdata'][str(c)] = [
                        crew['name'],
                        crew['leader'],
                        int(crew['leader_id']),
                        []
                    ]
                continue
            self.bot.data.save['gw']['gbfgdata'][str(c)] = [crew['name'], crew['leader'], int(crew['leader_id']), []]
            self.bot.data.save['gw']['gbfgdata'][str(c)][-1] = [p['id'] for p in crew['player']]
            self.bot.data.pending = True
        return self.bot.data.save['gw']['gbfgdata']

    @gw.sub_command_group()
    async def utility(self : commands.SubCommandGroup, inter : disnake.ApplicationCommandInteraction) -> None:
        pass

    @utility.sub_command()
    async def box(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        box : int = commands.Param(
            description="Number of box to clear",
            ge=1,
            le=1000
        ),
        box_done : int = commands.Param(
            description="Your current box progress, default 0 (Will be ignored if equal or higher than target)",
            ge=0,
            default=0
        ),
        with_token : str = commands.Param(
            description="Your current token amount (support T, B, M and K)",
            default="0"
        )
    ) -> None:
        """Convert Guild War box values"""
        try:
            await inter.response.defer(ephemeral=True)
            t : int = 0
            try:
                with_token_int : int = max(0, self.bot.util.strToInt(with_token))
            except:
                raise Exception(
                    "Your current token amount `{}` isn't a valid number".format(
                        with_token_int
                    )
                )
            if box_done >= box:
                raise Exception(
                    "Your current box count `{}` is higher or equal to your target `{}`".format(
                        box_done,
                        box
                    )
                )
            i : int = 0
            b : int
            for b in range(box_done + 1, box + 1):
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    i += 1
                t += self.BOX_COST[i][1]
            t = max(0, t - with_token_int)
            msgs : list[str] = [
                "**{:,}** tokens needed{:}{:}\n\n".format(
                    t,
                    ("" if box_done == 0 else " from box **{}**".format(box_done + 1)),
                    ("" if with_token_int == 0 else " with **{:,}** tokens".format(with_token_int))
                )
            ]
            f : str
            d : dict[str, float|int]
            for f, d in self.FIGHTS.items():
                n : int = math.ceil(t / d["token"])
                msgs.append("**{:,}** {:} (**{:,}** pots".format(n, f, n * d["AP"] // 75))
                if d["meat_cost"] > 0:
                    msgs.append(", **{:,}** meats".format(n * d["meat_cost"]))
                if d["clump_cost"] > 0:
                    msgs.append(", **{:,}** clumps".format(n * d["clump_cost"]))
                msgs.append(")\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Guild War Token Calculator ▫️ Box {}".format(
                        self.bot.emote.get('gw'),
                        box
                    ),
                    description="".join(msgs),
                    color=self.COLOR
                )
            )
        except Exception as e:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description=str(e),
                    color=self.COLOR
                )
            )

    @utility.sub_command()
    async def token(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        token_target : str = commands.Param(description="Number of tokens you want (support T, B, M and K)"),
        final_rally : int = commands.Param(
            description="1 to include final rally (default), 0 to disable",
            default=1,
            le=1,
            ge=0
        )
    ) -> None:
        """Convert Guild War token values"""
        try:
            await inter.response.defer(ephemeral=True)
            tok : int = self.bot.util.strToInt(token_target)
            if tok < 1 or tok > 9999999999:
                raise Exception()
            b : int = 0 # box count
            t : int = tok # copy of token
            i : int = 0 # BOX_COST index
            # increase b (box count) until we run out of tok (tokens)
            while True:
                if tok < self.BOX_COST[i][1]: # not enough to empty box, we stop
                    break
                tok -= self.BOX_COST[i][1] # remove token cost
                b += 1 # increase box
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    # move BOX_COST index to next if it exists
                    i += 1
            # create message
            msgs : list[str] = ["**{:,}** box(s) and **{:,}** leftover tokens\n\n".format(b, tok)]
            f : str
            d : dict[str, float|int]
            for f, d in self.FIGHTS.items():
                # calculate number of fights needed
                n : int
                if final_rally:
                    n = math.ceil(t / (d["token"] + d["rally_token"]))
                else:
                    n = math.ceil(t / d["token"])
                # prepare message
                msgs.append("**{:,}** {:} (**{:,}** pots".format(n, f, n * d["AP"] // 75))
                # add meat costs
                if d["meat_cost"] > 0:
                    msgs.append(", **{:,}** meats".format(n * d["meat_cost"]))
                if d["clump_cost"] > 0:
                    msgs.append(", **{:,}** clumps".format(n * d["clump_cost"]))
                msgs.append(")\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Guild War Token Calculator ▫️ {} tokens".format(
                        self.bot.emote.get('gw'),
                        t
                    ),
                    description="".join(msgs),
                    footer=(
                        "Imply you solo all your hosts and clear the final rally" if final_rally else ""
                    ),
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Invalid token number",
                    color=self.COLOR
                )
            )

    @utility.sub_command()
    async def meat(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        value : str = commands.Param(description="Value to convert (support T, B, M and K)")
    ) -> None:
        """Convert Guild War meat or clump values"""
        try:
            await inter.response.defer(ephemeral=True)
            meat : int = self.bot.util.strToInt(value)
            if meat < 5 or meat > 400000:
                raise Exception()
            msgs : list[str] = []
            f : str
            d : dict[str, float|int]
            for f, d in self.FIGHTS.items():
                # calculate meat/clump usable for each fight
                n = int
                if d["meat_cost"] > 0: # meat fight
                    n = meat // d["meat_cost"]
                    msgs.append(
                        "**{:,}** {:} or **{:}** honors".format(
                            n,
                            f,
                            self.bot.util.valToStr(n * d["honor"], 2)
                        )
                    )
                    # add clump drop if available
                    if d["clump_drop"] > 0:
                        msgs.append(
                            ", for **{:}** clump drops".format(
                                self.bot.util.valToStr(math.ceil(n * d["clump_drop"]), 2)
                            )
                        )
                    msgs.append("\n")
                elif d["clump_cost"] > 0: # clump fight
                    n = meat // d["clump_cost"]
                    msgs.append(
                        "**{:,}** {:} or **{:}** honors\n".format(
                            n,
                            f,
                            self.bot.util.valToStr(n * d["honor"], 2)
                        )
                    )
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Meat Calculator ▫️ {} meats or clumps".format(
                        self.bot.emote.get('gw'),
                        meat
                    ),
                    description="".join(msgs),
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Invalid meat number",
                    color=self.COLOR
                )
            )

    @utility.sub_command()
    async def honor(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        value : str = commands.Param(description="Value to convert (support T, B, M and K)")
    ) -> None:
        """Convert Guild War honor values"""
        try:
            await inter.response.defer(ephemeral=True)
            target : int = self.bot.util.strToInt(value)
            if target < 10000:
                raise Exception()
            msgs : list[str] = []
            f : str
            d : dict[str, float|int]
            for f, d in self.FIGHTS.items():
                n : int = math.ceil(target / d["honor"]) # number of fights needed
                msgs.append("**{:,}** {:} (**{:,}** pots".format(n, f, n * d["AP"] // 75))
                # add other infos if available
                if d["meat_cost"] > 0:
                    msgs.append(", **{:,}** meats".format(n * d["meat_cost"]))
                if d["clump_cost"] > 0:
                    msgs.append(", **{:,}** clumps".format(n * d["clump_cost"]))
                if d["clump_drop"] > 0:
                    msgs.append(", **{:,}** clump drops".format(math.ceil(n * d["clump_drop"])))
                msgs.append(")\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Honor Calculator ▫️ {} honors".format(
                        self.bot.emote.get('gw'),
                        self.bot.util.valToStr(target)
                    ),
                    description="".join(msgs),
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Invalid honor number",
                    color=self.COLOR
                )
            )

    @utility.sub_command()
    async def honorplanning(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        target : str = commands.Param(description="Number of honors (support T, B, M and K)")
    ) -> None:
        """Calculate how many NM100 to 250 you need for your targeted honor"""
        try:
            await inter.response.defer(ephemeral=True)
            target : int = self.bot.util.strToInt(target)
            if target < 1000000:
                raise Exception()
            honor : list[int] = [0, 0, 0, 0, 0] # prelims, day 1, 2, 3 and 4 honor
            ex : int = 0 # ex+ done
            interlude_fight : str = "NM90" # constant
            interlude_count : int = 0 # interlude fight done
            day_target : list[float] = [ # honor target for each day (1 to 4)
                target * 0.15,
                target * 0.20,
                target * 0.32,
                target * 0.33
            ]
            day_nm : list[str] = ["NM100", "NM150", "NM250", "NM250"] # constant, fight for each day
            nm : list[int] = [0, 0, 0, 0] # fight done on each day
            meat : float = 0 # meat available
            total_meat : float = 0 # total meat used
            clump : float = 0 # clump available
            prelim_clump : float = 0 # clump gathered during prelims/interlude
            total_clump : float = 0 # total clump used

            i : int
            for i in range(4): # for day 1 to 4
                daily : int = 0 # daily honor
                while daily < day_target[i]: # until target is reached
                    if self.FIGHTS[day_nm[i]]["meat_cost"] > 0: # if the fight cost meat
                        if meat < self.FIGHTS[day_nm[i]]["meat_cost"]: # not enough meat, do EX instead
                            meat += self.MEAT_PER_BATTLE_AVG
                            total_meat += self.MEAT_PER_BATTLE_AVG
                            ex += 1
                            daily += self.FIGHTS["EX+"]["honor"]
                            honor[0] += self.FIGHTS["EX+"]["honor"]
                        else:
                            meat -= self.FIGHTS[day_nm[i]]["meat_cost"] # enough meat, do NM
                            nm[i] += 1
                            clump += self.FIGHTS[day_nm[i]]["clump_drop"]
                            total_clump += self.FIGHTS[day_nm[i]]["clump_drop"]
                            daily += self.FIGHTS[day_nm[i]]["honor"]
                            honor[i + 1] += self.FIGHTS[day_nm[i]]["honor"]
                    elif self.FIGHTS[day_nm[i]]["clump_cost"] > 0: # else if it's a clump fight
                        if clump < self.FIGHTS[interlude_fight]["clump_cost"]: # not enough clump, do interlue instead
                            if meat < self.FIGHTS[interlude_fight]["meat_cost"]: # not enough meat, do EX instead
                                meat += self.MEAT_PER_BATTLE_AVG
                                total_meat += self.MEAT_PER_BATTLE_AVG
                                ex += 1
                                daily += self.FIGHTS["EX+"]["honor"]
                                honor[0] += self.FIGHTS["EX+"]["honor"]
                            else:
                                meat -= self.FIGHTS[interlude_fight]["meat_cost"] # do interlue
                                interlude_count += 1
                                clump += self.FIGHTS[interlude_fight]["clump_drop"]
                                total_clump += self.FIGHTS[interlude_fight]["clump_drop"]
                                prelim_clump += self.FIGHTS[interlude_fight]["clump_drop"]
                                daily += self.FIGHTS[interlude_fight]["honor"]
                                honor[0] += self.FIGHTS[interlude_fight]["honor"]
                        else:
                            clump -= self.FIGHTS[day_nm[i]]["clump_cost"] # enough meat, do NM
                            nm[i] += 1
                            daily += self.FIGHTS[day_nm[i]]["honor"]
                            honor[i + 1] += self.FIGHTS[day_nm[i]]["honor"]
            # make message from the result
            msgs : list[str] = [
                (
                    "Total used meat counts ▫️ **{:,}** meats, **{:,}** clumps\n"
                    "Prelim. & Interlude ▫️ Around **{:,}** EX+, **{:,}** {:} for **{:,}** clumps, **{:}** honors"
                ).format(
                    math.ceil(total_meat),
                    math.ceil(total_clump),
                    ex,
                    interlude_count,
                    interlude_fight,
                    math.ceil(prelim_clump),
                    self.bot.util.valToStr(honor[0], 2)
                )
            ]
            for i in range(0, len(nm)):
                msgs.append(
                    "Day {:} ▫️ **{:,}** {} (**{:}** honors)".format(
                        i + 1,
                        nm[i],
                        day_nm[i],
                        self.bot.util.valToStr(honor[i + 1], 2)
                    )
                )
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Honor Planning ▫️ {} honors".format(
                        self.bot.emote.get('gw'),
                        self.bot.util.valToStr(target)
                    ),
                    description="\n".join(
                        msgs
                    ),
                    footer="Assuming {} meats / EX+ on average".format(
                        self.MEAT_PER_BATTLE_AVG
                    ),
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Invalid honor number",
                    color=self.COLOR
                )
            )

    """speed_callback()
    CustomModal callback
    """
    async def speed_callback(self : GuildWar, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        # loading is the expected time wasted between fight
        # it's set by a command parameter, not the modal
        loading : int = int(modal.extra)
        error : bool = False
        msgs : list[str] = []
        f : str
        v : str
        for f, v in inter.text_values.items(): # go over entries
            try:
                if v == '' or f not in self.FIGHTS:
                    continue # empty or fight not supported, ignore
                elif '.' in v:
                    raise Exception() # dot inside, error
                elems : list[str] = v.split(':') # split with :
                time : int
                if len(elems) > 2: # if more than 2 :, unsupported
                    error = True
                    continue
                elif len(elems) == 2: # equal, we expect something like 00:00
                    a : int = int(elems[0])
                    b : int = int(elems[1])
                    if a < 0 or b < 0:
                        raise Exception() # check negative
                    # Note: possible additional checks: 60 seconds cap, etc... but we keep it loose on purpose
                    time = a * 60 + b
                else: # it's simply expected to be a single number
                    time = int(elems[0])
                # check if time is negative or null
                if time < 0:
                    raise Exception()
                elif time == 0:
                    continue
                # calculate how much fights is this per hour
                mod : float = (3600 / (time + loading))
                # make message
                msgs.append(
                    "**{}** ▫️ {}{} ▫️ **{}** ▫️ **{}** Tokens ▫️ **{}** pots".format(
                        f,
                        self.bot.emote.get('clock'),
                        v,
                        self.bot.util.valToStr(
                            mod * self.FIGHTS[f]["honor"],
                            2
                        ),
                        self.bot.util.valToStr(
                            mod * self.FIGHTS[f]["token"],
                            2
                        ),
                        self.bot.util.valToStr(
                            math.ceil(
                                mod * self.FIGHTS[f]["AP"] / 75
                            ),
                            2
                        )
                    )
                )
                # add additional infos
                if self.FIGHTS[f]["meat_cost"] > 0:
                    msgs.append(" ▫️ **{}** meats ".format(
                        self.bot.util.valToStr(
                            mod * self.FIGHTS[f]["meat_cost"],
                            2
                        )
                    ))
                if self.FIGHTS[f]["clump_cost"] > 0:
                    msgs.append(" ▫️ **{}** clumps ".format(
                        self.bot.util.valToStr(
                            mod * self.FIGHTS[f]["clump_cost"],
                            2
                        )
                    ))
                if self.FIGHTS[f]["clump_drop"] > 0:
                    msgs.append(" ▫️ **{}** clump drops ".format(
                        self.bot.util.valToStr(
                            math.ceil(mod * self.FIGHTS[f]["clump_drop"]),
                            2
                        )
                    ))
                msgs.append("\n")
            except:
                error = True
        if len(msgs) == 0:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Speed Comparator".format(
                        self.bot.emote.get('gw')
                    ),
                    description=(
                        "No clear times set.\n"
                        + '' if not error else (
                            'One or multiple values you sent were wrong.'
                            'Either put a number of seconds **or** a time'
                            'following the `MM:SS` format'
                        )
                    ),
                    color=self.COLOR
                )
            )
        else:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Speed Comparator".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="**Per hour**" + (
                        ', with {} seconds of wasted time between fights\n'.format(
                            loading
                        ) if loading > 0 else '\n'
                    ) + "".join(msgs),
                    color=self.COLOR,
                    footer='' if not error else 'Errors have been ignored'
                )
            )

    @utility.sub_command()
    async def speed(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        loading : int = commands.Param(description="Wasted time between fights, in second", default=0)
    ) -> None:
        """Compare multiple GW Nightmare fights based on your speed"""
        # Note: We're limited to 5 inputs
        await self.bot.singleton.make_and_send_modal(
            inter,
            "gw_speed-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()),
            "GW Speed Comparator",
            self.speed_callback,
            [
                disnake.ui.TextInput(
                    label="NM90",
                    placeholder="NM90 Kill Time (In seconds)",
                    custom_id="NM90",
                    style=disnake.TextInputStyle.short,
                    max_length=5,
                    required=False
                ),
                disnake.ui.TextInput(
                    label="NM100",
                    placeholder="NM100 Kill Time (In seconds)",
                    custom_id="NM100",
                    style=disnake.TextInputStyle.short,
                    max_length=5,
                    required=False
                ),
                disnake.ui.TextInput(
                    label="NM150",
                    placeholder="NM150 Kill Time (In seconds)",
                    custom_id="NM150",
                    style=disnake.TextInputStyle.short,
                    max_length=5,
                    required=False
                ),
                disnake.ui.TextInput(
                    label="NM200",
                    placeholder="NM200 Kill Time (In seconds)",
                    custom_id="NM200",
                    style=disnake.TextInputStyle.short,
                    max_length=5,
                    required=False
                ),
                disnake.ui.TextInput(
                    label="NM250",
                    placeholder="NM250 Kill Time (In seconds)",
                    custom_id="NM250",
                    style=disnake.TextInputStyle.short,
                    max_length=5,
                    required=False
                )
            ],
            str(loading)
        )

    @gw.sub_command_group()
    async def nm(self : commands.SubCommandGroup, inter : disnake.ApplicationCommandInteraction) -> None:
        pass

    @nm.sub_command()
    async def hp90_95(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Give a fight equivalent of NM95 and NM90"""
        await inter.response.defer()
        # fight data (Name, HP, URL)
        boss : dict[str, tuple[str, int, str]] = {
            'fire':('Ewiyar (Solo)', 180000000, "103471/3"),
            'water':('Wilnas (Solo)', 165000000, "103441/3"),
            'earth':('Wamdus (Solo)', 182000000, "103451/3"),
            'wind':('Galleon (Solo)', 196000000, "103461/3"),
            'light':('Gilbert (Proud)', 180000000, "103571/3"),
            'dark':('Lu Woh (Solo)', 192000000, "103481/3")
        }
        msgs : list[str] = []
        el : str
        for el in boss: # for each boss
            if boss.get(el, None) is None: # undefined
                msgs.append("{} *No equivalent*\n".format(self.bot.emote.get(el)))
            else:
                # add line with url and HP target equivalent for NM90 and NM95
                msgs.append(
                    (
                        "{:} [{:}](http://game.granbluefantasy.jp/#quest/supporter/{:})"
                        "▫️ NM95: **{:.1f}%** ▫️ NM90: **{:.1f}%** HP remaining.\n"
                    ).format(
                        self.bot.emote.get(el),
                        boss[el][0],
                        boss[el][2],
                        100 * (
                            (boss[el][1] - self.FIGHTS['NM95']['hp']) / boss[el][1]
                        ),
                        100 * (
                            (boss[el][1] - self.FIGHTS['NM90']['hp']) / boss[el][1]
                        )
                    )
                )
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="{} Guild War ▫️ NM95 and NM90 Simulation".format(
                    self.bot.emote.get('gw')
                ),
                description="".join(msgs),
                color=self.COLOR
            )
        )
        await self.bot.channel.clean(inter, 90)

    @nm.sub_command()
    async def hp100(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Give a fight equivalent of NM100"""
        await inter.response.defer()
        # fight data (Name, HP, URL)
        boss : dict[str, tuple[str, int, str]] = {
            'fire':('Ra', 565000000, "305351/1/0/44"),
            'water':('Atum', 570000000, "305321/1/0/41"),
            'earth':('Tefnut', 620000000, "305331/1/0/42"),
            'wind':('Bennu', 550000000, "305341/1/0/43"),
            'light':('Osiris', 600000000, "305371/1/0/46"),
            'dark':('Horus', 600000000, "305361/1/0/46")
        }
        msgs : list[str] = []
        el : str
        for el in boss:# for each boss
            if boss.get(el, None) is None: # undefined
                msgs.append("{} *No equivalent*\n".format(self.bot.emote.get(el)))
            else:
                # add line with url and HP target equivalent for NM90 and NM95
                msgs.append(
                    (
                        "{:} [{:}](http://game.granbluefantasy.jp/#quest/supporter/{:})"
                        " ▫️ NM100: **{:.1f}%** HP remaining.\n"
                    ).format(
                        self.bot.emote.get(el),
                        boss[el][0],
                        boss[el][2], 100 * (
                            (boss[el][1] - self.FIGHTS['NM100']['hp']) / boss[el][1]
                        )
                    )
                )
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="{} Guild War ▫️ NM100 Simulation".format(
                    self.bot.emote.get('gw')
                ),
                description="".join(msgs),
                color=self.COLOR
            )
        )
        await self.bot.channel.clean(inter, 90)

    @gw.sub_command_group()
    async def find(self : commands.SubCommandGroup, inter : disnake.ApplicationCommandInteraction) -> None:
        pass

    @find.sub_command(name="crew")
    async def crewfind(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        terms : str = commands.Param(description="What to search for"),
        search_type : int = commands.Param(
            description="0 = name (default). 1 = exact name. 2 = ID. 3 = ranking.",
            default=0,
            ge=0,
            le=3
        ),
        mode_past : int = commands.Param(
            description="1 to search the previous GW. 0  for the current/last (default).",
            default=0,
            ge=0,
            le=1
        )
    ) -> None:
        """Search a crew or player GW score in the bot data"""
        await inter.response.defer(ephemeral=True)
        await self.findranking(inter, True, terms, search_type, mode_past)

    @find.sub_command(name="player")
    async def playerfind(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        terms : str = commands.Param(description="What to search for"),
        search_type : int = commands.Param(
            description="0 = name (default). 1 = exact name. 2 = ID. 3 = ranking.",
            default=0,
            ge=0,
            le=3
        ),
        mode_past : int = commands.Param(
            description="1 to search the previous GW. 0  for the current/last (default).",
            default=0,
            ge=0,
            le=1
        )
    ) -> None:
        """Search a crew or player GW score in the bot data"""
        await inter.response.defer(ephemeral=True)
        await self.findranking(inter, False, terms, search_type, mode_past)

    """findranking()
    Extract parameters from terms and call searchGWDB() with the proper settings.
    inter is used to output the result.
    Used by find()

    Parameters
    ----------
    inter: Command interaction, must be deferred beforehand
    stype: Boolean, True for crews, False for players
    terms: Search string
    search_type: 0 = name, 1 = exact name, 2 = ID, 3 = ranking
    mode_past: to enable the past gw search
    """
    async def findranking(
        self : GuildWar,
        inter : disnake.ApplicationCommandInteraction,
        stype : bool,
        terms : str,
        search_type : int,
        mode_past : int
    ) -> None:
        # set the search strings based on the search type
        txt : str
        if stype:
            txt = "crew"
        else:
            txt = "player"
        if terms == "": # no search terms so we print how to use it
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} **Guild War**".format(
                        self.bot.emote.get('gw')
                    ),
                    description=(
                        "**Usage**"
                        "`/gw find {} terms:{}name` to search a {} by name\n"
                        "`/gw find {} terms:{}name search_type:1` for an exact match\n"
                        "`/gw find {} terms:{}id search_type:2` for an id search\n"
                        "`/gw find {} terms:{}ranking search_type:3` for a ranking search"
                    ).replace(
                        '{}',
                        txt
                    ),
                    color=self.COLOR
                )
            )
        else:
            try:
                # process/prepare parameters
                past : bool = (mode_past == 1)
                mode : int
                match search_type:
                    case 0:
                        mode = 0
                        terms = self.htmlescape(terms)
                    case 1:
                        terms = self.htmlescape(terms)
                        mode = 1
                    case 2:
                        try:
                            int(terms)
                            mode = 2
                        except:
                            await inter.edit_original_message(
                                embed=self.bot.embed(
                                    title="{} **Guild War**".format(
                                        self.bot.emote.get('gw')
                                    ),
                                    description="`{}` isn't a valid ID".format(terms),
                                    footer='ID mode is enabled',
                                    color=self.COLOR
                                )
                            )
                            raise Exception("Returning")
                    case 3:
                        try:
                            int(terms)
                            mode = 3
                        except:
                            await inter.edit_original_message(
                                embed=self.bot.embed(
                                    title="{} **Guild War**".format(
                                        self.bot.emote.get('gw')
                                    ),
                                    description="`{}` isn't a valid syntax".format(terms),
                                    color=self.COLOR
                                )
                            )
                            raise Exception("Returning")
                # do our search
                data : GWDBSearchResult|None = await self.bot.ranking.searchGWDB(terms, (mode + 10 if stype else mode))
                # select the right database (oldest one if %past is set or newest is unavailable, if not the newest)
                result : GWDBList|None
                if data[1] is None or past:
                    result = data[0]
                else:
                    result = data[1]
                # check validity
                if result is None:
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="{} **Guild War**".format(
                                self.bot.emote.get('gw')
                            ),
                            description="Database unavailable",
                            color=self.COLOR
                        )
                    )
                    raise Exception("Returning")
                # max to display
                max_v : int = 9 if stype else 18 # 9 for crews, 18 for players
                # check number of matches
                if len(result) == 0:
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="{} **Guild War**".format(
                                self.bot.emote.get('gw')
                            ),
                            description="`{}` not found".format(
                                html.unescape(str(terms))
                            ),
                            color=self.COLOR
                        )
                    )
                    raise Exception("Returning")
                elif len(result) > (max_v * 20) and mode != 1: # Max 20 pages
                    if mode == 0:
                        await inter.edit_original_message(
                            embed=self.bot.embed(
                                title="{} **Guild War**".format(
                                    self.bot.emote.get('gw')
                                ),
                                description="Way too many results for `{}`\nTry to set `search_type` to **1**".format(
                                    html.unescape(str(terms))
                                ),
                                color=self.COLOR
                            )
                        )
                    else:
                        await inter.edit_original_message(
                            embed=self.bot.embed(
                                title="{} **Guild War**".format(
                                    self.bot.emote.get('gw')
                                ),
                                description="Way too many results for `{}`\nPlease try another search".format(
                                    html.unescape(str(terms))
                                ),
                                color=self.COLOR
                            )
                        )
                    raise Exception("Returning")
                # embed fields for the message
                embeds : list[disnake.Embed] = []
                fields : list[dict[str, str|list]] = []
                search_results : list[tuple[int, str]] = []
                x : int
                gwnum : int|str = ""
                for x in range(0, 1 + len(result) // max_v):
                    # we iterate max_v per max_v (example: 9 per 9) to make each page
                    search_list : tuple[int, str] = []
                    y : int
                    for y in range(0, max_v): # and there we iterate over what will be the content
                        i : int = x * max_v + y # index in result
                        if i >= len(result):
                            break
                        if stype: # crew -----------------------------------------------------------------
                            fields.append({'name':"{}".format(html.unescape(result[i].name)), 'value':[]})
                            search_list.append((result[i].id, html.unescape(result[i].name)))
                            if result[i].ranking is not None:
                                fields[-1]['value'].append("▫️**#{}**\n".format(result[i].ranking))
                            else:
                                fields[-1]['value'].append("\n")
                            if result[i].preliminaries is not None:
                                fields[-1]['value'].append(
                                    "**P.** ▫️{:,}\n".format(
                                        result[i].preliminaries
                                    )
                                )
                            if result[i].day1 is not None:
                                fields[-1]['value'].append(
                                    "{}▫️{:,}\n".format(
                                        self.bot.emote.get('1'),
                                        result[i].day1
                                    )
                                )
                            if result[i].day2 is not None:
                                fields[-1]['value'].append(
                                    "{}▫️{:,}\n".format(
                                        self.bot.emote.get('2'),
                                        result[i].day2
                                    )
                                )
                            if result[i].day3 is not None:
                                fields[-1]['value'].append(
                                    "{}▫️{:,}\n".format(
                                        self.bot.emote.get('3'),
                                        result[i].day3
                                    )
                                )
                            if result[i].day4 is not None:
                                fields[-1]['value'].append(
                                    "{}▫️{:,}\n".format(
                                        self.bot.emote.get('4'),
                                        result[i].day4
                                    )
                                )
                            if result[i].top_speed is not None:
                                fields[-1]['value'].append(
                                    "{}▫️Top {}/m.\n".format(
                                        self.bot.emote.get('clock'),
                                        self.bot.util.valToStr(result[i].top_speed)
                                    )
                                )
                            if result[i].current_speed is not None and result[i].current_speed > 0:
                                fields[-1]['value'].append(
                                    "{}▫️Now {}/m.\n".format(
                                        self.bot.emote.get('clock'),
                                        self.bot.util.valToStr(result[i].current_speed)
                                    )
                                )
                            if len(fields[-1]['value']) == 0:
                                fields[-1]['value'] = ["No data"]
                            fields[-1]['value'].insert(
                                0,
                                "[{}](https://game.granbluefantasy.jp/#guild/detail/{})".format(
                                    result[i].id,
                                    result[i].id
                                )
                            )
                            fields[-1]['value'] = "".join(fields[-1]['value'])
                            gwnum = result[i].gw
                        else: # player -----------------------------------------------------------------
                            if y % (max_v // 3) == 0: # some trickery to make the columns
                                if len(fields) > 0:
                                    fields[-1]['value'] = "".join(fields[-1]['value'])
                                fields.append(
                                    {
                                        'name':'Page {}'.format(self.bot.emote.get(str(((i // 5) % 3) + 1))),
                                        'value':[]
                                    }
                                )
                            search_list.append((result[i].id, self.escape(result[i].name)))
                            if result[i].ranking is None:
                                fields[-1]['value'].append(
                                    "[{}](https://game.granbluefantasy.jp/#profile/{})\n".format(
                                        self.escape(result[i].name),
                                        result[i].id
                                    )
                                )
                            else:
                                fields[-1]['value'].append(
                                    "[{}](https://game.granbluefantasy.jp/#profile/{}) ▫️ **#{}**\n".format(
                                        self.escape(result[i].name),
                                        result[i].id,
                                        result[i].ranking
                                    )
                                )
                            if result[i].current is not None:
                                fields[-1]['value'].append("{:,}\n".format(result[i].current))
                            else:
                                fields[-1]['value'].append("n/a\n")
                            gwnum = result[i].gw
                    # create new embed
                    if len(fields) > 0:
                        if isinstance(fields[-1]['value'], list):
                            fields[-1]['value'] = "".join(fields[-1]['value'])
                        embeds.append(
                            self.bot.embed(
                                title="{} **Guild War {}**".format(
                                    self.bot.emote.get('gw'),
                                    gwnum
                                ),
                                description="Page **{}/{}**".format(
                                    x + 1,
                                    1 + len(result) // max_v
                                ),
                                fields=fields,
                                inline=True,
                                color=self.COLOR,
                                footer="Buttons expire in 3 minutes"
                            )
                        )
                        fields = []
                        search_results.append(search_list)
                        search_list = []
                # create embed with leftover
                if len(search_list) > 0:
                    embeds.append(
                        self.bot.embed(
                            title="{} **Guild War {}**".format(
                                self.bot.emote.get('gw'),
                                gwnum
                            ),
                            description="Page **{}/{}**".format(
                                x + 1,
                                1 + len(result) // max_v
                            ),
                            fields=fields,
                            inline=True,
                            color=self.COLOR,
                            footer="Buttons expire in 3 minutes"
                        )
                    )
                    search_results.append(search_list)
                    search_list = []
                view : PageRanking = PageRanking(
                    self.bot,
                    owner_id=inter.author.id,
                    embeds=embeds,
                    search_results=search_results,
                    color=self.COLOR,
                    stype=stype
                )
                await inter.edit_original_message(embed=embeds[0], view=view)
                view.message = await inter.original_message()
            except Exception as e:
                if str(e) != "Returning":
                    self.bot.logger.pushError("[GW] 'findranking' error:", e)
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="{} **Guild War**".format(
                                self.bot.emote.get('gw')
                            ),
                            description="An error occured",
                            color=self.COLOR
                        )
                    )

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(6, 60, commands.BucketType.guild)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def gbfg(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @gbfg.sub_command()
    async def recruit(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post all recruiting /gbfg/ crews"""
        await inter.response.defer()
        if not await self.bot.net.gbf_available():
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} /gbfg/ recruiting crews".format(
                        self.bot.emote.get(
                            'crew'
                        )
                    ),
                    description="Unavailable",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)
        else:
            # sort gbfg crews by average rank and availability
            sortedcrew : list[CrewData] = []
            c : str
            for c in self.bot.ranking.gbfgcrews_id:
                data : CrewData = await self.getCrewData(c, 2)
                if 'error' not in data and data['count'] != 30:
                    if len(sortedcrew) == 0:
                        sortedcrew.append(data)
                    else:
                        inserted : bool = False
                        i : int
                        for i in range(len(sortedcrew)):
                            if data['average'] >= sortedcrew[i]['average']:
                                sortedcrew.insert(i, data)
                                inserted = True
                                break
                        if not inserted:
                            sortedcrew.append(data)
            # output result
            fields : list[dict[str, str|list]] = []
            # column size
            size : int
            if len(sortedcrew) > 20:
                size = 15
            elif len(sortedcrew) > 10:
                size = 10
            else:
                size = 5
            slots : int = 0
            search_results : list[list[tuple[int|str]]] = []
            for i, v in enumerate(sortedcrew):
                if i % size == 0:
                    fields.append({'name':'Page {}'.format(self.bot.emote.get(str(len(fields) + 1))), 'value':[]})
                    search_results.append([])
                search_results[-1].append((v['id'], v['name']))
                fields[-1]['value'].append(
                    "Rank **{}** ▫️  **{}** ▫️ **{}** slot".format(
                        v['average'],
                        v['name'],
                        30 - v['count']
                    )
                )
                if 30 - v['count'] != 1:
                    fields[-1]['value'].append("s")
                fields[-1]['value'].append("\n")
                slots += 30 - v['count']
            field : dict[str, str|list]
            for field in fields:
                field['value'] = "".join(field['value'])
            embed : disnake.Embed = self.bot.embed(
                title="{} /gbfg/ recruiting crews ▫️ {} slots".format(
                    self.bot.emote.get('crew'),
                    slots
                ),
                fields=fields,
                inline=True,
                color=self.COLOR,
                timestamp=self.bot.util.UTC(),
                footer="Buttons expire in 100 seconds"
            )
            embeds : list[disnake.Embed] = [embed for i in range(len(search_results))]
            view : PageRanking = PageRanking(
                self.bot,
                owner_id=inter.author.id,
                embeds=embeds,
                search_results=search_results,
                color=self.COLOR,
                stype=True,
                timeout=100,
                enable_timeout_cleanup=True
            )
            await inter.edit_original_message(embed=embed, view=view)
            view.message = await inter.original_message()

    """_players()
    Retrieve the ranking data from all gbfg players and build embeds for the player command

    Parameters
    --------
    gbfgdata: Data from updateGBFGData()

    Returns
    --------
    Tuple:
        - embeds: List of embeds
        - final_results: List of results for each page
    """
    async def _players(self : GuildWar, gbfgdata : GBFGData) -> tuple[list[disnake.Embed], PageResultList]:
        try:
            embeds : list[disnake.Embed] = []
            final_results : PageResultList = []
            player_ranking : PlayerRanking = []
            dancho_ranking : PlayerRanking = []
            players : dict[str, str] = {} # player list
            danchos : dict[str, tuple[str, str]] = {} # captain list
            private : int = 0
            gwid : int|str|None
            # build dancho and player id list
            cid : str
            for cid in gbfgdata:
                danchos[str(gbfgdata[cid][2])] = (gbfgdata[cid][0], gbfgdata[cid][1])
                if len(gbfgdata[cid][3]) == 0:
                    private += 1
                    players[str(gbfgdata[cid][2])] = gbfgdata[cid][0]
                else:
                    for v in gbfgdata[cid][3]:
                        players[str(v)] = gbfgdata[cid][0]
            await asyncio.sleep(0)
            # query
            data : GWDBSearchResult|None = await self.bot.ranking.searchGWDB(
                "(" + ",".join(list(players.keys())) + ")",
                4
            )
            desc : str
            match private:
                case 0: desc = ""
                case 1: desc = "*1 crew is private*"
                case _: desc = "*{} crews are private*".format(private)
            # store result
            if data is not None and data[1] is not None:
                if data[2][1] is not None: # add timestamp if it exists
                    timestamp : datetime|None = data[2][1].timestamp
                    if timestamp is not None:
                        desc = "Updated: **{}** ago\n".format(
                            self.bot.util.delta2str(self.bot.util.JST() - timestamp, 0)
                        ) + desc
                if len(data[1]) > 0:
                    gwid = data[1][0].gw
                    res : Score
                    for res in data[1]:
                        player_ranking.append([players[str(res.id)], res.name, res.current, res.id, res.ranking])
                        if str(res.id) in danchos:
                            danchos.pop(str(res.id)) # remove successful dancho
                            dancho_ranking.append([players[str(res.id)], res.name, res.current, res.id, res.ranking])
            await asyncio.sleep(0)
            k : str
            v : tuple[str, str]
            for k, v in danchos.items(): # add n/a dancho
                dancho_ranking.append((v[0], v[1], None, k, None))
            # build dancho list (for emote separator)
            dancho_list : set[int] = {
                k[3] for k in dancho_ranking if k[3] is not None
            }
            await asyncio.sleep(0)
            if gwid is None:
                gwid = ""
            for captain in range(2):
                er : list[disnake.Embed]
                fr : PageResultList
                er, fr = await self.generate_player_ranking_embed(
                    (dancho_ranking if captain == 1 else player_ranking),
                    dancho_list,
                    "{} /gbfg/ GW{} Top {} Ranking".format(
                        self.bot.emote.get('gw'),
                        gwid,
                        ("Captain" if captain == 1 else "Player")
                    ),
                    desc,
                    captain * 2,
                    " - {} on page {}, {}".format(
                        ("Players" if captain == 1 else "Captains"),
                        (captain * 2 + 2) % 4 + 1,
                        (captain * 2 + 2) % 4 + 2
                    )
                )
                embeds.extend(er)
                final_results.extend(fr)
            return embeds, final_results
        except:
            return [], []

    """generate_player_ranking_embed()
    Coroutine to generate embeds from a PlayerRanking

    Parameters
    --------
    ranking: PlayerRanking, a list of player infos
    dancho_list: A set containing ID of captains. Pass empty set to ignore.
    title_string: The title used by embeds
    description: The description used by embeds
    page_offset: (Optional) Integer, offset added to the page
    footer_extra: (Optional) String appended to the embeds

    Returns
    --------
    Tuple:
        - embeds: List of embeds
        - final_results: List of results for each page
    """
    async def generate_player_ranking_embed(
        self : GuildWar,
        ranking : PlayerRanking,
        dancho_list : set[int],
        title_string : str,
        description : str,
        page_offset : int = 0,
        footer_extra : str = ""
    ) -> tuple[list[disnake.Embed], PageResultList]:
        embeds : list[disnake.Embed] = []
        final_results : PageResultList = []
        # sorting
        i : int
        j : int
        for i in range(len(ranking)):
            for j in range(i + 1, len(ranking)):
                if ranking[j][2] is not None and (ranking[i][2] is None or ranking[i][2] < ranking[j][2]):
                    ranking[i], ranking[j] = ranking[j], ranking[i]
        await asyncio.sleep(0)
        if len(ranking) >= 0:
            fields : list[dict[str, str|list]] = []
            search_results : PageResult = []
            # create field embeds
            element : PlayerEntry
            for i, element in enumerate(ranking):
                if i == 30:
                    break
                elif i % 15 == 0:
                    fields.append(
                        {
                            'name':'Page {}'.format(self.bot.emote.get(str(len(fields) + 1 + page_offset))),
                            'value':[]
                        }
                    )
                    search_results.append([])
                    await asyncio.sleep(0)
                rt : str # rank
                ht : str # honor
                ct : str # separator
                if element[4] is not None:
                    if element[4] >= 100000:
                        rt = "#**{}K**".format(element[4] // 1000)
                    else:
                        rt = "#**{}**".format(self.bot.util.valToStr(element[4]))
                    ht = " **{}**".format(self.bot.util.valToStr(element[2], 2))
                else:
                    rt = "**n/a** "
                    ht = ""
                ct = ' - ' if element[3] not in dancho_list else str(self.bot.emote.get('captain'))
                fields[-1]['value'].append(rt)
                fields[-1]['value'].append(ct)
                fields[-1]['value'].append(element[1]) # name
                if element[0] is not None:
                    fields[-1]['value'].append(" *")
                    fields[-1]['value'].append(element[0]) # crew
                    fields[-1]['value'].append("*")
                fields[-1]['value'].append(ht)
                fields[-1]['value'].append("\n")
                search_results[-1].append((element[3], element[1])) # id name
            field : dict[str, str|list]
            for field in fields:
                field['value'] = "".join(field['value'])
            embed : disnake.Embed = self.bot.embed(
                title=title_string,
                description=description,
                fields=fields,
                inline=True,
                color=self.COLOR,
                footer="Buttons expire in 100 seconds" + footer_extra
            )
            embeds.extend([embed for i in range(len(search_results))])
            final_results.extend(search_results)
        return embeds, final_results

    @gbfg.sub_command()
    async def players(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the /gbfg/ Top 30 (players or captains) per contribution"""
        await inter.response.defer()
        gbfgdata : GBFGData|None = await self.updateGBFGData() # get up to date data
        if gbfgdata is None:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} /gbfg/ Ranking".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="This command is only available during Guild War",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)
            return
        embeds : list[disnake.Embed]
        final_results : PageResultList
        embeds, final_results = await self._players(gbfgdata)
        if len(embeds) == 0:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} /gbfg/ Ranking".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="No players in the ranking",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)
        else:
            view = PageRanking(
                self.bot,
                owner_id=inter.author.id,
                embeds=embeds,
                search_results=final_results,
                color=self.COLOR,
                stype=False,
                timeout=100,
                enable_timeout_cleanup=True
            )
            await inter.edit_original_message(embed=embeds[0], view=view)
            view.message = await inter.original_message()

    """_gbfgranking()
    Get the /gbfg/ crew contribution and rank them

    Returns
    ----------
    tuple: Containing:
        - fields: Discord Embed fields containing the data
        - gwid: Integer GW ID
        - search_results: List of search results for PageRanking
    """
    async def _gbfgranking(self : GuildWar) -> tuple[list[disnake.Embed], PageResultList]:
        try:
            # build crew list using config.json list
            # query
            cdata : GWDBSearchResult|None = await self.bot.ranking.searchGWDB(
                "(" + ",".join(self.bot.ranking.gbfgcrews_id) + ")",
                14
            )
            if cdata is None or cdata[1] is None:
                return [], []
            await asyncio.sleep(0)
            # get gw id and timestamp
            gwid : int|str|None = cdata[1][0].gw
            day : int = 0 # will store further day forward detected
            timestamp : datetime|None = None
            if cdata[2][1] is not None:
                timestamp = cdata[2][1].timestamp
            embeds : list[disnake.Embed] = []
            final_results : PageResultList = []
            i : int
            # get day
            data : GWDBList
            for data in cdata[1]:
                day = max(day, data.day)
            sort_mode : int
            for sort_mode in range(3): # make 3 different rankings: honor, top speed, current speed
                footer : str
                match sort_mode:
                    case 1: # top speed
                        footer = "← Honor pages, Current Speed pages →"
                    case 2: # current speed
                        footer = "← Honor pages, Top Speed pages →"
                    case _: # default
                        footer = "← Top Speed pages, Current Speed pages →"
                tosort : dict[int, tuple[int, str, float|None, int|None, int|None]] = {}
                fields : list[dict[str, str|list]] = []
                for data in cdata[1]:
                    match sort_mode: # get and add data
                        case 1: # top speed
                            if data.top_speed is None or data.day < day:
                                continue
                            tosort[data.id] = (
                                data.id,
                                data.name,
                                data.top_speed,
                                data.ranking,
                                data.day
                            )
                        case 2: # current speed
                            if data.current_speed is None or data.day < day:
                                continue
                            tosort[data.id] = (
                                data.id,
                                data.name,
                                data.current_speed,
                                data.ranking,
                                data.day
                            )
                        case _: # default
                            if data.current is None or data.day < day:
                                continue
                            tosort[data.id] = (
                                data.id,
                                data.name,
                                data.current,
                                data.ranking,
                                data.day
                            )
                # sorting
                await asyncio.sleep(0)
                sorted : dict[int, tuple[int, str, float|None, int|None, int|None]] = []
                c : tuple[int, str, float|None, int|None, int|None]
                for c in tosort:
                    inserted : bool = False
                    for i in range(0, len(sorted)):
                        if tosort[c][2] > sorted[i][2]:
                            inserted = True
                            sorted.insert(i, tosort[c])
                            break
                    if not inserted:
                        sorted.append(tosort[c])
                await asyncio.sleep(0)
                # build embed fields
                if gwid is None:
                    gwid = ""
                search_results : PageResultList = []
                v : tuple[int, str, float|None, int|None, int|None]
                for i, v in enumerate(sorted):
                    if i % 15 == 0: # add extra at 15
                        fields.append(
                            {
                                'name':'Page {}'.format(self.bot.emote.get(str(len(fields) + 1 + len(embeds)))),
                                'value':[]
                            }
                        )
                        search_results.append([])
                        await asyncio.sleep(0)
                    fields[-1]['value'].append(
                        "#**{}** - {} - **{}".format(
                            self.bot.util.valToStr(v[3]),
                            v[1],
                            self.bot.util.valToStr(v[2], 2)
                        )
                    )
                    search_results[-1].append((v[0], v[1]))
                    if sort_mode > 0:
                        fields[-1]['value'].append("/min**\n")
                    else:
                        fields[-1]['value'].append("**\n")
                # embed content
                title : str = ["", "Top Speed ", "Current Speed "][sort_mode]
                desc : str = ""
                if timestamp is not None:
                    desc = "Updated: **{}** ago".format(self.bot.util.delta2str(self.bot.util.JST() - timestamp, 0))
                # creating embed
                if len(fields) == 0:
                    embed : disnake.Embed = self.bot.embed(
                        title="{} /gbfg/ GW{} {}Ranking".format(
                            self.bot.emote.get('gw'),
                            gwid,
                            title
                        ),
                        description=desc,
                        fields=[
                            {
                                'name':'Page {}'.format(self.bot.emote.get(str(1 + len(embeds)))),
                                'value':"No data currently available"
                            }
                        ],
                        inline=True,
                        color=self.COLOR,
                        footer="Buttons expire in 100 seconds - " + footer
                    )
                    final_results.append([])
                    embeds.append(embed)
                else:
                    # unranked crew message
                    notranked : int = len(self.bot.ranking.gbfgcrews_id) - len(cdata[1])
                    if notranked > 0:
                        fields[-1]['value'].append(
                            "**{}** unranked crew{}".format(
                                notranked,
                                's' if notranked > 1 else ''
                            )
                        )
                    # join field values
                    field : dict[str, str|list]
                    for field in fields:
                        field['value'] = "".join(field['value'])
                    # finalize this ranking embed
                    embed : disnake.Embed = self.bot.embed(
                        title="{} /gbfg/ GW{} {}Ranking".format(self.bot.emote.get('gw'), gwid, title),
                        description=desc,
                        fields=fields,
                        inline=True,
                        color=self.COLOR,
                        footer="Buttons expire in 100 seconds - " + footer
                    )
                    for i in range(len(search_results)):
                        final_results.append(search_results[i])
                        embeds.append(embed)
                    await asyncio.sleep(0)
            # return everything
            return embeds, final_results
        except Exception as e:
            self.bot.logger.pushError("test", e)
            return [], []

    @gbfg.sub_command(name="ranking")
    async def gbfgranking(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Sort and post all /gbfg/ crew per contribution or speed"""
        await inter.response.defer()
        embeds : list[disnake.Embed]
        final_results : PageResultList
        embeds, final_results = await self._gbfgranking() # see above
        if len(embeds) == 0:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} /gbfg/ Ranking".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="Unavailable",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)
        else:
            view = PageRanking(
                self.bot,
                owner_id=inter.author.id,
                embeds=embeds,
                search_results=final_results,
                color=self.COLOR,
                stype=True,
                timeout=100,
                enable_timeout_cleanup=True
            )
            await inter.edit_original_message(embed=embeds[0], view=view)
            view.message = await inter.original_message()

    """_supercrew()
    Retrieve the ranking data from all players registered in Rosetta and build embeds for the /gw rosetta command

    Returns
    --------
    Tuple:
        - embeds: List of embeds
        - final_results: List of results for each page
    """
    async def _supercrew(self : GuildWar) -> tuple[list[disnake.Embed], PageResultList]:
        try:
            player_ranking : PlayerRanking = []
            players : dict[str, str] = {} # player list
            gwid : int|str|None
            # build player id list
            players : list[str] = [str(v) for v in self.bot.data.save["gbfids"].values()]
            await asyncio.sleep(0)
            # query
            data : GWDBSearchResult|None = await self.bot.ranking.searchGWDB("(" + ",".join(players) + ")", 4)
            desc : str = ""
            # store result
            if data is not None and data[1] is not None:
                if data[2][1] is not None: # add timestamp if it exists
                    timestamp : datetime|None = data[2][1].timestamp
                    if timestamp is not None:
                        desc = "Updated: **{}** ago\n".format(
                            self.bot.util.delta2str(self.bot.util.JST() - timestamp, 0)
                        ) + desc
                if len(data[1]) > 0:
                    gwid = data[1][0].gw
                    res : Score
                    for res in data[1]:
                        player_ranking.append([None, res.name, res.current, res.id, res.ranking])
            desc += "-# Use {} to be added to the list".format(self.bot.util.command2mention("gbf profile set"))
            await asyncio.sleep(0)
            if gwid is None:
                gwid = ""
            return await self.generate_player_ranking_embed(
                player_ranking,
                set(),
                "{} Rosetta GW{} Top Player Ranking".format(
                    self.bot.emote.get('gw'),
                    gwid
                ),
                desc
            )
        except:
            return [], []

    @gw.sub_command()
    async def rosetta(self, inter: disnake.GuildCommandInteraction):
        """Post the Top 30 Players registered in Rosetta per contribution"""
        await inter.response.defer()
        embeds : list[disnake.Embed]
        final_results : PageResultList
        embeds, final_results = await self._supercrew()
        if not self.isGWRunning():
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Rosetta Ranking".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="This command is only available during Guild War",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)
        elif len(embeds) == 0:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Rosetta Ranking".format(
                        self.bot.emote.get(
                            'gw'
                        )
                    ),
                    description="No players in the ranking",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)
        else:
            view = PageRanking(
                self.bot,
                owner_id=inter.author.id,
                embeds=embeds,
                search_results=final_results,
                color=self.COLOR,
                stype=False,
                timeout=100,
                enable_timeout_cleanup=True
            )
            await inter.edit_original_message(embed=embeds[0], view=view)
            view.message = await inter.original_message()
