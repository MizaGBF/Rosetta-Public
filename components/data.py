import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import json
from io import BytesIO
from datetime import datetime, timedelta
import html

# ----------------------------------------------------------------------------------------------------------------
# Data Component
# ----------------------------------------------------------------------------------------------------------------
# This component manages the save data file (save.json) and handle the loading of config.json (once at startup).
# It also provides functions to maintain and clean up the save data.
# Works in tandem with the Drive component.
# ----------------------------------------------------------------------------------------------------------------

class Data():
    SAVEVERSION = 19
    BASE_SAVE = {
        'version':SAVEVERSION,
        'banned_guilds': [],
        'gbfaccount': {},
        'gbfversion': None,
        'gbfupdate': False,
        'gbfdata': {},
        'maintenance': {"state" : False, "time" : None, "duration" : 0},
        'stream': {'time':None, 'content':[]},
        'schedule': {},
        'spark': {},
        'gw': {'state':False},
        'dread': {'state':False},
        'reminders': {},
        'cleanup': {},
        'extra': {},
        'gbfids': {},
        'assignablerole': {},
        'matchtracker': None,
        'pinboard': {},
        'ban': {},
        'announcement': {},
        'log': []
    }
    BASE_CONFIG = [
        'tokens',
        'ids',
        'games'
    ]
    
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot
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
            with open('config.json', mode="r", encoding="utf-8") as f:
                data = json.load(f)
                self.config = data
                # basic validity check
                for check in self.BASE_CONFIG:
                    if check not in self.config:
                        raise Exception("'{}' section not found in 'config.json'".format(check))
            if self.debug: # we load AND merge config_test.json to config.json in memory
                with open('config_test.json', mode="r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.config = self.config | data # merge
                    # basic validity check
                    for check in self.BASE_CONFIG:
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
            with open('save.json', mode="r", encoding="utf-8") as f:
                data = json.load(f, object_pairs_hook=self.bot.util.json_deserial_dict) # add deserializer here
                if any(data): # check if it contains something
                    ver = data.get('version', None)
                else: # fresh save file
                    ver = self.SAVEVERSION
                # Version check and retrocompatibility
                if ver is None:
                    raise Exception("This save file isn't compatible")
                elif ver < self.SAVEVERSION: # Old save
                    if ver == 0: # We do conversions for every past versions up to our
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
                            data['announcement'][gid][1] = (data['announcement'][gid][1] & 1 == 1)
                            data['announcement'][gid][2] = (data['announcement'][gid][2] & 1 == 1)
                    if ver <= 12:
                        for gid in data['announcement']:
                            data['announcement'][gid] = [data['announcement'][gid][0], data['announcement'][gid][3]]
                    if ver <= 13:
                        data['schedule'] = {}
                    if ver <= 14:
                        try:
                            data['gbfdata']['gacha']['classic'] = [data['gbfdata']['gacha']['classic']]
                        except:
                            pass
                    if ver <= 15:
                        for i in range(len(data['gbfaccounts'])):
                            data['gbfaccounts'][i].pop(4)
                    if ver <= 16:
                        if 'teamraid_cookie' in data['gbfdata']:
                            data['gbfdata'].pop('teamraid_cookie')
                    if ver <= 17:
                        if 'granblue_en' in data['gbfdata']:
                            data['gbfdata'].pop("granblue_en")
                    if ver <= 18:
                        if 'gbfaccounts' in data and len(data['gbfaccounts']) > 0:
                            data['gbfaccount'] = {'id':data['gbfaccounts'][0][0], 'ck':data['gbfaccounts'][0][1], 'ua':data['gbfaccounts'][0][2], 'state':data['gbfaccounts'][0][3], 'last':data['gbfaccounts'][0][4]}
                            if len(data['gbfaccounts']) > 1:
                                self.bot.logger.push("[DATA] Only the first GBF account was kept during the save data conversion to **v19**.")
                            data.pop("gbfaccounts")
                        if 'valiant' in data:
                            data['dread'] = data['valiant']
                            data.pop("valiant")
                        if 'permitted' in data:
                            data['cleanup'] = {k: [True, v] for k, v in data['permitted'].items()}
                            data.pop("permitted")
                        if 'announcement' in data: # size fix
                            for k, v in data['announcement'].items():
                                if len(v) > 2:
                                    data['announcement'][k] = v[:2]
                    # Update the version
                    data['version'] = self.SAVEVERSION
                elif ver > self.SAVEVERSION: # Version is more recent??
                    raise Exception("Save file version higher than the expected version")
                # Do an extra conversions in checkData
                self.save = self.checkData(data)
                self.pending = False
                return True
        except Exception as e:
            self.bot.logger.pushError("[DATA] In `loadData`:", e)
            return False

    """saveData()
    Write save.json.
    
    Returns
    --------
    bool: True on success, False on failure
    """
    def saveData(self) -> bool: # saving (lock isn't used, use it outside!)
        if self.debug: # don't save in debug mode
            return True
        try:
            with open('save.json', mode='w', encoding="utf-8") as outfile: # save to json locally first
                json.dump(self.save, outfile, separators=(',', ':'), default=self.bot.util.json_serial)
        except Exception as e:
            self.bot.logger.pushError("[DATA] An error occured with the local save data:", e)
            return False # return to not upload a corrupt file
        # Now save remotely
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
        for k in list(data.keys()): # remove useless keys not present in BASE_SAVE
            if k not in self.BASE_SAVE:
                data.pop(k)
        for k in self.BASE_SAVE: # add missing keys
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
        if self.autosaving or self.debug: # no save in debug mode or if we're already autosaving
            return
        self.autosaving = True # raise flag
        result = False
        for i in range(0, 3): # try a few times to save the data
            if self.saveData():
                self.pending = False # unraise pending flag
                result = True # success
                break
            await asyncio.sleep(0)
        if not result: # no success
            await self.bot.send('debug', embed=self.bot.embed(title="Failed Save", timestamp=self.bot.util.UTC()))
            discordDump = True
        if discordDump: # if this is raised, we send a copy of the save file to discord, in the debug channel
            try:
                with BytesIO(json.dumps(self.save, separators=(',', ':'), default=self.bot.util.json_serial).encode('utf-8')) as infile:
                    with self.bot.file.discord(infile, filename="save.json") as df:
                        await self.bot.send('debug', file=df)
            except Exception as e:
                self.bot.logger.pushError("[DATA] 'autosave' Dump Error:", e)
        self.autosaving = False

    """maintenance()
    Bot Task managing the autocleanup of the save data and other routines
    """
    async def maintenance(self) -> None:
        # init
        try:
            await asyncio.sleep(10) # wait for boot to be over to start
            # the task will run every day at 2 am, so we calculate the next time it will happen
            target_time = self.bot.util.JST().replace(hour=2, minute=0, second=0, microsecond=0)
            ct = self.bot.util.JST()
            if ct >= target_time: target_time += timedelta(days=1)
            # used for the gw cog crew cache
            first_loop = True
        except asyncio.CancelledError:
            self.bot.logger.push("[TASK] 'data:maintenance' Task Cancelled")
            return
        except Exception as e:
            self.bot.logger.pushError("[TASK] 'data:maintenance' Task Error:", e)
        
        # loop
        while True:
            try:
                # compare current time to targeted time
                ct = self.bot.util.JST()
                if ct < target_time: # lesser, we sleep
                    await asyncio.sleep((target_time - ct).seconds + 1)
                    continue
                target_time += timedelta(days=1) # move target_time to next day
                self.bot.logger.push("[TASK] 'data:maintenance': Daily cleanup started", send_to_discord=False)
                
                # empty GW crew cache
                if not first_loop:
                    try:
                        self.bot.get_cog('GuildWar').clearCrewCache()
                    except Exception as xe:
                        self.bot.logger.pushError("[TASK] 'data:maintenance (Crew Cache)' Task Error:", xe)
                first_loop = False
                
                # update user agent (only on first day of month)
                if ct.day == 1:
                    await self.bot.net.update_user_agent()
                # update avatar on first day of some month
                if ct.day == 1:
                    match ct.month:
                        case 2: await self.bot.changeAvatar('flb.gif')
                        case 4: await self.bot.changeAvatar('bunny.gif')
                        case 6: await self.bot.changeAvatar('summer.gif')
                        case 9: await self.bot.changeAvatar('school.gif')
                        case 10: await self.bot.changeAvatar('halloween.gif')
                        case 11: await self.bot.changeAvatar('school.gif')
                        case 12: await self.bot.changeAvatar('xmas.gif')
                # set next month reminders
                remindcog = self.bot.get_cog('Reminder')
                if ct.day == 1:
                    try:
                        target = ct.replace(hour=5, minute=0, second=0, microsecond=0)
                        if target.month == 12:
                            target = (target + timedelta(days=31)).replace(day=1)
                        else:
                            target = target.replace(month=target.month+1)
                        remindcog.addBotReminder(target, "**A new month started!**\nDon't forget to check out the various shops (Casino, FP, pendant, login, Prisms...).")
                    except Exception as se:
                         self.bot.logger.pushError("[TASK] 'data:maintenance' Task Error (Monthly reminder):", se)
                try: # GW
                    if self.bot.get_cog('GuildWar').isGWRunning():
                        target = self.bot.data.save['gw']['dates']["End"] - timedelta(seconds=25200)
                        remindcog.addBotReminder(target, "**The Final Rally is ending soon!**\nDon't forget to claim your loot and use your tokens.")
                        target = target + timedelta(days=5)
                        remindcog.addBotReminder(target, "You have little time left to use your GW Tokens!")
                except Exception as se:
                     self.bot.logger.pushError("[TASK] 'data:maintenance' Task Error (GW reminders):", se)
                try: # DB
                    if self.bot.get_cog('DreadBarrage').isDBRunning():
                        target = self.bot.data.save['dread']['dates']["End"] - timedelta(seconds=25200)
                        remindcog.addBotReminder(target, "**Dread Barrage is ending soon!**\nDon't forget to claim your loot and use your tokens.")
                        target = target + timedelta(days=5)
                        remindcog.addBotReminder(target, "You have little time left to use your DB Tokens!")
                except Exception as se:
                     self.bot.logger.pushError("[TASK] 'data:maintenance' Task Error (DB reminders):", se)
                # update schedule
                await self.update_schedule()
                # various clean up
                await self.clean_stream() # clean stream data
                await self.clean_spark() # clean up spark data
                await self.bot.channel.clean_data() # clean auto cleanup and announcement settings
                if ct.day == 3: # only clean on the third day of each month
                    await self.clean_profile() # clean up profile data
                await self.clean_general() # clean up everything else
                
                self.bot.logger.push("[TASK] 'data:maintenance': Daily cleanup ended", send_to_discord=False)
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'data:maintenance' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'data:maintenance' Task Error:", e)

    """update_schedule()
    Coroutine to request the wiki to update the schedule
    """
    async def update_schedule(self) -> None:
        try:
            # request the event cargo table of the wiki
            data = await self.bot.net.requestWiki("index.php", params={"title":"Special:CargoExport", "tables":"event_history", "fields":"enname,time_start,time_end,time_known,utc_start,utc_end", "where":"time_start > CURRENT_TIMESTAMP OR time_end > CURRENT_TIMESTAMP", "format":"json", "order by":"time_start"})
            if data is not None:
                new_events = {}
                modified = False
                c = self.bot.util.UTC()
                # go over  events
                for ev in data:
                    if 'utc start' in ev and 'enname' in ev: # check the ones with start dates and names
                        event_times = [ev['utc start']]
                        if 'utc end' in ev: # if it has an end date
                            if c < datetime.utcfromtimestamp(ev['utc end']): # and it hasn't ended
                                event_times.append(ev['utc end']) # add it
                            else:
                                continue # event over
                        else:
                            if c >= datetime.utcfromtimestamp(ev['utc']) + timedelta(days=1): # if we have passed it by one day
                                continue # event over
                        new_events[html.unescape(ev['enname'])] = event_times
                # NOTE: Wiki timestamps are in UTC
                if len(new_events) > 0:
                    # add manual entry starting with specific keywords
                    for ev in self.save['schedule']:
                        evl = ev.lower()
                        if evl.startswith("update") or evl.startswith("maintenance") or evl.startswith("granblue fes") or evl.startswith("summer stream") or evl.startswith("christmas stream") or evl.startswith("anniversary stream"):
                            new_events[ev] = self.save['schedule'][ev]
                    # verify for changes
                    akeys = list(new_events.keys())
                    akeys.sort()
                    bkeys = list(self.save['schedule'].keys())
                    bkeys.sort()
                    if akeys != bkeys:
                        # different event list
                        self.save['schedule'] = new_events
                        modified = True
                    else:
                        # check for date
                        for k, v in new_events.items():
                            if v != self.save['schedule'][k]:
                                # different
                                self.save['schedule'] = new_events
                                modified = True
                                break
                # remove events which ended
                keys = list(self.save['schedule'].keys())
                for k in keys:
                    if (len(self.save['schedule'][k]) == 2 and c > datetime.utcfromtimestamp(self.save['schedule'][k][1])) or (len(self.save['schedule'][k]) == 1 and c > datetime.utcfromtimestamp(self.save['schedule'][k][0]) + timedelta(days=1)):
                        self.save['schedule'].pop(k, None)
                        modified = True
                if modified:
                    self.bot.logger.push("[DATA] update_schedule:\nSchedule updated with success")
                    self.pending = True
        except Exception as e:
            self.bot.logger.pushError("[DATA] update_schedule Error:", e)

    """clean_stream()
    Coroutine to clear stream data (if set)
    """
    async def clean_stream(self) -> None:
        await asyncio.sleep(0)
        # delete if stream exists and it's 4 days old or more
        if self.save['stream'] is not None and self.save['stream'].get('time', None) is not None and self.bot.util.UTC() - self.save['stream']['time'] >= timedelta(days=4):
            self.save['stream'] = None
            self.pending = True
            self.bot.logger.push("[DATA] clean_stream:\nCleaned the Stream data")

    """clean_spark()
    Coroutine to clear user spark data from the save data
    """
    async def clean_spark(self) -> None:
        await asyncio.sleep(0)
        count = 0
        c = self.bot.util.UTC()
        keys = list(self.save['spark'].keys())
        # go over entries
        for rid in keys:
            d = c - self.save['spark'][rid][4]
            if d.days >= 30: # older than 30 days
                del self.save['spark'][rid] # we remove
                self.pending = True
                count += 1
        if count > 0:
            self.bot.logger.push("[DATA] clean_spark:\nCleaned {} unused spark saves".format(count))

    """clean_profile()
    Coroutine to clean user gbf profiles from the save data
    """
    async def clean_profile(self) -> None:
        await asyncio.sleep(0)
        count = 0
        keys = list(self.save['gbfids'].keys())
        # go over registered profiles
        for uid in keys:
            found = False
            for g in self.bot.guilds: # check if the user is in any guild the bot is present in
                 if await g.get_or_fetch_member(int(uid)) is not None:
                    found = True
                    break
            if not found: # if the user hasn't been found
                count += 1
                self.save['gbfids'].pop(uid) # remove
                self.pending = True
        if count > 0:
            self.bot.logger.push("[DATA] clean_profile:\nCleaned {} unused profiles".format(count))

    """clean_general()
    Coroutine to clean the save data
    """
    async def clean_general(self) -> None:
        guild_ids = set([str(g.id) for g in self.bot.guilds])
        count = 0
        await asyncio.sleep(1)
        # Pinbaord cleaning
        for gid in list(self.save['pinboard'].keys()):
            if gid not in guild_ids: # the bot left the guild
                self.save['pinboard'].pop(gid)
                count += 1
            else:
                i = 0
                while i < len(self.save['pinboard'][gid]['tracked']): # remove deleted channels from data
                    if self.bot.get_channel(self.save['pinboard'][gid]['tracked'][i]) is None:
                        self.save['pinboard'][gid]['tracked'].pop(i)
                        count += 1
                    else:
                        i += 1
                if self.save['pinboard'][gid]['output'] is not None and self.bot.get_channel(self.save['pinboard'][gid]['output']) is None: # remove data if empty
                    self.save['pinboard'][gid]['output'] = None
                    count += 1
        await asyncio.sleep(1)
        # Self Assignable Roles
        for gid in list(self.save['assignablerole'].keys()): # the bot left the guild
            if gid not in guild_ids:
                self.save['assignablerole'].pop(gid)
                count += 1
        await asyncio.sleep(1)
        if 'extra' in self.save: # clean extra data (usually used for development, debug or temp events)
            c = self.bot.util.JST()
            to_pop = set()
            for k, v in self.save['extra'].items(): # check if it got an expire value and check if the date passed
                if isinstance(v, dict) and 'expire' in v:
                    if c >= v['expire']:
                        to_pop.add(k)
            if len(to_pop) > 0:
                count += len(to_pop)
                for k in to_pop:
                    self.save['extra'].pop(k)
                self.pending = True
        if count > 0:
            self.pending = True
            self.bot.logger.push("[DATA] clean_general:\nCleaned up {} elements".format(count))