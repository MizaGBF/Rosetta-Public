from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.singleton import Score, GWDB
    from components.util import JSON
    from components.network import RequestResult
    from components.sql import Database
    from cogs.gw import GuildWar
    from cogs.youcrew import YouCrew
    # Type Aliases
    type GWDBList = list[Score]
    type GWDBInfo = list[GWDB|None]
    type GWDBSearchResult = list[None|GWDBList, None|GWDBList, GWDBInfo]
    type CrewDataEntry = tuple[int, int, str, int, int, int, int, int, float, float]
    type InfoData = list[int]
    type RankingData = list[dict[str, int]]
    type PlayerDataEntry = tuple[int, int, str, int]
import types
from datetime import timedelta, datetime
from collections import deque
from bs4 import BeautifulSoup
from bs4 import element as bs4element
from urllib.parse import unquote
import sqlite3

# ----------------------------------------------------------------------------------------------------------------
# Ranking Component
# ----------------------------------------------------------------------------------------------------------------
# Manage the Unite and Fight rankings (access, DB update, etc...)
# ----------------------------------------------------------------------------------------------------------------

class Ranking():
    # The Ranking component
    
    # Ranking tiers
    TIER_CREWS_FINAL : list[int] = [2500, 5500, 9000, 14000, 18000, 30000]
    TIER_PLAYERS : list[int] = [2000, 100000, 150000, 200000, 270000, 370000]
    UNF_HERO : str = "2000"
    TIER_A : str = "9000"
    TIER_B : str = "19000"
    # Max ranking scrapping tasks
    MAX_TASK : list[int] = 15
    # DB File version
    DB_VERSION : list[int] = 5
    # others
    DB_FILES : list[str] = ["GW_old.sql", "GW.sql"]
    REVERSE_DAYS : list[str] = ['Day 5', 'Day 4', 'Day 3', 'Day 2', 'Day 1']
    REVERSE_DAYS_FULL : list[str] = REVERSE_DAYS+['Interlude', 'Preliminaries']

    def __init__(self : Ranking, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        # crew from config.json
        self.gbfgcrews : dict[str, str] = {}
        self.othercrews : dict[str, str] = {}
        self.allconfigcrews : dict[str, str] = {}
        self.gbfgcrews_id : list[str] = []
        self.othercrews_id : list[str] = []
        # stuff related to retrieving the ranking
        self.getrank_mode : bool = False
        self.getrank_count : int = 0
        self.getrank_update_time : datetime|None = None
        self.rankingtempdata : RankingData = []
        self.stoprankupdate : bool = False
        # gw databases
        self.dbstate : list[bool] = [True, True] # indicate if dbs are available on the drive, True by default
        self.dblock : asyncio.Lock = asyncio.Lock()

    def init(self : Ranking) -> None:
        self.gbfgcrews = self.bot.data.config.get('granblue', {}).get('gbfgcrew', {})
        self.othercrews = self.bot.data.config.get('granblue', {}).get('othercrew', {})
        self.allconfigcrews = self.gbfgcrews | self.othercrews
        for v in self.allconfigcrews.values():
            if not isinstance(v, str):
                raise TypeError
        self.gbfgcrews_id = list(set(self.gbfgcrews.values()))
        self.othercrews_id = list(set(self.othercrews.values()))
        i : int = 0 # remove dupes
        while i < len(self.othercrews_id):
            if self.othercrews_id[i] in self.gbfgcrews_id:
                self.othercrews_id.pop(i)
            else:
                i += 1
        self.gbfgcrews_id.sort()
        self.othercrews_id.sort()

    def startTasks(self : Ranking) -> None:
        if self.bot.isProduction():
            self.bot.runTask('ranking:check', self.checkGWRanking)

    """requestRanking()
    Request a page from the GW ranking
    
    Parameters
    ----------
    page: Requested page
    mode: 0=crew ranking, 1=prelim crew ranking, 2=player ranking
    timeout: if True, the request will have a timeout of 20 seconds
    
    Returns
    --------
    dict: JSON Data from the request
    """
    async def requestRanking(self : Ranking, page : int, mode : int = 0) -> RequestResult:
        # Check if gw is on going
        if self.bot.data.save['gw']['state'] is False or self.bot.util.JST() <= self.bot.data.save['gw']['dates']["Preliminaries"]:
            return None
        res : RequestResult
        match mode:
            case 0: # crew ranking
                res = await self.bot.net.requestGBF("teamraid{}/rest/ranking/totalguild/detail/{}/0".format(str(self.bot.data.save['gw']['id']).zfill(3), page), expect_JSON=True)
            case 1: # prelim crew ranking
                res = await self.bot.net.requestGBF("teamraid{}/rest/ranking/guild/detail/{}/0".format(str(self.bot.data.save['gw']['id']).zfill(3), page), expect_JSON=True)
            case 2: # player ranking
                res = await self.bot.net.requestGBF("teamraid{}/rest_ranking_user/detail/{}/0".format(str(self.bot.data.save['gw']['id']).zfill(3), page), expect_JSON=True)
        return res

    """checkGWRanking()
    Bot task to update the ranking data. Only needed once every 20 minutes
    """
    async def checkGWRanking(self : Ranking) -> None:
        cog : GuildWar = self.bot.get_cog('GuildWar') # retrieve cog
        if cog is None:
            return

        while True:
            cog.getGWState() # refresh gw state
            try:
                current_time : datetime = self.bot.util.JST()
                # check the gw state
                if self.bot.data.save['gw']['state'] is False: # is set ?
                    if 'ranking' not in self.bot.data.save['gw'] or self.bot.data.save['gw']['ranking'] is not None:
                        self.bot.data.save['gw']['ranking'] = None
                        self.bot.data.pending = True
                    await asyncio.sleep(86400) # sleep one day
                elif current_time < self.bot.data.save['gw']['dates']["Preliminaries"]: # hasn't started?
                    if 'ranking' not in self.bot.data.save['gw'] or self.bot.data.save['gw']['ranking'] is not None:
                        self.bot.data.save['gw']['ranking'] = None
                        self.bot.data.pending = True
                    delta : timedelta = self.bot.data.save['gw']['dates']["Preliminaries"] - current_time
                    # wait until the start before checking again
                    if delta >= timedelta(days=1):
                        await asyncio.sleep(86400)
                    else:
                        await asyncio.sleep(delta.seconds + 1)
                elif current_time > self.bot.data.save['gw']['dates']["Day 5"] - timedelta(seconds=21600): # day 4 is over?
                    await asyncio.sleep(3600) # just sleep
                else: # on going
                    # retrieve estimation from wiki
                    if 'estimation' not in self.bot.data.save['gw']:
                        await self.init_estimation()
                    # retrieve ranking
                    if await self.bot.net.gbf_available():
                        m : int = current_time.minute
                        h : int = current_time.hour
                        skip : bool = False
                        # check current day and if we should get the ranking
                        d : int
                        for d in ["End", "Day 5", "Day 4", "Day 3", "Day 2", "Day 1", "Interlude", "Preliminaries"]:
                            if current_time < self.bot.data.save['gw']['dates'][d]:
                                continue
                            if d == "Preliminaries":
                                diff : timedelta = current_time - self.bot.data.save['gw']['dates'][d]
                                if diff.days == 1 and diff.seconds >= 25200:
                                    skip = True
                            elif ((d.startswith("Day") and h < 7 and h >= 2) or d == "Day 5"):
                                skip = True
                            break
                        # taking action or not
                        if skip:
                            await asyncio.sleep(600) # we sleep 10min if we skip
                        elif m in [3, 4, 23, 24, 43, 44]: # minute to update
                            update_time : datetime = current_time.replace(minute=20 * (current_time.minute // 20), second=1, microsecond=0) # calculate this 20 minutes period time
                            # START THE UPDATE
                            if await self.update_ranking(update_time, d == "Preliminaries"):
                                # retrieve the whole ranking if it went well
                                await self.retrieve_ranking(update_time)
                            await asyncio.sleep(180) # wait 3 minutes
                        else:
                            await asyncio.sleep(25)
                    else:
                        await asyncio.sleep(60) # wait a minute
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'gw:ranking' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'gw:ranking' Task Error:", e)
                return

    """init_estimation()
    Coroutine to retrieve the previous GW data from the wiki
    """
    async def init_estimation(self : Ranking) -> None:
        cnt : RequestResult = await self.bot.net.requestWiki("User:Neofaucheur/Unite_and_Fight_Data", allow_redirects=True)
        # We use Neofaucheur's past GW data for /gw estimation
        # The data is embedded in the html, so it's a "simple" matter to parse and extract the past gw datas
        if cnt is not None:
            try: cnt = cnt.decode('utf-8')
            except: cnt = cnt.decode('iso-8859-1') # rare encoding used on the wiki
            soup : BeautifulSoup = BeautifulSoup(cnt, 'html.parser') # parse the html
            # look for the content
            content : bs4element.ResultSet = soup.find_all("div", id="mw-content-text")
            if len(content) == 0:
                return
            content = content[0].findChildren("div", class_="mw-parser-output", recursive=False)
            if len(content) == 0:
                return
            # variables
            crew : int|None = None
            data : list[dict[str, list[int|None]]] = [{}, {}]
            xaxis : dict[str, int] = {str((i+1)*1200):i for i in range(0, 447)} # the x plot is always the same: a big array of each timestamp. The ranking being updated every 20min, the array contains all multiples of 1200 (20min) to cover the whole duration of the gw
            # read the page
            children : bs4element.Tag
            for children in content[0].findChildren(recursive=False):
                div : bs4element.Tag|None = None
                if crew is None: # undefined
                    if children.name == "h2":
                        if children.text == "Individual":
                            crew = 1
                        elif children.text == "Crew Finals":
                            crew = 0
                        elif children.text == "Prelims":
                            crew = 0
                elif crew == 1: # indiv
                    if children.name == "h2":
                        if children.text == "Crew Finals":
                            crew = 0
                    elif children.name == "div":
                        try:
                            if "mw-collapsible" in children.attrs['class']:
                                div = children
                        except:
                            pass
                else: # crew
                    if children.name == "h2":
                        if children.text == "Individual":
                            crew = 1
                    elif children.name == "div":
                        try:
                            if "mw-collapsible" in children.attrs['class']:
                                div = children
                        except:
                            pass
                if div is not None: # if div found
                    tops : bs4element.ResultSet = div.findChildren("span", class_="mw-headline", recursive=True)
                    if len(tops) > 0:
                        try:
                            rank : str
                            if tops[0].text == '"Unite and Fight Hero"':
                                rank = self.UNF_HERO
                            elif tops[0].text.startswith('Top '):
                                rank = str(int(tops[0].text.replace('Top ', '').replace(',', '')))
                            elif tops[0].text.startswith('Tier '):
                                if crew == 0 and tops[0].text in ["Tier A", "Tier B"]:
                                    if tops[0].text[-1] == "A":
                                        rank = self.TIER_A
                                    else:
                                        rank = self.TIER_B
                                else:
                                    rank = int(tops[0].text.replace('Tier ', '').replace(',', ''))
                                    if crew == 1:
                                        rank = str(self.TIER_PLAYERS[rank])
                                    else:
                                        rank = str(self.TIER_CREWS[rank-1])
                            spans : bs4element.ResultSet = div.findChildren("span", recursive=True)
                            # bracket change end
                            span : bs4element.tag
                            for span in spans:
                                if span.has_attr("data-series-label") and span["data-series-label"].startswith('U&F') and int(span["data-series-label"].replace('U&F', '')) == self.bot.data.save['gw']['id'] - 1:
                                    data[crew][rank] = [None] * len(xaxis.keys())
                                    temp_x : list[str] = span["data-series-x"].split(',')
                                    temp_y : list[str] = span["data-series-y"].split(',')
                                    i : int
                                    v : str
                                    for i, v in enumerate(temp_y):
                                        data[crew][rank][xaxis[temp_x[i]]] = int(v)
                                    last : int|None = None
                                    for i in range(len(data[crew][rank])):
                                        if data[crew][rank][i] is None:
                                            data[crew][rank][i] = last
                                        else:
                                            last = data[crew][rank][i]
                                    break
                        except:
                            pass
            # saving
            if len(data[0].keys()) > 0 and len(data[1].keys()) > 0:
                self.bot.data.save['gw']['estimation'] = data
                self.bot.data.pending = True
                self.bot.logger.push("[RANKING] Wiki Guild War data loaded", send_to_discord=False)

    """update_ranking()
    Coroutine to start the ranking update process
    
    Parameters
    --------
    update_time: Datetime, current time period of 20min
    is_prelim: Boolean, set to True if we check the prelims page
    
    Returns
    --------
    bool: True if success, False if not
    """
    async def update_ranking(self : Ranking, update_time : datetime, is_prelim : bool) -> bool:
        self.bot.logger.push("[RANKING] Updating Main Ranking...", send_to_discord=False)
        # update $ranking and $estimation
        try:
            self.rankingtempdata = [{}, {}, {}, {}, update_time] # crew, player, speed crew, player speed, update_time
            diff : float
            if self.bot.data.save['gw']['ranking'] is not None:
                diff = round((self.rankingtempdata[4] - self.bot.data.save['gw']['ranking'][4]).total_seconds() / 60.0)
            else:
                diff = 0.0
            
            for uri, prelim_uri, is_player in [("teamraid{}/ranking/content/guild", True, False), ("teamraid{}/ranking/content/totalguild", False, False), ("teamraid{}/ranking/content/user", False, True)]:
                if not is_prelim and prelim_uri:
                    continue
                data = unquote((await self.bot.net.requestGBF(uri.format(str(self.bot.data.save['gw']['id']).zfill(3)), expect_JSON=True))["data"])
                soup : BeautifulSoup = BeautifulSoup(data, 'html.parser')
                tags : bs4element.ResultSet = soup.find_all("div", class_="lis-ranking")
                table : dict[str, int] = {}
                speed : dict[str, float]= {}
                for entry in tags:
                    try:
                        rank : str = entry.findChildren("div", class_="ico-rank-digits")[0].text.replace("#", "").replace(",", "")
                        if is_player:
                            table[rank] = int(entry.findChildren("div", class_="prt-point honors", recursive=True)[0].findChildren("div", class_="txt-total-record")[0].text.replace(",", ""))
                        else:
                            table[rank] = int(entry.findChildren("div", class_="txt-total-record", recursive=True)[0].text.replace(",", ""))
                        if diff > 0 and self.bot.data.save['gw']['ranking'] is not None and rank in self.bot.data.save['gw']['ranking'][0]:
                            speed[rank] = (table[rank] - self.bot.data.save['gw']['ranking'][0][rank]) / diff
                    except:
                        pass
                self.rankingtempdata[1 if is_player else 0] = self.rankingtempdata[1 if is_player else 0] | table # merge this one, for prelims
                self.rankingtempdata[3 if is_player else 2] = speed

            # sort the result
            i : int
            for i in range(0, 4):
                self.rankingtempdata[i] = dict(sorted(self.rankingtempdata[i].items(), reverse=True, key=lambda item: int(item[1])))

            # check if the result contains data
            if len(self.rankingtempdata[0]) + len(self.rankingtempdata[1]) > 0:
                # and save it if it does
                self.bot.data.save['gw']['ranking'] = self.rankingtempdata
                self.bot.data.pending = True
                self.bot.logger.push("[RANKING] Main Ranking done with success", send_to_discord=False)
                return True
            self.bot.logger.push("[RANKING] Main Ranking aborted: No data to retrieve", send_to_discord=False, level=self.bot.logger.WARNING)
            return False
        except Exception as ex:
            self.bot.logger.pushError("[TASK] 'gw:ranking' Task Error:", ex)
            self.bot.data.save['gw']['ranking'] = None
            self.bot.data.pending = True
            return False

    """retrieve_ranking()
    Coroutine to start the ranking retrieval process
    
    Parameters
    --------
    update_time: Datetime, current time period of 20min
    force: True to force regardless of time and day (only for debug/test purpose)
    """
    async def retrieve_ranking(self : Ranking, update_time : datetime, force : bool = False) -> None:
        # retrieve the ranking
        getrankout : str = await self.gwgetrank(update_time, force)
        # check the result message
        if getrankout == "": # no news, good news
            data : GWDBInfo = await self.getGWDB() # retrieve current databases
            async with self.dblock:
                if data is not None and data[1] is not None:
                    # compare if current gw is the same gw as we just retrieved
                    if self.bot.data.save['gw']['id'] != data[1].gw:
                        # different gw
                        # Now, check if the past gw database exists
                        if data[0] is not None:
                            # then create a backup
                            self.bot.drive.mvFile("GW_old.sql", self.bot.data.config['tokens']['files'], "GW{}_backup.sql".format(data[0].gw))
                            await asyncio.sleep(5)
                        # Move current gw to past gw
                        self.bot.drive.mvFile("GW.sql", self.bot.data.config['tokens']['files'], "GW_old.sql")
                        await self.bot.sql.remove_list(self.DB_FILES) # Clean databases in memory
                        self.bot.file.mv("GW.sql", "GW_old.sql")
                # Upload our new database
                err : int
                for err in range(5): # try to upload 5 times in case of issues
                    await asyncio.sleep(5)
                    if self.bot.drive.overwriteFile("temp.sql", "application/sql", "GW.sql", self.bot.data.config['tokens']['files']) is False: # upload
                        if err == 4:
                            self.bot.logger.pushError("[RANKING] 'retrieve_ranking' error, upload failed")
                    else:
                        break
                # remove GW.sql in memory
                await self.bot.sql.remove("GW.sql")
                # rename temp.sql to GW.sql
                self.bot.file.mv('temp.sql', "GW.sql")
                # refresh database states without redownloading
                self.dbstate = [False, False]
                i : int
                fs : str
                for i, fs in enumerate(self.DB_FILES):
                    await self.bot.sql.remove(fs)
                    if await self.bot.sql.add(fs) is not None:
                        self.dbstate[i] = True
                await asyncio.sleep(0)
        elif getrankout != "Invalid day" and getrankout != "Skipped":
            self.bot.logger.pushError("[RANKING] 'gwgetrank' failed:\n" + getrankout)
        else:
            self.bot.logger.push("[RANKING] 'gwgetrank' stop reason: " + getrankout, send_to_discord=False)

    """getrankProcess()
    Coroutine to retrieve mass data from the ranking
    
    Parameters
    ----------
    status: Task shared status and data
    """
    async def getrankProcess(self : Ranking, status : list[int|deque]) -> None:
        # status format:
        # [
        #     count task finished,
        #     input queue, queue the pages to retrieve,
        #     output queue, queue what we already retrieved on the first page
        # ]
        while True:
            # if the input queue is empty of certain flags are raised/unraised
            if len(status[1]) == 0 or not self.bot.running or self.stoprankupdate:
                # the download ended
                if status[0] == 0:  # the first task put a log message
                    self.bot.logger.push("[RANKING] Ranking download ended", send_to_discord=False)
                # increase counter
                status[0] += 1
                return
            try: # retrieve an element
                page : int = status[1].popleft()
            except: # error, go back to start of loop (shouldn't happen...)
                continue
            data : RequestResult = None
            while data is None: # attempt to download the page until we get a positive result
                data = await self.requestRanking(page, (0 if self.getrank_mode else 2)) # request the page
                # check if process has been stopped in the meantime
                if (self.bot.data.save['maintenance']['state'] and self.bot.data.save['maintenance']["duration"] == 0) or self.stoprankupdate:
                    status[0] += 1 # increase counter
                    return
            await asyncio.sleep(0) # sleep 0 to leave other tasks do their things
            item : JSON
            for item in data['list']: # put the entries in the output queue
                status[2].append(item)

    """getCurrentGWDayID()
    Associate the current GW day to an integer and return it
    
    Returns
    --------
    int:
        0=prelims, 1=interlude, 2=day 1, 3=day 2, 4=day 3, 5=day 4
        10 to 15: same as above but during the break period
        25: Final rally or end
        None: Undefined
    """
    def getCurrentGWDayID(self : Ranking) -> int|None:
        if self.bot.data.save['gw']['state'] is False: # gw isn't on going
            return None
        current_time : datetime = self.bot.util.JST()
        d : timedelta
        if current_time < self.bot.data.save['gw']['dates']["Preliminaries"]: # prelims
            return None
        elif current_time >= self.bot.data.save['gw']['dates']["End"]: # ended
            return 25
        elif current_time >= self.bot.data.save['gw']['dates']["Day 5"]: # final rally
            return 25
        elif current_time >= self.bot.data.save['gw']['dates']["Day 1"]: # day
            i : int
            for i in range(1, len(self.REVERSE_DAYS)): # loop to not copy paste this 5 more times
                if current_time >= self.bot.data.save['gw']['dates'][self.REVERSE_DAYS[i]]:
                    d = self.bot.data.save['gw']['dates'][self.REVERSE_DAYS[i-1]] - current_time
                    if d < timedelta(seconds=18000):
                        return 16 - i # day has ended
                    else:
                        return 6 - i # day on going
        elif current_time > self.bot.data.save['gw']['dates']["Interlude"]: # interlude
            return 1
        elif current_time > self.bot.data.save['gw']['dates']["Preliminaries"]: # prelims
            d = self.bot.data.save['gw']['dates']['Interlude'] - current_time
            if d < timedelta(seconds=18000):
                return 10
            else:
                return 0
        # undefined
        return None

    """gwdbbuilder()
    Coroutine to build the GW database from getrankProcess output
    
    Parameters
    ----------
    status: Task status
    day: Integer, current day (0 being prelim, 1 being interlude, 2 = day 1, etc...)
    
    Returns
    ----------
    str: Empty string if success, error message otherwise
    """
    async def gwdbbuilder(self : Ranking, status : list[int|deque], day : int) -> str:
        try:
            # open/create temp.sql
            conn : sqlite3.Connection = sqlite3.connect('temp.sql', isolation_level=None)
            c : sqlite3.Cursor = conn.cursor()
            c.execute("PRAGMA synchronous = normal")
            c.execute("PRAGMA locking_mode = exclusive")
            c.execute("PRAGMA journal_mode = OFF")
            c.execute("BEGIN") # no autocommit
            await asyncio.sleep(30) # wait a bit, downloads need to start anyway
            self.bot.logger.push("[RANKING] Starting to fill temp.sql...", send_to_discord=False)
            diff : float|None = None
            timestamp : int|None = None
            new_timestamp : int = int(self.getrank_update_time.timestamp())

            c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='info'") # retrieve the info table if it exists
            await asyncio.sleep(0)
            if c.fetchone()[0] < 1: # it doesn't, create it
                c.execute('CREATE TABLE info (gw int, ver int, date int)')
                c.execute('INSERT INTO info VALUES ({}, {}, {})'.format(self.bot.data.save['gw']['id'], self.DB_VERSION, new_timestamp))
                await asyncio.sleep(0)
            else: # it does...
                c.execute("SELECT * FROM info")
                await asyncio.sleep(0)
                x : InfoData = c.fetchone()
                # retrieve last update timestamp
                timestamp = x[2]
                # and compute the timedelta
                diffdelta : timedelta = self.getrank_update_time - datetime.utcfromtimestamp(timestamp)
                diff = diffdelta.seconds / 60
                # update the timestamp
                c.execute("UPDATE info SET date = {} WHERE ver = {}".format(new_timestamp, self.DB_VERSION))
                await asyncio.sleep(0)

            # create a ranking table
            crews : dict[str, CrewDataEntry]
            if self.getrank_mode: # crew table creation (fetch existing data, delete an existing one, we want the file to keep a small size)
                c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='crews'")
                await asyncio.sleep(0)
                if c.fetchone()[0] == 1:
                    c.execute("SELECT * FROM crews")
                    await asyncio.sleep(0)
                    crews = {x[1] : list(x) for x in c.fetchall()} # retrieve data
                    c.execute('DROP TABLE crews')
                    await asyncio.sleep(0)
                else:
                    crews = {}
                c.execute('CREATE TABLE crews (ranking int, id int, name text, preliminaries int, total_1 int, total_2 int, total_3 int, total_4 int, top_speed float, current_speed float)')
                await asyncio.sleep(0)
            else: # player table creation (delete an existing one, we want the file to keep a small size)
                c.execute("SELECT count(name) FROM sqlite_master WHERE type='table' AND name='players'")
                await asyncio.sleep(0)
                if c.fetchone()[0] == 1:
                    c.execute('DROP TABLE players')
                    await asyncio.sleep(0)
                c.execute('CREATE TABLE players (ranking int, id int, name text, current_total int)')
                await asyncio.sleep(0)
            c.execute("COMMIT") # commit changes until now
            c.execute("BEGIN")
            await asyncio.sleep(0)
            # now we'll read the output queue
            inserts : list[CrewDataEntry|PlayerDataEntry] = [] # will contain entries to insert in the database. we add them 1000 by 1000
            i : int = 0
            while i < self.getrank_count: # count is the number of ranking entries we're expected to process
                # check if the bot ordered to stop
                if not self.bot.running or (self.bot.data.save['maintenance']['state'] and self.bot.data.save['maintenance']['duration'] == 0) or self.stoprankupdate or (self.bot.util.JST() - self.getrank_update_time > timedelta(seconds=1100)):
                    self.stoprankupdate = True # send the stop signal to other tasks
                    try: # close cleanly
                        c.execute("COMMIT")
                        c.close()
                        conn.close()
                        await asyncio.sleep(0)
                    except:
                        pass
                    status[0] += 1
                    # error message
                    return "Forced stop\nCrew Mode: {}\nCount: {}/{}\nQueue: {}".format(self.getrank_mode, i, self.getrank_count, len(status[2]))
                # access the output queue
                try:
                    item : RequestResult = status[2].popleft() # retrieve an entry
                except:
                    await asyncio.sleep(2)
                    continue # wait and skip if the queue is empty

                if self.getrank_mode:
                    # if crew, update the existing crew (if it exists) or create a new entry
                    x : CrewDataEntry = crews.get(int(item['id']), [None, int(item['id']), None, None, None, None, None, None, None, None]) # retrieve old entry
                    last_val : int|None = x[3+day] # get last score of today
                    # if last score exists and delta is valid
                    if diff is not None and last_val is not None and last_val != int(item['point']) and new_timestamp != timestamp:
                        # compute speed
                        speed : float = (int(item['point']) - last_val) / diff
                        # update top speed
                        x[8] = (speed if (x[8] is None or speed > x[8]) else x[8])
                        # and store it
                        x[9] = speed
                    else: # else reset the current speed to unknown
                        x[9] = None
                    # set the updated infos
                    x[0] = int(item['ranking'])
                    x[2] = item['name'].replace("'", "''")
                    # set the current day total
                    x[3+day] = item['point']
                    # replace None by 'NULL'
                    j : int
                    for j in range(len(x)):
                        if x[j] is None: x[j] = 'NULL'
                    # add entry to lines to insert in the file
                    inserts.append("({},{},'{}',{},{},{},{},{},{},{})".format(*x))
                else:
                    # if player, it's simple, we just add the infos in the new table. No other fancy calculations
                    inserts.append("({},{},'{}',{})".format(int(item['rank']), int(item['user_id']), item['name'].replace("'", "''"), int(item['point'])))
                await asyncio.sleep(0)
                i += 1
                # if the inserts queue is full or the ranking is fully processed
                if len(inserts) == 1000 or i == self.getrank_count:
                    if len(inserts) > 0: # insert entries in the file
                        c.execute("INSERT INTO {} VALUES {}".format("crews" if self.getrank_mode else "players", ",".join(inserts)))
                        c.execute("COMMIT")
                        inserts = []
                    if i == self.getrank_count: # if we reached the end, we close the file
                        c.close()
                        conn.close()
                    else: # else we prepare the next commit
                        c.execute("BEGIN")
                    await asyncio.sleep(0.001)
            status[0] += 1
            return ""
        except Exception as err:
            try:
                c.close()
                conn.close()
            except:
                pass
            self.stoprankupdate = True # send the stop signal if a critical error happened
            status[0] += 1
            return 'gwdbbuilder() exception:\n' + self.bot.pexc(err)

    """gwgetrank()
    Setup and manage the retrieval the ranking
    
    Parameters
    ----------
    update_time: time of this ranking interval
    force: True to force the retrieval (debug only)
    
    Returns
    --------
    str: empty string if success, error message if not
    """
    async def gwgetrank(self : Ranking, update_time : datetime, force : bool) -> str:
        try:
            state : str = "" # return value
            self.getrank_update_time = update_time
            skip_mode : int = 0
            i : int
            itd : str
            for i, itd in enumerate(self.REVERSE_DAYS_FULL): # loop to not copy paste this 5 more times
                if update_time > self.bot.data.save['gw']['dates'][itd]:
                    match itd:
                        case 'Preliminaries':
                            if update_time - self.bot.data.save['gw']['dates'][itd] < timedelta(days=0, seconds=3600): # first hour of gw
                                skip_mode = 1 # skip all
                            elif self.bot.data.save['gw']['dates'][self.REVERSE_DAYS_FULL[i-1]] - update_time < timedelta(days=0, seconds=18800):
                                skip_mode = 1 # skip all
                        case 'Interlude':
                            if update_time.minute > 10: # only update players hourly
                                skip_mode = 1 # skip all
                            else:
                                skip_mode = 2 # skip crew
                        case 'Day 5':
                            skip_mode = 1 # skip all
                        case _:
                            if update_time - self.bot.data.save['gw']['dates'][itd] < timedelta(days=0, seconds=7200): # skip players at the start of rounds
                                skip_mode = 3 # skip player
                            elif self.bot.data.save['gw']['dates'][self.REVERSE_DAYS_FULL[i-1]] - update_time < timedelta(days=0, seconds=18800): # skip during break
                                skip_mode = 1 # skip all
                    break
            if force:
                skip_mode = 0
            if skip_mode == 1:
                return 'Skipped'
            await asyncio.sleep(0)
            day : int|None = self.getCurrentGWDayID() # check which day it is (0 being prelim, 1 being interlude, 2 = day 1, etc...)
            if day is None or day >= 10:
                return "Invalid day"
            if day > 0:
                day -= 1 # interlude is put into prelims
            self.bot.logger.push("[RANKING] Updating Database (mode={}, day={})...".format(skip_mode, day), send_to_discord=False)
            n : GWDBInfo = await self.getGWDB()
            await asyncio.sleep(0)
            if n[1] is None or n[1].gw != self.bot.data.save['gw']['id'] or n[1].ver != self.DB_VERSION:
                self.bot.logger.push("[RANKING] Invalid 'GW.sql'. A new 'GW.sql' file will be created", send_to_discord=False)
                self.bot.file.rm('temp.sql') # delete previous temp file (if any)
            else:
                async with self.dblock:
                    self.bot.file.cpy('GW.sql', 'temp.sql')
                self.bot.logger.push("[RANKING] Existing 'GW.sql' file will be updated", send_to_discord=False)

            n : int
            for n in [0, 1]: # n == 0 (crews) or 1 (players)
                # check if we should get this ranking
                if skip_mode == 2 and n == 0:
                    continue
                elif skip_mode == 3 and n == 1:
                    continue
                await asyncio.sleep(0)
                self.bot.logger.push("[RANKING] {} Step...".format('CREW' if n == 0 else 'PLAYER'), send_to_discord=False)
                self.getrank_mode = (n == 0)
                # get the first page of the ranking
                data : RequestResult = await self.requestRanking(1, (0 if self.getrank_mode else 2))
                if data is None or data['count'] is False:
                    return "gwgetrank() can't access the ranking"
                # read obtained data
                self.getrank_count = int(data['count']) # number of crews/players
                last : JSON = data['last'] # number of pages
                self.bot.logger.push("[RANKING] {} pages to download for {} {}...".format(last, self.getrank_count, 'crews' if n == 0 else 'players'), send_to_discord=False)
                # run in tasks
                self.stoprankupdate = False # if true, this flag will stop the tasks
                status : list[int|deque] = [
                    0, # count task finished
                    deque([i for i in range(2, last+1)], last-1), # input queue, queue the pages to retrieve
                    deque(data['list'], self.getrank_count) # output queue, queue what we already retrieved on the first page
                ]
                await asyncio.sleep(0)
                # prepare tasks
                coroutines : list[types.CoroutineType] = [self.getrankProcess(status) for i in range(self.MAX_TASK)]
                self.bot.logger.push("[RANKING] Download started...", send_to_discord=False)
                # start them and wait for result
                results : list[str|None] = await asyncio.gather(self.gwdbbuilder(status, day), *coroutines)
                self.stoprankupdate = True # all tasks should have ended but to be safe...
                r : str|None
                for r in results: # check if any returned an error
                    if r is not None: state = r
                self.bot.logger.push("[RANKING] {} Step Done".format('CREW' if n == 0 else 'PLAYER'), send_to_discord=False)
                if state != "":
                    self.bot.logger.pushError("[RANKING] Database update finished with an error", send_to_discord=False)
                    return state
                
                # if we are during day 1 to 4 and we just processed crews...
                if self.getrank_mode and day > 0 and day < 10: # then update (You) crew tracker
                    try:
                        c : YouCrew = self.bot.get_cog("YouCrew") # get the cog
                        if c is not None:
                            await c.updateTracker(update_time, day) # and pass infos
                    except Exception as ue:
                        self.bot.logger.pushError("[RANKING] 'updatetracker' error:", ue)
            self.bot.logger.push("[RANKING] Database update finished", send_to_discord=False)
            return ""
        except Exception as e:
            self.bot.logger.pushError("[RANKING] Database update interrupted", e, send_to_discord=False)
            self.stoprankupdate = True
            return "Exception: " + self.bot.pexc(e)

    """getGWDB()
    Return the Unite & fight ranking database infos, after downloading them from the google drive if needed
    
    Parameters
    ----------
    force_download: Force the database download if True
    
    Returns
    --------
    list: First element is for the old database, second is for the current one
    """
    async def getGWDB(self : Ranking, force_download : bool = False) -> GWDBInfo:
        res : GWDBInfo = [None, None] # will contain final GWDB() objects
        if force_download:
            self.dbstate = [True, True] # force dbstate to True (file exists)
        i : int
        fs : str
        db : Database
        for i, fs in enumerate(self.DB_FILES):
            async with self.dblock: # lock
                if not force_download: # attempt to get the file from the isk
                    db = await self.bot.sql.get(fs)
                if force_download or db is None: # if file doesn't exist or force_download is raised, start download
                    if not self.dbstate[i]:
                        continue # if dbstate indicates the file doesn't exist, we skip
                    await asyncio.sleep(0)
                    # clear state
                    try:
                        self.dbstate[i] = False # now False, meaning we won't try twice in a row
                        await self.bot.sql.remove(fs)
                    except:
                        pass
                    # download from the drive
                    j : int
                    for j in range(5): # trying 5 times in case of errors
                        try:
                            if self.bot.drive.dlFile(fs, self.bot.data.config['tokens']['files']) is True:
                                await self.bot.sql.add(fs) # add downloaded file to sql component
                                self.dbstate[i] = True # set state to True
                                break
                            else:
                                raise Exception()
                        except:
                            if j == 4:
                                self.bot.logger.pushError("[RANKING] Failed to load database ", fs)
                        await asyncio.sleep(1)
                    # if file is deemed to not exists
                    if not self.dbstate[i]:
                        continue # we skip
                    # attempt to access database content
                    db = await self.bot.sql.get(fs)
                    if db is None:
                        continue
            async with db as c: # read file
                if c is None: # an error occured
                    continue
                # we create GWDB() elements we'll return at the end
                x : InfoData
                try: # current version
                    c.execute("SELECT * FROM info")
                    x = c.fetchone()
                    if len(x) < 1:
                        raise Exception()
                    res[i] = self.bot.singleton.make_GWDB(x)
                except: # old versions
                    try:
                        c.execute("SELECT * FROM GW")
                        x = c.fetchone()
                        if len(x) < 1:
                            raise Exception()
                        res[i] = self.bot.singleton.make_GWDB(x)
                    except:
                        res[i] = self.bot.singleton.make_GWDB()
                await asyncio.sleep(0)
        return res

    """searchGWDB()
    Search the Unite & fight ranking databases
    Returned matches are Score instances
    
    Parameters
    ----------
    terms: Search string
    mode: Search mode (0 = normal search, 1 = exact search, 2 = id search, 3 = ranking search, 4 = custom equal, 5 = custom in, add 10 to search for crews instead of players)
    
    Returns
    --------
    list: Containing:
        - list: Matches in the past GW
        - list: Matches in the latest GW
        - list: GW DB info data
    """
    async def searchGWDB(self : Ranking, terms : str, mode : int) -> None|GWDBSearchResult:
        v : GWDBInfo = await self.getGWDB() # load and get the version of the database files
        async with self.dblock:
            data : GWDBSearchResult = [None, None, v]
            dbs : list[Database] = (await self.bot.sql.get("GW_old.sql"), await self.bot.sql.get("GW.sql")) # get access
            st : int = 1 if mode >= 10 else 0 # search type (crew or player)
            n : int
            for n in [0, 1]: # for both database
                if dbs[n] is None:
                    continue
                async with dbs[n] as c:
                    if c is not None and v[n] is not None: # if the data is loaded and alright
                        try:
                            data[n] : GWDBList = []
                            # search according to the mode
                            match mode:
                                case 10: # crew name search
                                    c.execute("SELECT * FROM crews WHERE lower(name) LIKE ?", ('%' + terms.lower().replace("'", "''").replace("%", "\\%") + '%',))
                                case 11: # crew name exact search
                                    c.execute("SELECT * FROM crews WHERE lower(name) LIKE ?", (terms.lower().replace("'", "''").replace("%", "\\%"),))
                                case 12: # crew id search
                                    c.execute("SELECT * FROM crews WHERE id = ?", (terms,))
                                case 13: # crew ranking search
                                    c.execute("SELECT * FROM crews WHERE ranking = ?", (terms,))
                                case 14: # custom id search, internal use only
                                    c.execute("SELECT * FROM crews WHERE id IN "+ terms)
                                case 0: # player name search
                                    c.execute("SELECT * FROM players WHERE lower(name) LIKE ?", ('%' + terms.lower().replace("'", "''").replace("%", "\\%") + '%',))
                                case 1: # player exact name search
                                    c.execute("SELECT * FROM players WHERE lower(name) LIKE ?", (terms.lower().replace("'", "''").replace("%", "\\%"),))
                                case 2: # player id search
                                    c.execute("SELECT * FROM players WHERE id = ?", (terms,))
                                case 3: # player ranking search
                                    c.execute("SELECT * FROM players WHERE ranking = ?", (terms,))
                                case 4: # custom id search, internal use only
                                    c.execute("SELECT * FROM players WHERE id IN "+ terms)
                            results = c.fetchall() # fetch the result
                            await asyncio.sleep(0)
                            r : CrewDataEntry|PlayerDataEntry
                            for r in results:
                                data[n].append(self.bot.singleton.make_Score(st, v[n].ver, v[n].gw, r)) # make a Score object and append to our list
                        except Exception as e:
                            self.bot.logger.pushError("[RANKING] searchGWDB failed (Settings: {}/{}/{}):".format(n, mode, terms), e)
                            data[n] = None
        return data