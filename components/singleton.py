from __future__ import annotations
import disnake
from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.ranking import CrewDataEntry, PlayerDataEntry
from dataclasses import dataclass
from datetime import datetime
import math

# ----------------------------------------------------------------------------------------------------------------
# Singleton Component
# ----------------------------------------------------------------------------------------------------------------
# This component manages singletons found in this file
# ----------------------------------------------------------------------------------------------------------------

class Singleton():
    def __init__(self : Singleton, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot
        self.gamecard_cache : dict[int, GameCard] = {}

    def init(self : Singleton) -> None:
        pass

    """make_and_send_modal()
    Create and manage a modal interaction
    
    Parameters
    ----------
    inter : base interaction
    custom_id : modal id
    title: modal title
    components: list of disnake ui components
    callback: the function to be called if the modal is submitted
    
    Returns
    ----------
    disnake.ModalInteraction: The modal, else None if failed/cancelled
    """
    async def make_and_send_modal(self : Singleton, inter : disnake.Interaction, custom_id : str, title : str, callback : Callable, components : list[disnake.ui.Component], extra : str|None = None) -> CustomModal:
        # see below for the custom modal class
        await inter.response.send_modal(modal=CustomModal(bot=self.bot, title=title,custom_id=custom_id,components=components, callback=callback, extra=extra))

    """get_GameCard()
    Create a GameCard to use for a game
    
    Parameters
    ----------
    value: Integer, 1 (ace) to 14 (high ace)
    suit: 0 to 3
    
    Returns
    ----------
    GameCard: The generated card
    """
    def get_GameCard(self : Singleton, value : int, suit : int) -> GameCard:
        if value < 1 or value > 14:
            raise Exception("Invalid GameCard value")
        elif suit < 0 or suit > 3:
            raise Exception("Invalid GameCard suit")
        index : int = value << 8 + suit # calculate index
        if index not in self.gamecard_cache: # add card in cache if it doesn't exist
            self.gamecard_cache[index] = GameCard.make_card(value, suit)
        return self.gamecard_cache[index]

    """make_Score()
    Initialize and return a Score instance
    
    Parameters
    ----------
    type: Integer, 0 (crew) or 1 (player)
    ver: Integer, Database version used
    gw: Integer, GW id
    
    Returns
    ----------
    Score: The generated card
    """
    def make_Score(self : Singleton, type : int|None, ver : int|None, gw : int|None, data : CrewDataEntry|PlayerDataEntry) -> Score:
        return Score.make_score(type, ver, gw, data)

    """make_GWDB()
    Initialize and return a GWDB instance
    
    Parameters
    ----------
    type: Integer, 0 (crew) or 1 (player)
    ver: Integer, Database version used
    gw: Integer, GW id
    
    Returns
    ----------
    Score: The generated card
    """
    def make_GWDB(self : Singleton, data : list|None) -> GWDB:
        return GWDB.make_GWDB(data)

    """make_calc()
    Initialize a Calculator instance and return a calcul result
    
    Parameters
    ----------
    type: Integer, 0 (crew) or 1 (player)
    ver: Integer, Database version used
    gw: Integer, GW id
    
    Returns
    ----------
    Score: The generated card
    """
    def make_calc(self : Singleton, expression : str = "", vars : dict = {}) -> int|float:
        return Calc().evaluate(expression, vars)

# ----------------------------------------------------------------------------------------------------------------
# Below are the singletons
# ----------------------------------------------------------------------------------------------------------------

"""CustomModal
A Modal class where you can set your own callback
"""
class CustomModal(disnake.ui.Modal):
    def __init__(self : CustomModal, bot : DiscordBot, title : str, custom_id : str, components : list, callback : Callable, extra : str|None = None) -> None:
        super().__init__(title=title, custom_id=custom_id, components=components)
        self.bot : DiscordBot = bot # bot reference
        self.custom_callback : Callable = callback # our callback
        self.extra : str = extra # any extra info we can pass here. will be accessible from the interaction in the callback

    async def on_error(self : CustomModal, error: Exception, inter : disnake.ModalInteraction) -> None:
        await inter.response.send_message(embed=self.bot.embed(title="Error", description="An unexpected error occured, my owner has been notified"))
        self.bot.logger.pushError("[MODAL] 'on_error' event:", error)

    async def callback(self : CustomModal, inter : disnake.ModalInteraction) -> None:
        await self.custom_callback(self, inter) # trigger the callback

"""GameCard
Standard card representation for card games
"""
@dataclass(frozen=True, slots=True)
class GameCard():
    value : int
    suit : int
    _strings_ : list[str]

    @classmethod
    def make_card(cls : GameCard, value: int, suit: int) -> GameCard:
        value = value # value ranges from 1 (ace) to 13 (king) or 14 (ace)
        suit = suit # suit ranges from 0 to 3
        _strings_ = [None, None, None] # value, suit, complete
        # set _strings_
        # value
        match value:
            case 1|14: _strings_[0] = "A"
            case 11: _strings_[0] = "J"
            case 12: _strings_[0] = "Q"
            case 13: _strings_[0] = "K"
            case _: _strings_[0] = str(value)
        # suit
        match suit:
            case 0: _strings_[1] = "\♦️"
            case 1: _strings_[1] = "\♠"
            case 2: _strings_[1] = "\♥️"
            case 3: _strings_[1] = "\♣️"
        _strings_[2] = "".join(_strings_[:2])
        return cls(value, suit, _strings_)

    def __repr__(self : GameCard) -> str: 
        return self._strings_[2]

    def __str__(self : GameCard) -> str:
        return self._strings_[2]

    def __int__(self : GameCard) -> int:
        return self.value

    def __lt__(self : GameCard, other : GameCard) -> bool:
         return self.value < other.value

    def getStringValue(self : GameCard) -> str:
        return self._strings_[0]

    def getStringSuit(self : GameCard) -> str:
        return self._strings_[1]

"""Score
Store a score for a Guild War participant/crew
"""
@dataclass(frozen=True, slots=True)
class Score(): # GW Score structure
    type : int|None # crew or player
    ver : int|None # database version
    gw : int|None # gw id
    ranking : int|None # ranking
    id : int|None # crew/player id
    name : str|None
    # scores
    current : int|None # will match preliminaries or total1-4
    current_day : int|None # current day. 0 : int = prelims, 1-4 : int = day 1-4
    day : int|None
    preliminaries : int|None
    day1 : int|None
    total1 : int|None
    day2 : int|None
    total2 : int|None
    day3 : int|None
    total3 : int|None
    day4 : int|None
    total4 : int|None
    # speed
    top_speed : float|None
    current_speed : float|None
    
    @classmethod
    def make_score(cls : Score, type : int|None, ver : int|None, gw : int|None, data : CrewDataEntry|PlayerDataEntry) -> None:
        # init
        ranking : int|None = None
        id : int|None = None
        name : str|None = None
        current : int|None = None
        current_day : int|None = None
        day : int|None = None
        preliminaries : int|None = None
        day1 : int|None = None
        total1 : int|None = None
        day2 : int|None = None
        total2 : int|None = None
        day3 : int|None = None
        total3 : int|None = None
        day4 : int|None = None
        total4 : int|None = None
        top_speed : float|None = None
        current_speed : float|None = None
        
        if type == 0: # player
            ranking = data[0]
            id = data[1]
            name = data[2]
            current = data[3]
        else: # crew
            if ver >= 2: # (version 2 and above)
                ranking = data[0]
                id = data[1]
                name = data[2]
                preliminaries = data[3]
                total1 = data[4]
                total2 = data[5]
                total3 = data[6]
                total4 = data[7]
                if total1 is not None and preliminaries is not None: day1 = total1 - preliminaries
                if total2 is not None and total1 is not None: day2 = total2 - total1
                if total3 is not None and total2 is not None: day3 = total3 - total2
                if total4 is not None and total3 is not None: day4 = total4 - total3
                if ver >= 3:
                    top_speed = data[8]
                if ver >= 4: # and version 6
                    current_speed = data[9]
            else: # old database format
                ranking = data[0]
                id = data[1]
                name = data[2]
                preliminaries = data[3]
                day1 = data[4]
                total1 = data[5]
                day2 = data[6]
                total2 = data[7]
                day3 = data[8]
                total3 = data[9]
                day4 = data[10]
                total4 = data[11]
            # set the current score, etc
            if total4 is not None:
                current = total4
                current_day = day4
                day = 4
            elif total3 is not None:
                current = total3
                current_day = day3
                day = 3
            elif total2 is not None:
                current = total2
                current_day = day2
                day = 2
            elif total1 is not None:
                current = total1
                current_day = day1
                day = 1
            elif preliminaries is not None:
                current = preliminaries
                current_day = preliminaries
                day = 0
        
        return cls(type, ver, gw, ranking, id, name, current, current_day, day, preliminaries, day1, total1, day2, total2, day3, total3, day4, total4, top_speed, current_speed)

    def __repr__(self : Score) -> str: # used for debug
        return "Score({}, {}, {}, {}, {})".format(self.gw,self.ver,self.type,self.name,self.current)

    def __str__(self : Score) -> str: # used for debug
        return "GW{}, v{}, {}, {}, {}".format(self.gw, self.ver, 'crew' if self.type else 'player', self.name, self.current)

"""GWDB
Handle a Guild War Database
Contain a database general infos, such which GW is it for, its version, etc...
"""
@dataclass(frozen=True, slots=True)
class GWDB():
    gw : int|None
    ver : int
    timestamp : datetime|None

    @classmethod
    def make_GWDB(cls : GWDB, data : list|None = None) -> GWDB:
        # data is the content of info table of our database
        gw : int|None
        ver : int
        timestamp : datetime|None
        try:
            gw = int(data[0])
        except:
            gw = None
            ver = 0
            timestamp = None
            return cls(gw, ver, timestamp)
        try:
            ver = int(data[1])
        except: 
            ver = 1
        try:
            timestamp = datetime.utcfromtimestamp(data[2])
        except: 
            timestamp = None
        return cls(gw, ver, timestamp)

    def __repr__(self : GWDB) -> str: # used for debug
        return str(self)

    def __str__(self : GWDB) -> str: # used for debug
        return "GWDB({}, {}, {})".format(self.gw,self.ver,self.timestamp)

"""Calculator
Simple class to make complicated calculations
Used by the $calc command
"""
class Calc():
    FUNCS : list[str] = ['cos', 'sin', 'tan', 'acos', 'asin', 'atan', 'cosh', 'sinh', 'tanh', 'acosh', 'asinh', 'atanh', 'exp', 'ceil', 'abs', 'factorial', 'floor', 'round', 'trunc', 'log', 'log2', 'log10', 'sqrt', 'rad', 'deg'] # supported functions

    def __init__(self : Calc) -> None:
        self.expression : str = ""
        self.index : int = 0
        self.vars : dict[str, float] = {
            'pi' : math.pi,
            'e' : math.e
        }

    """evaluate()
    Evaluate a mathematical expression and return the result
    
    Parameters
    ----------
    expression: Math expression
    vars: Variable
    
    Raises
    ------
    Exception: For any errors
    
    Returns
    --------
    float or int: Result
    """
    def evaluate(self : Calc, expression : str = "", vars : dict = {}) -> int|float:
        # prepare expression
        self.expression = expression.replace(' ', '').replace('\t', '').replace('\n', '').replace('\r', '')
        # store variables
        self.vars = self.vars | vars
        for func in self.FUNCS: # check variable names for dupes with function names
            if func in self.vars: raise Exception("Variable name '{}' can't be used".format(func))
        # parse expression and get the result
        value : float = float(self.parse())
        # interruption check
        if self.isNotDone():
            raise Exception("Unexpected character '{}' found at index {}".format(self.peek(), self.index))
        # adjust float if needed and convert to int
        epsilon : float = 0.0000000001
        if int(value) == value:
            return int(value)
        elif int(value + epsilon) != int(value):
            return int(value + epsilon)
        elif int(value - epsilon) != int(value):
            return int(value)
        return value

    """isNotDone()
    Return True if the evaluation isn't finished
    
    Returns
    --------
    bool: True if the evaluation isn't finished, False if it is
    """
    def isNotDone(self : Calc) -> bool:
        return self.index < len(self.expression)

    """peek()
    Get the next element
    
    Returns
    --------
    str: Next element to be parsed
    """
    def peek(self : Calc) -> str:
        return self.expression[self.index:self.index + 1]

    """parse()
    Parse the next elements
    
    Returns
    --------
    float or int: Result
    """
    def parse(self : Calc) -> int|float:
        values : list[float] = [self.multiply()] # start by calling multiply
        while True:
            c : str = self.peek() # get next character
            if c in ['+', '-']: # as long as it's a + or - operator
                self.index += 1
                if c == '-': values.append(- self.multiply()) # if -, minus multiply
                else: values.append(self.multiply()) # else just multiply
            else:
                break
        return sum(values) # addition all values

    """multiply()
    Multiply the next elements
    
    Returns
    --------
    float or int: Result
    """
    def multiply(self : Calc) -> int|float:
        values : list[float] = [self.parenthesis()] # call parenthesis first
        denominator : int|float 
        while True:
            c : str = self.peek() # check operator
            if c in ['*', 'x']: # multiply
                self.index += 1
                values.append(self.parenthesis())
            elif c == '/': # divie
                div_index = self.index
                self.index += 1
                denominator = self.parenthesis()
                if denominator == 0:
                    raise Exception("Division by 0 occured at index {}".format(div_index))
                values.append(1.0 / denominator)
            elif c == '%': # modulo
                mod_index = self.index
                self.index += 1
                denominator = self.parenthesis()
                if denominator == 0:
                    raise Exception("Modulo by 0 occured at index {}".format(mod_index))
                values[-1] = values[-1] % denominator
            elif c == '^': # exponent
                self.index += 1
                exponent : int|float = self.parenthesis()
                values[-1] = values[-1] ** exponent
            elif c == '!': # factorial
                self.index += 1
                values[-1] = math.factorial(values[-1])
            else:
                break
        value : float = 1.0
        factor : float
        for factor in values:
            value *= factor
        return value

    """parenthesis()
    Parse the elements in the parenthesis
    
    Raises
    ------
    Exception: Missing parenthesis
    
    Returns
    --------
    float or int: Result
    """
    def parenthesis(self : Calc) -> int|float:
        if self.peek() == '(': # check if next character is an open parenthesis
            self.index += 1
            value : int|float = self.parse() # then parse inside that parenthesis
            if self.peek() != ')': # we expect the parenthesis to be closed after
                raise Exception("No closing parenthesis foundat position {}".format(self.index))
            self.index += 1
            return value # return result
        else:
            return self.negative() # call negative, will return the next value

    """negative()
    Get the negative of the value
    
    Returns
    --------
    float or int: Result
    """
    def negative(self : Calc) -> int|float:
        if self.peek() == '-': # if minus, multiply next value with -1
            self.index += 1
            return -1 * self.parenthesis()
        else: # else return next value
            return self.value()

    """value()
    Get the value of the next element
    
    Returns
    --------
    float or int: Result
    """
    def value(self : Calc) -> int|float:
        if self.peek() in '0123456789.': # check if digit or dot
            return self.number()
        else: # else expect variable or function
            return self.variable_or_function()

    """variable_or_function()
    Get the result of a variable or a function
    
    Raises
    ------
    Exception: Error during the parsing
    
    Returns
    --------
    float or int: Result
    """
    def variable_or_function(self : Calc) -> int|float:
        var : str = ''
        while self.isNotDone(): # retrieve var/func name
            c : str = self.peek()
            if c.lower() in '_abcdefghijklmnopqrstuvwxyz0123456789':
                var += c
                self.index += 1
            else:
                break
        
        value : float|None = self.vars.get(var, None) # check if variable
        if value == None: # it's not
            # check if function
            if var not in self.FUNCS:
                raise Exception("Unrecognized variable '{}'".format(var))
            else:
                # parse func parameter
                param : int|float = self.parenthesis()
                match var: # call function for that parameter
                    case 'cos': value = math.cos(param)
                    case 'sin': value = math.sin(param)
                    case 'tan': value = math.tan(param)
                    case 'acos': value = math.acos(param)
                    case 'asin': value = math.asin(param)
                    case 'atan': value = math.atan(param)
                    case 'cosh': value = math.cosh(param)
                    case 'sinh': value = math.sinh(param)
                    case 'tanh': value = math.tanh(param)
                    case 'acosh': value = math.acosh(param)
                    case 'asinh': value = math.asinh(param)
                    case 'atanh': value = math.atanh(param)
                    case 'exp': value = math.exp(param)
                    case 'ceil': value = math.ceil(param)
                    case 'floor': value = math.floor(param)
                    case 'round': value = math.floor(param)
                    case 'abs': value = math.fabs(param)
                    case 'trunc': value = math.trunc(param)
                    case 'log':
                        if param <= 0: raise Exception("Can't evaluate the logarithm of '{}'".format(param))
                        value = math.log(param)
                    case 'log2':
                        if param <= 0: raise Exception("Can't evaluate the logarithm of '{}'".format(param))
                        value = math.log2(param)
                    case 'log10':
                        if param <= 0: raise Exception("Can't evaluate the logarithm of '{}'".format(param))
                        value = math.log10(param)
                    case 'sqrt': value = math.sqrt(param)
                    case 'rad': value = math.radians(param)
                    case 'deg': value = math.degrees(param)
                    case _: raise Exception("Unrecognized function '{}'".format(var))
        # return result
        return float(value)

    """number()
    Return a numerical value
    
    Raises
    ------
    Exception: Error during the parsing
    
    Returns
    --------
    float or int: Result
    """
    def number(self : Calc) -> int|float:
        strValue : list[str] = []
        decimal_found : bool = False
        c : str = ''
        # read number
        while self.isNotDone():
            c = self.peek()
            if c == '.':
                if decimal_found:
                    raise Exception("Found an extra period in a numberat position {}".format(self.index))
                decimal_found = True
                strValue.append('.')
            elif c in '0123456789':
                strValue.append(c)
            else:
                break
            self.index += 1
        # error check
        if len(strValue) == 0:
            if c == '': raise Exception("Unexpected end found\nDid you perhaps forget a bracket?\nExample: `log(20)` not `log 20`")
            else: raise Exception("Unexpected end found\nA value was expectedat position {}".format(self.index))
        return float("".join(strValue))