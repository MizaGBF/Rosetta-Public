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
    ZODIAC_WPN = ['Ramulus', 'Dormius', 'Gallinarius', 'Canisius', 'Porculius', 'Rodentius', 'Bovinius', 'Tigrisius', 'Leporidius', 'Dracosius']

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
        c = self.bot.util.JST().replace(microsecond=0) - timedelta(seconds=80)
        if ('gacha' not in self.bot.data.save['gbfdata'] or self.bot.data.save['gbfdata']['gacha'] is None or c >= self.bot.data.save['gbfdata']['gacha']['time']) and not await self.update():
            return []
        if self.bot.data.save['gbfdata']['gacha']['time'] is None:
            return []
        return [c, self.bot.data.save['gbfdata']['gacha']]

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
            # draw rate
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
                    if item['kind'] is None: # default for summon and scam select
                        if sub_id == 3 and item.get('name', '').startswith('Item '):
                            kind = " "
                        else:
                            kind = "S"
                    else:
                        kind = int(item['kind'])-1
                    attribute = item.get('attribute', None)
                    if attribute is None: attribute = " "
                    if item['drop_rate'] not in glist[rarity]['list']: glist[rarity]['list'][item['drop_rate']] = []
                    glist[rarity]['list'][item['drop_rate']].append("{}{}{}".format(attribute, kind, item['name']))

                    if rarity == 2: # ssr
                        if appear['category_name'] not in grateup: grateup[appear['category_name']] = {}
                        if 'character_name' in item and item.get('name', '') in self.ZODIAC_WPN:
                            grateup['zodiac'].append("{}{}{}".format(attribute, kind, item['character_name']))
                        if item.get('incidence', None) is not None:
                            if item['drop_rate'] not in grateup[appear['category_name']]: grateup[appear['category_name']][item['drop_rate']] = []
                            if 'character_name' in item and item['character_name'] is not None: grateup[appear['category_name']][item['drop_rate']].append("{}{}{}".format(item['attribute'], kind, item['character_name']))
                            else: grateup[appear['category_name']][item['drop_rate']].append("{}{}{}".format(attribute, kind, item['name']))
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
            appear = (await self.bot.net.requestGBF("gacha/provision_ratio/{}/{}/4".format(gtype, bid), expect_JSON=True))['appear']
            items = {}
            for e in appear:
                if e['num'] == '1': items[e['name']] = int(float(e['draw_rate']) * 1000)
                else:  items[e['name'] + ' x' + e['num']] = int(float(e['draw_rate']) * 1000)
            return items
        except Exception as e:
            self.bot.logger.pushError("[GACHA] Exception 2:", e)
            return None
    

    """update()
    Request and update the GBF gacha in the save data
    
    Returns
    --------
    bool: True if success, False if error
    """
    async def update(self) -> bool:
        if not await self.bot.net.gbf_available():
            return False
        try:
            c = self.bot.util.JST()
            #gacha page
            data = await self.bot.net.requestGBF("gacha/list", expect_JSON=True)
            if data is None: raise Exception()
            # will contain the data
            gacha_data = {}
            index = -1
            scam_ids = []
            for i, g in enumerate(data['legend']['lineup']):
                if g['name'] == "Premium Draw": index = i
                elif g['name'].find("Star Premium") != -1:
                    for subscam in g['campaign_gacha_ids']:
                        scam_ids.append(subscam['id'])
            
            gacha_data['time'] = datetime.strptime(str(c.year) + '/' + data['legend']['lineup'][index]['end'], '%Y/%m/%d %H:%M').replace(microsecond=0)
            NY = False
            if c > gacha_data['time']:
                gacha_data['time'] = gacha_data['time'].replace(year=gacha_data['time'].year+1) # new year fix
                NY = True
            gacha_data['timesub'] = datetime.strptime(data['ceiling']['end'], '%Y/%m/%d %H:%M').replace(microsecond=0)
            if (NY is False and gacha_data['timesub'] < gacha_data['time']) or (NY is True and gacha_data['timesub'] > gacha_data['time']): gacha_data['time'] = gacha_data['timesub'] # switched
            random_key = data['legend']['random_key']
            header_images = data['header_images']
            logo = {'logo_fire':1, 'logo_water':2, 'logo_earth':3, 'logo_wind':4, 'logo_dark':5, 'logo_light':6}.get(data.get('logo_image', ''), data.get('logo_image', '').replace('logo_', ''))
            gid = data['legend']['lineup'][index]['id']

            # draw rate
            gacha_data['ratio'], gacha_data['list'], gacha_data['rateup'] = await self.process('legend', gid, 1)
            if gacha_data['ratio'] is None:
                raise Exception()

            # scam gachas
            for sid in scam_ids:
                gratio, glist, grateup = await self.process('legend', sid, 3)
                if gratio is not None:
                    if 'scam' not in gacha_data:
                        gacha_data['scam'] = []
                    gacha_data['scam'].append({'ratio':gratio, 'list':glist, 'rateup':grateup, 'items': (await self.getScamRate('legend', sid))})

            # classic gacha
            gacha_data['classic'] = []
            for i in [500021, 501021]:
                data = await self.bot.net.requestGBF("rest/gacha/classic/toppage_data_by_classic_series_id/{}".format(i), expect_JSON=True)
                if data is not None and 'appearance_gacha_id' in data:
                    gratio, glist, grateup = await self.process('classic', data['appearance_gacha_id'], 1)
                    if gratio is not None:
                        gacha_data['classic'].append({'ratio':gratio, 'list':glist, 'rateup':grateup})

            # add image
            gachas = ['{}/tips/description_gacha.jpg'.format(random_key), '{}/tips/description_gacha_{}.jpg'.format(random_key, logo), '{}/tips/description_{}.jpg'.format(random_key, header_images[0]), 'header/{}.png'.format(header_images[0])]
            for g in gachas:
                data = await self.bot.net.request("https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/gacha/{}".format(g))
                if data is not None:
                    gacha_data['image'] = g
                    break

            # save
            # clean old version
            for key in ['rateup', 'gachatime', 'gachatimesub', 'gachabanner', 'gachacontent', 'gacharateups']:
                self.bot.data.save['gbfdata'].pop(key, None)
            self.bot.data.save['gbfdata']['gacha'] = gacha_data
            self.bot.data.pending = True
            return True
        except Exception as e:
            self.bot.logger.pushError("[GACHA] Update failed, exception:", e)
            self.bot.data.save['gbfdata']['gacha'] = None
            self.bot.data.pending = True # save anyway
            return False

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
                description = "{} Current gacha ends in **{}**".format(self.bot.emote.get('clock'), self.bot.util.delta2str(content[1]['time'] - content[0], 2))
                if content[1]['time'] != content[1]['timesub']:
                    description += "\n{} Spark period ends in **{}**".format(self.bot.emote.get('mark'), self.bot.util.delta2str(content[1]['timesub'] - content[0], 2))

                # calculate real ssr rate
                sum_ssr = 0
                # sum_total = 0 # NOTE: ignoring it for now
                for i, rarity in enumerate(content[1]['list']):
                    for r in rarity['list']:
                        # sum_total += float(r) * len(rarity['list'][r]) # NOTE: ignoring it for now
                        if i == 2: sum_ssr += float(r) * len(rarity['list'][r])

                # rate description
                description += "\n{} **Rate:** Advertised **{}**".format(self.bot.emote.get('SSR'), content[1]['ratio'])
                if not content[1]['ratio'].startswith('3'):
                    description += " **(Premium Gala)**"
                description += " ▫️ Sum of rates **{:.3f}%**".format(sum_ssr)
                if 'scam' in content[1]: description += "\n{} **{}** Star Premium Draw(s) available".format(self.bot.emote.get('mark'), len(content[1]['scam']))
                description += "\n"
                
                # build rate up list
                for k in content[1]['rateup']:
                    if k == 'zodiac':
                        if len(content[1]['rateup']['zodiac']) > 0:
                            description += "{} **Zodiac** ▫️ ".format(self.bot.emote.get('loot'))
                            for i in content[1]['rateup'][k]:
                                description += self.formatGachaItem(i) + " "
                            description += "\n"
                    else:
                        if len(content[1]['rateup'][k]) > 0:
                            for r in content[1]['rateup'][k]:
                                if k.lower().find("weapon") != -1: description += "{}**{}%** ▫️ ".format(self.bot.emote.get('sword'), r)
                                elif k.lower().find("summon") != -1: description += "{}**{}%** ▫️ ".format(self.bot.emote.get('summon'), r)
                                for i, item in enumerate(content[1]['rateup'][k][r]):
                                    if i >= 8 and len(content[1]['rateup'][k][r]) - i > 1:
                                        description += " and **{} more!**".format(len(content[1]['rateup'][k][r]) - i)
                                        break
                                    description += self.formatGachaItem(item) + " "
                                description += "\n"
                return description, "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/gacha/{}".format(content[1]['image'])
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
    async def retrieve(self, scam : Optional[bool] = None, classic : Optional[int] = None) -> tuple:
        try:
            data = (await self.get())[1]
            if scam is None:
                if classic is not None and classic > 0:
                    if 'classic' not in data or classic > len(data['classic']):
                        raise Exception()
                    gacha_data = data['classic'][classic-1]
                else:
                    gacha_data = data
            else:
                if 'scam' not in data or scam < 0 or scam >= len(data['scam']):
                    raise Exception()
                gacha_data = data['scam'][scam]
            if len(gacha_data['list']) == 0: raise Exception()
            data = gacha_data['list']
            rateups = []
            # build a list of rate up
            for k in gacha_data['rateup']:
                if k == "zodiac": continue
                if len(gacha_data['rateup'][k]) > 0:
                    for r in gacha_data['rateup'][k]:
                        if r not in rateups: rateups.append(r)
            ssrrate = int(gacha_data['ratio'][0])
            complete = True
            if scam is not None:
                return data, rateups, ssrrate, complete, gacha_data['items'], scam
        except:
            # legacy mode
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
    
    Returns
    --------
    tuple:
        float: ssr rate, return None if error
        list: Rate list, return None if error
    """
    def allRates(self) -> tuple:
        try:
            r = []
            for rate in list(self.bot.data.save['gbfdata']['gacha']['list'][2]['list'].keys()):
                if float(rate) not in r:
                    r.append(float(rate))
            return float(self.bot.data.save['gbfdata']['gacha']['ratio'][:-1]), sorted(r, reverse=True)
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
        if len(raw) < 3: return raw
        res = ""
        match raw[0]:
            case "1": res += str(self.bot.emote.get('fire'))
            case "2": res += str(self.bot.emote.get('water'))
            case "3": res += str(self.bot.emote.get('earth'))
            case "4": res += str(self.bot.emote.get('wind'))
            case "5": res += str(self.bot.emote.get('light'))
            case "6": res += str(self.bot.emote.get('dark'))
            case _: pass
        match raw[1]:
            case "0": res += str(self.bot.emote.get('sword'))
            case "1": res += str(self.bot.emote.get('dagger'))
            case "2": res += str(self.bot.emote.get('spear'))
            case "3": res += str(self.bot.emote.get('axe'))
            case "4": res += str(self.bot.emote.get('staff'))
            case "5": res += str(self.bot.emote.get('gun'))
            case "6": res += str(self.bot.emote.get('melee'))
            case "7": res += str(self.bot.emote.get('bow'))
            case "8": res += str(self.bot.emote.get('harp'))
            case "9": res += str(self.bot.emote.get('katana'))
            case "S": res += str(self.bot.emote.get('summon'))
            case _: res += str(self.bot.emote.get('question'))
        return res + raw[2:]

    """simulate()
    Create a GachaSimulator instance
    
    Parameters
    --------
    simtype: string, case sensitive. possible values: single, srssr, memerollA, memerollB, scam, ten, gachapin, mukku, supermukku
    gachatype: string for special gacha (scam...) or integer (0 for normal banner, 1~2 for classic)
    color: color to use for the embeds
    scamindex: index of the premium star gacha to use
    
    Returns
    --------
    GachaSimulator
    """
    async def simulate(self, simtype : str, gachatype : Union[int, str], color : int, scamindex : int = 1) -> 'GachaSimulator':
        scamdata = None
        isclassic = 0
        match gachatype: # retrieve the data (no need to copy)
            case 'scam':
                gachadata = await self.retrieve()
                scamdata = await self.retrieve(scam=scamindex-1)
            case _:
                if not isinstance(gachatype, int): gachatype = 0
                gachadata = await self.retrieve(classic=gachatype)
                isclassic = gachatype
        gsim = GachaSimulator(self.bot, gachadata, simtype, scamdata, isclassic, color) # create a simulator instance
        return gsim

class GachaSimulator():
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
    RATE_SUPER = 15
    RATE_MUKKU = 9
    RATE_GALA = 6
    RATE_NORMAL = 3
    RATE_ALL = 100
    CRYSTALS = [
        "https://mizagbf.github.io/assets/rosetta-remote-resources/0_s.png",
        "https://mizagbf.github.io/assets/rosetta-remote-resources/1_s.png",
        "https://mizagbf.github.io/assets/rosetta-remote-resources/2_s.png",
        "https://mizagbf.github.io/assets/rosetta-remote-resources/3_s.png"
    ]
    ROULETTE = "https://mizagbf.github.io/assets/rosetta-remote-resources/roulette.gif"
    ROULETTE_DELAY = 4

    """constructor
    
    Parameters
    --------
    bot: MizaBOT
    gachadata: output from Gacha.retrieve()
    simtype: value from Gacha.simulate() parameter simtype
    scamdata: Optional, output from Gacha.retrieve(scam=X). None to ignore.
    isclassic: Boolean, indicate if classic gacha is used
    color: Embed color
    """
    def __init__(self, bot : 'DiscordBot', gachadata : tuple, simtype : str, scamdata : Optional[tuple], isclassic : int, color : int) -> None:
        self.bot = bot
        self.data, self.rateups, self.ssrrate, self.complete = gachadata # unpack the data
        self.scamdata = scamdata # no need to unpack the scam gacha one (assume it might be None too)
        self.isclassic = isclassic
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
    check and calculate modifiers to get the exact rates we want
    
    Parameters
    --------
    ssrrate: Integer, wanted SSR rate in percent
    
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
            mods[2] = ssrrate / proba[2] # calculate mod
            tmp = proba[2] * mods[2] # get new proba
            diff = proba[2] - tmp # get diff between old and new
            if ssrrate == self.RATE_ALL:
                proba[0] = 0
                proba[1] = 0
                mods[0] = 0
                mods[1] = 0
            else:
                proba[0] = max(0, proba[0] + diff) # lower R proba
                try: mods[0] = (proba[0] + diff) / proba[0] # calculate lowered R rate modifer
                except: mods[0] = 1
            proba[2] = tmp # store SSR proba
        return mods, proba

    """generate()
    generate X amount of rolls and update self.result
    
    Parameters
    --------
    count: Integer, number of rolls wanted
    legfest: Integer, -1 for auto mod, 0 to force 3%, 1 to force 6%
    """
    async def generate(self, count : int, legfest : int = -1) -> None:
        try:
            # prep work
            legfest = self.bot.gacha.isLegfest(self.ssrrate, legfest)
            match self.mode:
                case self.MODE_ALL: ssrrate = self.RATE_ALL
                case self.MODE_SUPER: ssrrate = self.RATE_SUPER
                case self.MODE_MUKKU: ssrrate = self.RATE_MUKKU
                case _: ssrrate = self.RATE_GALA if legfest else self.RATE_NORMAL
            self.result = {} # empty output, used for error check
            result = {'list':[], 'detail':[0, 0, 0], 'rate':ssrrate}
            await asyncio.sleep(0)
            mods, proba = self.check_rate(ssrrate)
            tenrollsr = False # flag for guaranted SR in ten rolls 
            if self.mode == self.MODE_MEMEB and len(self.rateups) == 0:
                self.mode = self.MODE_MEMEA # revert memerollB to A if no rate ups
            # rolling loop
            for i in range(0, count):
                await asyncio.sleep(0)
                d = random.randint(1, int(sum(proba) * 1000)) / 1000 # our roll
                if self.mode == self.MODE_SRSSR or (self.mode >= self.MODE_TEN and (i % 10 == 9) and not tenrollsr): sr_mode = True # force sr in srssr self.mode OR when 10th roll of ten roll)
                else: sr_mode = False # else doesn't set
                if d <= proba[2]: # SSR CASE
                    r = 2
                    tenrollsr = True
                    d /= mods[2]
                elif (not sr_mode and d <= proba[1] + proba[2]) or sr_mode: # SR CASE
                    r = 1
                    d -= proba[2]
                    while d >= proba[1]: # for forced sr
                        d -= proba[1]
                    d /= mods[1]
                    tenrollsr = True
                else: # R CASE
                    r = 0
                    d -= proba[2] + proba[1]
                    d /= mods[0]
                if i % 10 == 9: tenrollsr = False # unset flag if we did 10 rolls
                if self.complete: # if we have a real gacha
                    roll = None
                    for rate in self.data[r]['list']: # find which item we rolled
                        fr = float(rate)
                        for item in self.data[r]['list'][rate]:
                            rateupitem = False 
                            if r == 2 and rate in self.rateups: rateupitem = True
                            if d <= fr:
                                roll = [r, item, rateupitem]
                                break
                            d -= fr
                        if roll is not None:
                            break
                    if roll is None:
                        roll = [r, item, rateupitem]
                    if roll[2]: result['list'].append([roll[0], "**" + self.bot.gacha.formatGachaItem(roll[1]) + "**"])
                    else: result['list'].append([roll[0], self.bot.gacha.formatGachaItem(roll[1])])
                    result['detail'][r] += 1
                    if rate in self.rateups and r + 1 > self.best[0]:
                        self.best = roll.copy()
                        self.best[0] += 1
                    elif r > self.best[0]:
                        self.best = roll.copy()
                    if r == 2:
                        # check memeroll must stop
                        if self.mode == self.MODE_MEMEA: break # memeroll mode A
                        elif self.mode == self.MODE_MEMEB and result['list'][-1][1].startswith("**"): break # memeroll mode B
                else: # using dummy gacha
                    result['list'].append([r, '']) # '' because no item names
                    result['detail'][r] += 1
                    if r == 2:
                        if self.mode == self.MODE_MEMEA or self.mode == self.MODE_MEMEB: break  # memeroll mode A and B
                # end of a serie of 10 rolls, check for gachapin/mukku/etc...
                if i % 10 == 9:
                    if (self.mode == self.MODE_GACHAPIN or self.mode == self.MODE_MUKKU) and result['detail'][2] >= 1: break # gachapin and mukku mode
                    elif self.mode == self.MODE_SUPER and result['detail'][2] >= 5: break # super mukku mode
            self.result = result # store result
        except Exception as e:
            self.exception = e

    """updateThumbnail()
    Update self.thumbnail based on self.best content
    To use after generate()
    """
    async def updateThumbnail(self) -> None:
        if self.best[0] != -1 and self.best[1] != "":
            search = self.best[1][2:]
            element = ['fire', 'water', 'earth', 'wind', 'light', 'dark'][int(self.best[1][0])-1]
            prof = (['sabre', 'dagger', 'spear', 'axe', 'staff', 'gun', 'melee', 'bow', 'harp', 'katana'][int(self.best[1][1])] if self.best[1][1] != 'S' else None)
            rid = await self.bot.util.search_wiki_for_id(search, "summons" if self.best[1][1] == 'S' else "weapons", from_gacha=True, element=element, proficiency=prof) # retrieve the id from the wiki
            if rid is None: self.thumbnail = None # and update self.thumbnail accordingly
            elif rid.startswith('1'): self.thumbnail = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/weapon/m/{}.jpg".format(rid)
            elif rid.startswith('2'): self.thumbnail = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/summon/m/{}.jpg".format(rid)
            else: self.thumbnail = None

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

    """output()
    Output the result via a disnake Interaction
    
    Parameters
    --------
    inter: Interaction to use. Must have been deferred beforehand
    display_mode: Integer. 0=single roll, 1=ten roll, 2=memeroll, 3=ssr list
    titles: Tuple of 2 strings. First and Second embed titles to display
    """
    async def output(self, inter: disnake.Interaction, display_mode : int, titles : tuple=("{}", "{}")) -> None:
        if 'list' not in self.result or self.exception is not None: # error check
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An error occured", color=self.color))
            self.bot.logger.pushError("[GACHA] 'simulator output' error:", self.exception)
            return
        elif self.mode == self.MODE_SCAM and (self.scamdata is None or not self.scamdata[3]): # scam error check
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="No Star Premium Gachas available at selected index", color=self.color))
            return
        # set embed footer
        footer = "{}% SSR rate".format(self.result['rate'])
        match self.mode:
            case self.MODE_MEMEB:
                footer += " ▫️ until rate up"
            case self.MODE_SCAM:
                footer += " ▫️ Selected Scam #{}".format(self.scamdata[5]+1)
            case _:
                pass
        if self.isclassic:
            footer += " ▫️ Classic {}".format(self.isclassic)
        # get scam roll
        if self.scamdata is not None:
            sroll = self.scamRoll()
        # update thumbnail
        await self.updateThumbnail()
        # select crystal image
        if (100 * self.result['detail'][2] / len(self.result['list'])) >= self.result['rate']: crystal = random.choice([self.CRYSTALS[2], self.CRYSTALS[3]])
        elif (100 * self.result['detail'][1] / len(self.result['list'])) >= self.result['rate']: crystal = self.CRYSTALS[2]
        else: crystal = random.choice([self.CRYSTALS[0], self.CRYSTALS[1]])
        # startup msg
        view = Tap(self.bot, owner_id=inter.author.id)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[0].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, image=crystal, color=self.color, footer=footer), view=view)
        await view.wait()

        match display_mode:
            case 0: # single roll display
                r = self.result['list'][0]
                await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="{}{}".format(self.bot.emote.get({0:'R', 1:'SR', 2:'SSR'}.get(r[0])), r[1]), color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)
            case 1: # ten roll display
                for i in range(0, 11):
                    msg = []
                    for j in range(0, i):
                        if j >= 10: break
                        # write
                        msg.append("{}{} ".format(self.bot.emote.get({0:'R', 1:'SR', 2:'SSR'}.get(self.result['list'][j][0])), self.result['list'][j][1]))
                        if j % 2 == 1: msg.append("\n")
                    for j in range(i, 10):
                        msg.append('{}'.format(self.bot.emote.get('crystal{}'.format(self.result['list'][j][0]))))
                        if j % 2 == 1: msg.append("\n")
                    if self.scamdata is not None: msg.append("{}{}\n{}".format(self.bot.emote.get('SSR'), self.bot.emote.get('crystal2'), self.bot.emote.get('red')))
                    await asyncio.sleep(0.7)
                    await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=''.join(msg), color=self.color, footer=footer, thumbnail=(self.thumbnail if (i == 10 and self.scamdata is None) else None)), view=None)
                if self.scamdata is not None:
                    msg = '\n'.join(''.join(msg).split('\n')[:-2]) + "\n{}**{}**\n{}**{}**".format(self.bot.emote.get('SSR'), self.bot.gacha.formatGachaItem(sroll[0]), self.bot.emote.get('red'), sroll[1])
                    await asyncio.sleep(1)
                    await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=msg, color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)
            case 2: # meme roll display
                counter = [0, 0, 0]
                msg = []
                best = [-1, ""]
                if self.mode == self.MODE_MEMEB: item_count = 5
                else: item_count = 3
                for i, v in enumerate(self.result['list']):
                    if i > 0 and i % item_count == 0:
                        await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[0].format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="{} {} ▫️ {} {} ▫️ {} {}\n{}".format(counter[2], self.bot.emote.get('SSR'), counter[1], self.bot.emote.get('SR'), counter[0], self.bot.emote.get('R'), ''.join(msg)), color=self.color, footer=footer), view=None)
                        await asyncio.sleep(1)
                        msg = []
                    msg.append("{} {}\n".format(self.bot.emote.get({0:'R', 1:'SR', 2:'SSR'}.get(v[0])), v[1]))
                    counter[v[0]] += 1
                title = (titles[1].format(inter.author.display_name, len(self.result['list'])) if (len(self.result['list']) < 300) else "{} sparked".format(inter.author.display_name))
                await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description="{} {} ▫️ {} {} ▫️ {} {}\n{}".format(counter[2], self.bot.emote.get('SSR'), counter[1], self.bot.emote.get('SR'), counter[0], self.bot.emote.get('R'), ''.join(msg)), color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)
            case 3: # spark display
                count = len(self.result['list'])
                rate = (100*self.result['detail'][2]/count)
                msg = []
                best = [-1, ""]
                rolls = self.getSSRList()
                for r in rolls: # check for best roll
                    if best[0] < 3 and '**' in r: best = [3, r.replace('**', '')]
                    elif best[0] < 2: best = [2, r]
                if len(rolls) > 0 and self.complete:
                    msg.append("{} ".format(self.bot.emote.get('SSR')))
                    for item in rolls:
                        msg.append(item)
                        if rolls[item] > 1: msg.append(" x{}".format(rolls[item]))
                        await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name, count), 'icon_url':inter.author.display_avatar}, description=''.join(msg), color=self.color, footer=footer), view=None)
                        await asyncio.sleep(0.75)
                        msg.append(" ")
                if self.mode == self.MODE_GACHAPIN: amsg = "Gachapin stopped after **{}** rolls\n".format(len(self.result['list']))
                elif self.mode == self.MODE_MUKKU: amsg = "Mukku stopped after **{}** rolls\n".format(len(self.result['list']))
                elif self.mode == self.MODE_SUPER: amsg = "Super Mukku stopped after **{}** rolls\n".format(len(self.result['list']))
                else: amsg = ""
                msg = "{}{:} {:} ▫️ {:} {:} ▫️ {:} {:}\n{:}\n**{:.2f}%** SSR rate".format(amsg, self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), ''.join(msg), rate)
                await inter.edit_original_message(embed=self.bot.embed(author={'name':titles[1].format(inter.author.display_name, count), 'icon_url':inter.author.display_avatar}, description=msg, color=self.color, footer=footer, thumbnail=self.thumbnail), view=None)

    """getSSRList()
    Extract the SSR from a full gacha list generated by gachaRoll()
    
    Returns
    --------
    dict: SSR List. The keys are the SSR name and the values are how many your rolled
    """
    def getSSRList(self) -> dict:
        rolls = {}
        for r in self.result['list']:
            if r[0] == 2: rolls[r[1]] = rolls.get(r[1], 0) + 1
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
        footer = ""
        roll = 0
        rps = ['rock', 'paper', 'scissor']
        ct = self.bot.util.JST()
        # apply settings
        settings = self.bot.data.save['gbfdata'].get('roulette', {})
        fixedS = ct.replace(year=2000+settings.get('year', 24), month=settings.get('month', 1), day=settings.get('day', 1), hour=5, minute=0, second=0, microsecond=0) # beginning of fixed rolls
        fixedE = fixedS + timedelta(days=1, seconds=0) # end of fixed rolls
        fixedS -= timedelta(seconds=36000) # move start 10h early
        forced3pc = settings.get('forced3%', True) # force 3%
        forcedRollCount = settings.get('forcedroll', 100) # number of rolls during fixed rolls
        forcedSuperMukku = settings.get('forcedsuper', True)
        enable200 = settings.get('enable200', False) # add 200 on wheel
        enableJanken = settings.get('enablejanken', False)
        maxJanken = settings.get('maxjanken', 1)
        doubleMukku = settings.get('doublemukku', False)
        realist = realist and settings.get('realist', False)
        birthdayMode = settings.get('birthday', False) # add birthday on wheel
        # settings end
        self.thumbnail = self.ROULETTE
        prev_best = None
        state = 0
        superFlag = False
        if ct >= fixedS and ct < fixedE:
            msg = "{} {} :confetti_ball: :tada: Guaranteed **{} 0 0** R O L L S :tada: :confetti_ball: {} {}\n".format(self.bot.emote.get('crystal'), self.bot.emote.get('crystal'), forcedRollCount//100, self.bot.emote.get('crystal'), self.bot.emote.get('crystal'))
            roll = forcedRollCount
            if forcedSuperMukku: superFlag = True
            if legfest == 1 and forced3pc:
                legfest = -1
            d = 0
            state = 1
        else:
            d = random.randint(1, 10000)
            results = []
            results.append((1, 800)) # gachapin 8%
            results.append((30, 2000)) # 30 rolls 20%
            if birthdayMode: results.append((2, 500)) # birthday 5%
            if realist:
                results.append((20, None))
            else:
                results.append((0, 200)) # hundred 2%
                results.append((20, 3500)) # 20 rolls 35%
                results.append((10, None))
            threshold = 0
            for r in results:
                if r[1] is not None and d > threshold + r[1]:
                    threshold += r[1]
                    continue
                match r[0]:
                    case 0:
                        if enable200:
                            msg = "{} {} :confetti_ball: :tada: **2 0 0 R O L L S** :tada: :confetti_ball: {} {}\n".format(self.bot.emote.get('crystal'), self.bot.emote.get('crystal'), self.bot.emote.get('crystal'), self.bot.emote.get('crystal'))
                            roll = 200
                        else:
                            msg = ":confetti_ball: :tada: **100** rolls!! :tada: :confetti_ball:\n"
                            roll = 100
                    case 1:
                        msg = "**Gachapin Frenzy** :four_leaf_clover:\n"
                        roll = -1
                        state = 2
                    case 2:
                        msg = ":birthday: You got the **Birthday Zone** :birthday:\n"
                        roll = -1
                        state = 5
                    case 30:
                        msg = "**30** rolls! :clap:\n"
                        roll = 30
                    case 20:
                        msg = "**20** rolls :open_mouth:\n"
                        roll = 20
                    case 10:
                        msg = "**10** rolls :pensive:\n"
                        roll = 10
                break
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} is spinning the Roulette".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=msg, color=self.color, footer=footer, thumbnail=self.thumbnail))
        if not enableJanken and state < 2: state = 1
        running = True
        # loop
        while running:
            if self.exception is not None:
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An error occured", color=self.color))
                self.bot.logger.pushError("[GACHA] 'simulator roulette' error:", self.exception)
                return
            start_time = time.time()
            await asyncio.sleep(0) # to not risk blocking
            match state:
                case 0: # RPS
                    if enableJanken and d >= 2000 and random.randint(0, 2) > 0:
                        a = 0
                        b = 0
                        while a == b:
                            a = random.randint(0, 2)
                            b = random.randint(0, 2)
                        msg += "You got **{}**, Gachapin got **{}**".format(rps[a], rps[b])
                        if (a == 1 and b == 0) or (a == 2 and b == 1) or (a == 0 and b == 2):
                            msg += " :thumbsup:\nYou **won** rock paper scissor, your rolls are **doubled** :confetti_ball:\n"
                            roll = roll * 2
                            if roll > (200 if enable200 else 100): roll = (200 if enable200 else 100)
                            maxJanken -= 1
                            if maxJanken == 0:
                                state = 1
                        else:
                            msg += " :pensive:\n"
                            state = 1
                    else:
                        state = 1
                case 1: # normal rolls
                    await self.generate(roll, legfest)
                    count = len(self.result['list'])
                    rate = (100*self.result['detail'][2]/count)
                    ssrs = self.getSSRList()
                    if len(ssrs) > 0: # make the text
                        tmp = "\n{} ".format(self.bot.emote.get('SSR'))
                        for item in ssrs:
                            tmp += item
                            if ssrs[item] > 1: tmp += " x{}".format(ssrs[item])
                            tmp += " "
                    else:
                        tmp = ""
                    footer = "{}% SSR rate".format(self.result['rate'])
                    if self.isclassic:
                        footer += " ▫️ Classic {}".format(self.isclassic)
                    msg += "{:} {:} ▫️ {:} {:} ▫️ {:} {:}{:}\n**{:.2f}%** SSR rate\n\n".format(self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), tmp, rate)
                    if superFlag: state = 4
                    else: running = False
                case 2: # gachapin
                    self.changeMode('gachapin')
                    await self.generate(300, legfest)
                    count = len(self.result['list'])
                    rate = (100*self.result['detail'][2]/count)
                    ssrs = self.getSSRList()
                    if len(ssrs) > 0: # make the text
                        tmp = "\n{} ".format(self.bot.emote.get('SSR'))
                        for item in ssrs:
                            tmp += item
                            if ssrs[item] > 1: tmp += " x{}".format(ssrs[item])
                            tmp += " "
                    else:
                        tmp = ""
                    footer = "{}% SSR rate".format(self.result['rate'])
                    if self.isclassic:
                        footer += " ▫️ Classic {}".format(self.isclassic)
                    msg += "Gachapin ▫️ **{}** rolls\n{:} {:} ▫️ {:} {:} ▫️ {:} {:}{:}\n**{:.2f}%** SSR rate\n\n".format(count, self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), tmp, rate)
                    if count == 10 and random.randint(1, 100) <= 99: state = 3
                    elif count == 20 and random.randint(1, 100) <= 60: state = 3
                    elif count == 30 and random.randint(1, 100) <= 30: state = 3
                    elif random.randint(1, 100) <= 3: state = 3
                    else: running = False
                case 3:
                    self.changeMode('mukku')
                    await self.generate(300, legfest)
                    count = len(self.result['list'])
                    rate = (100*self.result['detail'][2]/count)
                    ssrs = self.getSSRList()
                    if len(ssrs) > 0: # make the text
                        tmp = "\n{} ".format(self.bot.emote.get('SSR'))
                        for item in ssrs:
                            tmp += item
                            if ssrs[item] > 1: tmp += " x{}".format(ssrs[item])
                            tmp += " "
                    else:
                        tmp = ""
                    msg += ":confetti_ball: Mukku ▫️ **{}** rolls\n{:} {:} ▫️ {:} {:} ▫️ {:} {:}{:}\n**{:.2f}%** SSR rate\n\n".format(count, self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), tmp, rate)
                    if doubleMukku:
                        if random.randint(1, 100) < 25: pass
                        else: running = False
                        doubleMukku = False
                    else:
                        running = False
                case 4:
                    self.changeMode('supermukku')
                    await self.generate(300, legfest)
                    count = len(self.result['list'])
                    rate = (100*self.result['detail'][2]/count)
                    ssrs = self.getSSRList()
                    if len(ssrs) > 0: # make the text
                        tmp = "\n{} ".format(self.bot.emote.get('SSR'))
                        for item in ssrs:
                            tmp += item
                            if ssrs[item] > 1: tmp += " x{}".format(ssrs[item])
                            tmp += " "
                    else:
                        tmp = ""
                    msg += ":confetti_ball: **Super Mukku** ▫️ **{}** rolls\n{:} {:} ▫️ {:} {:} ▫️ {:} {:}{:}\n**{:.2f}%** SSR rate\n\n".format(count, self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), tmp, rate)
                    running = False
                case 5: # birthday roulette
                    d = random.randint(1, 10000)
                    tmp = ""
                    running = False
                    if d <= 2000: roll = 100
                    elif d <= 3400: roll = 50
                    elif d <= 4800: roll = 60
                    elif d <= 6200: roll = 70
                    elif d <= 7600: roll = 80
                    elif d <= 9000:
                        state = 2
                        msg += ":confetti_ball: You got the **Gachapin**!!\n"
                        running = True
                        tmp = "None"
                    else:
                        self.changeMode('all')
                        roll = 10
                    if tmp == "":
                        await self.generate(roll, legfest)
                        count = len(self.result['list'])
                        rate = (100*self.result['detail'][2]/count)
                        ssrs = self.getSSRList()
                        if len(ssrs) > 0: # make the text
                            tmp = "\n{} ".format(self.bot.emote.get('SSR'))
                            for item in ssrs:
                                tmp += item
                                if ssrs[item] > 1: tmp += " x{}".format(ssrs[item])
                                tmp += " "
                        else:
                            tmp = ""
                        if d > 9000: # guaranted ssr
                            msg += ":confetti_ball: :confetti_ball: **Guaranted SSR** ▫️ **{}** rolls\n{:} {:} ▫️ {:} {:} ▫️ {:} {:}{:}\n\n".format(count, self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), tmp)
                        else:
                            msg += ":confetti_ball: **{}** rolls\n{:} {:} ▫️ {:} {:} ▫️ {:} {:}{:}\n**{:.2f}%** SSR rate\n\n".format(count, self.result['detail'][2], self.bot.emote.get('SSR'), self.result['detail'][1], self.bot.emote.get('SR'), self.result['detail'][0], self.bot.emote.get('R'), tmp, rate)
                        footer = "{}% SSR rate".format(self.result['rate'])
            if realist: footer += " ▫️ Realist"
            if prev_best is None or str(self.best) != prev_best:
                prev_best = str(self.best)
                await self.updateThumbnail()
            diff = self.ROULETTE_DELAY - (time.time() - start_time)
            if diff > 0: await asyncio.sleep(diff)
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} spun the Roulette".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=msg + ("" if not running else "**...**"), color=self.color, footer=footer, thumbnail=self.thumbnail))