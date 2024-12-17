import disnake
from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from dataclasses import dataclass

# ----------------------------------------------------------------------------------------------------------------
# Singleton Component
# ----------------------------------------------------------------------------------------------------------------
# This component manages singletons found in this file
# ----------------------------------------------------------------------------------------------------------------

class Singleton():
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot

    def init(self) -> None:
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
    async def make_and_send_modal(self, inter : disnake.Interaction, custom_id : str, title : str, callback : Callable, components : list, extra : str = None) -> disnake.ModalInteraction:
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
    def get_GameCard(self, value : int, suit : int) -> 'GameCard':
        if value < 1 or value > 14:
            raise Exception("Invalid GameCard value")
        elif suit < 0 or suit > 3:
            raise Exception("Invalid GameCard suit")
        index = value << 8 + suit # calculate index
        if index not in self.gamecard_cache: # add card in cache if it doesn't exist
            self.gamecard_cache[index] = GameCard.make_card(value, suit)
        return self.gamecard_cache[index]

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

    async def on_error(self, error: Exception, inter: disnake.ModalInteraction) -> None:
        await inter.response.send_message(embed=self.bot.embed(title="Error", description="An unexpected error occured, my owner has been notified"))
        self.bot.logger.pushError("[MODAL] 'on_error' event:", error)

    async def callback(self, inter: disnake.ModalInteraction) -> None:
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
    def make_card(cls, value: int, suit: int):
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

    def __repr__(self) -> str: 
        return self.strings[2]

    def __str__(self) -> str:
        return self.strings[2]

    def __int__(self) -> int:
        return self.value

    def __lt__(self, other : 'GameCard') -> bool:
         return self.value < other.value

    def getStringValue(self) -> str:
        return self.strings[0]

    def getStringSuit(self) -> str:
        return self.strings[1]