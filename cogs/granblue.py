﻿import disnake
from disnake.ext import commands
import asyncio
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import html
import math
from views.url_button import UrlButton

# ----------------------------------------------------------------------------------------------------------------
# GranblueFantasy Cog
# ----------------------------------------------------------------------------------------------------------------
# All other Granblue Fantasy-related commands
# ----------------------------------------------------------------------------------------------------------------

class GranblueFantasy(commands.Cog):
    """Granblue Fantasy Utility."""
    COLOR = 0x34aeeb
    COLOR_NEWS = 0x00b07b
    SUMMON_ELEMENTS = ['misc', 'fire','water','earth','wind','light','dark']

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def startTasks(self) -> None:
        self.bot.runTask('granblue_watcher', self.granblue_watcher)

    """granblue_watcher()
    Bot Task checking for new content related to GBF
    """
    async def granblue_watcher(self) -> None:
        acc_check = False
        maint_check = False # False = no maintenance on going, True = maintenance on going
        v = None
        await asyncio.sleep(30)
        while True:
            # check
            try:
                t = int(self.bot.util.UTC().timestamp()) % 300
                await asyncio.sleep(355 - t)
                if not self.bot.running: return
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue_watcher' Task Cancelled")
                return

            try: # news checker
                news = await self.checkNews()
                if len(news) > 0: 
                    self.bot.logger.push("[GBF] {} new posts on the main website".format(len(news)), send_to_discord=False)
                for n in news:
                    try:
                        title = self.bot.net.translate(n[1])
                        footer = "Title from Google Translate"
                    except:
                        title = n[1]
                        footer = ""
                    await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(author={'name':"Granblue Fantasy News", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description="[{}]({})".format(title, n[0]), image=n[2], footer=footer, color=self.COLOR_NEWS))
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue_watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue_watcher (News)' Task Error:", e)

            try: # update check
                if maint_check:
                    if not await self.bot.net.gbf_maintenance(check_maintenance_end=True):
                        maint_check = False # maintenance ended
                        await self.bot.net.gbf_version() # update version
                        self.bot.data.save['gbfupdate'] = False
                        self.bot.data.pending = True
                    else:
                        continue # maintenance still on going
                else:
                    maint_check = await self.bot.net.gbf_maintenance(check_maintenance_end=True)
                if not maint_check and (self.bot.data.save['gbfupdate'] is True or (await self.bot.net.gbf_version()) == 3):
                    v = self.bot.data.save['gbfversion']
                    self.bot.logger.push("[GBF] The game has been updated to version {}".format(v), send_to_discord=False)
                    self.bot.data.save['gbfupdate'] = False
                    self.bot.data.pending = True
                    await self.bot.send("debug", embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description="Game has been updated to version `{} ({})`".format(v, self.bot.util.version2str(v)), color=self.COLOR))
                    await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description="Game has been updated", color=self.COLOR))
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue_watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue_watcher (Update)' Task Error:", e)

            if maint_check:
                continue

            acc = self.bot.net.get_account(self.bot.data.save['gbfcurrent'])
            if acc is None or acc[self.bot.net.ACC_STATE] == self.bot.net.ACC_STATUS_DOWN:
                if not acc_check:
                    acc_check = True
                    self.bot.logger.push("[TASK] 'granblue_watcher' checks will be skipped.\nPossible cause:\n- Game server is down (Check if it works)\n- Account is down (Try to set the cookie anew).\n- GBF Version check failed (See if other logs reported this issue).\n- Other undetermined causes.", level=self.bot.logger.WARNING)
                continue
            acc_check = False

            try: # 4koma news
                await self.check4koma()
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue_watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue_watcher (4koma)' Task Error:", e)

            try: # game news
                await self.checkGameNews()
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue_watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue_watcher (checkGameNews)' Task Error:", e)

    """checkGameNews()
    Coroutine checking for new in-game news, to post them in announcement channels
    """
    async def checkGameNews(self) -> None:
        # init
        try:
            if 'game_news' not in self.bot.data.save['gbfdata']:
                self.bot.data.save['gbfdata']['game_news'] = [7832]
                silent = True
                ncheck = 100
            else:
                ii = self.bot.data.save['gbfdata']['game_news'][0]
                silent = False
                ncheck = 10 + max(self.bot.data.save['gbfdata']['game_news']) - min(self.bot.data.save['gbfdata']['game_news'])
        except:
            ii = 7832
            silent = True
            ncheck = 100
        to_process = [i for i in range(ii, ii + ncheck) if i not in self.bot.data.save['gbfdata']['game_news']]
        # loop
        news = []
        for ii in to_process:
            data = await self.bot.net.requestGBF("news/news_detail/{}".format(ii), expect_JSON=True)
            if data is None:
                continue
            elif data[0]['id'] == str(ii):
                try:
                    news.append(ii)
                    if not silent:
                        if data[0]['title'].startswith('Grand Blues #') or 'Surprise Special Draw Set On Sale' in data[0]['title'] or 'Star Premium Draw Set On Sale' in data[0]['title']: continue
                        elif data[0]['title'].endswith(" Concluded"): limit = 40
                        elif data[0]['title'].endswith(" Premium Draw Update"): limit = 100
                        elif data[0]['title'].endswith(" Maintenance Completed"): limit = 50
                        elif data[0]['title'].endswith(" Added to Side Stories"): limit = 30
                        elif data[0]['title'].endswith(" Underway!"): limit = 30
                        else: limit = 250
                        description = data[0]['contents'].replace('</div>', '').replace('</span>', '').replace('<br>', '').replace('<Br>', '').replace('<ul>', '').replace('</ul>', '').replace('<li>', '').replace('</li>', '').replace('<i>', '*').replace('</i>', '*').replace('<b>', '**').replace('</b>', '**').replace('<u>', '__').replace('</u>', '__').replace('    ', '')
                        # first img
                        thumb = None
                        a = description.find('<img src="')
                        if a != -1:
                            b = description.find('"', a+10)
                            if b != -1:
                                tmp = description[a+10:b]
                                thumb = "https://prd-game-a-granbluefantasy.akamaized.net"
                                if tmp.startswith("assets"):
                                    thumb += "/" + tmp
                                elif tmp.startswith("http"):
                                    thumb = tmp
                                else:
                                    thumb += tmp
                        # remove div
                        cur = 0
                        while True:
                            a = description.find('<div', cur)
                            if a == -1: break
                            b = description.find('>', a)
                            if b == -1: break
                            description = description[:a] + description[b+1:]
                            cur = a
                        # remove span
                        cur = 0
                        while True:
                            a = description.find('<span', cur)
                            if a == -1: break
                            b = description.find('>', a)
                            if b == -1: break
                            description = description[:a] + description[b+1:]
                            cur = a
                        # first a
                        url = None
                        a = description.find('<a href="')
                        if a != -1:
                            b = description.find('"', a+9)
                            if b != -1:
                                url = "https://game.granbluefantasy.jp/" + description[a+9:b]
                        # remove a
                        cur = 0
                        while True:
                            a = description.find('<a ', cur)
                            if a == -1: break
                            b = description.find('/a>', a)
                            if b == -1: break
                            b += 2
                            description = description[:a] + description[b+1:]
                            cur = a
                        # remove font
                        cur = 0
                        while True:
                            a = description.find('<font ', cur)
                            if a == -1: break
                            b = description.find('/font>', a)
                            if b == -1: break
                            b += 5
                            description = description[:a] + description[b+1:]
                            cur = a
                        # remove img
                        cur = 0
                        while True:
                            a = description.find('<img ', cur)
                            if a == -1: break
                            b = description.find('>', a)
                            if b == -1: break
                            description = description[:a] + description[b+1:]
                            cur = a
                        description = description.replace('<li>', '**')
                        # remove comment
                        cur = 0
                        while True:
                            a = description.find('<!--', cur)
                            if a == -1: break
                            b = description.find('-->', a)
                            if b == -1: break
                            description = description[:a] + description[b+3:]
                            cur = a
                        description = description.replace('<li>', '**')
                        # final
                        elements = description.replace('\n\n', '\n').replace('\n\n', '\n').replace('\n\n', '\n').split('\n')
                        description = ""
                        for e in elements:
                            description += e + '\n'
                            if len(description) >= limit:
                                description += "[...]\n"
                                break
                        description += "\n[News Link](https://game.granbluefantasy.jp/#news/detail/{}/2/1/1)".format(ii)
                        # fixes for when intern kun mess up
                        if thumb is not None and '://' in thumb[8:]: thumb = None
                        if url is not None and '://' in url[8:]: url = None
                        await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(title=data[0]['title'].replace('<br>', ' '), description=description, url=url, image=thumb, timestamp=self.bot.util.UTC(), thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png", color=self.COLOR), publish=True)
                        # maintenance detect
                        if data[0]['title'].endswith(' Maintenance Announcement') and description.startswith("Server maintenance is scheduled for "):
                            try:
                                try: description = description.split('. ', 1)[0][len("Server maintenance is scheduled for "):].split(',')
                                except: description = description.split('. ', 1)[0][len("Server maintenance and game updates are scheduled for "):].split(',')
                                t = description[0].split(",", 1)[0]
                                u = t.split('–')
                                for e in range(len(u)):
                                    if 'noon' in u[e]: u[e] = '12 p.m.'
                                    elif 'midnight' in u[e]: u[e] = '0'
                                    u[e] = u[e].split(' ')
                                hour_start = int(u[0][0]) % 12
                                if len(u[0]) > 1 and u[0][1] == 'p.m.':
                                    hour_start += 12
                                hour_end = int(u[1][0]) % 12
                                if len(u[1]) > 1 and u[1][1] == 'p.m.':
                                    hour_end += 12
                                t = description[1].strip().split(" ")
                                day = int(t[1])
                                match t[0].lower():
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
                                    case _: raise Exception("Month Error")
                                t = description[2].strip().split(" ")
                                year = int(t[0])
                                self.bot.data.save['maintenance']['time'] = datetime.now().replace(year=year, month=month, day=day, hour=hour_start, minute=0, second=0, microsecond=0)
                                self.bot.data.save['maintenance']['duration'] = hour_end-hour_start
                                self.bot.data.save['maintenance']['state'] = True
                                self.bot.data.pending = True
                            except Exception as se:
                                self.bot.logger.pushError("[PRIVATE] 'checkGameNews (Maintenance)' Error:", se)
                except Exception as e:
                    self.bot.logger.pushError("[PRIVATE] 'checkGameNews' Error:", e)
                    return
        if len(news) > 0:
            self.bot.data.save['gbfdata']['game_news'] = self.bot.data.save['gbfdata']['game_news'] + news
            self.bot.data.save['gbfdata']['game_news'].sort()
            if len(self.bot.data.save['gbfdata']['game_news']) > 25:
                self.bot.data.save['gbfdata']['game_news'] = self.bot.data.save['gbfdata']['game_news'][max(0, len(self.bot.data.save['gbfdata']['game_news']) - 25):]
            self.bot.data.pending = True
            self.bot.logger.push("[GBF] {} new in-game News".format(len(news)), send_to_discord=False)

    """checkNews()
    Check for GBF news on the main site and update the save data.
    
    Returns
    --------
    list: List of new news
    """
    async def checkNews(self) -> list:
        res = []
        ret = []
        data = await self.bot.net.request("https://granbluefantasy.jp/news/index.php")
        if data is not None:
            soup = BeautifulSoup(data, 'html.parser')
            at = soup.find_all("article", class_="scroll_show_box")
            try:
                for a in at:
                    inner = a.findChildren("div", class_="inner", recursive=False)[0]
                    section = inner.findChildren("section", class_="content", recursive=False)[0]
                    h1 = section.findChildren("h1", recursive=False)[0]
                    url = h1.findChildren("a", class_="change_news_trigger", recursive=False)[0]

                    try:
                        mb25 = section.findChildren("div", class_="mb25", recursive=False)[0]
                        href = mb25.findChildren("a", class_="change_news_trigger", recursive=False)[0]
                        img = href.findChildren("img", recursive=False)[0].attrs['src']
                        if not img.startswith('http'):
                            if img.startswith('/'): img = 'https://granbluefantasy.jp' + img
                            else: img = 'https://granbluefantasy.jp/' + img
                    except:
                        img = None

                    res.append([url.attrs['href'], url.text, img])

                if 'news_url' in self.bot.data.save['gbfdata']:
                    foundNew = False
                    for i in range(0, len(res)):
                        found = False
                        for j in range(0, len(self.bot.data.save['gbfdata']['news_url'])):
                            if res[i][0] == self.bot.data.save['gbfdata']['news_url'][j][0]:
                                found = True
                                break
                        if not found:
                            ret.append(res[i])
                            foundNew = True
                    if foundNew:
                        self.bot.data.save['gbfdata']['news_url'] = res
                        self.bot.data.pending = True
                else:
                    self.bot.data.save['gbfdata']['news_url'] = res
                    self.bot.data.pending = True

            except:
                pass
        return ret

    """check4koma()
    Check for new GBF grand blues
    """
    async def check4koma(self) -> None:
        data = await self.bot.net.requestGBF('comic/list/1', expect_JSON=True)
        if data is None: return
        last = data['list'][0]
        if '4koma' in self.bot.data.save['gbfdata']:
            if last is not None and int(last['id']) > int(self.bot.data.save['gbfdata']['4koma']):
                self.bot.data.save['gbfdata']['4koma'] = last['id']
                self.bot.data.pending = True
                title = last['title_en']
                mtl = False
                if title == "":
                    try:
                        title = self.bot.net.translate(last['title'])
                        mtl = True
                    except:
                        title = last['title']
                await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(title=title, url="https://prd-game-a1-granbluefantasy.akamaized.net/assets/img/sp/assets/comic/episode/episode_{}.jpg".format(last['id']), image="https://prd-game-a1-granbluefantasy.akamaized.net/assets/img/sp/assets/comic/thumbnail/thum_{}.png".format(last['id'].zfill(5)), footer="Title from Google Translate" if mtl else "", color=self.COLOR), publish=True)
        else:
            self.bot.data.save['gbfdata']['4koma'] = last['id']
            self.bot.data.pending = True

    """checkExtraDrops()
    Check for GBF extra drops
    
    Returns
    --------
    list: List of ending time and element. Element is None if no extra drops is on going
    """
    async def checkExtraDrops(self) -> Optional[list]:
        try:
            c = self.bot.util.JST()
            extra = self.bot.data.save['gbfdata'].get('extradrop', None)
            if extra is None or c > extra[0]: # outdated/not valid
                r = await self.bot.net.requestGBF("rest/quest/adddrop_info", expect_JSON=True)
                if r is None: # no extra
                    self.bot.data.save['gbfdata']['extradrop'] = [c + timedelta(seconds=300), None] # next check in 5min, element set to unvalid
                    self.bot.data.pending = True
                    return None
                else:
                    elem_table = {'Tiamat':'wind', 'Colossus':'fire', 'Leviathan':'water', 'Yggdrasil':'earth', 'Aversa':'light', 'Luminiera':'light', 'Celeste':'dark'} # quest = element table
                    data = [None, None]
                    data[0] =  datetime.strptime(r['message_info']['ended_at'].replace(' (JST)', '').replace('a.m.', 'AM').replace('p.m.', 'PM'), '%I:%M %p, %b %d, %Y') # store end time
                    for e in r['quest_list']: # check quest name for element match
                        cs = e['quest_name'].split(' ')
                        for s in cs:
                            data[1] = elem_table.get(s, None)
                            if data[1] is not None: break
                        if data[1] is not None: break
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
    async def getGBFInfoTimers(self, inter: disnake.GuildCommandInteraction, current_time : datetime) -> str:
        output = []
        try:
            buf = await self.bot.net.gbf_maintenance_status()
            if len(buf) > 0:
                output.append(buf)
                output.append('\n')
        except:
            pass

        try:
            buf = await self.bot.gacha.get()
            if len(buf) > 0:
                output.append("{} Current {} ends in **{}**".format(self.bot.emote.get('SSR'), self.bot.util.command2mention('gbf gacha'), self.bot.util.delta2str(buf[1]['time'] - buf[0], 2)))
                if buf[1]['time'] != buf[1]['timesub']:
                    output.append(" (Spark period ends in **{}**)".format(self.bot.util.delta2str(buf[1]['timesub'] - buf[0], 2)))
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
                output.append(self.bot.util.command2mention("gw time"))
                output.append(")\n")
        except:
            pass

        try:
            buf = self.bot.get_cog('GuildWar').getNextBuff(inter)
            if len(buf) > 0:
                output.append(buf)
                output.append("\n")
        except:
            pass

        try:
            buf = await self.checkExtraDrops()
            if buf[1] is not None:
                output.append("{} Extra Drops end in **{}**\n".format(self.bot.emote.get(buf[1]), self.bot.util.delta2str(buf[0] - current_time, 2)))
        except:
            pass

        try:
            if current_time < self.bot.data.save['stream']['time']:
                output.append("{} {} on the **{}**\n".format(self.bot.emote.get('crystal'), self.bot.util.command2mention('gbf stream'), self.bot.util.time(self.bot.data.save['stream']['time'], style=['d','t'], removejst=True)))
        except:
            pass
        return ''.join(output)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 10, commands.BucketType.user)
    @commands.max_concurrency(16, commands.BucketType.default)
    async def gbf(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @gbf.sub_command()
    async def wiki(self, inter: disnake.GuildCommandInteraction, terms : str = commands.Param(description="Search expression")) -> None:
        """Search the GBF wiki"""
        await inter.response.defer()
        r = await self.bot.net.requestWiki("api.php", params={"action":"query", "format":"json", "list":"search", "srsearch":terms, "redirects":"return"})
        if r is None or len(r['query']['search']) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="Not Found, click here to refine", url="https://gbf.wiki/index.php?title=Special:Search&search={}".format(quote(terms)), color=self.COLOR))
            await self.bot.util.clean(inter, 40)
        else:
            try:
                page = r['query']['search'][0]
                title = page['title']
                tables = {'characters':'id,rarity,name,series,title,element,max_evo,join_weapon,profile,va', 'summons':'id,rarity,name,series,element,evo_max', 'weapons':'id,rarity,name,series,element,obtain,character_unlock,evo_max', 'classes':'id,name', 'npc_characters':'id,name,va,profile'}
                output = None
                for t, f in tables.items():
                    r = await self.bot.net.requestWiki("index.php", params={"title":"Special:CargoExport", "tables":t, "fields":"_pageName,{}".format(f), "format":"json", "where":'_pageName="{}"'.format(title)})
                    if r is None or len(r) == 0:
                        await asyncio.sleep(0.1)
                        continue
                    elem = r[0]
                    output = {}
                    output["url"] = "https://gbf.wiki/" + title.replace(" ", "_")
                    match t:
                        case 'characters':
                            output["desc"] = ""
                            if elem['profile'] is not None: output["desc"] += "*" + html.unescape(elem['profile']) + "*\n\n"
                            if elem['join weapon'] is not None:
                                jwpn = html.unescape(elem['join weapon'])
                                output["desc"] += "Weapon: [{}](https://gbf.wiki/index.php?title=Special:Search&search={})\n".format(jwpn, quote(jwpn))
                            output["desc"] += "[Assets](https://mizagbf.github.io/GBFAL/?id={})▫️[Animation](https://mizagbf.github.io/GBFAP/?id={})".format(elem["id"], elem["id"])
                            max_evo = elem["max evo"]
                            if max_evo is None or max_evo <= 4: max_evo = 1
                            else: max_evo -= 2
                            output["image"] = "https://prd-game-a3-granbluefantasy.akamaized.net/assets_en/img/sp/assets/npc/detail/{}_0{}.png".format(elem["id"], max_evo)
                            output["title"] = "{}{} {}".format(self.bot.emote.get(elem["rarity"]), self.bot.emote.get(elem["element"].lower()), html.unescape(elem["name"])) + (", {}".format(html.unescape(elem["title"])) if elem["title"] is not None else "") + (" [{}]".format(elem["series"].capitalize().replace(";", ", ")) if elem["series"] is not None else "")
                            output["footer"] = str(elem["id"])
                            if elem["va"] is not None: output["footer"] += " - " + elem["va"]
                        case 'summons':
                            output["desc"] = ""
                            output["desc"] += "[Assets](https://mizagbf.github.io/GBFAL/?id={})▫️[Animation](https://mizagbf.github.io/GBFAP/?id={})".format(elem["id"], elem["id"])
                            max_evo = elem["evo max"]
                            if max_evo is None or max_evo <= 3: max_evo = 1
                            else: max_evo -= 2
                            max_evo = "" if max_evo == 1 else "_0" + str(max_evo)
                            output["image"] = "https://prd-game-a3-granbluefantasy.akamaized.net/assets_en/img/sp/assets/summon/detail/{}{}.png".format(elem["id"], max_evo)
                            output["title"] = "{}{} {}".format(self.bot.emote.get(elem["rarity"]), self.bot.emote.get(elem["element"].lower()), html.unescape(elem["name"])) + (" [{}]".format(elem["series"].capitalize().replace(";", ", ")) if elem["series"] is not None else "")
                            output["footer"] = str(elem["id"])
                        case 'weapons':
                            output["desc"] = ""
                            if elem['obtain'] is not None:
                                if "[[" in elem['obtain']:
                                    otxt = html.unescape(elem['obtain']).split("[[", 1)[1].split("]]", 1)[0]
                                    output["desc"] += "Obtain: [{}](https://gbf.wiki/index.php?title=Special:Search&search={})\n".format(otxt, quote(otxt))
                                else:
                                    output["desc"] += "Obtain: {}\n".format(elem['obtain'].split(',', 1)[0].capitalize())
                            if elem['character unlock'] is not None:
                                chu = html.unescape(elem['character unlock'])
                                output["desc"] += "Unlock: [{}](https://gbf.wiki/index.php?title=Special:Search&search={})\n".format(chu, quote(chu))
                            output["desc"] += "[Assets](https://mizagbf.github.io/GBFAL/?id={})▫️[Animation](https://mizagbf.github.io/GBFAP/?id={})".format(elem["id"], elem["id"])
                            max_evo = elem["evo max"]
                            max_evo = "" if max_evo != 6 else "_03"
                            output["image"] = "https://prd-game-a3-granbluefantasy.akamaized.net/assets_en/img/sp/assets/weapon/m/{}{}.jpg".format(elem["id"], max_evo)
                            output["title"] = "{}{}{} {}".format(self.bot.emote.get(elem["rarity"]), self.bot.emote.get({'0': 'sword','1': 'dagger','2': 'spear','3': 'axe','4': 'staff','5': 'gun','6': 'melee','7': 'bow','8': 'harp','9': 'katana'}.get(str(elem["id"])[4], '')), self.bot.emote.get(elem["element"].lower()), html.unescape(elem["name"])) + (" [{}]".format(elem["series"].capitalize().replace(";", ", ")) if elem["series"] is not None else "")
                            output["footer"] = str(elem["id"])
                        case 'classes':
                            output["desc"] = ""
                            output["title"] = "{}".format(html.unescape(elem["name"]))
                            id = str(elem["id"]).split("_", 1)[0]
                            output["desc"] += "[Assets](https://mizagbf.github.io/GBFAL/?id={})▫️[Animation](https://mizagbf.github.io/GBFAP/?id={})".format(id, id)
                            output["image"] = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/leader/m/{}_01.jpg".format(id)
                            output["footer"] = str(id)
                        case 'npc_characters':
                            output["desc"] = ""
                            if elem['profile'] is not None: output["desc"] += "*" + html.unescape(elem['profile']) + "*\n\n"
                            output["desc"] += "[Assets](https://mizagbf.github.io/GBFAL/?id={})".format(elem["id"])
                            output["image"] = "https://prd-game-a3-granbluefantasy.akamaized.net/assets_en/img/sp/assets/npc/m/{}_01.jpg".format(elem["id"])
                            output["title"] = "{}".format(html.unescape(elem["name"])) 
                            output["footer"] = str(elem["id"])
                            if elem["va"] is not None and len(elem["va"]) > 0: output["footer"] += " - " + ",".join(elem["va"])
                    break
                if output is None:
                    output = {"title":html.unescape(title), "url":"https://gbf.wiki/" + title.replace(" ", "_"), "desc":"*Click to refine the search*"}
                await inter.edit_original_message(embed=self.bot.embed(title=output["title"], description=output.get("desc", None), image=output.get("image", None), url=output.get("url", None), footer=output.get("footer", None), color=self.COLOR))
                await self.bot.util.clean(inter, 80)
            except Exception as ex:
                self.bot.logger.pushError("[GBF] In 'gbf wiki' command:", ex)
                await inter.edit_original_message(embed=self.bot.embed(title="An error occured, click here to refine", url="https://gbf.wiki/index.php?title=Special:Search&search={}".format(quote(terms)), color=self.COLOR))
                await self.bot.util.clean(inter, 40)

    @gbf.sub_command()
    async def info(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post various Granblue Fantasy informations"""
        await inter.response.defer()
        current_time = self.bot.util.JST(delay=False)
        description = ["{} Current Time is **{}**".format(self.bot.emote.get('clock'), self.bot.util.time(style=['d','t'])),
                       "\n{} Japan Time is **{}**".format(self.bot.emote.get('clock'), current_time.strftime("%H:%M"))]

        if self.bot.data.save['gbfversion'] is not None:
            description.append("\n{} Version is `{}` (`{}`)".format(self.bot.emote.get('cog'), self.bot.data.save['gbfversion'], self.bot.util.version2str(self.bot.data.save['gbfversion'])))

        reset = current_time.replace(hour=5, minute=0, second=0, microsecond=0)
        if current_time.hour >= reset.hour:
            reset += timedelta(days=1)
        d = reset - current_time
        description.append("\n{} Reset in **{}**\n".format(self.bot.emote.get('mark'), self.bot.util.delta2str(d)))
        description.append(await self.getGBFInfoTimers(inter, current_time))

        await inter.edit_original_message(embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=''.join(description), color=self.COLOR))

    @gbf.sub_command()
    async def maintenance(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post GBF maintenance status"""
        try:
            await inter.response.defer()
            description = await self.bot.net.gbf_maintenance_status()
            if len(description) > 0:
                await inter.edit_original_message(embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=description, color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="Granblue Fantasy", description="No maintenance in my memory", color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'gbf maintenance' command:", e)

    @gbf.sub_command()
    async def stream(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the stream text"""
        await inter.response.defer(ephemeral=True)
        if self.bot.data.save['stream'] is None:
            await inter.edit_original_message(embed=self.bot.embed(title="No event or stream available", color=self.COLOR))
        else:
            msg = ""
            current_time = self.bot.util.JST()
            if self.bot.data.save['stream']['time'] is not None:
                if current_time < self.bot.data.save['stream']['time']:
                    d = self.bot.data.save['stream']['time'] - current_time
                    msg = "Stream starts in **{} ({})**\n".format(self.bot.util.delta2str(d, 2), self.bot.util.time(self.bot.data.save['stream']['time'], style=['d'], removejst=True))
                else:
                    msg = "Stream is **On going!! ({})**\n".format(self.bot.util.time(self.bot.data.save['stream']['time'], style=['d'], removejst=True))

            await inter.edit_original_message(embed=self.bot.embed(title=self.bot.data.save['stream']['title'], description=msg + self.bot.data.save['stream']['content'], timestamp=self.bot.util.UTC(), color=self.COLOR))

    @gbf.sub_command()
    async def schedule(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the GBF schedule"""
        await inter.response.defer()
        c = self.bot.util.UTC()
        events = {}
        next = None
        for event, dates in self.bot.data.save['schedule'].items():
            if dates[0] not in events:
                events[dates[0]] = []
            match len(dates):
                case 1:
                    start = datetime.utcfromtimestamp(dates[0])
                    diff = c - start
                    if c < start:
                        events[dates[0]].append("- {} ▫️ {}\n".format(event, self.bot.util.time(start, style=['d'])))
                        if next is None or start < next[0]:
                            next = [start, event]
                    elif diff > timedelta(days=1): # show as ended
                        events[dates[0]].append("- ~~{}~~\n".format(event))
                    elif diff > timedelta(days=3): # don't display
                        continue
                    else: # on going/happened
                        events[dates[0]].append("- **{}**\n".format(event))
                case 2:
                    start = datetime.utcfromtimestamp(dates[0])
                    end = datetime.utcfromtimestamp(dates[1])
                    if c < start:
                        events[dates[0]].append("- {} ▫️ {} - {}\n".format(event, self.bot.util.time(start, style=['d']), self.bot.util.time(end, style=['d'])))
                        if next is None or start < next[0]:
                            next = [start, event]
                    elif c >= end:
                        if c - end > timedelta(days=3): # don't display
                            continue
                        events[dates[0]].append("- ~~{}~~ ▫️ *Ended*\n".format(event))
                    else:
                        events[dates[0]].append("- **{}** ▫️ Ends in **{}** {}\n".format(event, self.bot.util.delta2str(end - c, 2), self.bot.util.time(end, style=['d'])))
                case _:
                    continue
        dates = list(events.keys())
        dates.sort()
        msgs = []
        for date in dates:
            msgs += events[date]
        if len(msgs) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="No schedule available", color=self.COLOR))
        else:
            msgs.append("{} Japan Time is **{}\n**".format(self.bot.emote.get('clock'), c.strftime("%I:%M %p")))
            if next is not None:
                if next[1].startswith("Update"):
                    next[1] = "update"
                elif next[1].startswith("Maintenance"):
                    next[1] = "maintenance"
                else:
                    next[1] = "event"
                msgs.append("{} Next {} approximately in **{}**\n".format(self.bot.emote.get('mark'), next[1], self.bot.util.delta2str(next[0] - c, 2)))
            msgs.append(await self.getGBFInfoTimers(inter, c))
            await inter.edit_original_message(embed=self.bot.embed(title="🗓 Event Schedule {} {}".format(self.bot.emote.get('clock'), self.bot.util.time(style=['d','t'])), url="https://gbf.wiki/", color=self.COLOR, description=''.join(msgs), footer="source: https://gbf.wiki/"))

    """getGrandList()
    Request the grand character list from the wiki page and return the list of latest released ones
    
    Returns
    ----------
    dict: Grand per element
    """
    async def getGrandList(self) -> dict:
        data = await self.bot.net.requestWiki("index.php", params={"title":"Special:CargoExport", "tables":"characters", "fields":"series,name,element,release_date", "where":'series = "grand"', "format":"json", "limit":"200"})
        if data is None:
            return {}
        grand_list = {'fire':None, 'water':None, 'earth':None, 'wind':None, 'light':None, 'dark':None}
        for c in data:
            try:
                if c['series'] != 'grand': continue
                grand = c
                d = grand['release date'].split('-')
                grand['release date'] = self.bot.util.UTC().replace(year=int(d[0]), month=int(d[1]), day=int(d[2]), hour=(12 if (int(d[2]) > 25) else 19), minute=0, second=0, microsecond=0)
                grand['element'] = grand['element'].lower()
                if grand_list[grand['element']] is None or grand['release date'] > grand_list[grand['element']]['release date']:
                    grand_list[grand['element']] = grand
            except:
                pass
        return grand_list

    @gbf.sub_command()
    async def gacha(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the current gacha informations"""
        try:
            await inter.response.defer()
            description, thumbnail = await self.bot.gacha.summary()
            if description is None: raise Exception('No Gacha')
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=description, thumbnail=thumbnail, color=self.COLOR))
        except Exception as e:
            if str(e) != 'No Gacha':
                self.bot.logger.pushError("[GBF] In 'gbf gacha' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description="Unavailable", color=self.COLOR))

    @gbf.sub_command_group()
    async def profile(self, inter: disnake.GuildCommandInteraction) -> None:
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
    def searchprofile(self, gbf_id : int) -> Optional[str]:
        try:
            return next(uid for uid, gid in self.bot.data.save['gbfids'].items() if gid == gbf_id)
        except:
            return None

    @profile.sub_command(name="unset")
    async def unsetprofile(self, inter: disnake.GuildCommandInteraction) -> None:
        """Unlink your GBF id"""
        await inter.response.defer(ephemeral=True)
        if str(inter.author.id) not in self.bot.data.save['gbfids']:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="You didn't set your GBF profile ID", color=self.COLOR))
            return
        try:
            del self.bot.data.save['gbfids'][str(inter.author.id)]
            self.bot.data.pending = True
        except:
            pass
        await inter.edit_original_message(embed=self.bot.embed(title="Your GBF profile has been unlinked", color=self.COLOR))

    @profile.sub_command(name="set")
    async def setprofile(self, inter: disnake.GuildCommandInteraction, profile_id : int = commands.Param(description="A valid GBF Profile ID. Usurpation will result in ban.", ge=0)) -> None:
        """Link your GBF id to your Discord ID"""
        try:
            await inter.response.defer(ephemeral=True)
            if self.bot.ban.check(inter.author.id, self.bot.ban.PROFILE):
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="You are banned to use this feature", color=self.COLOR))
                return
            if profile_id < 0 or profile_id >= 100000000:
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid ID", color=self.COLOR))
                return
            if not await self.bot.net.gbf_available():
                data = "Maintenance"
            else:
                data = await self.bot.net.requestGBF("profile/content/index/{}".format(profile_id), expect_JSON=True)
                if data is not None: data = unquote(data['data'])
            match data:
                case "Maintenance":
                    await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Game is in maintenance, try again later.", color=self.COLOR))
                    return
                case None:
                    await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Profile not found or Service Unavailable", color=self.COLOR))
                    return
                case _:
                    uid = self.searchprofile(profile_id)
                    if uid is not None:
                        if int(uid) == profile_id:
                            await inter.edit_original_message(embed=self.bot.embed(title="Information", description="Your profile is already set to ID `{}`.\nUse {} if you wish to remove it.".format(profile_id, self.bot.util.command2mention('gbf profile unset')), color=self.COLOR))
                        else:
                            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="This id is already in use, use {} if it's a case of griefing and send me the ID".format(self.bot.util.command2mention('bug_report')), color=self.COLOR))
                        return
            # register
            self.bot.data.save['gbfids'][str(inter.author.id)] = profile_id
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Success", description="Your ID `{}` is now linked to your Discord ID `{}`".format(profile_id, inter.author.id), color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'gbf profile set' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))

    """processProfile()
    Process profile data into discord embed elements
    
    Parameters
    ----------
    pid: Profile id
    data: Profile data
    
    Returns
    --------
    tuple: Containing:
        title: Discord embed title
        description: Discord embed description
        fields: Discord embed field
        thumbnail: main character thumbnail
    """
    async def processProfile(self, pid, data) -> None:
        soup = BeautifulSoup(data, 'html.parser')
        try: name = self.bot.util.shortenName(soup.find("span", class_="txt-other-name").string)
        except: name = None
        try: rank = "**Rank " + soup.find('div', class_='prt-user-name').get_text().split()[-1] + "**"
        except: name = ""
        rarity = "R"
        possible_headers = [("prt-title-bg-gld", "SSR"), ("prt-title-bg-slv", "SR"), ("prt-title-bg-nml", "R"), ("prt-title-bg-cpr", "R")]
        for h in possible_headers:
            try:
                if len(soup.find_all("div", class_=h[0])) > 0:
                    rarity = h[1]
                    break
            except:
                pass
        trophy = soup.find_all("div", class_="prt-title-name")[0].string
        comment = html.unescape(soup.find_all("div", class_="prt-other-comment")[0].string).replace('\t', '').replace('\n', '')
        if comment == "": pass
        elif rank == "": comment = "💬 `{}`".format(comment.replace('`', '\''))
        else: comment = " ▫️ 💬 `{}`".format(comment.replace('`', '\''))
        mc_url = soup.find_all("img", class_="img-pc")[0]['src'].replace("/po/", "/talk/").replace("/img_low/", "/img/")

        try:
            try:
                crew = self.bot.util.shortenName(soup.find_all("div", class_="prt-guild-name")[0].string)
                crewid = soup.find_all("div", class_="btn-guild-detail")[0]['data-location-href']
                crew = "[{}](https://game.granbluefantasy.jp/#{})".format(crew, crewid)
            except: crew = soup.find_all("div", class_="txt-notjoin")[0].string
        except:
            crew = None
        await asyncio.sleep(0)

        # get the last gw score
        scores = ""
        pdata = await self.bot.ranking.searchGWDB(pid, 2)
        for n in range(0, 2):
            try:
                pscore = pdata[n][0]
                if pscore.ranking is None: scores += "{} GW**{}** ▫️ **{:,}** honors\n".format(self.bot.emote.get('gw'), pscore.gw, pscore.current)
                else: scores += "{} GW**{}** ▫️ #**{}** ▫️ **{:,}** honors\n".format(self.bot.emote.get('gw'), pscore.gw, pscore.ranking, pscore.current)
            except:
                pass
        await asyncio.sleep(0)

        # support summons
        try:
            script = BeautifulSoup(soup.find("script", id="tpl-summon").get_text().replace(" <%=obj.summon_list.shift().viewClassName%>", ""), "html.parser")
            summon_list = [[] for i in range(7)]
            i = 0
            for x, e in enumerate(script.find_all("div", class_="prt-fix-support-wrap")):
                for y, v in enumerate(e.findChildren("div", class_="prt-fix-support", recursive=False)):
                    t = v.findChildren("div", recursive=False)[-1]
                    if "No support summon is set." not in t.get_text():
                        c = t.findChildren("div", recursive=False)
                        sname = c[0].get_text()
                        cname = c[1].get('class')[-1]
                        if 'bless-rank' in cname:
                            squal = "star{}".format(cname.split('bless-rank')[-1].split('-', 1)[0])
                        else:
                            squal = "star0"
                        summon_list[i].append((sname, squal))
                i += 1
            suppA = "{} **Support Summons**\n".format(self.bot.emote.get('summon'))
            suppB = ""
            for i, summons in enumerate(summon_list):
                tmp = "{} ".format(self.bot.emote.get(self.SUMMON_ELEMENTS[i]))
                for j, summon in enumerate(summons):
                    if j > 0: tmp += " ▫️ "
                    tmp += "{}{}".format(self.bot.emote.get(summon[1]), summon[0])
                if len(summons) == 0:
                    tmp += "None"
                tmp += "\n"
                if i == 0: suppB = tmp
                else: suppA += tmp
            summons = (suppA, suppB)
        except:
            summons = ("", "")
        await asyncio.sleep(0)

        # star chara
        try:
            pushed = soup.find("div", class_="prt-pushed")
            if pushed.find("div", class_="ico-augment2-s", recursive=True) is not None:
                star = "**\💍** "
            else:
                star = ""
            star += "{}".format(pushed.findChildren("span", class_="prt-current-npc-name", recursive=True)[0].get_text().strip()) # name
            if "Lvl" not in star: raise Exception()
            try: star += " **{}**".format(pushed.find("div", class_="prt-quality", recursive=True).get_text().strip()) # plus
            except: pass
            try: star += " ▫️ **{}** EMP".format(pushed.find("div", class_="prt-npc-rank", recursive=True).get_text().strip()) # emp
            except: pass
            try:
                starcom = pushed.find("div", class_="prt-pushed-info", recursive=True).get_text()
                if starcom != "" and starcom != "(Blank)": star += "\n\u202d💬 `{}`".format(starcom.replace('`', '\''))
            except: pass
            star = "\n{} **Star Character**\n{}".format(self.bot.emote.get('skill2'), star)
        except:
            star = ""
        await asyncio.sleep(0)

        if trophy == "No Trophy Displayed": title = "\u202d{} **{}**".format(self.bot.emote.get(rarity), name)
        else: title = "\u202d{} **{}**▫️{}".format(self.bot.emote.get(rarity), name, trophy)
        return title, "{}{}\n{} Crew ▫️ {}\n{}{}\n\n{}{}".format(rank, comment, self.bot.emote.get('gw'), crew, scores, star, summons[0], summons[1]), mc_url

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
    async def _profile(self, inter, pid, *, clean=True, color=None, view=None) -> None:
        if color is None: color = self.COLOR
        if not await self.bot.net.gbf_available():
            data = "Maintenance"
        else:
            data = await self.bot.net.requestGBF("profile/content/index/{}".format(pid), expect_JSON=True)
            if data is not None: data = unquote(data['data'])
        match data:
            case "Maintenance":
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Game is in maintenance", color=color), view=view)
                if clean:
                    await self.bot.util.clean(inter, 45)
                return
            case None:
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Profile not found or Service Unavailable", color=color), view=view)
                if clean:
                    await self.bot.util.clean(inter, 45)
                return
        soup = BeautifulSoup(data, 'html.parser')
        try: name = soup.find_all("span", class_="txt-other-name")[0].string
        except: name = None
        if name is None:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Profile is Private", color=color), view=view)
        else:
            title, description, thumbnail = await self.processProfile(pid, data)
            await inter.edit_original_message(embed=self.bot.embed(title=title, description=description, url="https://game.granbluefantasy.jp/#profile/{}".format(pid), thumbnail=thumbnail, inline=True, color=color), view=view)
        if clean:
            await self.bot.util.clean(inter, 45)

    @profile.sub_command()
    async def see(self, inter: disnake.GuildCommandInteraction, target : str = commands.Param(description="Either a valid GBF ID, discord ID or mention", default="")) -> None:
        """Retrieve a GBF profile"""
        try:
            await inter.response.defer()
            pid = await self.bot.util.str2gbfid(inter, target)
            if isinstance(pid, str):
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description=pid, color=self.COLOR))
            else:
                await self._profile(inter, pid)
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'gbf profile see' command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
        await self.bot.util.clean(inter, 60)

    @commands.user_command(name="GBF Profile")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 30, commands.BucketType.user)
    @commands.max_concurrency(4, commands.BucketType.default)
    async def gbfprofile(self, inter: disnake.UserCommandInteraction, member: disnake.Member) -> None:
        """Retrieve a GBF profile"""
        try:
            await inter.response.defer()
            pid = await self.bot.util.str2gbfid(inter, str(member.id), memberTarget=member)
            if isinstance(pid, str):
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description=pid, color=self.COLOR))
            else:
                await self._profile(inter, pid)
        except Exception as e:
            self.bot.logger.pushError("[GBF] In 'GBF Profile' user command:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
        await self.bot.util.clean(inter, 60)

    @gbf.sub_command_group(name="utility")
    async def _utility(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @_utility.sub_command()
    async def leechlist(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post a link to /gbfg/ leechlist collection"""
        await inter.response.defer()
        urls = [
            ('Anon #1 GW26-46', 'https://drive.google.com/open?id=1kfUi2GNcwXobEWnG_sdqPQu2r5YSLNpk'),
            ('Anon #2 GW47-58', 'https://drive.google.com/drive/folders/1f6DJ-u9D17CubY24ZHl9BtNv3uxTgPnQ'),
            ('My Data GW47-75', 'https://drive.google.com/drive/folders/18ZY2SHsa3CVTpusDHPg-IqNPFuXhYRHw')
        ]
        view = UrlButton(self.bot, urls)
        await inter.edit_original_message('\u200b', view=view)
        view.stopall()
        await self.bot.util.clean(inter, 60)

    @_utility.sub_command()
    async def spreadsheet(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post a link to my SpreadSheet Folder"""
        await inter.response.defer()
        view = UrlButton(self.bot, [('SpreadSheet Folder', 'https://drive.google.com/drive/folders/1p7rWQLJjVsoujQqYsJ0zVGUERMsQWmKn')])
        await inter.edit_original_message('\u200b', view=view)
        view.stopall()
        await self.bot.util.clean(inter, 60)

    @_utility.sub_command()
    async def xp(self, inter: disnake.GuildCommandInteraction, start_level : int = commands.Param(description="Starting Point of the calcul", ge=1, le=149, default=1), end_level : int = commands.Param(description="Final Point of the calcul", ge=1, le=150, default=1)) -> None:
        """Character experience calculator"""
        await inter.response.defer(ephemeral=True)
        xptable = [None, 30, 70, 100, 120, 140, 160, 180, 200, 220, 240, 260, 280, 300, 350, 400, 450, 500, 550, 600, 650, 700, 800, 900, 1000, 1100, 1200, 1300, 1400, 1500, 1600, 1700, 1800, 1900, 2000, 2100, 2200, 2400, 2600, 2800, 3000, 3200, 3400, 3600, 3800, 4000, 4200, 4400, 4600, 4800, 5000, 5250, 5500, 5750, 6000, 6250, 6500, 6750, 7000, 7250, 7500, 7800, 8100, 8400, 8700, 9000, 9500, 10000, 10500, 11000, 11500, 12000, 12500, 13000, 13500, 14000, 14500, 15000, 15500, 16000, 50000, 20000, 21000, 22000, 23000, 24000, 25000, 26000, 27000, 100000, 150000, 200000, 250000, 300000, 350000, 400000, 450000, 500000, 500000, 1000000, 1000000, 1200000, 1200000, 1200000, 1200000, 1200000, 1250000, 1250000, 1250000, 1250000, 1250000, 1300000, 1300000, 1300000, 1300000, 1300000, 1350000, 1350000, 1350000, 1350000, 1350000, 1400000, 1400000, 1400000, 1400000, 1400000, 1450000, 1450000, 1450000, 1450000, 1450000, 1500000, 1500000, 1500000, 1500000, 1500000, 1550000, 1550000, 1550000, 1550000, 1550000, 1600000, 1600000, 1600000, 1600000, 1600000, 1650000, 1650000, 1650000, 1650000, 0]
        if start_level < 1: start_level = 1
        elif start_level >= 150: start_level = 149
        msg = "From level **{}**, you need:\n".format(start_level)
        xpcount = xptable[start_level]
        for lvl in range(start_level+1, 151):
            if lvl in [80, 100, 110, 120, 130, 140, 150, end_level]:
                msg += "**{:,} XP** for lvl **{:}** ({:} books or {:,} candies)\n".format(xpcount, lvl, math.ceil(xpcount / 300000), math.ceil(xpcount / 745))
                if lvl == end_level: break
            xpcount += xptable[lvl]
        await inter.edit_original_message(embed=self.bot.embed(title="Experience Calculator", description=msg, color=self.COLOR))

    @_utility.sub_command()
    async def kirinanima(self, inter: disnake.GuildCommandInteraction, talisman : int = commands.Param(description="Talisman count", ge=0, le=100000, default=0), ream : int = commands.Param(description="Ream count", ge=0, le=100000, default=0), silver_anima : int = commands.Param(description="Silver Anima count", ge=0, le=100000, default=0), omega_anima : int = commands.Param(description="Omega Anima count", ge=0, le=100000, default=0)) -> None:
        """Calcul how many Omega animas of Kirin or Huanglong you own"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="Kirin Anima Calculator", description="You own the equivalent of **{}** Omega Animas".format(omega_anima + (ream+talisman//5+silver_anima)//10), thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img_low/sp/assets/item/article/s/{}.jpg".format([529, 531][int(datetime.now().timestamp())%2]), color=self.COLOR))

    @gbf.sub_command_group()
    async def check(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @check.sub_command()
    async def brand(self, inter: disnake.GuildCommandInteraction, target : str = commands.Param(description="Either a valid GBF ID, discord ID or mention", default="")) -> None:
        """Check if a GBF profile is restricted"""
        try:
            await inter.response.defer(ephemeral=True)
            id = await self.bot.util.str2gbfid(inter, target)
            if isinstance(id, str):
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description=id, color=self.COLOR))
            else:
                data = await self.bot.net.requestGBF("forum/search_users_id", expect_JSON=True, payload={"special_token":None,"user_id":int(id)})
                if data is None:
                    await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))
                else:
                    if len(data['user']) == 0:
                        await inter.edit_original_message(embed=self.bot.embed(title="Profile Error", description="In game message:\n`{}`".format(data['no_member_msg'].replace("<br>", " ")), url="https://game.granbluefantasy.jp/#profile/{}".format(id), color=self.COLOR))
                    else:
                        try:
                            if data['user']["restriction_flag_list"]["event_point_deny_flag"]:
                                status = "Account is restricted"
                            else:
                                status = "Account isn't restricted"
                        except:
                            status = "Account isn't restricted"
                        await inter.edit_original_message(embed=self.bot.embed(title="{} {}".format(self.bot.emote.get('gw'), self.bot.util.shortenName(data['user']['nickname'])), description=status, thumbnail="https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/leader/talk/{}.png".format(data['user']['image']), url="https://game.granbluefantasy.jp/#profile/{}".format(id), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))

    @check.sub_command()
    async def doom(self, inter: disnake.GuildCommandInteraction) -> None:
        """Give the time elapsed of various GBF related releases"""
        await inter.response.defer()
        msg = ""
        wiki_checks = ["Main_Quests", "Category:Campaign", "Surprise_Special_Draw_Set", "Damascus_Ingot", "Gold_Brick", "Sunlight_Stone", "Sephira_Evolite"]
        regexs = ["Time since last release\\s*<\/th><\/tr>\\s*<tr>\\s*<td colspan=\"3\" style=\"text-align: center;\">(\\d+ days)", "<td>(\\d+ days)<\\/td>\\s*<td>Time since last", "<td>(-\\d+ days)<\\/td>\\s*<td>Time since last", "<td>(\\d+ days)<\\/td>\\s*<td>Time since last", "<td>(\\d+ days)<\\/td>\\s*<td style=\"text-align: left;\">Time since last", "<td>(\\d+ days)<\\/td>\\s*<td style=\"text-align: center;\">\\?\\?\\?<\\/td>\\s*<td style=\"text-align: left;\">Time since last", "<td>(\\d+ days)<\\/td>\\s*<td style=\"text-align: center;\">\\?\\?\\?<\\/td>\\s*<td style=\"text-align: left;\">Time since last ", "<td style=\"text-align: center;\">\\?\\?\\?<\\/td>\\s*<td>(\\d+ days)<\\/td>\\s*"]
        for w in wiki_checks:
            t = await self.bot.net.requestWiki(w, allow_redirects=True)
            await asyncio.sleep(0.1) # to slow down the request a tiny bit
            if t is None:
                break
            try: t = t.decode('utf-8')
            except: t = t.decode('iso-8859-1')
            for r in regexs:
                if w == "Sunlight_Stone": # exception
                    ms = re.findall(r, t)
                    for i, m in enumerate(ms):
                        if i == 0: msg += "**{}** since the last [Sunlight Shard Sunlight Stone](https://gbf.wiki/Sunlight_Stone)\n".format(m)
                        elif i == 1: msg += "**{}** since the last [Arcarum Sunlight Stone](https://gbf.wiki/Sunlight_Stone)\n".format(m)
                    if len(ms) > 0:
                        break
                else:
                    m = re.search(r, t)
                    if m:
                        msg += "**{}** since the last [{}](https://gbf.wiki/{})\n".format(m.group(1), w.replace("_", " ").replace("Category:", "").replace('Sunlight', 'Arcarum Sunlight').replace('Sephira', 'Arcarum Sephira').replace('Gold', 'ROTB Gold'), w)
                        break

        # summer disaster
        c = self.bot.util.JST()
        msg += "**{} days** since the Summer Fortune 2021 results\n".format(self.bot.util.delta2str(c - c.replace(year=2021, month=8, day=16, hour=19, minute=0, second=0, microsecond=0), 3).split('d', 1)[0])
        msg += "**{} days** since the Settecide Day\n".format(self.bot.util.delta2str(c - c.replace(year=2023, month=11, day=9, hour=7, minute=0, second=0, microsecond=0), 3).split('d', 1)[0])
        msg += "**{} days** since {} KMR's retirement\n".format(self.bot.util.delta2str(c - c.replace(year=2024, month=7, day=27, hour=21, minute=0, second=0, microsecond=0), 3).split('d', 1)[0], self.bot.emote.get('kmr'))
        
        # grand
        try:
            grands = await self.getGrandList()
            for e in grands:
                msg += "**{} days** since {} [{}](https://gbf.wiki/{})\n".format(self.bot.util.delta2str(c - grands[e]['release date'], 3).split('d', 1)[0], self.bot.emote.get(e), grands[e]['name'], grands[e]['name'].replace(' ', '_'))
        except:
            pass

        if msg != "":
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=msg, footer="Source: http://gbf.wiki/", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))
        await self.bot.util.clean(inter, 40)

    @check.sub_command()
    async def coop(self, inter: disnake.GuildCommandInteraction) -> None:
        """Retrieve the current coop daily missions"""
        try:
            await inter.response.defer(ephemeral=True)
            data = (await self.bot.net.requestGBF('coopraid/daily_mission', expect_JSON=True))['daily_mission']
            msg = []
            for i in range(len(data)):
                if data[i]['category'] == '2':
                    items = {20011:'fire', 20012:'fire', 20111:'fire', 20021:'water', 20022:'water', 20121:'water', 20031:'earth', 20032:'earth', 20131:'earth', 20041:'wind', 20042:'wind', 20141:'wind'}
                    cid = int(data[i]['image'].split('/')[-1])
                    msg.append('{} {}\n'.format(self.bot.emote.get(items.get(cid, 'misc')), data[i]['description']))
                elif data[i]['category'] == '1':
                    quests = {'s00101':'wind', 's00104':'wind', 's00204':'wind', 's00206':'wind', 's00301':'fire', 's00303':'fire', 's00405':'fire', 's00406':'fire', 's00601':'water', 's00602':'water', 's00604':'water', 's00606':'water', 's00802':'earth', 's00704':'earth', 's00705':'earth', 's00806':'earth', 's01005':'wind', 's00905':'wind', 's00906':'wind', 's01006':'wind', 's01105':'fire', 's01403':'fire', 's01106':'fire', 's01206':'fire', 's01001':'water', 's01502':'water', 's01306':'water', 's01406':'water', 's01601':'earth', 's01405':'earth', 's01506':'earth', 's01606':'earth'}
                    cid = data[i]['image'].split('/')[-1]
                    msg.append('{} {}\n'.format(self.bot.emote.get(quests.get(cid, 'misc')), data[i]['description']))
                else:
                    msg.append('{} {}\n'.format(self.bot.emote.get(str(i+1)), data[i]['description']))
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"Daily Coop Missions", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=''.join(msg), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))

    @check.sub_command()
    async def koregra(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the time to the next monthly dev post"""
        await inter.response.defer()
        c = self.bot.util.JST()
        m = c.replace(day=1, hour=12, minute=0, second=0, microsecond=0)
        while m < c:
            m += timedelta(days=1)
        try:
            if c < self.bot.data.save['stream']['time'] and self.bot.data.save['stream']['time'] < (m + timedelta(days=1)):
                m = (self.bot.data.save['stream']['time'] + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        except:
            pass
        await inter.edit_original_message(embed=self.bot.embed(title="{} Kore Kara".format(self.bot.emote.get('clock')), description="Release approximately in **{}**".format(self.bot.util.delta2str(m - c, 2)),  url="https://granbluefantasy.jp/news/index.php", thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png", color=self.COLOR))

    @check.sub_command()
    async def news(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the latest news posts"""
        await inter.response.defer(ephemeral=True)
        if 'news_url' not in self.bot.data.save['gbfdata']:
            self.bot.data.save['gbfdata']['news_url'] = []
            self.bot.data.pending = True
        msg = ""
        for i in range(len(self.bot.data.save['gbfdata']['news_url'])):
            msg += "{} [{}]({})\n".format(self.bot.emote.get(str(i+1)), self.bot.data.save['gbfdata']['news_url'][i][1], self.bot.data.save['gbfdata']['news_url'][i][0])
        try:
            thumb = self.bot.data.save['gbfdata']['news_url'][0][2]
            if not thumb.startswith('http://granbluefantasy.jp') and not thumb.startswith('https://granbluefantasy.jp'):
                if thumb.startswith('/'): thumb = 'https://granbluefantasy.jp' + thumb
                else: thumb = 'https://granbluefantasy.jp/' + thumb
        except: thumb = None
        if msg == "":
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"Latest Granblue Fantasy News", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=msg, image=thumb, color=self.COLOR))

    @check.sub_command()
    async def granblues(self, inter: disnake.GuildCommandInteraction, episode : int = commands.Param(description="A Grand Blues! episode number", default=1, ge=1, le=99999)) -> None:
        """Post a Granblues Episode"""
        try:
            await inter.response.defer(ephemeral=True)
            if (await self.bot.net.request("https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/comic/episode/episode_{}.jpg".format(episode))) is None: raise Exception()
            await inter.edit_original_message(embed=self.bot.embed(title="Grand Blues! Episode {}".format(episode), url="https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/comic/episode/episode_{}.jpg".format(episode), image="https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/comic/thumbnail/thum_{}.png".format(str(episode).zfill(5)), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid Grand Blues! number", color=self.COLOR))

    @gbf.sub_command_group()
    async def campaign(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @campaign.sub_command()
    async def crystal(self, inter: disnake.GuildCommandInteraction) -> None:
        """Granblue Summer Festival - Crystal Countdown 2023"""
        await inter.response.defer()
        try:
            c = self.bot.util.JST()
            # settings
            start = c.replace(year=2023, month=8, day=1, hour=5, minute=0, second=0, microsecond=0)
            end = c.replace(year=2023, month=8, day=13, hour=4, minute=59, second=59, microsecond=0)
            maxwave = 2
            crystal_per_wave = 5000000000
            # end settings
            footer = ""
            if c > end or self.bot.data.save['extra'].get('campaign/dividecrystal', {}).get('wave', 9999) > maxwave:
                msg = "The event has ended for this year."
            elif c < start:
                msg = "The event hasn't started."
            else:
                if 'campaign/dividecrystal' not in self.bot.data.save['extra']:
                    self.bot.data.save['extra']['campaign/dividecrystal'] = {'wave':1, 'expire':end}
                try:
                    data = unquote((await self.bot.net.requestGBF("campaign/dividecrystal/content/index", expect_JSON=True))['data'])
                except Exception as tmp:
                    if maxwave > 1 and self.bot.data.save['extra']['campaign/dividecrystal']['wave'] < maxwave and (c - start).days > 2:
                        try:
                            await self.bot.net.requestGBF("campaign/dividecrystal/content/bonus_present", expect_JSON=True)
                            data = unquote((await self.bot.net.requestGBF("campaign/dividecrystal/content/index", expect_JSON=True))['data'])
                            self.bot.data.save['extra']['campaign/dividecrystal']['wave'] += 1
                            self.bot.data.pending = True
                        except:
                            raise tmp
                    elif self.bot.data.save['extra']['campaign/dividecrystal']['wave'] == maxwave: # likely triggered by the end
                        try:
                            await self.bot.net.requestGBF("campaign/dividecrystal/content/bonus_present", expect_JSON=True)
                            data = unquote((await self.bot.net.requestGBF("campaign/dividecrystal/content/index", expect_JSON=True))['data'])
                        except:
                            raise tmp
                    else:
                        raise tmp
                s = data.find('<div class="txt-amount">')
                if s == -1: raise Exception()
                s += len('<div class="txt-amount">')
                ds = data[s:].split('/')
                crystal = int(ds[0].replace(',', ''))
                available_crystal = int(ds[1].replace(',', '').replace('<', ''))
                if maxwave > 1:
                    if data.find('<div class="prt-wave-{}">'.format(self.bot.data.save['extra']['campaign/dividecrystal']['wave'])) == -1 and data.find('<div class="prt-wave-{}">'.format(self.bot.data.save['extra']['campaign/dividecrystal']['wave'] + 1)) != -1:
                        # additional wave change check
                        self.bot.data.save['extra']['campaign/dividecrystal']['wave'] += 1
                        self.bot.data.pending = True
                    footer += "Part {}/{}".format(self.bot.data.save['extra']['campaign/dividecrystal']['wave'], maxwave)
                    available_crystal = crystal_per_wave * maxwave
                    crystal += crystal_per_wave * (maxwave - self.bot.data.save['extra']['campaign/dividecrystal']['wave'])

                if crystal <= 0:
                    msg = "{} No crystals remaining".format(self.bot.emote.get('crystal'))
                else:
                    consumed = (available_crystal - crystal)
                    avg_completion_crystal = 1600
                    players = (consumed / ((c - start).days + 1)) / avg_completion_crystal
                    msg = "{:} **{:,}** crystals remaining (Average **{:}** players/day, at {:,} crystals average).\n".format(self.bot.emote.get('crystal'), crystal, self.bot.util.valToStr(players), avg_completion_crystal)
                    msg += "{} Event is ending in **{}**.\n".format(self.bot.emote.get('clock'), self.bot.util.delta2str(end - c, 2))
                    elapsed = c - start
                    duration = end - start
                    progresses = [100 * (consumed / available_crystal), 100 * (elapsed.days * 86400 + elapsed.seconds) / (duration.days * 86400 + duration.seconds)]
                    msg += "Progress ▫️ **{:.2f}%** {:} ▫️ **{:.2f}%** {:} ▫️ ".format(progresses[0], self.bot.emote.get('crystal'), progresses[1], self.bot.emote.get('clock'))
                    if progresses[1] > progresses[0]:
                        msg += "✅\n" # white check mark
                        leftover = available_crystal * (100 - (progresses[0] * 100 / progresses[1])) / 100
                        eligible = int(players * 1.1)
                        msg += "Estimating between **{:,}** and **{:,}** bonus crystals/player at the end.".format(int(leftover / eligible), int(leftover / 550000))
                        if footer != "": footer += " - "
                        footer += "Assuming ~{} eligible players.".format(self.bot.util.valToStr(eligible))
                    else:
                        msg += "⚠️\n"
                        t = timedelta(seconds = (duration.days * 86400 + duration.seconds) * (100 - (progresses[1] * 100 / progresses[0])) / 100)
                        msg += "Crystals will run out in **{}** at current pace.".format(self.bot.util.delta2str(end - t - c, 2))
        except Exception as e:
            msg = "An error occured, try again later."
            self.bot.logger.pushError("[GBF] 'crystal' error:", e)
        await inter.edit_original_message(embed=self.bot.embed(title="Granblue Summer Festival", description=msg, url="https://game.granbluefantasy.jp/#campaign/division", footer=footer, color=self.COLOR))

    @campaign.sub_command()
    async def element(self, inter: disnake.GuildCommandInteraction) -> None:
        """Granblue Summer Festival - Skyfarer Assemble 2024"""
        await inter.response.defer()
        try:
            c = self.bot.util.JST()
            # settings
            start = c.replace(year=2024, month=8, day=1, hour=5, minute=0, second=0, microsecond=0)
            end = c.replace(year=2024, month=8, day=13, hour=4, minute=59, second=59, microsecond=0)
            # end settings
            footer = ""
            if c > end:
                msg = "The event has ended for this year."
            elif c < start:
                msg = "The event hasn't started."
            else:
                data = await self.bot.net.requestGBF("rest/campaign/accumulatebattle/point_list", expect_JSON=True)
                msg = ["Goal ▫️ **{:,}**".format(data["goal"])]
                elems = {"1":"fire", "2":"water", "3":"earth", "4":"wind", "5":"light", "6":"dark"}
                for k, v in data["total"].items():
                    if v >= data['goal']:
                        msg.append("{:} ▫️ **{:,}** {:}".format(self.bot.emote.get(elems.get(k, k)), v, self.bot.emote.get('crown')))
                    else:
                        msg.append("{:} ▫️ **{:,}** ({:.2f}%)".format(self.bot.emote.get(elems.get(k, k)), v, 100*v/data['goal']))
                msg.append("{} Event is ending in **{}**.".format(self.bot.emote.get('clock'), self.bot.util.delta2str(end - c, 2)))
                msg = '\n'.join(msg)
        except Exception as e:
            msg = "An error occured, try again later."
            self.bot.logger.pushError("[GBF] 'element' error:", e)
        await inter.edit_original_message(embed=self.bot.embed(title="Granblue Summer Festival", description=msg, url="https://game.granbluefantasy.jp/#campaign/accumulatebattle", footer=footer, color=self.COLOR))

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def guide(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @guide.sub_command()
    async def defense(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post some known defense values"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="Defense Values", description="**8.5**▫️ Fediel Solo\n**9.5**▫️ Fediel HL\n**10** ▫️ Estimate Calculator / Trial / Story / Event / EX+\n**11** ▫️ PBaha N / UBaha HL / Xeno\n**12** ▫️ M1 HL / Kirin HL / Metatron / Avatar / GO HL / Lindwurm\n**13** ▫️ Normal / Hard / T2 / Primarchs N & HL / UBaha N / M2\n**15** ▫️ T1 HL / Malice / Menace / Akasha / Lucilius / Astaroth / Pride / NM90-100 / Other Dragon Solos\n**18** ▫️ Rose Queen / Other Dragons HL\n**20** ▫️ PBaha HL / Lucilius Hard / Belial\n**22** ▫️ Celeste (Mist)\n**25** ▫️ Beelzebub / NM150-200\n**30** ▫️ Rose Queen (Dark)", footer="20 def = Take half the damage of 10 def", color=self.COLOR, thumbnail="https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/ui/icon/status/x64/status_1019.png"))