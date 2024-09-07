import disnake
from disnake.ext import commands
import asyncio
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from views import BaseView
from datetime import datetime, timedelta
import random
import math
import re
import json
from bs4 import BeautifulSoup
import html
from urllib.parse import unquote
import statistics
from views.page import Page, PageRanking

# ----------------------------------------------------------------------------------------------------------------
# Guild War Cog
# ----------------------------------------------------------------------------------------------------------------
# Commands related to Unite and Fight and Granblue Fantasy Crews
# ----------------------------------------------------------------------------------------------------------------

class GuildWar(commands.Cog):
    """Unite & Fight and Crew commands."""
    COLOR = 0xff0000
    YOU_MEAT_REGEX = re.compile('(?<!.)(\\d+(\\.\\d+)?)([kK])?')
    FIGHTS = {
        "EX": {"token":56.0, "rally_token":3.84, "AP":30, "meat_cost":0, "honor":64000, "hp":20000000},
        "EX+": {"token":66.0, "rally_token":7.56, "AP":30, "meat_cost":0, "honor":126000, "hp":35000000},
        "NM90": {"token":83.0, "rally_token":18.3, "AP":30, "meat_cost":5, "honor":305000, "hp":50000000},
        "NM95": {"token":111.0, "rally_token":54.6, "AP":40, "meat_cost":10, "honor":910000, "hp":131250000},
        "NM100": {"token":168.0, "rally_token":159.0, "AP":50, "meat_cost":20, "honor":2650000, "hp":288750000},
        "NM150": {"token":257.0, "rally_token":246.0, "AP":50, "meat_cost":20, "honor":4100000, "hp":288750000},
        "NM200": {"token":338.0, "rally_token":800.98, "AP":50, "meat_cost":20, "honor":13350000, "hp":577500000},
        "NM250": {"token":338.0, "rally_token":800.98, "AP":50, "meat_cost":0, "honor":30000000, "hp":1000000000} # PLACEHOLDER
    }
    MEAT_PER_BATTLE_AVG = 20 # EX+ meat drop

    BOX_COST = [
        (1, 1600),
        (4, 2400),
        (45, 2000),
        (80, 10000),
        (None, 15000)
    ]

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.crewcache = {}

    def startTasks(self) -> None:
        self.bot.runTask('check_buff', self.checkGWBuff)
        self.bot.runTask('check_ranking', self.bot.ranking.checkGWRanking)

    """checkGWBuff()
    Bot Task managing the buff alert of the (You) server
    """
    async def checkGWBuff(self) -> None:
        self.getGWState()
        if self.bot.data.save['gw']['state'] is False or len(self.bot.data.save['gw']['buffs']) == 0: return
        try:
            guild = self.bot.get_guild(self.bot.data.config['ids'].get('you_server', 0))
            if guild is None:
                self.bot.logger.push("[TASK] 'checkgwbuff' Task Cancelled, no guild found")
            channel = self.bot.get_channel(self.bot.data.config['ids'].get('you_announcement', 0))
            if 'skip' not in self.bot.data.save['gw']:
                self.bot.data.save['gw']['skip'] = False
                self.bot.data.pending = True
            gl_role = guild.get_role(self.bot.data.config['ids'].get('gl', 0))
            fo_role = guild.get_role(self.bot.data.config['ids'].get('fo', 0))
            buff_role = [[guild.get_role(self.bot.data.config['ids'].get('atkace', 0)), 'atkace'], [guild.get_role(self.bot.data.config['ids'].get('deface', 0)), 'deface']]
            msg = []
            while self.bot.data.save['gw']['state'] and (len(self.bot.data.save['gw']['buffs']) > 0 or len(msg) != 0):
                current_time = self.bot.util.JST() + timedelta(seconds=32)
                if len(self.bot.data.save['gw']['buffs']) > 0 and current_time >= self.bot.data.save['gw']['buffs'][0][0]:
                    msg = []
                    if (current_time - self.bot.data.save['gw']['buffs'][0][0]) < timedelta(seconds=200):
                        if self.bot.data.save['gw']['buffs'][0][1]:
                            for r in buff_role:
                                msg.append("{} {}\n".format(self.bot.emote.get(r[1]), r[0].mention))
                        if self.bot.data.save['gw']['buffs'][0][2]:
                            msg.append("{} {}\n".format(self.bot.emote.get('foace'), fo_role.mention))
                        if self.bot.data.save['gw']['buffs'][0][3]:
                            msg.append('*Buffs in* **5 minutes**')
                        else:
                            msg.append('Buffs now!')
                        if self.bot.data.save['gw']['buffs'][0][4]: msg.append('\n**(Use everything this time! They are reset later.)**')
                        msg.append("\nhttps://game.granbluefantasy.jp/#event/teamraid{}/guild_ability".format(str(self.bot.data.save['gw']['id']).zfill(3)))
                        if self.bot.data.save['gw']['skip']:
                            msg = []
                        if not self.bot.data.save['gw']['buffs'][0][3]:
                            self.bot.data.save['gw']['skip'] = False
                    self.bot.data.save['gw']['buffs'].pop(0)
                    self.bot.data.pending = True
                else:
                    if len(msg) > 0:
                        await channel.send("{} {}\n{}".format(self.bot.emote.get('captain'), gl_role.mention, ''.join(msg)))
                        msg = []
                    if len(self.bot.data.save['gw']['buffs']) > 0:
                        d = self.bot.data.save['gw']['buffs'][0][0] - current_time
                        if d.seconds > 1:
                            await asyncio.sleep(d.seconds-1)
            if len(msg) > 0:
                await channel.send("{} {}\n{}".format(self.bot.emote.get('captain'), gl_role.mention, ''.join(msg)))
        except asyncio.CancelledError:
            self.bot.logger.push("[TASK] 'checkgwbuff' Task Cancelled")
        except Exception as e:
            self.bot.logger.pushError("[TASK] 'checkgwbuff' Task Error:", e)
        await self.bot.send('debug', embed=self.bot.embed(color=self.COLOR, title="User task ended", description="check_buff", timestamp=self.bot.util.UTC()))

    """buildDayList()
    Generate the day list used by the gw command
    
    Returns
    --------
    list: List of lists containing: The day string, the day key and the next day key
    """
    def buildDayList(self) -> list: # used by the gw schedule command
        return [
            ["{} Automatic BAN Execution".format(self.bot.emote.get('kmr')), "BW", ""], # for memes
            ["{} Preliminaries".format(self.bot.emote.get('gold')), "Preliminaries", "Interlude"],
            ["{} Interlude".format(self.bot.emote.get('wood')), "Interlude", "Day 1"],
            ["{} Day 1".format(self.bot.emote.get('1')), "Day 1", "Day 2"],
            ["{} Day 2".format(self.bot.emote.get('2')), "Day 2", "Day 3"],
            ["{} Day 3".format(self.bot.emote.get('3')), "Day 3", "Day 4"],
            ["{} Day 4".format(self.bot.emote.get('4')), "Day 4", "Day 5"],
            ["{} Final Rally".format(self.bot.emote.get('red')), "Day 5", "End"]
        ]

    """isGWRunning()
    Check the GW state and returns if the GW is on going.
    Clear the data if it ended.
    
    Returns
    --------
    bool: True if it's running, False if it's not
    """
    def isGWRunning(self) -> bool: # return True if a guild war is on going
        if self.bot.data.save['gw']['state'] is True:
            current_time = self.bot.util.JST()
            if current_time < self.bot.data.save['gw']['dates']["Preliminaries"]:
                return False
            elif current_time >= self.bot.data.save['gw']['dates']["End"]:
                self.bot.data.save['gw']['state'] = False
                self.bot.data.save['gw']['dates'] = {}
                self.bot.cancelTask('check_buff')
                self.bot.data.pending = True
                return False
            else:
                return True
        else:
            return False

    """escape()
    Proper markdown escape player names
    
    Parameters
    ----------
    s: String to escape
    lite: If True, less escapes are applied
    
    Returns
    --------
    str: Escaped string
    """
    def escape(self, s : str, lite : bool = False) -> str:
        # add the RLO character before
        x = html.unescape(s)
        if lite: return '\u202d' + x.replace('\\', '\\\\').replace('`', '\\`')
        else: return '\u202d' + x.replace('\\', '\\\\').replace('`', '\'').replace('*', '\\*').replace('_', '\\_').replace('{', '\\{').replace('}', '\\}').replace('[', '').replace(']', '').replace('(', '\\(').replace(')', '\\)').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('.', '\\.').replace('!', '\\!').replace('|', '\\|')

    """htmlescape()
    Escape special characters into html notation (used for crew and player names)
    
    Parameters
    ----------
    s: String to escape
    
    Returns
    --------
    str: Escaped string
    """
    def htmlescape(self, s : str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace('\'', "&#039;")

    """dayCheck()
    Check if the we are in the specified GW day
    
    Parameters
    ----------
    current: Current time, JST
    day: Day to compare to
    final_day: If True, check for the final GW day (it's shorter)
    
    Returns
    --------
    bool: True if successful, False if not
    """
    def dayCheck(self, current : datetime, day : datetime, final_day : bool = False) -> bool:
        d = day - current
        if current < day and (final_day or d >= timedelta(seconds=25200)):
            return True
        return False

    """getGWState()
    Return the state of the Unite & Fight event
    
    Returns
    --------
    str: Unite & Fight state
    """
    def getGWState(self) -> str:
        if self.bot.data.save['gw']['state'] is True:
            current_time = self.bot.util.JST()
            if current_time < self.bot.data.save['gw']['dates']["Preliminaries"]:
                d = self.bot.data.save['gw']['dates']["Preliminaries"] - current_time
                return "{} Guild War starts in **{}**".format(self.bot.emote.get('gw'), self.bot.util.delta2str(d, 2))
            elif current_time >= self.bot.data.save['gw']['dates']["End"]:
                self.bot.data.save['gw']['state'] = False
                self.bot.data.save['gw']['dates'] = {}
                self.bot.cancelTask('check_buff')
                self.bot.data.save['youtracker'] = None
                self.bot.data.pending = True
                return ""
            elif current_time > self.bot.data.save['gw']['dates']["Day 5"]:
                d = self.bot.data.save['gw']['dates']["End"] - current_time
                return "{} Final Rally is on going\n{} Guild War ends in **{}**".format(self.bot.emote.get('mark_a'), self.bot.emote.get('time'), self.bot.util.delta2str(d))
            elif current_time > self.bot.data.save['gw']['dates']["Day 1"]:
                it = ['Day 5', 'Day 4', 'Day 3', 'Day 2', 'Day 1']
                for i in range(1, len(it)): # loop to not copy paste this 5 more times
                    if current_time > self.bot.data.save['gw']['dates'][it[i]]:
                        d = self.bot.data.save['gw']['dates'][it[i-1]] - current_time
                        if d < timedelta(seconds=25200): msg = "{} {} ended".format(self.bot.emote.get('mark_a'), it[i])
                        else: msg = "{} GW {} is on going (Time left: **{}**)".format(self.bot.emote.get('mark_a'), it[i], self.bot.util.delta2str(self.bot.data.save['gw']['dates'][it[i]] + timedelta(seconds=61200) - current_time))
                        if i == 1: return "{}\n{} {} starts in **{}**".format(msg, self.bot.emote.get('time'), it[i-1].replace('Day 5', 'Final Rally'), self.bot.util.delta2str(d))
                        else: return "{}\n{} {} starts in **{}**".format(msg, self.bot.emote.get('time'), it[i-1], self.bot.util.delta2str(d))
            elif current_time > self.bot.data.save['gw']['dates']["Interlude"]:
                d = self.bot.data.save['gw']['dates']["Day 1"] - current_time
                return "{} Interlude is on going\n{} Day 1 starts in **{}**".format(self.bot.emote.get('mark_a'), self.bot.emote.get('time'), self.bot.util.delta2str(d))
            elif current_time > self.bot.data.save['gw']['dates']["Preliminaries"]:
                d = self.bot.data.save['gw']['dates']['Interlude'] - current_time
                if d < timedelta(seconds=25200): msg = "{} Preliminaries ended".format(self.bot.emote.get('mark_a'))
                else: msg = "{} Preliminaries are on going (Time left: **{}**)".format(self.bot.emote.get('mark_a'), self.bot.util.delta2str(self.bot.data.save['gw']['dates']["Preliminaries"] + timedelta(seconds=104400) - current_time, 2))
                return "{}\n{} Interlude starts in **{}**".format(msg, self.bot.emote.get('time'), self.bot.util.delta2str(d, 2))
            else:
                return ""
        else:
            return ""

    """getGWTimeLeft()
    Return the time left until the next unite & fight day
    
    Parameters
    --------
    current_time: Optional datetime
    
    Returns
    --------
    timedelta: Time left or None if error
    """
    def getGWTimeLeft(self, current_time : Optional[datetime] = None) -> Optional[timedelta]:
        if self.bot.data.save['gw']['state'] is False:
            return None
        if current_time is None: current_time = self.bot.util.JST()
        if current_time < self.bot.data.save['gw']['dates']["Preliminaries"] or current_time >= self.bot.data.save['gw']['dates']["Day 5"]:
            return None
        elif current_time > self.bot.data.save['gw']['dates']["Day 1"]:
            it = ['Day 5', 'Day 4', 'Day 3', 'Day 2', 'Day 1']
            for i in range(1, len(it)): # loop to not copy paste this 5 more times
                if current_time > self.bot.data.save['gw']['dates'][it[i]]:
                    if self.bot.data.save['gw']['dates'][it[i-1]] - current_time < timedelta(seconds=25200): return None
                    return self.bot.data.save['gw']['dates'][it[i]] + timedelta(seconds=61200) - current_time
            return None
        elif current_time > self.bot.data.save['gw']['dates']["Interlude"]:
            return self.bot.data.save['gw']['dates']["Day 1"] - current_time
        elif current_time > self.bot.data.save['gw']['dates']["Preliminaries"]:
            if self.bot.data.save['gw']['dates']["Interlude"] - current_time < timedelta(seconds=25200): return None
            return self.bot.data.save['gw']['dates']["Preliminaries"] + timedelta(seconds=104400) - current_time
        return None

    """getNextBuff()
    Return the time left until the next buffs for the (You) server
    
    Parameters
    ----------
    inter: Command interaction (to check the server)
    
    Returns
    --------
    str: Time left, empty if error
    """
    def getNextBuff(self, inter: disnake.GuildCommandInteraction) -> str: # for the (you) crew, get the next set of buffs to be called
        if self.bot.data.save['gw']['state'] is True and inter.guild.id == self.bot.data.config['ids'].get('you_server', 0):
            current_time = self.bot.util.JST()
            if current_time < self.bot.data.save['gw']['dates']["Preliminaries"]:
                return ""
            for b in self.bot.data.save['gw']['buffs']:
                if not b[3] and current_time < b[0]:
                    msg = "{} Next buffs in **{}** (".format(self.bot.emote.get('question'), self.bot.util.delta2str(b[0] - current_time, 2))
                    if b[1]:
                        msg += "Attack {}, Defense {}".format(self.bot.emote.get('atkace'), self.bot.emote.get('deface'))
                        if b[2]:
                            msg += ", FO {}".format(self.bot.emote.get('foace'))
                    elif b[2]:
                        msg += "FO {}".format(self.bot.emote.get('foace'))
                    msg += ")"
                    return msg
        return ""

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 20, commands.BucketType.user)
    @commands.max_concurrency(16, commands.BucketType.default)
    async def gw(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @gw.sub_command()
    async def time(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the GW schedule"""
        await inter.response.defer()
        if self.bot.data.save['gw']['state'] is True:
            try:
                current_time = self.bot.util.JST()
                em = self.bot.util.formatElement(self.bot.data.save['gw']['element'])
                title = "{} **Guild War {}** {} **{}**\n".format(self.bot.emote.get('gw'), self.bot.data.save['gw']['id'], em, self.bot.util.time(current_time, removejst=True))
                description = []
                day_list = self.buildDayList()
                if current_time < self.bot.data.save['gw']['dates']["End"]:
                    for it in day_list:
                        if it[1] == "BW":
                            d = self.bot.data.save['gw']['dates']["Preliminaries"] - timedelta(days=random.randint(1, 4))
                            if current_time < d and random.randint(1, 8) == 1:
                                description.append(it[0] + " **{}**\n".format(self.bot.util.time(d, removejst=True)))
                        else:
                            if self.dayCheck(current_time, self.bot.data.save['gw']['dates'][it[2]], it[1]=="Day 5") or (it[1] == "Interlude" and self.dayCheck(current_time, self.bot.data.save['gw']['dates'][it[2]] + timedelta(seconds=25200), False)):
                                description.append(it[0] + ": **{}**\n".format(self.bot.util.time(self.bot.data.save['gw']['dates'][it[1]], removejst=True)))
                else:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Not available", color=self.COLOR))
                    self.bot.data.save['gw']['state'] = False
                    self.bot.data.save['gw']['dates'] = {}
                    self.bot.cancelTask('check_buff')
                    self.bot.data.save['youtracker'] = None
                    self.bot.data.pending = True
                    await self.bot.util.clean(inter, 40)
                    return

                try:
                    description.append(self.getGWState())
                except:
                    pass

                try:
                    description.append('\n' + self.getNextBuff(inter))
                except:
                    pass

                await inter.edit_original_message(embed=self.bot.embed(title=title, description=''.join(description), color=self.COLOR))
            except Exception as e:
                self.bot.logger.pushError("[GW] In 'gw time' command:", e)
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Not available", color=self.COLOR))
            await self.bot.util.clean(inter, 40)

    @gw.sub_command()
    async def buff(self, inter: disnake.GuildCommandInteraction) -> None:
        """Check when is the next GW buff ((You) Server Only)"""
        try:
            await inter.response.defer()
            if inter.guild.id != self.bot.data.config['ids'].get('you_server', -1):
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable in this server", color=self.COLOR))
                return
            d = self.getNextBuff(inter)
            if d != "":
                await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War (You) Buff status".format(self.bot.emote.get('gw')), description=d, color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War (You) Buff status".format(self.bot.emote.get('gw')), description="Only available when Guild War is on going", color=self.COLOR))
                await self.bot.util.clean(inter, 40)
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
            self.bot.logger.pushError("[GW] In 'gw buff' command:", e)
            await self.bot.util.clean(inter, 40)

    @gw.sub_command(name="ranking")
    async def gwranking(self, inter: disnake.GuildCommandInteraction) -> None:
        """Retrieve the current GW ranking"""
        try:
            await inter.response.defer()
            if self.bot.data.save['gw']['state'] is False or self.bot.util.JST() < self.bot.data.save['gw']['dates']["Preliminaries"] or self.bot.data.save['gw']['ranking'] is None:
                await inter.edit_original_message(embed=self.bot.embed(title="Ranking unavailable", color=self.COLOR))
            else:
                fields = [{'name':'**Crew Ranking**', 'value':''}, {'name':'**Player Ranking**', 'value':''}]
                for x in [0, 1]:
                    for c in self.bot.data.save['gw']['ranking'][x]:
                        if int(c) < 1000:
                            fields[x]['value'] += "**#{:}** - {:,}".format(c, self.bot.data.save['gw']['ranking'][x][c])
                        elif int(c) % 1000 != 0:
                            fields[x]['value'] += "**#{:,}.{:,}K** - {:,}".format(int(c)//1000, (int(c)%1000)//100, self.bot.data.save['gw']['ranking'][x][c])
                        else:
                            fields[x]['value'] += "**#{:,}K** - {:,}".format(int(c)//1000, self.bot.data.save['gw']['ranking'][x][c])
                        if c in self.bot.data.save['gw']['ranking'][2+x] and self.bot.data.save['gw']['ranking'][2+x][c] != 0:
                            fields[x]['value'] += " - {}/min".format(self.bot.util.valToStr(self.bot.data.save['gw']['ranking'][2+x][c]))
                        fields[x]['value'] += "\n"
                    if fields[x]['value'] == '': fields[x]['value'] = 'Unavailable'

                em = self.bot.util.formatElement(self.bot.data.save['gw']['element'])
                d = self.bot.util.JST() - self.bot.data.save['gw']['ranking'][4]
                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War {}** {}".format(self.bot.emote.get('gw'), self.bot.data.save['gw']['id'], em), description="Updated: **{}** ago".format(self.bot.util.delta2str(d, 0)), fields=fields, footer="Update on minute 5, 25 and 45", timestamp=self.bot.util.UTC(), inline=True, color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[GW] In 'gw ranking' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))

    @gw.sub_command()
    async def estimation(self, inter: disnake.GuildCommandInteraction) -> None:
        """Estimatation of the GW ranking cutoffs"""
        await inter.response.defer()
        current_time =  self.bot.util.JST()
        if self.bot.data.save['gw']['state'] is False or current_time < self.bot.data.save['gw']['dates']["Preliminaries"] or current_time >= (self.bot.data.save['gw']['dates']["Day 5"] - timedelta(seconds=25200)) or self.bot.data.save['gw']['ranking'] is None or 'estimation' not in self.bot.data.save['gw']:
            await inter.edit_original_message(embed=self.bot.embed(title="Estimation unavailable", description="", color=self.COLOR))
        else:
            update_time = self.bot.data.save['gw']['ranking'][4]
            elapsed_seconds = int((update_time - self.bot.data.save['gw']['dates']['Preliminaries']).total_seconds())
            if elapsed_seconds < 1200:
                await inter.edit_original_message(embed=self.bot.embed(title="Estimation unavailable", description="Try again in a little while", color=self.COLOR))
            else:
                try:
                    index = (elapsed_seconds - 1200) // 1200
                    mods = [{}, {}]
                    for i in [0, 1]:
                        for rank in self.bot.data.save['gw']['ranking'][i]:
                            try:
                                if rank not in self.bot.data.save['gw']['estimation'][i]: raise Exception()
                                mods[i][rank] = self.bot.data.save['gw']['ranking'][i][rank] / self.bot.data.save['gw']['estimation'][i][rank][index]
                            except:
                                pass
                
                    embeds = []
                    for final in [0, 1]:
                        target_index = -1
                        if final == 1 or update_time >= self.bot.data.save['gw']['dates']['Day 4']:
                            current_time_left = self.bot.data.save['gw']['dates']['Day 5'] - timedelta(seconds=25200) - current_time
                            target_index = -1
                        else:
                            for d in ['Interlude', 'Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5']:
                                if update_time < self.bot.data.save['gw']['dates'][d]:
                                    current_time_left = self.bot.data.save['gw']['dates'][d] - current_time
                                    target_index = (int((self.bot.data.save['gw']['dates'][d] - self.bot.data.save['gw']['dates']['Preliminaries']).total_seconds()) - 1200) // 1200
                                    break
                        fields = [{'name':'**Crew Ranking**', 'value':''}, {'name':'**Player Ranking**', 'value':''}]
                        for i in [0, 1]:
                            for rank in mods[i]:
                                msg = ""
                                if int(rank) < 1000:
                                    msg += "**#{}** ▫️ ".format(rank)
                                elif int(rank) % 1000 != 0:
                                    msg += "**#{}.{}K** ▫️ ".format(int(rank)//1000, (int(rank)%1000)//100)
                                else:
                                    msg += "**#{}K** ▫️ ".format(int(rank)//1000)
                                try:
                                    msg += "{} (".format(self.bot.util.valToStr(self.bot.data.save['gw']['estimation'][i][rank][target_index]*mods[i][rank], 2))
                                    mod = mods[i][rank] - 1
                                    if mod > 0: msg += "+"
                                    msg += "{:.1f}%)\n".format(mod*100)
                                    fields[i]['value'] += msg
                                except:
                                    pass
                            if fields[i]['value'] == "":
                                fields[i]['value'] = "Unavailable"
                        
                        if current_time_left.total_seconds() < 0:
                            msg = ""
                        else:
                            if current_time_left.days > 0: timestring = self.bot.util.delta2str(current_time_left, 2)
                            else: timestring = self.bot.util.delta2str(current_time_left, 1)
                            if target_index == -1: msg = "Time left: **{}** ▫️ ".format(timestring)
                            else: msg = "Next Day: **{}** ▫️ ".format(timestring)
                        msg += "Updated: **{}** ago\n".format(self.bot.util.delta2str(current_time - update_time, 0))
                        if target_index == -1:
                            msg += "**Ending** "
                            title = "Ending Estimation"
                        else:
                            msg += "**Today** "
                            title = "Today Estimation"
                        msg += "projection, always **take it with a grain of salt**"
                        embeds.append(self.bot.embed(title="{} **Guild War {} {} {}**".format(self.bot.emote.get('gw'), self.bot.data.save['gw']['id'], self.bot.util.formatElement(self.bot.data.save['gw']['element']), title), description=msg, fields=fields, footer="https://gbf.wiki/User:Neofaucheur/Unite_and_Fight_Data", timestamp=self.bot.util.UTC(), inline=True, color=self.COLOR))
                        if target_index == -1:
                            break
                    if len(embeds) == 0:
                        await inter.edit_original_message(embed=self.bot.embed(title="Estimation unavailable", description="", color=self.COLOR))
                    elif len(embeds) > 1:
                        view = Page(self.bot, owner_id=inter.author.id, embeds=embeds, timeout=100)
                        await inter.edit_original_message(embed=embeds[0], view=view)
                        view.message = await inter.original_message()
                    else:
                        await inter.edit_original_message(embed=embeds[0])
                except Exception as e:
                    self.bot.logger.pushError("[GW] In 'estimation' command:", e)
                    await inter.edit_original_message(embed=self.bot.embed(title="Estimation unavailable", description="", color=self.COLOR))

    """getCrewSummary()
    Get a GBF crew summary (what you see on the main page of a crew)
    
    Parameters
    ----------
    cid: Crew id
    
    Returns
    --------
    dict: Crew data, None if error
    """
    async def getCrewSummary(self, cid : int) -> Optional[dict]:
        res = await self.bot.net.requestGBF("guild_main/content/detail/{}".format(cid), expect_JSON=True)
        if res is None: return None
        else:
            soup = BeautifulSoup(unquote(res['data']), 'html.parser')
            try:
                summary = soup.find_all("div", class_="prt-status-summary")[0].findChildren("div", class_="prt-status-value", recursive=True)
                data = {}
                data['count'] = int(summary[0].string)
                data['average'] = int(summary[1].string)
                data['online'] = int(summary[2].string)
                return data
            except:
                return None

    """getCrewData()
    Get a GBF crew data, including its player list if public
    
    Parameters
    ----------
    target: String, can be a crew id or a crew name registered in config.json
    mode: Integer: 0=all, 1=main page data only, 2=main page and summary | add 10 to skip the cache check
    
    Returns
    --------
    dict: Crew data, None if error
    """
    async def getCrewData(self, target : str, mode : int = 0) -> Optional[dict]:
        if not await self.bot.net.gbf_available(): # check for maintenance
            return {'error':'Game is in maintenance'}
        tid = self.bot.util.gbfgstr2crewid(target)
        gwdata = None
        # check id validityy
        try:
            tid = int(tid)
        except:
            if tid == "":
                return {'error':"Please input the ID or the name of the crew\nOnly some crews are registered, please input an ID instead\nYou can try {} to search for a specific crew".format(self.bot.util.command2mention('gw find crew'))}
            else:
                gwdata = await self.bot.ranking.searchGWDB(tid, 11)
                if len(gwdata[1]) == 1:
                    tid = gwdata[1][0].id
                else:
                    return {'error':"Invalid name `{}`\nOnly some crews are registered, please input an ID instead\nYou can try {} to search for a specific crew".format(tid, self.bot.util.command2mention('gw find crew'))}
        if tid < 0 or tid >= 10000000:
            return {'error':'Out of range ID'}

        if mode >= 10:
            skipcache = True
            mode -= 10
        else: skipcache = False

        crew = {'scores':[], 'id':tid}
        if not skipcache and tid in self.crewcache: # public crews are stored until next reboot (to limit the request amount)
            crew = self.crewcache[tid]
            if mode > 0: return crew
        else:
            for i in range(0, 4): # for each page (page 0 being the crew page, 1 to 3 being the crew page
                if i > 0 and mode > 0: break
                get = await self.requestCrew(tid, i)
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
                        crew['ship'] = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/guild/thumb/top/{}.png".format(get['ship_img'])
                        crew['ship_element'] = {"10001":"wind", "20001":"fire", "30001":"water", "40001":"earth", "50001":"light", "60001":"dark"}.get(get['ship_img'].split('_', 1)[0], 'gw')
                        crew['leader'] = html.unescape(get['leader_name'])
                        crew['leader_id'] = get['leader_user_id']
                        crew['donator'] = html.unescape(get['most_donated_name'])
                        crew['donator_id'] = get['most_donated_id']
                        crew['donator_amount'] = get['most_donated_lupi']
                        crew['message'] = html.unescape(get['introduction'])
                    else:
                        if 'player' not in crew: crew['player'] = []
                        for p in get['list']:
                            crew['player'].append({'id':p['id'], 'name':html.unescape(p['name']), 'level':p['level'], 'is_leader':p['is_leader'], 'member_position':p['member_position'], 'honor':None}) # honor is a placeholder
            
            if mode == 1: return crew
            data = await self.getCrewSummary(tid)
            if data is not None:
                crew = {**crew, **data}
            if mode > 0: return crew
            if not crew['private']: self.crewcache[tid] = crew # only cache public crews

        # get the last gw score
        crew['scores'] = []
        if gwdata is None:
            gwdata = await self.bot.ranking.searchGWDB(tid, 12)
        for n in range(0, 2):
            try:
                if gwdata[n][0].ranking is None or gwdata[n][0].day != 4:
                    crew['scores'].append("{} GW**{}** | {} | **{:,}** pts".format(self.bot.emote.get('gw'), gwdata[n][0].gw, ('Total Day {}'.format(gwdata[n][0].day) if gwdata[n][0].day > 0 else 'Total Prelim.'), gwdata[n][0].current))
                else:
                    crew['scores'].append("{} GW**{}** | #**{}** | **{:,}** pts".format(self.bot.emote.get('gw'), gwdata[n][0].gw, gwdata[n][0].ranking, gwdata[n][0].current))
                if gwdata[n][0].top_speed is not None: crew['scores'][-1] += " | Top **{}/m.**".format(self.bot.util.valToStr(gwdata[n][0].top_speed, 2))
                if gwdata[n][0].current_speed is not None and gwdata[n][0].current_speed > 0: crew['scores'][-1] += " | Last **{}/m.**".format(self.bot.util.valToStr(gwdata[n][0].current_speed, 2))
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
    """
    async def processCrewData(self, crew : dict, mode : int = 0) -> tuple:
        # embed initialization
        title = "\u202d{} **{}**".format(self.bot.emote.get(crew['ship_element']), self.bot.util.shortenName(crew['name']))
        if 'count' in crew: title += "▫️{}/30".format(crew['count'])
        if 'average' in crew: title += "▫️Rank {}".format(crew['average'])
        if 'online' in crew: title += "▫️{} online".format(crew['online'])
        description = ["💬 `{}`".format(self.escape(crew['message'], True))]
        footer = ""
        fields = []

        # append GW scores if any
        for s in crew['scores']:
            description.append("\n{}".format(s))
        await asyncio.sleep(0)

        if crew['private']:
            description.append('\n{} [{}](https://game.granbluefantasy.jp/#profile/{}) ▫️ *Crew is private*'.format(self.bot.emote.get('captain'), crew['leader'], crew['leader_id']))
        else:
            footer = "Public crew members updated daily"
            # get GW data
            match mode:
                case 2: gwstate = True
                case 1: gwstate = False
                case _: gwstate = self.isGWRunning()
            players = crew['player'].copy()
            gwid = None
            if gwstate:
                total = 0
                unranked = 0
                median = []
                # retrieve player honor
                player_list = {}
                for i in players:
                    player_list[i['id']] = i
                data = await self.bot.ranking.searchGWDB("("+",".join(list(player_list))+")", 4)
                await asyncio.sleep(0)
                if data is not None and data[1] is not None:
                    for honor in data[1]:
                        if gwid is None: gwid = honor.gw
                        total += honor.current
                        median.append(honor.current)
                        player_list[str(honor.id)]['honor'] = honor.current
                        unranked += 1
                unranked = len(players) - unranked
                for i in range(unranked):
                    median.append(0)
                # sorting
                for i in range(0, len(players)):
                    if i > 0 and players[i]['honor'] is not None:
                        for j in range(0, i):
                            if players[j]['honor'] is None or players[i]['honor'] > players[j]['honor']:
                                players[i], players[j] = players[j], players[i]
                if gwid and len(players) - unranked > 0:
                    average = total // (len(players) - unranked)
                    median = statistics.median(median)
                    if median > average * 1.1: health = ':sparkling_heart:'
                    elif median > average * 0.95: health = ':heart:'
                    elif median > average * 0.75: health = ':mending_heart:'
                    elif median > average * 0.5: health = ':warning:'
                    elif median > average * 0.25: health = ':put_litter_in_its_place:'
                    else: health = ':skull_crossbones:'
                    description.append("\n{} GW**{}** | Player Sum **{}** | Avg. **{}**".format(health, gwid, self.bot.util.valToStr(total, 2), self.bot.util.valToStr(average, 2)))
                    if median > 0:
                        description.append(" | Med. **{}**".format(self.bot.util.valToStr(median, 2)))
                    if unranked > 0:
                        description.append(" | **{}** n/a".format(unranked))
            # create the fields
            i = 0
            for p in players:
                if i % 10 == 0:
                    fields.append({'name':'Page {}'.format(self.bot.emote.get('{}'.format(len(fields)+1))), 'value':''})
                    await asyncio.sleep(0)
                i += 1
                match p['member_position']:
                    case "1": r = "captain"
                    case "2": r = "foace"
                    case "3": r = "atkace"
                    case "4": r = "deface"
                    case _: r = "ensign"
                entry = '{} [{}](https://game.granbluefantasy.jp/#profile/{})'.format(self.bot.emote.get(r), self.escape(self.bot.util.shortenName(p['name'])), p['id'])
                if gwstate:  entry += " - {}".format(self.bot.util.valToStr(p['honor'], 2))
                else: entry += " - r**{}**".format(p['level'])
                entry += "\n"
                fields[-1]['value'] += entry
        return title, ''.join(description), fields, footer


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
    async def _crew_sub(self, inter : disnake.GuildCommandInteraction, crew_id : str, mode : int, view : Optional['BaseView'] = None) -> bool:
        # retrieve formatted crew data
        crew = await self.getCrewData(crew_id, 0)
        if 'error' in crew: # print the error if any
            if len(crew['error']) > 0:
                await inter.edit_original_message(embed=self.bot.embed(title="Crew Error", description=crew['error'], color=self.COLOR), view=view)
            return True
        title, description, fields, footer = await self.processCrewData(crew, mode)
        embed=self.bot.embed(title=title, description=description, fields=fields, inline=True, url="https://game.granbluefantasy.jp/#guild/detail/{}".format(crew['id']), footer=footer, timestamp=crew['timestamp'], color=self.COLOR)
        self_view = False
        if view is None and not crew.get('private', False):
            self_view = True
            embed.footer.text += " ▫️ Buttons expire in 100 seconds"
            search_results = []
            for i, p in enumerate(crew['player']):
                if (i % 10) == 0: search_results.append([])
                search_results[-1].append((p['id'], self.escape(p['name'])))
            embeds = [embed for i in range(len(search_results))]
            view = PageRanking(self.bot, owner_id=inter.author.id, embeds=embeds, search_results=search_results, color=self.COLOR, stype=False, timeout=100, enable_timeout_cleanup=True)
        
        await inter.edit_original_message(embed=embed, view=view)
        if self_view:
            view.message = await inter.original_message()
            return False
        return True

    @gw.sub_command(name="crew")
    async def _crew(self, inter: disnake.GuildCommandInteraction, crew_id : str = commands.Param(description="Crew ID"), mode : int = commands.Param(description="Mode (0=Auto, 1=Rank, 2=Honor)", ge=0, le=2, default=0)) -> None:
        """Get a crew profile"""
        await inter.response.defer()
        try:
            if await self._crew_sub(inter, crew_id, mode):
                await self.bot.util.clean(inter, 60)
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="A critical error occured, wait for a fix if the error persists", color=self.COLOR))
            self.bot.logger.pushError("[GW] In 'gw crew' command:", e)
            await self.bot.util.clean(inter, 60)


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
    async def requestCrew(self, cid : int, page : int) -> Optional[dict]: # get crew data
        if page == 0: return await self.bot.net.requestGBF("guild_other/guild_info/{}".format(cid), expect_JSON=True)
        else: return await self.bot.net.requestGBF("guild_other/member_list/{}/{}".format(page, cid), expect_JSON=True)

    """_sortMembers()
    Sort members by GW contributions
    
    Parameters
    ------
    members: List of members
    
    Returns
    ----------
    list: Sorted list
    """
    def _sortMembers(self, members : list) -> list:
        for i in range(0, len(members)-1):
            for j in range(i, len(members)):
                if int(members[i][2]) < int(members[j][2]):
                    members[i], members[j] = members[j], members[i]
        return members

    @gw.sub_command()
    async def lead(self, inter: disnake.GuildCommandInteraction, id_crew_1 : str = commands.Param(description="First crew ID"), id_crew_2 : str = commands.Param(description="Second crew ID")) -> None:
        """Search two crew current scores and compare them"""
        await inter.response.defer()
        day = self.bot.ranking.getCurrentGWDayID()
        if day is None or (day % 10) <= 1:
            await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Unavailable", color=self.COLOR))
            return
        if day >= 10: day = day % 10
        msg = ""
        lead_flag = True
        lead_speed_flag = True
        lead = None
        lead_speed = None
        crew_id_list = self.bot.data.config['granblue'].get('gbfgcrew', {}) | self.bot.data.config['granblue'].get('othercrew', {})
        
        desc = ""
        for sid in [id_crew_1, id_crew_2]:
            if sid.lower() in crew_id_list:
                cid = crew_id_list[sid.lower()]
            else:
                try: cid = int(sid)
                except:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Invalid ID `{}`".format(sid), color=self.COLOR))
                    return

            data = await self.bot.ranking.searchGWDB(str(cid), 12)
            if data is None:
                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Unavailable", color=self.COLOR))
                return
            else:
                if desc == "" and data[2][1] is not None:
                    timestamp = data[2][1].timestamp
                    if timestamp is not None:
                        desc = "Updated: **{}** ago\n".format(self.bot.util.delta2str(self.bot.util.JST()-timestamp, 0))
                if data[1] is None:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="No data available for `{}` the current GW".format(sid), color=self.COLOR))
                    return
                result = data[1]
                gwnum = ''
                if len(result) == 0:
                    msg += "Crew [{}](https://game.granbluefantasy.jp/#guild/detail/{}) not found\n".format(sid, cid)
                    lead = None
                    lead_flag = False
                else:
                    gwnum = result[0].gw
                    msg += "[{:}](https://game.granbluefantasy.jp/#guild/detail/{:}) ▫️ {:,}".format(result[0].name, cid, result[0].current_day)
                    if result[0].current_speed is not None and result[0].top_speed is not None:
                        msg += " ▫️ +{}/m. ▫️ Top {}/m.\n".format(self.bot.util.valToStr(result[0].current_speed), self.bot.util.valToStr(result[0].top_speed))
                        if timestamp is not None and day - 1 > 0 and day - 1 < 5:
                            if timestamp < self.bot.data.save['gw']['dates']['Day ' + str(day)] - timedelta(seconds=25200):
                                current_time_left = self.bot.data.save['gw']['dates']['Day ' + str(day)] - timedelta(seconds=25200) - timestamp
                                current_estimation = result[0].current_day + result[0].current_speed * current_time_left.seconds//60
                                top_estimation = result[0].current_day + result[0].top_speed * current_time_left.seconds//60
                                msg += "**Estimation** ▫️ Now {} ▫️ Top {}\n".format(self.bot.util.valToStr(current_estimation, 3), self.bot.util.valToStr(top_estimation, 3))
                        if lead_speed is None: lead_speed = result[0].current_speed
                        else: lead_speed -= result[0].current_speed
                    else:
                        msg += "\n"
                        lead_speed_flag = False
                    if lead_flag:
                        if lead is None: lead = result[0].current_day
                        else: lead -= result[0].current_day
        if lead_flag and lead != 0:
            if lead < 0:
                lead = -lead
                if lead_speed_flag: lead_speed = -lead_speed
            msg += "\n**Difference** ▫️ {:,}".format(lead)
            if lead_speed_flag and lead_speed != 0:
                msg += " ▫️ "
                if lead_speed > 0: msg += "+"
                msg += "{}/m.\n".format(self.bot.util.valToStr(lead_speed, 3))
        await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War {} ▫️ Day {}**".format(self.bot.emote.get('gw'), gwnum, day - 1), description=desc+msg, timestamp=self.bot.util.UTC(), color=self.COLOR))


    """updateGBFGData()
    Store the /gbfg/ crew data for later use by playerranking and danchoranking
    
    Parameters
    ------
    crews: List of /gbfg/ crew IDs
    force_update: If True, update all crews
    
    Returns
    ----------
    dict: Content of self.bot.data.save['gw']['gbfgdata']
    """
    async def updateGBFGData(self, crews : list, force_update : bool = False) -> dict:
        if not self.isGWRunning():
            return None
    
        if 'gbfgdata' not in self.bot.data.save['gw'] or force_update:
            self.bot.data.save['gw']['gbfgdata'] = {}
            self.bot.data.pending = True

        if force_update or len(crews) != len(self.bot.data.save['gw']['gbfgdata']):
            cdata = {}
            for c in crews:
                if str(c) in self.bot.data.save['gw']['gbfgdata']:
                    cdata[str(c)] = self.bot.data.save['gw']['gbfgdata'][str(c)]
                    if not force_update:
                        continue
                crew = await self.getCrewData(c, 0)
                if 'error' in crew or crew['private']:
                    crew = await self.getCrewData(c, 1)
                    if str(c) not in cdata:
                        cdata[str(c)] = [crew['name'], crew['leader'], int(crew['leader_id']), []]
                    continue
                cdata[str(c)] = [crew['name'], crew['leader'], int(crew['leader_id']), []]
                cdata[str(c)][-1] = [p['id'] for p in crew['player']]
            self.bot.data.save['gw']['gbfgdata'] = cdata
            self.bot.data.pending = True
        return self.bot.data.save['gw']['gbfgdata']

    @gw.sub_command_group()
    async def utility(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @utility.sub_command()
    async def box(self, inter: disnake.GuildCommandInteraction, box : int = commands.Param(description="Number of box to clear", ge=1, le=1000), box_done : int = commands.Param(description="Your current box progress, default 0 (Will be ignored if equal or higher than target)", ge=0, default=0), with_token : str = commands.Param(description="Your current token amount (support T, B, M and K)", default="0")) -> None:
        """Convert Guild War box values"""
        try:
            await inter.response.defer(ephemeral=True)
            t = 0
            try: with_token = max(0, self.bot.util.strToInt(with_token))
            except: raise Exception("Your current token amount `{}` isn't a valid number".format(with_token))
            if box_done >= box: raise Exception("Your current box count `{}` is higher or equal to your target `{}`".format(box_done, box))
            i = 0
            for b in range(box_done+1, box+1):
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    i += 1
                t += self.BOX_COST[i][1]
            t = max(0, t-with_token)
            msg = "**{:,}** tokens needed{:}{:}\n\n".format(t, ("" if box_done == 0 else " from box **{}**".format(box_done+1)), ("" if with_token == 0 else " with **{:,}** tokens".format(with_token)))
            for f, d in self.FIGHTS.items():
                n = math.ceil(t/d["token"])
                msg += "**{:,}** {:} (**{:,}** pots".format(n, f, n*d["AP"]//75)
                if d["meat_cost"] > 0: msg += ", **{:,}** meats".format(n*d["meat_cost"])
                msg += ")\n"
            await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War Token Calculator ▫️ Box {}".format(self.bot.emote.get('gw'), box), description=msg, color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description=str(e), color=self.COLOR))

    @utility.sub_command()
    async def token(self, inter: disnake.GuildCommandInteraction, token_target : str = commands.Param(description="Number of tokens you want (support T, B, M and K)"), final_rally : int = commands.Param(description="1 to include final rally (default), 0 to disable", default=1, le=1, ge=0)) -> None:
        """Convert Guild War token values"""
        try:
            await inter.response.defer(ephemeral=True)
            final_rally = (final_rally == 1)
            tok = self.bot.util.strToInt(token_target)
            if tok < 1 or tok > 9999999999: raise Exception()
            b = 0
            t = tok
            i = 0
            while True:
                if tok < self.BOX_COST[i][1]:
                    break
                tok -= self.BOX_COST[i][1]
                b += 1
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    i += 1
            msg = "**{:,}** box(s) and **{:,}** leftover tokens\n\n".format(b, tok)
            for f, d in self.FIGHTS.items():
                if final_rally: n = math.ceil(t / (d["token"]+d["rally_token"]))
                else: n = math.ceil(t / d["token"])
                msg += "**{:,}** {:} (**{:,}** pots".format(n, f, n*d["AP"]//75)
                if d["meat_cost"] > 0: msg += ", **{:,}** meats".format(n*d["meat_cost"])
                msg += ")\n"
            await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War Token Calculator ▫️ {} tokens".format(self.bot.emote.get('gw'), t), description=msg, footer=("Imply you solo all your hosts and clear the final rally" if final_rally else ""), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid token number", color=self.COLOR))

    @utility.sub_command()
    async def meat(self, inter: disnake.GuildCommandInteraction, value : str = commands.Param(description="Value to convert (support T, B, M and K)")) -> None:
        """Convert Guild War meat values"""
        try:
            await inter.response.defer(ephemeral=True)
            meat = self.bot.util.strToInt(value)
            if meat < 5 or meat > 400000: raise Exception()
            msg = ""
            for f, d in self.FIGHTS.items():
                if d["meat_cost"] == 0: continue
                n = meat // d["meat_cost"]
                msg += "**{:,}** {:} or **{:}** honors\n".format(n, f, self.bot.util.valToStr(n*d["honor"], 2))
            await inter.edit_original_message(embed=self.bot.embed(title="{} Meat Calculator ▫️ {} meats".format(self.bot.emote.get('gw'), meat), description=msg, color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid meat number", color=self.COLOR))

    @utility.sub_command()
    async def honor(self, inter: disnake.GuildCommandInteraction, value : str = commands.Param(description="Value to convert (support T, B, M and K)")) -> None:
        """Convert Guild War honor values"""
        try:
            await inter.response.defer(ephemeral=True)
            target = self.bot.util.strToInt(value)
            if target < 10000: raise Exception()
            msg = ""
            for f, d in self.FIGHTS.items():
                n = math.ceil(target / d["honor"])
                msg += "**{:,}** {:} (**{:,}** pots".format(n, f, n*d["AP"]//75)
                if d["meat_cost"] > 0: msg += ", **{:,}** meats".format(n * d["meat_cost"])
                msg += ")\n"
            await inter.edit_original_message(embed=self.bot.embed(title="{} Honor Calculator ▫️ {} honors".format(self.bot.emote.get('gw'), self.bot.util.valToStr(target)), description=msg, color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid honor number", color=self.COLOR))

    @utility.sub_command()
    async def honorplanning(self, inter: disnake.GuildCommandInteraction, target : str = commands.Param(description="Number of honors (support T, B, M and K)")) -> None:
        """Calculate how many NM100 to 250 you need for your targeted honor"""
        try:
            await inter.response.defer(ephemeral=True)
            target = self.bot.util.strToInt(target)
            if target < 1000000: raise Exception()
            
            honor = [0, 0, 0, 0, 0]
            ex = 0
            day_target = [target * 0.3, target * 0.4, target * 0.15, target * 0.15]
            day_nm = ["NM100", "NM150", "NM250", "NM250"]
            nm = [0, 0, 0, 0]
            meat = 0
            total_meat = 0

            for i in [3, 2, 1, 0]:
                daily = 0
                while daily < day_target[i]:
                    if meat < self.FIGHTS[day_nm[i]]["meat_cost"]:
                        meat += self.MEAT_PER_BATTLE_AVG
                        total_meat += self.MEAT_PER_BATTLE_AVG
                        ex += 1
                        daily += self.FIGHTS["EX+"]["honor"]
                        honor[0] += self.FIGHTS["EX+"]["honor"]
                    else:
                        meat -= self.FIGHTS[day_nm[i]]["meat_cost"]
                        nm[i] += 1
                        daily += self.FIGHTS[day_nm[i]]["honor"]
                        honor[i+1] += self.FIGHTS[day_nm[i]]["honor"]

            msg = ["Preliminaries & Interlude ▫️ **{:,}** meats (around **{:,}** EX+ and **{:}** honors)".format(math.ceil(total_meat), ex, self.bot.util.valToStr(honor[0], 2))]
            for i in range(0, len(nm)):
                msg.append("Day {:} ▫️ **{:,}** {} (**{:}** honors)".format(i+1, nm[i], day_nm[i], self.bot.util.valToStr(honor[i+1], 2)))
            await inter.edit_original_message(embed=self.bot.embed(title="{} Honor Planning ▫️ {} honors".format(self.bot.emote.get('gw'), self.bot.util.valToStr(target)), description="\n".join(msg), footer="Assuming {} meats / EX+ on average".format(self.MEAT_PER_BATTLE_AVG), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid honor number", color=self.COLOR))

    """speed_callback()
    CustomModal callback
    """
    async def speed_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        loading = int(modal.extra)
        error = False
        msg = ""
        for f, v in inter.text_values.items():
            try:
                if v == '': continue
                elif '.' in v: raise Exception()
                elems = v.split(':')
                if len(elems) > 2:
                    error = True
                    continue
                elif len(elems) == 2:
                    a = int(elems[0])
                    b = int(elems[1])
                    if a < 0 or b < 0: raise Exception()
                    time = a * 60 + b
                else:
                    time = int(elems[0])
                if time < 0: raise Exception()
                elif time == 0: continue
                mod = (3600 / (time+loading))
                if f not in self.FIGHTS: continue
                msg += "**{}** ▫️ {}{} ▫️ **{}** ▫️ **{}** Tokens ▫️ **{}** pots ▫️ **{}** Meats\n".format(f, self.bot.emote.get('clock'), v, self.bot.util.valToStr(mod*self.FIGHTS[f]["honor"], 2), self.bot.util.valToStr(mod*self.FIGHTS[f]["token"], 2), self.bot.util.valToStr(math.ceil(mod*self.FIGHTS[f]["AP"]/75), 2), self.bot.util.valToStr(mod*self.FIGHTS[f]["meat_cost"], 2))
            except:
                error = True
        if msg == '':
            await inter.edit_original_message(embed=self.bot.embed(title="{} Speed Comparator".format(self.bot.emote.get('gw')), description="No clear times set.\n" + ('' if not error else 'One or multiple values you sent were wrong. Either put a number of seconds **or** a time following the `MM:SS` format'), color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="{} Speed Comparator".format(self.bot.emote.get('gw')), description="**Per hour**" + (', with {} seconds of wasted time between fights\n'.format(loading) if loading > 0 else '\n') + msg, color=self.COLOR, footer='' if not error else 'Errors have been ignored'))

    @utility.sub_command()
    async def speed(self, inter: disnake.GuildCommandInteraction, loading : int = commands.Param(description="Wasted time between fights, in second", default=0)) -> None:
        """Compare multiple GW Nightmare fights based on your speed"""
        await self.bot.util.send_modal(inter, "gw_speed-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "GW Speed Comparator", self.speed_callback, [
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
    async def nm(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @nm.sub_command()
    async def hp90_95(self, inter: disnake.GuildCommandInteraction) -> None:
        """Give a fight equivalent of NM95 and NM90"""
        await inter.response.defer()
        boss = {
            'fire':('Ewiyar (Solo)', 180000000, "103471/3"),
            'water':('Wilnas (Solo)', 165000000, "103441/3"),
            'earth':('Wamdus (Solo)', 182000000, "103451/3"),
            'wind':('Galleon (Solo)', 196000000, "103461/3"),
            'light':('Gilbert (Proud)', 180000000, "103571/3"),
            'dark':('Lu Woh (Solo)', 192000000, "103481/3")
        }
        msg = ""
        for el in boss:
            if boss[el] is None:
                msg += "{} *No equivalent*\n".format(self.bot.emote.get(el))
            else:
                msg += "{:} [{:}](http://game.granbluefantasy.jp/#quest/supporter/{:}) ▫️ NM95: **{:.1f}%** ▫️ NM90: **{:.1f}%** HP remaining.\n".format(self.bot.emote.get(el), boss[el][0], boss[el][2], 100 * ((boss[el][1] - self.FIGHTS['NM95']['hp']) / boss[el][1]), 100 * ((boss[el][1] - self.FIGHTS['NM90']['hp']) / boss[el][1]))
        await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War ▫️ NM95 and NM90 Simulation".format(self.bot.emote.get('gw')), description=msg, color=self.COLOR))
        await self.bot.util.clean(inter, 90)

    @nm.sub_command()
    async def hp100(self, inter: disnake.GuildCommandInteraction) -> None:
        """Give a fight equivalent of NM100"""
        await inter.response.defer()
        boss = {
            'fire':('Ra', 565000000, "305351/1/0/44"),
            'water':('Atum', 570000000, "305321/1/0/41"),
            'earth':('Tefnut', 620000000, "305331/1/0/42"),
            'wind':('Bennu', 550000000, "305341/1/0/43"),
            'light':('Osiris', 600000000, "305371/1/0/46"),
            'dark':('Horus', 600000000, "305361/1/0/46")
        }
        msg = ""
        for el in boss:
            if boss[el] is None:
                msg += "{} *No equivalent*\n".format(self.bot.emote.get(el))
            else:
                msg += "{:} [{:}](http://game.granbluefantasy.jp/#quest/supporter/{:}) ▫️ NM100: **{:.1f}%** HP remaining.\n".format(self.bot.emote.get(el), boss[el][0], boss[el][2], 100 * ((boss[el][1] - self.FIGHTS['NM100']['hp']) / boss[el][1]))
        await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War ▫️ NM100 Simulation".format(self.bot.emote.get('gw')), description=msg, color=self.COLOR))
        await self.bot.util.clean(inter, 90)

    @gw.sub_command_group()
    async def find(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @find.sub_command(name="crew")
    async def crewfind(self, inter: disnake.GuildCommandInteraction, terms : str = commands.Param(description="What to search for"), search_type : int = commands.Param(description="0 = name (default). 1 = exact name. 2 = ID. 3 = ranking.", default=0, ge=0, le=3), mode_past : int = commands.Param(description="1 to search the previous GW. 0  for the current/last (default).", default=0, ge=0, le=1)) -> None:
        """Search a crew or player GW score in the bot data"""
        await inter.response.defer(ephemeral=True)
        await self.findranking(inter, True, terms, search_type, mode_past)

    @find.sub_command(name="player")
    async def playerfind(self, inter: disnake.GuildCommandInteraction, terms : str = commands.Param(description="What to search for"), search_type : int = commands.Param(description="0 = name (default). 1 = exact name. 2 = ID. 3 = ranking.", default=0, ge=0, le=3), mode_past : int = commands.Param(description="1 to search the previous GW. 0  for the current/last (default).", default=0, ge=0, le=1)) -> None:
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
    async def findranking(self, inter: disnake.GuildCommandInteraction, stype : bool, terms : str, search_type : int, mode_past : int) -> None:
        # set the search strings based on the search type
        if stype: txt = "crew"
        else: txt = "player"
        
        if terms == "": # no search terms so we print how to use it
            await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="**Usage**\n`/gw find {} terms:{}name` to search a {} by name\n`/gw find {} terms:{}name search_type:1` for an exact match\n`/gw find {} terms:{}id search_type:2` for an id search\n`/gw find {} terms:{}ranking search_type:3` for a ranking search".replace('{}', txt), color=self.COLOR))
        else:
            try:
                past = (mode_past == 1)
                
                match search_type:
                    case 0:
                        mode = 0
                        terms = self.htmlescape(terms)
                    case 1:
                        terms = self.htmlescape(terms)
                        mode = 1
                    case 2:
                        try:
                            terms = int(terms)
                            mode = 2
                        except:
                            await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="`{}` isn't a valid ID".format(terms), footer='ID mode is enabled', color=self.COLOR))
                            raise Exception("Returning")
                    case 3:
                        try:
                            terms = int(terms)
                            mode = 3
                        except:
                            await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="`{}` isn't a valid syntax".format(terms), color=self.COLOR))
                            raise Exception("Returning")

                # do our search
                data = await self.bot.ranking.searchGWDB(terms, (mode+10 if stype else mode))

                # select the right database (oldest one if %past is set or newest is unavailable, if not the newest)
                if data[1] is None or past: result = data[0]
                else: result = data[1]
                
                # check validity
                if result is None:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Database unavailable", color=self.COLOR))
                    raise Exception("Returning")
                    
                # max to display
                max_v = 9 if stype else 18
                if len(result) == 0: # check number of matches
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="`{}` not found".format(html.unescape(str(terms))), color=self.COLOR))
                    raise Exception("Returning")
                elif len(result) > (max_v * 20) and mode != 1:
                    if mode == 0:
                        await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Way too many results for `{}`\nTry to set `search_type` to **1**".format(html.unescape(str(terms))), color=self.COLOR))
                    else:
                        await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Way too many results for `{}`\nPlease try another search".format(html.unescape(str(terms))), color=self.COLOR))
                    raise Exception("Returning")
                
                # embed fields for the message
                embeds = []
                fields = []
                search_results = []
                for x in range(0, 1+len(result)//max_v):
                    search_list = []
                    for y in range(0, max_v):
                        i = x * max_v + y
                        if i >= len(result): break
                        if stype: # crew -----------------------------------------------------------------
                            fields.append({'name':"{}".format(html.unescape(result[i].name)), 'value':''})
                            search_list.append((result[i].id, html.unescape(result[i].name)))
                            if result[i].ranking is not None: fields[-1]['value'] += "▫️**#{}**\n".format(result[i].ranking)
                            else: fields[-1]['value'] += "\n"
                            if result[i].preliminaries is not None: fields[-1]['value'] += "**P.** ▫️{:,}\n".format(result[i].preliminaries)
                            if result[i].day1 is not None: fields[-1]['value'] += "{}▫️{:,}\n".format(self.bot.emote.get('1'), result[i].day1)
                            if result[i].day2 is not None: fields[-1]['value'] += "{}▫️{:,}\n".format(self.bot.emote.get('2'), result[i].day2)
                            if result[i].day3 is not None: fields[-1]['value'] += "{}▫️{:,}\n".format(self.bot.emote.get('3'), result[i].day3)
                            if result[i].day4 is not None: fields[-1]['value'] += "{}▫️{:,}\n".format(self.bot.emote.get('4'), result[i].day4)
                            if result[i].top_speed is not None: fields[-1]['value'] += "{}▫️Top {}/m.\n".format(self.bot.emote.get('clock'), self.bot.util.valToStr(result[i].top_speed))
                            if result[i].current_speed is not None and result[i].current_speed > 0: fields[-1]['value'] += "{}▫️Now {}/m.\n".format(self.bot.emote.get('clock'), self.bot.util.valToStr(result[i].current_speed))
                            if fields[-1]['value'] == "": fields[-1]['value'] = "No data"
                            fields[-1]['value'] = "[{}](https://game.granbluefantasy.jp/#guild/detail/{}){}".format(result[i].id, result[i].id, fields[-1]['value'])
                            gwnum = result[i].gw
                        else: # player -----------------------------------------------------------------
                            if y % (max_v // 3) == 0:
                                fields.append({'name':'Page {}'.format(self.bot.emote.get(str(((i // 5) % 3) + 1))), 'value':''})
                            search_list.append((result[i].id, self.escape(result[i].name)))
                            if result[i].ranking is None:
                                fields[-1]['value'] += "[{}](https://game.granbluefantasy.jp/#profile/{})\n".format(self.escape(result[i].name), result[i].id)
                            else:
                                fields[-1]['value'] += "[{}](https://game.granbluefantasy.jp/#profile/{}) ▫️ **#{}**\n".format(self.escape(result[i].name), result[i].id, result[i].ranking)
                            if result[i].current is not None: fields[-1]['value'] += "{:,}\n".format(result[i].current)
                            else: fields[-1]['value'] += "n/a\n"
                            gwnum = result[i].gw
                    if len(fields) > 0:
                        embeds.append(self.bot.embed(title="{} **Guild War {}**".format(self.bot.emote.get('gw'), gwnum), description="Page **{}/{}**".format(x+1, 1+len(result)//max_v), fields=fields, inline=True, color=self.COLOR, footer="Buttons expire in 3 minutes"))
                        fields = []
                        search_results.append(search_list)
                        search_list = []
                if len(search_list) > 0:
                    embeds.append(self.bot.embed(title="{} **Guild War {}**".format(self.bot.emote.get('gw'), gwnum), description="Page **{}/{}**".format(x+1, 1+len(result)//max_v), fields=fields, inline=True, color=self.COLOR, footer="Buttons expire in 3 minutes"))
                    search_results.append(search_list)
                    search_list = []
                view = PageRanking(self.bot, owner_id=inter.author.id, embeds=embeds, search_results=search_results, color=self.COLOR, stype=stype)
                await inter.edit_original_message(embed=embeds[0], view=view)
                view.message = await inter.original_message()
            except Exception as e:
                if str(e) != "Returning":
                    self.bot.logger.pushError("[GW] 'findranking' error:", e)
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="An error occured", color=self.COLOR))

    @gw.sub_command_group()
    async def stats(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    """refresh_gbfteamraid()
    Refresh the cookie needed for https://info.gbfteamraid.fun
    
    Returns
    ----------
    Boolean: True if success, False if error
    """
    async def refresh_gbfteamraid(self) -> bool:
        try:
            rheaders = [[None]]
            r = await self.bot.net.request("https://info.gbfteamraid.fun/login", rtype=self.bot.net.POST, add_user_agent=True, allow_redirects=False, collect_headers=rheaders, headers={'Host':'info.gbfteamraid.fun', 'Origin':'https://info.gbfteamraid.fun'}, ssl=False)
            if r is None: return False
            self.bot.data.save['gbfdata']['teamraid_cookie'] = rheaders[0]['Set-Cookie'].split(';', 1)[0]
            self.bot.data.pending = True
            return True
        except:
            return False

    """refresh_gbfteamraid()
    Core of /gw stats player and /gw stats crew
    
    Parameters
    ----------
    inter: A Discord Interaction, already deferred
    id_str: String, ID of the target
    is_crew: Boolean, True if the ID is for a crew, False otherwise
    """
    async def generat_gbfteamraide_stats(self, inter : disnake.Interaction, id_str : str, is_crew : bool) -> None:
        r = await self.bot.ranking.searchGWDB(id_str, 2 + (10 if is_crew else 0))
        search_type = ("Crew" if is_crew else "Player")
        path = ("guildrank" if is_crew else "userrank")
        method = ("getGuildrankChartById" if is_crew else "getUserrankChartById")
        param = ("guildid" if is_crew else "userid")
        complete_count = (5 if is_crew else 6)
        link = ("https://game.granbluefantasy.jp/#guild/detail/" if is_crew else "https://game.granbluefantasy.jp/#profile/")
        if r is None or (r[0] is None and r[1] is None) or (len(r[0]) == 0 and len(r[1]) == 0):
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description=search_type + " not found in the latest rankings", color=self.COLOR))
        else:
            if self.bot.data.save['gbfdata'].get('teamraid_cookie', None) is None and not await self.refresh_gbfteamraid():
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable, try again later or go to [this website](https://info.gbfteamraid.fun/web/about)", color=self.COLOR))
            else:
                msg = ""
                for gwi in range(2):
                    if r[gwi] is None or len(r[gwi]) == 0: continue
                    for err in range(2):
                        try:
                            gwid = r[2][gwi].gw
                            table = await self.bot.net.request("https://info.gbfteamraid.fun/web/{}?method={}&params=%7B%22teamraidid%22%3A%22teamraid{}%22%2C%22{}%22%3A%22{}%22%7D".format(path, method, str(gwid).zfill(3), param, id_str), rtype=self.bot.net.POST, add_user_agent=True, allow_redirects=False, headers={'Host':'info.gbfteamraid.fun', 'Origin':'https://info.gbfteamraid.fun', 'Referer':'https://info.gbfteamraid.fun/web/userrank?teamraidid=teamraid{}'.format(str(gwid).zfill(3)), 'Cookies':self.bot.data.save['gbfdata']['teamraid_cookie']}, ssl=False)
                            table = json.loads(table.decode('utf-8'))
                            data = {}
                            if 'result' in table:
                                for i in range(len(table['result'])-1, 1, -1):
                                    key = list(table['result'][i].keys())[0]
                                    data[key] = {'points': 0, 'speed':0}
                                    data[key]['points'] = int(table['result'][i][key][-1]['point']) - int(table['result'][i][key][0]['point'])
                                    prev = (int(table['result'][i][key][0]['point']), int(table['result'][i][key][0]['updatetime']))
                                    for p in table['result'][i][key]:
                                        try:
                                            speed = (int(p['point']) - prev[0]) / (int(p['updatetime']) - prev[1])
                                        except:
                                            continue
                                        if speed > data[key]['speed']:
                                            data[key]['speed'] = speed
                                        prev = (int(p['point']), int(p['updatetime']))
                            msg += "**GW{:}** of **[{:}]({:}{:})**\nTotal **{:,}** honors\n".format(gwid, r[gwi][0].name, link, r[gwi][0].id, r[gwi][0].current)
                            c = 1
                            tmp = ""
                            for k, v in data.items():
                                if v['points'] > 0:
                                    tmp += "{:} {:} - **{:,}** honors - {:} Best **{:}**/min\n".format(self.bot.emote.get(str(c)), k, v['points'], self.bot.emote.get('clock'), self.bot.util.valToStr(v['speed']*60, 2))
                                    c += 1
                            if tmp == "":
                                msg += "*Couldn't fetch detailed data*\n"
                            else:
                                if c <= complete_count: tmp += "*Data is uncomplete*\n"
                                msg += "**Breakdown**\n" + tmp
                            msg += "\n"
                            break
                        except Exception as e:
                            if err == 0:
                                await self.refresh_gbfteamraid()
                            else:
                                self.bot.logger.pushError("[GW] 'generat_gbfteamraide_stats' Error:", e)
                                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
                                await self.bot.util.clean(inter, 90)
                                return
                if msg == "":
                    await inter.edit_original_message(embed=self.bot.embed(title="Error", description="No data for this " + search_type.lower(), color=self.COLOR))
                else:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} {} Stats".format(self.bot.emote.get('gw'), search_type), description=msg, footer="source: https://info.gbfteamraid.fun/web/about", url="https://info.gbfteamraid.fun/web/about", color=self.COLOR))

    @stats.sub_command(name="player")
    async def playerstats(self, inter: disnake.GuildCommandInteraction, target : str = commands.Param(description="Either a valid GBF ID, discord ID or mention", default="")) -> None:
        """Retrieve a GBF profile GW stats from https://info.gbfteamraid.fun/web/about"""
        try:
            await inter.response.defer()
            pid = await self.bot.util.str2gbfid(inter, target)
            if isinstance(pid, str):
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description=pid, color=self.COLOR))
            else:
                await self.generat_gbfteamraide_stats(inter, str(pid), False)
        except Exception as e:
            self.bot.logger.pushError("[GW] In 'gw player stat' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
        await self.bot.util.clean(inter, 90)

    @stats.sub_command(name="crew")
    async def crewstats(self, inter: disnake.GuildCommandInteraction, target : str = commands.Param(description="Crew ID")) -> None:
        """Retrieve a GBF crew GW stats from https://info.gbfteamraid.fun/web/about"""
        try:
            await inter.response.defer()
            await self.generat_gbfteamraide_stats(inter, self.bot.util.gbfgstr2crewid(target), True)
        except Exception as e:
            self.bot.logger.pushError("[GW] In 'gw player stat' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
        await self.bot.util.clean(inter, 90)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(6, 60, commands.BucketType.guild)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def gbfg(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @gbfg.sub_command()
    async def recruit(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post all recruiting /gbfg/ crews"""
        await inter.response.defer()
        if not await self.bot.net.gbf_available():
            await inter.edit_original_message(embed=self.bot.embed(title="{} /gbfg/ recruiting crews".format(self.bot.emote.get('crew')), description="Unavailable", color=self.COLOR))
            await self.bot.util.clean(inter, 40)
        else:
            # list gbfg crews
            crews = list(set(self.bot.data.config['granblue'].get('gbfgcrew', {}).values()))
            crews.sort()
            # sort crews
            sortedcrew = []
            for c in crews:
                data = await self.getCrewData(c, 2)
                if 'error' not in data and data['count'] != 30:
                    if len(sortedcrew) == 0: sortedcrew.append(data)
                    else:
                        inserted = False
                        for i in range(len(sortedcrew)):
                            if data['average'] >= sortedcrew[i]['average']:
                                sortedcrew.insert(i, data)
                                inserted = True
                                break
                        if not inserted: sortedcrew.append(data)
            crews = None
            # output result
            fields = []
            if len(sortedcrew) > 20: size = 15
            elif len(sortedcrew) > 10: size = 10
            else: size = 5
            slots = 0
            search_results = []
            for i, v in enumerate(sortedcrew):
                if i % size == 0:
                    fields.append({'name':'Page {}'.format(self.bot.emote.get(str(len(fields)+1))), 'value':''})
                    search_results.append([])
                search_results[-1].append((v['id'], v['name']))
                fields[-1]['value'] += "Rank **{}** ▫️  **{}** ▫️ **{}** slot".format(v['average'], v['name'], 30-v['count'])
                if 30-v['count'] != 1: fields[-1]['value'] += "s"
                fields[-1]['value'] += "\n"
                slots += 30-v['count']
            embed = embed=self.bot.embed(title="{} /gbfg/ recruiting crews ▫️ {} slots".format(self.bot.emote.get('crew'), slots), fields=fields, inline=True, color=self.COLOR, timestamp=self.bot.util.UTC(), footer="Buttons expire in 100 seconds")
            embeds = [embed for i in range(len(search_results))]
            view = PageRanking(self.bot, owner_id=inter.author.id, embeds=embeds, search_results=search_results, color=self.COLOR, stype=True, timeout=100, enable_timeout_cleanup=True)
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
    async def _players(self, gbfgdata : dict) -> tuple:
        try:
            embeds = []
            final_results = []
            player_ranking = []
            dancho_ranking = []
            players = {}
            danchos = {}
            # build dancho and player id list
            for cid in gbfgdata:
                danchos[str(gbfgdata[cid][2])] = (gbfgdata[cid][0], gbfgdata[cid][1])
                if len(gbfgdata[cid][3]) == 0:
                    players[str(gbfgdata[cid][2])] = gbfgdata[cid][0]
                else:
                    for v in gbfgdata[cid][3]:
                        players[v] = gbfgdata[cid][0]
            await asyncio.sleep(0)
            # query
            data = await self.bot.ranking.searchGWDB("(" + ",".join(list(players.keys())) + ")", 4)
            desc = ""
            # store result
            if data is not None and data[1] is not None:
                if data[2][1] is not None:
                    timestamp = data[2][1].timestamp
                    if timestamp is not None:
                        desc = "Updated: **{}** ago".format(self.bot.util.delta2str(self.bot.util.JST()-timestamp, 0))
                if len(data[1]) > 0:
                    gwid = data[1][0].gw
                    for res in data[1]:
                        player_ranking.append([players[str(res.id)], res.name, res.current, res.id, res.ranking])
                        if str(res.id) in danchos:
                            danchos.pop(str(res.id)) # remove successful dancho
                            dancho_ranking.append([players[str(res.id)], res.name, res.current, res.id, res.ranking])
            await asyncio.sleep(0)
            for k, v in danchos.items(): # add n/a dancho
                dancho_ranking.append([v[0], v[1], None, k, None])
            dancho_list = [k[3] for k in dancho_ranking] # build dancho list (for emote)
            await asyncio.sleep(0)
            for captain in range(2):
                title_string = ("Captain" if captain == 1 else "Player")
                # build ranking
                if captain == 0:
                    ranking = player_ranking
                else:
                    ranking = dancho_ranking
                # sorting
                for i in range(len(ranking)):
                    for j in range(i+1, len(ranking)):
                        if ranking[j][2] is not None and (ranking[i][2] is None or ranking[i][2] < ranking[j][2]):
                            ranking[i], ranking[j] = ranking[j], ranking[i]
                await asyncio.sleep(0)
                if len(ranking) == 0:
                    continue
                else:
                    if gwid is None: gwid = ""
                    fields = []
                    search_results = []
                    for i, v in enumerate(ranking):
                        if i == 30: break
                        elif i % 15 == 0:
                            fields.append({'name':'Page {}'.format(self.bot.emote.get(str(len(fields)+1+captain*2))), 'value':''})
                            search_results.append([])
                            await asyncio.sleep(0)
                        if v[4] is not None:
                            if v[4] >= 100000:
                                rt = "#**{}K**".format(v[4]//1000)
                            else:
                                rt = "#**{}**".format(self.bot.util.valToStr(v[4]))
                            ht = " **{}**".format(self.bot.util.valToStr(v[2], 2))
                        else:
                            rt = "**n/a** "
                            ht = ""
                        ct = ' - ' if v[3] not in dancho_list else self.bot.emote.get('captain')
                        fields[-1]['value'] += "{}{}{} *{}*{}\n".format(rt, ct, v[1], v[0], ht)
                        search_results[-1].append((v[3], v[1]))
                    embed = self.bot.embed(title="{} /gbfg/ GW{} Top {} Ranking".format(self.bot.emote.get('gw'), gwid, title_string), description=desc, fields=fields, inline=True, color=self.COLOR, footer="Buttons expire in 100 seconds - {} on page {}, {}".format(("Players" if captain == 1 else "Captains"), (captain * 2 + 2) % 4 + 1, (captain * 2 + 2) % 4 + 2))
                    embeds += [embed for i in range(len(search_results))]
                    final_results += search_results
            return embeds, final_results
        except:
            return [], []

    @gbfg.sub_command()
    async def players(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the /gbfg/ Top 30 (players or captains) per contribution"""
        await inter.response.defer()
        crews = list(set(self.bot.data.config['granblue'].get('gbfgcrew', {}).values()))
        crews.sort()
        gbfgdata = await self.updateGBFGData(crews)
        if gbfgdata is None:
            await inter.edit_original_message(embed=self.bot.embed(title="{} /gbfg/ Ranking".format(self.bot.emote.get('gw')), description="This command is only available during Guild War", color=self.COLOR))
            await self.bot.util.clean(inter, 40)
            return
        embeds, final_results = await self._players(gbfgdata)
        if len(embeds) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="{} /gbfg/ Ranking".format(self.bot.emote.get('gw')), description="No players in the ranking", color=self.COLOR))
            await self.bot.util.clean(inter, 40)
        else:
            view = PageRanking(self.bot, owner_id=inter.author.id, embeds=embeds, search_results=final_results, color=self.COLOR, stype=False, timeout=100, enable_timeout_cleanup=True)
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
    async def _gbfgranking(self) -> tuple:
        try:
            # build crew list
            crews = list(set(self.bot.data.config['granblue'].get('gbfgcrew', {}).values()))
            crews.sort()
            # query
            cdata = await self.bot.ranking.searchGWDB("("+",".join(crews)+")", 14)
            if cdata is None or cdata[1] is None:
                return [], []
            await asyncio.sleep(0)
            gwid = cdata[1][0].gw
            day = 0
            timestamp = None
            if cdata[2][1] is not None:
                timestamp = cdata[2][1].timestamp
            embeds = []
            final_results = []
            for sort_mode in range(3):
                match sort_mode:
                    case 1: # top speed
                        footer = "Honor page 1,2, Current Speed page 5, 6"
                    case 2: # current speed
                        footer = "Honor page 1,2, Top Speed page 3, 4"
                    case _: # default
                        footer = "Top Speed page 3,4, Current Speed page 5, 6"
                tosort = {}
                for data in cdata[1]:
                    day = max(day, data.day)
                for data in cdata[1]:
                    match sort_mode:
                        case 1: # top speed
                            if data.top_speed is None or data.day < day: continue
                            tosort[data.id] = [data.id, data.name, data.top_speed, data.ranking, data.day] # id, name, honor, rank, day
                        case 2: # current speed
                            if data.current_speed is None or data.day < day: continue
                            tosort[data.id] = [data.id, data.name, data.current_speed, data.ranking, data.day] # id, name, honor, rank, day
                        case _: # default
                            if data.current is None or data.day < day: continue
                            tosort[data.id] = [data.id, data.name, data.current, data.ranking, data.day] # id, name, honor, rank, day
                    # sorting
                    await asyncio.sleep(0)
                    sorted = []
                    for c in tosort:
                        inserted = False
                        for i in range(0, len(sorted)):
                            if tosort[c][2] > sorted[i][2]:
                                inserted = True
                                sorted.insert(i, tosort[c])
                                break
                        if not inserted: sorted.append(tosort[c])
                    await asyncio.sleep(0)
                    if gwid is None: gwid = ""
                    fields = []
                    search_results = []
                    for i, v in enumerate(sorted):
                        if i % 15 == 0:
                            fields.append({'name':'Page {}'.format(self.bot.emote.get(str(len(fields)+1+len(embeds)))), 'value':''})
                            search_results.append([])
                            await asyncio.sleep(0)
                        fields[-1]['value'] += "#**{}** - {} - **{}".format(self.bot.util.valToStr(v[3]), v[1], self.bot.util.valToStr(v[2], 2))
                        search_results[-1].append((v[0], v[1]))
                        if sort_mode > 0: fields[-1]['value'] += "/min**\n"
                        else: fields[-1]['value'] += "**\n"
                notranked = len(crews) - len(cdata[1])
                if notranked > 0:
                    fields[-1]['value'] += "**{}** unranked crew{}".format(notranked, 's' if notranked > 1 else '')
                # append embed and results
                title = ["", "Top Speed ", "Current Speed "][sort_mode]
                desc = ""
                if timestamp is not None:
                    desc = "Updated: **{}** ago".format(self.bot.util.delta2str(self.bot.util.JST()-timestamp, 0))
                embed = self.bot.embed(title="{} /gbfg/ GW{} {}Ranking".format(self.bot.emote.get('gw'), gwid, title), description=desc, fields=fields, inline=True, color=self.COLOR, footer="Buttons expire in 100 seconds - " + footer)
                for i in range(len(search_results)):
                    final_results.append(search_results[i])
                    embeds.append(embed)
                await asyncio.sleep(0)
            return embeds, final_results
        except:
            return [], []

    @gbfg.sub_command(name="ranking")
    async def gbfgranking(self, inter: disnake.GuildCommandInteraction) -> None:
        """Sort and post all /gbfg/ crew per contribution or speed"""
        await inter.response.defer()
        embeds, final_results = await self._gbfgranking()
        if len(embeds) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="{} /gbfg/ Ranking".format(self.bot.emote.get('gw')), description="Unavailable", color=self.COLOR))
            await self.bot.util.clean(inter, 40)
        else:
            view = PageRanking(self.bot, owner_id=inter.author.id, embeds=embeds, search_results=final_results, color=self.COLOR, stype=True, timeout=100, enable_timeout_cleanup=True)
            await inter.edit_original_message(embed=embeds[0], view=view)
            view.message = await inter.original_message()