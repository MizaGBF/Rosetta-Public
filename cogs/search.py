import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from bs4 import BeautifulSoup
from urllib.parse import quote
import html
import json
import re

# ----------------------------------------------------------------------------------------------------------------
# Search Cog
# ----------------------------------------------------------------------------------------------------------------
# To search stuff on the web
# ----------------------------------------------------------------------------------------------------------------

class Search(commands.Cog):
    """Manga, Anime, etc... Cog"""
    COLOR = 0xa4eb34
    REGEX_CLEAN_4CHAN = re.compile('<.*?>')

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 2, commands.BucketType.default)
    @commands.max_concurrency(30, commands.BucketType.default)
    async def search(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @search.sub_command()
    async def mangadex(self, inter: disnake.GuildCommandInteraction, search_query : str = commands.Param(description="Your search query.", default=""), target_language : str = commands.Param(description="Language that you want to read (Default: en).", default="en"), exclude_manwha : int = commands.Param(description="Set to 1 to ignore korean works.", default=0, ge=0, le=1), exclude_manhua : int = commands.Param(description="Set to 1 to ignore chinese works.", default=0, ge=0, le=1), enable_hentai : int = commands.Param(description="Set to 1 to include Hentai (NSFW channels only).", default=0, ge=0, le=1)) -> None:
        """Search Mangadex"""
        await inter.response.defer()
        exclude_language = []
        if exclude_manwha: exclude_language.append('ko')
        if exclude_manhua: exclude_language.append('cz')
        content_rating = ["safe"]
        if inter.channel.is_nsfw():
            content_rating += ["suggestive", "erotica"]
            if enable_hentai: content_rating.append("pornographic")
        params = {
            'limit':10,
            'order[latestUploadedChapter]':'desc',
            'availableTranslatedLanguage[]':[target_language],
            'excludedOriginalLanguage[]':exclude_language,
            'contentRating[]':content_rating,
            "includes[]":["cover_art"]
        }
        if search_query != "": params['title'] = search_query
        response = await self.bot.net.request("https://api.mangadex.org/manga", params=params, no_base_headers=True, add_user_agent=True, expect_JSON=True)
        if response is None:
            await inter.edit_original_message(embed=self.bot.embed(title="Mangadex", description="An error occured", color=self.COLOR))
        else:
            description = ""
            count = 0
            last = None
            thumbnail = None
            for m in response['data']:
                try:
                    try: description += "- [{}](https://mangadex.org/title/{})\n".format(m['attributes']['title']['en'], m['id'])
                    except: description += "- [{}](https://mangadex.org/title/{})\n".format(m['attributes']['title']['ja'], m['id'])
                    count += 1
                    last = m
                    if thumbnail is None:
                        for r in m['relationships']:
                            if r['type'] == 'cover_art':
                                thumbnail = "https://uploads.mangadex.org/covers/{}/{}".format(m['id'], r['attributes']['fileName'])
                                break
                except:
                    pass
        
            if count == 0:
                await inter.edit_original_message(embed=self.bot.embed(title="Mangadex", description="No results found", color=self.COLOR))
            elif count == 1:
                try:
                    description += "\n" + last['attributes']['description']['en']
                    if len(description) > 1000: description = description[:1000] + "..."
                except:
                    description += "\n*(No English Description)*"
                await inter.edit_original_message(embed=self.bot.embed(title="Mangadex - 1 positive search result", description=description, footer="Latest updated mangas", thumbnail=thumbnail, color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="Mangadex - {} positive search results".format(count), description=description, footer="Latest updated mangas", thumbnail=thumbnail, color=self.COLOR))
        await self.bot.util.clean(inter, 60)

    @search.sub_command()
    async def wikipedia(self, inter: disnake.GuildCommandInteraction, search_query : str = commands.Param(description="Your search query")) -> None:
        """Search Wikipedia"""
        await inter.response.defer()
        data = await self.bot.net.request("https://en.wikipedia.org/w/api.php?action=query&format=json&list=search&srsearch={}".format(quote(search_query)), no_base_headers=True, add_user_agent=True, expect_JSON=True)
        if data is None or len(data["query"]["search"]) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="Wikipedia", description="Article not found", color=self.COLOR))
        else:
            search_results = data["query"]["search"]
            article_title = search_results[0]["title"]
            
            data = await self.bot.net.request("https://en.wikipedia.org/w/api.php?action=query&format=json&prop=extracts|pageimages&titles={}&exintro=1&pithumbsize=500".format(article_title), no_base_headers=True, add_user_agent=True, expect_JSON=True)
            if data is None:
                await inter.edit_original_message(embed=self.bot.embed(title="Wikipedia", description="An error occured while retrieving the article", color=self.COLOR))
            else:
                pages = data["query"]["pages"]
                page_id = list(pages.keys())[0]
                page_content = pages[page_id]["extract"]
                soup = BeautifulSoup(page_content, "html.parser")
                parts = soup.get_text().strip().split("\n")
                clean_content = ""
                for p in parts:
                    if len(p) + len(clean_content) > 800: break
                    clean_content += p + "\n\n"
                thumbnail = pages[page_id].get("thumbnail", {}).get("source", None)
                await inter.edit_original_message(embed=self.bot.embed(title="Wikipedia - {}".format(article_title), description=clean_content, url="https://en.wikipedia.org/wiki/{}".format(article_title), thumbnail=thumbnail, color=self.COLOR))
        await self.bot.util.clean(inter, 60)

    @search.sub_command()
    async def google(self, inter: disnake.GuildCommandInteraction, search_query : str = commands.Param(description="Your search query")) -> None:
        """Search Google"""
        await inter.response.defer(ephemeral=True)
        data = await self.bot.net.request("https://www.google.com/search?q={}".format(quote(search_query)), no_base_headers=True, add_user_agent=True)
        if data is None:
            await inter.edit_original_message(embed=self.bot.embed(title="Google Search", description="An error occured", color=self.COLOR))
        else:
            soup = BeautifulSoup(data.decode('utf-8'), "html.parser")
            results = soup.find_all("div", class_="g")
            
            description = ""
            count = 0
            prev = ""
            for result in results:
                try:
                    title = result.find("h3").text
                    link = result.find("a")["href"]
                    if link.startswith('/search'): continue
                    line = "- [{}]({})\n".format(title, link)
                    if line == prev: continue
                    description += line
                    prev = line
                    count += 1
                    if count == 10: break
                except:
                    pass
            await inter.edit_original_message(embed=self.bot.embed(title="Google Search - {} positive results".format(count), description=description, url="https://www.google.com/search?q={}".format(quote(search_query)), color=self.COLOR))
        await self.bot.util.clean(inter, 60)

    """cleanhtml()
    Clean the html and escape the string properly
    
    Parameters
    ------
    raw: String to clean
    
    Returns
    ----------
    str: Cleaned string
    """
    def cleanhtml(self, raw : str) -> str:
      return html.unescape(self.REGEX_CLEAN_4CHAN.sub('', raw.replace('<br>', ' '))).replace('>', '')

    """get4chan()
    Call the 4chan api to retrieve a list of thread based on a search term
    
    Parameters
    ------
    board: board to search for (example: a for /a/)
    search: search terms
    
    Returns
    ----------
    list: Matching threads
    """
    async def get4chan(self, board : str, search : str) -> list: # be sure to not abuse it, you are not supposed to call the api more than once per second
        try:
            search = search.lower()
            data = await self.bot.net.request('http://a.4cdn.org/{}/catalog.json'.format(board), expect_JSON=True, no_base_headers=True, follow_redirects=True)
            threads = []
            for p in data:
                for t in p["threads"]:
                    try:
                        if t.get("sub", "").lower().find(search) != -1 or t.get("com", "").lower().find(search) != -1:
                            threads.append([t["no"], t["replies"], self.cleanhtml(t.get("com", ""))]) # store the thread ids matching our search word
                            if 'filename' in t and 'ext' in t:
                                threads[-1].append("https://i.4cdn.org/{}/{}{}".format(board, t['tim'], t['ext']))
                    except:
                        pass
            threads.sort(reverse=True)
            return threads
        except:
            return []

    """make4chanMessage()
    Generic function to make the embed description of 4chan commands based on a list of thread to display
    
    Parameters
    ------
    emoji: string, emoji to display
    board: string, 4chan board
    threads: list of threads as returned by get4chan()
    
    Returns
    ----------
    tuple: containing:
        str: The text, limited to 1800 characters
        str: The thumbnail url or None
    """
    def make4chanMessage(self, emoji : str, board : str, threads : list) -> str:
        msg = []
        l = 0
        thumbnail = None
        for t in threads:
            if len(t[2]) > 34:
                msg.append('{} [{} replies](https://boards.4channel.org/{}/thread/{}) ▫️ {}...\n'.format(emoji, t[1], board, t[0], t[2][:33]))
            else:
                msg.append('{} [{} replies](https://boards.4channel.org/{}/thread/{}) ▫️ {}\n'.format(emoji, t[1], board, t[0], t[2]))
            l += len(msg[-1])
            if thumbnail is None and len(t) >= 4: thumbnail = t[3]
            if l > 1800:
                msg.append('and more...')
                break
        return ''.join(msg), thumbnail

    @search.sub_command_group(name="4chan")
    async def fourchan(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @fourchan.sub_command()
    async def thread(self, inter: disnake.GuildCommandInteraction, board : str = commands.Param(description="The board to search on."), search : str = commands.Param(description="Search string")) -> None:
        """Search 4chan threads"""
        await inter.response.defer(ephemeral=True)
        nsfw = ['b', 'r9k', 'pol', 'bant', 'soc', 's4s', 's', 'hc', 'hm', 'h', 'e', 'u', 'd', 'y', 't', 'hr', 'gif', 'aco', 'r']
        board = board.lower().replace('/', '')
        if board in nsfw and not inter.channel.is_nsfw():
            await inter.edit_original_message("The board `{}` is restricted to NSFW channels".format(board))
            return
        threads = await self.get4chan(board, search)
        thumbnail = None
        if len(threads) > 0:
            msg, thumbnail = self.make4chanMessage(':four_leaf_clover:', board, threads)
            await inter.edit_original_message(embed=self.bot.embed(title="4chan Search result", description=msg, thumbnail=thumbnail, footer="Have fun, fellow 4channeler", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="4chan Search result", description="No matching threads found", color=self.COLOR))

    @fourchan.sub_command()
    async def gbfg(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the latest /gbfg/ threads"""
        await inter.response.defer(ephemeral=True)
        threads = await self.get4chan('vg', '/gbfg/')
        thumbnail = None
        if len(threads) > 0:
            msg, thumbnail = self.make4chanMessage(':poop:', 'vg', threads)
            await inter.edit_original_message(embed=self.bot.embed(title="/gbfg/ latest thread(s)", description=msg, thumbnail=thumbnail, footer="Have fun, fellow 4channeler", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="/gbfg/ Error", description="I couldn't find a single /gbfg/ thread 😔", color=self.COLOR))

    @fourchan.sub_command()
    async def hgg(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the latest /hgg2d/ threads (NSFW channels Only)"""
        await inter.response.defer(ephemeral=True)
        if not inter.channel.is_nsfw():
            await inter.edit_original_message(embed=self.bot.embed(title=':underage: NSFW channels only', color=self.COLOR))
            return
        threads = await self.get4chan('vg', '/hgg2d/')
        thumbnail = None
        if len(threads) > 0:
            msg, thumbnail = self.make4chanMessage('🔞', 'vg', threads)
            await inter.edit_original_message(embed=self.bot.embed(title="/hgg2d/ latest thread(s)", description=msg, thumbnail=thumbnail, footer="Have fun, fellow 4channeler", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="/hgg2d/ Error", description="I couldn't find a single /hgg2d/ thread 😔", color=self.COLOR))

    """yandex_reverse_image_search()
    Perform a reverse image search on yandex.com
    
    Parameters
    ----------
    image_url: String, the url of the image to reverse search
    
    Returns
    ----------
    list: List of tuples (Page Title, Url)
    """
    async def yandex_reverse_image_search(self, image_url : str) -> list:
        try:
            url = (await self.bot.net.request('https://www.yandex.com/images/search', params={'url': image_url, 'rpt': 'imageview', 'format': 'json','request': '{"blocks":[{"block":"b-page_type_search-by-image__link"}]}'}, no_base_headers=True, expect_JSON=True, add_user_agent=True))['blocks'][0]['params']['url']
            content = await self.bot.net.request('https://www.yandex.com/images/search' + '?' + url, no_base_headers=True, add_user_agent=True)
            soup = BeautifulSoup(content, "html.parser")
            divs = soup.find_all('div', class_='Root') # root divs
            for div in divs:
                if 'CbirSites_infinite' in div['id'] and div.has_attr('data-state') and len(div.attrs['data-state']) > 3: # part to parse
                    data = json.loads(div.attrs['data-state'])
                    results = []
                    for t in data['sites']:
                        if 'on Twitter:' in t['title']:
                            t['title'] = t['title'].split('on Twitter:', 1)[0] + 'on Twitter:' # fix for twitter names
                        results.append((t['title'], t['url']))
                        if len(results) == 8: break
                    return results
            return []
        except:
            return []

    @commands.message_command(name="Image Search")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.guild)
    async def reverse(self, inter: disnake.MessageCommandInteraction, message: disnake.Message) -> None:
        """Reverse image search an attached image on Yandex"""
        try:
            await inter.response.defer(ephemeral=True)
            try:
                img_url = message.attachments[0].url
            except:
                try:
                    img_url = message.content
                    a = img_url.find('http')
                    if a == -1: raise Exception()
                    m = 999999999999999
                    x = None
                    for ex in ['.png', '.jpeg', '.jpg', '.gif', '.webp', 'jpg:thumb', 'jpg:small', 'jpg:medium', 'jpg:large', 'jpg:orig', 'png:thumb', 'png:small', 'png:medium', 'png:large', 'png:orig']:
                        b = img_url.find(ex, a)
                        if b == -1: continue
                        b += len(ex)
                        if b < m:
                            m = b
                            x = ex
                    if x is None: raise Exception()
                    img_url = img_url[a:m]
                except:
                    img_url = None
            if img_url is None:
                await inter.edit_original_message(embed=self.bot.embed(title="Yandex Reverse Image Search", description="I couldn't find an image in this message", color=self.COLOR))
            else:
                description = ""
                for r in await self.yandex_reverse_image_search(img_url):
                    description += "- [{}]({}) ({})\n".format(r[0].replace('[', '(').replace(']', ')'), r[1], r[1].replace('http://', '').replace('https://', '').split('/', 1)[0])
                if description == "":
                    description = "No results"
                else:
                    description = "Possible matches:\n" + description
                await inter.edit_original_message(embed=self.bot.embed(title="Yandex Reverse Image Search", description=description, thumbnail=img_url, footer="Check where those links go before clicking", color=self.COLOR))
        except Exception as e:
            self.bot.logger.pushError("[SEARCH] 'Image Search' Error:", e)
            await inter.edit_original_message(embed=self.bot.embed(title="Yandex Reverse Image Search", description="An unexpected error occured", color=self.COLOR))