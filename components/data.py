import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import json
from io import BytesIO
from datetime import timedelta

# ----------------------------------------------------------------------------------------------------------------
# Save Component
# ----------------------------------------------------------------------------------------------------------------
# This component manages the save data file (save.json)
# It also lets you load config.json (once at startup)
# Works in tandem with the Drive component
# ----------------------------------------------------------------------------------------------------------------

class Data():
    SAVEVERSION = 12
    BASE_SAVE = {
        'version':SAVEVERSION,
        'banned_guilds': [],
        'gbfaccounts': [],
        'gbfcurrent': 0,
        'gbfversion': None,
        'gbfupdate': False,
        'gbfdata': {},
        'maintenance': {"state" : False, "time" : None, "duration" : 0},
        'stream': {'time':None, 'content':[]},
        'schedule': [],
        'spark': {},
        'gw': {'state':False},
        'valiant': {'state':False},
        'reminders': {},
        'permitted': {},
        'extra': {},
        'gbfids': {},
        'assignablerole': {},
        'matchtracker': None,
        'pinboard': {},
        'ban': {},
        'announcement': {},
        'log': [],
        'twitter': {},
        'vxtwitter' : {}
    }
    
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.bot.drive = None
        self.debug = bot.debug_mode or bot.test_mode
        self.config = {}
        self.save = self.BASE_SAVE
        self.pending = False
        self.autosaving = False

    def init(self) -> None:
        pass

    """loadConfig()
    Read config.json. Only called once during boot
    
    Returns
    --------
    bool: True on success, False on failure
    """
    def loadConfig(self) -> bool:
        try:
            with open('config.json') as f:
                data = json.load(f, object_pairs_hook=self.bot.util.json_deserial_dict) # deserializer here
                self.config = data
                # basic validity check
                for check in ['tokens', 'ids', 'emotes', 'games']:
                    if check not in self.config:
                        raise Exception("'{}' section not found in 'config.json'".format(check))
            if self.debug:
                with open('config_test.json') as f:
                    data = json.load(f, object_pairs_hook=self.bot.util.json_deserial_dict) # deserializer here
                    self.config = self.config | data
                    # basic validity check
                    for check in ['tokens', 'ids', 'emotes', 'games']:
                        if check not in self.config:
                            raise Exception("'{}' section not found in 'config_test.json'".format(check))
            return True
        except Exception as e:
            self.bot.logger.pushError("[BOOT] An error occured while loading the configuration file:", e)
            return False

    """loadData()
    Read save.json.
    Assure the retrocompatibility with older save files.
    
    Returns
    --------
    bool: True on success, False on failure
    """
    def loadData(self) -> bool:
        try:
            with open('save.json') as f:
                data = json.load(f, object_pairs_hook=self.bot.util.json_deserial_dict) # deserializer here
                if any(data):
                    ver = data.get('version', None)
                else: # fresh save file
                    ver = self.SAVEVERSION
                if ver is None:
                    raise Exception("This save file isn't compatible")
                elif ver < self.SAVEVERSION:
                    if ver == 0:
                        if 'newserver' in data:
                            newserver = data.pop('newserver', None)
                            if 'guilds' not in data:
                                data['guilds'] = {"owners": newserver.get('owners', []), "pending": newserver.get('pending', {}), "banned": newserver.get('servers', [])}
                        for rid in data.get('reminders', {}):
                            for r in data['reminders'][rid]:
                                if len(r) == 2:
                                    r.append("")
                        try: data['gbfdata'].pop('new_ticket', None)
                        except: pass
                        try: data['gbfdata'].pop('count', None)
                        except: pass
                    if ver <= 1:
                        data['ban'] = {}
                        if 'guilds' in data:
                            for i in data['guilds']['owners']:
                                data['ban'][str(i)] = 0b1
                            data['guilds'].pop('owners', None)
                        else:
                            data['guilds'] = {}
                        if 'spark' in data:
                            for i in data['spark'][1]:
                                data['ban'][str(i)] = 0b10 | data['ban'].get(str(i), 0)
                            data['spark'] = data['spark'][0]
                        else:
                            data['spark'] = {}
                    if ver <= 2:
                        if 'guilds' in data:
                            data['banned_guilds'] = data['guilds'].get('banned', [])
                        else:
                            data['banned_guilds'] = []
                        data.pop('guilds', None)
                    if ver <= 3:
                        data['guilds'] = None
                    if ver <= 4: # spark system update
                        if 'spark' in data:
                            keys = list(data['spark'].keys())
                            c = self.bot.util.UTC()
                            for rid in keys:
                                if len(data['spark'][rid]) == 3:
                                    data['spark'][rid].append(0) # 0 shrimp
                                    data['spark'][rid].append(c) # datetime
                                elif len(data['spark'][rid]) == 4:
                                    data['spark'][rid].insert(3, 0) # 0 shrimp, pos 3
                        else:
                            data['spark'] = {}
                    if ver <= 5:
                        data['gbfdata']['dtm'] = {}
                        data['gbfdata'].pop('ticket_id')
                        data['gbfdata'].pop('c')
                        data['gbfdata'].pop('w')
                    if ver <= 6:
                        announcement = {}
                        for k in data['announcement']:
                            announcement[k] = [data['announcement'][k], 1, False]
                        data['announcement'] = announcement
                    if ver <= 7:
                        data['gbfupdate'] = False
                    if ver <= 8:
                        for k in data['announcement']:
                            c = [data['announcement'][k][0], 0, 0, data['announcement'][k][2]]
                            match data['announcement'][k][1]:
                                case 0:
                                    c[1] = 0b111
                                    c[2] = 0b111
                                case 1:
                                    c[1] = 0b111
                                    c[2] = 0
                                case 2:
                                    c[1] = 1
                                    c[2] = 0
                                case 3:
                                    c[1] = 0
                                    c[2] = 0
                            data['announcement'][k] = c
                    if ver <= 9:
                        data['twitter'] = {'Granblue_GW': ['1623613232329158657', '1623606530988994560', '1623605270466428929', '1623601636634677252', '1623596821217165314', '1623593798738788355', '1623593466604421120', '1623592932849885185', '1623619936873742337'], 'granblue_en': ['1623599382036873217', '1623596794948235267', '1623594220580933632', '1623594634449666049', '1623595035454484480', '1623595590289588224', '1623593806678626310', '1623593523525332993', '1623592943356608512', '1623592823940587521'], 'granbluefantasy': ['1623592576849952770', '1623592567119175683']}
                    if ver <= 10:
                        for i, acc in enumerate(data['gbfaccounts']):
                            data['gbfaccounts'][i][1] = self.bot.net.str2cookie(acc[1])
                    if ver <= 11:
                        for gid in data['announcement']:
                            data['announcement'][gid][1] = (data['announcement'][gid][1] % 2 == 1)
                            data['announcement'][gid][2] = (data['announcement'][gid][2] % 2 == 1)
                    data['version'] = self.SAVEVERSION
                elif ver > self.SAVEVERSION:
                    raise Exception("Save file version higher than the expected version")
                self.save = self.checkData(data)
                self.pending = False
                return True
        except:
            return False

    """saveData()
    Write save.json.
    
    Returns
    --------
    bool: True on success, False on failure
    """
    def saveData(self) -> bool: # saving (lock isn't used, use it outside!)
        if self.debug:
            return True
        try:
            with open('save.json', 'w') as outfile:
                json.dump(self.save, outfile, separators=(',', ':'), default=self.bot.util.json_serial) # locally first
        except Exception as e:
            self.bot.logger.pushError("[DATA] An error occured with the local save data:", e)
        try:
            if self.bot.drive.save(json.dumps(self.save, separators=(',', ':'), default=self.bot.util.json_serial)) is not True: # sending to the google drive
                raise Exception("Couldn't save to google drive")
            return True
        except Exception as e:
            if str(e) != "Couldn't save to google drive":
                self.bot.logger.pushError("[DATA] An error occured while saving the data:", e)
            return False

    """checkData()
    Fill the save data with missing keys, if any
    
    Parameters
    --------
    dict: Save data
    
    Returns
    --------
    dict: Updated data (not a copy)
    """
    def checkData(self, data : dict) -> dict: # used to initialize missing data or remove useless data from the save file
        for k in list(data.keys()): # remove useless
            if k not in self.BASE_SAVE:
                data.pop(k)
        for k in self.BASE_SAVE: # add missing
            if k not in data:
                data[k] = self.BASE_SAVE[k]
        return data

    """autosave()
    Write save.json. Called periodically by statustask()
    The file is also sent to the google drive or to discord if it failed
    
    Parameters
    --------
    discordDump: If True, save.json will be sent to discord even on success
    """
    async def autosave(self, discordDump : bool = False) -> None:
        if self.autosaving or self.debug: return
        self.autosaving = True
        result = False
        for i in range(0, 3): # try a few times
            if self.saveData():
                self.pending = False
                result = True
                break
            await asyncio.sleep(0)
        if not result:
            await self.bot.send('debug', embed=self.bot.embed(title="Failed Save", timestamp=self.bot.util.UTC()))
            discordDump = True
        if discordDump:
            try:
                with BytesIO(json.dumps(self.save, separators=(',', ':'), default=self.bot.util.json_serial).encode('utf-8')) as infile:
                    with self.bot.file.discord(infile, filename="save.json") as df:
                        await self.bot.send('debug', file=df)
            except Exception as se:
                print(se)
        self.autosaving = False

    """maintenance()
    Bot Task managing the autocleanup of the save data and other routines
    """
    async def maintenance(self) -> None:
        try:
            await asyncio.sleep(1000) # after 1000 seconds
            if not self.bot.running: return
        except asyncio.CancelledError:
            return
        first_loop = True
        while True:
            try:
                ct = self.bot.util.JST()
                # empty crew cache
                if not first_loop:
                    try:
                        self.bot.get_cog('GuildWar').crewcache = {}
                    except Exception as xe:
                        self.bot.logger.pushError("[TASK] 'maintenance (Crew Cache)' Task Error:", xe)
                first_loop = False
                # update avatar on first day of some month
                if ct.day == 1:
                    match ct.month:
                        case 2: await self.bot.changeAvatar('icon_flb.png')
                        case 4: await self.bot.changeAvatar('icon_bunny.png')
                        case 6: await self.bot.changeAvatar('icon_summer.png')
                        case 9: await self.bot.changeAvatar('icon.png')
                        case 10: await self.bot.changeAvatar('icon_halloween.png')
                        case 11: await self.bot.changeAvatar('icon.png')
                        case 12: await self.bot.changeAvatar('icon_xmas.png')
                # various clean up
                await self.clean_spark() # clean up spark data
                if ct.day == 3: # only clean on the third day of each month
                    await self.clean_profile() # clean up profile data
                await self.clean_others() # clean up everything else
                await self.clean_schedule() # clean schedule
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'maintenance' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'maintenance' Task Error:", e)
            await asyncio.sleep(86399 - (self.bot.util.JST() - ct).total_seconds()) # wait next day


    """clean_spark()
    Coroutine to clear user spark data from the save data
    """
    async def clean_spark(self) -> None:
        await asyncio.sleep(0)
        count = 0
        c = self.bot.util.UTC()
        keys = list(self.save['spark'].keys())
        for rid in keys:
            d = c - self.save['spark'][rid][4]
            if d.days >= 30:
                del self.save['spark'][rid]
                self.pending = True
                count += 1
        if count > 0:
            await self.bot.send('debug', embed=self.bot.embed(title="clean()", description="Cleaned {} unused spark saves".format(count), timestamp=self.bot.util.UTC()))

    """clean_profile()
    Coroutine to clean user gbf profiles from the save data
    """
    async def clean_profile(self) -> None:
        await asyncio.sleep(0)
        count = 0
        keys = list(self.save['gbfids'].keys())
        for uid in keys:
            found = False
            for g in self.bot.guilds:
                 if await g.get_or_fetch_member(int(uid)) is not None:
                    found = True
                    break
            if not found:
                count += 1
                self.save['gbfids'].pop(uid)
                self.pending = True
        if count > 0:
            await self.bot.send('debug', embed=self.bot.embed(title="clean()", description="Cleaned {} unused profiles".format(count), timestamp=self.bot.util.UTC()))

    """clean_schedule()
    Coroutine to clean the gbf schedule from the save data
    """
    async def clean_schedule(self) -> None:
        c = self.bot.util.JST()
        new_schedule = []
        for i in range(0, ((len(self.save['schedule'])//2)*2), 2):
            try:
                date = self.save['schedule'][i].replace(" ", "").split("-")[-1].split("/")
                x = c.replace(month=int(date[0]), day=int(date[1])+1, microsecond=0)
                if c - x > timedelta(days=160):
                    x = x.replace(year=x.year+1)
                if c >= x:
                    continue
            except:
                pass
            new_schedule.append(self.save['schedule'][i])
            new_schedule.append(self.save['schedule'][i+1])
        if len(new_schedule) != 0 and len(new_schedule) != len(self.save['schedule']):
            self.save['schedule'] = new_schedule
            self.pending = True
            await self.bot.send('debug', embed=self.bot.embed(title="clean()", description="The schedule has been cleaned up", timestamp=self.bot.util.UTC()))

    """clean_others()
    Coroutine to clean the save data
    """
    async def clean_others(self) -> None:
        guild_ids = []
        for g in self.bot.guilds:
             guild_ids.append(str(g.id))
        count = 0
        for gid in list(self.save['permitted'].keys()):
            if gid not in guild_ids or len(self.save['permitted'][gid]) == 0:
                self.save['permitted'].pop(gid)
                count += 1
            else:
                i = 0
                while i < len(self.save['permitted'][gid]):
                    if self.bot.get_channel(self.save['permitted'][gid][i]) is None:
                        self.save['permitted'][gid].pop(i)
                        count += 1
                    else:
                        i += 1
        await asyncio.sleep(1)
        for gid in list(self.save['pinboard'].keys()):
            if gid not in guild_ids:
                self.save['pinboard'].pop(gid)
                count += 1
            else:
                i = 0
                while i < len(self.save['pinboard'][gid]['tracked']):
                    if self.bot.get_channel(self.save['pinboard'][gid]['tracked'][i]) is None:
                        self.save['pinboard'][gid]['tracked'].pop(i)
                        count += 1
                    else:
                        i += 1
                if self.save['pinboard'][gid]['output'] is not None and self.bot.get_channel(self.save['pinboard'][gid]['output']) is None:
                    self.save['pinboard'][gid]['output'] = None
                    count += 1
        await asyncio.sleep(1)
        for gid in list(self.save['vxtwitter'].keys()):
            if gid not in guild_ids:
                self.save['vxtwitter'].pop(gid)
                count += 1
        await asyncio.sleep(1)
        for gid in list(self.save['announcement'].keys()):
            if gid not in guild_ids or self.bot.get_channel(self.save['announcement'][gid][0]) is None:
                self.save['announcement'].pop(gid)
                count += 1
        await asyncio.sleep(1)
        for gid in list(self.save['assignablerole'].keys()):
            if gid not in guild_ids:
                self.save['assignablerole'].pop(gid)
                count += 1
        await asyncio.sleep(1)
        if count > 0:
            self.bot.channel.update_announcement_channels()
            self.pending = True
        await asyncio.sleep(1)
        if 'extra' in self.save:
            c = self.bot.util.JST()
            to_pop = set()
            for k, v in self.save['extra'].items():
                if isinstance(v, dict) and 'expire' in v:
                    if c >= v['expire']:
                        to_pop.add(k)
            if len(to_pop) > 0:
                count += len(to_pop)
                for k in to_pop:
                    self.save['extra'].pop(k)
                self.pending = True
        if count > 0:
            await self.bot.send('debug', embed=self.bot.embed(title="clean()", description="Cleaned up {} elements".format(count), timestamp=self.bot.util.UTC()))