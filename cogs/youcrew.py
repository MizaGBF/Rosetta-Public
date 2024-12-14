import disnake
from disnake.ext import commands
import asyncio
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from cogs import CREW_SERVER_ID
from datetime import datetime, timedelta
from PIL import Image, ImageFont, ImageDraw
import sqlite3
import math
from io import BytesIO

# ----------------------------------------------------------------------------------------------------------------
# (You) Crew Cog
# ----------------------------------------------------------------------------------------------------------------
# Commands for my crew server
# Remove this file if you don't need it
# ----------------------------------------------------------------------------------------------------------------

class YouCrew(commands.Cog):
    """Owner only."""
    if CREW_SERVER_ID is None: guild_ids = [] # CREW_SERVER_ID is defined in cogs/init
    else: guild_ids = [CREW_SERVER_ID]
    COLOR = 0xffce47

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def startTasks(self) -> None:
        self.bot.runTask('you:buff', self.checkGWBuff)

    """checkGWBuff()
    Bot Task managing the buff alert of the (You) server
    """
    async def checkGWBuff(self) -> None:
        # retrieve cog
        gwcog = self.bot.get_cog('GuildWar')
        if gwcog is None:
            # add warning in log, just in case
            self.bot.logger.push("[TASK] 'you:buff' Task Cancelled, the 'GuildWar' Cog is missing.", send_to_discord=False, level=self.logger.WARNING)
            return
        # check if gw is on going
        self.gwcog.getGWState()
        if self.bot.data.save['gw']['state'] is False or len(self.bot.data.save['gw']['buffs']) == 0:
            return # silently cancel if not
        try:
            # check if guild set in config.json
            guild = self.bot.get_guild(self.bot.data.config['ids'].get('you_server', 0))
            if guild is None:
                self.bot.logger.push("[TASK] 'you:buff' Task Cancelled, no guild 'you_server' found")
                return
            # check if channel set in config.json
            channel = self.bot.get_channel(self.bot.data.config['ids'].get('you_announcement', 0))
            if guild is None:
                self.bot.logger.push("[TASK] 'you:buff' Task Cancelled, no channel 'you_announcement' found")
                return
            # init skip flag if missing
            if 'skip' not in self.bot.data.save['gw']:
                self.bot.data.save['gw']['skip'] = False
                self.bot.data.pending = True
            # retrieve roles
            gl_role = guild.get_role(self.bot.data.config['ids'].get('gl', 0))
            fo_role = guild.get_role(self.bot.data.config['ids'].get('fo', 0))
            buff_role = [[guild.get_role(self.bot.data.config['ids'].get('atkace', 0)), 'atkace'], [guild.get_role(self.bot.data.config['ids'].get('deface', 0)), 'deface']]
            # task loop (as long as gw is on and buffs are remaining in the queue)
            msgs = []
            while self.bot.data.save['gw']['state'] and (len(self.bot.data.save['gw']['buffs']) > 0 or len(msgs) != 0):
                # check if we passed next buff date
                current_time = self.bot.util.JST() + timedelta(seconds=32)
                if len(self.bot.data.save['gw']['buffs']) > 0 and current_time >= self.bot.data.save['gw']['buffs'][0][0]:
                    msgs = []
                    # if recent (in the last 200s)
                    if (current_time - self.bot.data.save['gw']['buffs'][0][0]) < timedelta(seconds=200):
                        if self.bot.data.save['gw']['buffs'][0][1]: # flag 1: ATK and DEF aces
                            for r in buff_role:
                                msgs.append("{} {}\n".format(self.bot.emote.get(r[1]), r[0].mention))
                        if self.bot.data.save['gw']['buffs'][0][2]: # flag 2: First Officers
                            msgs.append("{} {}\n".format(self.bot.emote.get('foace'), fo_role.mention))
                        if self.bot.data.save['gw']['buffs'][0][3]: # flag 3: Merely an advance warning
                            msgs.append('*Buffs in* **5 minutes**')
                        else:
                            msgs.append('Buffs now!')
                        # flag 4: Prelims "Use Twice" mention
                        if self.bot.data.save['gw']['buffs'][0][4]:
                            msgs.append('\n**(Use everything this time! They are reset later.)**')
                        # add Link
                        msgs.append("\nhttps://game.granbluefantasy.jp/#event/teamraid{}/guild_ability".format(str(self.bot.data.save['gw']['id']).zfill(3)))
                        # If skip flag is on, reset and ignore
                        if self.bot.data.save['gw']['skip']:
                            msgs = []
                        # If flag 3 was off: Reset skip flag
                        if not self.bot.data.save['gw']['buffs'][0][3]:
                            self.bot.data.save['gw']['skip'] = False
                    self.bot.data.save['gw']['buffs'].pop(0)
                    self.bot.data.pending = True
                else:
                    # if a message is pending
                    if len(msgs) > 0: # send and reset
                        await channel.send("{} {}\n{}".format(self.bot.emote.get('captain'), gl_role.mention, ''.join(msgs)))
                        msgs = []
                    if len(self.bot.data.save['gw']['buffs']) > 0: # if a buff is remaining, sleep until its time
                        d = self.bot.data.save['gw']['buffs'][0][0] - current_time
                        if d.seconds > 1:
                            await asyncio.sleep(d.seconds-1)
            # send message if any is pending
            if len(msgs) > 0:
                await channel.send("{} {}\n{}".format(self.bot.emote.get('captain'), gl_role.mention, ''.join(msgs)))
        except asyncio.CancelledError:
            self.bot.logger.push("[TASK] 'you:buff' Task Cancelled")
        except Exception as e:
            self.bot.logger.pushError("[TASK] 'you:buff' Task Error:", e)
        # quit
        await self.bot.send('debug', embed=self.bot.embed(color=self.COLOR, title="User task ended", description="you:buff", timestamp=self.bot.util.UTC()))

    """setBuffTask()
    Start or stop the checkGWBuff() coroutine as a task.
    
    Parameters
    ----------
    state: Boolean, True to (re)start the task, False to stop it
    """
    def setBuffTask(self, state : bool) -> None:
        if state: # (re)start buff task
            self.bot.runTask('you:buff', self.checkGWBuff)
        else: # stop buff task
            self.bot.cancelTask('you:buff')

    """getNextBuff()
    Return the time left until the next buffs for the (You) server
    
    Parameters
    ----------
    inter: Command interaction (to check the server)
    
    Returns
    --------
    str: Time left in a string, empty if error
    """
    def getNextBuff(self, inter: disnake.GuildCommandInteraction) -> str: 
        if self.bot.data.save['gw']['state'] is True and inter.guild.id == self.bot.data.config['ids'].get('you_server', 0): # check if gw is on going and the server is the right one
            current_time = self.bot.util.JST() # get current time
            if current_time < self.bot.data.save['gw']['dates']["Preliminaries"]: # gw hasn't started
                return "" # return nothing
            for b in self.bot.data.save['gw']['buffs']: # iterate until closest buff to current time
                if not b[3] and current_time < b[0]:
                    # build message
                    msgs = ["{} Next buffs in **{}** (".format(self.bot.emote.get('question'), self.bot.util.delta2str(b[0] - current_time, 2))]
                    if b[1]:
                        msgs.append("Attack {}, Defense {}".format(self.bot.emote.get('atkace'), self.bot.emote.get('deface')))
                        if b[2]:
                            msgs.append(", FO {}".format(self.bot.emote.get('foace')))
                    elif b[2]:
                        msgs.append("FO {}".format(self.bot.emote.get('foace')))
                    msgs.append(")")
                    # and return it
                    return "".join(msgs)
        return ""

    """searchScoreForTracker()
    Search the targeted crews for the YouTracker in the database being built
    
    Parameters
    ----------
    day: current day ID
    crews: List of crew IDs
    
    Returns
    --------
    list: Crew informations
    """
    async def searchScoreForTracker(self, day : int, crews : list) -> list:
        infos = []
        conn = sqlite3.connect('temp.sql') # open temp.sql
        c = conn.cursor()
        c.execute("PRAGMA synchronous = normal")
        c.execute("PRAGMA locking_mode = exclusive")
        c.execute("PRAGMA journal_mode = OFF")
        await asyncio.sleep(0)
        d = [3, 4, 5, 6, 7] # prelims to day 4 slots
        for sid in crews: # retrieve both crews data
            c.execute("SELECT * FROM crews WHERE id = {}".format(sid)) # get the score
            data = c.fetchall()
            if data is None or len(data) == 0: raise Exception("Failed to retrieve data")
            infos.append([data[0][2], data[0][d[day]]-data[0][d[day]-1], data[0][8]]) # name, score of the day, top speed
            await asyncio.sleep(0)  
        c.close()
        conn.close()
        # return their details
        return infos

    """drawChart()
    Draw the YouTracker chart (GW Match tracker for my crew)
    
    Parameters
    ----------
    plot: list of points, format: [datetime, float, float]
    
    Raises
    ------
    Exception: If an error occurs
    
    Returns
    ----------
    str: filename of the image, None if error
    """
    async def drawChart(self, plot : list) -> Optional[str]:
        if len(plot) == 0: return None # no plot data
        # make a white RGB image, 800x600px
        img = Image.new("RGB", (800, 600), (255,255,255))
        d = ImageDraw.Draw(img)
        # load our font for texts
        font = ImageFont.truetype("assets/font.ttf", 14)
        
        # y grid lines
        for i in range(0, 4):
            d.line([(50, 50+125*i), (750, 50+125*i)], fill=(200, 200, 200), width=1)
        # x grid lines
        for i in range(0, 10):
            d.line([(120+70*i, 50), (120+70*i, 550)], fill=(200, 200, 200), width=1)
        await asyncio.sleep(0)
        # legend
        d.text((10, 10),"Speed (M/min)",font=font,fill=(0,0,0))
        d.line([(150, 15), (170, 15)], fill=(0, 0, 255), width=2)
        d.text((180, 10),"You",font=font,fill=(0,0,0))
        d.line([(220, 15), (240, 15)], fill=(255, 0, 0), width=2)
        d.text((250, 10),"Opponent",font=font,fill=(0,0,0))
        d.text((720, 580),"Time (JST)",font=font,fill=(0,0,0))
        await asyncio.sleep(0)
        
        # y axis notes
        miny = 999
        maxy = 0
        for p in plot:
            miny = math.floor(min(miny, p[1], p[2]))
            maxy = math.ceil(max(maxy, p[1], p[2]))
        deltay= maxy - miny
        if deltay <= 0: return None
        tvar = maxy
        for i in range(0, 5):
            d.text((10, 40+125*i),"{:.2f}".format(float(tvar)).replace('.00', '').replace('.10', '.1').replace('.20', '.2').replace('.30', '.3').replace('.40', '.4').replace('.50', '.5').replace('.60', '.6').replace('.70', '.7').replace('.80', '.8').replace('.90', '.9').replace('.0', '').rjust(6),font=font,fill=(0,0,0))
            tvar -= deltay / 4
        await asyncio.sleep(0)
        # x axis notes
        minx = plot[0][0]
        maxx = plot[-1][0]
        deltax = maxx - minx
        deltax = (deltax.seconds + deltax.days * 86400)
        if deltax <= 0: return None
        tvar = minx
        for i in range(0, 11):
            d.text((35+70*i, 560),"{:02d}:{:02d}".format(tvar.hour, tvar.minute),font=font,fill=(0,0,0))
            tvar += timedelta(seconds=deltax/10)
        await asyncio.sleep(0)

        # scores curves
        lines = [[], []]
        for p in plot:
            x = p[0] - minx
            x = (x.seconds + x.days * 86400)
            x = 50 + 700 * (x / deltax)
            y = maxy - p[1]
            y = 50 + 500 * (y / deltay)
            lines[0].append((x, y))
            y = maxy - p[2]
            y = 50 + 500 * (y / deltay)
            lines[1].append((x, y))
        await asyncio.sleep(0)

        # plot lines
        d.line([(50, 50), (50, 550), (750, 550)], fill=(0, 0, 0), width=1)
        d.line(lines[0], fill=(0, 0, 255), width=2, joint="curve")
        d.line(lines[1], fill=(255, 0, 0), width=2, joint="curve")
        await asyncio.sleep(0)

        # save the image to memory as PNG and return its binary value
        with BytesIO() as output:
            img.save(output, format="PNG")
            img.close()
            return output.getvalue()

    """updateTracker()
    Update the YouTracker data (GW Match tracker for my crew)
    Ideally called between the crew ranking and player ranking retrieval
    Check the ranking component to look for where it's called
    
    Parameters
    ----------
    t: time of this ranking interval
    day: Integer, current day number
    """
    async def updateTracker(self, t : datetime, day : int) -> None:
        you_id = self.bot.data.config['granblue']['gbfgcrew'].get('you', None) # our id
        if you_id is None: return
        
        # check tracker state
        if self.bot.data.save['matchtracker'] is None: return # not initialized
        if self.bot.data.save['matchtracker']['day'] != day: # new day, reset data
            self.bot.data.save['matchtracker'] = {
                'day':day,
                'init':False,
                'id':self.bot.data.save['matchtracker']['id'],
                'plot':[]
            }
            self.bot.data.pending = True
        
        # Retrieve scores
        infos = await self.searchScoreForTracker(day, [you_id, self.bot.data.save['matchtracker']['id']])
        # Make tracker copy, to be safe
        newtracker = self.bot.data.save['matchtracker'].copy()
        if newtracker['init']: # it's initialized
            d = t - newtracker['last'] # time delta
            minute = d.seconds//60 # elapsed minutes in that delta
            # rounding minute to multiple of 20min
            if minute % 20 > 15:
                minute += 20 - (minute % 20)
            elif minute % 20 < 5:
                minute -= (minute % 20)
            # calculating speeds
            if minute != 0:
                speed = [(infos[0][1] - newtracker['scores'][0]) / minute, (infos[1][1] - newtracker['scores'][1]) / minute]
                if speed[0] > newtracker['top_speed'][0]: newtracker['top_speed'][0] = speed[0]
                if speed[1] > newtracker['top_speed'][1]: newtracker['top_speed'][1] = speed[1]
                newtracker['speed'] = speed
            else:
                newtracker['speed'] = None
        else: # not initialized
            newtracker['init'] = True
            newtracker['speed'] = None
            newtracker['top_speed'] = [0, 0]
        # set crew datas
        newtracker['names'] = [infos[0][0], infos[1][0]]
        newtracker['scores'] = [infos[0][1], infos[1][1]]
        newtracker['max_speed'] = [infos[0][2], infos[1][2]]
        newtracker['last'] = t # timestamp
        newtracker['gwid'] = self.bot.data.save['gw']['id'] # gw id
        if newtracker['speed'] is not None: # save chart data
            newtracker['plot'].append([t, newtracker['speed'][0] / 1000000, newtracker['speed'][1] / 1000000])
        if len(newtracker['plot']) > 1: # generate a chart
            try:
                imgdata = await self.drawChart(newtracker['plot'])
                with BytesIO(imgdata) as f:
                    if f.getbuffer().nbytes > 0: # send file to discord if valid and retrieve its url
                        with self.bot.file.discord(f, filename="chart.png") as df:
                            message = await self.bot.send('image', file=df)
                            newtracker['chart'] = message.attachments[0].url
            except Exception as e:
                self.bot.logger.pushError("[RANKING] 'updatetracker (Upload)' error:", e)
        # save the new tracker data
        self.bot.data.save['matchtracker'] = newtracker
        self.bot.data.pending = True

    @commands.slash_command(guild_ids=guild_ids)
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    async def you(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @you.sub_command()
    async def buff(self, inter: disnake.GuildCommandInteraction) -> None:
        """Check when is the next GW buff ((You) Server Only)"""
        try:
            await inter.response.defer()
            d = self.getNextBuff(inter) # retrieve next buff string
            if d != "":
                await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War (You) Buff status".format(self.bot.emote.get('gw')), description=d, color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="{} Guild War (You) Buff status".format(self.bot.emote.get('gw')), description="Only available when Guild War is on going", color=self.COLOR))
                await self.bot.util.clean(inter, 40)
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
            self.bot.logger.pushError("[YOU] In 'you buff' command:", e)
            await self.bot.util.clean(inter, 40)

    @you.sub_command()
    async def lead(self, inter: disnake.GuildCommandInteraction, opponent : str = commands.Param(description="Opponent ID to set it (Mod Only)", default="")) -> None:
        """Show the current match of (You) ((You) Server Only)"""
        await inter.response.defer()
        if opponent != "" and self.bot.isMod(inter): # opponent set mode (MUST BE A MODERATOR)
            # lookup the opponent id
            crew_id_list = self.bot.data.config['granblue'].get('gbfgcrew', {}) | self.bot.data.config['granblue'].get('othercrew', {})
            if opponent.lower() in crew_id_list:
                oid = crew_id_list[opponent.lower()]
            else:
                try: oid = int(opponent)
                except:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Invalid ID `{}`".format(opponent), color=self.COLOR))
                    return
            # set the tracker if not set with this id
            if self.bot.data.save['matchtracker'] is None or self.bot.data.save['matchtracker']['id'] != oid:
                self.bot.data.save['matchtracker'] = {
                    'day':None,
                    'init':False,
                    'id':oid,
                    'plot':[]
                }
                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Opponent set to id `{}`, please wait the next ranking update".format(oid), color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Opponent already set to id `{}`".format(oid), color=self.COLOR))
        else: # normal mode (show stats)
            # check if data is available
            if self.bot.data.save['matchtracker'] is None or not self.bot.data.save['matchtracker']['init']:
                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Unavailable, either wait the next ranking update or add the opponent id after the command to initialize it", color=self.COLOR))
            else: # it is
                ct = self.bot.util.JST() # get current time
                you_id = self.bot.data.config['granblue']['gbfgcrew'].get('you', None) # our id
                d = ct - self.bot.data.save['matchtracker']['last'] # time elapsed since last update
                msgs = ["Updated: **{}** ago".format(self.bot.util.delta2str(d, 0))]
                if d.seconds >= 1200 and d.seconds <= 1800: msgs.append(" ▫ *updating*") # add updating message if a next update is imminent
                msgs.append("\n")
                if self.bot.data.save['matchtracker']['last'].hour < 7: # if match is on going
                    end_time = self.bot.data.save['matchtracker']['last'].replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    end_time = self.bot.data.save['matchtracker']['last'].replace(day=self.bot.data.save['matchtracker']['last'].day+1, hour=0, minute=0, second=0, microsecond=0)
                remaining = end_time - self.bot.data.save['matchtracker']['last'] # calculate remaining time
                lead_speed = None
                for i in range(2): # our crew, opponent crew
                    # add crew name, id and score
                    msgs.append("[{:}](https://game.granbluefantasy.jp/#guild/detail/{:}) ▫️ **{:,}**".format(self.bot.data.save['matchtracker']['names'][i], (you_id if i == 0 else self.bot.data.save['matchtracker']['id']), self.bot.data.save['matchtracker']['scores'][i]))
                    # check if it got speed data
                    if self.bot.data.save['matchtracker']['speed'] is None:
                        msgs.append("\n\n")
                        continue
                    # it does
                    if i == 0:
                        lead_speed = self.bot.data.save['matchtracker']['speed'][0] # first crew, not the speed
                    elif lead_speed is not None: # second crew, substract the opponent speed to get the lead speed
                        lead_speed -= self.bot.data.save['matchtracker']['speed'][1]
                    else: # anything else / error, no lead speed
                        lead_speed = None
                    # add the speed data of this crew
                    msgs.append("\n**Speed** ▫️ Now {}/m".format(self.bot.util.valToStr(self.bot.data.save['matchtracker']['speed'][i], 2)))
                    if self.bot.data.save['matchtracker']['speed'][i] >= self.bot.data.save['matchtracker']['top_speed'][i]:
                        msgs.append(" ▫️ **Top {}/m** {}".format(self.bot.util.valToStr(self.bot.data.save['matchtracker']['top_speed'][i], 2), ":white_check_mark:" if i == 0 else ":warning:"))
                    else:
                        msgs.append(" ▫️ Top {}/m".format(self.bot.util.valToStr(self.bot.data.save['matchtracker']['top_speed'][i], 2)))
                    # add the max speed of this crew
                    max_speed = max(self.bot.data.save['matchtracker']['max_speed'][i], self.bot.data.save['matchtracker']['top_speed'][i])
                    if self.bot.data.save['matchtracker']['speed'][i] >= max_speed:
                        msgs.append(" ▫️ **Max {}/m** {}".format(self.bot.util.valToStr(max_speed, 2), ":white_check_mark:" if i == 0 else ":warning:"))
                    else:
                        msgs.append(" ▫️ Max {}/m".format(self.bot.util.valToStr(max_speed, 2)))
                    # if the match hasn't ended, add estimations
                    if end_time > self.bot.data.save['matchtracker']['last']:
                        # estimations do current score and apply the current, top and max speeds to it
                        current_estimation = self.bot.data.save['matchtracker']['scores'][i] + self.bot.data.save['matchtracker']['speed'][i] * remaining.seconds//60
                        max_estimation = self.bot.data.save['matchtracker']['scores'][i] + max_speed * remaining.seconds//60
                        top_estimation = self.bot.data.save['matchtracker']['scores'][i] + self.bot.data.save['matchtracker']['top_speed'][i] * remaining.seconds//60
                        msgs.append("\n**Estimation** ▫ Now {} ▫️ Top {} ▫️ Max {}".format(self.bot.util.valToStr(current_estimation, 3), self.bot.util.valToStr(top_estimation, 3), self.bot.util.valToStr(max_estimation, 3)))
                    else:
                        lead_speed = None # disable lead check if the match ended
                    msgs.append("\n\n")
                # calculate lead
                lead = self.bot.data.save['matchtracker']['scores'][0] - self.bot.data.save['matchtracker']['scores'][1]
                if lead != 0: # check if non null
                    msgs.append("**Difference** ▫️ {:,}".format(abs(lead))) # remove sign
                    # add lead speed if it exists
                    if lead_speed is not None and lead_speed != 0:
                        try:
                            if lead < 0: lead_speed *= -1 # lead negative, then reverse speed
                            msgs.append(" ▫️ {}/m".format(self.bot.util.valToStr(lead_speed, 3)))
                            lead_will_switch = False # this flag will be set to true if the winner is expected to change before the match end
                            if lead_speed < 0: # negative lead speed
                                minute = abs(lead) / abs(lead_speed) # check remaining minutes to exshaut current lead
                                d = self.bot.data.save['matchtracker']['last'] + timedelta(seconds=minute*60)
                                e = ct.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                                if e > d: # the lead WILL switch before the end
                                    if lead > 0: msgs.append("\n:warning: ")
                                    else: msgs.append("\n:white_check_mark: ")
                                    if d >= ct:
                                        msgs.append("The Lead switches in **{}** at current speeds".format(self.bot.util.delta2str(d - ct)))
                                    else:
                                        msgs.append("The Lead might have switched")
                                    lead_will_switch = True
                            # if the lead won't switch
                            if not lead_will_switch and lead > 0:
                                if self.bot.data.save['matchtracker']['scores'][0] > top_estimation: # winning case
                                    if self.bot.data.save['matchtracker']['max_speed'][1] > self.bot.data.save['matchtracker']['top_speed'][1]:
                                        msgs.append("\n:confetti_ball: Opponent can't catch up but **can still go faster**, be careful")
                                    else:
                                        msgs.append("\n:confetti_ball: Opponent can't catch up without surpassing their **max speed**")
                                elif self.bot.data.save['matchtracker']['scores'][0] > current_estimation: # ahead case
                                    msgs.append("\n:white_check_mark: Opponent can't catch up without increasing their **current speed**")
                                else: # ahead but probably not for long case
                                    msgs.append("\n:ok: Opponent can't catch up at **current speeds**, keep going!")
                        except:
                            pass
                # send message
                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War {} ▫️ Day {}**".format(self.bot.emote.get('gw'), self.bot.data.save['matchtracker']['gwid'], self.bot.data.save['matchtracker']['day']), description="".join(msgs), timestamp=self.bot.util.UTC(), thumbnail=self.bot.data.save['matchtracker'].get('chart', None), color=self.COLOR))
                await self.bot.util.clean(inter, 90)

    @you.sub_command()
    async def honor(self, inter: disnake.GuildCommandInteraction) -> None:
        """Retrieve (You) members's honor ((You) Server Only)"""
        await inter.response.defer(ephemeral=True)
        crews = list(set(self.bot.data.config['granblue'].get('gbfgcrew', {}).values()))
        crews.sort()
        cid = self.bot.data.config['granblue'].get('gbfgcrew', {}).get("(you)", None) # retrieve (You) id
        if cid is None: # id not found
            await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="Crew not found", color=self.COLOR))
        else:
            data = await self.bot.get_cog('GuildWar').updateGBFGData(crews) # get gbfg data
            if data is None or cid not in data or len(data[cid][-1]) == 0:
                await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="No player data found", color=self.COLOR))
            else: # list honor per players, not sorted
                players = data[cid][-1]
                await asyncio.sleep(0)
                # query db
                data = await self.bot.ranking.searchGWDB("(" + ",".join(players) + ")", 4)
                # send result
                if data[1] is None:
                    await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="No GW data found", color=self.COLOR))
                else:
                    players = {int(p) : "n/a" for p in players}
                    for p in data[1]:
                        if p.id in players:
                            players[p.id] = str(p.current)
                    await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="\n".join(list(players.values())), color=self.COLOR))