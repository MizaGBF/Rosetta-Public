from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
import random

# ----------------------------------------------------------------------
# Chest Rush View
# ----------------------------------------------------------------------
# Chest Rush class and its button used by the chest rush game
# ----------------------------------------------------------------------


class ChestRushButton(disnake.ui.Button):
    """__init__()
    Button Constructor

    Parameters
    ----------
    grid: the list of remaining winnable items
    row: an integer indicating on what row to set the button on
    """
    def __init__(self : ChestRushButton, grid : list[str], row : int) -> None:
        super().__init__(style=disnake.ButtonStyle.secondary, label='Chest', row=row)
        # ref to the view chest grid
        self.grid : list[str] = grid

    """callback()
    Coroutine callback called when the button is called
    Stop the view when the game is won

    Parameters
    ----------
    interaction: a Discord interaction
    """
    async def callback(
        self : ChestRushButton,
        interaction: disnake.Interaction
    ) -> None:
        # check if the button is enabled and the interaction author is the player
        if not self.disabled and self.view.ownership_check(interaction):
            # disable this button
            self.disabled = True
            # retrieve the item from the grid
            self.label = self.view.grid.pop()
            if self.label.startswith('$$$'): # check prefix to set a particular color
                self.style = disnake.ButtonStyle.success
                self.label = self.label[3:]
            else:
                self.style = disnake.ButtonStyle.primary
            # check the game status
            if self.view.check_status(): # if game is over
                self.view.stopall()
                await interaction.response.edit_message(
                    embed=self.view.bot.embed(
                        author={
                            'name':"{} opened the chests".format(interaction.user.display_name),
                            'icon_url':interaction.user.display_avatar
                        },
                        description="Here's the collected loot.",
                        color=self.view.color
                    ),
                    view=self.view
                )
                await self.view.bot.channel.clean(interaction, 70)
            else: # game continues
                await interaction.response.edit_message(view=self.view)
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)


class ChestRush(BaseView):
    """__init__()
    Constructor

    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    owner_id: the id of the user responsible for the interaction, leave to None to ignore
    grid: list of items to be hidden behind the buttons
    color: the color to be used for the message embed
    """
    def __init__(self : ChestRush, bot : DiscordBot, owner_id : int, grid : list[str], color : int) -> None:
        super().__init__(bot, owner_id=owner_id, timeout=120.0)
        # Chest grid, i.e list of the items to win (1 to 9 items)
        self.grid : list[str] = grid
        self.color : int = color
        # Create 9 buttons (one for each theorical grid space)
        # The buttons aren't directly linked to a particular grid space,
        # we just create the illusion of random placement.
        # The game simply take the next grid item in order
        i : int
        for i in range(9):
            self.add_item(ChestRushButton(self.grid, i // 3)) # second parameter is the row the button is on

    """check_status()
    Function to check the game state

    Parameters
    ----------
    item: the last item revealed behind a button

    Returns
    --------
    bool: True if the game is over, False if not
    """
    def check_status(self : ChestRush) -> bool:
        c : disnake.ui.Component
        if len(self.grid) == 0: # Grid is empty, game is over
            for c in self.children:
                if not c.disabled: # disable remaining buttons and set label to empty space
                    c.disabled = True
                    c.label = '\u200b'
            return True # game is over
        elif len(self.grid) == 1 and self.grid[0].startswith("###"): # last item is a bonus item
            self.grid[0] = self.grid[0].replace("###", "$$$")
            while True:
                c = random.choice(self.children) # pick a random button
                if c.disabled:
                    continue # the button must NOT be disabled
                c.style = disnake.ButtonStyle.danger # change its color to show it's special
                c.label = "Surprise" # add surprise name
                for c in self.children: # disable every other buttons
                    if not c.disabled and c.style != disnake.ButtonStyle.danger:
                        c.disabled = True
                        c.label = '\u200b'
                break
        return False # game isn't over
