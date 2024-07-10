from typing import Any, Generator, Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from contextlib import asynccontextmanager
import aiohttp
import re
from datetime import timedelta
from yarl import URL # package should come with aiohttp/disnake
from deep_translator import GoogleTranslator

# ----------------------------------------------------------------------------------------------------------------
# Network Component
# ----------------------------------------------------------------------------------------------------------------
# This component is the interface with Granblue Fantasy (account wise) and other websites
# ----------------------------------------------------------------------------------------------------------------

class Network():
    VERSION_REGEX = re.compile("Game\.version = \"(\d+)\";")
    GET = 0
    POST = 1
    HEAD = 2
    CONDITIONAL_GET = 4
    ACC_UID = 0
    ACC_CK = 1
    ACC_UA = 2
    ACC_STATE = 3
    ACC_TIME = 4
    ACC_STATUS_UNDEF = 0
    ACC_STATUS_OK = 1
    ACC_STATUS_DOWN = 2
    
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36 Rosetta/'+bot.VERSION
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
    Coroutine to request a network resource.
    Use requestGBF to request GBF with an account, or requestWiki to request the Wiki
    
    Parameters
    ----------
    url: Url to request from.
    rtype: Integer (Default is 0 or GET). Set the request type when payload is None. Use the constant GET, POST, HEAD, CONDITIONAL-GET defined in this class.
    headers: Dict, request headers set by the user. Prefer using add_user_agent instead of setting the user agent yourself.
    params: Dict, set to None to ignore.
    payload: Dict (Default is None), POST request payload. Set to None to do another request type.
    allow_redirects: Boolean (Default is False), set to True to follow request redirections if you expect any.
    expect_JSON: Boolean (Default is False), set to True if you expect to receive a JSON and the function will return an error if it's not one.
    ssl: BOolean (Default is True), set to False to disable ssl verifications
    collect_headers: Default is None. Pass the following '[[None]]' and the request headers will be inserted in place of None.
    
    Returns
    ----------
    unknown: None if error, else Bytes or JSON object for GET/POST, headers for HEAD, response for PARTIAL-GET
    """
    async def request(self, url : str, *, rtype : int = 0, headers : dict = {}, params : Optional[dict] = None, payload : Optional[dict] = None, add_user_agent : bool = False, allow_redirects : bool = False, expect_JSON : bool = False, ssl : bool = True, collect_headers : Optional[dict] = None) -> Any:
        try:
            headers['Connection'] = 'keep-alive'
            if add_user_agent and 'User-Agent' not in headers:
                headers['User-Agent'] = self.user_agent
            if payload is None:
                match rtype:
                    case self.GET|self.CONDITIONAL_GET:
                        response = await self.client.get(url, params=params, headers=headers, allow_redirects=allow_redirects, ssl=ssl)
                    case self.HEAD:
                        response = await self.client.get(url, params=params, headers=headers, allow_redirects=allow_redirects, ssl=ssl)
                    case self.POST:
                        response = await self.client.post(url, params=params, headers=headers, allow_redirects=allow_redirects, ssl=ssl)
                    case _:
                        raise Exception("Unknown request type")
            else:
                rtype = self.POST
                response = await self.client.post(url, params=params, headers=headers, json=payload, allow_redirects=allow_redirects, ssl=ssl)
            if rtype == "CONDITIONAL-GET":
                return response
            async with response:
                if response.status >= 400 or response.status < 200:
                    raise Exception("HTTP Error " + str(response.status))
                if collect_headers is not None and collect_headers == [[None]]:
                    try: collect_headers[0] = response.headers
                    except: pass
                ct = response.headers.get('content-type', '')
                is_json = 'application/json' in ct
                if expect_JSON and not is_json: raise Exception("Expected `application/json`, got `{}`".format(ct))
                if rtype == "HEAD": return True
                elif is_json: return await response.json()
                else: return await response.read()
        except Exception as e:
            self.bot.logger.pushError("[NET] request `{}` Error:".format(url), e)
            return None

    """requestGBF()
    Coroutine to request Granblue Fantasy with a working account.
    
    Parameters
    ----------
    path: Url path.
    account: Registered account to use.
    rtype: Integer (Default is 0 or GET). Set the request type when payload is None. Use the constant GET, POST, HEAD, CONDITIONAL-GET defined in this class.
    params: Dict. Automatically set when requesting GBF.
    payload: Dict (Default is None), POST request payload. Set to None to do another request type. Additionaly, the 'user_id' value can be automatically set if it's equal to the following:
        - "ID": The GBF Profile ID
        - "SID": The GBF Profile ID, as a string
        - "IID": The GBF Profile ID, as an integer
    allow_redirects: Bool, set to True to follow redirects.
    expect_JSON: Boolean (Default is False), set to True if you expect to receive a JSON and the function will return an error if it's not one.
    _updated_: Boolean, for internal use only.
    
    Returns
    ----------
    unknown: None if error, else Bytes or JSON object for GET/POST, headers for HEAD, response for CONDITIONAL-GET
    """
    async def requestGBF(self, path : str, account : int, *, rtype : int = 0, params : dict = {}, payload : Optional[dict] = None, allow_redirects : bool = False, expect_JSON : bool = False, _updated_ : bool = False) -> Any:
        try:
            silent = True
            if await self.gbf_maintenance(): return None
            if path[:1] != "/": url = "https://game.granbluefantasy.jp/" + path
            else: url = "https://game.granbluefantasy.jp" + path
            # retrieve account info
            acc = self.get_account(account)
            if acc is None: raise Exception("Invalid account selection")
            silent = (acc[self.ACC_STATE] == self.ACC_STATUS_DOWN)
            # retrieve version
            ver = self.bot.data.save['gbfversion']
            if ver == "Maintenance":
                raise Exception("Maintenance on going")
            elif ver is None:
                ver = 0
            # set headers
            headers = {'Connection':'keep-alive', 'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'en', 'Host': 'game.granbluefantasy.jp', 'Origin': 'https://game.granbluefantasy.jp', 'Referer': 'https://game.granbluefantasy.jp/', 'User-Agent':acc[2], 'X-Requested-With':'XMLHttpRequest', 'X-VERSION':str(ver)}
            # set cookies
            self.client.cookie_jar.update_cookies(acc[1], URL('https://game.granbluefantasy.jp'))
            # set params
            ts = int(self.bot.util.UTC().timestamp() * 1000)
            params["_"] = str(ts)
            params["t"] = str(ts+300)
            params["uid"] = str(acc[0])
            if payload is None:
                match rtype:
                    case self.GET|self.CONDITIONAL_GET:
                        response = await self.client.get(url, params=params, headers=headers, allow_redirects=allow_redirects)
                    case self.HEAD:
                        response = await self.client.head(url, params=params, headers=headers, allow_redirects=allow_redirects)
                    case self.POST:
                        response = await self.client.post(url, params=params, headers=headers, allow_redirects=allow_redirects)
                    case _:
                        raise Exception("Unknown request type")
            else:
                rtype = self.POST
                # auto set ID
                if 'user_id' in payload:
                    match payload['user_id']:
                        case "ID": payload['user_id'] = acc[0]
                        case "SID": payload['user_id'] = str(acc[0])
                        case "IID": payload['user_id'] = int(acc[0])
                response = await self.client.post(url, params=params, headers=headers, json=payload, allow_redirects=allow_redirects)
            # response handling
            async with response:
                if rtype == self.CONDITIONAL_GET:
                    return response
                if response.status >= 400 or response.status < 200:
                    # retry if it's a version error
                    if not _updated_:
                        x = await self.gbf_version() # check if update
                        if x is not None and x >= 2: # if some sort of update
                            if x == 3: _updated_ = True
                            return await self.requestGBF(path, account, rtype, params, payload, allow_redirects, expect_JSON, _updated_)
                    raise Exception()
                ct = response.headers.get('content-type', '')
                is_json = 'application/json' in ct
                if expect_JSON and not is_json:
                    self.bot.logger.pushError("[ACCOUNT] GBF Account #{} might be down".format(account), send_to_discord=(not silent))
                    self.set_account_state(account, self.ACC_STATUS_DOWN)
                    return None
                self.refresh_account(account, response.headers['set-cookie'])
                if rtype == "HEAD": return True
                elif is_json: return await response.json()
                else: return await response.read()
        except Exception as e:
            if str(e) != "":
                self.bot.logger.pushError("[NET] requestGBF `{}` Error:".format(path), e, send_to_discord=(not silent))
            return None

    """requestWiki()
    Coroutine to request the gbf.wiki.
    Only support GET requests.
    
    Parameters
    ----------
    path: Url path.
    allow_redirects: Bool, set to True to follow redirects.
    
    Returns
    ----------
    unknown: None if error, else Bytes or JSON object
    """
    async def requestWiki(self, path : str, allow_redirects : bool = False) -> Any:
        try:
            if path[:1] != "/": url = "https://gbf.wiki/" + path
            else: url = "https://gbf.wiki" + path
            response = await self.client.get(url, headers= {'Connection':'keep-alive', 'User-Agent':self.user_agent, "Accept":"text/html,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Accept-Encoding":"gzip, deflate", "Accept-Language":"en-US,en;q=0.9", 'Host':'gbf.wiki', 'Origin':'https://gbf.wiki', "Referer":"https://gbf.wiki/"}, timeout=8, allow_redirects=allow_redirects)
            async with response:
                if response.status == 403:
                    raise Exception("HTTP Error 403 - Possibly Cloudflare related")
                elif response.status >= 400 or response.status < 200:
                    raise Exception("HTTP Error " + str(response.status))
                if response.headers.get('content-type', '').startswith('application/json'): return await response.json()
                else: return await response.read()
        except Exception as e:
            self.bot.logger.pushError("[NET] requestWiki `{}` Error:".format(path), e)
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
        self.bot.data.save['gbfaccounts'].append([uid, self.str2cookie(ck), ua, self.ACC_STATUS_UNDEF, None])
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
                self.bot.data.save['gbfaccounts'][aid][self.ACC_UID] = uid
                self.bot.data.pending = True
            if ck is not None:
                self.bot.data.save['gbfaccounts'][aid][self.ACC_CK] = self.str2cookie(ck)
                self.bot.data.pending = True
            if ua is not None:
                self.bot.data.save['gbfaccounts'][aid][self.ACC_UA] = ua
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
            self.bot.data.save['gbfaccounts'][aid][self.ACC_CK] = A
            self.bot.data.save['gbfaccounts'][aid][self.ACC_STATE] = self.ACC_STATUS_OK
            self.bot.data.save['gbfaccounts'][aid][self.ACC_TIME] = self.bot.util.JST()
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
            if state != self.bot.data.save['gbfaccounts'][aid][self.ACC_STATE]:
                self.bot.data.save['gbfaccounts'][aid][self.ACC_STATE] = state
                self.bot.data.pending = True
        except:
            pass

    """gbf_version()
    Coroutine to retrieve the GBF version number. If success, call gbf_update() and return its result
    
    Returns
    ----------
    unknown: None if GBF is down, "Maintenance" if in maintenance, -1 if version comparison error, 0 if equal, 1 if v is None, 2 if saved number is None, 3 if different
    """
    async def gbf_version(self) -> Any: # retrieve the game version
        res = await self.request('https://game.granbluefantasy.jp/', headers={'Accept-Language':'en', 'Accept-Encoding':'gzip, deflate', 'Host':'game.granbluefantasy.jp', 'Connection':'keep-alive'}, add_user_agent=True, allow_redirects=True)
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
        v = await self.gbf_version()
        if v is None: v = await self.gbf_version() # try again in case their shitty server is lagging
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