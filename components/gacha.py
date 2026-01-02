from __future__ import annotations
import disnake
import asyncio
from datetime import datetime, timedelta
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.util import JSON
    from components.network import RequestResult
    # Type Aliases
    type CurrentGacha = list[timedelta|JSON]
    type CurrentBanner = tuple[int, JSON, list[str], int, bool, dict[str, int]|None, int]
from enum import IntEnum, StrEnum
import random
import time
from views.roll_tap import Tap


# General enum
class Rarity(IntEnum):
    R = 0
    SR = 1
    SSR = 2

# ----------------------------------------------------------------------
# Gacha Component
# ----------------------------------------------------------------------
# Manage the real granblue gacha
# Also provide a simulator for games
# ----------------------------------------------------------------------


class Gacha():
    ZODIAC_WPN : list[str] = [ # for the twelve generals detection, gotta update it yearly
        'Ramulus', 'Dormius', 'Gallinarius', 'Canisius',
        'Porculius', 'Rodentius', 'Bovinius', 'Tigrisius',
        'Leporidius', 'Dracosius', 'Serpentius', 'Equinius'
    ]
    CLASSIC_COUNT : int = 2 # number of classic banners
    # constants
    NO_INFO : str = " "
    SUMMON_KIND : str = "S"
    # Dummy scam data
    SCAM_DUMMY : dict[str, int] = {
        'Sunlight Stone':2000,
        'Damascus Ingot':2000,
        'Damascus Crystal x2':6000,
        'Brimstone Earrings x2':5000,
        'Permafrost Earrings x2':5000,
        'Brickearth Earrings x2':5000,
        'Jetstream Earrings x2':5000,
        'Sunbeam Earrings x2':5000,
        'Nightshade Earrings x2':5000,
        'Intracacy Ring':5000,
        'Meteorite x10':5000,
        'Abyssal Wing x5':5000,
        'Tears of the Apocalypse x10':5000,
        'Ruby Awakening Orb x2':4000,
        'Sapphire Awakening Orb x2':4000,
        'Citrine  Awakening Orb x2':4000,
        'Sephira Stone x10':4000,
        'Weapon Plus Mark x30':4000,
        'Summon Plus Mark x30':4000,
        'Gold Moon x2':4000,
        'Half Elixir x100':4000,
        'Soul Berry x300':4000
    }
    GACHA_IMG_URL : str = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/gacha/{}"

    __slots__ = ("bot")

    def __init__(self : Gacha, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

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
    async def get(self : Gacha) -> CurrentGacha:
        # current time, a bit in the past to ensure it's updated later
        c : datetime = self.bot.util.JST().replace(microsecond=0) - timedelta(seconds=70)
        # we check:
        # - if gacha data doesn't exist
        # - if gacha data is outdated
        # - if a gacha collab banner ended
        # - if the update failed
        if (('gacha' not in self.bot.data.save['gbfdata']
                or self.bot.data.save['gbfdata']['gacha'] is None
                or c >= self.bot.data.save['gbfdata']['gacha']['time']
                or c >= self.bot.data.save['gbfdata']['gacha'].get('collaboration', c + timedelta(seconds=10)))
                and not await self.update()):
            # if all those passed, we return nothing
            return []
        # if we lack the gacha banner timer, we also return nothing
        if self.bot.data.save['gbfdata']['gacha']['time'] is None:
            return []
        # else, return current time used (for timing reasons) and the gacha data
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
    async def process(self : Gacha, gtype : str, bid : str|int, sub_id : int) -> tuple[JSON, JSON, JSON]:
        try:
            # get the banner draw rate
            data : RequestResult = await self.bot.net.requestGBF(
                "gacha/provision_ratio/{}/{}/{}".format(
                    gtype,
                    bid,
                    sub_id
                ),
                expect_JSON=True
            )
            gratio : JSON = data['ratio'][0]['ratio']
            glist : JSON = [{'rate':0, 'list':{}}, {'rate':0, 'list':{}}, {'rate':0, 'list':{}}]
            grateup : JSON = {'zodiac':[]}
            # loop over data
            appear : JSON
            for appear in data['appear']:
                rarity : int = appear['rarity'] - 2
                if rarity < Rarity.R or rarity > Rarity.SSR:
                    continue # eliminate possible N rarity
                glist[rarity]['rate'] = float(data['ratio'][2 - rarity]['ratio'][:-1])
                item : JSON
                for item in appear['item']:
                    kind : str|int
                    attribute : str|int|None
                    if item['kind'] is None: # summon and scam select use None by default
                        if sub_id == 3 and item.get('name', '').startswith('Item '): # check if it's an item
                            kind = self.NO_INFO
                        else:
                            kind = self.SUMMON_KIND
                    else:
                        kind = int(item['kind']) - 1 # weapon prof
                    attribute = item.get('attribute', None) # get element
                    if attribute is None:
                        attribute = self.NO_INFO # empty if element is missing
                    # if item rate isn't in the data
                    if item['drop_rate'] not in glist[rarity]['list']:
                        glist[rarity]['list'][item['drop_rate']] = [] # add a list for that rate
                    # add the item to that array
                    # (Format is Element Character, Type character and Item name.
                    # Example: 5STriple Zero (5 is light, S for summon, Triple Zero is the name)
                    glist[rarity]['list'][item['drop_rate']].append("{}{}{}".format(attribute, kind, item['name']))

                    if rarity == Rarity.SSR: # if it's a SSR
                        if appear['category_name'] not in grateup:
                            # Add rate dict for that type of item (Usually Character Weapons and Summon)
                            grateup[appear['category_name']] = {}
                        # check if it's a twelve general
                        if 'character_name' in item and item.get('name', '') in self.ZODIAC_WPN:
                            # add it to the list of generals present in the banner
                            grateup['zodiac'].append("{}{}{}".format(attribute, kind, item['character_name']))
                        # Check if on rate up
                        if item.get('incidence', None) is not None:
                            if item['drop_rate'] not in grateup[appear['category_name']]:
                                # If rate isn't in rate list type
                                grateup[appear['category_name']][item['drop_rate']] = []
                            if 'character_name' in item and item['character_name'] is not None: # If it's a character
                                # Add character to rate up (Format is Element Character, Type character and Item name)
                                grateup[appear['category_name']][item['drop_rate']].append(
                                    "{}{}{}".format(
                                        item['attribute'],
                                        kind,
                                        item['character_name']
                                    )
                                )
                            else: # Else item name
                                # (Format is Element Character, Type character and Item name)
                                grateup[appear['category_name']][item['drop_rate']].append(
                                    "{}{}{}".format(
                                        attribute,
                                        kind,
                                        item['name']
                                    )
                                )
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
    dict: Pair of item names and rates
    """
    async def getScamRate(self : Gacha, gtype : str, bid : str|int) -> dict[str, int]:
        try:
            # request given scam data
            appear : JSON = (await self.bot.net.requestGBF(
                "gacha/provision_ratio/{}/{}/4".format(gtype, bid),
                expect_JSON=True
            ))['appear']
            items : dict[str, int] = {}
            e : JSON
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
    Banner timers usually don't have the year, so we use the current year in our datetime.
    If a banner carries over from one year to another, this fix is needed.

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
    def fix_time_newyear(self : Gacha, current : datetime, d : datetime) -> tuple[datetime, bool]:
        NY : bool = False
        if current > d: # If the banner time is before our current time
            d = d.replace(year=d.year + 1) # we add a year
            NY = True
        return d, NY

    """update()
    Request and update the GBF gacha in the save data

    Returns
    --------
    bool: True if success, False if error
    """
    async def update(self : Gacha) -> bool:
        # check if GBF can be accessed
        if not self.bot.net.has_account() or not await self.bot.net.gbf_available():
            return False
        try:
            c : datetime = self.bot.util.JST() # current time
            # check the gacha page
            data : RequestResult = await self.bot.net.requestGBF("gacha/list", expect_JSON=True)
            if data is None:
                raise Exception()
            # data container
            gacha_data = {'banners':[]}
            # retrieve data from gacha page request
            index : int = -1
            scam_ids : list[int|str] = []
            i : int
            g : JSON
            for i, g in enumerate(data['legend']['lineup']):
                if g['name'] == "Premium Draw":
                    index = i # normal banner index in the data
                elif g['name'].find("Star Premium") != -1:
                    for subscam in g['campaign_gacha_ids']: # scam(s) ids, if they exist
                        scam_ids.append(subscam['id'])

            # set timers
            gacha_data['time'] = datetime.strptime(
                str(c.year) + '/' + data['legend']['lineup'][index]['end'],
                '%Y/%m/%d %H:%M'
            ).replace(microsecond=0) # banner end timer
            NY : bool
            gacha_data['time'], NY = self.fix_time_newyear(c, gacha_data['time']) # apply fix
            # sub banner time (usually for multi element banners, whose sparks carry over)
            gacha_data['timesub'] = datetime.strptime(data['ceiling']['end'], '%Y/%m/%d %H:%M').replace(microsecond=0)
            if ((NY is False and gacha_data['timesub'] < gacha_data['time'])
                    or (NY is True and gacha_data['timesub'] > gacha_data['time'])):
                gacha_data['time'] = gacha_data['timesub'] # switch around if the New year fix has been applied

            # read crypto key
            random_key : str = data['legend']['random_key']
            # read header images
            header_images : list[str] = data['header_images']
            # read logo images
            logo : str = {
                'logo_fire':1,
                'logo_water':2,
                'logo_earth':3,
                'logo_wind':4,
                'logo_dark':5,
                'logo_light':6
            }.get(data.get('logo_image', ''), data.get('logo_image', '').replace('logo_', ''))
            # get normal banner id (single draw)
            gid : int|str = data['legend']['lineup'][index]['id']

            gratio : JSON
            glist : JSON
            grateup : JSON
            # request main banner details
            gratio, glist, grateup = await self.process('legend', gid, 1)
            if gratio is None:
                raise Exception("Couldn't retrieve main gacha banner")
            # append to data
            gacha_data['banners'].append({'ratio':gratio, 'list':glist, 'rateup':grateup})

            # request scam details (if they exist)
            sid : int|str
            for sid in scam_ids:
                gratio, glist, grateup = await self.process('legend', sid, 3)
                if gratio is not None:
                    if 'scam' not in gacha_data: # add scam data list if not set
                        gacha_data['scam'] = []
                    gacha_data['scam'].append( # append to scam data
                        {
                            'ratio':gratio,
                            'list':glist,
                            'rateup':grateup,
                            'items': (await self.getScamRate('legend', sid))
                        }
                    )

            # additional banners
            # it works like the main banner request
            # # classic gacha
            i : int
            for i in (500031, 501031): # id has to be set manually (for now)
                data : RequestResult = await self.bot.net.requestGBF(
                    "rest/gacha/classic/toppage_data_by_classic_series_id/{}".format(i),
                    expect_JSON=True
                )
                if data is not None and 'appearance_gacha_id' in data:
                    gratio, glist, grateup = await self.process('classic', data['appearance_gacha_id'], 1)
                    if gratio is not None:
                        gacha_data['banners'].append({'ratio':gratio, 'list':glist, 'rateup':grateup})
            # # collab gacha
            data : RequestResult = await self.bot.net.requestGBF(
                "rest/gacha/collaboration/toppage_data",
                expect_JSON=True
            )
            if data is not None and "collaboration" in data and "collaboration_ceiling" in data:
                # store the collaboration end time
                gacha_data['collaboration'] = datetime.strptime(
                    data['collaboration_ceiling']['end'],
                    '%Y/%m/%d %H:%M'
                ).replace(microsecond=0)
                gacha_data['collaboration'], NY = self.fix_time_newyear(c, gacha_data['collaboration'])
                gratio, glist, grateup = await self.process(
                    'collaboration',
                    data["collaboration"]["lineup"][-1]["id"],
                    1
                )
                if gratio is not None:
                    gacha_data['banners'].append({'ratio':gratio, 'list':glist, 'rateup':grateup})

            # add image
            gachas : list[str] = [
                '{}/tips/description_gacha.jpg'.format(random_key),
                '{}/tips/description_gacha_{}.jpg'.format(random_key, logo),
                '{}/tips/description_{}.jpg'.format(random_key, header_images[0]),
                'header/{}.png'.format(header_images[0])
            ]
            g : str
            for g in gachas: # check which one exists
                data : RequestResult = await self.bot.net.request(self.GACHA_IMG_URL.format(g))
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
    list: List of string to use to make the description.
        In list form to use join() later, for less string instantiation.
    """
    def summary_subroutine(
        self : Gacha,
        data : dict,
        index : int,
        time : datetime,
        timesub : datetime|None,
        remaining : datetime
    ) -> list[str]:
        # banner timer
        description : list[str] = [
            "{} Current gacha ends in **{}**".format(
                self.bot.emote.get('clock'),
                self.bot.util.delta2str(time - remaining, 2)
            )
        ]
        if timesub is not None and time != timesub:
            description.append(
                "\n{} Spark period ends in **{}**".format(
                    self.bot.emote.get('mark'),
                    self.bot.util.delta2str(timesub - remaining, 2)
                )
            )

        # calculate ssr rate sum
        sum_ssr : float = 0.0
        i : int
        rarity : int
        for i, rarity in enumerate(data['banners'][index]['list']):
            for r in rarity['list']:
                if i == Rarity.SSR: # SSR
                    sum_ssr += float(r) * len(rarity['list'][r]) # add rate multiplied by number of item

        # rate description
        description.append(
            "\n{} **Rate:** Advertised **{}**".format(
                self.bot.emote.get('SSR'),
                data['banners'][index]['ratio']
            )
        )
        if not data['banners'][index]['ratio'].startswith('3'):
            description.append(" **(Premium Gala)**")
        description.append(" ▫️ Sum of rates **{:.3f}%**".format(sum_ssr))
        if index == 0 and 'scam' in data: # Add number of available Scam gachas
            description.append(
                "\n{} **{}** Star Premium Draw(s) available".format(
                    self.bot.emote.get('mark'),
                    len(data['scam'])
                )
            )
        description.append("\n")

        # build rate up list
        k : str
        for k in data['banners'][index]['rateup']:
            if k == 'zodiac': # It should be first in the order
                # Write list of zodiacs to be available in the banner
                if len(data['banners'][index]['rateup']['zodiac']) > 0:
                    description.append("{} **Zodiac** ▫️ ".format(self.bot.emote.get('loot')))
                    item : str
                    for item in data['banners'][index]['rateup'][k]:
                        description.append(self.formatGachaItem(item) + " ")
                    description.append("\n")
            else:
                if len(data['banners'][index]['rateup'][k]) > 0:
                    # List top rate up for each category (Weapons and Summons)
                    for r in data['banners'][index]['rateup'][k]:
                        if k.lower().find("weapon") != -1:
                            description.append("{}**{}%** ▫️ ".format(self.bot.emote.get('sword'), r))
                        elif k.lower().find("summon") != -1:
                            description.append("{}**{}%** ▫️ ".format(self.bot.emote.get('summon'), r))
                        item : str
                        for i, item in enumerate(data['banners'][index]['rateup'][k][r]):
                            if i >= 8 and len(data['banners'][index]['rateup'][k][r]) - i > 1:
                                description.append(
                                    " and **{} more!**".format(
                                        len(data['banners'][index]['rateup'][k][r]) - i
                                    )
                                )
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
    async def summary(self : Gacha) -> None|tuple[str, str]:
        try:
            content : CurrentGacha = await self.get()
            if len(content) > 0:
                remaining : timedelta
                data : JSON
                remaining, data = tuple(content)
                # main banner summary
                description : list[str] = self.summary_subroutine(data, 0, data['time'], data['timesub'], remaining)
                # check if a collab exists
                if (len(data["banners"]) > self.CLASSIC_COUNT
                        and "collaboration" in data
                        and remaining < data["collaboration"]):
                    # add extra line
                    description.append("{} **Collaboration**\n".format(self.bot.emote.get('crystal')))
                    # and its summary
                    description.extend(
                        self.summary_subroutine(data, self.CLASSIC_COUNT + 1, data['collaboration'], None, remaining)
                    )
                # return message and the image url
                return (
                    "".join(description),
                    self.GACHA_IMG_URL.format(data['image'])
                )
            return None
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
        - The banner ID (after correcting if needed)
        - The whole rate list
        - The banner rate up
        - The ssr rate, in %
        - Boolean indicating if the gacha is the real one
        - (OPTIONAL): Dict, item list
        - (OPTIONAL): Integer, star premium gacha index
    """
    async def retrieve(self : Gacha, scam : int|None = None, banner : int = 0) -> CurrentBanner:
        try:
            data : JSON = (await self.get())[1] # retrieve the rate
            gacha_data : JSON
            if scam is None: # not asking for scam
                if 0 <= banner < len(data['banners']): # access asked banner
                    gacha_data = data['banners'][banner]
                else: # or first banner if invalid index
                    gacha_data = data['banners'][0]
                    banner = 0
            else:
                if 'scam' not in data or scam < 0 or scam >= len(data['scam']): # raise error if couldn't get scam
                    raise Exception()
                gacha_data = data['scam'][scam]
            # final check
            if len(gacha_data['list']) == 0:
                raise Exception()
            # gacha_data is now the data to the banner we're interested in
            data = gacha_data['list']
            rateups : list[str] = []
            # build a list of rate up for this banner
            k : str
            for k in gacha_data['rateup']:
                if k == "zodiac":
                    continue # ignore zodiac category
                elif len(gacha_data['rateup'][k]) > 0:
                    r : str
                    for r in gacha_data['rateup'][k]:
                        if r not in rateups:
                            rateups.append(r)
            # get SSR rate
            ssrrate : int = int(gacha_data['ratio'][0])
            complete : bool = True
            if scam is not None: # return scam data on top
                return banner, data, rateups, ssrrate, complete, gacha_data['items'], scam
        except:
            # legacy mode, dummy data
            data = [
                {"rate": 82.0, "list": {"82": [None]}},
                {"rate": 15.0, "list": {"15": [None]}},
                {"rate": 3.0, "list": {"3": [None]}}
            ]
            rateups = None
            ssrrate = 3
            complete = False
            banner = 0
        return banner, data, rateups, ssrrate, complete, None, None

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
    def isLegfest(self : Gacha, ssrrate : int, selected : int) -> bool:
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
    def allRates(self : Gacha, index : int) -> tuple[float, list[float]]:
        try:
            r : list[float] = []
            rate : str
            # SSR list
            for rate in list(self.bot.data.save['gbfdata']['gacha']['banners'][index]['list'][-1]['list'].keys()):
                if float(rate) not in r:
                    r.append(float(rate))
            return (
                float(self.bot.data.save['gbfdata']['gacha']['banners'][index]['ratio'][:-1]),
                sorted(r, reverse=True)
            )
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
    def formatGachaItem(self : Gacha, raw : str) -> str:
        if len(raw) < 3:
            return raw
        res : list[str] = []
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
    simtype: string, case sensitive. possible values:
        single, srssr, memerollA, memerollB, scam, ten, gachapin, mukku, supermukku
    bannerid: string for special gacha (scam...) or integer
        (0 for normal banner, 1~2 for classic, 3 for collab...)
    color: color to use for the embeds
    scamindex: index of the premium star gacha to use

    Returns
    --------
    GachaSimulator
    """
    async def simulate(
        self : Gacha,
        simtype : str,
        bannerid : int|str,
        color : int,
        scamindex : int = 1
    ) -> GachaSimulator:
        gachadata : CurrentBanner
        scamdata : CurrentBanner|None = None
        match bannerid:
            case 'scam':
                gachadata = await self.retrieve() # retrieve the data
                scamdata = await self.retrieve(scam=scamindex - 1) # and the scam data
                bannerid = 0
            case _:
                if not isinstance(bannerid, int): # invalid string, set to default index
                    bannerid = 0
                gachadata = await self.retrieve(banner=bannerid) # retrieve the data
        # create and return a simulator instance
        return GachaSimulator(self.bot, gachadata, simtype, scamdata, color)


# Type Aliases
GachaRoll = tuple[int, str, bool]


class GachaSimulator():
    class Mode(IntEnum): # Simulator modes
        UNDEF : int = -1
        SINGLE : int = 0
        SRSSR : int = 1
        MEMEA : int = 2
        MEMEB : int = 3
        TEN : int = 10
        GACHAPIN : int = 11
        MUKKU : int = 12
        SUPER : int = 13
        SCAM : int = 14
        ALL : int = 20

    class SSRRate(IntEnum): # SSR rate in percent
        SUPER : int = 15
        MUKKU : int = 9
        GALA : int = 6
        COLLAB : int = 4
        NORMAL : int = 3
        ALL : int = 100 # guaranted ssr

    # assets
    WPN_URL : str = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/weapon/m/{}.jpg"
    SUM_URL : str = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/summon/m/{}.jpg"
    ELEM_EMOTE : list[str] = ['fire', 'water', 'earth', 'wind', 'light', 'dark']
    PROF_EMOTE : list[str] = ['sabre', 'dagger', 'spear', 'axe', 'staff', 'gun', 'melee', 'bow', 'harp', 'katana']
    ROULETTE : str = "https://mizagbf.github.io/assets/rosetta-remote-resources/roulette.gif"

    class Crystal(StrEnum):
        N   : str = "https://mizagbf.github.io/assets/rosetta-remote-resources/0_s.png"
        R   : str = "https://mizagbf.github.io/assets/rosetta-remote-resources/1_s.png"
        SR  : str = "https://mizagbf.github.io/assets/rosetta-remote-resources/2_s.png"
        SSR : str = "https://mizagbf.github.io/assets/rosetta-remote-resources/3_s.png"

    # Others
    RarityStrTable = {Rarity.R:'R', Rarity.SR:'SR', Rarity.SSR:'SSR'}
    RPS : list[str] = ['rock', 'paper', 'scissor']
    ROULETTE_DELAY : int = 4

    __slots__ = (
        "bot", "bannerid", "data", "rateups", "ssrrate", "complete",
        "scamdata", "iscollab", "color", "mode", "result",
        "thumbnail", "best", "exception"
    )

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
    def __init__(
        self : GachaSimulator,
        bot : DiscordBot,
        gachadata : CurrentBanner,
        simtype : str,
        scamdata : CurrentBanner|None,
        color : int
    ) -> None:
        self.bot : DiscordBot = bot
        # unpack the data
        self.bannerid : int = gachadata[0]
        self.data : JSON = gachadata[1]
        self.rateups : list[str] = gachadata[2]
        self.ssrrate : int = gachadata[3]
        self.complete : bool = gachadata[4]
        self.scamdata : CurrentBanner = scamdata # no need to unpack the scam gacha one (assume it might be None too)
        self.iscollab : bool = (self.bannerid > self.bot.gacha.CLASSIC_COUNT)
        self.color : int = color
        self.mode : int = self.Mode.UNDEF
        self.changeMode(simtype)
        self.result : JSON = {} # output of generate()
        self.thumbnail : str|None = None # thumbnail of self.best
        self.best : GachaRoll = [-1, "", False] # best roll
        self.exception : Exception|None = None # contains the last exception

    """changeMode()
    update self.mode with a new value

    Parameters
    --------
    simtype: value from Gacha.simulate parameter() simtype
    """
    def changeMode(self : GachaSimulator, simtype : str) -> None:
        self.mode = {
            'single':self.Mode.SINGLE,
            'srssr':self.Mode.SRSSR,
            'memerollA':self.Mode.MEMEA,
            'memerollB':self.Mode.MEMEB,
            'ten':self.Mode.TEN,
            'gachapin':self.Mode.GACHAPIN,
            'mukku':self.Mode.MUKKU,
            'supermukku':self.Mode.SUPER,
            'scam':self.Mode.SCAM,
            'all':self.Mode.ALL
        }[simtype]

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
    def check_rate(self : GachaSimulator, ssrrate : int) -> tuple[list[float], list[float]]:
        # calcul R,SR,SSR & total
        proba : list[float] = [] # store the % of R, SR and SSR
        mods : list[float] = [1.0, 1.0, 1.0] # modifiers vs advertised rates, 1 by default
        for r in self.data:
            proba.append(0.0)
            rate : str
            for rate in r['list']:
                proba[-1] += float(rate) * len(r['list'][rate]) # sum of rates x items
        if ssrrate != self.data[Rarity.SSR]['rate']: # if wanted ssr rate different from advertised one
            mods[Rarity.SSR] = ssrrate / proba[Rarity.SSR] # calculate mod
            tmp : float = proba[Rarity.SSR] * mods[Rarity.SSR] # get new proba
            diff : float = proba[Rarity.SSR] - tmp # get diff between old and new
            if ssrrate == self.SSRRate.ALL:
                proba[Rarity.R] = 0
                proba[Rarity.SR] = 0
                mods[Rarity.R] = 0
                mods[Rarity.SR] = 0
            else:
                proba[Rarity.R] = max(0, proba[Rarity.R] + diff) # lower R proba
                try:
                    # calculate lowered R rate modifer
                    mods[Rarity.R] = (proba[Rarity.R] + diff) / proba[Rarity.R]
                except:
                    mods[Rarity.R] = 1
            proba[Rarity.SSR] = tmp # store SSR proba
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
    def get_generation_rate_and_modifiers(
        self : GachaSimulator,
        legfest : int
    ) -> tuple[int, list[float], list[float]]:
        ssrrate : int
        match self.mode:
            case self.Mode.ALL:
                ssrrate = self.SSRRate.ALL
            case self.Mode.SUPER:
                ssrrate = self.SSRRate.SUPER
            case self.Mode.MUKKU:
                ssrrate = self.SSRRate.MUKKU
            case _:
                if self.bot.gacha.isLegfest(self.ssrrate, legfest):
                    ssrrate = self.SSRRate.GALA
                else:
                    if self.iscollab:
                        ssrrate = self.SSRRate.COLLAB
                    else:
                        ssrrate = self.SSRRate.NORMAL
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
    def retrieve_single_roll_item(self : GachaSimulator, result: dict, rarity : int, dice : float) -> bool:
        if self.complete: # if we have a real gacha in memory
            roll : GachaRoll|None = None # will contain our rolled item
            # find which item we rolled
            rate : str
            rarity : int
            item : str
            rateupitem : bool
            for rate in self.data[rarity]['list']: # go over each rate category
                floatrate : float = float(rate)
                item : str
                for item in self.data[rarity]['list'][rate]: # and each item
                    rateupitem = False
                    if rarity == Rarity.SSR and rate in self.rateups: # if this is a rate up SSR
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
                roll = (rarity, item, rateupitem)
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
            if rarity == Rarity.SSR:
                # the loop must stop if we fulfilled the memeroll types
                if self.mode == self.Mode.MEMEA:
                    return True # memeroll mode A
                elif self.mode == self.Mode.MEMEB and result['list'][-1][1].startswith("**"):
                    return True # memeroll mode B
        else: # using dummy gacha
            result['list'].append([rarity, '']) # '' because no item names
            result['detail'][rarity] += 1
            if rarity == Rarity.SSR:
                if self.mode == self.Mode.MEMEA or self.mode == self.Mode.MEMEB:
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
    def generate_single_roll(
        self : GachaSimulator,
        result: dict,
        index : int,
        tenrollsr : bool,
        mods : list,
        proba : list
    ) -> tuple[bool, bool]:
        # our "dice" roll
        dice : int = random.randint(1, int(sum(proba) * 1000)) / 1000
        # Check if we must force a SR
        if self.mode == self.Mode.SRSSR or (self.mode >= self.Mode.TEN and index == 9 and not tenrollsr):
            # if SRSSR mode OR (we're doing a ten draw type of roll and we're on the 10th roll without SR/SSR)
            sr_mode = True
        else:
            sr_mode = False
        # determine what rarity we got
        rarity : int
        if dice <= proba[Rarity.SSR]: # SSR CASE
            rarity = Rarity.SSR
            tenrollsr = True # raise got sr flag
            dice /= mods[Rarity.SSR] # apply modifier
        elif (not sr_mode and dice <= proba[Rarity.SR] + proba[Rarity.SSR]) or sr_mode: # SR CASE
            rarity = Rarity.SR
            dice -= proba[Rarity.SSR]
            while dice >= proba[Rarity.SR]: # in case we forced a SR and we're above the rate
                dice -= proba[Rarity.SR]
            tenrollsr = True # raise got sr flag
            dice /= mods[Rarity.SR] # apply modifier
        else: # R CASE
            rarity = Rarity.R
            dice -= proba[Rarity.SSR] + proba[Rarity.SR]
            dice /= mods[Rarity.R] # apply modifier
        return tenrollsr, self.retrieve_single_roll_item(result, rarity, dice)

    """generate()
    Generate X amount of rolls and update self.result

    Parameters
    --------
    count: Integer, number of rolls wanted
    legfest: Integer, -1 for auto mod, 0 to force 3%, 1 to force 6%
    """
    async def generate(self : GachaSimulator, count : int, legfest : int = -1) -> None:
        try:
            ssrrate : int
            mods : list[float]
            proba: list[float]
            ssrrate, mods, proba = self.get_generation_rate_and_modifiers(legfest) # get ssr rate
            self.result = {} # reset the output
            result : JSON = {'list':[], 'detail':[0, 0, 0], 'rate':ssrrate} # temp output
            tenrollsr : bool = False # flag for guaranted SR in ten rolls
            if self.mode == self.Mode.MEMEB and len(self.rateups) == 0:
                self.mode = self.Mode.MEMEA # revert memerollB to A if no rate ups
            # rolling loop
            i : int
            for i in range(0, count):
                modulo_i : int = i % 10 # get index in current ten roll
                stop : bool
                tenrollsr, stop = self.generate_single_roll(result, modulo_i, tenrollsr, mods, proba)
                if stop:
                    break
                # end of a series of 10 rolls, check for gachapin/mukku/etc...
                if modulo_i == 9:
                    tenrollsr = False # unset SR flag if we did 10 rolls
                    if ((self.mode == self.Mode.GACHAPIN or self.mode == self.Mode.MUKKU)
                            and result['detail'][Rarity.SSR] >= 1):
                        break # gachapin and mukku mode, we end here
                    elif self.mode == self.Mode.SUPER and result['detail'][Rarity.SSR] >= 5:
                        break # super mukku mode, we end here
            self.result = result # store result
        except Exception as e:
            self.exception = e

    """updateThumbnail()
    Update self.thumbnail based on self.best content
    To use after generate()
    """
    async def updateThumbnail(self : GachaSimulator) -> None:
        try:
            if self.best[0] != -1 and self.best[1] != "":
                search : str = self.best[1][2:]
                # extract element and proficiency for wiki search
                element : str = self.ELEM_EMOTE[int(self.best[1][0]) - 1]
                prof : str = (self.PROF_EMOTE[int(self.best[1][1])] if self.best[1][1] != 'S' else None)
                # retrieve the element id from the wiki
                rid : str|None = await self.bot.util.search_wiki_for_id(
                    search,
                    "summons" if self.best[1][1] == 'S' else "weapons",
                    from_gacha=True,
                    element=element,
                    proficiency=prof
                )
                if rid is None: # not found
                    self.thumbnail = None
                elif rid.startswith('1'): # weapon
                    self.thumbnail = self.WPN_URL.format(rid)
                elif rid.startswith('2'): # summon
                    self.thumbnail = self.SUM_URL.format(rid)
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
    def scamRoll(self : GachaSimulator) -> tuple[str, str]:
        _unused_ : int
        data : JSON
        rateups : list[str]
        ssrrate : int
        complete : bool
        items : dict[str, int]|None
        scamindex : int
        # no error check, do it before calling the function
        _unused_, data, rateups, ssrrate, complete, items, scamindex = self.scamdata
        if items is None:
            items = self.bot.gacha.SCAM_DUMMY
        scam_rate : int = sum(list(items.values()))
        roll : int = random.randint(1, scam_rate) # roll a dice for the item
        loot : str|None = None
        n : int = 0
        k : str
        v : int
        for k, v in items.items(): # iterate over items with our dice value
            n += v
            if roll <= n:
                loot = k
                break
        # pick the random ssr
        # force ssr in self.best by setting to True
        self.best = (99, random.choice(data[2]['list'][list(data[2]['list'].keys())[0]]), True)
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
    def bannerIDtoFooter(self : GachaSimulator, footer : list[str]) -> str:
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
    async def render_errors(self : GachaSimulator, inter : disnake.Interaction) -> bool:
        if 'list' not in self.result or self.exception is not None: # an error occured
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An error occured",
                    color=self.color
                )
            )
            self.bot.logger.pushError("[GACHA] 'simulator output' error:", self.exception)
            return True
        elif (
            self.mode == self.Mode.SCAM
            and (
                self.scamdata is None
                or not self.scamdata[3]
                or self.scamdata[6] is None
            )
        ): # scam error occured
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="No Star Premium Gachas available at selected index",
                    color=self.color
                )
            )
            return True
        return False

    """generate_render_footer()
    Return the string to be used as an Embed footer in render()

    Returns
    --------
    str: The footer
    """
    def generate_render_footer(self : GachaSimulator) -> str:
        footer : list[str] = ["{}% SSR rate".format(self.result['rate'])] # banner rate
        match self.mode:
            case self.Mode.MEMEB:
                footer.append(" ▫️ until rate up")
            case self.Mode.SCAM:
                footer.append(" ▫️ Selected Scam #{}".format(self.scamdata[6] + 1))
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
    def generate_render_crystal(self : GachaSimulator) -> str:
        # select crystal image
        if (100 * self.result['detail'][Rarity.SSR] / len(self.result['list'])) >= self.result['rate']: # SSR
            return random.choice([self.Crystal.SR, self.Crystal.SSR])
        elif (100 * self.result['detail'][Rarity.SR] / len(self.result['list'])) >= self.result['rate']: # SR
            return self.Crystal.SR
        else:
            return random.choice([self.Crystal.N, self.Crystal.R]) # R

    """render_single_roll()
    Display the result of a single draw in the given interaction.
    Called by render().

    Parameters
    --------
    inter: render() interaction
    titles: Tuple of Strings. Second element is used in the embed author name. First is unused.
    footer: String, embed footer
    """
    async def render_single_roll(
        self : GachaSimulator,
        inter : disnake.Interaction,
        titles : tuple[str, str],
        footer : str
    ) -> None:
        item : GachaRoll = self.result['list'][0] # get the first (and likely only) item
        await inter.edit_original_message(
            embed=self.bot.embed(
                author={
                    'name':titles[1].format(inter.author.display_name),
                    'icon_url':inter.author.display_avatar
                },
                description="{}{}".format(
                    self.bot.emote.get(self.RarityStrTable.get(item[0])), item[1]
                ),
                color=self.color,
                footer=footer,
                thumbnail=self.thumbnail
            ),
            view=None
        )

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
    async def render_ten_roll(
        self : GachaSimulator,
        inter : disnake.Interaction,
        titles : tuple[str, str],
        footer : str,
        scamroll : tuple[str, str]|None
    ) -> None:
        scam_position : int = -1
        i : int
        j : int
        msgs : list[str] = []
        for i in range(0, 11): # 1 by 1 + the final displaying all ten, so 11
            msgs = []
            for j in range(0, i): # display revealed items
                if j >= 10:
                    break
                # write
                msgs.append(
                    "{}{} ".format(
                        self.bot.emote.get(
                            self.RarityStrTable.get(self.result['list'][j][0])
                        ),
                        self.result['list'][j][1]
                    )
                )
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
            await inter.edit_original_message(
                embed=self.bot.embed(
                    author={
                        'name':titles[1].format(inter.author.display_name),
                        'icon_url':inter.author.display_avatar
                    },
                    description=''.join(msgs),
                    color=self.color,
                    footer=footer,
                    thumbnail=(
                        self.thumbnail
                        if (i == 10 and self.scamdata is None)
                        else None
                    )
                ),
                view=None
            )
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
            await inter.edit_original_message(
                embed=self.bot.embed(
                    author={
                        'name':titles[1].format(inter.author.display_name),
                        'icon_url':inter.author.display_avatar
                    },
                    description=''.join(msgs),
                    color=self.color,
                    footer=footer,
                    thumbnail=self.thumbnail
                ),
                view=None
            )

    """render_meme_roll()
    Display the result of a "memerolling" in the given interaction.
    Called by render().
    Note: "Memerolling" refers to the fact of using single tickets until obtaining a SSR.

    Parameters
    --------
    inter: render() interaction
    titles: Tuple of Strings. First (during rolling) and Second element (after the end)
        are used in the embed author name.
    footer: String, embed footer
    """
    async def render_meme_roll(
        self : GachaSimulator,
        inter : disnake.Interaction,
        titles : tuple[str, str],
        footer : str
    ) -> None:
        counter : list[int] = [0, 0, 0]
        msgs : list[str] = []
        # speed selection
        item_count : int
        if self.mode == self.Mode.MEMEB:
            item_count = 5 # by 5 items
        else:
            item_count = 3 # by 3items
        # iterate over rolled items
        i : int
        v : GachaRoll
        for i, v in enumerate(self.result['list']):
            if i > 0 and i % item_count == 0:
                # display once we reached item_count
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        author={
                            'name':titles[0].format(inter.author.display_name),
                            'icon_url':inter.author.display_avatar
                        },
                        description="{} {} ▫️ {} {} ▫️ {} {}\n".format(
                            counter[Rarity.SSR],
                            self.bot.emote.get('SSR'),
                            counter[Rarity.SR],
                            self.bot.emote.get('SR'),
                            counter[Rarity.R],
                            self.bot.emote.get('R')
                        ) + ''.join(msgs),
                        color=self.color,
                        footer=footer,
                    ),
                    view=None
                )
                await asyncio.sleep(1)
                msgs = []
            # add result
            msgs.append("{} {}\n".format(self.bot.emote.get(self.RarityStrTable.get(v[0])), v[1]))
            counter[v[0]] += 1
        # update title
        title : str = (
            titles[1].format(inter.author.display_name, len(self.result['list']))
            if (len(self.result['list']) < 300)
            else "{} sparked".format(inter.author.display_name)
        )
        await inter.edit_original_message(
            embed=self.bot.embed(
                author={
                    'name':title,
                    'icon_url':inter.author.display_avatar
                },
                description="{} {} ▫️ {} {} ▫️ {} {}\n".format(
                    counter[Rarity.SSR],
                    self.bot.emote.get('SSR'),
                    counter[Rarity.SR], self.bot.emote.get('SR'),
                    counter[Rarity.R],
                    self.bot.emote.get('R')
                ) + ''.join(msgs),
                color=self.color,
                footer=footer,
                thumbnail=self.thumbnail
            ),
            view=None
        )

    """render_spark_roll()
    Display the result of a spark in the given interaction.
    Called by render().

    Parameters
    --------
    inter: render() interaction
    titles: Tuple of Strings. Second element is used in the embed author name. First is unused.
    footer: String, embed footer
    """
    async def render_spark_roll(
        self : GachaSimulator,
        inter : disnake.Interaction,
        titles : tuple[str, str],
        footer : str
    ) -> None:
        count : int = len(self.result['list'])
        rate : float = (100 * self.result['detail'][Rarity.SSR] / count)
        msgs : list[str] = []
        rolls : dict[str, int] = self.getSSRList()
        if len(rolls) > 0 and self.complete:
            msgs.append("{} ".format(self.bot.emote.get('SSR')))
            item : str
            for item in rolls: # for each ssr
                msgs.append(item)
                if rolls[item] > 1: # add occurence
                    msgs.append(" x{}".format(rolls[item]))
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        author={
                            'name':titles[1].format(inter.author.display_name, count),
                            'icon_url':inter.author.display_avatar
                        },
                        description=''.join(msgs),
                        color=self.color,
                        footer=footer
                    ),
                    view=None
                )
                await asyncio.sleep(0.75)
                msgs.append(" ")
        # add extra messages for other modes
        amsg : str = ""
        if self.mode == self.Mode.GACHAPIN:
            amsg = "Gachapin stopped after **{}** rolls\n".format(len(self.result['list']))
        elif self.mode == self.Mode.MUKKU:
            amsg = "Mukku stopped after **{}** rolls\n".format(len(self.result['list']))
        elif self.mode == self.Mode.SUPER:
            amsg = "Super Mukku stopped after **{}** rolls\n".format(len(self.result['list']))
        await inter.edit_original_message(
            embed=self.bot.embed(
                author={
                    'name':titles[1].format(inter.author.display_name, count),
                    'icon_url':inter.author.display_avatar
                },
                description="{}{:} {:} ▫️ {:} {:} ▫️ {:} {:}\n{:}\n**{:.2f}%** SSR rate".format(
                    amsg,
                    self.result['detail'][Rarity.SSR],
                    self.bot.emote.get('SSR'),
                    self.result['detail'][Rarity.SR],
                    self.bot.emote.get('SR'),
                    self.result['detail'][Rarity.R],
                    self.bot.emote.get('R'),
                    ''.join(msgs),
                    rate
                ),
                color=self.color,
                footer=footer,
                thumbnail=self.thumbnail
            ),
            view=None
        )

    """render()
    Output the result in a message, via a given disnake Interaction.

    Parameters
    --------
    inter: Interaction to use. Must have been deferred beforehand
    display_mode: Integer. 0=single roll, 1=ten roll, 2=memeroll, 3=ssr list
    titles: Tuple of 2 strings. First and Second embed titles to display
    """
    async def render(
        self : GachaSimulator,
        inter : disnake.Interaction,
        display_mode : int,
        titles : tuple[str, str] = ("{}", "{}")
    ) -> None:
        # check errors in result
        if await self.render_errors(inter):
            return
        # retrieve footer
        footer : str = self.generate_render_footer()
        # get scam roll
        scamroll : tuple[str, str]|None = None
        if self.scamdata is not None:
            scamroll = self.scamRoll()
        # update thumbnail
        await self.updateThumbnail()
        # start and tap button
        view : Tap = Tap(self.bot, owner_id=inter.author.id)
        await inter.edit_original_message(
            embed=self.bot.embed(
                author={
                    'name':titles[0].format(inter.author.display_name),
                    'icon_url':inter.author.display_avatar
                },
                image=self.generate_render_crystal(),
                color=self.color,
                footer=footer
            ),
            view=view
        )
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
    def getSSRList(self : GachaSimulator) -> dict[str, int]:
        rolls : dict[str, int] = {}
        r : GachaRoll
        for r in self.result['list']:
            if r[0] == Rarity.SSR:
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
    async def roulette(
        self : GachaSimulator,
        inter : disnake.Interaction,
        legfest : int = -1,
        realist : bool = False
    ) -> None:
        prev_best : GachaRoll|None = None
        current_time : datetime = self.bot.util.JST()
        # initialize roulette
        roulette : Roulette = Roulette(self.bot, self, current_time, legfest, realist)
        # and spin the wheel!
        roulette.spin_the_wheel()
        # Default message
        await inter.edit_original_message(
            embed=self.bot.embed(
                author={
                    'name':"{} is spinning the Roulette".format(inter.author.display_name),
                    'icon_url':inter.author.display_avatar
                },
                description=roulette.get_message(),
                color=self.color,
                footer=roulette.get_footer(),
                thumbnail=self.ROULETTE
            )
        )
        # Main loop
        while roulette.running:
            # error occured, abort
            if self.exception is not None:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description="An error occured",
                        color=self.color
                    )
                )
                self.bot.logger.pushError("[GACHA] 'simulator roulette' error:", self.exception)
                return
            try:
                start_time : float = time.time() # current time
                await asyncio.sleep(0) # to not risk blocking
                # update the roulette state
                await roulette.update()
                # update thumbnail if it changed
                if prev_best is None or str(self.best) != prev_best:
                    prev_best = str(self.best)
                    await self.updateThumbnail()
                # wait next roulette update, for the remainer of Rarity.ROULETTE_DELAY
                diff : float = self.ROULETTE_DELAY - (time.time() - start_time)
                if diff > 0:
                    await asyncio.sleep(diff)
                # send message
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        author={
                            'name':"{} spun the Roulette".format(inter.author.display_name),
                            'icon_url':inter.author.display_avatar
                        },
                        description=roulette.get_message() + ("" if not roulette.running else "**...**"),
                        color=self.color,
                        footer=roulette.get_footer(),
                        thumbnail=self.thumbnail
                    )
                )
            except Exception as e:
                self.exception = e


