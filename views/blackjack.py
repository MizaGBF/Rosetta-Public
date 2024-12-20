from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.singleton import GameCard
    # Type Aliases
    import types
    CardList : types.GenericAlias = list[GameCard]
    Hand : types.GenericAlias = list[int|CardList]
import random

# ----------------------------------------------------------------------------------------------------------------
# Blackjack View
# ----------------------------------------------------------------------------------------------------------------
# View class used for the blackjack minigame
# ----------------------------------------------------------------------------------------------------------------

class Blackjack(BaseView):
    # player states
    PLAYING : int = 0
    STOPPED : int = 1
    BLACKJACK : int = 2
    TWENTYONE : int = 3
    LOST : int = 4

    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    players: list of Players
    embed: disnake.Embed to edit
    """
    def __init__(self : Blackjack, bot : DiscordBot, players : list[disnake.User|disnake.Member], embed : disnake.Embed) -> None:
        super().__init__(bot, timeout=240)
        # game state
        self.state : int = 0
        # player list
        self.players : list[disnake.User|disnake.Member] = players
        # add bot to the player list if there are space
        if len(self.players) < 6:
            self.players.append(self.bot.user)
        # shuffle player order
        random.shuffle(self.players)
        # the view embed
        self.embed : disnake.Embed = embed
        # build a deck (A card is a tuple: (Card strength[1-13], Card suit[0-4])
        self.deck : CardList = [self.bot.singleton.get_GameCard((i % 13) + 1, i // 13) for i in range(51)]
        # shuffle the deck
        random.shuffle(self.deck)
        # make hands and give one card to each player
        self.hands : list[Hand] = [[self.PLAYING, [self.deck.pop()]] for i in range(len(self.players))] # player state, cards
        # Start
        # If the player to start is the bot, call play ai
        if self.players[self.state].id == self.bot.user.id:
            self.playai()
        # Then the player in slot 0 will play
        self.notification : str = "Turn of **{}**".format(self.players[self.state].display_name)

    """renderHand()
    Generate a Hand string for the given hand
    
    Parameters
    ----------
    hand: one list of card from self.hands
    playing: boolean, True if it's the currently playing user
    
    Returns
    ----------
    list: resulting list of strings to add to a message list
    """
    def renderHand(self : Blackjack, hand : Hand, playing : bool) -> str:
        msgs : list[str] = []
        score : int = self.computeScore(hand[1])
        for card in hand[1]: # display each card
            msgs.append(str(card))
            msgs.append(", ")
        if playing: # if the player is playing
            msgs.append("🎴") # add hidden card
        else:
            msgs.pop(-1) # remove last comma
        # add score to message
        msgs.append(" ▫️")
        match hand[0]:
            case self.PLAYING: msgs.append(" Score is **{}**".format(score))
            case self.STOPPED: msgs.append(" Stopped at **{}**".format(score))
            case self.BLACKJACK: msgs.append(" **Blackjack**")
            case self.TWENTYONE: msgs.append(" Reached **21**")
            case self.LOST: msgs.append(" **Lost**")
        return msgs

    """getWinner()
    Generate a string indicating who won the game

    Returns
    ----------
    str: resulting string
    """
    def getWinner(self : Blackjack) -> str:
        winner : list[disnake.User|disnake.Member] = []
        best : int = 0
        i : int
        p : disnake.User|disnake.Member
        for i, p in enumerate(self.players):
            if self.hands[i][0] == self.LOST: # this player lost anyway, skip
                continue
            else:
                score : int = self.computeScore(self.hands[i][1])
                if score == 21 and len(self.hands[i][1]) == 2:
                    score = 22 # blackjack, set to 22 to ensure it's considered higher than regular 21
                if score == best: # if it's equal to the best score
                    winner.append(p) # add player to winner list
                elif score > best: # else if it's greater than the best score
                    winner = [p] # set the winner list to this player
                    best = score # and the best score to this player
        # process winner list
        match len(winner):
            case 0: # no winners
                return "No one won"
            case 1: # one winner
                return "**{}** is the winner".format(winner[0].display_name)
            case _: # multiple winners
                msgs : list[str] = ["It's a **draw** between "]
                for p in winner:
                    msgs.append(p.display_name)
                    msgs.append(", ")
                return "".join(msgs[:-1])

    """update()
    Update the embed
    
    Parameters
    ----------
    inter : an interaction
    init: if True, it uses a different method (only used from the command call itself)
    """
    async def update(self : Blackjack, inter : disnake.Interaction, init : bool = False) -> None:
        desc : list[str] = []
        # iterate over player
        i : int
        p : disnake.User|disnake.Member
        for i, p in enumerate(self.players):
            # and display their hand and score
            desc.append(str(self.bot.emote.get(str(i+1))))
            desc.append(" ")
            desc.append(p.display_name if len(p.display_name) <= 10 else p.display_name[:10] + "...")
            desc.append(" ▫️ ")
            desc.extend(self.renderHand(self.hands[i], (i == self.state)))
            desc.append("\n")
        # add notification line
        desc.append(self.notification)
        # update embed
        self.embed.description = "".join(desc)
        # set message
        if init:
            await inter.edit_original_message(embed=self.embed, view=self) # init is true, we edit
        elif self.state >= 0:
            await inter.response.edit_message(embed=self.embed, view=self) # game is on going
        else:
            await inter.response.edit_message(embed=self.embed, view=None) # game is over, remove the view

    """computeScore()
    Calculate the score of the given hand
    
    Parameters
    ----------
    cards: List, a list of card tuples
    
    Returns
    ----------
    int: The score
    """
    def computeScore(self : Blackjack, cards : CardList) -> int:
        score : int = 0
        card: GameCard
        for card in cards:
            if card.value == 1 and score < 11: # ace
                score += 11
            elif card.value >= 10: # head
                score += 10
            else:
                score += card.value
        return score

    """playai()
    The logic for the bot to play the game
    """
    def playai(self : Blackjack) -> None:
        score : int = self.computeScore(self.hands[self.state][1])
        # act depending on score
        if score < 12: # score is 11 or less
            self.play(False) # keep playing
        else:
            if score >= 19: # score is 19~20
                self.play(True) # stop
            if score >= 17: # score is 17~18
                self.play(random.randint(1, 100) > 10) # 10% chance to continue
            elif score >= 15: # score is 15~16
                self.play(random.randint(1, 100) > 40) # 40% chance to continue
            else: # score is 12~14
                self.play(random.randint(1, 100) > 80) # 80% chance to continue

    """play()
    Allow the player to make a move
    
    Parameters
    ----------
    stop: boolean, True for the player to stop, False to draw a card
    """
    def play(self : Blackjack, stop : bool) -> None:
        if self.state == -1: # check if game is over
            return
        if stop: # set player as stopped
            self.hands[self.state][0] = self.STOPPED
        else: # continue
            # draw card
            self.hands[self.state][1].append(self.deck.pop())
            # compute score
            score : int = self.computeScore(self.hands[self.state][1])
            # game over checks
            if score == 21: # reached max
                if len(self.hands[self.state][1]) == 2: # only 2 cards, blackjack
                    self.hands[self.state][0] = self.BLACKJACK
                else:
                    self.hands[self.state][0] = self.TWENTYONE # reached 21 state
            elif score > 21: # over max
                self.hands[self.state][0] = self.LOST # lost
        # look for next player
        self.lookupNextPlayerTurn()
        # check if we're still playing AND if it's the bot turn to play
        if self.state >= 0 and self.players[self.state].id == self.bot.user.id and self.hands[self.state][0] == self.PLAYING:
            self.playai()

    """lookupNextPlayerTurn()
    Cycle over the players until the next one in line able to play, to update the game state
    Stop the game if no players can play.
    """
    def lookupNextPlayerTurn(self : Blackjack) -> None:
        current_state : int = self.state
        while True:
            # go to next player
            self.state = (self.state + 1) % len(self.players)
            # check player state
            if self.hands[self.state][0] == self.PLAYING: # is playing, good
                return
            elif current_state == self.state: # it's the player we started with and they can't play, this means we did a full loop without finding a player able to play, i.e. GAME IS OVER
                self.state = -1 # game over
                return

    """buttoncallback()
    Callback for buttons
    
    Parameters
    ----------
    interaction: a Discord interaction
    action: boolean used for self.play()
    """
    async def buttoncallback(self : Blackjack, interaction: disnake.Interaction, action: bool) -> None:
        if self.state >= 0 and self.players[self.state].id == interaction.user.id: # check if the game is on going and if the interaction author is the current player
            self.play(action) # do the action corresponding to the button (True = stop, False = draw)
            # Check if the game is over and print status accordingly
            if self.state >= 0:
                self.notification = "Turn of **{}**".format(self.players[self.state].display_name)
            else:
                self.notification = self.getWinner()
                self.stopall()
            # update display
            await self.update(interaction)
        else:
            await interaction.response.send_message("It's not your turn to play or you aren't the player", ephemeral=True)

    """draw()
    The draw button coroutine callback.
    Allow the player to draw a card.
    
    Parameters
    ----------
    button: the Discord button
    interaction: a Discord interaction
    """
    @disnake.ui.button(label='Draw Card', style=disnake.ButtonStyle.success)
    async def draw(self : Blackjack, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        await self.buttoncallback(interaction, False)

    """giveup()
    The stop button coroutine callback.
    Allow the player to stop.
    
    Parameters
    ----------
    button: the Discord button
    interaction: a Discord interaction
    """
    @disnake.ui.button(label='Stop', style=disnake.ButtonStyle.danger)
    async def giveup(self : Blackjack, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        await self.buttoncallback(interaction, True)