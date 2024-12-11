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
    VERSION_REGEX = [ # possible regex to detect the game version
        re.compile("\"version\": \"(\d+)\""), # new one
        re.compile("\\/assets\\/(\d+)\\/"), # alternative/fallback
        re.compile("Game\.version = \"(\d+)\";") # old one
    ]
    GET = 0
    POST = 1
    HEAD = 2
    CONDITIONAL_GET = 4
    ACC_STATUS_UNSET = -1
    ACC_STATUS_UNDEF = 0
    ACC_STATUS_OK = 1
    ACC_STATUS_DOWN = 2
    DEFAULT_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.user_agent = self.DEFAULT_UA + ' Rosetta/' + self.bot.VERSION
        self.translator = GoogleTranslator(source='auto', target='en')
        self.client = None
        self.client_req = {}
        self.gbf_client = None
        self.gbf_client_req = {}

    def init(self) -> None:
        pass

    """update_user_agent()
    Automatically update the default Chrome user agent used by Rosetta
    """
    async def update_user_agent(self) -> None:
        try:
            response = await self.client.get("https://jnrbsn.github.io/user-agents/user-agents.json")
            async with response:
                if 200 <= response.status < 400:
                    for ua in await response.json():
                        if "Windows" in ua and "Chrome" in ua:
                            self.user_agent = ua + ' Rosetta/' + self.bot.VERSION
                            self.bot.logger.push("[NET] Default user-agent set to `{}`".format(self.user_agent), send_to_discord=False)
                            return
            raise Exception("Missing data")
        except Exception as e:
            self.bot.logger.pushError("[NET] Couldn't retrieve the latest Chrome user-agent from `https://jnrbsn.github.io/user-agents/user-agents.json`.\nIt has been set to `{}` in the meantime.".format(self.user_agent), e)

    """init_clients()
    Context manager for the aiohttp clients, to ensure it will be closed upon exit. Used in bot.py
    """
    @asynccontextmanager
    async def init_clients(self) -> Generator[tuple, None, None]:
        try:
            conn = aiohttp.TCPConnector(keepalive_timeout=60, ttl_dns_cache=600)
            # set generic client
            self.client = aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=20))
            self.client_req[self.GET] = self.client.get
            self.client_req[self.POST] = self.client.post
            self.client_req[self.HEAD] = self.client.head
            self.client_req[self.CONDITIONAL_GET] = self.client.get
            # set gbf client
            self.gbf_client = aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=20))
            self.gbf_client_req[self.GET] = self.gbf_client.get
            self.gbf_client_req[self.POST] = self.gbf_client.post
            self.gbf_client_req[self.HEAD] = self.gbf_client.head
            self.gbf_client_req[self.CONDITIONAL_GET] = self.gbf_client.get
            # update user agent
            await self.update_user_agent()
            yield (self.client, self.gbf_client)
        finally:
            await self.client.close()
            await self.gbf_client.close()


    """unknown_req
    Do nothing. Used for error handling
    
    Raises
    ----------
    Exception
    """
    async def unknown_req(*args, **kwargs) -> None:
        raise Exception("Unknown request type")

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
                response = await (self.client_req.get(rtype, self.unknown_req))(url, params=params, headers=headers, allow_redirects=allow_redirects, ssl=ssl)
            else:
                rtype = self.POST
                response = await self.client.post(url, params=params, headers=headers, json=payload, allow_redirects=allow_redirects, ssl=ssl)
            if rtype == self.CONDITIONAL_GET:
                return response
            async with response:
                if response.status >= 400 or response.status < 200:
                    raise Exception()
                if collect_headers is not None and collect_headers == [[None]]:
                    try: collect_headers[0] = response.headers
                    except: pass
                ct = response.headers.get('content-type', '')
                is_json = 'application/json' in ct
                if expect_JSON and not is_json: raise Exception("Expected `application/json`, got `{}`".format(ct))
                if rtype == self.HEAD: return True
                elif is_json: return await response.json()
                else: return await response.read()
        except Exception as e:
            if str(e) != "":
                self.bot.logger.pushError("[NET] request `{}` Error:".format(url), e)
            return None

    """requestGBF()
    Coroutine to request Granblue Fantasy with a working account.
    
    Parameters
    ----------
    path: Url path.
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
    async def requestGBF(self, path : str, *, rtype : int = 0, params : dict = {}, payload : Optional[dict] = None, allow_redirects : bool = False, expect_JSON : bool = False, _updated_ : bool = False) -> Any:
        try:
            silent = True
            if await self.gbf_maintenance(): return None
            if path[:1] != "/": url = "https://game.granbluefantasy.jp/" + path
            else: url = "https://game.granbluefantasy.jp" + path
            # retrieve account info
            if not self.has_account(): raise Exception("No GBF account set")
            acc = self.get_account()
            silent = (acc['state'] == self.ACC_STATUS_DOWN)
            # retrieve version
            ver = self.bot.data.save['gbfversion']
            if ver == "Maintenance":
                raise Exception("Maintenance on going")
            elif ver is None:
                ver = 0
            # set headers
            headers = {'Connection':'keep-alive', 'Accept-Encoding': 'gzip, deflate', 'Accept-Language': 'en', 'Host': 'game.granbluefantasy.jp', 'Origin': 'https://game.granbluefantasy.jp', 'Referer': 'https://game.granbluefantasy.jp/', 'User-Agent':acc['ua'], 'X-Requested-With':'XMLHttpRequest', 'X-VERSION':str(ver)}
            # set cookies
            self.gbf_client.cookie_jar.clear()
            self.gbf_client.cookie_jar.update_cookies(acc['ck'])
            # set params
            ts = int(self.bot.util.UTC().timestamp() * 1000)
            params["_"] = str(ts)
            params["t"] = str(ts+300)
            params["uid"] = str(acc['id'])
            if payload is None:
                response = await (self.gbf_client_req.get(rtype, self.unknown_req))(url, params=params, headers=headers, allow_redirects=allow_redirects)
            else:
                rtype = self.POST
                # auto set ID
                if 'user_id' in payload:
                    match payload['user_id']:
                        case "ID": payload['user_id'] = acc['id']
                        case "SID": payload['user_id'] = str(acc['id'])
                        case "IID": payload['user_id'] = int(acc['id'])
                response = await self.gbf_client.post(url, params=params, headers=headers, json=payload, allow_redirects=allow_redirects)
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
                            return await self.requestGBF(path, rtype, params, payload, allow_redirects, expect_JSON, _updated_)
                    raise Exception()
                ct = response.headers.get('content-type', '')
                is_json = 'application/json' in ct
                if expect_JSON and not is_json:
                    self.set_account_state(self.ACC_STATUS_DOWN)
                    return None
                if 'set-cookie' in response.headers:
                    self.set_account_cookie(response.headers['set-cookie'])
                if rtype == self.HEAD: return True
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
    params: Dict. Request parameters.
    allow_redirects: Bool, set to True to follow redirects.
    
    Returns
    ----------
    unknown: None if error, else Bytes or JSON object
    """
    async def requestWiki(self, path : str, params : dict = {}, allow_redirects : bool = False) -> Any:
        try:
            if path[:1] != "/": url = "https://gbf.wiki/" + path
            else: url = "https://gbf.wiki" + path
            response = await self.client.get(url, headers= {'Connection':'keep-alive', 'User-Agent':self.user_agent, "Accept":"text/html,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7", "Accept-Encoding":"gzip, deflate", "Accept-Language":"en-US,en;q=0.9", 'Host':'gbf.wiki', 'Origin':'https://gbf.wiki', "Referer":"https://gbf.wiki/"}, params=params, timeout=8, allow_redirects=allow_redirects)
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
            ct = c.split("=", 1)
            cd[ct[0].strip()] = ct[1].strip()
        return cd

    """refresh_account()
    Refresh the GBF account cookie by making a request (only if not done recently)
    """
    async def refresh_account(self) -> None:
        if self.has_account():
            state = self.bot.data.save['gbfaccount'].get('state', self.ACC_STATUS_UNSET)
            last = self.bot.data.save['gbfaccount'].get('last', None)
            if state != self.ACC_STATUS_DOWN and (last is None or self.bot.util.JST() - last >= timedelta(seconds=1800)):
                await self.bot.net.requestGBF("user/user_id/1", expect_JSON=True)

    """has_account()
    Return if the GBF account is set
    Doesn't check if the account is down or not, only if it has been set
    
    Returns
    ----------
    bool: True if valid, False if not
    """
    def has_account(self) -> bool:
        return self.bot.data.save['gbfaccount'].get('state', self.ACC_STATUS_UNSET) != self.ACC_STATUS_UNSET and len(self.bot.data.save['gbfaccount'].get('ck', {})) > 0 and self.bot.data.save['gbfaccount'].get('ua', "") != ""

    """is_account_valid()
    Return True if the GBF account is usable.
    Like has_account() but perform an extra check.
    
    Returns
    ----------
    bool: True if usable, False if not
    """
    def is_account_valid(self) -> bool:
        return self.has_account() and self.bot.data.save['gbfaccount'].get('state', self.ACC_STATUS_UNSET) != self.ACC_STATUS_DOWN

    """get_account()
    Return the GBF account data
    
    Returns
    ----------
    dict: Account data
    """
    def get_account(self) -> dict:
        return self.bot.data.save['gbfaccount']

    """set_account()
    Set a GBF account
    
    Parameters
    ----------
    uid: Integer, profile ID
    ck: String, valid Cookie
    ua: String, User-Agent used to get the Cookie
    """
    def set_account(self, uid : int, ck : str, ua : str):
        self.bot.data.save['gbfaccount'] = {"id":uid, "ck":self.str2cookie(ck), "ua":ua, "state":self.ACC_STATUS_UNDEF, "last":None}
        self.bot.data.pending = True

    """edit_account()
    Edit an account value
    
    Parameters
    ----------
    uid: Integer (Optional), profile ID
    ck: String (Optional), valid Cookie
    ua: String (Optional), User-Agent used to get the Cookie
    
    Returns
    ----------
    Boolean: True if success, False if error
    """
    def edit_account(self, **options : dict) -> bool:
        try:
            uid = options.pop('uid', None)
            ck = options.pop('ck', None)
            ua = options.pop('ua', None)
            if uid is not None:
                self.bot.data.save['gbfaccount']['id'] = uid
                self.bot.data.pending = True
            if ck is not None:
                self.bot.data.save['gbfaccount']['ck'] = self.str2cookie(ck)
                self.bot.data.pending = True
            if ua is not None:
                self.bot.data.save['gbfaccount']['ua'] = ua
                self.bot.data.pending = True
            return True
        except:
            return False

    """clear_account()
    Clear the GBF account data
    """
    def clear_account(self) -> None:
        self.bot.data.save['gbfaccount'] = {}
        self.bot.data.pending = True

    """set_account_cookie()
    Update a registered account cookie. For internal use only.
    
    Parameters
    ----------
    ck: String, new Cookie
    
    Returns
    ----------
    Boolean: True if success, False if error
    """
    def set_account_cookie(self, ck : str) -> bool:
        try:
            if ck is None: return False
            A = self.bot.data.save['gbfaccount']['ck']
            B = self.str2cookie(ck)
            self.bot.data.save['gbfaccount']['ck'] = A | {k:v for k, v in B.items() if k in A}
            self.bot.data.save['gbfaccount']['state'] = self.ACC_STATUS_OK
            self.bot.data.save['gbfaccount']['last'] = self.bot.util.JST()
            self.bot.data.pending = True
            return True
        except Exception as e:
            self.bot.logger.pushError("[ACCOUNT] 'set_account_cookie' error:", e)
            return False

    """set_account_state()
    Change a GBF account status. For internal use only.
    
    Parameters
    ----------
    state: Integer, 0 for undefined, 1 for good, 2 for bad
    """
    def set_account_state(self, state : int) -> None:
        try:
            if state != self.bot.data.save['gbfaccount'].get('state', self.ACC_STATUS_UNSET):
                self.bot.data.save['gbfaccount']['state'] = state
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
        i = 0
        while i < len(self.VERSION_REGEX):
            try:
                return self.gbf_update(int(self.VERSION_REGEX[i].findall(res)[0]))
            except:
                if i == 0 and 'maintenance' in res.lower():
                    return "Maintenance"
                elif i == len(self.VERSION_REGEX) - 1:
                    return None
            i += 1

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