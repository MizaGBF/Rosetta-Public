from __future__ import annotations
import disnake
from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from dataclasses import dataclass
from datetime import datetime

# ----------------------------------------------------------------------------------------------------------------
# Singleton Component
# ----------------------------------------------------------------------------------------------------------------
# This component manages singletons found in this file
# ----------------------------------------------------------------------------------------------------------------

class Singleton():
    def __init__(self : Singleton, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot

    def init(self : Singleton) -> None:
        pass

    """make_and_send_modal()
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
    async def make_and_send_modal(self : Singleton, inter : disnake.Interaction, custom_id : str, title : str, callback : Callable, components : list, extra : str = None) -> CustomModal:
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
        index = value << 8 + suit # calculate index
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
    def make_Score(self : Singleton, type : int|None, ver : int|None, gw : int|None) -> Score:
        return Score(type, ver, gw)

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

# ----------------------------------------------------------------------------------------------------------------
# Below are the singletons
# ----------------------------------------------------------------------------------------------------------------

"""CustomModal
A Modal class where you can set your own callback
"""
class CustomModal(disnake.ui.Modal):
    def __init__(self, bot : 'DiscordBot', title : str, custom_id : str, components : list, callback : Callable, extra : str = None) -> None:
        super().__init__(title=title, custom_id=custom_id, components=components)
        self.bot : 'DiscordBot' = bot # bot reference
        self.custom_callback = callback # our callback
        self.extra = extra # any extra info we can pass here. will be accessible from the interaction in the callback

    async def on_error(self, error: Exception, inter : disnake.ModalInteraction) -> None:
        await inter.response.send_message(embed=self.bot.embed(title="Error", description="An unexpected error occured, my owner has been notified"))
        self.bot.logger.pushError("[MODAL] 'on_error' event:", error)

    async def callback(self, inter : disnake.ModalInteraction) -> None:
        await self.custom_callback(self, inter) # trigger the callback

"""GameCard
Standard card representation for card games
"""
@dataclass(frozen=True, slots=True)
class GameCard():
    value : int
    suit : int
    strings : list[str]

    @classmethod
    def make_card(cls : GameCard, value: int, suit: int) -> GameCard:
        value = value # value ranges from 1 (ace) to 13 (king) or 14 (ace)
        suit = suit # suit ranges from 0 to 3
        strings = [None, None, None] # value, suit, complete
        # set strings
        # value
        match value:
            case 1|14: strings[0] = "A"
            case 11: strings[0] = "J"
            case 12: strings[0] = "Q"
            case 13: strings[0] = "K"
            case _: strings[0] = str(value)
        # suit
        match suit:
            case 0: strings[1] = "\♦️"
            case 1: strings[1] = "\♦️"
            case 2: strings[1] = "\♥️"
            case 3: strings[1] = "\♣️"
        strings[2] = "".join(strings[:2])
        return cls(value, suit, strings)

    def __repr__(self : GameCard) -> str: 
        return self.strings[2]

    def __str__(self : GameCard) -> str:
        return self.strings[2]

    def __int__(self : GameCard) -> int:
        return self.value

    def __lt__(self : GameCard, other : GameCard) -> bool:
         return self.value < other.value

    def getStringValue(self : GameCard) -> str:
        return self.strings[0]

    def getStringSuit(self : GameCard) -> str:
        return self.strings[1]

"""Score
Store a score for a Guild War participant/crew
"""
@dataclass(slots=True)
class Score(): # GW Score structure
    type : int
    ver : int # database version
    gw : int # gw id
    ranking : int # ranking
    id : int # crew/player id
    name : str
    # scores
    current : int # will match preliminaries or total1-4
    current_day : int # current day. 0 : int = prelims, 1-4 : int = day 1-4
    day : int
    preliminaries : int
    day1 : int
    total1 : int
    day2 : int
    total2 : int
    day3 : int
    total3 : int
    day4 : int
    total4 : int
    # speed
    top_speed : int
    current_speed : int
    
    def __init__(self : Score, type : int|None = None, ver : int|None = None, gw : int|None = None) -> None:
        self.type = type # crew or player
        self.ver = ver # database version
        self.gw = gw # gw id
        self.ranking = None # ranking
        self.id = None # crew/player id
        self.name = None
        # scores
        self.current = None # will match preliminaries or total1-4
        self.current_day = None # current day. 0 = prelims, 1-4 = day 1-4
        self.day = None
        self.preliminaries = None
        self.day1 = None
        self.total1 = None
        self.day2 = None
        self.total2 = None
        self.day3 = None
        self.total3 = None
        self.day4 = None
        self.total4 = None
        # speed
        self.top_speed = None
        self.current_speed = None

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