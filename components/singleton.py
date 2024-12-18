from __future__ import annotations
import disnake
from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.ranking import CrewDataEntry, PlayerDataEntry
from dataclasses import dataclass
from datetime import datetime

# ----------------------------------------------------------------------------------------------------------------
# Singleton Component
# ----------------------------------------------------------------------------------------------------------------
# This component manages singletons found in this file
# ----------------------------------------------------------------------------------------------------------------

class Singleton():
    def __init__(self : Singleton, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

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