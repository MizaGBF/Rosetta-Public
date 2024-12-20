﻿import disnake
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
    if CREW_SERVER_ID is None: guild_ids = []
    else: guild_ids = [CREW_SERVER_ID]
    COLOR = 0xffce47

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def startTasks(self) -> None:
        pass

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
        for sid in crews:
            c.execute("SELECT * FROM crews WHERE id = {}".format(sid)) # get the score
            data = c.fetchall()
            if data is None or len(data) == 0: raise Exception("Failed to retrieve data")
            infos.append([data[0][2], data[0][d[day]]-data[0][d[day]-1], data[0][8]]) # name, score of the day, top speed
            await asyncio.sleep(0)  
        c.close()
        conn.close()
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
        if len(plot) == 0: return None
        img = Image.new("RGB", (800, 600), (255,255,255))
        d = ImageDraw.Draw(img)
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
        
        # y notes
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
        # x notes
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

        # lines
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

        with BytesIO() as output:
            img.save(output, format="PNG")
            img.close()
            return output.getvalue()

    """updateTracker()
    Update the YouTracker data (GW Match tracker for my crew)
    
    Parameters
    ----------
    t: time of this ranking interval
    day: Integer, current day number
    """
    async def updateTracker(self, t : datetime, day : int) -> None:
        you_id = self.bot.data.config['granblue']['gbfgcrew'].get('you', None) # our id
        
        if you_id is None: return
        if self.bot.data.save['matchtracker'] is None: return # not initialized
        if self.bot.data.save['matchtracker']['day'] != day: # new day, reset
            self.bot.data.save['matchtracker'] = {
                'day':day,
                'init':False,
                'id':self.bot.data.save['matchtracker']['id'],
                'plot':[]
            }
            self.bot.data.pending = True
            
        infos = await self.searchScoreForTracker(day, [you_id, self.bot.data.save['matchtracker']['id']])
        newtracker = self.bot.data.save['matchtracker'].copy()
        if newtracker['init']:
            d = t - newtracker['last']
            speed = d.seconds//60
            # rounding to multiple of 20min
            if speed % 20 > 15:
                speed += 20 - (speed % 20)
            elif speed % 20 < 5:
                speed -= (speed % 20)
            # applying
            if speed != 0:
                speed = [(infos[0][1] - newtracker['scores'][0]) / speed, (infos[1][1] - newtracker['scores'][1]) / speed]
                if speed[0] > newtracker['top_speed'][0]: newtracker['top_speed'][0] = speed[0]
                if speed[1] > newtracker['top_speed'][1]: newtracker['top_speed'][1] = speed[1]
                newtracker['speed'] = speed
            else:
                newtracker['speed'] = None
        else:
            newtracker['init'] = True
            newtracker['speed'] = None
            newtracker['top_speed'] = [0, 0]
        newtracker['names'] = [infos[0][0], infos[1][0]]
        newtracker['scores'] = [infos[0][1], infos[1][1]]
        newtracker['max_speed'] = [infos[0][2], infos[1][2]]
        newtracker['last'] = t
        newtracker['gwid'] = self.bot.data.save['gw']['id']
        if newtracker['speed'] is not None: # save chart data
            newtracker['plot'].append([t, newtracker['speed'][0] / 1000000, newtracker['speed'][1] / 1000000])
        if len(newtracker['plot']) > 1: # generate chart
            try:
                imgdata = await self.drawChart(newtracker['plot'])
                with BytesIO(imgdata) as f:
                    if f.getbuffer().nbytes > 0:
                        with self.bot.file.discord(f, filename="chart.png") as df:
                            message = await self.bot.send('image', file=df)
                            newtracker['chart'] = message.attachments[0].url
            except Exception as e:
                self.bot.logger.pushError("[RANKING] 'updatetracker (Upload)' error:", e)
        self.bot.data.save['matchtracker'] = newtracker
        self.bot.data.pending = True

    @commands.slash_command(guild_ids=guild_ids)
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    async def you(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @you.sub_command()
    async def lead(self, inter: disnake.GuildCommandInteraction, opponent : str = commands.Param(description="Opponent ID to set it (Mod Only)", default="")) -> None:
        """Show the current match of (You) ((You) Server Only)"""
        await inter.response.defer()
        if opponent != "" and self.bot.isMod(inter):
            crew_id_list = self.bot.data.config['granblue'].get('gbfgcrew', {}) | self.bot.data.config['granblue'].get('othercrew', {})
            if opponent.lower() in crew_id_list:
                oid = crew_id_list[opponent.lower()]
            else:
                try: oid = int(opponent)
                except:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Invalid ID `{}`".format(opponent), color=self.COLOR))
                    return
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
        else:
            if self.bot.data.save['matchtracker'] is None or not self.bot.data.save['matchtracker']['init']:
                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War**".format(self.bot.emote.get('gw')), description="Unavailable, either wait the next ranking update or add the opponent id after the command to initialize it", color=self.COLOR))
            else:
                ct = self.bot.util.JST()
                you_id = self.bot.data.config['granblue']['gbfgcrew'].get('you', None)
                d = ct - self.bot.data.save['matchtracker']['last']
                msg = "Updated: **{}** ago".format(self.bot.util.delta2str(d, 0))
                if d.seconds >= 1200 and d.seconds <= 1800: msg += " ▫ *updating*"
                msg += "\n"
                if self.bot.data.save['matchtracker']['last'].hour < 7:
                    end_time = self.bot.data.save['matchtracker']['last'].replace(hour=0, minute=0, second=0, microsecond=0)
                else:
                    end_time = self.bot.data.save['matchtracker']['last'].replace(day=self.bot.data.save['matchtracker']['last'].day+1, hour=0, minute=0, second=0, microsecond=0)
                remaining = end_time - self.bot.data.save['matchtracker']['last']
                lead_speed = None
                for i in range(2):
                    msg += "[{:}](https://game.granbluefantasy.jp/#guild/detail/{:}) ▫️ **{:,}**".format(self.bot.data.save['matchtracker']['names'][i], (you_id if i == 0 else self.bot.data.save['matchtracker']['id']), self.bot.data.save['matchtracker']['scores'][i])
                    
                    if self.bot.data.save['matchtracker']['speed'] is None:
                        msg += "\n\n"
                        continue
                    if i == 0: lead_speed = self.bot.data.save['matchtracker']['speed'][0]
                    elif lead_speed is not None: lead_speed -= self.bot.data.save['matchtracker']['speed'][1]
                    else: lead_speed = None
                    
                    msg += "\n**Speed** ▫️ Now {}/m".format(self.bot.util.valToStr(self.bot.data.save['matchtracker']['speed'][i], 2))
                    if self.bot.data.save['matchtracker']['speed'][i] >= self.bot.data.save['matchtracker']['top_speed'][i]:
                        msg += " ▫️ **Top {}/m** {}".format(self.bot.util.valToStr(self.bot.data.save['matchtracker']['top_speed'][i], 2), ":white_check_mark:" if i == 0 else ":warning:")
                    else:
                        msg += " ▫️ Top {}/m".format(self.bot.util.valToStr(self.bot.data.save['matchtracker']['top_speed'][i], 2))
                    max_speed = max(self.bot.data.save['matchtracker']['max_speed'][i], self.bot.data.save['matchtracker']['top_speed'][i])
                    if self.bot.data.save['matchtracker']['speed'][i] >= max_speed:
                        msg += " ▫️ **Max {}/m** {}".format(self.bot.util.valToStr(max_speed, 2), ":white_check_mark:" if i == 0 else ":warning:")
                    else:
                        msg += " ▫️ Max {}/m".format(self.bot.util.valToStr(max_speed, 2))
                    if end_time > self.bot.data.save['matchtracker']['last']:
                        current_estimation = self.bot.data.save['matchtracker']['scores'][i] + self.bot.data.save['matchtracker']['speed'][i] * remaining.seconds//60
                        max_estimation = self.bot.data.save['matchtracker']['scores'][i] + max_speed * remaining.seconds//60
                        top_estimation = self.bot.data.save['matchtracker']['scores'][i] + self.bot.data.save['matchtracker']['top_speed'][i] * remaining.seconds//60
                        msg += "\n**Estimation** ▫ Now {} ▫️ Top {} ▫️ Max {}".format(self.bot.util.valToStr(current_estimation, 3), self.bot.util.valToStr(top_estimation, 3), self.bot.util.valToStr(max_estimation, 3))
                    else:
                        lead_speed = None # disable lead check if the match ended
                    msg += "\n\n"
                lead = self.bot.data.save['matchtracker']['scores'][0] - self.bot.data.save['matchtracker']['scores'][1]
                if lead != 0:
                    msg += "**Difference** ▫️ {:,}".format(abs(lead))
                    if lead_speed is not None and lead_speed != 0:
                        try:
                            if lead < 0: lead_speed *= -1
                            msg += " ▫️ {}/m".format(self.bot.util.valToStr(lead_speed, 3))
                            lead_will_switch = False
                            if lead_speed < 0:
                                minute = abs(lead) / abs(lead_speed)
                                d = self.bot.data.save['matchtracker']['last'] + timedelta(seconds=minute*60)
                                e = ct.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
                                if e > d:
                                    if lead > 0: msg += "\n:warning: "
                                    else: msg += "\n:white_check_mark: "
                                    if d >= ct:
                                        msg += "The Lead switches in **{}** at current speeds".format(self.bot.util.delta2str(d - ct))
                                    else:
                                        msg += "The Lead might have switched"
                                    lead_will_switch = True
                            if not lead_will_switch and lead > 0:
                                if self.bot.data.save['matchtracker']['scores'][0] > top_estimation:
                                    if self.bot.data.save['matchtracker']['max_speed'][1] > self.bot.data.save['matchtracker']['top_speed'][1]:
                                        msg += "\n:confetti_ball: Opponent can't catch up but **can still go faster**, be careful"
                                    else:
                                        msg += "\n:confetti_ball: Opponent can't catch up without surpassing their **max speed**"
                                elif self.bot.data.save['matchtracker']['scores'][0] > current_estimation:
                                    msg += "\n:white_check_mark: Opponent can't catch up without increasing their **current speed**"
                                else:
                                    msg += "\n:ok: Opponent can't catch up at **current speeds**, keep going!"
                        except:
                            pass

                await inter.edit_original_message(embed=self.bot.embed(title="{} **Guild War {} ▫️ Day {}**".format(self.bot.emote.get('gw'), self.bot.data.save['matchtracker']['gwid'], self.bot.data.save['matchtracker']['day']), description=msg, timestamp=self.bot.util.UTC(), thumbnail=self.bot.data.save['matchtracker'].get('chart', None), color=self.COLOR))
                await self.bot.util.clean(inter, 90)

    @you.sub_command()
    async def honor(self, inter: disnake.GuildCommandInteraction) -> None:
        """Retrieve (You) members's honor ((You) Server Only)"""
        await inter.response.defer(ephemeral=True)
        crews = list(set(self.bot.data.config['granblue'].get('gbfgcrew', {}).values()))
        crews.sort()
        cid = self.bot.data.config['granblue'].get('gbfgcrew', {}).get("(you)", None)
        if cid is None:
            await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="Crew not found", color=self.COLOR))
        else:
            data = await self.bot.get_cog('GuildWar').updateGBFGData(crews)
            if data is None or cid not in data or len(data[cid][-1]) == 0:
                await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="No player data found", color=self.COLOR))
            else:
                players = data[cid][-1]
                await asyncio.sleep(0)
                # query
                data = await self.bot.ranking.searchGWDB("(" + ",".join(players) + ")", 4)
                
                if data[1] is None:
                    await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="No GW data found", color=self.COLOR))
                else:
                    players = {int(p) : "n/a" for p in players}
                    for p in data[1]:
                        if p.id in players:
                            players[p.id] = str(p.current)
                    await inter.edit_original_message(embed=self.bot.embed(title="(You) Honor List", description="\n".join(list(players.values())), color=self.COLOR))