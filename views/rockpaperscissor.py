from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
import random

# ----------------------------------------------------------------------------------------------------------------
# RPS View
# ----------------------------------------------------------------------------------------------------------------
# View class used to play Rock Paper Scissor
# ----------------------------------------------------------------------------------------------------------------

class RPS(BaseView):
    # Picks
    ROCK : int = 0
    PAPER : int = 1
    SCISSOR : int = 2
    # Strings for results
    PICK_STRINGS : list[str] = [
        "🪨 **Rock**",
        "🧻 **Paper**",
        "✂️ **Scissor**"
    ]
    # Indexes
    DRAW : int = -1
    PLAYER_1 : int = 0
    PLAYER_2 : int = 1
    # Pick combinations and results
    WIN_STATES : dict[int, int] = {
        ROCK*10+ROCK : DRAW,
        PAPER*10+ROCK : PLAYER_1,
        SCISSOR*10+ROCK : PLAYER_2,
        ROCK*10+PAPER : PLAYER_2,
        PAPER*10+PAPER : DRAW,
        SCISSOR*10+PAPER : PLAYER_1,
        ROCK*10+SCISSOR : PLAYER_1,
        PAPER*10+SCISSOR : PLAYER_2,
        SCISSOR*10+SCISSOR : DRAW
    }
    
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    players: list of Players
    embed: disnake.Embed to edit
    scores: list, current player scores
    target: number of round won to win
    """
    def __init__(self : RPS, bot : DiscordBot, players : list[disnake.User|disnake.Member], embed : disnake.Embed, scores : list[int], target : int) -> None:
        super().__init__(bot, timeout=60)
        self.players : list[disnake.User|disnake.Member] = players # player list
        self.embed : disnake.Embed = embed # embed to update
        self.scores : list[int] = scores # global score
        self.target : int = target # best of X wins
        self.state : list[int] = [-1, -1] # players selection
        self.won : bool = False # game state

    """update()
    Update the embed
    
    Parameters
    ----------
    inter: an interaction
    init: if True, it uses a different method (only used from the command call itself)
    """
    async def update(self : RPS, inter : disnake.Interaction, init : bool = False) -> None:
        if not self.won: # if the game is on going
            desc : list[str] = []
            if self.state[self.PLAYER_1] == -1 or self.state[self.PLAYER_2] == -1: # at least one player hasn't picked a choice yet
                # display pending state
                for i in range(len(self.players)):
                    desc.extend(self.renderPlayer(i, True))
                self.embed.description = "".join(desc)
            else: # both player picked
                # display picks
                i : int
                for i in range(len(self.players)):
                    desc.extend(self.renderPlayer(i, False))
                # this round ended, raise flag
                self.won = True
                # check who won
                win : int = self.WIN_STATES[self.state[self.PLAYER_1] * 10 + self.state[self.PLAYER_2]]
                match win:
                    case self.DRAW:
                        desc.append("This round is a **draw**\n**Next round in 10 seconds...**")
                    case self.PLAYER_1|self.PLAYER_2:
                        self.scores[win] += 1
                        if self.target > 1: # if multiple rounds
                            desc.append("**")
                            desc.append(self.players[win].display_name)
                            desc.append("** won this round\n")
                            for i in range(len(self.scores)):
                                desc.append("**")
                                desc.append(self.players[i].display_name)
                                desc.append("** won ")
                                desc.append(str(self.scores[i]))
                                desc.append(" time(s)")
                                if i < len(self.scores) - 1:
                                    desc.append(" ▫️ ")
                                else:
                                    desc.append("\n")
                            if self.scores[win] >= self.target:
                                desc.append("**")
                                desc.append(self.players[win].display_name)
                                desc.append("** is the **Winner**")
                            else:
                                desc.append("**Next round in 10 seconds...**")
                        else:
                            desc.append("**")
                            desc.append(self.players[win].display_name)
                            desc.append("** is the **Winner**")
                # join strings
                self.embed.description = "".join(desc)
                self.stopall()
        if init: # initialization
            await inter.edit_original_message(content=self.bot.util.players2mentions(self.players), embed=self.embed, view=self) # ping players
            self.message = await inter.original_message()
        elif not self.won: # game is on going
            await self.message.edit(embed=self.embed, view=self)
        else: # game is over
            await self.message.edit(embed=self.embed, view=None)

    """renderPlayer()
    Render the given player state
    
    Parameters
    ----------
    index: Integer, player index in self.players
    pending: Boolean, set to True if players are picking their choice, False otherwise
    """
    def renderPlayer(self : RPS, index : int, pending : bool) -> list[str]:
        desc : list[str] = ["**"]
        desc.append(self.players[index].display_name)
        if pending: # picking choice
            if self.state[index] == -1: # hasn't picked
                desc.append("** ▫️ *is thinking...*")
            else: # picked
                desc.append("** ▫️ *made its choice.*")
        else: # show pick
            desc.append("** ▫️ selected ")
            desc.append(self.PICK_STRINGS[self.state[index]])
        desc.append("\n")
        return desc

    """timeoutCheck()
    Force a result if the view timedout
    
    Parameters
    ----------
    inter: a Discord interaction
    """
    async def timeoutCheck(self : RPS, inter : disnake.Interaction) -> None:
        if not self.won: # if game isn't over
            # generate random hand for players waiting confirmation
            i : int
            for i in range(len(self.state)):
                if self.state[i] == -1:
                    self.state[i] = random.randint(0, 2)
            # update the game
            await self.update(inter)

    """callback()
    Callback for the various buttons
    
    Parameters
    ----------
    interaction: a Discord interaction
    action: integer, what item the player picked
    """
    async def callback(self : RPS, interaction: disnake.Interaction, action: int) -> None:
        i : int|None = None
        idx : int
        p : disnake.User|disnake.Member
        for idx, p in enumerate(self.players): # look which of the two players pressed this button
            if p.id == interaction.user.id:
                if self.state[idx] == -1:
                    i = idx
                    break
        if i is not None:
            if self.state[i] != -1: # this player already pressed the button
                await interaction.response.send_message("You can't change your choice", ephemeral=True)
            else:
                self.state[i] = action # set this player action
                await self.update(interaction) # update game choice
                # send confirmation to the player
                match action:
                    case 0:
                        await interaction.response.send_message("You selected Rock", ephemeral=True)
                    case 1:
                        await interaction.response.send_message("You selected Paper", ephemeral=True)
                    case 2:
                        await interaction.response.send_message("You selected Scissor", ephemeral=True)
        else:
            await interaction.response.send_message("You can't play this game", ephemeral=True)

    @disnake.ui.button(label='Rock', style=disnake.ButtonStyle.primary, emoji='🪨')
    async def rock(self: RPS, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        await self.callback(interaction, self.ROCK)

    @disnake.ui.button(label='Paper', style=disnake.ButtonStyle.primary, emoji='🧻')
    async def paper(self: RPS, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        await self.callback(interaction, self.PAPER)

    @disnake.ui.button(label='Scissor', style=disnake.ButtonStyle.primary, emoji='✂️')
    async def scissor(self: RPS, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        await self.callback(interaction, self.SCISSOR)