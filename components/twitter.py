import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import html
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import re
import random
import sys

# ----------------------------------------------------------------------------------------------------------------
# Twitter Component
# ----------------------------------------------------------------------------------------------------------------
# Tweet feed for @granblue_en
# ----------------------------------------------------------------------------------------------------------------

class Twitter():
    SCHEDULE_REGEX = re.compile("^([a-zA-Z]+ [0-9]+ schedule)") # regex for schedule detection
    ACCOUNT = 'granblue_en' # account to follow
    SUFFIX = "" # url suffix
    MAX_TWEET = 150 # max tweet to old in memory
    REMOVE_AMOUNT = 20 # old tweets to remove from memory at once
    TWEET_TIMESPAN = 1200 # seconds
    SPAM_TIMESPAN = 240 # seconds
    SPAM_THRESHOLD = 2 # 4 tweets
    NIGHT_MULTIPLIER = 3 # increase in cooldown during night
    NIGHT_START = 1 # start hour of night (JST)
    NIGHT_END = 7 # start hour of night (JST)
    STAT_COUNT = 10 # number of stat data point

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.prev_cache = {self.ACCOUNT:[]}
        self.stats = []
        self.instance_stats = {}
        self.debug = '-twitter' in sys.argv and self.bot.debug_mode
        self.recent = {}

    def init(self):
        pass

    """isCorrection()
    Calculate if a tweet is a fix for a previous tweet
    
    Parameters
    --------
    content: String to compare
    author: Tweet author
    
    Returns
    --------
    bool: True if similar to a previous tweet, False otherwise
    """
    def isCorrection(self, content : str, author : str) -> bool:
        if author in self.prev_cache:
            for previous in self.prev_cache[author]:
                if SequenceMatcher(None, content, previous).ratio() >= 0.68:
                    return True
        return False

    """get_stats()
    Return nitter instance uptime stats
    
    Returns
    --------
    String
    """
    def get_stats(self) -> str:
        if len(self.stats) == 0:
            return "Undefined"
        else:
            return "{:.1f}%, Avg. {:.1f}%".format(self.stats[-1] * 100, 100 * sum(self.stats) / len(self.stats)).replace('.0', '')

    """tweetfeed()
    Coroutine task used to get tweets to announcement channels
    """
    async def tweetfeed(self) -> None:
        if len(self.bot.data.config['nitter']) == 0:
            self.bot.logger.push("[TASK] 'tweetfeed' got no Nitter instances set in config.json\nSet them and restart Rosetta to use this feature.", level=self.bot.logger.WARNING)
            return
        for instance in self.bot.data.config['nitter']: # set stats
            self.instance_stats[instance] = [0, 0]
        ierr = 0 # instance error
        sleep = False # to tell to sleep between requests
        stats = [0, 0] # stats collection
        if self.ACCOUNT not in self.bot.data.save['twitter']:
            self.bot.data.save['twitter'][self.ACCOUNT] = []
        try:
            await asyncio.sleep(60)
            while True:
                for instance in self.bot.data.config['nitter']:
                    # clean stats if too big
                    if sum(self.instance_stats[instance]) >= 100000:
                        self.instance_stats[instance] = [0, 0]
                    # sleep between each runs
                    if sleep:
                        h = self.bot.util.JST().hour
                        sleep_mod = self.NIGHT_MULTIPLIER if ((self.NIGHT_START < self.NIGHT_END and h >= self.NIGHT_START and h < self.NIGHT_END) or (self.NIGHT_START > self.NIGHT_END and (h >= self.NIGHT_START or h < self.NIGHT_END))) else 1 # double sleep duration during japan night
                        await asyncio.sleep(random.randint(50, 90)*sleep_mod)
                    sleep = False
                    stats[0] += 1
                    print(instance + self.ACCOUNT + self.SUFFIX)
                    req = await self.bot.net.request(instance + self.ACCOUNT + self.SUFFIX, follow_redirects=True, no_base_headers=True, add_user_agent=True, headers={"accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9", "accept-encoding": "gzip, deflate", "accept-language": "en", "cache-control": "no-cache"}|self.bot.net.DEFAULT_SEC_HEADERS)
                    # error handling
                    if req is None:
                        ierr += 1
                        print(ierr)
                        self.instance_stats[instance][0] += 1 # error, go to next instance
                        if self.instance_stats[instance][1] == 0 and self.instance_stats[instance][0] == 100:
                            self.bot.logger.pushError("[TASK] 'tweetfeed' Instance `{}` might be down".format(instance))
                        if ierr >= len(self.bot.data.config['nitter']):
                            self.bot.logger.pushError("[TASK] 'tweetfeed' Down")
                            await asyncio.sleep(7200)
                        continue
                    self.instance_stats[instance][1] += 1 # success
                    stats[1] += 1
                    sleep = True
                    # set variables
                    recent = {} # count tweet received per author for the current iteration
                    ierr = 0 # reset error count
                    current_time = self.bot.util.UTC()
                    # parse html
                    soup = BeautifulSoup(req.decode('utf-8'), 'html.parser') # parse page
                    # read timeline
                    timeline = soup.find_all('div', class_='timeline')[0] # get timeline
                    tweets = []
                    dd = timeline.findChildren("div", recursive=False) # extract div
                    for child in dd: # read tweets
                        if 'unavailable' in child.attrs['class']:
                            continue
                        elif 'timeline-item' in child.attrs['class']: # timeline
                            tweets.append((child, 0, 0))
                        elif 'thread-line' in child.attrs['class']: # thread (only in multi mode it seems)
                            for i, item in enumerate(child.findChildren("div", class_='timeline-item', recursive=False)): # timeline of thread
                                tweets.append((item, i, 1))
                    # iterate over tweets to detect new ones
                    to_send = []
                    for tweet, chain, tweettype in tweets:
                        # link
                        reference = tweet.findChildren('a', class_='tweet-link')
                        if len(reference) == 0: continue # continue if no data
                        reference = reference[0].attrs['href'].split('#')[0]
                        author = reference.split('/')[1]
                        if author != self.ACCOUNT: continue
                        tid = reference.split('/')[-1]
                        if tid in self.bot.data.save['twitter'].get(author, []): # keep known tweet at the end of data
                            try: self.bot.data.save['twitter'].get(author, []).pop(self.bot.data.save['twitter'].get(author, []).index(tid))
                            except: pass
                            self.bot.data.save['twitter'][author].append(tid)
                            self.bot.data.pending = True
                            continue
                        # extract date
                        date = tweet.findChildren('span', class_='tweet-date')[0].findChildren('a')[0].attrs['title'].replace(',', '').split(' ')
                        date[0] = {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}.get(date[0], date[0])
                        date[1] = date[1].zfill(2)
                        date.pop(3)
                        date.pop()
                        date[-2] = date[-2].split(':')
                        h = int(date[-2][0]) % 12 + (12 if date[-1] == 'PM' else 0)
                        date[-2] = '{}:{}'.format(h, date[-2][1])
                        date.pop()
                        date = datetime.strptime(' '.join(date), '%m %d %Y %H:%M')
                        # extract content
                        content = tweet.findChildren('div', class_='tweet-content')[0].text
                        # tweet flags
                        replying = (len(tweet.findChildren('div', class_='tweet-body')[0].findChildren('div', class_='replying-to', recursive=False)) > 0 or chain > 0 or (tweettype == 0 and len(tweet.findChildren('a', class_='show-thread')) > 0))
                        retweet = len(tweet.findChildren('div', class_='retweet-header')) > 0
                        # video = len(tweet.findChildren('div', class_='video-container')) > 0 # UNUSED
                        # filter RT and similar tweets
                        if retweet or author not in reference or self.isCorrection(content, author): continue
                        # cache
                        self.prev_cache[author].append(content)
                        if len(self.prev_cache[author]) >= self.MAX_TWEET:
                            self.prev_cache[author] = self.prev_cache[author][self.REMOVE_AMOUNT:]
                        recent[author] = recent.get(author, 0) + 1
                        if current_time - date < timedelta(seconds=self.TWEET_TIMESPAN):
                            to_send.append((author, tid, reference, replying, content))
                    # send tweets
                    if len(to_send) > 0:
                        to_send.reverse()
                        timestamp = int(current_time.timestamp())
                        # count recent tweets sent to main channels
                        recent_count = 0
                        ts = list(self.recent.keys())
                        for t in ts:
                            if timestamp - t > self.SPAM_TIMESPAN: self.recent.pop(t)
                            else: recent_count += self.recent[t]
                        spam_count = 0
                        # send
                        for i, tweet in enumerate(to_send):
                            author, tid, reference, replying, content = tweet
                            self.bot.data.save['twitter'][author].append(tid)
                            self.bot.data.pending = True
                            if self.debug: # debug mode
                                await self.bot.send('debug', 'https://twitter.com' + reference)
                            else:
                                is_spam = i > 0 or recent_count+spam_count >= self.SPAM_THRESHOLD or replying
                                if is_spam:
                                    chs = self.bot.channel.tweets_spam
                                else:
                                    chs = self.bot.channel.tweets
                                    # spam count
                                    spam_count += 1
                                await self.bot.sendMulti(chs, 'https://vxtwitter.com' + reference, publish=(not is_spam)) # keep using vxtwitter for now
                            # check new schedule
                            if author == 'granblue_en':
                                try:
                                    content = html.unescape(content)
                                    group = self.SCHEDULE_REGEX.findall(content)
                                    if len(group) > 0:
                                        title = group[0].lower().split(' ')
                                        if title[0] in ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']:
                                            s = content.find("https://t.co/")
                                            if s != -1: content = content[:s]
                                            lines = content.split('\n')
                                            schedule = []
                                            for i in range(1, len(lines)):
                                                lines[i] = lines[i].strip()
                                                if lines[i] != "":
                                                    tmp = lines[i].replace(": ", " = ").split(" = ")
                                                    if len(tmp) > 2:
                                                        tmp = [tmp[0], ": ".join(tmp[1:])]
                                                    elif len(tmp) < 2:
                                                        tmp = ["??/??", tmp[0]]
                                                    schedule += tmp
                                            if len(schedule) > 0:
                                                self.bot.data.save['schedule'] = schedule
                                                self.bot.data.pending = True
                                except Exception as se:
                                    self.bot.logger.pushError("[TASK] 'tweetfeed (Schedule)' Task Error:", se)
                        if spam_count > 0:
                            self.recent[timestamp] = spam_count
                        if len(self.bot.data.save['twitter'][author]) > self.MAX_TWEET:
                            self.bot.data.save['twitter'][author] = self.bot.data.save['twitter'][author][self.REMOVE_AMOUNT:]
                            self.bot.data.pending = True
                    # nitter stats for this loop
                    self.stats.append(stats[1] / stats[0])
                    if len(self.stats) > self.STAT_COUNT:
                        self.stats = self.stats[len(self.stats)-5:]
                    stats = [0, 0]
        except asyncio.CancelledError:
            self.bot.logger.push("[TASK] 'tweetfeed' Task Cancelled")
            return
        except Exception as e:
            self.bot.logger.pushError("[TASK] 'tweetfeed' Task Error (instance: `{}`):".format(instance), e)
            await asyncio.sleep(120)