from __future__ import annotations
from . import BaseView
import disnake
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.util import GameCard
    from . import User
    # Type Aliases
    type CardList = list[GameCard]
    type Hand = list[int|CardList]
from enum import IntEnum
import random


# General enum
class Constant(IntEnum):
    CARD_1_HOLD : int = 0b001
    CARD_2_HOLD : int = 0b010
    CONFIRMED   : int = 0b100

    BUTTON_CONFIRM : int = 0
    BUTTON_CARD_1 : int = 1
    BUTTON_CARD_2 : int = 2


# ----------------------------------------------------------------------
# Poker View
# ----------------------------------------------------------------------
# View class used to play Poker
# PokerSub is for ephemeral messages
# ----------------------------------------------------------------------

class PokerSub(BaseView):

    __slots__ = ("parent")

    """__init__()
    Constructor

    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    parent: the Poker view
    """
    def __init__(self : PokerSub, bot : DiscordBot, parent : Poker) -> None:
        super().__init__(bot, timeout=120)
        self.parent : Poker = parent # Poker view

    """do()
    Coroutine called by buttons

    Parameters
    ----------
    interaction: the button interaction
    mode: 0 = confirm, 1 = toggle card 1, 2 = toggle card 2
    """
    async def do(self : PokerSub, interaction: disnake.Interaction, mode : int) -> None:
        i : int
        p : disnake.User|disnake.Member
        for i, p in enumerate(self.parent.players): # search for player
            if p.id == interaction.user.id:
                break
        if self.parent.hands[i][0] & Constant.CONFIRMED == Constant.CONFIRMED:
            await interaction.response.send_message("You can't modify your choice", ephemeral=True)
            return
        match mode:
            case Constant.BUTTON_CONFIRM: # confirm button
                # check held card
                if self.parent.hands[i][0] & Constant.CARD_1_HOLD == 0: # card 1 isn't held
                    self.parent.hands[i][1][0] = self.parent.deck.pop() # draw new
                if self.parent.hands[i][0] & Constant.CARD_2_HOLD == 0: # card 2 isn't held
                    self.parent.hands[i][1][1] = self.parent.deck.pop() # draw new
                # set state to confirmed
                self.parent.hands[i][0] = self.parent.hands[i][0] | Constant.CONFIRMED
                # update message
                self.parent.updateSubEmbed(i)
                await interaction.response.edit_message(embed=self.parent.subembeds[i], view=None)
                # check if all players confirmed
                for h in self.parent.hands:
                    if h[0] & Constant.CONFIRMED == 0:
                        return # if one hasn't, stop
                # all confirmed, disable this sub view and change parent to state 1
                self.stopall()
                self.parent.stopall()
                self.parent.state = 1
            case Constant.BUTTON_CARD_1: # card 1
                # toggle bit
                self.parent.hands[i][0] = self.parent.hands[i][0] ^ Constant.CARD_1_HOLD
                # update message
                self.parent.updateSubEmbed(i)
                await interaction.response.edit_message(embed=self.parent.subembeds[i], view=self)
            case Constant.BUTTON_CARD_2: # card 2
                # toggle bit
                self.parent.hands[i][0] = self.parent.hands[i][0] ^ Constant.CARD_2_HOLD
                # update message
                self.parent.updateSubEmbed(i)
                await interaction.response.edit_message(embed=self.parent.subembeds[i], view=self)

    @disnake.ui.button(label='Toggle Card 1', style=disnake.ButtonStyle.success)
    async def holdcard1(self : PokerSub, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if self.parent.state == 0: # card selection stage
            await self.do(interaction, Constant.BUTTON_CARD_1)
        else:
            await interaction.response.send_message("The game is over", ephemeral=True)

    @disnake.ui.button(label='Toggle Card 2', style=disnake.ButtonStyle.success)
    async def holdcard2(self : PokerSub, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if self.parent.state == 0: # card selection stage
            await self.do(interaction, Constant.BUTTON_CARD_2)
        else:
            await interaction.response.send_message("The game is over", ephemeral=True)

    @disnake.ui.button(label='Confirm', style=disnake.ButtonStyle.danger)
    async def confirm(self : PokerSub, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if self.parent.state == 0: # card selection stage
            await self.do(interaction, Constant.BUTTON_CONFIRM)
        else:
            await interaction.response.send_message("The game is over", ephemeral=True)


class Poker(BaseView):
    ROYAL_FLUSH_SET : set[str] = {"10", "11", "12", "13", "14"}
    STRAIGTH_SET : set[str] = {"14", "2", "3", "4", "5"}
    FULL_HOUSE_SET : set[int] = {2, 3}
    FOUR_KIND_SET : set[int] = {1, 4}
    THREE_KIND_SET : set[int] = {1, 3}
    DOUBLE_PAIR_LIST : list[int] = [1, 2, 2]

    __slots__ = (
        "state", "players", "embed", "color", "deck",
        "dealer", "min_value", "hands", "sub", "subembeds",
        "max_state", "winners", "remaining"
    )

    """__init__()
    Constructor

    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    players: list of Players
    embed: disnake.Embed to edit
    remaining: integer, remaining number of rounds, put 0 to ignore the round system
    """
    def __init__(
        self : Poker,
        bot : DiscordBot,
        players : list[User],
        embed : disnake.Embed,
        remaining : int = 0
    ) -> None:
        super().__init__(bot, timeout=120)
        self.state : int = 0 # game state, -1 = over, 0~N player turn
        self.players : list[User] = players # player list
        self.embed : disnake.Embed = embed # embed to updae
        # build a deck (A card is a tuple: (Card strength[1-13], Card suit[0-4])
        self.deck : CardList = [self.bot.singleton.get_GameCard((i % 13) + 2, i // 13) for i in range(51)]
        # shuffle the deck
        random.shuffle(self.deck)
        # draw 3 cards for the dealer
        self.dealer : CardList = [self.deck.pop(), self.deck.pop(), self.deck.pop()]
        # get dealer minimum hand value
        self.min_value : int = Poker.calculateMinValue(self.dealer) # dealer hand value
        # set player hands
        # Format is: state, hand (currently 2 cards)
        self.hands : list[Hand] = [
            [
                Constant.CARD_1_HOLD | Constant.CARD_2_HOLD,
                [self.deck.pop(), self.deck.pop()]
            ] for i in range(len(self.players))]
        # set sub view to select cards
        self.sub : PokerSub = PokerSub(self.bot, self)
        # set sub embeds
        self.subembeds : list[disnake.Embed] = []
        i : int
        p : disnake.User|disnake.Member
        for i, p in enumerate(self.players):
            self.subembeds.append(
                self.bot.embed(
                    title=f"♠️ {p.display_name}'s hand ♥",
                    description="Initialization",
                    color=self.embed.color
                )
            )
            self.updateSubEmbed(i)
        # the max number of cards to draw
        self.max_state : int = 3 + len(self.players) * 2 # 3 from dealer, 2 for each player
        # winner list
        self.winners : list[disnake.User|disnake.Member] = []
        # remaining rounds
        self.remaining : int = remaining

    """update()
    Update the embed

    Parameters
    ----------
    inter: an interaction
    init: if True, it uses a different method (only used from the command call itself)
    """
    async def update(self : Poker, inter : disnake.Interaction, init : bool = False) -> None:
        desc : list[str] = await self.renderTable()
        # check game state
        if self.state == 0: # start
            desc.append("Waiting for all players to make their choices")
        elif self.state >= self.max_state - 1: # card reveal reached the end
            match len(self.winners):
                case 0:
                    pass # shouldn't happen
                case 1: # 1 winner
                    desc.append(f"**{self.winners[0].display_name}** is the winner")
                case _: # draw
                    desc.append("It's a **draw** between ")
                    for p in self.winners:
                        desc.append(p.display_name)
                        desc.append(", ")
                    desc.pop(-1)
            # add remaining rounds
            match self.remaining:
                case 0:
                    pass
                case 1: # that was the final one
                    desc.append("\n*Please wait for the results*")
                case _:
                    desc.append("\n*Next round in 10 seconds...*")
        # set embed
        self.embed.description = "".join(desc)
        if init:
            # Note: ping players
            self.message = await inter.followup.send(
                content=self.bot.util.players2mentions(self.players),
                embed=self.embed,
                view=self
            ) # init is true, we edit
        elif self.state >= 0:
            await self.message.edit(embed=self.embed, view=None) # game is on going
        else:
            await self.message.edit(embed=self.embed, view=self) # game is over, remove the view

    """renderTable()
    Render the table (dealer and player hands) according to the game state

    Returns
    ----------
    list: List of strings for the embed description
    """
    async def renderTable(self : Poker) -> list:
        # init message
        desc : list[str] = [":spy: Dealer ▫️ ", str(self.dealer[0]), ", "]
        # dealer card 2
        if self.state < 1:
            desc.append("🎴, ")
        else:
            desc.append(str(self.dealer[1]))
            desc.append(", ")
        # dealer card 3
        if self.state < 2:
            desc.append("🎴\n")
        else:
            desc.append(str(self.dealer[2]))
            desc.append("\n")

        s : int = self.state - 3 # state WITHOUT the dealer draw steps
        self.winners = [] # list of winners
        best : int = 0
        i : int
        p : disnake.User|disnake.Member
        for i, p in enumerate(self.players): # write a line for each player
            desc.append(str(self.bot.emote.get(str(i + 1)))) # number
            desc.append(" ")
            desc.append(p.display_name if len(p.display_name) <= 10 else p.display_name[:10] + "...") # name
            desc.append(" ▫️ ")

            if s < 0: # dealer draw stage
                desc.append("🎴, 🎴\n") # nothing revealed
            elif s == 0: # 1st card revealed
                desc.append(str(self.hands[i][1][0])) # card 1 revealed
                desc.append(", 🎴\n")
            else:
                desc.append(str(self.hands[i][1][0])) # card 1 revealed
                desc.append(", ")
                desc.append(str(self.hands[i][1][1])) # card 2 revealed
                desc.append(", ")
                score : int
                scorestr : str
                score, scorestr = Poker.checkPokerHand(self.dealer + self.hands[i][1])
                desc.append(scorestr)
                await asyncio.sleep(0)
                if score <= self.min_value: # check if total hand is inferior to dealer value
                    highestCard = Poker.highestCard(self.hands[i][1])
                    score = int(highestCard) # set score to highest card
                    desc.append(", Best in hand is **")
                    desc.append(highestCard.getStringValue()) # add highest mention
                    desc.append("**")
                desc.append("\n")
                if score > best: # best score among players so far
                    best = score
                    self.winners = [p] # set this player to winner list
                elif score == best: # equal to best score so far
                    self.winners.append(p) # add this player to winner list
            s -= 2
        return desc

    """control()
    The button making the PokerSub view appears.
    Allow the player to manage their cards.

    Parameters
    ----------
    button: the Discord button
    interaction: a Discord interaction
    """
    @disnake.ui.button(label='See Your Hand', style=disnake.ButtonStyle.primary)
    async def control(self : Poker, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        i : int|None = None
        idx : int
        p : disnake.User|disnake.Member
        for idx, p in enumerate(self.players): # search which player used this button
            if p.id == interaction.user.id:
                i = idx
                break
        if self.state == 0 and i is not None: # show them their hand
            await interaction.response.send_message(embed=self.subembeds[i], view=self.sub, ephemeral=True)
        else:
            await interaction.response.send_message("You can't play this game", ephemeral=True)

    """updateSubEmbed()
    Update an user embed

    Parameters
    ----------
    index: Player index
    """
    def updateSubEmbed(self : Poker, index : int) -> None:
        has_confirmed : bool = self.hands[index][0] & Constant.CONFIRMED == Constant.CONFIRMED
        self.subembeds[index].description = [
            str(self.bot.emote.get("1")),
            " ",
            str(self.hands[index][1][0]),
            " ",
            "",
            "\n",
            str(self.bot.emote.get("2")),
            " ",
            str(self.hands[index][1][1]),
            " ",
            "",
            "\n"
        ]
        # Add card selections
        if self.hands[index][0] & Constant.CARD_1_HOLD == Constant.CARD_1_HOLD:
            if not has_confirmed:
                self.subembeds[index].description[4] = "**Hold**"
        elif not has_confirmed:
            self.subembeds[index].description[4] = "*Exchange*"
        else:
            self.subembeds[index].description[4] = "*Exchanged*"
        if self.hands[index][0] & Constant.CARD_2_HOLD == Constant.CARD_2_HOLD:
            if not has_confirmed:
                self.subembeds[index].description[10] = "**Hold**"
        elif not has_confirmed:
            self.subembeds[index].description[10] = "*Exchange*"
        else:
            self.subembeds[index].description[10] = "*Exchanged*"
        # Add confirm message
        if has_confirmed:
            self.subembeds[index].description.append("**Your hand is locked**\nYou can dismiss this message")
        # Merge strings
        self.subembeds[index].description = "".join(self.subembeds[index].description)

    """playRound()
    Coroutine to play the round
    """
    async def playRound(self : Poker) -> None:
        while self.state < self.max_state:
            await asyncio.sleep(1)
            await self.update(None)
            self.state += 1

    """calculateMinValue()
    Returns the value of the dealt cards

    Parameters
    ----------
    dealer: List of card to check

    Returns
    --------
    int : Strength value
    """
    def calculateMinValue(dealer : CardList) -> int:
        value_counts : dict[int, int] = {}
        for card in dealer:
            value_counts[card.value] = value_counts.get(card.value, 0) + 1
        if 3 in value_counts.values():
            return 300 + int(Poker.highestCardForOccurence(dealer, value_counts, 3))
        elif 2 in value_counts.values():
            return 100 + int(Poker.highestCardForOccurence(dealer, value_counts, 2))
        return int(Poker.highestCard(dealer))

    """checkPokerHand()
    Static function
    Check a poker hand strength

    Parameters
    ----------
    hand: List of card to check

    Returns
    --------
    tuple:
        - int : Hand strength value
        - str: Hand string
    """
    def checkPokerHand(hand : CardList) -> tuple:
        # flush detection
        flush : bool = len({card.suit for card in hand}) == 1 # if only one suit found in hand
        # variables needed for hand checks
        values : list[int] = [card.value for card in hand] # get card values
        value_counts : dict[int, int] = {}
        for v in values: # count occurences of each value (for example, 3 kings -> value_counts[13] = 3 )
            value_counts[v] = value_counts.get(v, 0) + 1
        sorted_values : list[int] = sorted(value_counts.values()) # sorted values
        counts_set : set[int] = set(sorted_values) # the unique values of value_counts
        value_range : int = max(values) - min(values) # get the difference between highest and lowest card
        highest_card : GameCard = Poker.highestCard(hand) # get highest card (for later use)
        card : GameCard
        # determinate hand strength
        # checks happen in strength order, from highest to lowest
        if flush and set(values) == Poker.ROYAL_FLUSH_SET: # flush and royal flush set match
            return 1000, "**Royal Straight Flush**"
        elif flush and ((len(counts_set) == 1 and (value_range == 4)) or set(values) == Poker.STRAIGTH_SET):
            # flush and ((all values are unique and the range between highest and lowest is 4)
            # or it matches STRAIGTH_SET)
            return f"**Straight Flush, high {highest_card.getStringValue()}**"
        elif counts_set == Poker.FOUR_KIND_SET:
            card = Poker.highestCardForOccurence(hand, value_counts, 4)
            return 700 + int(card), f"**Four of a Kind of {card.getStringValue()}**"
        elif counts_set == Poker.FULL_HOUSE_SET:
            return 600 + int(highest_card), f"**Full House, high {highest_card.getStringValue()}**"
        elif flush:
            return 500 + int(highest_card), f"**Flush, high {highest_card.getStringValue()}**"
        elif (len(counts_set) == 1 and (value_range == 4)) or set(values) == Poker.STRAIGTH_SET:
            # (all values are unique and the range between highest and lowest is 4)
            # or it matches STRAIGTH_SET
            return 400 + int(highest_card), f"**Straight, high {highest_card.getStringValue()}**"
        elif counts_set == Poker.THREE_KIND_SET:
            card = Poker.highestCardForOccurence(hand, value_counts, 3)
            return 300 + int(card), f"**Three of a Kind of {card.getStringValue()}**"
        elif sorted_values == Poker.DOUBLE_PAIR_LIST:
            card = Poker.highestCardForOccurence(hand, value_counts, 2)
            return 200 + int(card), f"**Two Pairs, high {card.getStringValue()}**"
        elif 2 in counts_set:
            card = Poker.highestCardForOccurence(hand, value_counts, 2)
            return 100 + int(card), f"**Pair of {card.getStringValue()}**"
        else:
            return int(highest_card), f"**Highest card is {highest_card.getStringValue()}**"

    """highestCardForOccurence()
    Static function
    Look for a card which is present N number of time in the selection

    Parameters
    ----------
    selection: List of cards to check
    occurences: Dict, a dictionary of pair (card value: occurence of this value)
    occurence: Integer, the occurence to check for

    Returns
    --------
    GameCard: A matching card or None if none is found
    """
    def highestCardForOccurence(selection : CardList, occurences : dict[int, int], occurence : int) -> GameCard|None:
        # get the highest value matching the asked occurence
        bestval : int|None = None
        val : int
        ocu : int
        for val, ocu in occurences.items():
            if ocu == occurence and (bestval is None or val > bestval):
                bestval = val
        if bestval is not None:
            # return a matching card
            card : GameCard
            for card in selection:
                if card.value == bestval:
                    return card
        return None

    """highestCard()
    Static function
    Return the highest card in the list

    Parameters
    ----------
    selection: List of cards to check

    Returns
    --------
    GameCard: Highest card
    """
    def highestCard(selection : CardList) -> GameCard:
        cards : CardList = selection.copy()
        cards.sort()
        return cards[-1]
