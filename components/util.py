import disnake
import asyncio
from typing import Optional, Union, Callable, Any, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from datetime import datetime, timedelta, timezone
import psutil
import platform
import os
import sys
import html

# ----------------------------------------------------------------------------------------------------------------
# Utility Component
# ----------------------------------------------------------------------------------------------------------------
# Feature a lot of utility functions
# ----------------------------------------------------------------------------------------------------------------

class Util():
    JSTDIFF = 32400 # JST <-> UTC difference in seconds
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot
        self.emote = None
        self.starttime = self.UTC() # used to check the uptime
        self.process = psutil.Process(os.getpid())
        self.process.cpu_percent() # called once to initialize

    def init(self) -> None:
        self.emote = self.bot.emote

    """json_deserial_array()
    Deserialize a list (used for our json files)
    
    Parameters
    ----------
    array: List
    
    Returns
    --------
    list: Deserialized list
    """
    def json_deserial_array(self, array : list) -> list:
        a = []
        for v in array:
            match v:
                case list():
                    a.append(self.json_deserial_array(v))
                case dict():
                    a.append(self.json_deserial_dict(list(v.items())))
                case str():
                    try:
                        a.append(datetime.strptime(v, "%Y-%m-%dT%H:%M:%S")) # needed for datetimes
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
    def json_deserial_dict(self, pairs : dict) -> dict: # deserialize a dict from a json
        d = {}
        for k, v in pairs:
            if isinstance(v, list):
                d[k] = self.json_deserial_array(v)
            elif isinstance(v, dict):
                d[k] = self.json_deserial_dict(list(v.items()))
            elif isinstance(v, str):
                try:
                    d[k] = datetime.strptime(v, "%Y-%m-%dT%H:%M:%S") # needed for datetimes
                except ValueError:
                    d[k] = v
            else:
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
    def json_serial(self, obj : Any) -> Any: # serialize everything including datetime objects
        if isinstance(obj, datetime):
            return obj.replace(microsecond=0).isoformat()
        raise TypeError ("Type %s not serializable" % type(obj))

    """UTC()
    Return the current time, UTC timezone

    Returns
    --------
    datetime: Current time
    """
    def UTC(self) -> datetime:
        return datetime.now(timezone.utc).replace(tzinfo=None)

    """JST()
    Return the current time, JST timezone

    Parameters
    --------
    delay: Boolean, shift the clock back by 30 seconds if True (to ensure proper synchro for some functions)

    Returns
    --------
    datetime: Current time
    """
    def JST(self, delay : bool = True) -> datetime:
        if delay: return self.UTC() + timedelta(seconds=self.JSTDIFF) - timedelta(seconds=30)
        else: return self.UTC() + timedelta(seconds=self.JSTDIFF)

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
    def time(self, to_convert : Optional[datetime] = None, style : list = ['f'], removejst : bool = False, naivecheck : bool = True) -> str:
        if to_convert is None: to_convert = self.UTC()
        msgs = []
        if removejst:
            to_convert -= timedelta(seconds=self.JSTDIFF)
        if naivecheck and (to_convert.tzinfo is None or to_convert.tzinfo.utcoffset(to_convert)):
            to_convert = to_convert.replace(tzinfo=timezone.utc)
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
    def uptime(self, as_string : bool = True) -> Union[str, timedelta]: # get the uptime
        delta = self.UTC() - self.starttime
        if as_string: return "{}".format(self.delta2str(delta, 3))
        else: return delta

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
    def delta2str(self, delta : timedelta, mode : int = 1) -> str:
        match mode:
            case 3: return "{}d{}h{}m{}s".format(delta.days, delta.seconds // 3600, (delta.seconds // 60) % 60, delta.seconds % 60)
            case 2: return "{}d{}h{}m".format(delta.days, delta.seconds // 3600, (delta.seconds // 60) % 60)
            case 1: return "{}h{}m".format(delta.seconds // 3600, (delta.seconds // 60) % 60)
            case _: return "{}m".format(delta.seconds // 60)

    """str2delta()
    Convert string to a a timedelta object (format: XdXhXmXs)
    
    Parameters
    ----------
    d: The string to convert
    
    Returns
    --------
    timedelta: Resulting timedelta object
    """
    def str2delta(self, d : str) -> Optional[timedelta]: # return None if error
        flags = {'d':False,'h':False,'m':False,'s':False}
        tmp = 0 # buffer
        sum = 0 # delta in seconds
        for c in d:
            if c.isdigit():
                tmp = (tmp * 10) + int(c)
            elif c.lower() in flags:
                if flags[c.lower()]:
                    return None
                if tmp < 0:
                    return None
                flags[c.lower()] = True
                match c:
                    case 'd': sum += tmp * 86400
                    case 'h': sum += tmp * 3600
                    case 'm': sum += tmp * 60
                    case 's': sum += tmp
                tmp = 0
            else:
                return None
        if tmp != 0: return None
        return timedelta(days=sum//86400, seconds=sum%86400)

    """status()
    Return the bot status
    
    Returns
    --------
    dict: Dict of string
    """
    def status(self) -> dict:
        return {
            "Version": self.bot.VERSION,
            "Python": "{}.{}.{}".format(sys.version_info.major, sys.version_info.minor, sys.version_info.micro),
            "OS": platform.platform(),
            "Uptime": self.uptime(),
            "CPU": "{:.2f}%".format(self.process.cpu_percent()),
            "Memory": "{:.1f}MB ({:.2f}%)".format(self.process.memory_full_info().uss / 1048576, self.process.memory_percent()).replace(".0M", "M").replace(".00%", "%").replace("0%", "%"),
            "Save": ("**Pending**" if self.bot.data.pending else "Ok"),
            "GBF Update": ("**Pending**" if self.bot.data.save['gbfupdate'] else "Ok"),
            "Task Count": str(len(asyncio.all_tasks())),
            "Server Count": str(len(self.bot.guilds)),
            "Cogs Loaded": "{}/{}".format(len(self.bot.cogs), self.bot.cogn) if (len(self.bot.cogs) == self.bot.cogn) else "**{}**/{}".format(len(self.bot.cogs), self.bot.cogn)
        }

    """statusString()
    Return the bot status as a single string (call status() )
    
    Returns
    --------
    str: Status string
    """
    def statusString(self) -> str:
        status = self.status()
        msgs = []
        for k in status:
            msgs.append("**{}**▫️{}\n".format(k, status[k]))
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
    async def react(self, msg : disnake.Message, key : str) -> bool:
        try:
            await msg.add_reaction(self.emote.get(key))
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
    async def unreact(self, msg : disnake.Message, key : str) -> bool:
        try:
            await msg.remove_reaction(self.emote.get(key), msg.guild.me)
            return True
        except Exception as e:
            if str(e) != "404 Not Found (error code: 10008): Unknown Message":
                self.bot.logger.pushError("[UTIL] 'unreact' error:", e)
            return False

    """clean()
    Delete a bot command message after X amount of time.
    A white check mark is added in reaction to the original command after deletion
    
    Parameters
    ----------
    target: Tuple of a Disnake Context and Message OR a Disnake Interaction
    delay: Time in second before deletion
    all: if True, the message will be deleted, if False, the message is deleted it it was posted in an unauthorized channel
    """
    async def clean(self, target : Union[tuple, disnake.Message, disnake.ApplicationCommandInteraction], delay : Optional[Union[int, float]] = None, all : bool = False) -> None:
        try:
            if isinstance(target, tuple): # unused, legacy of old version
                if all or not self.bot.isAuthorized(target[0]):
                    await target[1].delete(delay=delay)
                    try: await self.react(target[0].message, '✅') # white check mark
                    except: pass
            elif isinstance(target, disnake.ApplicationCommandInteraction) or isinstance(target, disnake.ModalInteraction):
                if all or not self.bot.isAuthorized(target):
                    if delay is not None: await asyncio.sleep(delay)
                    await target.edit_original_message(content="{}".format(self.bot.emote.get('lyria')), embed=None, view=None, attachments=[])
            elif isinstance(target, disnake.Message):
                if all or not self.bot.isAuthorized(target):
                    if delay is not None: await asyncio.sleep(delay)
                    await target.edit(content="{}".format(self.bot.emote.get('lyria')), embed=None, view=None, attachments=[])
        except Exception as e:
            if "Unknown Message" not in str(e):
                self.bot.logger.pushError("[UTIL] 'clean' error:", e)
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
    def shortenName(self, name : str) -> str:
        name = html.unescape(name)
        arabic = 0
        rlo = []
        for i, c in enumerate(name):
            o = ord(c)
            if o == 0x202E:
                rlo.append(i - len(rlo))
            elif o >= 0xFB50 and o <= 0xFDFF:
                arabic += 1
        name = list(name)
        for i in rlo:
            name.pop(i)
        name = "".join(name)
        if len(name) == 0: name = "?"
        if arabic > 1: return name[0] + "..."
        else: return name

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
    def breakdownHTML(self, content : str) -> list:
        firstsplit = content.replace('\n', '').replace('    ','').split('<')
        result = [firstsplit[0]]
        for i in range(1, len(firstsplit)):
            result.extend(firstsplit[i].split('>', 1))
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
    async def str2gbfid(self, inter : disnake.ApplicationCommandInteraction, target : str, memberTarget: disnake.Member = None) -> Union[int, str]:
        if memberTarget is not None:
            if str(memberTarget.id) not in self.bot.data.save['gbfids']:
                return "`{}` didn't set its GBF profile ID.".format(memberTarget.display_name)
            tid = self.bot.data.save['gbfids'][str(memberTarget.id)]
        elif target == "":
            if str(inter.author.id) not in self.bot.data.save['gbfids']:
                return "You didn't set your GBF profile ID.\nUse {} to link it with your Discord ID.".format(self.command2mention('gbf profile set'))
            tid = self.bot.data.save['gbfids'][str(inter.author.id)]
        elif target.startswith('<@') and target.endswith('>'):
            try:
                if target[2] == "!": target = str(int(target[3:-1]))
                else: target = str(int(target[2:-1]))
                if target not in self.bot.data.save['gbfids']:
                    return "This member didn't set its profile ID.\nTry to use {} to search the GW Database instead".format(self.command2mention('gw find player'))
                tid = self.bot.data.save['gbfids'][target]
            except:
                return "An error occured: Invalid parameter {} -> {}.".format(target, type(target))
        else:
            try: tid = int(target)
            except: return "`{}` isn't a valid target.\nUse {} if it's for yourself.\nOr either input a valid GBF ID or a Discord Mention of someone with a set ID.".format(target, self.command2mention('gbf profile set'))
        if tid < 0 or tid >= 100000000:
            return "Invalid ID range (ID must be between 0 and 100 000 000)."
        return tid

    """gbfgstr2crewid()
    Take a string as an input and attempt to match it to a crew ID registered in config.json
    
    Parameters
    ----------
    target: String, can be a crew id or a crew name registered in config.json
    
    Returns
    --------
    str: The crew ID or the original string if no match is found
    """
    def gbfgstr2crewid(self, target : str) -> str:
        crew_id_list = {**(self.bot.data.config['granblue']['gbfgcrew']), **(self.bot.data.config['granblue'].get('othercrew', {}))}
        return crew_id_list.get(target.lower(), target)

    """formatElement()
    Format the unite&fight/dread barrage element into a string containing the superior and inferior elements
    
    Parameters
    ----------
    elem: unite&fight/dread barrage element string
    
    Returns
    --------
    str: Formatted string
    """
    def formatElement(self, elem : str) -> str:
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
    def strToInt(self, s : str) -> int:
        try:
            return int(s)
        except:
            n = float(s[:-1]) # float to support for example 1.2B
            m = s[-1].lower()
            l = {'k':1000, 'm':1000000, 'b':1000000000, 't':1000000000000}
            return int(n * l[m])

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
    def valToStr(self, s : Union[int, float], p : int = 1) -> str:
        if s is None: return "n/a"
        if isinstance(s, int): s = float(s)
        bs = abs(s)
        match p:
            case 2:
                b = "{:,.2f}"
                rs = ".00"
            case 3:
                b = "{:,.3f}"
                rs = ".000"
            case _:
                b = "{:,.1f}"
                rs = ".0"
        if bs >= 1000000000000:
            return b.format(s/1000000000000).replace(rs, '') + "T"
        elif bs >= 1000000000:
            return b.format(s/1000000000).replace(rs, '') + "B"
        elif bs >= 1000000:
            return b.format(s/1000000).replace(rs, '') + "M"
        elif bs >= 1000:
            return b.format(s/1000).replace(rs, '') + "K"
        else:
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
    def players2mentions(self, players : list) -> str:
        s = []
        for p in players:
            s.append(p.mention)
        return " ".join(s)

    """search_wiki_for_id()
    Search the wiki for a weapon/character/summon id
    
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
    async def search_wiki_for_id(self, name : str, category : str, from_gacha : bool = False, element : Optional[str] = None, proficiency : Optional[str] = None) -> Optional[str]:
        try:
            addition = []
            extra_fields = ""
            if from_gacha:
                addition.append('AND (obtain LIKE "%normal%" OR obtain LIKE "%premium%" OR obtain LIKE "%gala%")')
            if element is not None:
                addition.append('AND element = "{}"'.format(element))
            if proficiency is not None and category == "weapons":
                addition.append('AND type = "{}"'.format(proficiency))
                extra_fields = ",type"
            data = (await self.bot.net.requestWiki("index.php", params={"title":"Special:CargoExport", "tables":category, "where":'name = "{}"{}'.format(name, ' '.join(addition)), "fields":"name,id,obtain,element{}".format(extra_fields), "format":"json", "limit":"10"}, allow_redirects=True))
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
    list: [full name, id, description]
    """
    def process_command(self, cmd : Union[disnake.APISlashCommand, disnake.APIUserCommand, disnake.APIMessageCommand]) -> list:
        has_sub = False
        results = []
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
                    rs = self.process_command(opt) # recursive call for that child
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
    def command2mention(self, base_command_name : str) -> str:
        global_slash_commands = self.bot.global_slash_commands
        if base_command_name.startswith('/'):
            cmd_name = base_command_name[1:].lower()
        else:
            cmd_name = base_command_name.lower()

        for command in global_slash_commands:
            rs = self.process_command(command)
            for r in rs:
                if cmd_name.lower() == r[0].lower():
                    return '</{}:{}>'.format(r[0], r[1])
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
    def version2str(self, version_number : Union[str, int]) -> str: # convert gbf version number to its timestamp
        try: return "{0:%Y/%m/%d %H:%M} JST".format(datetime.utcfromtimestamp(int(version_number)) + timedelta(seconds=self.JSTDIFF)) # JST
        except: return ""

    """send_modal()
    Create and manage a modal interaction
    
    Parameters
    ----------
    inter: base interaction
    custom_id : modal id
    title: modal title
    components: list of disnake ui components
    callback: the function to be called if the modal is submitted
    
    Returns
    ----------
    disnake.ModalInteraction: The modal, else None if failed/cancelled
    """
    async def send_modal(self, inter : disnake.Interaction, custom_id : str, title : str, callback : Callable, components : list, extra : str = None) -> disnake.ModalInteraction:
        await inter.response.send_modal(modal=CustomModal(bot=self.bot, title=title,custom_id=custom_id,components=components, callback=callback, extra=extra))

"""CustomModal
A Modal class where you can set your own callback
"""
class CustomModal(disnake.ui.Modal):
    def __init__(self, bot : 'DiscordBot', title : str, custom_id : str, components : list, callback : Callable, extra : str = None) -> None:
        super().__init__(title=title, custom_id=custom_id, components=components)
        self.bot = bot
        self.custom_callback = callback
        self.extra = extra

    async def on_error(self, error: Exception, inter: disnake.ModalInteraction) -> None:
        await inter.response.send_message(embed=self.bot.embed(title="Error", description="An unexpected error occured, my owner has been notified"))
        self.bot.logger.pushError("[MODAL] 'on_error' event:", error)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
        await self.custom_callback(self, inter)