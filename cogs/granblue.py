from __future__ import annotations
import disnake
from disnake.ext import commands
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.network import RequestResult
    from components.gacha import CurrentGacha
    from components.singleton import Score
    from components.ranking import GWDBSearchResult
    # Type Aliases
    type NewsResult = list[str]
    type ExtraDropData = list[None|str]
from views import BaseView
from views.url_button import UrlButton
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from bs4 import element as bs4element
from urllib.parse import quote, unquote
import html
import math

# ----------------------------------------------------------------------
# GranblueFantasy Cog
# ----------------------------------------------------------------------
# All other Granblue Fantasy-related commands
# ----------------------------------------------------------------------


class GranblueFantasy(commands.Cog):
    """Granblue Fantasy Utility."""
    COLOR : int = 0x34aeeb
    COLOR_NEWS : int = 0x00b07b
    # Constants
    SUMMON_ELEMENTS : list[str] = ['fire','water','earth','wind','light','dark','misc']
    DEFAULT_NEWS : int = 9081
    EXTRA_DROPS_TABLE : dict[str, str] = { # quest : element
        'Tiamat':'wind', 'Colossus':'fire', 'Leviathan':'water',
        'Yggdrasil':'earth', 'Aversa':'light', 'Luminiera':'light', 'Celeste':'dark'
    }
    XP_TABLE : list[None|str] = [
        None, 30, 70, 100, 120, 140, 160, 180, 200, 220,
        240, 260, 280, 300, 350, 400, 450, 500, 550, 600,
        650, 700, 800, 900, 1000, 1100, 1200, 1300, 1400,
        1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2400,
        2600, 2800, 3000, 3200, 3400, 3600, 3800, 4000, 4200,
        4400, 4600, 4800, 5000, 5250, 5500, 5750, 6000, 6250,
        6500, 6750, 7000, 7250, 7500, 7800, 8100, 8400, 8700,
        9000, 9500, 10000, 10500, 11000, 11500, 12000, 12500,
        13000, 13500, 14000, 14500, 15000, 15500, 16000, 50000,
        20000, 21000, 22000, 23000, 24000, 25000, 26000, 27000,
        100000, 150000, 200000, 250000, 300000, 350000, 400000,
        450000, 500000, 500000, 1000000, 1000000, 1200000, 1200000,
        1200000, 1200000, 1200000, 1250000, 1250000, 1250000,
        1250000, 1250000, 1300000, 1300000, 1300000, 1300000,
        1300000, 1350000, 1350000, 1350000, 1350000, 1350000,
        1400000, 1400000, 1400000, 1400000, 1400000, 1450000,
        1450000, 1450000, 1450000, 1450000, 1500000, 1500000,
        1500000, 1500000, 1500000, 1550000, 1550000, 1550000,
        1550000, 1550000, 1600000, 1600000, 1600000, 1600000,
        1600000, 1650000, 1650000, 1650000, 1650000, 0
    ]
    GBF_ICON : str = "https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"

    __slots__ = ("bot")

    def __init__(self : GranblueFantasy, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    def startTasks(self : GranblueFantasy) -> None:
        if self.bot.isProduction():
            self.bot.runTask('granblue:watcher', self.granblue_watcher)

    """granblue_watcher()
    Bot Task checking for new content related to GBF
    """
    async def granblue_watcher(self : GranblueFantasy) -> None:
        maint_check : bool = False # False = no maintenance on going, True = maintenance on going
        v : int|None = None
        await asyncio.sleep(30)
        while True:
            # we only check every 5 minutes
            try:
                t : int = int(self.bot.util.UTC().timestamp()) % 300
                await asyncio.sleep(355 - t)
                if not self.bot.running:
                    return
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue:watcher' Task Cancelled")
                return

            try: # news checker
                news = await self.checkNews()
                if len(news) > 0:
                    self.bot.logger.push(
                        f"[GBF] {len(news)} new posts on the main website",
                        send_to_discord=False
                    )
                for n in news: # for each news
                    try:
                        title = self.bot.net.translate(n[1]) # translate title
                        if "Error 500" in title and "Server Error" in title:
                            raise Exception()
                        footer = "Title from Google Translate"
                    except:
                        title = n[1]
                        footer = ""
                    await self.bot.sendMulti(
                        self.bot.channel.announcements,
                        embed=self.bot.embed(
                            author={
                                'name':"Granblue Fantasy",
                                'icon_url':self.GBF_ICON
                            },
                            description=f"[{title}]({n[0]})",
                            image=n[2],
                            footer=footer,
                            color=self.COLOR_NEWS
                        )
                    )
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue:watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue:watcher (News)' Task Error:", e)

            try: # update check
                if maint_check: # maintenance was on going
                    if not await self.bot.net.gbf_maintenance(check_maintenance_end=True): # is it not anymore?
                        maint_check = False # maintenance ended
                        await self.bot.net.gbf_version() # update version
                        self.bot.data.save['gbfupdate'] = False
                        self.bot.data.pending = True
                    else:
                        continue # maintenance still on going
                else:
                    # check if there is a maintenance
                    maint_check = await self.bot.net.gbf_maintenance(check_maintenance_end=True)
                # check for updates if no maintenance
                if (not maint_check
                        and (
                            self.bot.data.save['gbfupdate'] is True
                            or (await self.bot.net.gbf_version()) == 3
                        )):
                    v = self.bot.data.save['gbfversion']
                    self.bot.logger.push(
                        f"[GBF] The game has been updated to version {v}",
                        send_to_discord=False
                    )
                    self.bot.data.save['gbfupdate'] = False
                    self.bot.data.pending = True
                    await self.bot.send(
                        "debug",
                        embed=self.bot.embed(
                            author={
                                'name':"Granblue Fantasy",
                                'icon_url':self.GBF_ICON
                            },
                            description="Game has been updated to version `{} ({})`".format(
                                v,
                                self.bot.util.version2str(v)
                            ),
                            color=self.COLOR
                        )
                    )
                    await self.bot.sendMulti(
                        self.bot.channel.announcements,
                        embed=self.bot.embed(
                            author={
                                'name':"Granblue Fantasy",
                                'icon_url':self.GBF_ICON
                            },
                            description="Game has been updated",
                            color=self.COLOR
                        )
                    )
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue:watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue:watcher (Update)' Task Error:", e)

            if maint_check: # stop here if there is a maintenance
                continue

            try: # game news
                await self.checkGameNews()
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue:watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue:watcher (checkGameNews)' Task Error:", e)

            try: # 4koma news
                await self.check4koma()
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue:watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue:watcher (4koma)' Task Error:", e)

    """fix_news_thumbnail()
    Fix a thumbnail url used by checkGameNews()

    Parameters
    ----------
    thumbnail: String, an url

    Returns
    --------
    str: The thumbnail url
    """
    def fix_news_thumbnail(self : GranblueFantasy, thumbnail : str|None) -> str|None:
        if thumbnail is not None and "granbluefantasy" not in thumbnail:
            if thumbnail == "":
                thumbnail = None
            elif not thumbnail.startswith("https://"):
                if thumbnail[0] == "/":
                    thumbnail = "https://prd-game-a-granbluefantasy.akamaized.net" + thumbnail
                else:
                    thumbnail = "https://prd-game-a-granbluefantasy.akamaized.net/" + thumbnail
        return thumbnail

    """fix_news_link()
    Fix a news url used by checkGameNews()

    Parameters
    ----------
    link: String, a news url

    Returns
    --------
    str: The news url
    """
    def fix_news_link(self : GranblueFantasy, link : str|None) -> str|None:
        if link is not None and not link.startswith("https://"):
            if link == "":
                link = None
            elif link[0] == "/":
                link = "https://game.granbluefantasy.jp" + link
            else:
                link = "https://game.granbluefantasy.jp/" + link
        return link

    """compute_news_description_character_limit()
    Return the character limit used by checkGameNews(), given a specific news title

    Parameters
    ----------
    title: String, the news title

    Returns
    --------
    int: The character limit
    """
    def compute_news_description_character_limit(self : GranblueFantasy, title : str) -> int:
        limit : int
        if (title.startswith('Grand Blues #')
                or 'Surprise Special Draw Set On Sale' in title
                or 'Star Premium Draw Set On Sale' in title):
            # grand blues, suptix and scam news
            limit = 0 # 0 = we'll ignore those news
        elif title.endswith(" Concluded"): # event end
            limit = 40
        elif title.endswith(" Premium Draw Update"): # gacha update
            limit = 100
        elif title.endswith(" Maintenance Completed"): # maintenance end
            limit = 50
        elif title.endswith(" Added to Side Stories"): # new side story
            limit = 30
        elif title.endswith(" Underway!"): # event start
            limit = 30
        else:
            limit = 250
        return limit

    """parse_maintenance_from_news()
    Read a news title and description and, if it's a Maintenance news,
    attempt to set the bot maintenance state to the date found in the news body.

    Parameters
    ----------
    title: String, the news title
    description: String, the news description
    """
    def parse_maintenance_from_news(self : GranblueFantasy, title : str, description : str) -> None:
        # we check for specific titles
        if title.endswith(' Maintenance Announcement') and "aintenance is scheduled for " in description:
            try:
                # break down the first line by words
                words : list[str] = description.split(' (JST)', 1)[0].split(" ")
                state : bool = False
                sections : list[list[str]] = []
                # read the words we look for (the dates)
                w : str
                for w in words:
                    if not state:
                        if w.isdigit() or w in ("noon", "midnight"):
                            state = True
                            sections.append(w)
                    elif state:
                        if "-" in w:
                            sections.extend(w.split("-"))
                        elif "–" in w:
                            sections.extend(w.split("–"))
                        else:
                            sections.append(w.replace(',', ''))
                # parse the start and end hour
                i : int = 0
                hours : list[int] = [0, 0]
                for j in range(2):
                    match sections[i]:
                        case "noon":
                            hours[j] = 12
                        case "midnight":
                            hours[j] = 0
                        case _:
                            hours[j] = int(sections[i])
                            if sections[1] == "p.m.":
                                hours[j] += 12
                                i += 1
                            elif sections[1] == "a.m.":
                                i += 1
                    i += 1
                # parse the day, month and year
                day : int = 0
                month : int = 0
                year : int = 0
                for j in range(i, i + 3):
                    if sections[j].isdigit():
                        if len(sections[j]) == 4:
                            year = int(sections[j])
                        else:
                            day = int(sections[j])
                    else:
                        match sections[j].lower():
                            case 'jan': month = 1
                            case 'feb': month = 2
                            case 'mar': month = 3
                            case 'apr': month = 4
                            case 'may': month = 5
                            case 'jun': month = 6
                            case 'jul': month = 7
                            case 'aug': month = 8
                            case 'sep': month = 9
                            case 'oct': month = 10
                            case 'nov': month = 11
                            case 'dec': month = 12
                            case _:
                                raise Exception(f"Month Error for '{sections[j]}'")
                # set in memory
                self.bot.data.save['maintenance']['time'] = datetime.now().replace(
                    year=year,
                    month=month,
                    day=day,
                    hour=hours[0],
                    minute=0,
                    second=0,
                    microsecond=0
                )
                self.bot.data.save['maintenance']['duration'] = hours[1] - hours[0]
                self.bot.data.save['maintenance']['state'] = True
                self.bot.data.pending = True
            except Exception as se:
                self.bot.logger.pushError("[Granblue] 'checkGameNews (Maintenance)' Error:", se)

    """checkGameNews()
    Coroutine checking for new in-game news, to post them in announcement channels
    """
    async def checkGameNews(self : GranblueFantasy) -> None:
        ii : int
        initialization : bool
        ncheck : int
        if 'game_news' not in self.bot.data.save['gbfdata']: # init data
            self.bot.data.save['gbfdata']['game_news'] = [self.DEFAULT_NEWS]
            ii = self.DEFAULT_NEWS - 40
            initialization = True
            ncheck = 10000
        else:
            ii = self.bot.data.save['gbfdata']['game_news'][0] # ii is the iterator
            initialization = False
            # max number of check
            ncheck = 10 + max(
                self.bot.data.save['gbfdata']['game_news']
            ) - min(self.bot.data.save['gbfdata']['game_news'])
        # HTML tag substitutions
        tags : dict[str, str] = {
            "br":"\n",
            "/br":"\n",
            "b":"**",
            "/b":"**",
            "i":"*",
            "/i":"*",
            "u":"__",
            "/u":"__",
            "tr":"\n",
            "div":"\n",
            "/div":"\n",
            "li":"- ",
            "/li":"\n",
            "/ul":"\n",
        }
        # build a list of id to check
        to_process : list[int] = [
            i for i in range(ii, ii + ncheck)
            if i not in self.bot.data.save['gbfdata']['game_news']
        ]
        # prepare cookies
        self.bot.net.client.cookie_jar.update_cookies({"ln":"2"})
        try:
            await self.bot.net.request("https://game.granbluefantasy.jp/#top") # make a request to set cookies
        except: # try twice in case of lag
            await self.bot.net.request("https://game.granbluefantasy.jp/#top")
        # loop over this list
        news : list[int] = []
        err : int = 0
        for ii in to_process:
            # request news patch
            data : RequestResult = await self.bot.net.requestGBF_offline(
                f"news/news_detail/{ii}",
                expect_JSON=True
            )
            if data is None:
                err += 1
                if initialization and err >= 30:
                    break
                continue
            elif data[0]['id'] == str(ii): # check if id matches
                try:
                    err = 0
                    news.append(ii) # append id to news list
                    if not initialization:
                        # process the news content
                        # determine the character limit
                        limit : int = self.compute_news_description_character_limit(data[0]['title'])
                        if limit == 0: # Null, skip
                            continue
                        # Breakdown the html
                        content : list[str] = self.bot.util.breakdownHTML(data[0]['contents'])
                        elements : list[str] = []
                        link : str|None = None
                        thumbnail : str|None = None
                        # Iterate over strings
                        i : int
                        is_comment : bool = False
                        for i in range(0, len(content)):
                            if i & 1 == 1: # Odd, it's a tag
                                tag : str = content[i].split(' ', 1)[0]
                                if is_comment:
                                    if tag == "/comment":
                                        is_comment = False
                                else:
                                    if tag == "comment":
                                        is_comment = True
                                    elif tag in tags:
                                        # known tag, replace with corresponding string (see 60 lines above)
                                        elements.append(tags[tag])
                                    else: # not a known tag
                                        if elements[-1].strip() != "": # last element wasn't empty, we add a space
                                            elements.append(" ")
                                        if thumbnail is None and tag == "img": # thumbnail detection
                                            thumbnail = content[i].split('src="', 1)[1].split('"', 1)[0]
                                        elif link is None and tag == "a": # url detection
                                            link = content[i].split('href="', 1)[1].split('"', 1)[0]
                            else: # even, it's text
                                if not is_comment:
                                    tmp : str = content[i].strip()
                                    if i > 0 and tmp == "" and tmp == elements[-1].strip():
                                        # don't insert spaces if the previous string is
                                        # empty or possibly containing white spaces
                                        pass
                                    else:
                                        elements.append(content[i])
                        # Remove extra new lines
                        i = 0
                        counter : int = 0
                        while i < len(elements):
                            if elements[i] == '\n':
                                if i == 0 or counter >= 2:
                                    elements.pop(i)
                                else:
                                    counter += 1
                                    i += 1
                            else:
                                counter = 0
                                i += 1
                        # Adjust thumbnail url
                        thumbnail = self.fix_news_thumbnail(thumbnail)
                        # Adjust link url
                        link = self.fix_news_link(link)
                        # build description
                        description : list[str] = []
                        length : int = 0
                        e : str
                        for e in elements:
                            description.append(e)
                            length += len(description[-1]) + 1
                            if length >= limit:
                                if len(description) > 0:
                                    if description[-1] == "- " or description[-1] == "\n":
                                        description.pop()
                                description.append(" [...]")
                                break
                        if len(description) == 0:
                            description.append("")
                        description.append(
                            (
                                "\n[News Link](https://game.granbluefantasy.jp"
                                "/#news/detail/{}/2/1/1)"
                            ).format(ii)
                        )
                        description = "".join(description)
                        # send news
                        await self.bot.sendMulti(
                            self.bot.channel.announcements,
                            embed=self.bot.embed(
                                title=data[0]['title']
                                    .replace('<br>', ' ')
                                    .replace('<b>', '**')
                                    .replace('</b>', '*')
                                    .replace('<i>', '*')
                                    .replace('</i>', '*'),
                                description=description,
                                url=link,
                                image=thumbnail,
                                timestamp=self.bot.util.UTC(),
                                thumbnail=self.GBF_ICON,
                                color=self.COLOR
                            ),
                            publish=True
                        )
                        # detect maintenance to automatically set the date
                        self.parse_maintenance_from_news(data[0]['title'], description)
                except Exception as e:
                    self.bot.logger.pushError("[Granblue] 'checkGameNews' Error:", e)
                    return
        if len(news) > 0: # add processed news
            self.bot.data.save['gbfdata']['game_news'] = self.bot.data.save['gbfdata']['game_news'] + news
            self.bot.data.save['gbfdata']['game_news'].sort()
            if len(self.bot.data.save['gbfdata']['game_news']) > 25: # remove old ones
                start : int = max(0, len(self.bot.data.save['gbfdata']['game_news']) - 25)
                self.bot.data.save['gbfdata']['game_news'] = self.bot.data.save['gbfdata']['game_news'][start:]
            self.bot.data.pending = True
            self.bot.logger.push(f"[GBF] {len(news)} new in-game News", send_to_discord=False)

    """checkNews()
    Check for GBF news on the main site and update the save data.

    Returns
    --------
    list: List of new news
    """
    async def checkNews(self : GranblueFantasy) -> list:
        res : list[NewsResult] = [] # news list
        ret : list[NewsResult] = [] # new news articles to return
        # retrieve news page
        data : RequestResult = await self.bot.net.request("https://granbluefantasy.jp/news/index.php")
        if data is not None:
            soup : BeautifulSoup = BeautifulSoup(data, 'html.parser')
            # extract articles
            at : bs4element.ResultSet = soup.find_all("article", class_="scroll_show_box")
            try:
                a : bs4element.Tag
                for a in at:
                    # get content and url
                    inner : bs4element.Tag = a.findChildren("div", class_="inner", recursive=False)[0]
                    section : bs4element.Tag = inner.findChildren("section", class_="content", recursive=False)[0]
                    h1 : bs4element.Tag = section.findChildren("h1", recursive=False)[0]
                    url : bs4element.Tag = h1.findChildren("a", class_="change_news_trigger", recursive=False)[0]
                    # retrieve news image (if any)
                    try:
                        mb25 : bs4element.Tag = section.findChildren(
                            "div",
                            class_="mb25",
                            recursive=False
                        )[0]
                        href : bs4element.Tag = mb25.findChildren(
                            "a",
                            class_="change_news_trigger",
                            recursive=False
                        )[0]
                        img : str = href.findChildren("img", recursive=False)[0].attrs['src']
                        if not img.startswith('http'):
                            if img.startswith('/'):
                                img = 'https://granbluefantasy.jp' + img
                            else:
                                img = 'https://granbluefantasy.jp/' + img
                    except:
                        img = None
                    # add to list
                    res.append([url.attrs['href'], url.text, img])

                if 'news_url' in self.bot.data.save['gbfdata']: # if data exists in memory
                    foundNew : bool = False
                    i : int
                    j : int
                    for i in range(0, len(res)): # process detected news
                        found : bool = False
                        for j in range(0, len(self.bot.data.save['gbfdata']['news_url'])): # check if it exists
                            if res[i][0] == self.bot.data.save['gbfdata']['news_url'][j][0]:
                                found = True
                                break
                        if not found: # if it doesn't
                            ret.append(res[i]) # add to list
                            foundNew = True
                    if foundNew: # update memory data
                        self.bot.data.save['gbfdata']['news_url'] = res
                        self.bot.data.pending = True
                else: # update memory data
                    self.bot.data.save['gbfdata']['news_url'] = res
                    self.bot.data.pending = True
            except:
                pass
        return ret

    """check4koma()
    Check for new GBF grand blues
    """
    async def check4koma(self : GranblueFantasy) -> None:
        if '4koma' not in self.bot.data.save['gbfdata']:
            self.bot.data.save['gbfdata']['4koma'] = 2925
        i : int = self.bot.data.save['gbfdata']['4koma']
        i += 1
        while True:
            url : str = (
                "https://prd-game-a-granbluefantasy.akamaized.net/"
                "assets_en/img/sp/assets/comic/thumbnail/thum_{}.png"
            ).format(str(i).zfill(5))
            if await self.bot.net.request(url, rtype=self.bot.net.Method.HEAD) is None:
                i -= 1
                break
            else:
                i += 1
        if i > self.bot.data.save['gbfdata']['4koma']:
            self.bot.data.save['gbfdata']['4koma'] = i
            self.bot.data.pending = True
            await self.bot.sendMulti(
                self.bot.channel.announcements,
                embed=self.bot.embed(
                    title="Episode " + str(i),
                    url=(
                        "https://prd-game-a-granbluefantasy.akamaized.net/"
                        "assets/img/sp/assets/comic/episode/episode_{}.jpg"
                    ).format(i),
                    image=(
                        "https://prd-game-a-granbluefantasy.akamaized.net/"
                        "assets_en/img/sp/assets/comic/thumbnail/thum_{}.png"
                    ).format(str(i).zfill(5)),
                    color=self.COLOR
                ),
                publish=True
            )

    """checkExtraDrops()
    Check for GBF extra drops

    Returns
    --------
    list: List of ending time and element. Element is None if no extra drops is on going
    """
    async def checkExtraDrops(self : GranblueFantasy) -> ExtraDropData|None:
        try:
            c : datetime = self.bot.util.JST()
            # retrieve data (if it exists)
            extra : ExtraDropData|None = self.bot.data.save['gbfdata'].get('extradrop', None)
            if extra is None or c > extra[0]: # outdated/not valid
                # call endpoint
                r : RequestResult = await self.bot.net.requestGBF("rest/quest/adddrop_info", expect_JSON=True)
                if r is None: # no extra
                    # next check is in 5min, element set to None to make it NOT VALID
                    self.bot.data.save['gbfdata']['extradrop'] = [c + timedelta(seconds=300), None]
                    self.bot.data.pending = True
                    return None
                else:
                    data : ExtraDropData = [None, None]
                    data[0] = datetime.strptime( # store end time
                        r['message_info']['ended_at'].replace(
                            ' (JST)', ''
                        ).replace(
                            'a.m.', 'AM'
                        ).replace(
                            'p.m.', 'PM'
                        ),
                        '%I:%M %p, %b %d, %Y'
                    )
                    e : dict[str, str]
                    for e in r['quest_list']: # check quest name for element match
                        cs : list[str] = e['quest_name'].split(' ')
                        s : str
                        for s in cs:
                            data[1] : str|None = self.EXTRA_DROPS_TABLE.get(s, None)
                            if data[1] is not None:
                                break
                        if data[1] is not None:
                            break
                    # set in memory
                    self.bot.data.save['gbfdata']['extradrop'] = data
                    self.bot.data.pending = True
                    return data
            elif extra[1] is not None: # if valid
                return extra
        except:
            pass
        return None

    """getGBFInfoTimers()
    Generate a string containing various timers (to maintenance, next gacha, etc...).
    Used by /gbf info and /gbf schedule.

    Parameters
    --------
    inter: Valid Disnake interaction. Required for getNextBuff().
    current_time: Current time datetime in JST. Required for extra drop and stream timers.

    Returns
    --------
    str: Resulting string. Intended to be appended to an embed description.
    """
    async def getGBFInfoTimers(
        self : GranblueFantasy,
        inter : disnake.ApplicationCommandInteraction,
        current_time : datetime
    ) -> str:
        output : list[str] = []
        # output will contain strings before .join()
        # in this function, we simply call various info functions
        # from various cog and component
        # and compile the result in one big string
        try:
            buf : str = (await self.bot.net.gbf_maintenance_status())[0]
            if len(buf) > 0:
                output.append(str(self.bot.emote.get('cog')))
                output.append(' ')
                output.append(buf)
                output.append('\n')
        except:
            pass
        try:
            gdata : CurrentGacha = await self.bot.gacha.get()
            if len(gdata) > 0:
                output.append(
                    "{} Current {} ends in **{}**".format(
                        self.bot.emote.get('SSR'),
                        self.bot.util.command2mention('gbf gacha'),
                        self.bot.util.delta2str(gdata[1]['time'] - gdata[0], 2)
                    )
                )
                if gdata[1]['time'] != gdata[1]['timesub']:
                    output.append(
                        " (Spark period ends in **{}**)".format(
                            self.bot.util.delta2str(gdata[1]['timesub'] - gdata[0], 2)
                        )
                    )
                output.append('\n')
        except:
            pass
        try:
            buf = self.bot.get_cog('GuildWar').getGWState()
            if len(buf) > 0:
                output.append(buf)
                output.append(" (")
                output.append(self.bot.util.command2mention("gw time"))
                output.append(")\n")
        except:
            pass

        try:
            buf = self.bot.get_cog('DreadBarrage').getBarrageState()
            if len(buf) > 0:
                output.append(buf)
                output.append(" (")
                output.append(self.bot.util.command2mention("db time"))
                output.append(")\n")
        except:
            pass
        try:
            buf = self.bot.get_cog('YouCrew').getNextBuff(inter)
            if len(buf) > 0:
                output.append(buf)
                output.append("\n")
        except:
            pass
        try:
            exdata : ExtraDropData|None = await self.checkExtraDrops()
            if exdata[1] is not None:
                output.append(
                    "{} Extra Drops end in **{}**\n".format(
                        self.bot.emote.get(exdata[1]),
                        self.bot.util.delta2str(exdata[0] - current_time, 2)
                    )
                )
        except:
            pass
        try:
            if current_time < self.bot.data.save['stream']['time']:
                output.append(
                    "{} {} on the **{}**\n".format(
                        self.bot.emote.get('crystal'),
                        self.bot.util.command2mention('gbf stream'),
                        self.bot.util.time(
                            self.bot.data.save['stream']['time'],
                            style=['d','t'],
                            removejst=True
                        )
                    )
                )
        except:
            pass
        return ''.join(output)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(2, 10, commands.BucketType.user)
    @commands.max_concurrency(16, commands.BucketType.default)
    async def gbf(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @gbf.sub_command()
    async def wiki(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        terms : str = commands.Param(description="Search expression")
    ) -> None:
        """Search the GBF wiki"""
        await inter.response.defer()
        # call the search API
        r : RequestResult = await self.bot.net.requestWiki(
            "api.php",
            params={
                "action":"opensearch",
                "format":"json",
                "formatversion":"2",
                "search":quote(terms),
                "namespace":"0",
                "limit":"10"
            }
        )
        title : str = "Search for " + terms
        if len(title) >= 200:
            title = title[:200] + "..."
        if r is None or len(r[1]) == 0:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title=title,
                    description=(
                        "**No results**\n"
                        "[Click here to refine](https://gbf.wiki/index.php?title=Special:Search&search={})"
                    ).format(quote(terms)),
                    thumbnail="https://gbf.wiki/images/1/18/Vyrnball.png",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)
        else:
            descs : list[str] = ["**Search results**\n"]
            i : int
            for i in range(len(r[1])):
                descs.append("- [")
                descs.append(r[1][i])
                descs.append("](")
                descs.append(r[3][i])
                descs.append(")\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title=title,
                    url=f"https://gbf.wiki/index.php?title=Special:Search&search={quote(terms)}",
                    description="".join(descs),
                    thumbnail="https://gbf.wiki/images/1/18/Vyrnball.png",
                    color=self.COLOR
                )
            )

    @gbf.sub_command()
    async def info(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post various Granblue Fantasy informations"""
        await inter.response.defer()
        current_time : datetime = self.bot.util.JST(delay=False)
        description : list[str] = [
            "{} Current Time is **{}**".format(
                self.bot.emote.get('clock'),
                self.bot.util.time(style=['d','t'])
            ),
            "\n{} Japan Time is **{}**".format(
                self.bot.emote.get('clock'),
                current_time.strftime("%H:%M")
            )
        ]
        if self.bot.data.save['gbfversion'] is not None:
            description.append(
                "\n{} Version is `{}` (`{}`)".format(
                    self.bot.emote.get('cog'),
                    self.bot.data.save['gbfversion'],
                    self.bot.util.version2str(self.bot.data.save['gbfversion'])
                )
            )
        # reset timer
        reset : datetime = current_time.replace(hour=5, minute=0, second=0, microsecond=0)
        if current_time.hour >= reset.hour:
            reset += timedelta(days=1)
        d : timedelta = reset - current_time
        description.append(f"\n{self.bot.emote.get('mark')} Reset in **{self.bot.util.delta2str(d)}**\n")
        # add informations
        description.append(await self.getGBFInfoTimers(inter, current_time))
        # send message
        await inter.edit_original_message(
            embed=self.bot.embed(
                author={
                    'name':"Granblue Fantasy",
                    'icon_url':self.GBF_ICON
                },
                description=''.join(description),
                color=self.COLOR
            )
        )

    @gbf.sub_command()
    async def maintenance(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post GBF maintenance status"""
        try:
            await inter.response.defer()
            # simply retrieve maintenance string
            description : str = (await self.bot.net.gbf_maintenance_status())[0]
            if len(description) > 0:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        author={
                            'name':"Granblue Fantasy",
                            'icon_url':self.GBF_ICON
                        },
                        description=description,
                        color=self.COLOR
                    )
                )
            else:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Granblue Fantasy",
                        description="No maintenance in my memory",
                        color=self.COLOR
                    )
                )
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'gbf maintenance' command:", e)

    @gbf.sub_command()
    async def stream(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the stream text"""
        await inter.response.defer(ephemeral=True)
        if self.bot.data.save['stream'] is None:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="No event or stream available",
                    color=self.COLOR
                )
            )
        else:
            msg : str = ""
            current_time : datetime = self.bot.util.JST()
            if self.bot.data.save['stream']['time'] is not None:
                # retrieve stream time and add it before the description
                if current_time < self.bot.data.save['stream']['time']:
                    d : timedelta = self.bot.data.save['stream']['time'] - current_time
                    msg = "Stream starts in **{} ({})**\n".format(
                        self.bot.util.delta2str(d, 2),
                        self.bot.util.time(
                            self.bot.data.save['stream']['time'],
                            style=['d'],
                            removejst=True
                        )
                    )
                else:
                    msg = "Stream is **On going!! ({})**\n".format(
                        self.bot.util.time(
                            self.bot.data.save['stream']['time'],
                            style=['d'],
                            removejst=True
                        )
                    )
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title=self.bot.data.save['stream']['title'],
                    description=msg + self.bot.data.save['stream']['content'],
                    timestamp=self.bot.util.UTC(),
                    color=self.COLOR
                )
            )

    @gbf.sub_command()
    async def schedule(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the GBF schedule"""
        await inter.response.defer()
        current_time : datetime = self.bot.util.UTC()
        events : dict[int, list[str]] = {}
        next : None|tuple[datetime, str] = None
        # we'll first build and event list, stored in events, the key being the event(s) start date
        # next will store the next event to occur after our current time c
        event : str
        dates : list[int]
        start : datetime
        diff : timedelta
        for event, dates in self.bot.data.save['schedule'].items(): # for each schedule entry
            if dates[0] not in events: # make array if no events at this date
                events[dates[0]] = []
            match len(dates):
                case 1: # single timestamp event
                    start = datetime.utcfromtimestamp(dates[0])
                    diff = current_time - start
                    if current_time < start: # event hasn't started
                        events[dates[0]].append(f"- {event} ▫️ {self.bot.util.time(start, style=['d'])}\n")
                        if next is None or start < next[0]:
                            next = (start, event)
                    elif diff > timedelta(days=1): # 1 day old, show as ended
                        events[dates[0]].append(f"- ~~{event}~~\n")
                    elif diff > timedelta(days=3): # 3 days old, don't display
                        continue
                    else: # on going/happened
                        events[dates[0]].append(f"- **{event}**\n")
                case 2: # double timestamp event
                    start = datetime.utcfromtimestamp(dates[0])
                    end = datetime.utcfromtimestamp(dates[1])
                    if current_time < start: # event hasn't started
                        events[dates[0]].append(
                            "- {} ▫️ {} - {}\n".format(
                                event, self.bot.util.time(
                                    start, style=['d']
                                ),
                                self.bot.util.time(end, style=['d'])
                            )
                        )
                        if next is None or start < next[0]:
                            next = (start, event)
                    elif current_time >= end: # event has ended
                        if current_time - end > timedelta(days=3): # don't display
                            continue
                        events[dates[0]].append(f"- ~~{event}~~ ▫️ *Ended*\n")
                    else: # on going
                        events[dates[0]].append(
                            "- **{}** ▫️ Ends in **{}** {}\n".format(
                                event,
                                self.bot.util.delta2str(end - current_time, 2),
                                self.bot.util.time(end, style=['d'])
                            )
                        )
                case _:
                    continue
        # get and sort date list
        dates = list(events.keys())
        dates.sort()
        # make schedule by going over sorted dates
        msgs : list[str] = []
        date : int
        for date in dates:
            msgs.extend(events[date])
        if len(msgs) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="No schedule available", color=self.COLOR))
        else:
            # add extra infos at the bottom
            msgs.append(
                "{} Japan Time is **{}\n**".format(
                    self.bot.emote.get('clock'),
                    self.bot.util.JST().strftime("%I:%M %p")
                )
            )
            if next is not None:
                next_str : str
                if next[1].startswith("Update"):
                    next_str = "update"
                elif next[1].startswith("Maintenance"):
                    next_str = "maintenance"
                else:
                    next_str = "event"
                msgs.append(
                    "{} Next {} approximately in **{}**\n".format(
                        self.bot.emote.get('mark'),
                        next_str,
                        self.bot.util.delta2str(next[0] - current_time, 2)
                    )
                )
            msgs.append(await self.getGBFInfoTimers(inter, current_time))
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="🗓 Event Schedule {} {}".format(
                        self.bot.emote.get('clock'),
                        self.bot.util.time(style=['d', 't'])
                    ),
                    url="https://gbf.wiki/",
                    color=self.COLOR,
                    description=''.join(msgs),
                    footer="source: https://gbf.wiki/"
                )
            )
        await self.bot.channel.clean(inter, 120)

    @gbf.sub_command()
    async def gacha(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the current gacha informations"""
        try:
            await inter.response.defer()
            # simply retrieve and display gacha component summary
            summary : None|tuple[str, str] = await self.bot.gacha.summary()
            if summary is None:
                raise Exception('No Gacha')
            await inter.edit_original_message(
                embed=self.bot.embed(
                    author={
                        'name':"Granblue Fantasy",
                        'icon_url':self.GBF_ICON
                    },
                    description=summary[0],
                    thumbnail=summary[1],
                    color=self.COLOR
                )
            )
        except Exception as e:
            if str(e) != 'No Gacha':
                self.bot.logger.pushError("[GBF] In 'gbf gacha' command:", e)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    author={
                        'name':"Granblue Fantasy",
                        'icon_url':self.GBF_ICON
                    },
                    description="Unavailable",
                    color=self.COLOR
                )
            )
        await self.bot.channel.clean(inter, 120)

    @gbf.sub_command_group()
    async def profile(self : commands.SubCommandGroup, inter : disnake.ApplicationCommandInteraction) -> None:
        pass

    """searchprofile()
    Search a set profile in the save data

    Parameters
    ----------
    gbf_id: GBF profile id

    Returns
    --------
    str: matching discord ID as a string, None if error
    """
    def searchprofile(self : GranblueFantasy, gbf_id : int) -> str|None:
        try:
            return next(uid for uid, gid in self.bot.data.save['gbfids'].items() if gid == gbf_id)
        except:
            return None

    @profile.sub_command(name="unset")
    async def unsetprofile(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Unlink your GBF id"""
        await inter.response.defer(ephemeral=True)
        if str(inter.author.id) not in self.bot.data.save['gbfids']:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="You didn't set your GBF profile ID",
                    color=self.COLOR
                )
            )
            return
        try:
            del self.bot.data.save['gbfids'][str(inter.author.id)]
            self.bot.data.pending = True
        except:
            pass
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Your GBF profile has been unlinked",
                color=self.COLOR
            )
        )

    @profile.sub_command(name="set")
    async def setprofile(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        profile_id : int = commands.Param(
            description="A valid GBF Profile ID. Usurpation will result in ban.",
            ge=0,
            le=50000000
        )
    ) -> None:
        """Link your GBF id to your Discord ID"""
        try:
            await inter.response.defer(ephemeral=True)
            if self.bot.ban.check(str(inter.author.id), self.bot.ban.PROFILE): # check if author is banned
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description="You are banned to use this feature",
                        color=self.COLOR
                    )
                )
                await self.bot.channel.clean(inter, 60)
                return
            # check if account exists
            data : RequestResult
            if not self.bot.net.has_account() or not await self.bot.net.gbf_available():
                data = "Maintenance"
            else:
                data = await self.bot.net.requestGBF(
                    f"profile/content/index/{profile_id}",
                    expect_JSON=True
                )
                if data is not None:
                    data = unquote(data['data'])
            match data:
                case "Maintenance":
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="Error",
                            description="Game is unavailable, try again later.",
                            color=self.COLOR
                        )
                    )
                    return
                case None:
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title="Error",
                            description="Profile not found or Service Unavailable",
                            color=self.COLOR
                        )
                    )
                    return
                case _:
                    # check if profile is already linked
                    uid : str|None = self.searchprofile(profile_id)
                    if uid is not None:
                        if int(uid) == profile_id:
                            await inter.edit_original_message(
                                embed=self.bot.embed(
                                    title="Information",
                                    description=(
                                        "Your profile is already set to ID `{}`.\n"
                                        "Use {} if you wish to remove it."
                                    ).format(
                                        profile_id,
                                        self.bot.util.command2mention('gbf profile unset')
                                    ),
                                    color=self.COLOR
                                )
                            )
                        else:
                            await inter.edit_original_message(
                                embed=self.bot.embed(
                                    title="Error",
                                    description=(
                                        "This id is already in use, use {}"
                                        "if it's a case of griefing and send me the ID"
                                    ).format(
                                        self.bot.util.command2mention('bug_report')
                                    ),
                                    color=self.COLOR
                                )
                            )
                        return
            # register linked GBF profile
            self.bot.data.save['gbfids'][str(inter.author.id)] = profile_id
            self.bot.data.pending = True
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Success",
                    description="Your ID `{}` is now linked to your Discord ID `{}`".format(
                        profile_id,
                        inter.author.id
                    ),
                    color=self.COLOR
                )
            )
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'gbf profile set' command:", e)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An unexpected error occured",
                    color=self.COLOR
                )
            )
        await self.bot.channel.clean(inter, 60)

    """processProfile()
    Process profile data into discord embed elements

    Parameters
    ----------
    pid: Integer or String, Profile id
    soup: BeautifulSoup instance, HTML profile page soup

    Returns
    --------
    tuple: Containing:
        title: Discord embed title
        description: Discord embed description
        thumbnail: main character thumbnail
    """
    async def processProfile(self : GranblueFantasy, pid : int|str, soup : BeautifulSoup) -> tuple[str, str, str]:
        titles : list[str] = ["\u202d"]
        descs : list[str] = []
        thumbnail : str|None = None
        # # Generate Embed Title #################################
        # Trophy rarity
        rarity : str = "R"
        possible_headers : list[tuple[str, str]] = [
            ("prt-title-bg-gld", "SSR"),
            ("prt-title-bg-slv", "SR"),
            ("prt-title-bg-nml", "R"),
            ("prt-title-bg-cpr", "R")
        ]
        h : tuple[str, str]
        for h in possible_headers:
            try:
                if len(soup.find_all("div", class_=h[0])) > 0:
                    rarity = h[1]
                    break
            except:
                pass
        titles.append(str(self.bot.emote.get(rarity)))
        # Profile name
        try:
            titles.append(" **")
            titles.append(self.bot.util.shortenName(soup.find("span", class_="txt-other-name").string))
            titles.append("**")
        except:
            pass
        # Trophy text
        trophy : str = soup.find_all("div", class_="prt-title-name")[0].string
        if trophy != "No Trophy Displayed":
            titles.append("▫️")
            titles.append(trophy)
        # Final
        title : str = "".join(titles)
        # # Generate Embed Description #################################
        # Rank
        try:
            descs.append("**Rank ")
            descs.append(soup.find('div', class_='prt-user-name').get_text().split()[-1])
            descs.append("**")
        except:
            pass
        # Profile message
        comment : str = html.unescape(
            soup.find_all("div", class_="prt-other-comment")[0].string
        ).replace('\t', '').replace('\n', '')
        if comment != "":
            if len(descs) > 0:
                descs.append(" ▫️ 💬 `")
            else:
                descs.append("💬 `")
            descs.append(comment.replace('`', '\'')) # Replace ` by '
            descs.append("`\n")
        elif len(descs) > 0:
            descs.append("\n")
        # Crew name and id
        try:
            try:
                crew : str = self.bot.util.shortenName(soup.find_all("div", class_="prt-guild-name")[0].string)
                crewid : str = soup.find_all("div", class_="btn-guild-detail")[0]['data-location-href']
                crew = f"[{crew}](https://game.granbluefantasy.jp/#{crewid})"
            except:
                crew : str = soup.find_all("div", class_="txt-notjoin")[0].string
            descs.append(str(self.bot.emote.get('gw')))
            descs.append(" Crew ▫️ ")
            descs.append(crew)
            descs.append("\n")
        except:
            pass
        # GW Scores
        pdata : None|GWDBSearchResult = await self.bot.ranking.searchGWDB(str(pid), 2)
        n : int
        for n in range(0, 2):
            try:
                pscore : Score = pdata[n][0]
                if pscore.ranking is None:
                    descs.append(
                        "{} GW**{}** ▫️ **{:,}** honors\n".format(
                            self.bot.emote.get('gw'),
                            pscore.gw,
                            pscore.current
                        )
                    )
                else:
                    descs.append(
                        "{} GW**{}** ▫️ #**{}** ▫️ **{:,}** honors\n".format(
                            self.bot.emote.get('gw'),
                            pscore.gw,
                            pscore.ranking,
                            pscore.current
                        )
                    )
            except:
                pass
        # Spacer
        if len(descs) > 0:
            descs.append("\n")
        # Star character
        try:
            pushed : bs4element.Tag = soup.find("div", class_="prt-pushed")
            star : list[str]
            if pushed.find("div", class_="ico-augment2-s", recursive=True) is not None:
                # Check perp ring
                star = ["**\\💍** "]
            else:
                star = []
            # Add the star chara name
            star.append(
                pushed.findChildren(
                    "span",
                    class_="prt-current-npc-name",
                    recursive=True
                )[0].get_text().strip()
            )
            if "Lvl" not in star[-1]: # something went wrong if level is missing
                raise Exception()
            # add plus bonus if it exists
            try:
                star.append(
                    " **{}**".format(
                        pushed.find(
                            "div",
                            class_="prt-quality",
                            recursive=True
                        ).get_text().strip()
                    )
                )
            except:
                pass
            # add EMP level if it exists
            try:
                star.append(
                    " ▫️ **{}** EMP".format(
                        pushed.find(
                            "div",
                            class_="prt-npc-rank",
                            recursive=True
                        ).get_text().strip()
                    )
                )
            except:
                pass

            descs.append(str(self.bot.emote.get('skill2')))
            descs.append("**Star Character**\n")
            descs.extend(star)
            descs.append("\n")

            # Add star character comment if it exists
            try:
                starcom : str = pushed.find("div", class_="prt-pushed-info", recursive=True).get_text()
                if starcom != "" and starcom != "(Blank)":
                    descs.append("\u202d💬 `")
                    descs.append(starcom.replace('`', '\''))
                    descs.append("`\n")
            except:
                pass
        except:
            pass
        # Spacer
        if len(descs) > 1:
            descs.append("\n")
        # Support Summons
        try:
            script : BeautifulSoup = BeautifulSoup(
                soup.find(
                    "script", id="tpl-summon"
                ).get_text().replace(
                    " <%=obj.summon_list.shift().viewClassName%>", ""
                ),
                "html.parser"
            )
            # 2 lines for each element + misc. Misc is located last. Also, we support up to 4 summons per element.
            summon_lines : list[list[tuple[str, str]]] = [[] for i in range(7 * 2)]
            i : int = 0
            j : int
            x : int
            e : bs4element.ResultSet
            for x, e in enumerate(script.find_all("div", class_="prt-fix-support-wrap")): # iterate over summons
                y : int
                v : bs4element.Tag
                for y, v in enumerate(e.findChildren("div", class_="prt-fix-support", recursive=False)):
                    t : bs4element.Tag = v.findChildren("div", recursive=False)[-1]
                    if "No support summon is set." not in t.get_text(): # check if set
                        c : bs4element.ResultSet = t.findChildren("div", recursive=False)
                        sname : str = c[0].get_text() # summon name
                        cname : str = c[1].get('class')[-1] # HTML text class
                        # determine quality (i.e. uncap level)
                        squal : str
                        if 'bless-rank' in cname:
                            squal = f"star{cname.split('bless-rank')[-1].split('-', 1)[0]}"
                        else:
                            squal = "star0"
                        # misc summons are first in the list but last in our summon_lines array
                        j = (i - 1) * 2 if i > 0 else 6 * 2
                        if len(summon_lines[j]) >= 2:
                            j += 1 # switch to second line if first line is "full"
                        summon_lines[j].append((sname, squal))
                i += 1
            support_summons = []
            summons: list[tuple[str, str]]
            for i, summons in enumerate(summon_lines):
                if len(summons) > 0:
                    support_summons.append(str(self.bot.emote.get(self.SUMMON_ELEMENTS[i // 2])))
                    support_summons.append(" ")
                    summon : tuple[str, str]
                    for j, summon in enumerate(summons):
                        if j > 0:
                            support_summons.append(" ▫️ ")
                        support_summons.append(str(self.bot.emote.get(summon[1])))
                        support_summons.append(summon[0])
                    support_summons.append("\n")
                elif i & 1 == 0: # display None on first line
                    support_summons.append(str(self.bot.emote.get(self.SUMMON_ELEMENTS[i // 2])))
                    support_summons.append(" None\n")
            if len(support_summons) > 0:
                descs.append(str(self.bot.emote.get('summon')))
                descs.append(" **Support Summons**\n")
                descs.extend(support_summons)
        except:
            pass
        # Final
        desc : str = "".join(descs)
        # # Generate Embed Thumbnail #################################
        # MC class image. We use the talk bubble path
        try:
            thumbnail = soup.find_all(
                "img", class_="img-pc"
            )[0]['src'].replace(
                "/po/", "/talk/"
            ).replace(
                "/img_low/", "/img/"
            )
        except:
            pass
        return title, desc, thumbnail

    """_profile()
    Retrieve a GBF profile and post it

    Parameters
    ----------
    inter: Command interaction, must be deferred beforehand
    pid: GBF id
    clean: Boolean, set to false to disable the cleanup
    color: To change the embed color
    view: Optional view
    """
    async def _profile(
        self : GranblueFantasy,
        inter, pid,
        *,
        clean : bool = True,
        color : int|None = None,
        view : BaseView|None = None
    ) -> None:
        if color is None:
            color = self.COLOR # use cog color
        # retrieve profile data
        data : RequestResult
        if not self.bot.net.has_account() or not await self.bot.net.gbf_available():
            data = "Maintenance"
        else:
            data = await self.bot.net.requestGBF(
                f"profile/content/index/{pid}",
                expect_JSON=True
            )
            if data is not None:
                data = unquote(data['data'])
        match data: # check validity
            case "Maintenance":
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description="Game is in maintenance",
                        color=color
                    ),
                    view=view
                )
                if clean:
                    await self.bot.channel.clean(inter, 45)
                return
            case None:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description="Profile not found or Service Unavailable",
                        color=color
                    ),
                    view=view
                )
                if clean:
                    await self.bot.channel.clean(inter, 45)
                return
        # parse page
        soup : BeautifulSoup = BeautifulSoup(data, 'html.parser')
        name : str|None
        try:
            name = soup.find_all("span", class_="txt-other-name")[0].string
        except:
            name = None
        if name is None:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Profile is Private",
                    color=color
                ),
                view=view
            )
        else:
            title : str
            description : str
            thumbnail : str|None
            title, description, thumbnail = await self.processProfile(pid, soup)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title=title,
                    description=description,
                    url=f"https://game.granbluefantasy.jp/#profile/{pid}",
                    thumbnail=thumbnail,
                    inline=True,
                    color=color
                ),
                view=view
            )
        if clean:
            await self.bot.channel.clean(inter, 45)

    @profile.sub_command()
    async def see(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        target : str = commands.Param(description="Either a valid GBF ID, discord ID or mention", default="")
    ) -> None:
        """Retrieve a GBF profile"""
        try:
            await inter.response.defer()
            pid : str|int = await self.bot.util.str2gbfid(inter, target)
            if isinstance(pid, str):
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description=pid,
                        color=self.COLOR
                    )
                )
            else:
                await self._profile(inter, pid, clean=False) # call _profile above
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'gbf profile see' command:", e)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An unexpected error occured",
                    color=self.COLOR
                )
            )
        await self.bot.channel.clean(inter, 60)

    @commands.user_command(name="GBF Profile")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.max_concurrency(4, commands.BucketType.default)
    async def gbfprofile(
        self : commands.user_command,
        inter : disnake.UserCommandInteraction,
        member: disnake.Member
    ) -> None:
        """Retrieve a GBF profile"""
        try: # SAME function as see above
            await inter.response.defer()
            pid : str|int = await self.bot.util.str2gbfid(inter, str(member.id), memberTarget=member)
            if isinstance(pid, str):
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description=pid,
                        color=self.COLOR
                    )
                )
            else:
                await self._profile(inter, pid)
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'GBF Profile' user command:", e)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An unexpected error occured",
                    color=self.COLOR
                )
            )
        await self.bot.channel.clean(inter, 60)

    @gbf.sub_command_group(name="utility")
    async def _utility(self : commands.SubCommandGroup, inter : disnake.ApplicationCommandInteraction) -> None:
        pass

    @_utility.sub_command()
    async def spreadsheet(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post a link to my SpreadSheet Folder"""
        await inter.response.defer()
        view : UrlButton = UrlButton(
            self.bot,
            [
                (
                    'SpreadSheet Folder',
                    'https://drive.google.com/drive/folders/1p7rWQLJjVsoujQqYsJ0zVGUERMsQWmKn'
                )
            ]
        )
        await inter.edit_original_message('\u200b', view=view)
        view.stopall()
        await self.bot.channel.clean(inter, 60)

    @_utility.sub_command()
    async def xp(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        start_level : int = commands.Param(description="Starting Point of the calcul", ge=1, le=149, default=1),
        end_level : int = commands.Param(description="Final Point of the calcul", ge=1, le=150, default=1)
    ) -> None:
        """Character experience calculator"""
        await inter.response.defer(ephemeral=True)
        if start_level < 1:
            start_level = 1
        elif start_level >= 150:
            start_level = 149
        msgs : list[str] = [f"From level **{start_level}**, you need:\n"]
        xpcount : int = self.XP_TABLE[start_level]
        # iterate over level and counts the exp
        lvl : int
        for lvl in range(start_level + 1, 151):
            if lvl in (80, 100, 110, 120, 130, 140, 150, end_level): # add messages at specific thresholds
                msgs.append(
                    "**{:,} XP** for lvl **{:}** ({:} books or {:,} candies)\n".format(
                        xpcount,
                        lvl,
                        math.ceil(xpcount / 300000),
                        math.ceil(xpcount / 745)
                    )
                )
                if lvl == end_level:
                    break
            xpcount += self.XP_TABLE[lvl]
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Experience Calculator",
                description="".join(msgs),
                color=self.COLOR
            )
        )

    @_utility.sub_command()
    async def kirinanima(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        talisman : int = commands.Param(description="Talisman count", ge=0, le=100000, default=0),
        ream : int = commands.Param(description="Ream count", ge=0, le=100000, default=0),
        silver_anima : int = commands.Param(description="Silver Anima count", ge=0, le=100000, default=0),
        omega_anima : int = commands.Param(description="Omega Anima count", ge=0, le=100000, default=0)
    ) -> None:
        """Calcul how many Omega animas of Kirin or Huanglong you own"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Kirin Anima Calculator",
                description="You own the equivalent of **{}** Omega Animas".format(
                    omega_anima + (ream + talisman // 5 + silver_anima) // 10
                ),
                thumbnail=(
                    "https://prd-game-a-granbluefantasy.akamaized.net/"
                    "assets_en/img_low/sp/assets/item/article/s/{}.jpg"
                ).format([529,531][int(datetime.now().timestamp()) & 1]),
                color=self.COLOR
            )
        )

    @gbf.sub_command_group()
    async def check(self : commands.SubCommandGroup, inter : disnake.ApplicationCommandInteraction) -> None:
        pass

    """getGrandList()
    Request the grand character list from the wiki page and return the list of latest released ones

    Returns
    ----------
    dict: Grand per element
    """
    async def getGrandList(self : GranblueFantasy) -> dict[str, None|dict[str, str|datetime]]:
        if "wiki_grand_list" not in self.bot.data.save["gbfdata"]:
            self.bot.data.save["gbfdata"]["wiki_grand_list"] = {"list":{}, "last":None}
        forced_check : bool = False
        current_time : datetime = self.bot.util.JST()
        if (self.bot.data.save["gbfdata"]["wiki_grand_list"]["last"] is None
                or current_time - self.bot.data.save["gbfdata"]["wiki_grand_list"]["last"] > timedelta(days=1)):
            forced_check = True
        if forced_check:
            # get grand list from cargo table
            data : RequestResult = await self.bot.net.requestWiki(
                "index.php",
                params={
                    "title":"Special:CargoExport",
                    "tables":"characters",
                    "fields":"series,name,element,release_date",
                    "where":'series LIKE "%grand%"',
                    "format":"json",
                    "limit":"200"
                }
            )
            if data is None:
                return {}
            grand_list : dict[str, None|dict[str, str|datetime]] = {
                'fire':None, 'water':None, 'earth':None,
                'wind':None, 'light':None, 'dark':None
            }
            # take note of latest grand for each element
            c : dict[str, str|datetime]
            for c in data:
                try:
                    if 'grand' not in c['series']:
                        continue
                    grand : dict[str, str] = c
                    d : list[str] = grand['release date'].split('-')
                    grand['release date'] = self.bot.util.UTC().replace( # parse release date
                        year=int(d[0]),
                        month=int(d[1]),
                        day=int(d[2]),
                        hour=(12 if (int(d[2]) > 25) else 19),
                        minute=0,
                        second=0, microsecond=0
                    )
                    grand['element'] = grand['element'].lower()
                    # update grand if more recent
                    if (grand_list[grand['element']] is None
                            or grand['release date'] > grand_list[grand['element']]['release date']):
                        grand_list[grand['element']] = grand
                except:
                    pass
            self.bot.data.save["gbfdata"]["wiki_grand_list"]["list"] = grand_list
            self.bot.data.save["gbfdata"]["wiki_grand_list"]["last"] = current_time
            self.bot.data.pending = True
            return grand_list
        else:
            return self.bot.data.save["gbfdata"]["wiki_grand_list"]["list"]

    """retrieve_wiki_wait_intervals()
    Request specific wiki pages to retrieve the latest release dates of these elements

    Returns
    ----------
    dict: Pairs of String and Tuple (containing release dates and wiki page names)
    """
    async def retrieve_wiki_wait_intervals(self : GranblueFantasy) -> dict[str, tuple[datetime, str]]:
        if "wiki_intervals" not in self.bot.data.save["gbfdata"]:
            self.bot.data.save["gbfdata"]["wiki_intervals"] = {"list":{}, "last":None}
        current_time : datetime = self.bot.util.JST()
        forced_check : bool = False
        if (self.bot.data.save["gbfdata"]["wiki_intervals"]["last"] is None
                or current_time - self.bot.data.save["gbfdata"]["wiki_intervals"]["last"] > timedelta(days=1)):
            forced_check = True
        # targeted pages
        targets : list[tuple[str, str, str|None, dict[int, str], str|None]] = [
            # Format is:
            # page, template name, split string, substitutes,
            # tuple containing extra regex to detect extra duration
            ("Main_Quest", "MainStoryRelease", None, {}, None),
            ("Category:Campaign", "WaitInterval", None, {0:"Campaign"}, "\\|duration=([0-9]+)\\|duration2=([0-9]+)"),
            ("Surprise_Special_Draw_Set", "WaitInterval", None, {}, None),
            ("Damascus_Ingot", "WaitInterval", None, {}, None),
            ("Gold_Brick", "WaitInterval", None, {0:"ROTB Gold Brick"}, None),
            ("Sunlight_Stone", "WaitInterval", "Arcarum Shop", {
                0:"Sunlight Shard Sunlight Stone",
                1:"Arcarum Sunlight Stone"
            }, None),
            ("Sephira_Evolite", "WaitInterval", None, {0:"Arcarum Sephira Evolite"}, None)
        ]
        result : dict[str, tuple[datetime, str]] = {}
        if forced_check:
            # loop over target
            page : str
            findstr : str
            splitstr : str|None # to split the page in parts
            displaystr : dict # string to display in the msg
            matchstr : str|None # to extend the regex
            for page, findstr, splitstr, displaystr, matchstr in targets:
                await asyncio.sleep(0.2)
                # make a wiki API request for the page
                content = await self.bot.net.requestWiki(
                    f"api.php?action=query&prop=revisions&titles={page}&rvslots=*&rvprop=content&format=json"
                )
                if content is None: # return if error
                    continue
                page_is_done : bool = False # this flag is used to break out of loops
                # loop over pages...
                data : dict[str, str|dict|list]
                for data in content["query"]["pages"].values():
                    rev : dict[str, str|dict|list]
                    for rev in data["revisions"]: # ... and revisions
                        codes : list[str]
                        if splitstr is None:
                            codes = [rev["slots"]["main"]["*"]]
                        else:
                            codes = rev["slots"]["main"]["*"].split(splitstr)
                        # iterate over these parts
                        i : int
                        code : str
                        for i, code in enumerate(codes):
                            matches : list[str|list[str]]
                            if matchstr is None:
                                matches = re.findall("{{" + findstr + "\\|(\\d{4}-\\d{2}-\\d{2})", code)
                            else:
                                # add the extra regex
                                matches = re.findall("{{" + findstr + "\\|(\\d{4}-\\d{2}-\\d{2})" + matchstr, code)
                            highest : datetime|None = None
                            data : str|list[str]
                            d : datetime
                            for date in matches:
                                if matchstr is None:
                                    d = datetime.strptime(date, "%Y-%m-%d")
                                else: # extended regex
                                    d = datetime.strptime(date[0], "%Y-%m-%d")
                                    duration : int = 0
                                    j : int
                                    for j in range(1, len(date)): # iterate over extra groups
                                        if date[j] != "0": # Note: we're expected to find numbers only
                                            duration = max(duration, int(date[j]))
                                    if current_time > d + timedelta(days=duration):
                                        d += timedelta(days=duration) # add to date
                                # check if our date is the highest, i.e. closest to us
                                if highest is None or d > highest:
                                    highest = d
                            if highest is not None:
                                result[displaystr.get(i, data['title'])] = (highest.replace(hour=12), page)
                                # Note: set to 12 am JST as reference, even if it's not always the case
                            page_is_done = True # done, raise the flag
                        if page_is_done:
                            break
                    if page_is_done:
                        break
            self.bot.data.save["gbfdata"]["wiki_intervals"]["list"] = {}
            k : str
            v : tuple[datetime, str]
            for k, v in result.items():
                self.bot.data.save["gbfdata"]["wiki_intervals"]["list"][k] = list(v)
            self.bot.data.save["gbfdata"]["wiki_intervals"]["last"] = current_time
            self.bot.data.pending = True
        else:
            k : str
            v : str|datetime
            for k, v in self.bot.data.save["gbfdata"]["wiki_intervals"]["list"].items():
                result[k] = tuple(v)
        return result

    @check.sub_command()
    async def doom(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Give the time elapsed of various GBF related releases"""
        await inter.response.defer()
        msgs : list[str] = []
        c : datetime = self.bot.util.JST() # current time
        # Various releases
        k : str
        v : tuple[datetime, str]
        for k, v in (await self.retrieve_wiki_wait_intervals()).items():
            msgs.append("**")
            msgs.append(str((c - v[0]).days))
            msgs.append(" days** since the last [")
            msgs.append(k)
            msgs.append("](https://gbf.wiki/")
            msgs.append(v[1])
            msgs.append(")\n")

        additions : list[tuple[datetime, str]] = [
            (
                c.replace(year=2021, month=8, day=16, hour=19, minute=0, second=0, microsecond=0),
                "the Summer Fortune 2021 results\n"
            ),
            (
                c.replace(year=2023, month=11, day=9, hour=7, minute=0, second=0, microsecond=0),
                "the Settecide Day\n"
            ),
            (
                c.replace(year=2024, month=7, day=27, hour=21, minute=0, second=0, microsecond=0),
                "the new Producer takeover\n"
            ),
            (
                c.replace(year=2025, month=1, day=14, hour=21, minute=30, second=0, microsecond=0),
                "the Mjolnir's nerf\n"
            )
        ]
        # Additional texts
        for v in additions:
            msgs.append(f"**{self.bot.util.delta2str(c - v[0], 3).split('d', 1)[0]} days** since ")
            msgs.append(v[1])
        # Grand List (check getGrandList() above)
        try:
            grands : dict[str, None|dict[str, str|datetime]] = await self.getGrandList()
            e : str
            for e in grands:
                msgs.append(
                    "**{} days** since {} [{}](https://gbf.wiki/{})\n".format(
                        self.bot.util.delta2str(
                            c - grands[e]['release date'],
                            3
                        ).split('d', 1)[0],
                        self.bot.emote.get(e),
                        grands[e]['name'],
                        grands[e]['name'].replace(' ', '_')
                    )
                )
        except:
            pass
        # Display the result
        if len(msgs) > 0:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    author={
                        'name':"Granblue Fantasy",
                        'icon_url':self.GBF_ICON
                    },
                    description="".join(msgs),
                    footer="Source: http://gbf.wiki/",
                    color=self.COLOR
                )
            )
        else:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Unavailable",
                    color=self.COLOR
                )
            )
        await self.bot.channel.clean(inter, 40)

    @check.sub_command()
    async def coop(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Retrieve the current coop daily missions"""
        try:
            await inter.response.defer(ephemeral=True)
            # check mission endpoint
            data : RequestResult = (
                await self.bot.net.requestGBF(
                    'coopraid/daily_mission',
                    expect_JSON=True
                )
            )['daily_mission']
            msgs : list[str] = []
            i : int
            for i in range(len(data)):
                if data[i]['category'] == '2':
                    items : dict[int, str] = {
                        20011:'fire', 20012:'fire', 20111:'fire', 20021:'water',
                        20022:'water', 20121:'water', 20031:'earth', 20032:'earth',
                        20131:'earth', 20041:'wind', 20042:'wind', 20141:'wind'
                    }
                    cid : int = int(data[i]['image'].split('/')[-1])
                    msgs.append(f"{self.bot.emote.get(items.get(cid, 'misc'))} {data[i]['description']}\n")
                elif data[i]['category'] == '1':
                    quests : dict[str, str] = {
                        's00101':'wind', 's00104':'wind', 's00204':'wind', 's00206':'wind',
                        's00301':'fire', 's00303':'fire', 's00405':'fire', 's00406':'fire',
                        's00601':'water', 's00602':'water', 's00604':'water', 's00606':'water',
                        's00802':'earth', 's00704':'earth', 's00705':'earth', 's00806':'earth',
                        's01005':'wind', 's00905':'wind', 's00906':'wind', 's01006':'wind',
                        's01105':'fire', 's01403':'fire', 's01106':'fire', 's01206':'fire',
                        's01001':'water', 's01502':'water', 's01306':'water', 's01406':'water',
                        's01601':'earth', 's01405':'earth', 's01506':'earth', 's01606':'earth'
                    }
                    cid : str = data[i]['image'].split('/')[-1]
                    msgs.append(f"{self.bot.emote.get(quests.get(cid, 'misc'))} {data[i]['description']}\n")
                else:
                    msgs.append(f"{self.bot.emote.get(str(i + 1))} {data[i]['description']}\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    author={
                        'name':"Daily Coop Missions",
                        'icon_url':self.GBF_ICON
                    },
                    description=''.join(msgs),
                    url="https://game.granbluefantasy.jp/#coopraid",
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Unavailable",
                    color=self.COLOR
                )
            )

    @check.sub_command()
    async def koregra(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the time to the next monthly dev post"""
        await inter.response.defer()
        c : datetime = self.bot.util.JST()
        # rough estimate of when it's released
        m : datetime = c.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
        if m < c and m.month == 12: # new year fix
            m = m.replace(year=m.year + 1, month=1)
        else:
            m = m.replace(month=m.month + 1)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title=f"{self.bot.emote.get('clock')} Kore Kara",
                description="Release approximately in **{}**".format(
                    self.bot.util.delta2str(
                        m - c,
                        2
                    )
                ),
                url="https://granbluefantasy.jp/news/index.php",
                thumbnail=self.GBF_ICON,
                color=self.COLOR
            )
        )

    @check.sub_command()
    async def news(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the latest news posts"""
        await inter.response.defer(ephemeral=True)
        msgs : list[str] = []
        i : int
        for i in range(len(self.bot.data.save['gbfdata'].get('news_url', []))):
            # simply iterate over stored data
            msgs.append(
                "{} [{}]({})\n".format(
                    self.bot.emote.get(str(i + 1)),
                    self.bot.data.save['gbfdata']['news_url'][i][1],
                    self.bot.data.save['gbfdata']['news_url'][i][0]
                )
            )
        thumb : str|None
        try:
            thumb = self.bot.data.save['gbfdata']['news_url'][0][2] # add thumbnail of most recent element
            if not thumb.startswith('http://granbluefantasy.jp') and not thumb.startswith('https://granbluefantasy.jp'):
                if thumb.startswith('/'):
                    thumb = 'https://granbluefantasy.jp' + thumb
                else:
                    thumb = 'https://granbluefantasy.jp/' + thumb
        except:
            thumb = None
        # send message
        if len(msgs) == 0:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Unavailable",
                    color=self.COLOR
                )
            )
        else:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    author={
                        'name':"Latest Granblue Fantasy News",
                        'icon_url':self.GBF_ICON
                    },
                    description="".join(msgs),
                    image=thumb,
                    color=self.COLOR
                )
            )

    @check.sub_command()
    async def granblues(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        episode : int = commands.Param(
            description="A Grand Blues! episode number",
            default=1,
            ge=1,
            le=99999
        )
    ) -> None:
        """Post a Granblues Episode"""
        try:
            await inter.response.defer(ephemeral=True)
            url : str = (
                "https://prd-game-a-granbluefantasy.akamaized.net/"
                "assets_en/img/sp/assets/comic/episode/episode_{}.jpg"
            ).format(episode)
            if (await self.bot.net.request(url)) is None:
                raise Exception()
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title=f"Grand Blues! Episode {episode}",
                    url=(
                        "https://prd-game-a-granbluefantasy.akamaized.net/"
                        "assets_en/img/sp/assets/comic/episode/episode_{}.jpg"
                    ).format(episode),
                    image=(
                        "https://prd-game-a-granbluefantasy.akamaized.net/"
                        "assets_en/img/sp/assets/comic/thumbnail/thum_{}.png"
                    ).format(
                        str(episode).zfill(5)
                    ),
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Invalid Grand Blues! number",
                    color=self.COLOR
                )
            )

    @gbf.sub_command_group()
    async def campaign(self : commands.SubCommandGroup, inter : disnake.ApplicationCommandInteraction) -> None:
        pass

    @campaign.sub_command()
    async def crystal(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Granblue Summer Festival - Crystal Countdown 2023"""
        await inter.response.defer()
        try:
            msg : str
            c : datetime = self.bot.util.JST()
            # settings
            start : datetime = c.replace(year=2023, month=8, day=1, hour=5, minute=0, second=0, microsecond=0)
            end : datetime = c.replace(year=2023, month=8, day=13, hour=4, minute=59, second=59, microsecond=0)
            maxwave : datetime = 2
            crystal_per_wave : datetime = 5000000000
            # end settings
            footer : str = ""
            if c > end or self.bot.data.save['extra'].get('campaign/dividecrystal', {}).get('wave', 9999) > maxwave:
                msg = "The event has ended for this year."
            elif c < start:
                msg = "The event hasn't started."
            else:
                if 'campaign/dividecrystal' not in self.bot.data.save['extra']:
                    self.bot.data.save['extra']['campaign/dividecrystal'] = {'wave':1, 'expire':end}
                try:
                    # access endpoint
                    data : str = unquote(
                        (
                            await self.bot.net.requestGBF(
                                "campaign/dividecrystal/content/index",
                                expect_JSON=True
                            )
                        )['data']
                    )
                except Exception as tmp:
                    # hacky way to detect which wave we are at
                    if (maxwave > 1
                            and self.bot.data.save['extra']['campaign/dividecrystal']['wave'] < maxwave
                            and (c - start).days > 2):
                        try:
                            await self.bot.net.requestGBF(
                                "campaign/dividecrystal/content/bonus_present",
                                expect_JSON=True
                            )
                            data : str = unquote(
                                (
                                    await self.bot.net.requestGBF(
                                        "campaign/dividecrystal/content/index",
                                        expect_JSON=True
                                    )
                                )['data']
                            )
                            self.bot.data.save['extra']['campaign/dividecrystal']['wave'] += 1
                            self.bot.data.pending = True
                        except:
                            raise tmp
                    elif self.bot.data.save['extra']['campaign/dividecrystal']['wave'] == maxwave:
                        # likely triggered by the end
                        try:
                            await self.bot.net.requestGBF(
                                "campaign/dividecrystal/content/bonus_present",
                                expect_JSON=True
                            )
                            data : str = unquote(
                                (
                                    await self.bot.net.requestGBF(
                                        "campaign/dividecrystal/content/index",
                                        expect_JSON=True
                                    )
                                )['data']
                            )
                        except:
                            raise tmp
                    else:
                        raise tmp
                # extract amount
                s : int = data.find('<div class="txt-amount">')
                if s == -1:
                    raise Exception()
                s += len('<div class="txt-amount">')
                ds : list[str] = data[s:].split('/')
                crystal : int = int(ds[0].replace(',', ''))
                available_crystal : int = int(ds[1].replace(',', '').replace('<', ''))
                if maxwave > 1:
                    s1 : str = '<div class="prt-wave-{}">'.format(
                        self.bot.data.save['extra']['campaign/dividecrystal']['wave']
                    )
                    s2 : str = '<div class="prt-wave-{}">'.format(
                        self.bot.data.save['extra']['campaign/dividecrystal']['wave'] + 1
                    )
                    if data.find(s1) == -1 and data.find(s2) != -1:
                        # additional wave change check
                        self.bot.data.save['extra']['campaign/dividecrystal']['wave'] += 1
                        self.bot.data.pending = True
                    footer += "Part {}/{}".format(
                        self.bot.data.save['extra']['campaign/dividecrystal']['wave'],
                        maxwave
                    )
                    available_crystal : int = crystal_per_wave * maxwave
                    crystal += crystal_per_wave * (
                        maxwave - self.bot.data.save['extra']['campaign/dividecrystal']['wave']
                    )

                if crystal <= 0:
                    msg = f"{self.bot.emote.get('crystal')} No crystals remaining"
                else:
                    # do the math and finalize messages
                    consumed : int = (available_crystal - crystal)
                    avg_completion_crystal : int = 1600
                    players : float = (consumed / ((c - start).days + 1)) / avg_completion_crystal
                    msgs : list[str] = [
                        (
                            "{:} **{:,}** crystals remaining"
                            "(Average **{:}** players/day, at {:,} crystals average).\n"
                        ).format(
                            self.bot.emote.get('crystal'),
                            crystal,
                            self.bot.util.valToStr(players),
                            avg_completion_crystal
                        )
                    ]
                    msgs.append(
                        "{} Event is ending in **{}**.\n".format(
                            self.bot.emote.get('clock'),
                            self.bot.util.delta2str(end - c, 2)
                        )
                    )
                    elapsed : timedelta = c - start
                    duration : timedelta = end - start
                    progresses : list[float] = [
                        100 * (consumed / available_crystal),
                        100 * (elapsed.days * 86400 + elapsed.seconds) / (duration.days * 86400 + duration.seconds)
                    ]
                    msgs.append(
                        "Progress ▫️ **{:.2f}%** {:} ▫️ **{:.2f}%** {:} ▫️ ".format(
                            progresses[0],
                            self.bot.emote.get('crystal'),
                            progresses[1],
                            self.bot.emote.get('clock')
                        )
                    )
                    if progresses[1] > progresses[0]:
                        msgs.append("✅\n") # white check mark
                        leftover : float = available_crystal * (100 - (progresses[0] * 100 / progresses[1])) / 100
                        eligible : int = int(players * 1.1)
                        msgs.append(
                            "Estimating between **{:,}** and **{:,}** bonus crystals/player at the end.".format(
                                int(leftover / eligible),
                                int(leftover / 550000)
                            )
                        )
                        if footer != "":
                            footer += " - "
                        footer += f"Assuming ~{self.bot.util.valToStr(eligible)} eligible players."
                    else:
                        msgs.append("⚠️\n")
                        t : timedelta = timedelta(
                            seconds=(
                                (duration.days * 86400 + duration.seconds)
                                * (100 - (progresses[1] * 100 / progresses[0]))
                                / 100)
                        )
                        msgs.append(
                            "Crystals will run out in **{}** at current pace.".format(
                                self.bot.util.delta2str(end - t - c, 2)
                            )
                        )
                    msg = "".join(msgs)
        except Exception as e:
            msg = "An error occured, try again later."
            self.bot.logger.pushError("[GBF] 'crystal' error:", e)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Granblue Summer Festival",
                description=msg,
                url="https://game.granbluefantasy.jp/#campaign/division",
                footer=footer,
                color=self.COLOR
            )
        )

    @campaign.sub_command()
    async def element(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Granblue Summer Festival - Skyfarer Assemble 2024/2025"""
        await inter.response.defer()
        try:
            msg : str
            c : datetime = self.bot.util.JST()
            # settings
            start : datetime = c.replace(year=2025, month=8, day=1, hour=5, minute=0, second=0, microsecond=0)
            end : datetime = c.replace(year=2025, month=8, day=13, hour=4, minute=59, second=59, microsecond=0)
            # end settings
            footer : str = ""
            if c > end:
                msg = "The event has ended for this year."
            elif c < start:
                msg = "The event hasn't started."
            else:
                # get data from endpoint
                data : RequestResult = await self.bot.net.requestGBF(
                    "rest/campaign/accumulatebattle/point_list",
                    expect_JSON=True
                )
                msgs : list[str] = [f"Goal ▫️ **{data['goal']:,}**"]
                elems : dict[str, str] = {"1":"fire", "2":"water", "3":"earth", "4":"wind", "5":"light", "6":"dark"}
                k : str
                v : int
                for k, v in data["total"].items():
                    if v >= data['goal']:
                        msgs.append(
                            "{:} ▫️ **{:,}** {:}".format(
                                self.bot.emote.get(elems.get(k, k)),
                                v,
                                self.bot.emote.get('crown')
                            )
                        )
                    else:
                        msgs.append(
                            "{:} ▫️ **{:,}** ({:.2f}%)".format(
                                self.bot.emote.get(elems.get(k, k)),
                                v,
                                100 * v / data['goal']
                            )
                        )
                msgs.append(
                    "{} Event is ending in **{}**.".format(
                        self.bot.emote.get('clock'),
                        self.bot.util.delta2str(end - c, 2)
                    )
                )
                msg = '\n'.join(msgs)
        except Exception as e:
            msg = "An error occured, try again later."
            self.bot.logger.pushError("[GBF] 'element' error:", e)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Granblue Summer Festival",
                description=msg,
                url="https://game.granbluefantasy.jp/#campaign/accumulatebattle",
                footer=footer,
                color=self.COLOR
            )
        )

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def guide(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @guide.sub_command()
    async def defense(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post some known defense values"""
        await inter.response.defer(ephemeral=True)
        dev_values : dict[str, str] = {
            "8.5" : "Fediel Solo",
            "9.5" : "Fediel HL",
            "10"  : "Estimate / Trial / Story / Event / EX+",
            "11"  : "PBaha N / UBaha HL / Xeno",
            "12"  : "M1 HL / Kirin HL / Metatron / Avatar / GO HL / Lindwurm",
            "13"  : "Normal / Hard / T2 / Primarchs N & HL / UBaha N / M2",
            "15"  : "T1 HL / Malice / Menace / Akasha / Lucilius / Astaroth / Pride",
            "18"  : "Rose Queen / 6 Dragons HL / SUbaha",
            "20"  : "PBaha HL / Lucilius Hard / Belial",
            "22"  : "Celeste HL (Mist)",
            "25"  : "Beelzebub / NM150-200",
            "30"  : "Rose Queen (Dark)"
        }
        descs : list[str] = []
        for val, fights in dev_values.items():
            descs.append("**")
            descs.append(val)
            descs.append("**▫️ ")
            descs.append(fights)
            descs.append("\n")
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Defense Values",
                description="".join(descs),
                footer="20 def = Take half the damage of 10 def",
                color=self.COLOR,
                thumbnail=(
                    "https://prd-game-a-granbluefantasy.akamaized.net/"
                    "assets_en/img/sp/ui/icon/status/x64/status_1019.png"
                )
            )
        )
