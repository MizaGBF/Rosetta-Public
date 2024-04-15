from typing import Any, Generator, Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from contextlib import asynccontextmanager
import aiohttp
import re
from datetime import timedelta
from deep_translator import GoogleTranslator

# ----------------------------------------------------------------------------------------------------------------
# Network Component
# ----------------------------------------------------------------------------------------------------------------
# This component is the interface with Granblue Fantasy (account wise) and other websites
# ----------------------------------------------------------------------------------------------------------------

class Network():
    VERSION_REGEX = re.compile("Game\.version = \"(\d+)\";")
    DEFAULT_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    DEFAULT_CHROME_VER = 120
    DEFAULT_SEC_HEADERS = {"Sec-Ch-Ua": '"Not=A?Brand";v="99", "Chromium";v="{}"'.format(DEFAULT_CHROME_VER), "Sec-Ch-Ua-Mobile": "?0", "Sec-Ch-Ua-Platform": "Windows", "Sec-Fetch-Dest": "document", "Sec-Fetch-Mode": "navigate", "Sec-Fetch-Site": "none", "Sec-Fetch-User": "?1"}
    DEFAULT_HEADERS = {'Connection': 'keep-alive', 'Accept': 'application/json, text/javascript, */*; q=0.01', 'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'en', 'Host': 'game.granbluefantasy.jp', 'Origin': 'https://game.granbluefantasy.jp', 'Referer': 'https://game.granbluefantasy.jp/'}
    
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.translator = GoogleTranslator(source='auto', target='en')
        self.client = None

    def init(self) -> None:
        pass

    """init_client()
    Context manager for the aiohttp client, to ensure it will be closed upon exit. Used in bot.py
    """
    @asynccontextmanager
    async def init_client(self) -> Generator[aiohttp.ClientSession, None, None]:
        try:
            self.client = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
            yield self.client
        finally:
            await self.client.close()

    """request()
    Coroutine to request a network resource. This function is tailored to be used with GBF.
    
    Parameters
    ----------
    base_url: Url to request from. Special keywords can be added to the URL to substitute some values automatically:
        - VER: GBF Version number
        - TS1: Timestamp
        - TS2: Timestamp (further than TS1)
        - ID: GBF Profile ID
        - PARAMS: GBF request parameters: _=TS1&t=TS2&uid=ID
    options: Possible options are:
        - no_base_headers: Boolean (Default is False). If False, set the necessary headers to communicate with GBF main server.
        - add_user_agent: Boolean (Default is False). If True and an user agent is not set, set it.
        - headers: Dict, headers set by the user
        - params: Dict, set to None to ignore
        - account: Integer, registered GBF account id to use. Default is None to not use one.
        - payload: Dict (Default is None), POST request payload. Set to None to do a GET request. Additionaly, some the 'user_id' value can be automatically set if it's equal to the following:
            - "ID": The GBF Profile ID
            - "SID": The GBF Profile ID, as a string
            - "IID": The GBF Profile ID, as an integer
        - timeout: Integer, timeout in seconds. Set to None to use the default 20s timeout.
        - follow_redirects: Boolean (Default is False), set to True to follow request redirections if you expect any.
        - rtype: To do another type of request. Only when payload is None (aka for GET requests). Possible values are "GET" (default), "HEAD", "CONDITIONAL-GET" (will return the response), "POST"
        - expect_JSON: Boolean (Default is False), set to True if you expect to receive a JSON and the function will return an error if it's not one.
        - collect_headers: Default is None. Set it to a list of size one and the request headers will be inserted in the first emplacement.
        - skip_check: Boolean, skip the maintenance check. For internal use only, ignore it.
        - updated: Boolean. For internal use only, ignore it.
    
    Returns
    ----------
    unknown: None if error, else Bytes or JSON object for GET/POST, headers for HEAD, response for PARTIAL-GET
    """
    async def request(self, base_url : str, **options : dict) -> Any:
        try:
            host = base_url.replace('http://', '').replace('https://', '').split('/')[0]
            if not options.get('skip_check', False) and host == "game.granbluefantasy.jp" and await self.gbf_maintenance(): return None
            params = options.get('params', None)
            headers = {'Connection':'keep-alive'}
            if not options.get('no_base_headers', False): headers = self.DEFAULT_HEADERS.copy()
            else: headers = {'Connection':'keep-alive'}
            if "headers" in options: headers = headers | options["headers"]
            aid = options.get('account', None)
            acc = self.get_account(aid) if aid is not None else None
            ver = self.bot.data.save['gbfversion']
            url = base_url.replace("PARAMS", "_=TS1&t=TS2&uid=ID")
            if ver == "Maintenance": 
                url = url.replace("VER/", "")
                ver = None
            elif ver is None:
                ver = 0
                url = url.replace("VER/", "{}/".format(ver))
            else:
                url = url.replace("VER/", "{}/".format(ver))
            ts = int(self.bot.util.UTC().timestamp() * 1000)
            url = url.replace("TS1", "{}".format(ts))
            url = url.replace("TS2", "{}".format(ts+300))
            cookies = None
            if aid is not None:
                if acc is None: return None
                url = url.replace("ID", "{}".format(acc[0]))
                if 'Cookie' not in headers:
                    cookies = acc[1]
                else:
                    cd = {}
                    for c in headers['Cookie'].split(";"):
                        ct = c.strip().split("=")
                        cd[ct[0]] = ct[1]
                    cookies = cd
                    del headers['Cookie']
                if 'User-Agent' not in headers: headers['User-Agent'] = acc[2]
                if 'X-Requested-With' not in headers: headers['X-Requested-With'] = 'XMLHttpRequest'
                if 'X-VERSION' not in headers: headers['X-VERSION'] = str(ver)
            payload = options.get('payload', None)
            timeout = options.get('timeout', None)
            
            if base_url.startswith('https://game.granbluefantasy.jp/'):
                self.client.cookie_jar.clear()
            
            if cookies is not None:
                self.client.cookie_jar.update_cookies(cookies)
            
            if options.get('add_user_agent', False) and 'User-Agent' not in headers:
                # try to use existing user agent
                for au in self.bot.data.save['gbfaccounts']:
                    if au[2] is not None and au[2] != '':
                        headers['User-Agent'] = au[2]
                        break
                if 'User-Agent' not in headers: # default
                    headers['User-Agent'] = self.DEFAULT_UA
            if payload is None:
                rtype = options.get('rtype', 'GET')
                match rtype:
                    case 'GET'|'CONDITIONAL-GET':
                        response = await self.client.get(url, params=params, headers=headers, timeout=timeout, allow_redirects=options.get('follow_redirects', False))
                    case 'HEAD':
                        response = await self.client.get(url, params=params, headers=headers, timeout=timeout, allow_redirects=options.get('follow_redirects', False))
                    case 'POST':
                        response = await self.client.post(url, params=params, headers=headers, timeout=timeout, allow_redirects=options.get('follow_redirects', False))
            else:
                rtype = 'POST'
                if not options.get('no_base_headers', False) and 'Content-Type' not in headers: headers['Content-Type'] = 'application/json'
                if 'user_id' in payload:
                    match payload['user_id']:
                        case "ID": payload['user_id'] = acc[0]
                        case "SID": payload['user_id'] = str(acc[0])
                        case "IID": payload['user_id'] = int(acc[0])
                response = await self.client.post(url, params=params, headers=headers, timeout=timeout, json=payload)
            if rtype == "CONDITIONAL-GET":
                return response
            async with response:
                if response.status == 503 and base_url == 'https://game.granbluefantasy.jp/': # maintenance
                    if rtype == "HEAD": return None
                    return await response.read()
                elif response.status >= 400 or response.status < 200:
                    # retry if it's a version error
                    if options.get('updated', False) is False and aid is not None and acc is not None and host == "game.granbluefantasy.jp":
                        x = await self.gbf_version() # check if update
                        if x >= 2: # if some sort of update
                            if x == 3: options['updated'] = True # trigger update
                            return await self.request(base_url, **options)
                    raise Exception()
                if aid is not None:
                    self.refresh_account(aid, response.headers['set-cookie'])
                if isinstance(options.get('collect_headers', None), list):
                    try: options['collect_headers'][0] = response.headers
                    except: pass
                is_json = response.headers.get('content-type', '').startswith('application/json')
                if options.get('expect_JSON', False) and not is_json: raise Exception()
                if rtype == "HEAD": return True
                elif is_json: return await response.json()
                else: return await response.read()
        except:
            try:
                if aid is not None: self.set_account_state(aid, 2)
            except: pass
            return None

    """str2cookie()
    Convert a cookie header string to a dictionnary
    
    Parameters
    ----------
    header: str, cookie header
    
    Returns
    ----------
    Dict: Resulting dict
    """
    def str2cookie(self, header : str) -> dict:
        cd = {}
        for c in header.split(";"):
            ct = c.split("=")
            cd[ct[0].strip()] = ct[1].strip()
        return cd

    """get_account()
    Retrieve a registered GBF account info
    
    Parameters
    ----------
    aid: Integer, account index
    
    Returns
    ----------
    List: None if error, else account data
    """
    def get_account(self, aid : int = 0) -> Optional[list]:
        try: return self.bot.data.save['gbfaccounts'][aid]
        except: return None

    """add_account()
    Register a GBF account
    
    Parameters
    ----------
    uid: Integer, profile ID
    ck: String, valid Cookie
    ua: String, User-Agent used to get the Cookie
    """
    def add_account(self, uid : int, ck : str, ua : str):
        if 'gbfaccounts' not in self.bot.data.save:
            self.bot.data.save['gbfaccounts'] = []
        self.bot.data.save['gbfaccounts'].append([uid, self.str2cookie(ck), ua, 0, 0, None])
        self.bot.data.pending = True

    """update_account()
    Edit an account value
    
    Parameters
    ----------
    aid: Integer, index of the account to edit
    uid: Integer (Optional), profile ID
    ck: String (Optional), valid Cookie
    ua: String (Optional), User-Agent used to get the Cookie
    
    Returns
    ----------
    Boolean: True if success, False if error
    """
    def update_account(self, aid : int, **options : dict) -> bool:
        try:
            uid = options.pop('uid', None)
            ck = options.pop('ck', None)
            ua = options.pop('ua', None)
            if uid is not None:
                self.bot.data.save['gbfaccounts'][aid][0] = uid
            if ck is not None:
                self.bot.data.save['gbfaccounts'][aid][1] = self.str2cookie(ck)
            if ua is not None:
                self.bot.data.save['gbfaccounts'][aid][2] = ua
            self.bot.data.pending = True
            return True
        except:
            return False

    """remove_account()
    Remove a registered account from memory
    
    Parameters
    ----------
    aid: Integer, index of the account to remove
    
    Returns
    ----------
    Boolean: True if success, False if error
    """
    def remove_account(self, aid : int) -> bool:
        try:
            if aid < 0 or aid >= len(self.bot.data.save['gbfaccounts']):
                return False
            self.bot.data.save['gbfaccounts'].pop(aid)
            if self.bot.data.save['gbfcurrent'] >= aid and self.bot.data.save['gbfcurrent'] >= 0: self.bot.data.save['gbfcurrent'] -= 1
            self.bot.data.pending = True
            return True
        except:
            return False

    """refresh_account()
    Update a registered account cookie. For internal use only.
    
    Parameters
    ----------
    aid: Integer, index of the account to refresh
    ck: String, new Cookie
    
    Returns
    ----------
    Boolean: True if success, False if error
    """
    def refresh_account(self, aid : int, ck : str) -> bool:
        try:
            if ck is None: return False
            A = self.bot.data.save['gbfaccounts'][aid][1]
            B = self.str2cookie(ck)
            for k, v in B.items():
                if k in A:
                    A[k] = v
            self.bot.data.save['gbfaccounts'][aid][1] = A
            self.bot.data.save['gbfaccounts'][aid][3] = 1
            self.bot.data.save['gbfaccounts'][aid][5] = self.bot.util.JST()
            self.bot.data.pending = True
            return True
        except Exception as e:
            self.bot.logger.pushError("[ACCOUNT] 'refresh' error:", e)
            return False

    """set_account_state()
    Change a GBF account status. For internal use only.
    
    Parameters
    ----------
    aid: Integer, index of the account to refresh
    state: Integer, 0 for undefined, 1 for good, 2 for bad
    """
    def set_account_state(self, aid : int, state : int) -> None:
        try:
            self.bot.data.save['gbfaccounts'][aid][3] = state
            self.bot.data.pending = True
        except:
            pass

    """gbf_version()
    Coroutine to retrieve the GBF version number. If success, call gbf_update() and return its result
    
    Parameters
    ----------
    skip_check: Boolean, skip the maintenance check (for internal use only)
    
    Returns
    ----------
    unknown: None if GBF is down, "Maintenance" if in maintenance, -1 if version comparison error, 0 if equal, 1 if v is None, 2 if saved number is None, 3 if different
    """
    async def gbf_version(self, skip_check = False) -> Any: # retrieve the game version
        res = await self.request('https://game.granbluefantasy.jp/', headers={'Accept-Language':'en', 'Accept-Encoding':'gzip, deflate', 'Host':'game.granbluefantasy.jp', 'Connection':'keep-alive'}, add_user_agent=True, no_base_headers=True, skip_check=skip_check, follow_redirects=True)
        if res is None: return None
        res = str(res)
        try:
            return self.gbf_update(int(self.VERSION_REGEX.findall(res)[0]))
        except:
            if 'maintenance' in res.lower():
                return "Maintenance"
            else:
                return None

    """gbf_update()
    Compare a GBF version number with the one stored in memory and update if needed
    
    Parameters
    ----------
    v: Integer, a GBF version number. Also support None.
    
    Returns
    ----------
    Integer: -1 if error, 0 if equal, 1 if v is None, 2 if saved number is None, 3 if different
    """
    def gbf_update(self, v : Optional[int]) -> int: # compare version with given value, then update and return a value depending on difference
        try:
            int(v)
            if v is None:
                return 1 # unchanged because of invalid parameter
            elif self.bot.data.save['gbfversion'] is None:
                self.bot.data.save['gbfversion'] = v
                self.bot.data.save['gbfupdate'] = False
                self.savePending = True
                return 2 # value is set
            elif self.bot.data.save['gbfversion'] != v:
                self.bot.data.save['gbfversion'] = v
                self.bot.data.save['gbfupdate'] = True
                self.bot.data.pending = True
                return 3 # update happened
            return 0 # unchanged
        except:
            return -1 # v isn't an integer

    """gbf_available()
    Coroutine to retrieve the GBF version to check if the game is available.
    
    Parameters
    ----------
    skip_check: Boolean, skip the maintenance check (for internal use only)
    
    Returns
    ----------
    Boolean: True if the game is available, False otherwise.
    """
    async def gbf_available(self, skip_check = False) -> bool: # use the above to check if the game is up
        if skip_check is False and await self.gbf_maintenance(): return False
        v = await self.gbf_version(skip_check)
        if v is None: v = await self.gbf_version(skip_check) # try again in case their shitty server is lagging
        match v:
            case None:
                return False
            case 'Maintenance':
                if self.bot.data.save['maintenance']['state'] is False or (self.bot.data.save['maintenance']['state'] is True and self.bot.data.save['maintenance']['duration'] > 0 and self.bot.util.JST() > self.bot.data.save['maintenance']['time'] + timedelta(seconds=3600*self.bot.data.save['maintenance']['duration'])):
                    self.bot.data.save['maintenance'] = {"state" : True, "time" : None, "duration" : 0}
                    self.bot.data.pending = True
                    self.bot.logger.push("[GBF] Possible emergency maintenance detected")
                return False
            case _:
                return True

    """gbf_maintenance_status()
    Check if GBF is in maintenance and return a string.
    Save data is updated if it doesn't match the current state.
    
    Parameters
    ----------
    check_maintenance_end: Boolean, check if emergency maintenance ended (for internal use only)
    
    Returns
    --------
    str: Status string
    """
    async def gbf_maintenance_status(self, check_maintenance_end : bool = False) -> str:
        current_time = self.bot.util.JST()
        msg = ""
        if self.bot.data.save['maintenance']['state'] is True:
            if self.bot.data.save['maintenance']['time'] is not None and current_time < self.bot.data.save['maintenance']['time']:
                if self.bot.data.save['maintenance']['duration'] == 0:
                    msg = "{} Maintenance at **{}**".format(self.bot.emote.get('cog'), self.bot.util.time(self.bot.data.save['maintenance']['time'], style=['d','t'], removejst=True))
                else:
                    d = self.bot.data.save['maintenance']['time'] - current_time
                    msg = "{} Maintenance starts in **{}**, for **{} hour(s)**".format(self.bot.emote.get('cog'), self.bot.util.delta2str(d, 2), self.bot.data.save['maintenance']['duration'])
            else:
                if self.bot.data.save['maintenance']['duration'] <= 0:
                    if not check_maintenance_end or (check_maintenance_end and not await self.gbf_available(skip_check=True)):
                        msg = "{} Emergency maintenance on going".format(self.bot.emote.get('cog'))
                    else:
                        self.bot.data.save['maintenance'] = {"state" : False, "time" : None, "duration" : 0}
                        self.bot.data.pending = True
                else:
                    d = current_time - self.bot.data.save['maintenance']['time']
                    if (d.seconds // 3600) >= self.bot.data.save['maintenance']['duration']:
                        self.bot.data.save['maintenance'] = {"state" : False, "time" : None, "duration" : 0}
                        self.bot.data.pending = True
                    else:
                        e = self.bot.data.save['maintenance']['time'] + timedelta(seconds=3600*self.bot.data.save['maintenance']['duration'])
                        d = e - current_time
                        msg = "{} Maintenance ends in **{}**".format(self.bot.emote.get('cog'), self.bot.util.delta2str(d, 2))
        return msg

    """gbf_maintenance()
    Return True if a scheduled or emergency ùaintenance is on going
    
    Parameters
    ----------
    check_maintenance_end: Boolean, check if emergency maintenance ended (for internal use only)
    
    Returns
    --------
    bool: True if on going, False otherwise
    """
    async def gbf_maintenance(self, check_maintenance_end : bool = False) -> bool:
        msg = await self.gbf_maintenance_status(check_maintenance_end=check_maintenance_end)
        return (' ends in ' in msg or 'on going' in msg)

    """translate()
    Machine translate some text to english
    
    Parameters
    ----------
    original_text: String to translate
    
    Returns
    ----------
    str: Translated String
    
    Raises
    ----------
    exception: If an error occurs
    """
    def translate(self, original_text : str) -> str:
        if original_text == "": return original_text
        return self.translator.translate(original_text)