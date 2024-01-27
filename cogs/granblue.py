import disnake
from disnake.ext import commands
import asyncio
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from datetime import datetime, timedelta
import re
from bs4 import BeautifulSoup
from bs4 import element as bs4element
from urllib import parse
from urllib.parse import unquote
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
    SUMMON_ELEMENTS = ['fire','water','earth','wind','light','dark','misc']

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def startTasks(self) -> None:
        self.bot.runTask('granblue_watcher', self.granblue_watcher)

    """granblue_watcher()
    Bot Task checking for new content related to GBF
    """
    async def granblue_watcher(self) -> None:
        maint_check = 0 # 0 = no maintenance on going, 1 = maintenance on going, 2 = maintenance on going & task done
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
                if maint_check == 2:
                    if not await self.bot.net.gbf_maintenance(check_maintenance_end=True):
                        maint_check = 0 # maintenance ended
                        await self.bot.net.gbf_version() # update version
                        self.bot.data.save['gbfupdate'] = False
                        self.bot.data.pending = True
                    else:
                        continue # maintenance still on going
                else:
                    maint_check = int(await self.bot.net.gbf_maintenance(check_maintenance_end=True))
                run_check = False
                if maint_check == 0 and (self.bot.data.save['gbfupdate'] is True or (await self.bot.net.gbf_version()) == 3):
                    v = self.bot.data.save['gbfversion']
                    self.bot.data.save['gbfupdate'] = False
                    self.bot.data.pending = True
                    run_check = True
                elif maint_check == 1 and (self.bot.util.UTC().minute % 20) < 5: # every 20 min
                    run_check = True
                if run_check:
                    try: maint_check = await (self.bot.get_cog('Private').analysis(v, maint_check))
                    except: pass

            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'granblue_watcher' Task Cancelled")
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'granblue_watcher (Update)' Task Error:", e)

            if maint_check > 0:
                continue

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
                self.bot.data.save['gbfdata']['game_news'] = [6329]
                silent = True
                ncheck = 100
            else:
                ii = self.bot.data.save['gbfdata']['game_news'][0]
                silent = False
                ncheck = 10 + max(self.bot.data.save['gbfdata']['game_news']) - min(self.bot.data.save['gbfdata']['game_news'])
        except:
            ii = 6329
            silent = True
            ncheck = 100
        to_process = []
        for i in range(ii, ii + ncheck):
            if i not in self.bot.data.save['gbfdata']['game_news']:
                to_process.append(i)
        # loop
        news = []
        for ii in to_process:
            data = await self.bot.net.request("https://game.granbluefantasy.jp/news/news_detail/{}?PARAMS".format(ii), account=self.bot.data.save['gbfcurrent'], expect_JSON=True)
            if data is None:
                continue # interrupt
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
                                thumb = "https://prd-game-a-granbluefantasy.akamaized.net" + description[a+10:b]
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
                        await self.bot.sendMulti(self.bot.channel.announcements, embed=self.bot.embed(title=data[0]['title'], description=description, url=url, image=thumb, timestamp=self.bot.util.UTC(), thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png", color=self.COLOR), publish=True)
                        if data[0]['title'].endswith(' Maintenance Announcement') and description.startswith("Server maintenance is scheduled for "):
                            try:
                                try: description = description.split('. ')[0][len("Server maintenance is scheduled for "):].split(',')
                                except: description = description.split('. ')[0][len("Server maintenance and game updates are scheduled for "):].split(',')
                                t = description[0].split(",")[0]
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
        data = await self.bot.net.request("https://granbluefantasy.jp/news/index.php", no_base_headers=True)
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
        data = await self.bot.net.request('https://game.granbluefantasy.jp/comic/list/1?PARAMS', account=self.bot.data.save['gbfcurrent'], expect_JSON=True)
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

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 10, commands.BucketType.user)
    @commands.max_concurrency(16, commands.BucketType.default)
    async def gbf(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    """stripWikiStr()
    Formating function for wiki skill descriptions
    
    Parameters
    ----------
    elem: String, html element
    
    Returns
    --------
    str: Stripped string
    """
    def stripWikiStr(self, elem : bs4element.Tag) -> str:
        txt = elem.text.replace('foeBoost', 'foe. Boost') # special cases
        checks = [['span', 'tooltiptext'], ['sup', 'reference'], ['span', 'skill-upgrade-text']]
        for target in checks:
            f = elem.findChildren(target[0], class_=target[1])
            for e in f:
                txt = txt.replace(e.text, "")
        return txt.replace('Slight', '_sligHt_').replace('C.A.', 'CA').replace('.', '. ').replace('!', '! ').replace('?', '? ').replace(':', ': ').replace('. )', '.)').replace("Damage cap", "Cap").replace("Damage", "DMG").replace("damage", "DMG").replace(" and ", " and").replace(" and", " and ").replace("  ", " ").replace("fire", str(self.bot.emote.get('fire'))).replace("water", str(self.bot.emote.get('water'))).replace("earth", str(self.bot.emote.get('earth'))).replace("wind", str(self.bot.emote.get('wind'))).replace("dark", str(self.bot.emote.get('dark'))).replace("light", str(self.bot.emote.get('light'))).replace("Fire", str(self.bot.emote.get('fire'))).replace("Water", str(self.bot.emote.get('water'))).replace("Earth", str(self.bot.emote.get('earth'))).replace("Wind", str(self.bot.emote.get('wind'))).replace("Dark", str(self.bot.emote.get('dark'))).replace("Light", str(self.bot.emote.get('light'))).replace('_sligHt_', 'Slight')

    """processWikiMatch()
    Process a successful wiki search match
    
    Parameters
    ----------
    soup: beautifulsoup object
    
    Returns
    --------
    tuple: Containing:
        - data: Dict containing the match data
        - tables: List of wikitables on the page
    """
    async def processWikiMatch(self, soup : BeautifulSoup) -> tuple:
        data = {}
        # what we are interested in
        type_check = {"/Category:Fire_Characters":0, "/Category:Water_Characters":1, "/Category:Earth_Characters":2, "/Category:Wind_Characters":3, "/Category:Dark_Characters":4, "/Category:Light_Characters":5, "/Category:Special_Characters":6, "/Category:Fire_Summons":10, "/Category:Water_Summons":11, "/Category:Earth_Summons":12, "/Category:Wind_Summons":13, "/Category:Dark_Summons":14, "/Category:Light_Summons":15, "/Category:Special_Summons":16, "/Category:Sabre_Weapons":20, "/Category:Dagger_Weapons":21, "/Category:Spear_Weapons":22, "/Category:Axe_Weapons":23, "/Category:Staff_Weapons":24, "/Category:Gun_Weapons":25, "/Category:Melee_Weapons":26, "/Category:Bow_Weapons":27, "/Category:Harp_Weapons":28, "/Category:Katana_Weapons":29}
        for k, n in type_check.items(): # check if the page matches
            r = soup.find_all("a", {'href' : k})
            if len(r) > 0:
                data['object'] = n // 10 # 0 = chara, 1 = summon, 2 = weapon
                if data['object'] < 2: data['element'] = {0:'fire', 1:'water', 2:'earth', 3:'wind', 4:'dark', 5:'light', 6:'misc'}.get(n%10, "") # retrieve the element here for chara and summon
                else: data['type'] = k[len('/Category:'):k.find('_Weapons')].lower().replace('sabre', 'sword') # retrieve the wpn type here
                break

        # retrieve ID
        tables = soup.find_all("table", class_='wikitable') # iterate all wikitable
        for t in tables:
            await asyncio.sleep(0)
            try:
                body = t.findChildren("tbody" , recursive=False)[0].findChildren("tr" , recursive=False) # check for tr tag
                for tr in body:
                    if str(tr).find("ID") != -1:
                        try:
                            if tr.findChildren("th")[0].text.strip() == "ID" and 'id' not in data:
                                data['id'] = tr.findChildren("td")[0].text.replace(' ', '')
                                if len(data['id']) == 10:
                                    match data['id'][0]:
                                        case '1':
                                            data['image'] = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/weapon/m/{}.jpg".format(data['id'])
                                        case '2':
                                            data['image'] = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/summon/m/{}.jpg".format(data['id'])
                                        case '3':
                                            data['image'] = "https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/npc/m/{}_01.jpg".format(data['id'])
                                        case _:
                                            pass
                        except:
                            pass
            except:
                pass

        # retrieve description
        try: data['description'] = soup.find_all("meta", {'name' : 'description'})[0].attrs['content']
        except: pass

        # get rarity, title and name
        try: 
            header = soup.find_all("div", class_='char-header')[0] # get it
            try: # first we get the rarity
                data['rarity'] = str(header.findChildren("div" , class_='char-rarity', recursive=False)[0])
                if data['rarity'].find("Rarity SSR") != -1: data['rarity'] = "SSR"
                elif data['rarity'].find("Rarity SR") != -1: data['rarity'] = "SR"
                elif data['rarity'].find("Rarity R") != -1: data['rarity'] = "R"
                else: data['rarity'] = ""
            except:
                pass
            for child in header.findChildren("div" , recursive=False): # then the name and title if any
                if 'class' not in child.attrs:
                    for divs in child.findChildren("div" , recursive=False):
                        if 'class' in divs.attrs:
                            if 'char-name' in divs.attrs['class']: data['name'] = divs.text
                            elif 'char-title' in divs.attrs['class']:
                                try:
                                    tx = divs.findChildren("span", recursive=False)[0].text
                                    data['title'] = tx[1:tx.find("]")]
                                except:
                                    tx = divs.text
                                    data['title'] = tx[1:tx.find("]")]
        except:
            pass
        return data, tables

    """processWikiItem()
    Process the processWikiMatch() wikitables and add the result into data
    
    Parameters
    ----------
    data: processWikiMatch() data
    tables: processWikiMatch() tables
    
    Returns
    --------
    dict: Updated data (not a copy)
    """
    async def processWikiItem(self, data : dict, tables : bs4element.ResultSet) -> dict:
        # iterate all wikitable again
        for t in tables:
            await asyncio.sleep(0)
            body = t.findChildren("tbody" , recursive=False)[0].findChildren("tr" , recursive=False) # check for tr tag
            if str(body).find("Copyable?") != -1: continue # for chara skills if I add it one day
            expecting_hp = False
            expecting_wpn_skill = False
            expecting_sum_call = False
            aura = 0
            for tr in body: # iterate on tags
                await asyncio.sleep(0)
                content = str(tr)
                if expecting_sum_call:
                    if content.find("This is the call for") != -1 or content.find("This is the basic call for") != -1:
                        try: data['call'][1] = self.stripWikiStr(tr.findChildren("td")[0])
                        except: pass
                    else:
                        expecting_sum_call = False
                elif expecting_wpn_skill:
                    if 'class' in tr.attrs and tr.attrs['class'][0].startswith('skill'):
                        if tr.attrs['class'][-1] == "post" or (tr.attrs['class'][0] == "skill" and len(tr.attrs['class']) == 1):
                            try: 
                                n = tr.findChildren("td", class_="skill-name", recursive=False)[0].text.replace("\n", "")
                                d = tr.findChildren("td", class_="skill-desc", recursive=False)[0]
                                if 'skill' not in data: data['skill'] = []
                                data['skill'].append([n, self.stripWikiStr(d)])
                            except: pass
                    else:
                        expecting_wpn_skill = False
                elif expecting_hp:
                    if content.find('Level ') != -1:
                        childs = tr.findChildren(recursive=False)
                        try: data['lvl'] = childs[0].text[len('Level '):]
                        except: pass
                        try: data['hp'] = childs[1].text
                        except: pass
                        try: data['atk'] = childs[2].text
                        except: pass
                    else:
                        expecting_hp = False
                elif content.find('class="hp-text"') != -1 and content.find('class="atk-text"') != -1:
                    try:
                        expecting_hp = True
                        elem_table = {"/Weapon_Lists/SSR/Fire":"fire", "/Weapon_Lists/SSR/Water":"water", "/Weapon_Lists/SSR/Earth":"earth", "/Weapon_Lists/SSR/Wind":"wind", "/Weapon_Lists/SSR/Dark":"dark", "/Weapon_Lists/SSR/Light":"light"}
                        for s, e in elem_table.items():
                            if content.find(s) != -1:
                                data['element'] = e
                                break
                    except: pass
                elif content.find('"Skill charge attack.png"') != -1:
                    try:
                        n = tr.findChildren("td", class_="skill-name", recursive=False)[0].text
                        d = tr.findChildren("td", recursive=False)[-1]
                        data['ca'] = [n, self.stripWikiStr(d)]
                    except: pass
                elif content.find('"/Weapon_Skills"') != -1:
                    expecting_wpn_skill = True
                elif content.find('<a href="/Sword_Master" title="Sword Master">Sword Master</a>') != -1 or content.find('Status_Energized') != -1:
                    try:
                        tds = tr.findChildren("td", recursive=False)
                        n = tds[0].text
                        d = tds[1]
                        if 'sm' not in data: data['sm'] = []
                        data['sm'].append([n, self.stripWikiStr(d)])
                    except: pass
                elif content.find('"/Summons#Calls"') != -1:
                    try:
                        data['call'] = [tr.findChildren("th")[0].text[len("Call - "):], '']
                        expecting_sum_call = True
                    except: pass
                elif content.find("Main Summon") != -1:
                    aura = 1
                elif content.find("Sub Summon") != -1:
                    aura = 2
                elif content.find("This is the basic aura") != -1:
                    try:
                        if aura == 0: aura = 1
                        n = tr.findChildren("span", class_="tooltip")[0].text.split("This is the basic aura")[0]
                        d = tr.findChildren("td")[0]
                        if aura == 1: data['aura'] = self.stripWikiStr(d)
                        elif aura == 2: data['subaura'] = self.stripWikiStr(d)
                    except: pass
                elif content.find("This is the aura") != -1:
                    try:
                        n = tr.findChildren("span", class_="tooltip")[0].text.split("This is the aura")[0]
                        d = tr.findChildren("td")[0]
                        if aura == 1: data['aura'] = self.stripWikiStr(d)
                        elif aura == 2: data['subaura'] = self.stripWikiStr(d)
                    except: pass
        return data

    """requestWiki()
    Request a wiki page and post the result after calling processWikiMatch() and processWikiItem()
    
    Parameters
    ----------
    inter: Command interaction
    url: Wiki url to request (url MUST be for gbf.wiki)
    search_mode: Boolean, if True it expects a search result page
    """
    async def requestWiki(self, inter: disnake.GuildCommandInteraction, url : str, search_mode : bool = False) -> None:
        cnt = await self.bot.net.request(url, no_base_headers=True, follow_redirects=True)
        if cnt is None:
            raise Exception("HTTP Error 404: Not Found")
        try: cnt = cnt.decode('utf-8')
        except: cnt = cnt.decode('iso-8859-1')
        soup = BeautifulSoup(cnt, 'html.parser') # parse the html
        try: title = soup.find_all("h1", id="firstHeading", class_="firstHeading")[0].text # page title
        except: title = ""
        if search_mode and not title.startswith('Search results'): # handling rare cases of the search function redirecting the user directly to a page
            search_mode = False
            url = "https://gbf.wiki/{}".format(title.replace(' ', '_')) # update the url so it looks pretty (with the proper page name)

        if search_mode: # use the wiki search function
            try:
                res = soup.find_all("ul", class_="mw-search-results")[0].findChildren("li", class_="mw-search-result", recursive=False) # recuperate the search results
            except:
                raise Exception("HTTP Error 404: Not Found") # no results
            matches = []
            for r in res: # for each, get the title
                matches.append(r.findChildren("div", class_="mw-search-result-heading", recursive=False)[0].findChildren("a", recursive=False)[0].attrs['title'])
                if len(matches) >= 5: break # max 5
            if len(matches) == 0: # no results check
                raise Exception("No results")
            elif len(matches) == 1: # single result, request it directly
                await self.requestWiki(inter, "https://gbf.wiki/{}".format(matches[0]))
                return
            desc = ""
            for m in matches: # build the message with the results
                desc += "[{}](https://gbf.wiki/{})\n".format(m, m.replace(" ", "_"))
            desc = "First five results\n{}".format(desc)
            await inter.edit_original_message(embed=self.bot.embed(title="Not Found, click here to refine", description=desc, url=url, color=self.COLOR))
        else: # direct access to the page (assume a match)
            data, tables = await self.processWikiMatch(soup)

            x = data.get('object', None)
            if data.get('id', None) is not None: 
                gbfal = "\n[Assets](https://mizagbf.github.io/GBFAL/?id={})".format(data['id'])
                try:
                    if str(data['id'])[:3] in ['302', '303', '304', '371', '101', '102', '103', '104']:
                        gbfal += "▫️[Animation](https://mizagbf.github.io/GBFAP/?id={})".format(data['id'])
                except:
                    pass
            else:
                gbfal = ""
            match x:
                case None: # if no match
                    await inter.edit_original_message(embed=self.bot.embed(title=title, description=data.get('description', '') + '\n' + gbfal, image=data.get('image', ''), url=url, footer=data.get('id', ''), color=self.COLOR))
                case 0: # character
                    if 'title' in data: title = title + ", " + data['title']
                    if 'rarity' in data: title = "{} {}".format(self.bot.emote.get(data['rarity']), title)
                    try:
                        # check all character versions
                        versions = soup.find_all("div", class_="character__versions")[0].findChildren("table", recursive=False)[0].findChildren("tbody", recursive=False)[0].findChildren("tr", recursive=False)[2].findChildren("td", recursive=False)
                        elems = []
                        for v in versions:
                            s = v.findChildren("a", recursive=False)[0].text
                            if s != title: elems.append(s)
                        if len(elems) == 0: raise Exception()
                        desc = "This character has other versions\n"
                        for e in elems:
                            desc += "[{}](https://gbf.wiki/{})\n".format(e, e.replace(" ", "_"))
                        await inter.edit_original_message(embed=self.bot.embed(title=title, description=desc + gbfal, image=data.get('image', ''), url=url, footer=data.get('id', ''), color=self.COLOR))
                    except: # if none, just send the link
                        await inter.edit_original_message(embed=self.bot.embed(title=title, description=data.get('description', '') + gbfal, image=data.get('image', ''), url=url, footer=data.get('id', ''), color=self.COLOR))
                case _: # summon and weapon
                    data = await self.processWikiItem(data, tables)
                    # final message
                    title = ""
                    title += "{}".format(self.bot.emote.get(data.get('element', '')))
                    title += "{}".format(self.bot.emote.get(data.get('rarity', '')))
                    title += "{}".format(self.bot.emote.get(data.get('type', '')))
                    title += "{}".format(data.get('name', ''))
                    if 'title' in data: title += ", {}".format(data['title'])

                    desc = ""
                    if 'lvl' in data: desc += "**Lvl {}** ".format(data['lvl'])
                    if 'hp' in data: desc += "{} {} ".format(self.bot.emote.get('hp'), data['hp'])
                    if 'atk' in data: desc += "{} {}".format(self.bot.emote.get('atk'), data['atk'])
                    if desc != "": desc += "\n"
                    if 'ca' in data: desc += "{} **{}**▫️{}\n".format(self.bot.emote.get('skill1'), data['ca'][0], data['ca'][1])
                    if 'skill' in data:
                        for s in data['skill']:
                            desc += "{} **{}**▫️{}\n".format(self.bot.emote.get('skill2'), s[0], s[1])
                    if 'sm' in data:
                        if desc != "": desc += "\n"
                        for s in data['sm']:
                            if s[0] == "Attack" or s[0] == "Defend": continue
                            desc += "**{}**▫️{}\n".format(s[0], s[1])
                    if 'call' in data: desc += "{} **{}**▫️{}\n".format(self.bot.emote.get('skill1'), data['call'][0], data['call'][1])
                    if 'aura' in data: desc += "{} **Aura**▫️{}\n".format(self.bot.emote.get('skill2'), data['aura'])
                    if 'subaura' in data: desc += "{} **Sub Aura**▫️{}\n".format(self.bot.emote.get('skill2'), data['subaura'])

                    await inter.edit_original_message(embed=self.bot.embed(title=title, description=desc + gbfal, thumbnail=data.get('image', ''), url=url, footer=data.get('id', ''), color=self.COLOR))
        await self.bot.util.clean(inter, 80)

    @gbf.sub_command()
    async def wiki(self, inter: disnake.GuildCommandInteraction, terms : str = commands.Param(description="Search expression")) -> None:
        """Search the GBF wiki"""
        await inter.response.defer()
        # build the url (the wiki is case sensitive)
        arr = []
        for s in terms.split(" "):
            arr.append(self.bot.util.wiki_fixCase(s))
        sch = "_".join(arr)
        url = "https://gbf.wiki/{}".format(sch)
        try:
            await self.requestWiki(inter, url) # try to request
        except Exception as e:
            url = "https://gbf.wiki/index.php?title=Special:Search&search={}".format(parse.quote_plus(terms))
            if str(e) != "HTTP Error 404: Not Found": # unknown error, we stop here
                self.bot.logger.pushError("[GBF] In 'gbf wiki' command:", e)
                await inter.edit_original_message(embed=self.bot.embed(title="Unexpected error, click here to search", url=url, footer=str(e), color=self.COLOR))
            else: # failed, we try the search function
                try:
                    await self.requestWiki(inter, url, True) # try
                except Exception as f:
                    if str(f) == "No results":
                        await inter.edit_original_message(embed=self.bot.embed(title="No matches found", color=self.COLOR)) # no results
                    else:
                        await inter.edit_original_message(embed=self.bot.embed(title="Not Found, click here to refine", url=url, color=self.COLOR)) # no results
        await self.bot.util.clean(inter, 45)

    @gbf.sub_command()
    async def info(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post various Granblue Fantasy informations"""
        await inter.response.defer()
        current_time = self.bot.util.JST(delay=False)
        description = "{} Current Time is **{}**".format(self.bot.emote.get('clock'), self.bot.util.time(style='dT'))
        description += "\n{} Japan Time is **{}**".format(self.bot.emote.get('clock'), current_time.strftime("%H:%M"))

        if self.bot.data.save['gbfversion'] is not None:
            description += "\n{} Version is `{}` (`{}`)".format(self.bot.emote.get('cog'), self.bot.data.save['gbfversion'], self.bot.util.version2str(self.bot.data.save['gbfversion']))

        reset = current_time.replace(hour=5, minute=0, second=0, microsecond=0)
        if current_time.hour >= reset.hour:
            reset += timedelta(days=1)
        d = reset - current_time
        description += "\n{} Reset in **{}**".format(self.bot.emote.get('mark'), self.bot.util.delta2str(d))

        try:
            buf = await self.bot.net.gbf_maintenance_status()
            if len(buf) > 0: description += "\n" + buf
        except:
            pass

        try:
            buf = await self.bot.gacha.get()
            if len(buf) > 0:
                description += "\n{} Current gacha ends in **{}**".format(self.bot.emote.get('SSR'), self.bot.util.delta2str(buf[1]['time'] - buf[0], 2))
                if buf[1]['time'] != buf[1]['timesub']:
                    description += " (Spark period ends in **{}**)".format(self.bot.util.delta2str(buf[1]['timesub'] - buf[0], 2))
        except:
            pass

        try:
            if current_time < self.bot.data.save['stream']['time']:
                description += "\n{} Stream at **{}**".format(self.bot.emote.get('crystal'), self.bot.util.time(self.bot.data.save['stream']['time'], style='dt', removejst=True))
        except:
            pass

        try:
            buf = self.bot.get_cog('GuildWar').getGWState()
            if len(buf) > 0: description += "\n" + buf
        except:
            pass

        try:
            buf = self.bot.get_cog('DreadBarrage').getBarrageState()
            if len(buf) > 0: description += "\n" + buf
        except:
            pass

        try:
            buf = self.bot.get_cog('GuildWar').getNextBuff(inter)
            if len(buf) > 0: description += "\n" + buf
        except:
            pass

        await inter.edit_original_message(embed=self.bot.embed(author={'name':"Granblue Fantasy", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=description, color=self.COLOR))

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
                    msg = "Stream starts in **{} ({})**\n".format(self.bot.util.delta2str(d, 2), self.bot.util.time(self.bot.data.save['stream']['time'], 'd', True))
                else:
                    msg = "Stream is **On going!! ({})**\n".format(self.bot.util.time(self.bot.data.save['stream']['time'], 'd', True))

            await inter.edit_original_message(embed=self.bot.embed(title=self.bot.data.save['stream']['title'], description=msg + self.bot.data.save['stream']['content'], timestamp=self.bot.util.UTC(), color=self.COLOR))

    @gbf.sub_command()
    async def schedule(self, inter: disnake.GuildCommandInteraction, raw : int = commands.Param(default=0)) -> None:
        """Post the GBF schedule"""
        await inter.response.defer()
        if len(self.bot.data.save['schedule']) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="No schedule available", color=self.COLOR))
        elif raw != 0:
            await inter.edit_original_message(embed=self.bot.embed(title="🗓 Event Schedule {} {}".format(self.bot.emote.get('clock'), self.bot.util.time(style='dt')), url="https://twitter.com/granblue_en", color=self.COLOR, description='`{}`'.format(';'.join(self.bot.data.save['schedule']))))
        else:
            l = len(self.bot.data.save['schedule'])
            l = l - (l%2) # need an even amount, skipping the last one if odd
            i = 0
            msg = ""
            c = self.bot.util.JST()
            nx = None
            nxn = None
            md = c.month * 100 + c.day
            while i < l:
                try: # checking if the event is on going (to bold it)
                    dates = self.bot.data.save['schedule'][i].replace(' ', '').split('-')
                    ev_md = []
                    for dd in dates:
                        if "??" in dd: break
                        ev_md.append(int(dd.split('/')[0]) * 100 + int(dd.split('/')[1]))
                    if len(ev_md) == 2:
                        if ev_md[0] - md >= 1000: ev_md[0] -= 1200 # new year fixes
                        elif md - ev_md[1] >= 1000: ev_md[1] += 1200
                        on_going = (md >= ev_md[0] and md <= ev_md[1])
                    else:
                        on_going = (md == ev_md[0])
                except:
                    on_going = False
                # check if it's the next event in line
                if not on_going:
                    try:
                        dates = self.bot.data.save['schedule'][i].replace(' ', '').split('-')
                        evd = dates[0].split('/')
                        evt = c.replace(month=int(evd[0]), day=int(evd[1]), hour=18, minute=0, second=0, microsecond=0)
                        if evt > c and (nx is None or evt < nx):
                            nx = evt
                            nxn = self.bot.data.save['schedule'][i+1] # event name
                            if nx - c > timedelta(days=300): # new year fix
                                nx = None
                                nxn = None
                    except:
                        pass
                msg += "- "
                if on_going: msg += "**"
                msg += "{} ▫️ {}".format(self.bot.data.save['schedule'][i], self.bot.data.save['schedule'][i+1])
                if on_going: msg += "**"
                msg += "\n"
                i += 2
            current_time = self.bot.util.JST()
            msg += "{} Japan Time is **{}\n**".format(self.bot.emote.get('clock'), current_time.strftime("%H:%M"))
            if nx is not None and c < nx:
                added = False
                if 'Unite and Fight' in nxn:
                    try:
                        buf = self.bot.get_cog('GuildWar').getGWState()
                        if len(buf) > 0:
                            msg += buf + '\n'
                            added = True
                    except:
                        pass
                elif 'Dread Barrage' in nxn:
                    try:
                        buf = self.bot.get_cog('DreadBarrage').getBarrageState()
                        if len(buf) > 0:
                            msg += buf + '\n'
                            added = True
                    except:
                        pass
                if not added:
                    msg += "{} Next event approximately in **{}**\n".format(self.bot.emote.get('mark'), self.bot.util.delta2str(nx - c, 2))
            try:
                buf = await self.bot.net.gbf_maintenance_status()
                if len(buf) > 0: msg += buf + '\n'
            except:
                pass
            try:
                buf = await self.bot.gacha.get()
                if len(buf) > 0:
                    msg += "{} Current gacha ends in **{}**".format(self.bot.emote.get('SSR'), self.bot.util.delta2str(buf[1]['time'] - buf[0], 2))
                    if buf[1]['time'] != buf[1]['timesub']:
                        msg += " (Spark period ends in **{}**)".format(self.bot.util.delta2str(buf[1]['timesub'] - buf[0], 2))
                    msg += "\n"
            except:
                pass
            try:
                if current_time < self.bot.data.save['stream']['time']:
                    msg += "{} Stream at **{}**".format(self.bot.emote.get('crystal'), self.bot.util.time(self.bot.data.save['stream']['time'], style='dt', removejst=True))
            except:
                pass
            await inter.edit_original_message(embed=self.bot.embed(title="🗓 Event Schedule {} {}".format(self.bot.emote.get('clock'), self.bot.util.time(style='dt')), url="https://twitter.com/granblue_en", color=self.COLOR, description=msg))

    """getGrandList()
    Request the grand character list from the wiki page and return the list of latest released ones
    
    Returns
    ----------
    dict: Grand per element
    """
    async def getGrandList(self) -> dict:
        cnt = await self.bot.net.request('https://gbf.wiki/SSR_Characters_List#Grand_Series', no_base_headers=True, follow_redirects=True)
        if cnt is None:
            raise Exception("HTTP Error 404: Not Found")
        try: cnt = cnt.decode('utf-8')
        except: cnt = cnt.decode('iso-8859-1')
        soup = BeautifulSoup(cnt, 'html.parser') # parse the html
        tables = soup.find_all("table", class_="wikitable")
        for t in tables:
            if "Gala" in str(t):
                table = t
                break
        children = table.findChildren("tr")
        grand_list = {'fire':None, 'water':None, 'earth':None, 'wind':None, 'light':None, 'dark':None}
        for c in children:
            td = c.findChildren("td")
            grand = {}
            for elem in td:
                # name search
                if 'name' not in grand and elem.text != "" and "Base uncap" not in elem.text:
                    try:
                        int(elem.text)
                    except:
                        grand['name'] = elem.text
                # elem search
                if 'element' not in grand:
                    imgs = elem.findChildren("img")
                    for i in imgs:
                        try:
                            label = i['alt']
                            if label.startswith('Label Element '):
                                grand['element'] = label[len('Label Element '):-4].lower()
                                break
                        except:
                            pass
                # date search
                if 'date' not in grand and elem.text != "":
                    try:
                        date_e = elem.text.split('-')
                        grand['date'] = self.bot.util.UTC().replace(year=int(date_e[0]), month=int(date_e[1]), day=int(date_e[2]), hour=(12 if (int(date_e[2]) > 25) else 19), minute=0, second=0, microsecond=0)
                    except:
                        pass
            if len(grand.keys()) > 2:
                if grand_list[grand['element']] is None or grand['date'] > grand_list[grand['element']]['date']:
                    grand_list[grand['element']] = grand
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
                data = await self.bot.net.request("https://game.granbluefantasy.jp/profile/content/index/{}?PARAMS".format(profile_id), account=self.bot.data.save['gbfcurrent'], expect_JSON=True)
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
                rarity = h[1]
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
            summon_list = [[None for i in range(7)], [None for i in range(7)]]
            for x, e in enumerate(script.find_all("div", class_="prt-fix-support-wrap")):
                for y, v in enumerate(e.findChildren("div", class_="prt-fix-support", recursive=False)):
                    t = v.findChildren("div", recursive=False)[-1]
                    if "No support summon is set." not in t.get_text():
                        c = t.findChildren("div", recursive=False)
                        sname = c[0].get_text()
                        cname = c[1].get('class')[-1]
                        if 'bless-rank' in cname:
                            squal = "star{}".format(cname.split('bless-rank')[-1].split('-')[0])
                        else:
                            squal = "star0"
                        summon_list[y][(x+6)%7] = (sname, squal)
            fields = [{'name':"{} **Summons**".format(self.bot.emote.get('summon')), 'value':'', 'inline':True}, {'name':"{} **Summons**".format(self.bot.emote.get('summon')), 'value':'', 'inline':True}]
            for i in range(len(summon_list)):
                for j in range(len(summon_list[i])):
                    if summon_list[i][j] is None:
                        fields[i]['value'] += "{} *None*\n".format(self.bot.emote.get(self.SUMMON_ELEMENTS[j]))
                    else:
                        fields[i]['value'] += "{} {}{}\n".format(self.bot.emote.get(self.SUMMON_ELEMENTS[j]), self.bot.emote.get(summon_list[i][j][1]), summon_list[i][j][0])
        except:
            fields = []
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
        return title, "{}{}\n{} Crew ▫️ {}\n{}{}".format(rank, comment, self.bot.emote.get('gw'), crew, scores, star), fields, mc_url

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
            data = await self.bot.net.request("https://game.granbluefantasy.jp/profile/content/index/{}?PARAMS".format(pid), account=self.bot.data.save['gbfcurrent'], expect_JSON=True)
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
            title, description, fields, thumbnail = await self.processProfile(pid, data)
            await inter.edit_original_message(embed=self.bot.embed(title=title, description=description, url="https://game.granbluefantasy.jp/#profile/{}".format(pid), thumbnail=thumbnail, fields=fields, inline=True, color=color), view=view)
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
            ('Leechlist Anon #1', 'https://drive.google.com/open?id=1kfUi2GNcwXobEWnG_sdqPQu2r5YSLNpk'),
            ('Leechlist Anon #2', 'https://drive.google.com/drive/folders/1f6DJ-u9D17CubY24ZHl9BtNv3uxTgPnQ'),
            ('My Data', 'https://drive.google.com/drive/folders/18ZY2SHsa3CVTpusDHPg-IqNPFuXhYRHw')
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

    """crit_callback()
    CustomModal callback
    """
    async def crit_callback(self, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        try:
            await inter.response.defer(ephemeral=True)
            values = {'small10':2, 'small15':3, 'small20':4, 'medium10':5, 'medium15':6.5, 'medium20':7.5, 'big10':8, 'big15':10, 'big20':11, 'bigii15':12, 'wamdus':20, 'hercules':11.5, 'sephira':30}
            ts = {'small':'small15', 'med':'medium15', 'medium':'medium15', 'big':'big15', 'big2':'bigii15', 's10':'small10', 's15':'small15', 's20':'small20', 'm10':'medium10', 'm15':'medium15', 'm20':'medium20', 'med10':'medium10', 'med15':'medium15', 'med20':'medium20', 'b10':'big10', 'b15':'big15', 'b20':'big20', 'bii10':'bigii10', 'bii15':'bigii15', 'b210':'bigii10', 'b215':'bigii15', 'big210':'bigii10', 'big215':'bigii15', 'ameno':'medium20', 'gaebulg':'medium20', 'bulg':'medium20', 'bulge':'medium20', 'gae':'medium20', 'mjolnir':'small20', 'herc':'hercules', 'ecke':'medium15', 'eckesachs':'medium15', 'sachs':'medium15', 'blut':'small15', 'blutgang':'small15', 'indra':'medium15', 'ivory':'bigii15', 'ivoryark':'bigii15', 'ark':'bigii15', 'auberon':'medium15', 'aub':'medium15', 'taisai':'big15', 'pholia':'big15', 'galilei':'medium15', 'europa':'medium15', 'benedia':'medium15', 'thunderbolt':'big15', 'shibow':'big15', 'rein':'bigii15', 'babel':'bigii15', 'mandeb':'bigii15', 'bab-el-mandeb':'bigii15', 'arca':'sephira', 'arcarum':'sephira', 'spoon':'medium15', 'coruscant':'medium15', 'crozier':'medium15', 'eva':'bigii15', 'evanescence':'bigii15', 'opus':'medium20'}
            flats = ['wamdus', 'sephira']
            summons = {'magna':0, 'omega':0, 'tiamat':0, 'colossus':0, 'leviathan':0, 'yggdrasil':0, 'luminiera':0, 'celeste':0, 'm2':0, 'tia':0, 'colo':0, 'levi':0, 'ygg':0, 'yugu':0, 'lumi':0, 'chevalier':0, 'chev':0, 'boat':0, 'primal':1, 'whale':1, 'god':1, 'agni':1, 'varuna':1, 'titan':1, 'zephyrus':1, 'zeus':1, 'hades':1, 'zeph':1}
            if inter.text_values['modifiers'] == "": raise Exception("Empty Parameter")
            mods = inter.text_values['modifiers'].lower().replace('\r', '').replace('\n', ' ').split(' ')
            mod_data = [0, 0, 0, 0] # magna, primal, other, summon
            mod_string = [[], [], [], []]
            for m in mods:
                if len(m) == 0: continue
                if ts.get(m, m) in flats:
                    mod_data[2] += values[ts.get(m, m)]
                    mod_string[2].append(str(values[ts.get(m, m)]))
                elif m not in ts and m not in values:
                    match m[0]:
                        case 'm'|'o':
                            b = 0
                        case 'p'|'n':
                            b = 1
                        case _:
                            b = 2
                    v = m[1:]
                    mod_data[b] += values[ts.get(v, v)]
                    mod_string[b].append(str(values[ts.get(v, v)]))
                else:
                    mod_data[3] += values[ts.get(m, m)]
                    mod_string[3].append(str(values[ts.get(m, m)]))
            
            sum_config = inter.text_values['summon'].lower().split('x')
            if len(sum_config) != 2:
                raise Exception(str("`{}` isn't a valid summon configuration.\nTry a main summon mod and support mod separated by an X (Example: MagnaXEle, Magna 150% X Other, and so on...)."))
            main_text = sum_config[0].strip().split(' ')
            support_text = sum_config[1].strip().split(' ')
            
            main_value = None
            for m in summons:
                if m in main_text:
                    main = summons[m]
                    break
            else:
                main = 2
            match main:
                case 0:
                    if '0*' in main_text or 'base' in main_text or '50%' in main_text:
                        main_value = 0.5
                    elif '3*' in main_text or 'mlb' in main_text or '100%' in main_text:
                        main_value = 1
                    elif '4*' in main_text or 'flb' in main_text or '120%' in main_text:
                        main_value = 1.2
                    else:
                        main_value = 1.4
                    main_text = "Magna"
                    if main_value != 1.4: main_text += " {}%".format(int(main_value*100))
                case 1:
                    if '0*' in main_text or 'base' in main_text or '80%' in main_text:
                        main_value = 0.8
                    elif '3*' in main_text or 'mlb' in main_text or '120%' in main_text:
                        main_value = 1.2
                    elif '4*' in main_text or 'flb' in main_text or '140%' in main_text:
                        main_value = 1.4
                    else:
                        main_value = 1.5
                    main_text = "Primal"
                    if main_value != 1.5: main_text += " {}%".format(int(main_value*100))
                case _:
                    main_value = 0
                    main_text = "Other"
            support_value = None
            for m in summons:
                if m in support_text:
                    support = summons[m]
                    break
            else:
                support = 2
            match support:
                case 0:
                    if '0*' in support_text or 'base' in support_text or '50%' in support_text:
                        support_value = 0.5
                    elif '3*' in support_text or 'mlb' in support_text or '100%' in support_text:
                        support_value = 1
                    elif '4*' in support_text or 'flb' in support_text or '120%' in support_text:
                        support_value = 1.2
                    else:
                        support_value = 1.4
                    support_text = "Magna"
                    if support_value != 1.4: support_text += " {}%".format(int(support_value*100))
                case 1:
                    if '0*' in support_text or 'base' in support_text or '80%' in support_text:
                        support_value = 0.8
                    elif '3*' in support_text or 'mlb' in support_text or '120%' in support_text:
                        support_value = 1.2
                    elif '4*' in support_text or 'flb' in support_text or '140%' in support_text:
                        support_value = 1.4
                    else:
                        support_value = 1.5
                    support_text = "Primal"
                    if support_value != 1.5: support_text += " {}%".format(int(support_value*100))
                case _:
                    support_value = 0
                    support_text = "Other"
            mod_data[min(main, support)] += mod_data[3]
            mod_string[min(main, support)] += mod_string[3]
            
            try:
                dragon = int(inter.text_values['dragon'])
                match dragon:
                    case 0:
                        dragon = 0.1
                    case 1:
                        dragon = 0.1
                    case 2:
                        dragon = 0.1
                    case 3:
                        dragon = 0.2
                    case 4:
                        dragon = 0.4
                    case _:
                        dragon = 0
            except:
                dragon = 0
            
            try:
                exalto = (max(0, min(3, int(inter.text_values['exalto']))) * 30) / 100
            except:
                exalto = 0
            
            try:
                primarch = inter.text_values['primarch'].lower()
                match primarch:
                    case 'y'|'yes':
                        primarch = 0.2
                    case 'n'|'no':
                        primarch = 0
                    case _:
                        primarch = 0
            except:
                primarch = 0
            
            
            for i in range(3):
                m = 1
                if i == main: m += main_value
                if i == support: m += support_value
                if i == 1:
                    m += dragon
                    m += exalto
                if i < 2: m += primarch
                mod_data[i] *= m
            
            msg = "**Summons**  ▫️ {} x {}\n".format(main_text, support_text)
            if dragon != 0:
                msg += "**Dragon Boost**  ▫️ {}%\n".format(int(dragon*100))
            if primarch != 0:
                msg += "**Primarch Boost**  ▫️ {}%\n".format(int(primarch*100))
            if exalto != 0:
                msg += "**Exalto Boost**  ▫️ {}%\n".format(int(exalto*100))
            msg += "**Modifiers** ▫️ `"
            for i in range(3):
                if len(mod_string[i]) > 0:
                    match i:
                        case 0: msg += "Magna "
                        case 1: msg += "Primal "
                        case 2: msg += "Other "
                    msg += '+'.join(mod_string[i])
                    if i < 2: msg += ' '
            msg += '`\n'
            msg += "**Result**  ▫️ {:.2f}% Critical Rate".format(min(100, mod_data[0]+mod_data[1]+mod_data[2]))
            await inter.edit_original_message(embed=self.bot.embed(title="Critical Calculator", description=msg.replace('.0%', '%'), color=self.COLOR))
        except Exception as e:
            if str(e) == "Empty Parameter":
                modstr = ""
                for m in values:
                    modstr += "`{}`, ".format(m)
                for m in ts:
                    modstr += "`{}`, ".format(m)
                await inter.edit_original_message(embed=self.bot.embed(title="Critical Calculator", description="**Posible modifiers:**\n" + modstr[:-2] + "\n\nModifiers must be separated by spaces\nAdd `m` before a modifier to make it magna, `p` to make it primal, `u` to make it unboosted (else, it will use your summons to determine it)" , color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description=str(e), color=self.COLOR))

    @_utility.sub_command()
    async def critical(self, inter: disnake.GuildCommandInteraction) -> None:
        """Calculate critical rate"""
        await self.bot.util.send_modal(inter, "crit-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()), "Calculate Critical Rate", self.crit_callback, [
                disnake.ui.TextInput(
                    label="Summon Configuration",
                    placeholder="MagnaXMagna, PrimalXEle, etc...",
                    custom_id="summon",
                    style=disnake.TextInputStyle.short,
                    min_length=1,
                    max_length=200,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="Six Dragon Star",
                    placeholder="None, 0, 3, 4",
                    custom_id="dragon",
                    style=disnake.TextInputStyle.short,
                    min_length=0,
                    max_length=20,
                    required=False
                ),
                disnake.ui.TextInput(
                    label="Optimus Exalto Count",
                    placeholder="number",
                    custom_id="exalto",
                    style=disnake.TextInputStyle.short,
                    value="0",
                    min_length=1,
                    max_length=20,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="Primarch Passive",
                    placeholder="yes or no",
                    custom_id="primarch",
                    style=disnake.TextInputStyle.short,
                    value="no",
                    min_length=1,
                    max_length=20,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="Weapon Modifier List",
                    placeholder="Leave empty to receive a list",
                    custom_id="modifiers",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=0,
                    max_length=2000,
                    required=False
                )
            ]
        )

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
                data = await self.bot.net.request("https://game.granbluefantasy.jp/forum/search_users_id?PARAMS", account=self.bot.data.save['gbfcurrent'], expect_JSON=True, payload={"special_token":None,"user_id":int(id)})
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
            t = await self.bot.net.request("https://gbf.wiki/{}".format(w), no_base_headers=True, follow_redirects=True, timeout=8)
            if t is not None:
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
        msg += "**{} days** since the Summer Fortune 2021 results\n".format(self.bot.util.delta2str(c - c.replace(year=2021, month=8, day=16, hour=19, minute=0, second=0, microsecond=0), 3).split('d')[0])
        msg += "**{} days** since the Settecide Day\n".format(self.bot.util.delta2str(c - c.replace(year=2023, month=11, day=9, hour=7, minute=0, second=0, microsecond=0), 3).split('d')[0])
        
        # grand
        try:
            grands = await self.getGrandList()
            for e in grands:
                msg += "**{} days** since {} [{}](https://gbf.wiki/{})\n".format(self.bot.util.delta2str(c - grands[e]['date'], 3).split('d')[0], self.bot.emote.get(e), grands[e]['name'], grands[e]['name'].replace(' ', '_'))
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
            data = (await self.bot.net.request('https://game.granbluefantasy.jp/coopraid/daily_mission?PARAMS', account=self.bot.data.save['gbfcurrent'], expect_JSON=True))['daily_mission']
            msg = ""
            for i in range(len(data)):
                if data[i]['category'] == '2':
                    items = {20011:'fire', 20012:'fire', 20111:'fire', 20021:'water', 20022:'water', 20121:'water', 20031:'earth', 20032:'earth', 20131:'earth', 20041:'wind', 20042:'wind', 20141:'wind'}
                    cid = int(data[i]['image'].split('/')[-1])
                    msg += '{} {}\n'.format(self.bot.emote.get(items.get(cid, 'misc')), data[i]['description'])
                elif data[i]['category'] == '1':
                    quests = {'s00101':'wind', 's00104':'wind', 's00204':'wind', 's00206':'wind', 's00301':'fire', 's00303':'fire', 's00405':'fire', 's00406':'fire', 's00601':'water', 's00602':'water', 's00604':'water', 's00606':'water', 's00802':'earth', 's00704':'earth', 's00705':'earth', 's00806':'earth', 's01005':'wind', 's00905':'wind', 's00906':'wind', 's01006':'wind', 's01105':'fire', 's01403':'fire', 's01106':'fire', 's01206':'fire', 's01001':'water', 's01502':'water', 's01306':'water', 's01406':'water', 's01601':'earth', 's01405':'earth', 's01506':'earth', 's01606':'earth'}
                    cid = data[i]['image'].split('/')[-1]
                    msg += '{} {}\n'.format(self.bot.emote.get(quests.get(cid, 'misc')), data[i]['description'])
                else:
                    msg += '{} {}\n'.format(self.bot.emote.get(str(i+1)), data[i]['description'])
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"Daily Coop Missions", 'icon_url':"https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png"}, description=msg, color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Unavailable", color=self.COLOR))

    @check.sub_command()
    async def koregra(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the time to the next monthly dev post"""
        await inter.response.defer()
        c = self.bot.util.JST()
        try:
            if c < self.bot.data.save['stream']['time']:
                target = self.bot.data.save['stream']['time']
            else:
                raise Exception()
        except:
            if c.day == 1:
                if c.hour >= 12:
                    if c.month == 12: target = datetime(year=c.year+1, month=1, day=1, hour=12, minute=0, second=0, microsecond=0)
                    else: target = datetime(year=c.year, month=c.month+1, day=1, hour=12, minute=0, second=0, microsecond=0)
                else:
                    target = datetime(year=c.year, month=c.month, day=1, hour=12, minute=0, second=0, microsecond=0)
            else:
                if c.month == 12: target = datetime(year=c.year+1, month=1, day=1, hour=12, minute=0, second=0, microsecond=0)
                else: target = datetime(year=c.year, month=c.month+1, day=1, hour=12, minute=0, second=0, microsecond=0)
        delta = target - c
        await inter.edit_original_message(embed=self.bot.embed(title="{} Kore Kara".format(self.bot.emote.get('clock')), description="Release approximately in **{}**".format(self.bot.util.delta2str(delta, 2)),  url="https://granbluefantasy.jp/news/index.php", thumbnail="https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/touch_icon.png", color=self.COLOR))

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
            if (await self.bot.net.request("https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/comic/episode/episode_{}.jpg".format(episode), no_base_headers=True)) is None: raise Exception()
            await inter.edit_original_message(embed=self.bot.embed(title="Grand Blues! Episode {}".format(episode), url="https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/comic/episode/episode_{}.jpg".format(episode), image="https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/comic/thumbnail/thum_{}.png".format(str(episode).zfill(5)), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid Grand Blues! number", color=self.COLOR))

    @gbf.sub_command()
    async def crystal(self, inter: disnake.GuildCommandInteraction) -> None:
        """Granblue Summer Festival - Crystal Countdown"""
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
                    data = unquote((await self.bot.net.request("https://game.granbluefantasy.jp/campaign/dividecrystal/content/index?PARAMS", account=self.bot.data.save['gbfcurrent'], expect_JSON=True))['data'])
                except Exception as tmp:
                    if maxwave > 1 and self.bot.data.save['extra']['campaign/dividecrystal']['wave'] < maxwave and (c - start).days > 2:
                        try:
                            await self.bot.net.request("https://game.granbluefantasy.jp/campaign/dividecrystal/content/bonus_present?PARAMS", account=self.bot.data.save['gbfcurrent'], expect_JSON=True)
                            data = unquote((await self.bot.net.request("https://game.granbluefantasy.jp/campaign/dividecrystal/content/index?PARAMS", account=self.bot.data.save['gbfcurrent'], expect_JSON=True))['data'])
                            self.bot.data.save['extra']['campaign/dividecrystal']['wave'] += 1
                            self.bot.data.pending = True
                        except:
                            raise tmp
                    elif self.bot.data.save['extra']['campaign/dividecrystal']['wave'] == maxwave: # likely triggered by the end
                        try:
                            await self.bot.net.request("https://game.granbluefantasy.jp/campaign/dividecrystal/content/bonus_present?PARAMS", account=self.bot.data.save['gbfcurrent'], expect_JSON=True)
                            data = unquote((await self.bot.net.request("https://game.granbluefantasy.jp/campaign/dividecrystal/content/index?PARAMS", account=self.bot.data.save['gbfcurrent'], expect_JSON=True))['data'])
                        except:
                            raise tmp
                    else:
                        raise tmp
                s = data.find('<div class="txt-amount">')
                if s == -1: raise Exception()
                s += len('<div class="txt-amount">')
                crystal = int(data[s:].split('/')[0].replace(',', ''))
                available_crystal = int(data[s:].split('/')[1].replace(',', '').replace('<', ''))
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
        await inter.edit_original_message(embed=self.bot.embed(title="Defense Values", description="**8.5**▫️ Fediel Solo\n**9.5**▫️ Fediel HL\n**10** ▫️ Estimate Calculator / Trial / Story / Event / EX+\n**11** ▫️ PBaha N / UBaha HL / Xeno\n**12** ▫️ M1 HL / Kirin HL / Metatron / Avatar / GO HL / Lindwurm\n**13** ▫️ Normal / Hard / T2 / Primarchs N & HL / UBaha N / M2\n**15** ▫️ T1 HL / Malice / Menace / Akasha / Lucilius / Astaroth / Pride / NM90-100 / Other Dragon Solos\n**18** ▫️ Rose Queen / Other Dragons HL\n**20** ▫️ PBaha HL / Lucilius Hard / Belial\n**22** ▫️ Celeste (Mist)\n**25** ▫️ Beelzebub / NM150\n**30** ▫️ Rose Queen (Dark)", footer="20 def = Take half the damage of 10 def", color=self.COLOR, thumbnail="https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/ui/icon/status/x64/status_1019.png"))