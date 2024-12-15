import disnake
import asyncio
from typing import Union, Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import random
import time
from datetime import datetime, timedelta
from views.roll_tap import Tap

# ----------------------------------------------------------------------------------------------------------------
# Gacha Component
# ----------------------------------------------------------------------------------------------------------------
# Manage the real granblue gacha
# Also provide a simulator for games
# ----------------------------------------------------------------------------------------------------------------

class Gacha():
    ZODIAC_WPN = ['Ramulus', 'Dormius', 'Gallinarius', 'Canisius', 'Porculius', 'Rodentius', 'Bovinius', 'Tigrisius', 'Leporidius', 'Dracosius'] # for the twelve generals detection, gotta update it yearly
    CLASSIC_COUNT = 2 # number of classic banners
    # constants
    NO_INFO = " "
    SUMMON_KIND = "S"

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def init(self) -> None:
        pass

    """get()
    Get the current GBF gacha banner data.
    
    Returns
    --------
    list: Containing:
        - timedelta: Remaining time
        - dict: Gacha data
    """
    async def get(self) -> list:
        c = self.bot.util.JST().replace(microsecond=0) - timedelta(seconds=70) # current time, a bit in the past to ensure it's updated later
        # we check:
        # - if gacha data doesn't exist
        # - if gacha data is outdated
        # - if a gacha collab banner ended
        # - if the update failed
        if ('gacha' not in self.bot.data.save['gbfdata'] or self.bot.data.save['gbfdata']['gacha'] is None or c >= self.bot.data.save['gbfdata']['gacha']['time'] or c >= self.bot.data.save['gbfdata']['gacha'].get('collaboration', c+timedelta(seconds=10))) and not await self.update():
            # if all those passed, we return nothing
            return []
        if self.bot.data.save['gbfdata']['gacha']['time'] is None: # if we lack the gacha banner timer, we also return nothing
            return []
        return [c, self.bot.data.save['gbfdata']['gacha']] # else, return current time used (for timing reasons) and the gacha data

    """process()
    Retrieve and process the gacha rates
    
    Prameters
    --------
    gtype: string, gacha type
    bid: Banner id
    sub_id: draw id (1 = single roll, 2 = ten roll, 3 = scam gacha)
    
    Returns
    --------
    tuple: Contains:
        -ratio, the gacha rates
        -list, the item list
        -rateup, the rate up items
    """
    async def process(self, gtype : str, bid : Union[str, int], sub_id : int) -> tuple:
        try:
            # get the banner draw rate
            data = await self.bot.net.requestGBF("gacha/provision_ratio/{}/{}/{}".format(gtype, bid, sub_id), expect_JSON=True)
            gratio = data['ratio'][0]['ratio']
            
            glist = [{'rate':0, 'list':{}}, {'rate':0, 'list':{}}, {'rate':0, 'list':{}}]
            grateup = {'zodiac':[]}
            # loop over data
            for appear in data['appear']:
                rarity = appear['rarity'] - 2
                if rarity < 0 or rarity > 2: continue # eliminate possible N rarity
                glist[rarity]['rate'] = float(data['ratio'][2 - rarity]['ratio'][:-1])
                for item in appear['item']:
                    if item['kind'] is None: # summon and scam select use None by default
                        if sub_id == 3 and item.get('name', '').startswith('Item '): # check if it's an item
                            kind = self.NO_INFO
                        else:
                            kind = self.SUMMON_KIND
                    else:
                        kind = int(item['kind'])-1 # weapon prof
                    attribute = item.get('attribute', None) # get element
                    if attribute is None:
                        attribute = self.NO_INFO # empty if element is missing
                    # if item rate isn't in the data
                    if item['drop_rate'] not in glist[rarity]['list']:
                        glist[rarity]['list'][item['drop_rate']] = [] # add a list for that rate
                    glist[rarity]['list'][item['drop_rate']].append("{}{}{}".format(attribute, kind, item['name'])) # add the item to that array (Format is Element Character, Type character and Item name. Example: 5STriple Zero (5 is light, S for summon, Triple Zero is the name)

                    if rarity == 2: # if it's a SSR
                        if appear['category_name'] not in grateup: # Add rate list for that type of item (Usually Character Weapons and Summon)
                            grateup[appear['category_name']] = {}
                        if 'character_name' in item and item.get('name', '') in self.ZODIAC_WPN: # check if it's a twelve general
                            grateup['zodiac'].append("{}{}{}".format(attribute, kind, item['character_name'])) # add it to the list of generals present in the banner
                        # Check if on rate up
                        if item.get('incidence', None) is not None:
                            if item['drop_rate'] not in grateup[appear['category_name']]: # If rate isn't in rate list type
                                grateup[appear['category_name']][item['drop_rate']] = [] # Add list
                            if 'character_name' in item and item['character_name'] is not None: # If it's a character
                                grateup[appear['category_name']][item['drop_rate']].append("{}{}{}".format(item['attribute'], kind, item['character_name'])) # Add character to rate up (Format is Element Character, Type character and Item name)
                            else: # Else item name
                                grateup[appear['category_name']][item['drop_rate']].append("{}{}{}".format(attribute, kind, item['name'])) # (Format is Element Character, Type character and Item name)
            # return results
            return gratio, glist, grateup
        except Exception as e:
            self.bot.logger.pushError("[GACHA] Exception 1:", e)
            return None, None, None

    """getScamRate()
    Retrieve and process the scam item rates
    
    Prameters
    --------
    gtype: string, gacha type
    bid: Banner id
    
    Returns
    --------
    dict: item list and rate
    """
    async def getScamRate(self, gtype : str, bid : Union[str, int]) -> dict:
        try:
            # request given scam data
            appear = (await self.bot.net.requestGBF("gacha/provision_ratio/{}/{}/4".format(gtype, bid), expect_JSON=True))['appear']
            items = {}
            for e in appear: # take note of items and their rates
                if e['num'] == '1':
                    items[e['name']] = int(float(e['draw_rate']) * 1000)
                else:
                    items[e['name'] + ' x' + e['num']] = int(float(e['draw_rate']) * 1000)
            # return them
            return items
        except Exception as e:
            self.bot.logger.pushError("[GACHA] Exception 2:", e)
            return None
    
    """fix_time_newyear()
    Adjust banner end time on new year
    Banner timers usually don't have the year, so we use the current year in our datetime. If a banner carries over from one year to another, this fix is needed.
    
    Parameters
    --------
    current: Datetime, current time
    d: Datetime, banner time to adjust
    
    Returns
    --------
    tuple:
        - datetime: Adjusted time
        - bool: True if it has been modified
    """
    def fix_time_newyear(self, current : datetime, d : datetime) -> datetime:
        NY = False
        if current > d: # If the banner time is before our current time
            d = d.replace(year=d.year+1) # we add a year
            NY = True
        return d, NY

    """update()
    Request and update the GBF gacha in the save data
    
    Returns
    --------
    bool: True if success, False if error
    """
    async def update(self) -> bool:
        if not await self.bot.net.gbf_available(): # check if GBF can be accessed
            return False
        try:
            c = self.bot.util.JST() # current time
            # check the gacha page
            data = await self.bot.net.requestGBF("gacha/list", expect_JSON=True)
            if data is None: raise Exception()
            # data container
            gacha_data = {'banners':[]}
            # retrieve data from gacha page request
            index = -1
            scam_ids = []
            for i, g in enumerate(data['legend']['lineup']):
                if g['name'] == "Premium Draw":
                    index = i # normal banner index in the data
                elif g['name'].find("Star Premium") != -1:
                    for subscam in g['campaign_gacha_ids']: # scam(s) ids, if they exist
                        scam_ids.append(subscam['id'])
            
            # set timers
            gacha_data['time'] = datetime.strptime(str(c.year) + '/' + data['legend']['lineup'][index]['end'], '%Y/%m/%d %H:%M').replace(microsecond=0) # banner end timer
            gacha_data['time'], NY = self.fix_time_newyear(c, gacha_data['time']) # apply fix
            # sub banner time (usually for multi element banners, whose sparks carry over)
            gacha_data['timesub'] = datetime.strptime(data['ceiling']['end'], '%Y/%m/%d %H:%M').replace(microsecond=0)
            if (NY is False and gacha_data['timesub'] < gacha_data['time']) or (NY is True and gacha_data['timesub'] > gacha_data['time']): gacha_data['time'] = gacha_data['timesub'] # switch around if the New year fix has been applied
            
            # read crypto key
            random_key = data['legend']['random_key']
            # read header images
            header_images = data['header_images']
            # read logo images
            logo = {'logo_fire':1, 'logo_water':2, 'logo_earth':3, 'logo_wind':4, 'logo_dark':5, 'logo_light':6}.get(data.get('logo_image', ''), data.get('logo_image', '').replace('logo_', ''))
            # get normal banner id (single draw)
            gid = data['legend']['lineup'][index]['id']

            # request main banner details
            gratio, glist, grateup = await self.process('legend', gid, 1)
            if gratio is None:
                raise Exception("Couldn't retrieve main gacha banner")
            gacha_data['banners'].append({'ratio':gratio, 'list':glist, 'rateup':grateup}) # append to data

            # request scam details (if they exist)
            for sid in scam_ids:
                gratio, glist, grateup = await self.process('legend', sid, 3)
                if gratio is not None:
                    if 'scam' not in gacha_data: # add scam data list if not set
                        gacha_data['scam'] = []
                    gacha_data['scam'].append({'ratio':gratio, 'list':glist, 'rateup':grateup, 'items': (await self.getScamRate('legend', sid))}) # append to scam data

            # additional banners
            # it works like the main banner request
            # # classic gacha
            for i in [500021, 501021]: # id has to be set manually (for now)
                data = await self.bot.net.requestGBF("rest/gacha/classic/toppage_data_by_classic_series_id/{}".format(i), expect_JSON=True)
                if data is not None and 'appearance_gacha_id' in data:
                    gratio, glist, grateup = await self.process('classic', data['appearance_gacha_id'], 1)
                    if gratio is not None:
                        gacha_data['banners'].append({'ratio':gratio, 'list':glist, 'rateup':grateup})
            # # collab gacha
            data = await self.bot.net.requestGBF("rest/gacha/collaboration/toppage_data", expect_JSON=True)
            if data is not None and "collaboration" in data and "collaboration_ceiling" in data:
                # store the collaboration end time
                gacha_data['collaboration'] = datetime.strptime(data['collaboration_ceiling']['end'], '%Y/%m/%d %H:%M').replace(microsecond=0)
                gacha_data['collaboration'], NY = self.fix_time_newyear(c, gacha_data['collaboration'])
                gratio, glist, grateup = await self.process('collaboration', data["collaboration"]["lineup"][-1]["id"], 1)
                if gratio is not None:
                    gacha_data['banners'].append({'ratio':gratio, 'list':glist, 'rateup':grateup})

            # add image
            gachas = ['{}/tips/description_gacha.jpg'.format(random_key), '{}/tips/description_gacha_{}.jpg'.format(random_key, logo), '{}/tips/description_{}.jpg'.format(random_key, header_images[0]), 'header/{}.png'.format(header_images[0])]
            for g in gachas: # check which one exists
                data = await self.bot.net.request("https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/gacha/{}".format(g))
                if data is not None:
                    gacha_data['image'] = g # store the  first one to be found and stop here
                    break

            # save the data
            self.bot.data.save['gbfdata']['gacha'] = gacha_data
            self.bot.data.pending = True
            return True
        except Exception as e:
            self.bot.logger.pushError("[GACHA] Update failed, exception:", e)
            self.bot.data.save['gbfdata']['gacha'] = None
            self.bot.data.pending = True # save anyway
            return False


    """summary_subroutine()
    summary() subroutine.
    
    Parameters
    --------
    data: Dict, main gacha data
    index: Integer, banner index
    time: Datetime, banner end time
    timesub: Optional Datetime, sub banner end time
    remaining: Datetime, remaining banner time
    
    Returns
    --------
    list: List of string to use to make the description. In list form to use join() later, for less string instantiation.
    """
    def summary_subroutine(self, data : dict, index : int, time : datetime, timesub : Optional[datetime], remaining : datetime) -> str:
        # banner timer
        description = ["{} Current gacha ends in **{}**".format(self.bot.emote.get('clock'), self.bot.util.delta2str(time - remaining, 2))]
        if timesub is not None and time != timesub:
            description.append("\n{} Spark period ends in **{}**".format(self.bot.emote.get('mark'), self.bot.util.delta2str(timesub - remaining, 2)))

        # calculate ssr rate sum
        sum_ssr = 0
        for i, rarity in enumerate(data['banners'][index]['list']):
            for r in rarity['list']:
                if i == 2: # SSR
                    sum_ssr += float(r) * len(rarity['list'][r]) # add rate multiplied by number of item

        # rate description
        description.append("\n{} **Rate:** Advertised **{}**".format(self.bot.emote.get('SSR'), data['banners'][index]['ratio']))
        if not data['banners'][index]['ratio'].startswith('3'):
            description.append(" **(Premium Gala)**")
        description.append(" ▫️ Sum of rates **{:.3f}%**".format(sum_ssr))
        if index == 0 and 'scam' in data: # Add number of available Scam gachas
            description.append("\n{} **{}** Star Premium Draw(s) available".format(self.bot.emote.get('mark'), len(data['scam'])))
        description.append("\n")
        
        # build rate up list
        for k in data['banners'][index]['rateup']:
            if k == 'zodiac': # It should be first in the order
                if len(data['banners'][index]['rateup']['zodiac']) > 0: # Write list of zodiacs to be available in the banner
                    description.append("{} **Zodiac** ▫️ ".format(self.bot.emote.get('loot')))
                    for i in data['banners'][index]['rateup'][k]:
                        description.append(self.formatGachaItem(i) + " ")
                    description.append("\n")
            else:
                if len(data['banners'][index]['rateup'][k]) > 0:
                    for r in data['banners'][index]['rateup'][k]: # List top rate up for each category (Weapons and Summons)
                        if k.lower().find("weapon") != -1: description.append("{}**{}%** ▫️ ".format(self.bot.emote.get('sword'), r))
                        elif k.lower().find("summon") != -1: description.append("{}**{}%** ▫️ ".format(self.bot.emote.get('summon'), r))
                        for i, item in enumerate(data['banners'][index]['rateup'][k][r]):
                            if i >= 8 and len(data['banners'][index]['rateup'][k][r]) - i > 1:
                                description.append(" and **{} more!**".format(len(data['banners'][index]['rateup'][k][r]) - i))
                                break
                            description.append(self.formatGachaItem(item) + " ")
                        description.append("\n")
        return description


    """summary()
    Make a text summary of the current gacha
    
    Raise
    --------
    Exception
    
    Returns
    --------
    tuple:
        - str: Description
        - str: url of thumbnail
    """
    async def summary(self) -> tuple:
        try:
            content = await self.get()
            if len(content) > 0:
                remaining, data = tuple(content)
                description = self.summary_subroutine(data, 0, data['time'], data['timesub'], remaining) # main banner summary
                if len(data["banners"]) > self.CLASSIC_COUNT and "collaboration" in data and remaining < data["collaboration"]: # check if a collab exists
                    description.append("{} **Collaboration**\n".format(self.bot.emote.get('crystal'))) # add extra line
                    description.extend(self.summary_subroutine(data, self.CLASSIC_COUNT+1, data['collaboration'], None, remaining)) # and its summary
                return "".join(description), "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/gacha/{}".format(data['image']) # return message and the image url
            return None, None
        except Exception as e:
            raise e


    """retrieve()
    Return the current real gacha from GBF, if it exists in the bot memory.
    If not, a dummy/limited one is generated.
    
    Prameters
    --------
    scam: Integer, to retrieve a scam gacha data (None to ignore)
    classic: Integer, to retrieve the classic gacha (None or 0 to ignore scam has priority)
    
    Returns
    --------
    tuple: Containing:
        - The whole rate list
        - The banner rate up
        - The ssr rate, in %
        - Boolean indicating if the gacha is the real one
        - (OPTIONAL): Dict, item list
        - (OPTIONAL): Integer, star premium gacha index
    """
    async def retrieve(self, scam : Optional[bool] = None, banner : int = 0) -> tuple:
        try:
            data = (await self.get())[1] # retrieve the rate
            if scam is None: # not asking for scam
                if 0 <= banner < len(data): # access asked banner
                    gacha_data = data['banners'][banner]
                else: # or first banner if invalid index
                    gacha_data = data['banners'][0]
            else:
                if 'scam' not in data or scam < 0 or scam >= len(data['scam']): # raise error if couldn't get scam
                    raise Exception()
                gacha_data = data['scam'][scam]
            # final check
            if len(gacha_data['list']) == 0:
                raise Exception()
            # gacha_data is now the data to the banner we're interested in
            data = gacha_data['list']
            rateups = []
            # build a list of rate up for this banner
            for k in gacha_data['rateup']:
                if k == "zodiac":
                    continue # ignore zodiac category
                elif len(gacha_data['rateup'][k]) > 0:
                    for r in gacha_data['rateup'][k]:
                        if r not in rateups: rateups.append(r)
            # get SSR rate
            ssrrate = int(gacha_data['ratio'][0])
            complete = True
            if scam is not None: # return scam data on top
                return data, rateups, ssrrate, complete, gacha_data['items'], scam
        except:
            # legacy mode, dummy data
            data = [{"rate": 82.0, "list": {"82": [None]}}, {"rate": 15.0, "list": {"15": [None]}}, {"rate": 3.0, "list": {"3": [None]}}]
            rateups = None
            ssrrate = 3
            complete = False
        return data, rateups, ssrrate, complete

    """isLegfest()
    Check the provided parameter and the real gacha to determine if we will be using a 6 or 3% SSR rate
    
    Parameters
    ----------
    ssrrate: Integer, SSR rate in percent
    selected: Integer, selected value by the user (-1 default, 0 is 3%, anything else is 6%)
    
    Returns
    --------
    bool: True if 6%, False if 3%
    """
    def isLegfest(self, ssrrate : int, selected : int) -> bool:
        match selected:
            case 0:
                return False
            case -1:
                try:
                    return (ssrrate == 6)
                except:
                    return False
            case _:
                return True

    """allRates()
    Return a list of all different possible SSR rates in the current gacha
    Doesn't support scam banners
    
    Parameters
    --------
    index: Integer, banner index (0 default, 1-2 classic, 3 collab...)
    
    Returns
    --------
    tuple:
        float: ssr rate, return None if error
        list: Rate list, return None if error
    """
    def allRates(self, index : int) -> tuple:
        try:
            r = []
            for rate in list(self.bot.data.save['gbfdata']['gacha']['banners'][index]['list'][-1]['list'].keys()): # SSR list
                if float(rate) not in r:
                    r.append(float(rate))
            return float(self.bot.data.save['gbfdata']['gacha']['banners'][index]['ratio'][:-1]), sorted(r, reverse=True)
        except:
            return None, None

    """formatGachaItem()
    Format the item string used by the gacha simulator to add an element emoji
    
    Parameters
    ----------
    raw: string to format
    
    Returns
    --------
    str: self.resulting string
    """
    def formatGachaItem(self, raw : str) -> str:
        if len(raw) < 3:
            return raw
        res = []
        match raw[0]:
            case "1": res.append(str(self.bot.emote.get('fire')))
            case "2": res.append(str(self.bot.emote.get('water')))
            case "3": res.append(str(self.bot.emote.get('earth')))
            case "4": res.append(str(self.bot.emote.get('wind')))
            case "5": res.append(str(self.bot.emote.get('light')))
            case "6": res.append(str(self.bot.emote.get('dark')))
            case _: pass
        match raw[1]:
            case "0": res.append(str(self.bot.emote.get('sword')))
            case "1": res.append(str(self.bot.emote.get('dagger')))
            case "2": res.append(str(self.bot.emote.get('spear')))
            case "3": res.append(str(self.bot.emote.get('axe')))
            case "4": res.append(str(self.bot.emote.get('staff')))
            case "5": res.append(str(self.bot.emote.get('gun')))
            case "6": res.append(str(self.bot.emote.get('melee')))
            case "7": res.append(str(self.bot.emote.get('bow')))
            case "8": res.append(str(self.bot.emote.get('harp')))
            case "9": res.append(str(self.bot.emote.get('katana')))
            case self.SUMMON_KIND: res.append(str(self.bot.emote.get('summon')))
            case _: res.append(str(self.bot.emote.get('question')))
        res.append(raw[2:])
        return "".join(res)

    """simulate()
    Create a GachaSimulator instance
    
    Parameters
    --------
    simtype: string, case sensitive. possible values: single, srssr, memerollA, memerollB, scam, ten, gachapin, mukku, supermukku
    bannerid: string for special gacha (scam...) or integer (0 for normal banner, 1~2 for classic, 3 for collab...)
    color: color to use for the embeds
    scamindex: index of the premium star gacha to use
    
    Returns
    --------
    GachaSimulator
    """
    async def simulate(self, simtype : str, bannerid : Union[int, str], color : int, scamindex : int = 1) -> 'GachaSimulator':
        scamdata = None
        match bannerid:
            case 'scam':
                gachadata = await self.retrieve() # retrieve the data
                scamdata = await self.retrieve(scam=scamindex-1) # and the scam data
                bannerid = 0
            case _:
                if not isinstance(bannerid, int): # invalid string, set to default index
                    bannerid = 0
                gachadata = await self.retrieve(banner=bannerid) # retrieve the data
        # create and return a simulator instance
        return GachaSimulator(self.bot, gachadata, simtype, scamdata, bannerid, color)

