from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from . import User

# ----------------------------------------------------------------------
# ConnectFour View
# ----------------------------------------------------------------------
# View class used to play Connect Four
# ----------------------------------------------------------------------


class ConnectFourButton(disnake.ui.Button):
    """__init__()
    Button Constructor
    A button to place a piece in one column

    Parameters
    ----------
    column: Corresponding column in the grid (0 - 6)
    """
    def __init__(self : ConnectFourButton, column : int) -> None:
        super().__init__(style=disnake.ButtonStyle.primary, label='{}'.format(column + 1))
        self.column : int = column # column this button is linked to

    """callback()
    Coroutine callback called when the button is called
    Stop the view when the game is won

    Parameters
    ----------
    interaction: a disnake interaction
    """
    async def callback(self : ConnectFourButton, interaction: disnake.Interaction) -> None:
        # check if the game is on going and interaction author is the current player
        if (self.view.state >= 0
                and self.view.players[self.view.state].id == interaction.user.id
                and self.view.grid[self.column] == 0):
            # insert in that column
            self.view.insert(self.column)
            self.view.notification = "{} played in column **{}**\n".format(
                self.view.players[self.view.state].display_name,
                self.column + 1
            )
            # check if the game is won
            if self.view.checkWin():
                self.view.notification += "**{}** is the winner".format(self.view.players[self.view.state].display_name)
                self.view.state = -1
            elif 0 not in self.view.grid: # check if the grid is full
                self.view.notification += "It's a **Draw**..."
                self.view.state = -1
            else: # else continue
                self.view.state = (self.view.state + 1) & 1 # cycle to next player
                self.view.notification += "Turn of **{}**".format(self.view.players[self.view.state].display_name)
            # check if game over
            if self.view.state < 0:
                self.view.stopall() # then stop all
            elif self.view.grid[self.column] != 0: # column is full, disable this button column
                self.disabled = True
            await self.view.update(interaction)
        else:
            await interaction.response.send_message(
                "It's not your turn to play or you aren't the player",
                ephemeral=True
            )


class ConnectFour(BaseView):
    # Directions used for the win check
    DIRECTIONS : list[tuple[int, int]] = [
        (1, 0), # Horizontal right
        (0, 1), # Vertical down
        (1, 1), # Diagonal down right, top left to bottom right
        (1, -1) # Diagonal up right, bottom left to bottom right
    ]
    # Grid size
    ROW : int = 6
    COLUMN : int = 7

    """__init__()
    Constructor

    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    players: list of Players
    embed: disnake.Embed to edit
    """
    def __init__(
        self : ConnectFour,
        bot : DiscordBot,
        players : list[User],
        embed : disnake.Embed
    ) -> None:
        super().__init__(bot, timeout=480)
        self.grid : list[int] = [0 for i in range(self.ROW * self.COLUMN)]
        self.state : int = 0 # game state
        self.players : list[User] = players # player list
        # message embed to update
        self.embed : disnake.Embed = embed
        # create button
        i : int
        for i in range(self.COLUMN):
            self.add_item(ConnectFourButton(i))
        self.notification : str = "Turn of **{}**".format(self.players[self.state].display_name)

    """update()
    Update the embed

    Parameters
    ----------
    inter: an interaction
    init: if True, it uses a different method (only used from the command call itself)
    """
    async def update(self : ConnectFour, inter : disnake.Interaction, init : bool = False) -> None:
        # show player names
        # the game state (notification)
        # and the grid (render() call)
        self.embed.description : list[str] = [
            ":red_circle: ",
            self.players[0].display_name,
            " :yellow_circle: ",
            self.players[1].display_name,
            "\n",
            self.notification,
            "\n"
        ]
        self.embed.description.extend(self.render())
        self.embed.description = "".join(self.embed.description)
        # set message
        if init:
            await inter.edit_original_message(embed=self.embed, view=self) # init is true, we edit
        elif self.state >= 0:
            await inter.response.edit_message(embed=self.embed, view=self) # game is on going
        else:
            await inter.response.edit_message(embed=self.embed, view=None) # game is over, remove the view

    """insert()
    Insert a piece in the grid

    Parameters
    ----------
    col: Column to insert to (note: it must have been checked previously for empty spaces)
    """
    def insert(self : ConnectFour, col : int) -> None:
        index : int = col
        i : int
        for i in range(1, self.ROW): # look for the next free cell in that column
            if self.grid[col + self.COLUMN * i] != 0: # cell has already been used
                break
            index = col + self.COLUMN * i # set index to this cell
        self.grid[index] = self.state + 1 # set player state id (0 or 1) + 1, to that cell
        # this means:
        # 0 = free cell
        # 1 = player 1 piece
        # 2 = player 2 piece

    """checkWin()
    Check if the current player won

    Return
    ----------
    bool: True if won, False if not
    """
    def checkWin(self : ConnectFour) -> bool:
        piece : int = self.state + 1 # check which player piece we're checking for
        c : int
        r : int
        for c in range(self.COLUMN):
            for r in range(self.ROW):
                # check if the piece in this space is owned by this player
                if self.grid[c + r * self.COLUMN] == piece:
                    for dc, dr in self.DIRECTIONS: # for each possible directions
                        if all(
                            [ # check if the 3 next pieces in that direction are also from that player
                                (
                                    0 <= r + dr * i < self.ROW
                                    and 0 <= c + dc * i < self.COLUMN
                                    and self.grid[(c + dc * i) + (r + dr * i) * self.COLUMN] == piece
                                )
                                for i in range(1, 4)
                            ]
                        ):
                            # this player won
                            # mark these pieces as the winning move
                            i : int
                            for i in range(0, 4):
                                self.grid[(c + dc * i) + (r + dr * i) * self.COLUMN] += 10
                            return True
        return False # this player hasn't won

    """render()
    Render the grid into a string

    Return
    ----------
    list: resulting list of strings
    """
    def render(self : ConnectFour) -> str:
        msgs : list[str] = []
        # iterate over grid
        r : int
        c : int
        for r in range(self.ROW): # row
            for c in range(self.COLUMN): # column
                match self.grid[c + r * self.COLUMN]: # get cell state
                    case 10: msgs.append(":blue_circle:")
                    case 11: msgs.append(":brown_circle:")
                    case 12: msgs.append(":orange_circle:")
                    case 0: msgs.append(":blue_circle:")
                    case 1: msgs.append(":red_circle:")
                    case 2: msgs.append(":yellow_circle:")
                    case _: msgs.append(str(self.grid[c + r * self.COLUMN])) # undefined
                msgs.append(" ")
            msgs.append("\n")
        msgs.append(":one: :two: :three: :four: :five: :six: :seven:")
        return msgs