class Roulette():

    class Wheel(IntEnum): # Roulette Wheel Zones
        MAX_ROLL : int = 0
        GACHAPIN : int = 1
        BIRTHDAY : int = 2
        ROLL_10 : int = 10
        ROLL_20 : int = 20
        ROLL_30 : int = 30

    NORMAL_ROLLS : list[int] = [Wheel.MAX_ROLL, Wheel.ROLL_10, Wheel.ROLL_20, Wheel.ROLL_30]

    class State(IntEnum): # Roulette states
        JANKEN : int = 0
        NORMAL : int = 1
        GACHAPIN : int = 2
        MUKKU : int = 3
        SUPER_MUKKU : int = 4
        BIRTHDAY_ZONE : int = 5

    __slots__ = (
        "bot", "sim", "fixed_start", "fixed_end", "fixed_start", "forced_3_percent",
        "forced_rolls", "forced_super_mukku", "enable_200_rolls", "enable_janken",
        "max_janken", "double_mukku", "realist", "birthday_zone", "running", "state",
        "current_time", "msgs", "footers", "dice", "rolls", "legfest", "super_mukku",
        "janken_threshold"
    )

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
    def __init__(
        self : Roulette,
        bot : DiscordBot,
        sim : GachaSimulator,
        current_time : datetime,
        legfest : int,
        realist : bool
    ) -> None:
        self.bot : DiscordBot = bot
        self.sim : GachaSimulator = sim
        # get settings
        settings : JSON = self.bot.data.save['gbfdata'].get('roulette', {})
        # copy them here
        # Fixed roll period
        # beginning of fixed rolls
        self.fixed_start : datetime = current_time.replace(
            year=2000 + settings.get('year', 24),
            month=settings.get('month', 1),
            day=settings.get('day', 1),
            hour=5,
            minute=0,
            second=0,
            microsecond=0
        )
        # end of fixed rolls (one day later)
        self.fixed_end : datetime = self.fixed_start + timedelta(days=1, seconds=0)
        # move start 36000s or 10h early
        self.fixed_start -= timedelta(seconds=36000)
        # Fixed period forced 3 percent
        self.forced_3_percent : bool = settings.get('forced3%', True)
        # Fixed period roll count
        self.forced_rolls : int = settings.get('forcedroll', 100)
        # Fixed period forced Super Mukku
        self.forced_super_mukku : bool = settings.get('forcedsuper', True)
        # Enable 200 rolls as the max
        self.enable_200_rolls : bool = settings.get('enable200', False)
        # Enable the Rock Paper Scissor
        self.enable_janken : bool = settings.get('enablejanken', False)
        # Maximum number of Rock Paper Scissor in a row
        self.max_janken : bool = settings.get('enablejanken', False)
        # Enable double Mukku
        self.double_mukku : bool = settings.get('doublemukku', False)
        # Use realist mode (if allowed)
        self.realist : bool = realist and settings.get('realist', False)
        # Add Birthday Zone on the wheel
        self.birthday_zone : bool = settings.get('birthday', False)

        # variables and flags
        self.running : bool = True
        self.state : int = self.State.NORMAL
        self.current_time : datetime = current_time
        self.msgs : list[str] = [] # message strings container
        self.footers : list[str] = [] # footer strings container
        self.dice : int = 0
        self.rolls : int = 0
        self.legfest : int = legfest
        self.super_mukku : bool = False
        self.janken_threshold : int = 0

    """get_message()
    Return an usable embed description

    Returns
    --------
    str: The message
    """
    def get_message(self : Roulette) -> str:
        return "".join(self.msgs)

    """get_footer()
    Return an usable embed footer

    Returns
    --------
    str: The footer
    """
    def get_footer(self : Roulette) -> str:
        return "".join(self.footers)

    """SSRList2StrList()
    Convert a SSR list to a list of string to be used by roulette()

    Parameters
    --------
    ssrs: Dict of rolled gacha items (name and occurences)

    Returns
    --------
    list: List of string (to be combined with join())
    """
    def SSRList2StrList(self : Roulette, ssrs : dict[str, int]) -> list[str]:
        if len(ssrs) > 0:
            tmp : list[str] = [str(self.bot.emote.get('SSR')), " "]
            item : str
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
    def generated_fixed_rolls(self : Roulette) -> None:
        self.msgs = [
            "{} {} :confetti_ball: :tada: Guaranteed **{} 0 0** R O L L S :tada: :confetti_ball: {} {}\n".format(
                self.bot.emote.get('crystal'),
                self.bot.emote.get('crystal'),
                self.forced_rolls // 100,
                self.bot.emote.get('crystal'),
                self.bot.emote.get('crystal')
            )
        ]
        self.stats = self.State.NORMAL
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
    def spin_the_wheel(self : Roulette) -> None:
        # Check fixed period
        if self.fixed_start <= self.current_time < self.fixed_end:
            self.generated_fixed_rolls()
            return
        # Add possible wheel results depending on settings
        wheel : list[tuple[int, int|None]] = []
        wheel.append((self.Wheel.GACHAPIN, 800)) # gachapin 8%
        if self.birthday_zone:
            wheel.append((self.Wheel.BIRTHDAY, 500)) # birthday 5%
        if self.realist:
            wheel.append((self.Wheel.ROLL_30, 2000)) # 30 rolls 20%
            wheel.append((self.Wheel.ROLL_20, None))
        else:
            wheel.append((self.Wheel.MAX_ROLL, 200)) # hundred 2%
            wheel.append((self.Wheel.ROLL_30, 2000)) # 30 rolls 20%
            wheel.append((self.Wheel.ROLL_20, 3500)) # 20 rolls 35%
            wheel.append((self.Wheel.ROLL_10, None))
        # Calculate minimum value to get janken
        zone : tuple[int, int|None]
        for zone in wheel:
            if zone[0] in self.NORMAL_ROLLS:
                break # stop at "normal" rolls
            self.janken_threshold += zone[1]
        # Now spin the wheel
        self.dice = random.randint(1, 10000) # roulette roll
        threshold : int = 0
        # Look for what result we got in variable d
        for zone in wheel:
            if zone[1] is not None and self.dice > threshold + zone[1]: # over threshold
                threshold += zone[1] # remove and iterate
                continue
            match zone[0]:
                case self.Wheel.MAX_ROLL:
                    if self.enable_200_rolls: # forced 200 rolls
                        self.msgs = [
                            "{} {} :confetti_ball: :tada: **2 0 0 R O L L S** :tada: :confetti_ball: {} {}\n".format(
                                self.bot.emote.get('crystal'),
                                self.bot.emote.get('crystal'),
                                self.bot.emote.get('crystal'),
                                self.bot.emote.get('crystal')
                            )
                        ]
                        self.rolls = 200
                    else: # forced 100 rolls
                        self.msgs = [":confetti_ball: :tada: **100** rolls!! :tada: :confetti_ball:\n"]
                        self.rolls = 100
                case self.Wheel.GACHAPIN:
                    self.msgs = ["**Gachapin Frenzy** :four_leaf_clover:\n"]
                    self.rolls = -1
                    self.state = self.State.GACHAPIN
                case self.Wheel.BIRTHDAY: # Birthday zone
                    self.msgs = [":birthday: You got the **Birthday Zone** :birthday:\n"]
                    self.rolls = -1
                    self.state = self.State.BIRTHDAY_ZONE
                case self.Wheel.ROLL_30:
                    self.msgs = ["**30** rolls! :clap:\n"]
                    self.rolls = 30
                case self.Wheel.ROLL_20:
                    self.msgs = ["**20** rolls :open_mouth:\n"]
                    self.rolls = 20
                case self.Wheel.ROLL_10:
                    self.msgs = ["**10** rolls :pensive:\n"]
                    self.rolls = 10
            break
        # to disable janken if needed
        if not self.enable_janken and self.state == self.State.JANKEN:
            self.state = self.State.NORMAL

    """janken_event()
    Simulate the Rock Paper Scissor event (if enabled).
    Called by update().
    """
    async def janken_event(self : Roulette) -> None:
        # only if enabled and we rolled above the threshold and we got lucky (33% chance)
        if self.enable_janken and self.dice >= self.janken_threshold and random.randint(0, 2) > 0:
            # simulate basic rock paper scisor
            a : int
            b : int
            while True:
                a = random.randint(0, 2)
                b = random.randint(0, 2)
                if a != b:
                    break
            # Add result
            self.msgs.append("You got **{}**, Gachapin got **{}**".format(self.RPS[a], self.RPS[b]))
            # Check the win condition
            if (a == 1 and b == 0) or (a == 2 and b == 1) or (a == 0 and b == 2):
                self.msgs.append(" :thumbsup:\n")
                self.msgs.append("You **won** rock paper scissor,")
                self.msgs.append("your rolls are **doubled** :confetti_ball:\n")
                self.rolls = self.rolls * 2 # double roll
                roll_cap : int = (200 if self.enable_200_rolls else 100) # maximum roulette rolls
                if self.rolls > roll_cap: # cap roll
                    self.rolls = roll_cap
                    self.max_janken = 0 # cancel other jankens
                else:
                    self.max_janken -= 1
                if self.max_janken == 0:
                    self.state = self.State.NORMAL # go to normal roll
            else:
                self.msgs.append(" :pensive:\n")
                self.state = self.State.NORMAL # go to normal roll
        else:
            self.state = self.State.NORMAL # go to normal roll

    """normal_event()
    Simulate standard rolls.
    Called by update().
    """
    async def normal_event(self : Roulette) -> None:
        # Generate rolls
        await self.sim.generate(self.rolls, self.legfest)
        # Number of SSR
        count : int = len(self.sim.result['list'])
        # Result SSR rate
        rate : float = (100 * self.sim.result['detail'][2] / count)
        # Get ssr list
        tmp : list[str] = self.SSRList2StrList(self.sim.getSSRList())
        # Update the footer
        self.footers = self.sim.bannerIDtoFooter(["{}% SSR rate".format(self.sim.result['rate'])])
        # Rarity counter line
        rarity : int
        for rarity in reversed(Rarity):
            self.msgs.append(str(self.sim.result['detail'][rarity]))
            self.msgs.append(" ")
            self.msgs.append(str(self.bot.emote.get(
                {
                    Rarity.SSR:'SSR',
                    Rarity.SR:'SR',
                    Rarity.R:'R'
                }.get(rarity, rarity))))
            if rarity > Rarity.R:
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
            self.state = self.State.SUPER_MUKKU # go to Super Mukku
        else:
            self.running = False # Over

    """gachapin_mukku_event()
    Simulate Gachapin/Mukku/Super Mukku rolls.
    Called by update().


    Parameters
    --------
    sim_mode: String, The simulator mode to use. It must corresponds to the state.
        The behavior is undefined if there is a mismatch
        (example, self.state == self.State.GACHAPIN but sim_mode = "mukku")
    """
    async def gachapin_mukku_event(self : Roulette, sim_mode : str) -> None:
        # Generate rolls
        self.sim.changeMode(sim_mode)
        await self.sim.generate(300, self.legfest)
        # Number of SSR
        count : int = len(self.sim.result['list'])
        # Result SSR rate
        rate : float = (100 * self.sim.result['detail'][Rarity.SSR] / count)
        # Get ssr list
        tmp : list[str] = self.SSRList2StrList(self.sim.getSSRList())
        # Update the footer (if gachapin)
        if self.state == self.State.GACHAPIN:
            self.footers = self.sim.bannerIDtoFooter(["{}% SSR rate".format(self.sim.result['rate'])])
        # Roll line
        match self.state:
            case self.State.GACHAPIN:
                self.msgs.append("Gachapin ▫️ **")
            case self.State.MUKKU:
                self.msgs.append(":confetti_ball: Mukku ▫️ **")
            case self.State.SUPER_MUKKU:
                self.msgs.append(":confetti_ball: **Super Mukku** ▫️ **")
        self.msgs.append(str(count))
        self.msgs.append("** rolls\n")
        # Rarity counter line
        rarity : int
        for rarity in reversed(Rarity):
            self.msgs.append(str(self.sim.result['detail'][rarity]))
            self.msgs.append(" ")
            self.msgs.append(str(self.bot.emote.get(
                {
                    Rarity.SSR:'SSR',
                    Rarity.SR:'SR',
                    Rarity.R:'R'
                }.get(rarity, rarity))))
            if rarity > Rarity.R:
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
            case self.State.GACHAPIN:
                # depending on how many rolls we got, and some rng, we decide on the next step
                if count == 10 and random.randint(1, 100) <= 99:
                    self.state = self.State.MUKKU
                elif count == 20 and random.randint(1, 100) <= 60:
                    self.state = self.State.MUKKU
                elif count == 30 and random.randint(1, 100) <= 30:
                    self.state = self.State.MUKKU
                elif random.randint(1, 100) <= 3:
                    self.state = self.State.MUKKU
                else:
                    self.running = False # Over
            case self.State.MUKKU:
                if self.double_mukku: # Double mukku enabled
                    if random.randint(1, 100) < 25: # roll a dice
                        self.double_mukku = False # disable double mukku and wait to go to mukku again
                        # Note: stay on this state
                    else:
                        self.running = False # Over
                else:
                    self.running = False # Over
            case self.State.SUPER_MUKKU:
                self.running = False # Over

    """birthday_event()
    Simulate the Birthday Zone of the March 2024 Anniversary Roulette
    Called by update().
    """
    async def birthday_event(self : Roulette) -> None:
        d : int = random.randint(1, 10000) # roll another dice
        self.running = False # we'll stop here
        # Decide on event
        if d <= 2000:
            self.rolls = 100
        elif d <= 3400:
            self.rolls = 50
        elif d <= 4800:
            self.rolls = 60
        elif d <= 6200:
            self.rolls = 70
        elif d <= 7600:
            self.rolls = 80
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
    async def update(self : Roulette) -> None:
        if self.running:
            match self.state:
                case self.State.JANKEN:
                    await self.janken_event()
                case self.State.NORMAL: # normal rolls
                    await self.normal_event()
                case self.State.GACHAPIN: # gachapin
                    await self.gachapin_mukku_event('gachapin')
                case self.State.MUKKU:
                    await self.gachapin_mukku_event('mukku')
                case self.State.SUPER_MUKKU:
                    await self.gachapin_mukku_event('supermukku')
                case self.State.BIRTHDAY_ZONE:
                    await self.birthday_event()
            # tweak footer
            if self.realist:
                self.footers.append(" ▫️ Realist")