class GachaSimulator():
    # Mode constants
    MODE_SINGLE = 0
    MODE_SRSSR = 1
    MODE_MEMEA = 2
    MODE_MEMEB = 3
    MODE_TEN = 10
    MODE_GACHAPIN = 11
    MODE_MUKKU = 12
    MODE_SUPER = 13
    MODE_SCAM = 14
    MODE_ALL = 20
    # SSR rates
    RATE_SUPER = 15
    RATE_MUKKU = 9
    RATE_GALA = 6
    RATE_NORMAL = 3
    RATE_ALL = 100 # guaranted ssr
    # Rarity
    SSR = 2
    SR = 1
    R = 0
    # Assets
    CRYSTALS = [
        "https://mizagbf.github.io/assets/rosetta-remote-resources/0_s.png",
        "https://mizagbf.github.io/assets/rosetta-remote-resources/1_s.png",
        "https://mizagbf.github.io/assets/rosetta-remote-resources/2_s.png",
        "https://mizagbf.github.io/assets/rosetta-remote-resources/3_s.png"
    ]
    ROULETTE = "https://mizagbf.github.io/assets/rosetta-remote-resources/roulette.gif"
    # Others
    RPS = ['rock', 'paper', 'scissor']
    ROULETTE_DELAY = 4

    """constructor
    
    Parameters
    --------
    bot: MizaBOT
    gachadata: output from Gacha.retrieve()
    simtype: value from Gacha.simulate() parameter simtype
    scamdata: Optional, output from Gacha.retrieve(scam=X). None to ignore.
    bannerid: integer, banner index
    color: Embed color
    """
    def __init__(self, bot : 'DiscordBot', gachadata : tuple, simtype : str, scamdata : Optional[tuple], bannerid : int, color : int) -> None:
        self.bot = bot
        self.data, self.rateups, self.ssrrate, self.complete = gachadata # unpack the data
        self.scamdata = scamdata # no need to unpack the scam gacha one (assume it might be None too)
        self.bannerid = bannerid
        self.color = color
        self.mode = None
        self.changeMode(simtype)
        self.result = {} # output of generate()
        self.thumbnail = None # thumbnail of self.best
        self.best = [-1, "", False] # best roll
        self.exception = None # contains the last exception

    """changeMode()
    update self.mode with a new value
    
    Parameters
    --------
    simtype: value from Gacha.simulate parameter() simtype
    """
    def changeMode(self, simtype : str) -> None:
        self.mode = {'single':self.MODE_SINGLE, 'srssr':self.MODE_SRSSR, 'memerollA':self.MODE_MEMEA, 'memerollB':self.MODE_MEMEB, 'ten':self.MODE_TEN, 'gachapin':self.MODE_GACHAPIN, 'mukku':self.MODE_MUKKU, 'supermukku':self.MODE_SUPER, 'scam':self.MODE_SCAM, 'all':self.MODE_ALL}[simtype]

    """check_rate()
    Check and calculate modifiers needed to modify real rates to the ones we desire.
    
    Parameters
    --------
    ssrrate: Integer, wanted SSR rate, in percent
    
    Returns
    --------
    tuple:
        - mods: List of modifiers (R, SR, SSR)
        - proba: List of Item rates (R, SR, SSR)
    """
    def check_rate(self, ssrrate : int) -> tuple:
        # calcul R,SR,SSR & total
        proba = [] # store the % of R, SR and SSR
        mods = [1, 1, 1] # modifiers vs advertised rates, 1 by default
        for r in self.data:
            proba.append(0)
            for rate in r['list']:
                proba[-1] += float(rate) * len(r['list'][rate]) # sum of rates x items
        if ssrrate != self.data[2]['rate']: # if wanted ssr rate different from advertised one
            mods[self.SSR] = ssrrate / proba[self.SSR] # calculate mod
            tmp = proba[self.SSR] * mods[self.SSR] # get new proba
            diff = proba[self.SSR] - tmp # get diff between old and new
            if ssrrate == self.RATE_ALL:
                proba[self.R] = 0
                proba[self.SR] = 0
                mods[self.R] = 0
                mods[self.SR] = 0
            else:
                proba[self.R] = max(0, proba[self.R] + diff) # lower R proba
                try:
                    mods[self.R] = (proba[self.R] + diff) / proba[self.R] # calculate lowered R rate modifer
                except:
                    mods[self.R] = 1
            proba[self.SSR] = tmp # store SSR proba
        return mods, proba

    """get_generation_rate_and_modifiers()
    Get SSR rates and modifiers
    
    Parameters
    --------
    legfest: Integer, value to pass to isLegfest() if needed
    
    Returns
    --------
    tuple: Contains the SSR rate, in %, and the output of check_rate() (mods and probas)
    """
    def get_generation_rate_and_modifiers(self, legfest : int) -> tuple:
        match self.mode:
            case self.MODE_ALL: ssrrate = self.RATE_ALL
            case self.MODE_SUPER: ssrrate = self.RATE_SUPER
            case self.MODE_MUKKU: ssrrate = self.RATE_MUKKU
            case _: ssrrate = self.RATE_GALA if self.bot.gacha.isLegfest(self.ssrrate, legfest) else self.RATE_NORMAL
        return ssrrate, *self.check_rate(ssrrate)

    """retrieve_single_roll_item()
    Use the generated roll to retrieve an item.
    Called by generate_single_roll.
    If no real gacha data exists in memory, we create a dummy item.
    
    Parameters
    --------
    result: Dict, temporary output container
    rarity: Integer, item rarity
    dice: Float, rolled value
    
    Returns
    --------
    bool: Stop boolean, True if we must stop generating items, False if not
    """
    def retrieve_single_roll_item(self, result: dict, rarity : int, dice : float) -> bool:
        if self.complete: # if we have a real gacha in memory
            roll = None # will contain our rolled item
            # find which item we rolled
            for rate in self.data[rarity]['list']: # go over each rate category
                floatrate = float(rate)
                for item in self.data[rarity]['list'][rate]: # and each item
                    rateupitem = False 
                    if rarity == self.SSR and rate in self.rateups: # if this is a rate up SSR
                        rateupitem = True # raise the flag
                    # if our dice value is under the item rate
                    if dice <= floatrate: # this is the one
                        roll = [rarity, item, rateupitem]
                        break
                    # else substract the item rate
                    dice -= floatrate
                if roll is not None: # we stop the loop if we got a roll
                    break
            # fallback if the roll is still empty, we put the last item encountered
            if roll is None:
                roll = [rarity, item, rateupitem]
            # add item to list
            if roll[2]: # bold if rate up
                result['list'].append([roll[0], "**" + self.bot.gacha.formatGachaItem(roll[1]) + "**"])
            else:
                result['list'].append([roll[0], self.bot.gacha.formatGachaItem(roll[1])])
            # increase rarity counter by 1
            result['detail'][rarity] += 1
            # update best item obtained so far
            if rate in self.rateups and rarity + 1 > self.best[0]: # rate up SSR
                self.best = roll.copy()
                self.best[0] += 1 # set rate up ssr to SSR+1 to ensure they aren't superseeded by normal SSR
            elif rarity > self.best[0]:
                self.best = roll.copy()
            # final check
            if rarity == self.SSR:
                # the loop must stop if we fulfilled the memeroll types
                if self.mode == self.MODE_MEMEA:
                    return True # memeroll mode A
                elif self.mode == self.MODE_MEMEB and result['list'][-1][1].startswith("**"):
                    return True # memeroll mode B
        else: # using dummy gacha
            result['list'].append([rarity, '']) # '' because no item names
            result['detail'][rarity] += 1
            if rarity == self.SSR:
                if self.mode == self.MODE_MEMEA or self.mode == self.MODE_MEMEB:
                    return True  # memeroll mode A and B
        return False

    """generate_single_roll()
    Generate a single roll.
    Used by generate()
    
    Parameters
    --------
    result: Dict, temporary output container
    index: Integer, current roll in a 10 rolls series (Goes from 0 to 9)
    tenrollsr: Flag indicating we got a SR in the current ten roll
    mods: List, of 3 elements (rate modifiers for each rarity)
    proba: List, of 3 elements (% rates of each rarity)
    
    Returns
    --------
    tuple: Containes updated tenrollsr boolean and stop boolean
    """
    def generate_single_roll(self, result: dict, index : int, tenrollsr : bool, mods : list, proba : list) -> tuple:
        # our "dice" roll
        dice = random.randint(1, int(sum(proba) * 1000)) / 1000
        # Check if we must force a SR
        if self.mode == self.MODE_SRSSR or (self.mode >= self.MODE_TEN and index == 9 and not tenrollsr): # if SRSSR mode OR (we're doing a ten draw type of roll and we're on the 10th roll without SR/SSR)
            sr_mode = True
        else:
            sr_mode = False
        # determine what rarity we got
        if dice <= proba[self.SSR]: # SSR CASE
            rarity = self.SSR
            tenrollsr = True # raise got sr flag
            dice /= mods[self.SSR] # apply modifier
        elif (not sr_mode and dice <= proba[1] + proba[2]) or sr_mode: # SR CASE
            rarity = self.SR
            dice -= proba[self.SSR]
            while dice >= proba[self.SR]: # in case we forced a SR and we're above the rate
                dice -= proba[self.SR]
            tenrollsr = True # raise got sr flag
            dice /= mods[self.SR] # apply modifier
        else: # R CASE
            rarity = self.R
            dice -= proba[self.SSR] + proba[self.SR]
            dice /= mods[self.R] # apply modifier
        return tenrollsr, self.retrieve_single_roll_item(result, rarity, dice)

    """generate()
    Generate X amount of rolls and update self.result
    
    Parameters
    --------
    count: Integer, number of rolls wanted
    legfest: Integer, -1 for auto mod, 0 to force 3%, 1 to force 6%
    """
    async def generate(self, count : int, legfest : int = -1) -> None:
        try:
            ssrrate, mods, proba = self.get_generation_rate_and_modifiers(legfest) # get ssr rate
            self.result = {} # reset the output
            result = {'list':[], 'detail':[0, 0, 0], 'rate':ssrrate} # temp output
            tenrollsr = False # flag for guaranted SR in ten rolls 
            if self.mode == self.MODE_MEMEB and len(self.rateups) == 0:
                self.mode = self.MODE_MEMEA # revert memerollB to A if no rate ups
            # rolling loop
            for i in range(0, count):
                modulo_i = i % 10 # get index in current ten roll
                tenrollsr, stop = self.generate_single_roll(result, modulo_i, tenrollsr, mods, proba)
                if stop:
                    break
                # end of a series of 10 rolls, check for gachapin/mukku/etc...
                if modulo_i == 9:
                    tenrollsr = False # unset SR flag if we did 10 rolls
                    if (self.mode == self.MODE_GACHAPIN or self.mode == self.MODE_MUKKU) and result['detail'][2] >= 1:
                        break # gachapin and mukku mode, we end here
                    elif self.mode == self.MODE_SUPER and result['detail'][2] >= 5:
                        break # super mukku mode, we end here
            self.result = result # store result
        except Exception as e:
            self.exception = e

    """updateThumbnail()
    Update self.thumbnail based on self.best content
    To use after generate()
    """
    async def updateThumbnail(self) -> None:
        try:
            if self.best[0] != -1 and self.best[1] != "":
                search = self.best[1][2:]
                # extract element and proficiency for wiki search
                element = ['fire', 'water', 'earth', 'wind', 'light', 'dark'][int(self.best[1][0])-1]
                prof = (['sabre', 'dagger', 'spear', 'axe', 'staff', 'gun', 'melee', 'bow', 'harp', 'katana'][int(self.best[1][1])] if self.best[1][1] != 'S' else None)
                # retrieve the element id from the wiki
                rid = await self.bot.util.search_wiki_for_id(search, "summons" if self.best[1][1] == 'S' else "weapons", from_gacha=True, element=element, proficiency=prof)
                if rid is None: # not found
                    self.thumbnail = None
                elif rid.startswith('1'): # weapon
                    self.thumbnail = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/weapon/m/{}.jpg".format(rid)
                elif rid.startswith('2'): # summon
                    self.thumbnail = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/summon/m/{}.jpg".format(rid)
                else:
                    self.thumbnail = None
        except:
            pass

    """scamRoll()
    Roll the Star Premium SSR and item

    Returns
    --------
    tuple:
        - choice: string, SSR name
        - loot: string, item name
    """
    def scamRoll(self) -> tuple:
        data, rateups, ssrrate, complete, items, index = self.scamdata # no error check, do it before
        if items is None: items = self.bot.gacha.scam
        scam_rate = sum(list(items.values()))
        roll = random.randint(1, scam_rate) # roll a dice for the item
        loot = None
        n = 0
        for k, v in items.items(): # iterate over items with our dice value
            n += v
            if roll <= n:
                loot = k
                break
        # pick the random ssr
        self.best = [99, random.choice(data[2]['list'][list(data[2]['list'].keys())[0]]), True] # force ssr in self.best
        return self.best[1], loot

    """bannerIDtoFooter()
    Appends extra text to an embed footer depending on the banner type
    
    Parameters
    --------
    footer: List of string, future embed footer beforer join
    
    Returns
    --------
    list: footer reference
    """
    def bannerIDtoFooter(self, footer : list) -> str:
        if self.bannerid > 0:
            if self.bannerid <= self.bot.gacha.CLASSIC_COUNT:
                footer.append(" ▫️ Classic {}".format(self.bannerid))
            else:
                footer.append(" ▫️ Collaboration")
        return footer

    """render_errors()
    Check for errors and display them in the interaction message.
    Called by render().
    
    Parameters
    --------
    inter: render() interaction
    
    Returns
    --------
    bool: True if an error occured, False otherwise
    """
    async def render_errors(self, inter: disnake.Interaction) -> bool:
        if 'list' not in self.result or self.exception is not None: # an error occured
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An error occured", color=self.color))
            self.bot.logger.pushError("[GACHA] 'simulator output' error:", self.exception)
            return True
        elif self.mode == self.MODE_SCAM and (self.scamdata is None or not self.scamdata[3]): # scam error occured
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="No Star Premium Gachas available at selected index", color=self.color))
            return True
        return False

    """generate_render_footer()
    Return the string to be used as an Embed footer in render()
    
    Returns
    --------
    str: The footer
    """
    def generate_render_footer(self) -> str:
        footer = ["{}% SSR rate".format(self.result['rate'])] # banner rate
        match self.mode:
            case self.MODE_MEMEB:
                footer.append(" ▫️ until rate up")
            case self.MODE_SCAM:
                footer.append(" ▫️ Selected Scam #{}".format(self.scamdata[5]+1))
            case _:
                pass
        return "".join(self.bannerIDtoFooter(footer))

    """generate_render_crystal()
    Return the image url to be used as the crystal image, for the Tap prompt.
    Called by render().
    
    Returns
    --------
    str: An url
    """
    def generate_render_crystal(self) -> str:
        # select crystal image
        if (100 * self.result['detail'][self.SSR] / len(self.result['list'])) >= self.result['rate']: # SSR
            return random.choice([self.CRYSTALS[2], self.CRYSTALS[3]])
        elif (100 * self.result['detail'][self.SR] / len(self.result['list'])) >= self.result['rate']: # SR
            return self.CRYSTALS[2]
        else:
            return random.choice([self.CRYSTALS[0], self.CRYSTALS[1]]) # R

    """render_single_roll()
    Display the result of a single draw in the given interaction.
    Called by render().
    
    Parameters
    --------
    inter: render() interaction
    titles: Tuple of Strings. Second element is used in the embed author name. First is unused.
    footer: String, embed footer
    """
    async def render_single_roll(self, inter: disnake.Interaction, titles : tuple, footer : str) -> None:
        item = self.result['list'][0] # get the first (and likely only) item
        await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="{}{}".format(self.bot.emote.get({0:'R', 1:'SR', 2:'SSR'}.get(item[0])), item[1]), color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)

    """render_ten_roll()
    Display the result of a ten draw in the given interaction.
    Called by render().
    
    Parameters
    --------
    inter: render() interaction
    titles: Tuple of Strings. Second element is used in the embed author name. First is unused.
    footer: String, embed footer
    scamroll: Optional tuple, result of scamRoll()
    """
    async def render_ten_roll(self, inter: disnake.Interaction, titles : tuple, footer : str, scamroll : Optional[tuple]) -> None:
        scam_position = -1
        for i in range(0, 11): # 1 by 1 + the final displaying all ten, so 11
            msgs = []
            for j in range(0, i): # display revealed items
                if j >= 10: break
                # write
                msgs.append("{}{} ".format(self.bot.emote.get({0:'R', 1:'SR', 2:'SSR'}.get(self.result['list'][j][0])), self.result['list'][j][1]))
                if j & 1 == 1:
                    msgs.append("\n")
            for j in range(i, 10): # display hidden items
                msgs.append('{}'.format(self.bot.emote.get('crystal{}'.format(self.result['list'][j][0]))))
                if j & 1 == 1:
                    msgs.append("\n")
            if self.scamdata is not None: # add unreleaved scam icons if data exists
                scam_position = len(msgs) - 1
                msgs.append(str(self.bot.emote.get('SSR')))
                msgs.append(str(self.bot.emote.get('crystal2')))
                msgs.append("\n")
                msgs.append(str(self.bot.emote.get('red')))
            await asyncio.sleep(0.7)
            await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=''.join(msgs), color=self.color, footer=footer, thumbnail=(self.thumbnail if (i == 10 and self.scamdata is None) else None)), view=None)
        # display scam result (if it exists)
        if self.scamdata is not None:
            msgs = msgs[:scam_position]
            msgs.append("\n")
            msgs.append(str(self.bot.emote.get('SSR')))
            msgs.append("**")
            msgs.append(self.bot.gacha.formatGachaItem(scamroll[0]))
            msgs.append("**\n")
            msgs.append(str(self.bot.emote.get('red')))
            msgs.append("**")
            msgs.append(scamroll[1])
            msgs.append("**")
            await asyncio.sleep(1)
            await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=''.join(msgs), color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)

    """render_meme_roll()
    Display the result of a "memerolling" in the given interaction.
    Called by render().
    Note: "Memerolling" refers to the fact of using single tickets until obtaining a SSR.
    
    Parameters
    --------
    inter: render() interaction
    titles: Tuple of Strings. First (during rolling) and Second element (after the end) are used in the embed author name.
    footer: String, embed footer
    """
    async def render_meme_roll(self, inter: disnake.Interaction, titles : tuple, footer : str) -> None:
        counter = [0, 0, 0]
        msgs = []
        # speed selection
        if self.mode == self.MODE_MEMEB:
            item_count = 5 # by 5 items
        else:
            item_count = 3 # by 3items
        # iterate over rolled items
        for i, v in enumerate(self.result['list']):
            if i > 0 and i % item_count == 0:
                # display once we reached item_count
                await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[0].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="{} {} ▫️ {} {} ▫️ {} {}\n".format(counter[2], self.bot.emote.get('SSR'), counter[1], self.bot.emote.get('SR'), counter[0], self.bot.emote.get('R')) + ''.join(msgs), color=self.color, footer=footer), view=None)
                await asyncio.sleep(1)
                msgs = []
            # add result
            msgs.append("{} {}\n".format(self.bot.emote.get({0:'R', 1:'SR', 2:'SSR'}.get(v[0])), v[1]))
            counter[v[0]] += 1
        # update title
        title = (titles[1].format(inter.author.display_name, len(self.result['list'])) if (len(self.result['list']) < 300) else "{} sparked".format(inter.author.display_name))
        await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description="{} {} ▫️ {} {} ▫️ {} {}\n".format(counter[2], self.bot.emote.get('SSR'), counter[1], self.bot.emote.get('SR'), counter[0], self.bot.emote.get('R')) + ''.join(msgs), color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)

    """render_spark_roll()
    Display the result of a spark in the given interaction.
    Called by render().
    
    Parameters
    --------
    inter: render() interaction
    titles: Tuple of Strings. Second element is used in the embed author name. First is unused.
    footer: String, embed footer
    """
    async def render_spark_roll(self, inter: disnake.Interaction, titles : tuple, footer : str) -> None:
        count = len(self.result['list'])
        rate = (100*self.result['detail'][2]/count)
        msgs = []
        best = [-1, ""]
        rolls = self.getSSRList()
        for r in rolls: # check for best rolls
            if best[0] < 3 and '**' in r:
                best = [3, r.replace('**', '')]
            elif best[0] < 2:
                best = [2, r]
        if len(rolls) > 0 and self.complete:
            msgs.append("{} ".format(self.bot.emote.get('SSR')))
            for item in rolls: # for each ssr
                msgs.append(item)
                if rolls[item] > 1: # add occurence
                    msgs.append(" x{}".format(rolls[item]))
                await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name, count), 'icon_url':inter.author.display_avatar}, description=''.join(msgs), color=self.color, footer=footer), view=None)
                await asyncio.sleep(0.75)
                msgs.append(" ")
        # add extra messages for other modes
        if self.mode == self.MODE_GACHAPIN: amsg = "Gachapin stopped after **{}** rolls\n".format(len(self.result['list']))
        elif self.mode == self.MODE_MUKKU: amsg = "Mukku stopped after **{}** rolls\n".format(len(self.result['list']))
        elif self.mode == self.MODE_SUPER: amsg = "Super Mukku stopped after **{}** rolls\n".format(len(self.result['list']))
        else: amsg = ""
        await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name, count), 'icon_url':inter.author.display_avatar}, description="{}{:} {:} ▫️ {:} {:} ▫️ {:} {:}\n{:}\n**{:.2f}%** SSR rate".format(amsg, self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), ''.join(msgs), rate), color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)

    """render()
    Output the result in a message, via a given disnake Interaction.
    
    Parameters
    --------
    inter: Interaction to use. Must have been deferred beforehand
    display_mode: Integer. 0=single roll, 1=ten roll, 2=memeroll, 3=ssr list
    titles: Tuple of 2 strings. First and Second embed titles to display
    """
    async def render(self, inter: disnake.Interaction, display_mode : int, titles : tuple = ("{}", "{}")) -> None:
        # check errors in result
        if await self.render_errors(inter):
            return
        # retrieve footer
        footer = self.generate_render_footer()
        # get scam roll
        scamroll = None
        if self.scamdata is not None:
            scamroll = self.scamRoll()
        # update thumbnail
        await self.updateThumbnail()
        # start and tap button
        view = Tap(self.bot, owner_id=inter.author.id)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[0].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, image=self.generate_render_crystal(), color=self.color, footer=footer), view=view)
        await view.wait()
        # Display roll result
        match display_mode:
            case 0:
                await self.render_single_roll(inter, titles, footer)
            case 1:
                await self.render_ten_roll(inter, titles, footer, scamroll)
            case 2:
                await self.render_meme_roll(inter, titles, footer)
            case 3:
                await self.render_spark_roll(inter, titles, footer)

    """getSSRList()
    Extract the SSR from a full gacha list generated by gachaRoll()
    
    Returns
    --------
    dict: SSR List. The keys are the SSR name and the values are how many your rolled
    """
    def getSSRList(self) -> dict:
        rolls = {}
        for r in self.result['list']:
            if r[0] == 2: # extra SSRs
                rolls[r[1]] = rolls.get(r[1], 0) + 1
        return rolls

    """roulette()
    Simulate a roulette and output the result
    
    Parameters
    --------
    inter: Interaction to use. Must have been deferred beforehand
    legfest: Integer, -1 for auto mod, 0 to force 3%, 1 to force 6%
    realist: Bool, True to force 20 and 30 rolls
    """
    async def roulette(self, inter : disnake.Interaction, legfest : int = -1, realist : bool = False) -> None:
        prev_best = None
        current_time = self.bot.util.JST()
        # initialize roulette
        roulette = Roulette(self.bot, self, current_time, legfest, realist)
        # and spin the wheel!
        roulette.spin_the_wheel()
        # Default message
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} is spinning the Roulette".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=roulette.get_message(), color=self.color, footer=roulette.get_footer(), thumbnail=self.ROULETTE))
        
        # Main loop
        while roulette.running:
            # error occured, abort
            if self.exception is not None:
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An error occured", color=self.color))
                self.bot.logger.pushError("[GACHA] 'simulator roulette' error:", self.exception)
                return
            start_time = time.time() # current time
            await asyncio.sleep(0) # to not risk blocking
            # update the roulette state
            await roulette.update()
            # update thumbnail if it changed
            if prev_best is None or str(self.best) != prev_best:
                prev_best = str(self.best)
                await self.updateThumbnail()
            # wait next roulette update, for the remainer of self.ROULETTE_DELAY
            diff = self.ROULETTE_DELAY - (time.time() - start_time)
            if diff > 0:
                await asyncio.sleep(diff)
            # send message
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} spun the Roulette".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=roulette.get_message() + ("" if not roulette.running else "**...**"), color=self.color, footer=roulette.get_footer(), thumbnail=self.thumbnail))

