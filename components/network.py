from __future__ import annotations
from typing import Generator, Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.util import JSON
    # Type Aliases
    type RequestResult = JSON|bytes|None # cover None, JSON types, bytes
    type GBFAccount = JSON
from enum import IntEnum
from contextlib import asynccontextmanager
import aiohttp
import re
from datetime import datetime, timedelta
from deep_translator import GoogleTranslator

# ----------------------------------------------------------------------
# Network Component
# ----------------------------------------------------------------------
# This component is the interface with Granblue Fantasy (account wise) and other websites
# ----------------------------------------------------------------------


class Network():
    VERSION_REGEX : list[re.Pattern] = [ # possible regex to detect the GBF game version
        re.compile("\"version\": \"(\\d+)\""), # new one
        re.compile("\\/assets\\/(\\d+)\\/"), # alternative/fallback
        re.compile("Game\\.version = \"(\\d+)\";") # old one
    ]

    class Method(IntEnum):
        GET : int = 0
        POST : int = 1
        HEAD : int = 2

    class AccountStatus(IntEnum):
        UNSET : int = -1
        UNDEF : int = 0
        OK : int = 1
        DOWN : int = 2

    # Default user agent
    DEFAULT_UA : str = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        "AppleWebKit/537.36 (KHTML, like Gecko)"
        "Chrome/131.0.0.0 Safari/537.36"
    )

    def __init__(self : Network, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        # default user agent
        # we add Rosetta name and version for websites which might have bot exceptions for it
        self.user_agent : str = self.DEFAULT_UA + ' Rosetta/' + self.bot.VERSION
        self.translator : GoogleTranslator = GoogleTranslator(source='auto', target='en') # translator instance
        self.client : aiohttp.ClientSession|None = None
        self.client_req : dict[int, Callable] = {}
        self.gbf_client : aiohttp.ClientSession|None = None
        self.gbf_client_req : dict[int, Callable] = {}

    def init(self : Network) -> None:
        pass

    """update_user_agent()
    Automatically update the default Chrome user agent used by Rosetta
    """
    async def update_user_agent(self : Network) -> None:
        try:
            # access this list of user agents
            response : aiohttp.HTTPResponse = await self.client.get(
                "https://jnrbsn.github.io/user-agents/user-agents.json"
            )
            async with response:
                if 200 <= response.status < 400:
                    ua : str
                    for ua in await response.json(): # look for the latest chrome one...
                        if "Windows" in ua and "Chrome" in ua:
                            self.user_agent = ua + ' Rosetta/' + self.bot.VERSION # and update our user agent
                            self.bot.logger.push(
                                "[NET] Default user-agent set to `{}`".format(self.user_agent),
                                send_to_discord=False
                            )
                            return
            raise Exception("Missing data")
        except Exception as e:
            self.bot.logger.pushError(
                (
                    "[NET] Couldn't retrieve the latest Chrome user-agent from"
                    "`https://jnrbsn.github.io/user-agents/user-agents.json`.\n"
                    "It has been set to `{}` in the meantime."
                ).format(self.user_agent),
                e
            )

    """init_clients()
    Context manager for the aiohttp clients, to ensure it will be closed upon exit. Used in bot.py
    """
    @asynccontextmanager
    async def init_clients(self : Network) -> Generator[
        tuple[aiohttp.ClientSession, aiohttp.ClientSession],
        None,
        None
    ]:
        try:
            # The TCPConnector is shared/common to both clients
            conn : aiohttp.TCPConnector = aiohttp.TCPConnector(keepalive_timeout=60, ttl_dns_cache=600)
            # set generic client and methods
            self.client = aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=20))
            self.client_req[self.Method.GET] = self.client.get
            self.client_req[self.Method.POST] = self.client.post
            self.client_req[self.Method.HEAD] = self.client.head
            # set gbf client and methods
            self.gbf_client = aiohttp.ClientSession(connector=conn, timeout=aiohttp.ClientTimeout(total=20))
            self.gbf_client_req[self.Method.GET] = self.gbf_client.get
            self.gbf_client_req[self.Method.POST] = self.gbf_client.post
            self.gbf_client_req[self.Method.HEAD] = self.gbf_client.head
            # update the default user agent
            await self.update_user_agent()
            yield (self.client, self.gbf_client)
        finally: # close the clients properly
            await self.client.close()
            await self.gbf_client.close()

    """unknown_req
    Do nothing. Used for error handling

    Raises
    ----------
    Exception
    """
    async def unknown_req(self : Network, *args, **kwargs) -> None:
        raise Exception("Unknown request type")

    """request()
    Coroutine to request a network resource.
    Use requestGBF to request GBF with an account, or requestWiki to request the Wiki

    Parameters
    ----------
    url: Url to request from.
    rtype: Integer (Default is 0 or GET). Set the request type when payload is None.
        Use the constant GET, POST, HEAD defined in this class.
    headers: Dict, request headers set by the user.
        Prefer using add_user_agent instead of setting the user agent yourself.
    params: Dict, set to None to ignore.
    payload: Dict (Default is None), POST request payload.
        Set to None to do another request type.
    allow_redirects: Boolean (Default is False), set to True to follow request redirections if you expect any.
    expect_JSON: Boolean (Default is False), set to True if you expect to receive a JSON and
        the function will return an error if it's not one.
    ssl: Boolean (Default is True), set to False to disable ssl verifications

    Returns
    ----------
    unknown: None if error, else Bytes or JSON object for GET/POST, headers for HEAD
    """
    async def request(
        self : Network,
        url : str,
        *,
        rtype : int = 0,
        headers : dict = {},
        params : dict|None = None,
        payload : dict|None = None,
        add_user_agent : bool = False,
        allow_redirects : bool = False,
        expect_JSON : bool = False,
        ssl : bool = True
    ) -> RequestResult:
        try:
            headers['Connection'] = 'keep-alive'
            # Add user agent
            if add_user_agent and 'User-Agent' not in headers:
                headers['User-Agent'] = self.user_agent
            response : aiohttp.HTTPResponse
            if payload is None: # call request method with given parameters
                response = await (self.client_req.get(rtype, self.unknown_req))(
                    url,
                    params=params,
                    headers=headers,
                    allow_redirects=allow_redirects,
                    ssl=ssl
                )
            else: # the request is always POST if we have a payload
                rtype = self.Method.POST
                response = await self.client.post(
                    url,
                    params=params,
                    headers=headers,
                    json=payload,
                    allow_redirects=allow_redirects,
                    ssl=ssl
                )
            async with response:
                # raise Exception if our HTTP code isn't in the 200-399 range
                if response.status >= 400 or response.status < 200:
                    raise Exception()
                ct : str = response.headers.get('content-type', '')
                is_json : bool = 'application/json' in ct
                # raise error if we expected a json and it's not
                if expect_JSON and not is_json:
                    raise Exception("Expected `application/json`, got `{}`".format(ct))
                if rtype == self.Method.HEAD: # HEAD request, we simply return True to signify it's successful
                    return True
                elif is_json: # JSON, we return it as a JSON object
                    return await response.json()
                elif response.status == 204:
                    return True
                else: # else, binary
                    return await response.read()
        except Exception as e:
            if str(e) != "":
                self.bot.logger.pushError("[NET] request `{}` Error:".format(url), e) # log unexpected errors
            return None

    """requestGBF()
    Coroutine to request Granblue Fantasy with a working account.

    Parameters
    ----------
    path: Url path.
    rtype: Integer (Default is 0 or GET). Set the request type when payload is None.
        Use the constant GET, POST, HEAD defined in this class.
    params: Dict. Automatically set when requesting GBF.
    payload: Dict (Default is None), POST request payload. Set to None to do another request type.
        Additionaly, the 'user_id' value can be automatically set if it's equal to the following:
        - "ID": The GBF Profile ID
        - "SID": The GBF Profile ID, as a string
        - "IID": The GBF Profile ID, as an integer
    allow_redirects: Bool, set to True to follow redirects.
    expect_JSON: Boolean (Default is False), set to True if you expect to receive a JSON
        and the function will return an error if it's not one.
    _updated_: Boolean, for internal use only.

    Returns
    ----------
    unknown: None if error, else Bytes or JSON object for GET/POST, headers for HEAD
    """
    async def requestGBF(
        self : Network,
        path : str,
        *,
        rtype : int = 0,
        params : dict = {},
        payload : dict|None = None,
        allow_redirects : bool = False,
        expect_JSON : bool = False,
        _updated_ : bool = False
    ) -> RequestResult:
        try:
            silent : bool = True
            # don't proceed if the game is down
            if await self.gbf_maintenance():
                return None
            # build the URL
            url : str
            if path[:1] != "/":
                url = "https://game.granbluefantasy.jp/" + path
            else:
                url = "https://game.granbluefantasy.jp" + path
            # check and retrieve the account info
            if not self.has_account():
                raise Exception("No GBF account set")
            acc : GBFAccount = self.get_account()
            # if account is down, we silence errors
            silent : bool = (acc['state'] == self.AccountStatus.DOWN)
            # retrieve the game version
            ver : JSON = self.bot.data.save['gbfversion']
            if ver == "Maintenance":
                # Note: I don't think the version should ever be equal to "Maintenance"
                # but I'm keeping this  check for safety
                raise Exception("Maintenance on going")
            elif ver is None:
                # If not set, we proceed with a version of 0.
                # Other mechanisms will take care of the rest
                ver = 0
            # prepare and set headers
            headers : dict[str, str] = {
                'Connection':'keep-alive',
                'Accept-Encoding':'gzip, deflate',
                'Accept-Language':'en',
                'Host':'game.granbluefantasy.jp',
                'Origin':'https://game.granbluefantasy.jp',
                'Referer':'https://game.granbluefantasy.jp/',
                'User-Agent':acc['ua'],
                'X-Requested-With':'XMLHttpRequest',
                'X-VERSION':str(ver)
            }
            # set cookies
            # Note: To ensure the cookie doesn't expire, we have to clear and reset the jar manually
            # We use a separe client for that purpose
            # Clearing just the GBF cookies on a the main client would burn way too much CPU, especially during GW
            self.gbf_client.cookie_jar.clear()
            self.gbf_client.cookie_jar.update_cookies(acc['ck'])
            # set request params
            ts : int = int(self.bot.util.UTC().timestamp() * 1000)
            params["_"] = str(ts)
            params["t"] = str(ts + 300) # second timestamp is always a bit further.
            # Note for above: No idea if a random number would be better
            params["uid"] = str(acc['id'])
            response : aiohttp.HTTPResponse
            if payload is None: # call request method with given parameters
                response = await (self.gbf_client_req.get(rtype, self.unknown_req))(
                    url,
                    params=params,
                    headers=headers,
                    allow_redirects=allow_redirects
                )
            else: # if we have a payload, it's always a POST request
                rtype = self.Method.POST
                # auto set 'user_id' in the payload according to its value
                if 'user_id' in payload:
                    match payload['user_id']:
                        case "ID": payload['user_id'] = acc['id']
                        case "SID": payload['user_id'] = str(acc['id'])
                        case "IID": payload['user_id'] = int(acc['id'])
                # do the request
                response = await self.gbf_client.post(
                    url,
                    params=params,
                    headers=headers,
                    json=payload,
                    allow_redirects=allow_redirects
                )
            # response handling
            async with response:
                # error if our HTTP code isn't in the 200-399 range
                if response.status >= 400 or response.status < 200:
                    # if _updated_ isn't raised, it MIGHT be due to an invalid version (in case an update happened)
                    if not _updated_:
                        x : int|str|None = await self.gbf_version() # in that case, we check for an update
                        if x is not None and not isinstance(x, str) and x >= 2:
                            # x = 2: our version number in memory wasn't set
                            # x = 3: an update occured
                            if x == 3:
                                _updated_ = True # raise updated flag because an update occured
                            # we try this request again
                            return await self.requestGBF(
                                path,
                                rtype,
                                params,
                                payload,
                                allow_redirects,
                                expect_JSON,
                                _updated_
                            )
                    # else, raise exception
                    raise Exception()
                # check content type
                ct : str = response.headers.get('content-type', '')
                is_json : bool = 'application/json' in ct
                if expect_JSON and not is_json: # we expected a json but we didn't receive one
                    self.set_account_state(self.AccountStatus.DOWN) # the account is likely down
                    return None
                # retrieve cookies
                if 'set-cookie' in response.headers:
                    self.set_account_cookie(response.headers['set-cookie']) # and update our copy
                # result
                if rtype == self.Method.HEAD: # HEAD request returns True to signify success
                    return True
                elif is_json: # JSON, we return the json object
                    return await response.json()
                elif response.status == 204:
                    return True
                else: # else the binary
                    return await response.read()
        except Exception as e:
            if str(e) != "":
                self.bot.logger.pushError(
                    "[NET] requestGBF `{}` Error:".format(path),
                    e,
                    send_to_discord=(not silent)
                )
            return None

    """requestGBF_offline()
    Coroutine to request Granblue Fantasy without a working account.
    Only work for some limited content.
    Note: Might require to set the cookie ln: 2 first,
        for the english language and to request the main page with request() first to set other cookies.
    Note²: It uses client, not gbf_client and is a lightweight copy paste of request()

    Parameters
    ----------
    path: Url path.
    rtype: Integer (Default is 0 or GET). Set the request type when payload is None.
        Use the constant GET, POST, HEAD defined in this class.
    params: Dict. Automatically set when requesting GBF.
    payload: Dict (Default is None), POST request payload. Set to None to do another request type.
    allow_redirects: Bool, set to True to follow redirects.
    expect_JSON: Boolean (Default is False), set to True if you expect to receive a JSON and
        the function will return an error if it's not one.
    _updated_: Boolean, for internal use only.

    Returns
    ----------
    unknown: None if error, else Bytes or JSON object for GET/POST, headers for HEAD
    """
    async def requestGBF_offline(
        self : Network,
        path : str,
        *,
        rtype : int = 0,
        params : dict = {},
        payload : dict|None = None,
        allow_redirects : bool = False,
        expect_JSON : bool = False,
        _updated_ : bool = False
    ) -> RequestResult:
        try:
            silent : bool = True
            # don't proceed if the game is down
            if await self.gbf_maintenance():
                return None
            # build the URL
            url : str
            if path[:1] != "/":
                url = "https://game.granbluefantasy.jp/" + path
            else:
                url = "https://game.granbluefantasy.jp" + path
            # check and retrieve the account info
            if not self.has_account():
                raise Exception("No GBF account set")
            # retrieve the game version
            ver : JSON = self.bot.data.save['gbfversion']
            if ver == "Maintenance":
                # Note: I don't think the version should ever be equal to "Maintenance"
                # but I'm keeping this check for safety
                raise Exception("Maintenance on going")
            elif ver is None:
                # If not set, we proceed with a version of 0.
                # Other mechanisms will take care of the rest
                ver = 0
            # prepare and set headers
            headers : dict[str, str] = {
                'Connection':'keep-alive',
                'Accept-Encoding':'gzip, deflate',
                'Accept-Language':'en',
                'Host':'game.granbluefantasy.jp',
                'Origin':'https://game.granbluefantasy.jp',
                'Referer':'https://game.granbluefantasy.jp/',
                'User-Agent':self.user_agent,
                'X-Requested-With':'XMLHttpRequest',
                'X-VERSION':str(ver)
            }
            # set request params
            ts : int = int(self.bot.util.UTC().timestamp() * 1000)
            params["_"] = str(ts)
            params["t"] = str(ts + 300) # second timestamp is always a bit further.
            # Note for above: No idea if a random number would be better
            params["uid"] = str(0)
            response : aiohttp.HTTPResponse
            if payload is None: # call request method with given parameters
                response = await (self.client_req.get(rtype, self.unknown_req))(
                    url,
                    params=params,
                    headers=headers,
                    allow_redirects=allow_redirects
                )
            else: # if we have a payload, it's always a POST request
                rtype = self.Method.POST
                # auto set 'user_id' in the payload according to its value
                if 'user_id' in payload:
                    match payload['user_id']:
                        case "ID": payload['user_id'] = 0
                        case "SID": payload['user_id'] = str(0)
                        case "IID": payload['user_id'] = int(0)
                # do the request
                response = await self.client.post(
                    url,
                    params=params,
                    headers=headers,
                    json=payload,
                    allow_redirects=allow_redirects
                )
            # response handling
            async with response:
                # error if our HTTP code isn't in the 200-399 range
                if response.status >= 400 or response.status < 200:
                    if not _updated_:
                        # if _updated_ isn't raised, it MIGHT be due to an invalid version (in case an update happened)
                        x : int|str|None = await self.gbf_version() # in that case, we check for an update
                        if x is not None and not isinstance(x, str) and x >= 2:
                            # x = 2: our version number in memory wasn't set
                            # x = 3: an update occured
                            if x == 3:
                                _updated_ = True # raise updated flag because an update occured
                            # we try this request again
                            return await self.requestGBF_offline(
                                path,
                                rtype,
                                params,
                                payload,
                                allow_redirects,
                                expect_JSON,
                                _updated_
                            )
                    # else, raise exception
                    raise Exception()
                # check content type
                ct : str = response.headers.get('content-type', '')
                is_json : bool = 'application/json' in ct
                if expect_JSON and not is_json: # we expected a json but we didn't receive one
                    return None
                # result
                if rtype == self.Method.HEAD: # HEAD request returns True to signify success
                    return True
                elif is_json: # JSON, we return the json object
                    return await response.json()
                elif response.status == 204:
                    return True
                else: # else the binary
                    return await response.read()
        except Exception as e:
            if str(e) != "":
                self.bot.logger.pushError(
                    "[NET] requestGBF_offline `{}` Error:".format(path),
                    e,
                    send_to_discord=(not silent)
                )
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
    async def requestWiki(
        self : Network,
        path : str,
        params : dict = {},
        allow_redirects : bool = False
    ) -> RequestResult:
        try:
            # build the URL
            url : str
            if path[:1] != "/":
                url = "https://gbf.wiki/" + path
            else:
                url = "https://gbf.wiki" + path
            # make the GET request with given parameters
            response : aiohttp.HTTPResponse = await self.client.get(
                url,
                headers={
                    'Connection':'keep-alive',
                    'User-Agent':self.user_agent,
                    "Accept":"text/html,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                    "Accept-Encoding":"gzip, deflate",
                    "Accept-Language":"en-US,en;q=0.9",
                    'Host':'gbf.wiki',
                    'Origin':'https://gbf.wiki',
                    "Referer":"https://gbf.wiki/"
                },
                params=params,
                timeout=8,
                allow_redirects=allow_redirects
            )
            async with response:
                if response.status == 403:
                    # if you get this error, contact the wiki admins to get your user-agent whitelisted
                    raise Exception("HTTP Error 403 - Possibly Cloudflare related")
                elif response.status >= 400 or response.status < 200: # valid error codes
                    raise Exception("HTTP Error " + str(response.status))
                # result
                if response.headers.get('content-type', '').startswith('application/json'): # JSON content
                    return await response.json()
                else: # binary content
                    return await response.read()
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
    def str2cookie(self : Network, header : str) -> dict[str, str]:
        cd : dict[str, str] = {}
        for c in header.split(";"): # split via ;
            ct : list[str] = c.split("=", 1) # then each element by =
            cd[ct[0].strip()] = ct[1].strip() # store each part as a pair in our dict
        # return the dict
        return cd

    """refresh_account()
    Refresh the GBF account cookie by making a request (only if not done recently)
    """
    async def refresh_account(self : Network) -> None:
        if self.has_account() and await self.gbf_available(skip_check=True): # check if the account exists
            state : int = self.bot.data.save['gbfaccount'].get('state', self.AccountStatus.UNSET)
            last : datetime|None = self.bot.data.save['gbfaccount'].get('last', None)
            # if it's down...
            if (state != self.AccountStatus.DOWN
                    and (last is None or self.bot.util.JST() - last >= timedelta(seconds=3600))):
                # attempt a request
                await self.bot.net.requestGBF("an/z/14", expect_JSON=True)
                if self.bot.data.save['gbfaccount'].get('state', self.AccountStatus.UNSET) == self.AccountStatus.DOWN:
                    self.bot.logger.push(
                        (
                            "[TASK] 'admin:status' refresh_account() failed.\n"
                            "The Account might be down (Try to set the cookie anew)."
                        ),
                        level=self.bot.logger.WARNING
                    )

    """has_account()
    Return if the GBF account is set
    Doesn't check if the account is down or not, only if it has been set

    Returns
    ----------
    bool: True if valid, False if not
    """
    def has_account(self : Network) -> bool:
        return (
            self.bot.data.save['gbfaccount'].get('state', self.AccountStatus.UNSET)
            != self.AccountStatus.UNSET
            and len(self.bot.data.save['gbfaccount'].get('ck', {})) > 0
            and self.bot.data.save['gbfaccount'].get('ua', "") != ""
        )

    """is_account_valid()
    Return True if the GBF account is usable.
    Like has_account() but perform an extra check.

    Returns
    ----------
    bool: True if usable, False if not
    """
    def is_account_valid(self : Network) -> bool:
        return (
            self.has_account()
            and self.bot.data.save['gbfaccount'].get('state', self.AccountStatus.UNSET)
            != self.AccountStatus.DOWN
        )

    """get_account()
    Return the GBF account data

    Returns
    ----------
    dict: Account data
    """
    def get_account(self : Network) -> GBFAccount:
        return self.bot.data.save['gbfaccount']

    """set_account()
    Set a GBF account

    Parameters
    ----------
    uid: Integer, profile ID
    ck: String, valid Cookie
    ua: String, User-Agent used to get the Cookie
    """
    def set_account(self : Network, uid : int, ck : str, ua : str):
        self.bot.data.save['gbfaccount'] = {
            "id":uid,
            "ck":self.str2cookie(ck),
            "ua":ua,
            "state":self.AccountStatus.UNDEF,
            "last":None
        }
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
    def edit_account(self : Network, **options : dict[str, int|str]) -> bool:
        try:
            uid : str|int|None = options.pop('uid', None)
            ck : str|None = options.pop('ck', None)
            ua : str|None = options.pop('ua', None)
            if uid is not None: # GBF user id
                self.bot.data.save['gbfaccount']['id'] = uid
                self.bot.data.pending = True
            if ck is not None: # GBF cookie
                self.bot.data.save['gbfaccount']['ck'] = self.str2cookie(ck)
                self.bot.data.pending = True
            if ua is not None: # user-agent used
                self.bot.data.save['gbfaccount']['ua'] = ua
                self.bot.data.pending = True
            return True
        except:
            return False

    """clear_account()
    Clear the GBF account data
    """
    def clear_account(self : Network) -> None:
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
    def set_account_cookie(self : Network, ck : str) -> bool:
        try:
            if ck is None:
                return False
            cookie : dict[str, str] = self.str2cookie(ck) # convert it to dict
            reference : dict[str, str] = self.bot.data.save['gbfaccount']['ck']
            self.bot.data.save['gbfaccount']['ck'] = reference | {
                k:v for k, v in cookie.items() if k in reference
            }
            # account has a new cookie so it should be considered ok
            self.bot.data.save['gbfaccount']['state'] = self.AccountStatus.OK
            # cookie just updated, updating the last timestamp
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
    def set_account_state(self : Network, state : int) -> None:
        try:
            if state != self.bot.data.save['gbfaccount'].get('state', self.AccountStatus.UNSET):
                self.bot.data.save['gbfaccount']['state'] = state
                self.bot.data.pending = True
        except:
            pass

    """gbf_version()
    Coroutine to retrieve the GBF version number. If success, call gbf_update() and return its result

    Returns
    ----------
    int or string: None if GBF is down,
        "Maintenance" if in maintenance,
        -1 if version comparison error,
        0 if equal,
        1 if v is None,
        2 if saved number is None,
        3 if different
    """
    async def gbf_version(self : Network) -> int|str|None: # retrieve the game version
        # simply request the main page
        response = await self.request(
            'https://game.granbluefantasy.jp/',
            headers={
                'Accept-Language':'en',
                'Accept-Encoding':'gzip, deflate',
                'Host':'game.granbluefantasy.jp',
                'Connection':'keep-alive'
            },
            add_user_agent=True,
            allow_redirects=True
        )
        if response is None: # main page is down, try again
            response = await self.request(
                'https://game.granbluefantasy.jp/',
                headers={
                    'Accept-Language':'en',
                    'Accept-Encoding':'gzip, deflate',
                    'Host':'game.granbluefantasy.jp',
                    'Connection':'keep-alive'
                },
                add_user_agent=True,
                allow_redirects=True
            )
        if response is None: # main page is down
            return None
        # convert page html to string
        res : str = str(response)
        i : int = 0
        # look for the version number.
        # it's always embedded in the html.
        # It recently changed, so we used multiple regexes to cover our tracks now.
        while i < len(self.VERSION_REGEX):
            try:
                # if the number if found, we call gbf_update and return its result
                return self.gbf_update(int(self.VERSION_REGEX[i].findall(res)[0]))
            except:
                if i == 0 and 'maintenance' in res.lower(): # if maintenance is in the page html
                    return "Maintenance"
                elif i == len(self.VERSION_REGEX) - 1: # if we tried all regexes, the version number hasn't been found
                    return None
            i += 1
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
    def gbf_update(self : Network, v : int|None) -> int:
        try:
            if v is None:
                return 1 # invalid parameter
            int(v) # double check the version number is a number
            if self.bot.data.save['gbfversion'] is None: # the version in memory is None
                self.bot.data.save['gbfversion'] = v # this number replaces it
                self.bot.data.save['gbfupdate'] = False
                self.savePending = True
                return 2 # version has been set
            elif self.bot.data.save['gbfversion'] != v: # this number is DIFFERENT from the one in memory
                self.bot.data.save['gbfversion'] = v # this number replaces it
                self.bot.data.save['gbfupdate'] = True
                self.bot.data.pending = True
                return 3 # an update has occured
            return 0 # unchanged  version number
        except:
            return -1 # v isn't an integer

    """gbf_available()
    Coroutine to retrieve the GBF version to check if the game is available.
    Use gbf_version() to check if the game is available by looking for the version number.

    Parameters
    ----------
    skip_check: Boolean, skip the maintenance check (for internal use only)

    Returns
    ----------
    Boolean: True if the game is available, False otherwise.
    """
    async def gbf_available(self : Network, skip_check : bool = False) -> bool:
        # if skip_check isn't raised an the game is in maintenance, we return False
        if skip_check is False and await self.gbf_maintenance():
            return False
        v : int|str|None = await self.gbf_version() # get version number
        if v is None: # if None, try again in case it was a server lag
            v = await self.gbf_version()
        match v: # check result
            case None: # Server is down
                return False
            case 'Maintenance': # Server is in maintenance
                # If no maintenance is set in memory, put the bot in emergency maintenance mode
                if (self.bot.data.save['maintenance']['state'] is False
                        or (self.bot.data.save['maintenance']['state'] is True
                            and self.bot.data.save['maintenance']['duration'] > 0
                            and self.bot.util.JST() > self.bot.data.save['maintenance']['time']
                            + timedelta(seconds=3600 * self.bot.data.save['maintenance']['duration']))):
                    self.bot.data.save['maintenance'] = {"state" : True, "time" : None, "duration" : 0}
                    self.bot.data.pending = True
                    self.bot.logger.push("[GBF] Possible emergency maintenance detected")
                return False
            case _: # Server is up
                return True

    """gbf_maintenance_status()
    Check if GBF is in maintenance and return a string.
    Save data is updated if it doesn't match the current state.

    Parameters
    ----------
    check_maintenance_end: Boolean, check if emergency maintenance ended (for internal use only)

    Returns
    --------
    tuple: Containing the Status string and the Status flag (True if on going, False if not)
    """
    async def gbf_maintenance_status(self : Network, check_maintenance_end : bool = False) -> str:
        current_time : datetime = self.bot.util.JST()
        d : timedelta
        # Check GBF maintenance data in memory
        if self.bot.data.save['maintenance']['state'] is True: # there is data
            if (self.bot.data.save['maintenance']['time'] is not None
                    and current_time < self.bot.data.save['maintenance']['time']): # Maintenance hasn't started
                if self.bot.data.save['maintenance']['duration'] == 0:
                    return "Maintenance at **{}**".format(
                        self.bot.util.time(
                            self.bot.data.save['maintenance']['time'],
                            style=['d','t'],
                            removejst=True
                        )
                    ), False
                else:
                    d = self.bot.data.save['maintenance']['time'] - current_time
                    return "Maintenance starts in **{}**, for **{} hour{}**, from **{}** to **{}**".format(
                        self.bot.util.delta2str(d, 2),
                        self.bot.data.save['maintenance']['duration'],
                        ("s" if self.bot.data.save['maintenance']['duration'] > 1 else ""),
                        self.bot.util.time(
                            self.bot.data.save['maintenance']['time'],
                            style=['d','t'],
                            removejst=True
                        ),
                        self.bot.util.time(
                            self.bot.data.save['maintenance']['time'] + timedelta(seconds=3600*self.bot.data.save['maintenance']['duration']),
                            style=['d','t'],
                            removejst=True
                        )
                    ), False
            else:
                if self.bot.data.save['maintenance']['duration'] <= 0: # No duration, emergency maintenance
                    # use gbf_available with skip_check=True to check if it ended
                    if (not check_maintenance_end
                            or (check_maintenance_end
                                and not await self.gbf_available(skip_check=True))):
                        return "{} Emergency maintenance on going".format(self.bot.emote.get('cog')), True
                    else: # no maintenance
                        self.bot.data.save['maintenance'] = {"state":False, "time":None, "duration":0}
                        self.bot.data.pending = True
                        return "", False
                else: # has duration
                    d = current_time - self.bot.data.save['maintenance']['time']
                    if (d.seconds // 3600) >= self.bot.data.save['maintenance']['duration']: # check if it ended
                        # clear data then
                        self.bot.data.save['maintenance'] = {"state":False, "time":None, "duration":0}
                        self.bot.data.pending = True
                        return "", False
                    else:
                        e : datetime = (
                            self.bot.data.save['maintenance']['time']
                            + timedelta(seconds=3600 * self.bot.data.save['maintenance']['duration'])
                        )
                        d = e - current_time
                        return "Maintenance ends in **{}**, at **{}**".format(
                            self.bot.util.delta2str(d, 2),
                            self.bot.util.time(
                                self.bot.data.save['maintenance']['time'] + timedelta(seconds=3600*self.bot.data.save['maintenance']['duration']),
                                style=['d','t'],
                                removejst=True
                            )
                        ), True
        return "", False

    """gbf_maintenance()
    Return True if a scheduled or emergency ùaintenance is on going
    Use gbf_maintenance_status()

    Parameters
    ----------
    check_maintenance_end: Boolean, check if emergency maintenance ended (for internal use only)

    Returns
    --------
    bool: True if on going, False otherwise
    """
    async def gbf_maintenance(self : Network, check_maintenance_end : bool = False) -> bool:
        return (await self.gbf_maintenance_status(check_maintenance_end=check_maintenance_end))[1]

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
    def translate(self : Network, original_text : str) -> str:
        if original_text == "": # ignore empty strings
            return original_text
        return self.translator.translate(original_text)
