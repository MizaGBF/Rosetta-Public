from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# TicTacToe View
# ----------------------------------------------------------------------------------------------------------------
# View class used to play Tic Tac Toe
# ----------------------------------------------------------------------------------------------------------------

class TicTacToeButton(disnake.ui.Button):
    """__init__()
    Button Constructor
    
    Parameters
    ----------
    pos: Integer position in grid (0 - 9)
    """
    def __init__(self : TicTacToeButton, pos : int) -> None:
        super().__init__(style=disnake.ButtonStyle.secondary, label='\u200b', row=pos // 3)
        self.pos : int = pos

    """callback()
    Coroutine callback called when the button is called
    Stop the view when the game is won
    
    Parameters
    ----------
    interaction: a disnake interaction
    """
    async def callback(self : TicTacToeButton, interaction: disnake.Interaction) -> None:
        if not self.disabled and interaction.user.id == self.view.playing.id and self.view.grid[self.pos] == 0: # if enabled and author is current player and this space in the grid is free
            self.disabled = True # disable this button
            self.view.grid[self.pos] = self.view.playing_index + 1 # set player id + 1
            # set text and color
            if self.view.playing_index == 0:
                self.style = disnake.ButtonStyle.success
                self.label = "X"
            else:
                self.style = disnake.ButtonStyle.danger
                self.label = "O"
            # update the game
            state : bool = self.view.update_status()
            # update description
            self.view.embed.description = ":x: {} :o: {}\n{}".format(self.view.players[0].display_name, self.view.players[1].display_name, self.view.notification)
            # check game state
            if state: # over
                self.view.stopall() # stop all
                await interaction.response.edit_message(embed=self.view.embed, view=self.view) # keep the view for the grid to be visible
            else: # not over
                await interaction.response.edit_message(embed=self.view.embed, view=self.view)
        else:
            await interaction.response.send_message("It's not your turn to play", ephemeral=True)

class TicTacToe(BaseView):
    WIN_SCENARIOS : list[list[int]] = [ # index of cells to check for a possible win
        [0,1,2],
        [3,4,5],
        [6,7,8],
        [0,3,6],
        [1,4,7],
        [2,5,8],
        [0,4,8],
        [2,4,6]
    ]
    
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    players: list of Players
    embed: disnake.Embed to edit
    """
    def __init__(self : TicTacToe, bot : DiscordBot, players : list[disnake.User|disnake.Member], embed : disnake.Embed) -> None:
        super().__init__(bot, timeout=180)
        self.players : list[disnake.User|disnake.Member] = players # players
        self.embed : disnake.Embed = embed # embed to update
        self.playing : disnake.User|disnake.Member = self.players[0] # current player
        self.playing_index : int = 0 # player index in players
        self.grid : list[int] = [0, 0, 0, 0, 0, 0, 0, 0, 0] # 3x3 grid
        self.moves : int = 0 # total moves played
        self.notification : str = "Turn of {}".format(self.playing.display_name)
        # add buttons
        i : int
        for i in range(len(self.grid)):
            self.add_item(TicTacToeButton(i))

    """state()
    Return if the game is won or not
    
    Returns
    --------
    tuple: (win boolean, id of the winning player)
    """
    def state(self : TicTacToe) -> tuple[bool, int|None]:
        w : list[int]
        for w in self.WIN_SCENARIOS: # check each configuration
            if self.grid[w[0]] != 0 and self.grid[w[0]] == self.grid[w[1]] and self.grid[w[0]] == self.grid[w[2]]:
                # change button color
                self.children[w[0]].style = disnake.ButtonStyle.primary
                self.children[w[1]].style = disnake.ButtonStyle.primary
                self.children[w[2]].style = disnake.ButtonStyle.primary
                return True, self.grid[w[0]] - 1 # win
        return False, None # no win

    """update_status()
    Function to check the game state
    
    Returns
    --------
    bool: True if the game is over, False if not
    """
    def update_status(self : TicTacToe) -> bool:
        self.moves += 1 # increase move count
        won : bool
        win_id : int|None
        won, win_id = self.state() # check for win
        if won or self.moves == 9: # check if game over
            if win_id is not None: # a player won
                self.playing = self.players[win_id]
                self.playing_index = win_id
                self.notification = "**{}** is the winner".format(self.playing.display_name)
            else: # draw, out of space for more moves
                self.notification = "It's a **Draw**..."
            # disable buttons
            c : disnake.ui.Component
            for c in self.children:
                c.disabled = True
            # return game over
            return True
        else:
            # cycle player
            self.playing_index = (self.playing_index + 1) & 1
            # update playing player
            self.playing = self.players[self.playing_index]
            # update text
            self.notification = "Turn of **{}**".format(self.playing.display_name)
            # return game continue
            return False