class Roulette():
    # Wheel zones
    MAX_ROLL = 0
    GACHAPIN = 1
    BIRTHDAY = 2
    ROLL_10 = 10
    ROLL_20 = 20
    ROLL_30 = 30
    NORMAL_ROLLS = [MAX_ROLL, ROLL_10, ROLL_20, ROLL_30]
    # States
    STATE_JANKEN = 0
    STATE_NORMAL = 1
    STATE_GACHAPIN = 2
    STATE_MUKKU = 3
    STATE_SUPER_MUKKU = 4
    STATE_BIRTHDAY_ZONE = 5
    
    """__init__()
    Constructor.
    
    Parameters
    --------
    bot: DiscordBot, Rosetta instance
    sim: GachaSimulator instance which created this Roulette object
    current_time: datetime, Time at which the roulette was invoked
    legfest: Integer, Legfest rate setting
    realist: Boolean, realist roulette setting
    """
    def __init__(self, bot : 'DiscordBot', sim : GachaSimulator, current_time : datetime, legfest : int, realist : bool) -> None:
        self.bot = bot
        self.sim = sim
        # get settings
        settings = self.bot.data.save['gbfdata'].get('roulette', {})
        # copy them here
        # Fixed roll period
        self.fixed_start = current_time.replace(year=2000+settings.get('year', 24), month=settings.get('month', 1), day=settings.get('day', 1), hour=5, minute=0, second=0, microsecond=0) # beginning of fixed rolls
        self.fixed_end = self.fixed_start  + timedelta(days=1, seconds=0) # end of fixed rolls (one day later)
        # move start 36000s or 10h early
        self.fixed_start -= timedelta(seconds=36000)
        # Fixed period forced 3 percent
        self.forced_3_percent = settings.get('forced3%', True)
        # Fixed period roll count
        self.forced_rolls = settings.get('forcedroll', 100)
        # Fixed period forced Super Mukku
        self.forced_super_mukku = settings.get('forcedsuper', True)
        # Enable 200 rolls as the max
        self.enable_200_rolls = settings.get('enable200', False)
        # Enable the Rock Paper Scissor
        self.enable_janken = settings.get('enablejanken', False)
        # Maximum number of Rock Paper Scissor in a row
        self.max_janken = settings.get('enablejanken', False)
        # Enable double Mukku
        self.double_mukku = settings.get('doublemukku', False)
        # Use realist mode (if allowed)
        self.realist = realist and settings.get('realist', False)
        # Add Birthday Zone on the wheel
        self.birthday_zone = settings.get('birthday', False)
        
        # variables and flags
        self.running = True
        self.state = self.STATE_NORMAL
        self.current_time = current_time
        self.msgs = [] # message strings container
        self.footers = [] # footer strings container
        self.dice = 0
        self.rolls = 0
        self.legfest = -1
        self.super_mukku = False
        self.janken_threshold = 0

    """get_message()
    Return an usable embed description
    
    Returns
    --------
    str: The message
    """
    def get_message(self) -> str:
        return "".join(self.msgs)

    """get_footer()
    Return an usable embed footer
    
    Returns
    --------
    str: The footer
    """
    def get_footer(self) -> str:
        return "".join(self.footers)

    """SSRList2StrList()
    Convert a SSR list to a list of string to be used by roulette()
    
    Parameters
    --------
    ssrs: List of gacha items
    
    Returns
    --------
    list: List of string (to be combined with join())
    """
    def SSRList2StrList(self, ssrs : list) -> list:
        if len(ssrs) > 0:
            tmp = [str(self.bot.emote.get('SSR')), " "]
            for item in ssrs: # make a list of SSR only
                tmp.append(item)
                if ssrs[item] > 1:
                    tmp.append(" x{}".format(ssrs[item]))
                tmp.append(" ")
            return tmp
        else:
            return []

    """generated_fixed_rolls()
    Set the settings for the fixed roll period.
    """
    def generated_fixed_rolls(self) -> None:
        self.msgs = ["{} {} :confetti_ball: :tada: Guaranteed **{} 0 0** R O L L S :tada: :confetti_ball: {} {}\n".format(self.bot.emote.get('crystal'), self.bot.emote.get('crystal'), self.forced_rolls//100, self.bot.emote.get('crystal'), self.bot.emote.get('crystal'))]
        self.stats = self.STATE_NORMAL
        self.rolls = self.forced_rolls
        self.enable_janken = False
        if self.forced_super_mukku:
            self.super_mukku = True
        if self.legfest == 1 and self.forced_3_percent:
            self.legfest = -1

    """spin_the_wheel()
    Determine the region of the wheel the user landed on.
    Note: If the current_time is set in the fixed roll period, generated_fixed_rolls() will be invoked.
    """
    def spin_the_wheel(self) -> None:
        # Check fixed period
        if self.fixed_start <= self.current_time < self.fixed_end:
            self.generated_fixed_rolls()
            return
        # Add possible wheel results depending on settings
        wheel = []
        wheel.append((self.GACHAPIN, 800)) # gachapin 8%
        if self.birthday_zone:
            wheel.append((self.BIRTHDAY, 500)) # birthday 5%
        if self.realist:
            wheel.append((self.ROLL_30, 2000)) # 30 rolls 20%
            wheel.append((self.ROLL_20, None))
        else:
            wheel.append((self.MAX_ROLL, 200)) # hundred 2%
            wheel.append((self.ROLL_30, 2000)) # 30 rolls 20%
            wheel.append((self.ROLL_20, 3500)) # 20 rolls 35%
            wheel.append((self.ROLL_10, None))
        # Calculate minimum value to get janken
        for zone in wheel:
            if zone[0] in self.NORMAL_ROLLS:
                break # stop at "normal" rolls
            self.janken_threshold += zone[1]
        # Now spin the wheel
        self.dice = random.randint(1, 10000) # roulette roll
        threshold = 0
        # Look for what result we got in variable d
        for zone in wheel:
            if zone[1] is not None and self.dice > threshold + zone[1]: # over threshold
                threshold += zone[1] # remove and iterate
                continue
            match zone[0]:
                case self.MAX_ROLL:
                    if self.enable_200_rolls: # forced 200 rolls
                        self.msgs = ["{} {} :confetti_ball: :tada: **2 0 0 R O L L S** :tada: :confetti_ball: {} {}\n".format(self.bot.emote.get('crystal'), self.bot.emote.get('crystal'), self.bot.emote.get('crystal'), self.bot.emote.get('crystal'))]
                        self.rolls = 200
                    else: # forced 100 rolls
                        self.msgs = [":confetti_ball: :tada: **100** rolls!! :tada: :confetti_ball:\n"]
                        self.rolls = 100
                case self.GACHAPIN:
                    self.msgs = ["**Gachapin Frenzy** :four_leaf_clover:\n"]
                    self.rolls = -1
                    self.state = self.STATE_GACHAPIN
                case self.BIRTHDAY: # Birthday zone
                    self.msgs = [":birthday: You got the **Birthday Zone** :birthday:\n"]
                    self.rolls = -1
                    self.state = self.STATE_BIRTHDAY_ZONE
                case self.ROLL_30:
                    self.msgs = ["**30** rolls! :clap:\n"]
                    self.rolls = 30
                case self.ROLL_20:
                    self.msgs = ["**20** rolls :open_mouth:\n"]
                    self.rolls = 20
                case self.ROLL_10:
                    self.msgs = ["**10** rolls :pensive:\n"]
                    self.rolls = 10
            break
        # to disable janken if needed
        if not self.enable_janken and self.state == self.STATE_JANKEN:
            self.state = self.STATE_NORMAL

    """janken_event()
    Simulate the Rock Paper Scissor event (if enabled).
    Called by update().
    """
    async def janken_event(self) -> None:
        if self.enable_janken and self.dice >= self.janken_threshold and random.randint(0, 2) > 0: # only if enabled and we rolled above the threshold and we got lucky (33% chance)
            # simulate basic rock paper scisor
            while True:
                a = random.randint(0, 2)
                b = random.randint(0, 2)
                if a != b:
                    break
            # Add result
            self.msgs.append("You got **{}**, Gachapin got **{}**".format(self.RPS[a], self.RPS[b]))
            # Check the win condition
            if (a == 1 and b == 0) or (a == 2 and b == 1) or (a == 0 and b == 2):
                self.msgs.append(" :thumbsup:\nYou **won** rock paper scissor, your rolls are **doubled** :confetti_ball:\n")
                self.rolls = self.rolls * 2 # double roll
                roll_cap = (200 if self.enable_200_rolls else 100) # maximum roulette rolls
                if self.rolls > roll_cap: # cap roll
                    self.rolls = roll_cap
                    self.max_janken = 0 # cancel other jankens
                else:
                    self.max_janken -= 1
                if self.max_janken == 0:
                    self.state = self.STATE_NORMAL # go to normal roll
            else:
                self.msgs.append(" :pensive:\n")
                self.state = self.STATE_NORMAL # go to normal roll
        else:
            self.state = self.STATE_NORMAL # go to normal roll

    """normal_event()
    Simulate standard rolls.
    Called by update().
    """
    async def normal_event(self) -> None:
        # Generate rolls
        await self.sim.generate(self.rolls, self.legfest)
        # Number of SSR
        count = len(self.sim.result['list'])
        # Result SSR rate
        rate = (100*self.sim.result['detail'][2]/count)
        # Get ssr list
        tmp = self.SSRList2StrList(self.sim.getSSRList())
        # Update the footer
        self.footers = self.sim.bannerIDtoFooter(["{}% SSR rate".format(self.sim.result['rate'])])
        # Rarity counter line
        for rarity in range(self.sim.SSR, self.sim.R-1, -1):
            self.msgs.append(str(self.sim.result['detail'][rarity]))
            self.msgs.append(" ")
            self.msgs.append(str(self.bot.emote.get({self.sim.SSR:'SSR', self.sim.SR:'SR', self.sim.R:'R'}.get(rarity, rarity))))
            if rarity > self.sim.R:
                self.msgs.append(" ▫️ ")
        self.msgs.append("\n")
        # SSR List
        if len(tmp) > 0:
            self.msgs.extend(tmp)
            self.msgs.append("\n")
        # SSR Rate line
        self.msgs.append("**{:.2f}%** SSR rate\n\n".format(rate))
        # Next step
        if self.super_mukku:
            self.state = self.STATE_SUPER_MUKKU # go to Super Mukku
        else:
            self.running = False # Over

    """gachapin_mukku_event()
    Simulate Gachapin/Mukku/Super Mukku rolls.
    Called by update().
    
    
    Parameters
    --------
    sim_mode: String, The simulator mode to use. It must corresponds to the state. The behavior is undefined if there is a mismatch (example, self.state == self.STATE_GACHAPIN but sim_mode = "mukku")
    """
    async def gachapin_mukku_event(self, sim_mode : str) -> None:
        # Generate rolls
        self.sim.changeMode(sim_mode)
        await self.sim.generate(300, self.legfest)
        # Number of SSR
        count = len(self.sim.result['list'])
        # Result SSR rate
        rate = (100*self.sim.result['detail'][2]/count)
        # Get ssr list
        tmp = self.SSRList2StrList(self.sim.getSSRList())
        # Update the footer (if gachapin)
        if self.state == self.STATE_GACHAPIN:
            self.footers = self.sim.bannerIDtoFooter(["{}% SSR rate".format(self.sim.result['rate'])])
        # Roll line
        match self.state:
            case self.STATE_GACHAPIN:
                self.msgs.append("Gachapin ▫️ **")
            case self.STATE_MUKKU:
                self.msgs.append(":confetti_ball: Mukku ▫️ **")
            case self.STATE_SUPER_MUKKU:
                self.msgs.append(":confetti_ball: **Super Mukku** ▫️ **")
        self.msgs.append(str(count))
        self.msgs.append("** rolls\n")
        # Rarity counter line
        for rarity in range(self.sim.SSR, self.sim.R-1, -1):
            self.msgs.append(str(self.sim.result['detail'][rarity]))
            self.msgs.append(" ")
            self.msgs.append(str(self.bot.emote.get({self.sim.SSR:'SSR', self.sim.SR:'SR', self.sim.R:'R'}.get(rarity, rarity))))
            if rarity > self.sim.R:
                self.msgs.append(" ▫️ ")
        self.msgs.append("\n")
        # SSR List
        if len(tmp) > 0:
            self.msgs.extend(tmp)
            self.msgs.append("\n")
        # SSR Rate line
        self.msgs.append("**{:.2f}%** SSR rate\n\n".format(rate))
        # Check next step
        match self.state:
            case self.STATE_GACHAPIN:
                # depending on how many rolls we got, and some rng, we decide on the next step
                if count == 10 and random.randint(1, 100) <= 99:
                    self.state = self.STATE_MUKKU
                elif count == 20 and random.randint(1, 100) <= 60:
                    self.state = self.STATE_MUKKU
                elif count == 30 and random.randint(1, 100) <= 30:
                    self.state = self.STATE_MUKKU
                elif random.randint(1, 100) <= 3:
                    self.state = self.STATE_MUKKU
                else:
                    self.running = False # Over
            case self.STATE_MUKKU:
                if self.double_mukku: # Double mukku enabled
                    if random.randint(1, 100) < 25: # roll a dice
                        self.double_mukku = False # disable double mukku and wait to go to mukku again
                        # Note: stay on this state
                    else:
                        self.running = False # Over
                else:
                    self.running = False # Over
            case self.STATE_SUPER_MUKKU:
                self.running = False # Over

    """birthday_event()
    Simulate the Birthday Zone of the March 2024 Anniversary Roulette
    Called by update().
    """
    async def birthday_event(self) -> None:
        d = random.randint(1, 10000) # roll another dice
        self.running = False # we'll stop here
        # Decide on event
        if d <= 2000: self.rolls = 100
        elif d <= 3400: self.rolls = 50
        elif d <= 4800: self.rolls = 60
        elif d <= 6200: self.rolls = 70
        elif d <= 7600: self.rolls = 80
        elif d <= 9000: # gachapin
            self.msgs.append(":confetti_ball: You got the **Gachapin**!!\n")
            await self.gachapin_mukku_event('gachapin') # call directly to keep running flag to False
            return
        else: # 10 ssr mode
            self.sim.changeMode('all')
            self.rolls = 10
            self.msgs.append(":confetti_ball: :confetti_ball: **Guaranted SSR** ▫️ **")
        if self.rolls > 10:
            self.msgs.append(":confetti_ball: **")
        self.msgs.append(str(self.rolls))
        self.msgs.append("** rolls\n")
        await self.normal_event() # call directly to keep running flag to False

    """update()
    Process the Roulette state and trigger the corresponding event.
    """
    async def update(self) -> None:
        if self.running:
            match self.state:
                case self.STATE_JANKEN:
                    await self.janken_event()
                case self.STATE_NORMAL: # normal rolls
                    await self.normal_event()
                case self.STATE_GACHAPIN: # gachapin
                    await self.gachapin_mukku_event('gachapin')
                case self.STATE_MUKKU:
                    await self.gachapin_mukku_event('mukku')
                case self.STATE_SUPER_MUKKU:
                    await self.gachapin_mukku_event('supermukku')
                case self.STATE_BIRTHDAY_ZONE:
                    await self.birthday_event()
            # tweak footer
            if self.realist:
                self.footers.append(" ▫️ Realist")