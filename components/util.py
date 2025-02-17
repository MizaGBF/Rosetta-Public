from __future__ import annotations
import disnake
from datetime import datetime, timedelta, timezone
from typing import Any, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.network import RequestResult
    # Type Aliases
    type BotCommand = disnake.APISlashCommand|disnake.APIUserCommand|disnake.APIMessageCommand
    type BotCommandSearch = list[None|int|str]
    type JSON = datetime|int|float|str|list['JSON']|dict[str, 'JSON']|None
import psutil
import platform
import os
import sys
import html

# ----------------------------------------------------------------------------------------------------------------
# Utility Component
# ----------------------------------------------------------------------------------------------------------------
# Feature a lot of utility functions and classes
# ----------------------------------------------------------------------------------------------------------------

class Util():
    JSTDIFF : int = 32400 # JST <-> UTC difference in seconds
    MULTIPLIER_1000 : dict[str, int] = {'t':1000000000000, 'b':1000000000, 'm':1000000, 'k':1000} # thousand multipliers (Note: ORDER Is important)

    def __init__(self : Util, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.starttime : datetime = self.UTC() # used to check the bot uptime
        # bot process
        self.process : psutil.Process = psutil.Process(os.getpid())
        self.process.cpu_percent() # called once to initialize

    def init(self : Util) -> None:
        pass

    """json_deserial_array()
    Deserialize a list (used for our json files)
    
    Parameters
    ----------
    array: List
    
    Returns
    --------
    list: Deserialized list
    """
    def json_deserial_array(self : Util, array : list) -> list:
        a : list = []
        for v in array: # go over entries
            match v: # check type
                case list():
                    a.append(self.json_deserial_array(v))
                case dict():
                    a.append(self.json_deserial_dict(list(v.items())))
                case str():
                    try: # try to convert it to datetime
                        a.append(datetime.strptime(v, "%Y-%m-%dT%H:%M:%S"))
                    except ValueError:
                        a.append(v)
                case _:
                    a.append(v)
        return a

    """json_deserial_dict()
    Deserialize a dict (used for our json files)
    
    Parameters
    ----------
    pairs: dict
    
    Returns
    --------
    dict: Deserialized Dict
    """
    def json_deserial_dict(self : Util, pairs : dict) -> dict: # deserialize a dict from a json
        d : dict = {}
        for k, v in pairs: # go over entries
            match v: # check type
                case list():
                    d[k] = self.json_deserial_array(v)
                case dict():
                    d[k] = self.json_deserial_dict(list(v.items()))
                case str():
                    try: # try to convert it to datetime
                        d[k] = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S") # needed for datetimes
                    except ValueError:
                        d[k] = v
                case _:
                    d[k] = v
        return d

    """json_serial()
    Serialize a datetime instance (used for our json files)
    
    Parameters
    ----------
    obj: datetime instance
    
    Raises
    ------
    TypeError: obj isn't a datetime
    
    Returns
    --------
    unknown: Serialized object
    """
    def json_serial(self : Util, obj : Any) -> Any: # serialize everything including datetime objects
        if isinstance(obj, datetime): # convert datetimes to string isoformat
            return obj.replace(microsecond=0).isoformat()
        raise TypeError ("Type %s not serializable" % type(obj))

    """UTC()
    Return the current time, UTC timezone

    Returns
    --------
    datetime: Current time
    """
    def UTC(self : Util) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None) # we don't use timezone data to avoid headaches

    """JST()
    Return the current time, JST timezone

    Parameters
    --------
    delay: Boolean, shift the clock back by 30 seconds if True (to ensure proper synchro for some functions)

    Returns
    --------
    datetime: Current time
    """
    def JST(self : Util, delay : bool = True) -> datetime:
        # we apply a delay by default to be sure some functions are sure to get the content at certain time
        if delay:
            return self.UTC() + timedelta(seconds=self.JSTDIFF) - timedelta(seconds=30)
        else:
            return self.UTC() + timedelta(seconds=self.JSTDIFF)

    """time()
    Format a timestamp or datetime object

    Parameters
    --------
    to_convert: time to format
    style: format style, see https://discord.com/developers/docs/reference#message-formatting-timestamp-styles
           you can combine multiple styles together
    removejst: Bool, if True, remove 9h to the datetime
    naivecheck: Bool, if True, add UTC timezone to naive Datetime

    Returns
    --------
    str: Formatted time
    """
    def time(self : Util, to_convert : datetime|None = None, style : list[str] = ['f'], removejst : bool = False, naivecheck : bool = True) -> str:
        if to_convert is None: # if no datetime isn't passed, we get the current time, as UTC
            to_convert = self.UTC()
        msgs : list[str] = []
        if removejst: # remove JST time difference
            to_convert -= timedelta(seconds=self.JSTDIFF)
        # additional timezone checks
        if naivecheck and (to_convert.tzinfo is None or to_convert.tzinfo.utcoffset(to_convert)):
            to_convert = to_convert.replace(tzinfo=timezone.utc)
        # apply discord styles
        for c in style:
            msgs.append(disnake.utils.format_dt(to_convert, c))
        return " ".join(msgs)

    """uptime()
    Return the bot uptime
    
    Parameters
    ----------
    as_string: If true, the uptime is returned as a string
    
    Returns
    --------
    timedelta: Bot uptime
    """
    def uptime(self : Util, as_string : bool = True) -> str|timedelta: # get the uptime
        # get elapsed time between now and the start
        delta : timedelta = self.UTC() - self.starttime
        if as_string:
            return "{}".format(self.delta2str(delta, 3))
        else:
            return delta

    """delta2str()
    Convert a timedelta object to a string (format: XdXhXmXs)
    
    Parameters
    ----------
    delta: Timedelta object
    mode: Affect the formatting:
        1 (default): Hours and Minutes
        2: Days, Hours and Minutes
        3: Days, Hours, Minutes and Seconds
        Anything else: Minutes
    
    Returns
    --------
    str: Resulting string
    """
    def delta2str(self : Util, delta : timedelta, mode : int = 1) -> str:
        match mode: # convert a timedelta into a string. different modes possible:
            case 3:
                return "{}d{}h{}m{}s".format(delta.days, delta.seconds // 3600, (delta.seconds // 60) % 60, delta.seconds % 60)
            case 2:
                return "{}d{}h{}m".format(delta.days, delta.seconds // 3600, (delta.seconds // 60) % 60)
            case 1:
                return "{}h{}m".format(delta.seconds // 3600, (delta.seconds // 60) % 60)
            case _:
                return "{}m".format(delta.seconds // 60)

    """str2delta()
    Convert string to a a timedelta object (format: XdXhXmXs)
    
    Parameters
    ----------
    d: The string to convert
    
    Returns
    --------
    timedelta: Resulting timedelta object or None if error
    """
    def str2delta(self : Util, d : str) -> timedelta|None: # return None if error
        flags : dict[str, bool] = {'d':False,'h':False,'m':False,'s':False} # expected string parts
        tmp : int = 0 # buffer
        sum : int = 0 # delta in seconds
        c : str
        for c in d: # go character by character
            if c.isdigit(): # digit
                tmp = (tmp * 10) + int(c)
            elif c.lower() in flags: # one of the flags
                if flags[c.lower()]: # flag has already been used
                    return None
                if tmp < 0: # negative number in the buffer
                    return None
                flags[c.lower()] = True # raise flag
                match c: # add buffer value to total sum
                    case 'd': sum += tmp * 86400
                    case 'h': sum += tmp * 3600
                    case 'm': sum += tmp * 60
                    case 's': sum += tmp
                tmp = 0
            else: # error, return None
                return None
        if tmp != 0: # didn't end properly
            return None
        # create timedelta
        return timedelta(days=sum//86400, seconds=sum%86400)

    """status()
    Return the bot status
    
    Returns
    --------
    dict: Dict of string
    """
    def status(self : Util) -> dict[str, str]:
        return {
            "Uptime": self.uptime(),
            "Version": self.bot.VERSION,
            "Python": "{}, v{}.{}.{}".format(platform.python_implementation(), sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
            "OS": platform.platform(),
            "CPU": "{:.2f}%".format(self.process.cpu_percent()),
            "Memory": "{:.1f}MB ({:.2f}%)".format(self.process.memory_full_info().uss / 1048576, self.process.memory_percent()).replace(".0M", "M").replace(".00%", "%").replace("0%", "%"),
            "Save": ("**Pending**" if self.bot.data.pending else "Ok"),
            "GBF Update": ("**Pending**" if self.bot.data.save['gbfupdate'] else "Ok"),
            "Task Count": str(len(self.bot.tasks)),
            "Server Count": str(len(self.bot.guilds)),
            "Cogs Loaded": "{}/{}".format(len(self.bot.cogs), self.bot.cogn) if (len(self.bot.cogs) == self.bot.cogn) else "**{}**/{}".format(len(self.bot.cogs), self.bot.cogn)
        }

    """statusString()
    Return the bot status as a single string (call status() )
    
    Returns
    --------
    str: Status string
    """
    def statusString(self : Util) -> str:
        status : dict[str, str] = self.status()
        msgs : list[str] = []
        # make a string from the status dict
        for k in status:
            msgs.append("**")
            msgs.append(k)
            msgs.append("**▫️")
            msgs.append(status[k])
            msgs.append("\n")
        return "".join(msgs)

    """react()
    React to a message with an emoji
    
    Parameters
    ----------
    msg: disnake.Message object
    key: Either the emoji key set in config.json or the emoji in string format

    Returns
    --------
    bool: True if success, False if not
    """
    async def react(self : Util, msg : disnake.Message, key : str) -> bool:
        try:
            await msg.add_reaction(self.bot.emote.get(key)) # add reaction to given message
            return True
        except Exception as e:
            if str(e) != "404 Not Found (error code: 10008): Unknown Message":
                self.bot.logger.pushError("[UTIL] 'react' error:", e)
            return False

    """unreact()
    Remove a bot reaction to a message
    
    Parameters
    ----------
    msg: disnake.Message object
    key: Either the emoji key set in config.json or the emoji in string format

    Returns
    --------
    bool: True if success, False if not
    """
    async def unreact(self : Util, msg : disnake.Message, key : str) -> bool:
        try:
            await msg.remove_reaction(self.bot.emote.get(key), msg.guild.me) # remove reaction to given message
            return True
        except Exception as e:
            if str(e) != "404 Not Found (error code: 10008): Unknown Message":
                self.bot.logger.pushError("[UTIL] 'unreact' error:", e)
            return False

    """formatName()
    Shorten and fix player or crew names if they use long or some special characters.
    
    Parameters
    ----------
    name: The player name to shorten
    
    Returns
    --------
    str: The resulting name
    """
    def shortenName(self : Util, name : str) -> str:
        name : str = html.unescape(name) # unescape html special characters
        arabic : int = 0 # arabic characters
        rlo : list[int] = [] # rlo characters
        i : int
        c : str
        for i, c in enumerate(name): # iterate over string
            o : int = ord(c)
            if o == 0x202E:
                rlo.append(i - len(rlo))
            elif o >= 0xFB50 and o <= 0xFDFF:
                arabic += 1
        namel : list[str] = list(name)
        for i in rlo: # remove rlo characters
            namel.pop(i)
        name = "".join(namel)
        if len(name) == 0: # resulting name is empty
            name = "?" # return question mark
        if arabic > 1: # there are arabic characters
            return name[0] + "..." # only return first one + 3 dots, to avoid display issues
        else:
            return name # return name

    """breakdownHTML()
    Take a string containing HTML tags and break it down in a list.
    Odd elements should be the tags, even should be the text in between.
    
    Parameters
    ----------
    content: String, the string to breakdown
    
    Returns
    --------
    list: The resulting list
    """
    def breakdownHTML(self : Util, content : str) -> list[str]:
        split : list[str] = content.replace('\n', '').replace('    ','').replace('<!--','<comment>').replace('-->','</comment>').split('<') # split string by <
        result : list[str] = [split[0]]
        for i in range(1, len(split)):
            result.extend(split[i].split('>', 1)) # additional split by >
        # The split works shit way:
        # Replace <!-- --> by <comment></comment>
        # then
        # TEXT < TAG > TEXT ... TEXT < TAG > etc...
        # Result contains:
        # TEXT, TAG, TEXT, TAG ... etc...
        return result

    """str2gbfid()
    Convert a string to a GBF profile ID.
    
    Parameters
    ----------
    inter: The command interaction
    target: String, which can be:
        - Empty (the author GBF ID will be used if set, doesn't work if you set inter to a channel)
        - Positive integer, representing a GBF ID
        - A Discord Mention (<@discord_id> or <@!discord_id>)
    memberTarget: disnake.Member to search, set to None to ignore
    
    Returns
    --------
    int or str: The GBF ID or an error string if an error happened
    """
    async def str2gbfid(self : Util, inter : disnake.ApplicationCommandInteraction, target : str, memberTarget: disnake.Member = None) -> int|str:
        tid : int|str
        if memberTarget is not None: # memberTarget is valid
            if str(memberTarget.id) not in self.bot.data.save['gbfids']: # check if their id is linked
                return "`{}` didn't set its GBF profile ID.".format(memberTarget.display_name)
            tid = self.bot.data.save['gbfids'][str(memberTarget.id)] # return GBF ID
        elif target == "": # empty target string
            if str(inter.author.id) not in self.bot.data.save['gbfids']: # check if their id is linked
                return "You didn't set your GBF profile ID.\nUse {} to link it with your Discord ID.".format(self.command2mention('gbf profile set'))
            tid = self.bot.data.save['gbfids'][str(inter.author.id)] # return GBF ID
        elif target.startswith('<@') and target.endswith('>'): # mention
            try:
                if target[2] == "!":
                    target = str(int(target[3:-1])) # parse to retrieve member id
                else:
                    target = str(int(target[2:-1]))
                if target not in self.bot.data.save['gbfids']: # check if their id is linked
                    return "This member didn't set its profile ID.\nTry to use {} to search the GW Database instead".format(self.command2mention('gw find player'))
                tid = self.bot.data.save['gbfids'][target] # return gbf id
            except:
                return "An error occured: Invalid parameter {} -> {}.".format(target, type(target))
        else: # maybe a number?
            try: tid = int(target) # check
            except: return "`{}` isn't a valid target.\nUse {} if it's for yourself.\nOr either input a valid GBF ID or a Discord Mention of someone with a set ID.".format(target, self.command2mention('gbf profile set'))
        if tid < 0 or tid >= 100000000: # check if the id looks legit
            return "Invalid ID range (ID must be between 0 and 100 000 000)."
        return tid

    """formatElement()
    Format the unite&fight/dread barrage element into a string containing the superior and inferior elements
    
    Parameters
    ----------
    elem: unite&fight/dread barrage element string
    
    Returns
    --------
    str: Formatted string
    """
    def formatElement(self : Util, elem : str) -> str:
        # left is the advantaged element, right is the disadvantaged
        return "{}⚔️{}".format(self.bot.emote.get(elem), self.bot.emote.get({'fire':'wind', 'water':'fire', 'earth':'water', 'wind':'earth', 'light':'dark', 'dark':'light'}.get(elem)))

    """strToInt()
    Convert string to int, with support for T, B, M and K
    
    Parameters
    ----------
    s: String to convert
    
    Returns
    --------
    int: Converted value
    """
    def strToInt(self : Util, s : str) -> int:
        try:
            return int(s) # try to convert to int
        except: # error, there are characters
            n : float = float(s[:-1]) # convert to float, except the last character (to support for example something like 1.2B)
            m : str = s[-1].lower() # get last character
            return int(n * self.MULTIPLIER_1000[m]) # if m isn't in MULTIPLIER_1000, trigger an exception

    """valToStr()
    Convert an int or float to str and shorten it with T, B, M, K
    If None is sent in parameter, it returns "n/a"
    
    Parameters
    ----------
    s: Value to convert
    p: Integer, select the float precision (Default 1, Max 3)
    
    Returns
    --------
    str: Converted string
    """
    def valToStr(self : Util, s : int|float, p : int = 1) -> str:
        if s is None: # value is None
            return "n/a"
        if isinstance(s, int): # convert int to float
            s = float(s)
        bs : int|float = abs(s) # bs is the unsigned version
        b : str
        rs : str
        match p: # float precision
            case 2:
                b = "{:,.2f}"
                rs = ".00"
            case 3:
                b = "{:,.3f}"
                rs = ".000"
            case _:
                b = "{:,.1f}"
                rs = ".0"
        # go over string formats
        chara : str
        value : int
        for chara, value in self.MULTIPLIER_1000.items():
            if bs >= value: # greater, so we divive by value, format and add the character
                return b.format(s/value).replace(rs, '') + chara.upper()
        # else return the number
        return b.format(s).replace(rs, '')

    """players2mentions()
    Take a list of users and return a string mentionning all of them.
    Used for Games.
    
    Parameters
    ----------
    players: list of disnake.User/Member
    
    Returns
    --------
    str: resulting string
    """
    def players2mentions(self : Util, players : list) -> str:
        s : list[str] = []
        for p in players:
            s.append(p.mention)
        return " ".join(s)

    """search_wiki_for_id()
    Search the wiki cargo table for a weapon/character/summon id
    
    Parameters
    ----------
    name: String, target search name
    category: String, table to use for the request (either characters, summons or weapons)
    from_gacha: Boolean, set to True to only except elements from the gacha
    element: String (optional), element of the target
    proficiency: String (optional), weapon type of the target (weapon only)
    
    Returns
    --------
    str: Target ID, None if error/not found
    """
    async def search_wiki_for_id(self : Util, name : str, category : str, from_gacha : bool = False, element : str|None = None, proficiency : str|None = None) -> str|None:
        try:
            addition : list[str] = []
            extra_fields : str = ""
            if from_gacha: # add check to be sure it's a gacha weapon
                addition.append('AND (obtain LIKE "%normal%" OR obtain LIKE "%premium%" OR obtain LIKE "%gala%")')
            if element is not None: # add element check
                addition.append('AND element = "{}"'.format(element))
            if proficiency is not None and category == "weapons": # add proficiency check
                addition.append('AND type = "{}"'.format(proficiency))
                extra_fields = ",type"
            # make request
            data : RequestResult = await self.bot.net.requestWiki("index.php", params={"title":"Special:CargoExport", "tables":category, "where":'name = "{}"{}'.format(name, ' '.join(addition)), "fields":"name,id,obtain,element{}".format(extra_fields), "format":"json", "limit":"10"}, allow_redirects=True)
            # return result id
            return str(data[0]['id'])
        except:
            return None

    """process_command()
    Recursivly search the slash command list
    
    Parameters
    ----------
    cmd: Command or sub command
    
    Returns
    ----------
    list: Contains [full name, id, description]
    """
    def process_command(self : Util, cmd : BotCommand) -> list[BotCommandSearch]:
        has_sub : bool = False
        results : list[BotCommandSearch] = []
        opt : disnake.app_commands.Option
        # check if command has sub command(s)
        try:
            for opt in cmd.options:
                if opt.type == disnake.OptionType.sub_command_group or opt.type == disnake.OptionType.sub_command:
                    has_sub = True
                    break
        except:
            pass
        # if it has sub command(s)
        if has_sub:
            for opt in cmd.options:
                if opt.type == disnake.OptionType.sub_command_group or opt.type == disnake.OptionType.sub_command:
                    rs : list[BotCommandSearch] = self.process_command(opt) # recursive call for that child
                    for r in rs: # process result
                        r[0] = cmd.name + " " + r[0]
                        try:
                            if r[1] is None:
                                r[1] = cmd.id
                        except:
                            pass
                    # add results to our
                    results.extend(rs)
            return results
        else:
            # return command details (2 possibilities depending if it got an id)
            try: return [[cmd.name, cmd.id, cmd.description]]
            except: return [[cmd.name, None, cmd.description]]

    """command2mention()
    Convert a global slash command name to a mention string
    
    Parameters
    ----------
    base_command_name: Command or sub command full name string
    
    Returns
    ----------
    str: mention or base_command_name if failed
    """
    def command2mention(self : Util, base_command_name : str) -> str:
        global_slash_commands : list[disnake.APISlashCommand|disnake.APIUserCommand|disnake.APIMessageCommand] = self.bot.global_slash_commands
        # retrieve command name
        cmd_name : str
        if base_command_name.startswith('/'):
            cmd_name = base_command_name[1:].lower()
        else:
            cmd_name = base_command_name.lower()
        # look for that command in the list
        command : disnake.APISlashCommand|disnake.APIUserCommand|disnake.APIMessageCommand
        for command in global_slash_commands:
            rs : list[BotCommandSearch] = self.process_command(command) # child command check
            r : BotCommandSearch
            for r in rs:
                if cmd_name.lower() == r[0].lower(): # good match
                    return '</{}:{}>'.format(r[0], r[1]) # make and return the mention (format: </command_name:command_id> )
        return base_command_name

    """version2str()
    Convert a GBF version number to its timestamp and date
    
    Parameters
    ----------
    version_number: Number, either an Integer or String
    
    Returns
    ----------
    str: Timestamp string
    """
    def version2str(self : Util, version_number : str|int) -> str: # convert gbf version number to its timestamp
        try:
            return "{0:%Y/%m/%d %H:%M} JST".format(datetime.utcfromtimestamp(int(version_number)) + timedelta(seconds=self.JSTDIFF)) # add JST
        except:
            return ""