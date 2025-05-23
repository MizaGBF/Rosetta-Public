from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    # Type Aliases
    type Grid = list[tuple[str, str]]

# ----------------------------------------------------------------------
# Scratcher View
# ----------------------------------------------------------------------
# Scratcher class and its button used by the scratcher game
# ----------------------------------------------------------------------


class ScratcherButton(disnake.ui.Button):
    ENDPOINT = 'https://prd-game-a-granbluefantasy.akamaized.net/assets_en/img/sp/assets/'

    __slots__ = ("item", "label")

    """__init__()
    Button Constructor

    Parameters
    ----------
    item: a tuple, containing two strings (item name and thumbnail) representing the gbf item hidden behind the button
    row: an integer indicating on what row to set the button on
    label: the default string label on the button
    style: the default Discord button style
    """
    def __init__(
        self : ScratcherButton,
        item: tuple[str, str],
        row : int,
        label : str = '???',
        style : disnake.ButtonStyle = disnake.ButtonStyle.secondary
    ) -> None:
        super().__init__(style=style, label='\u200b', row=row)
        self.item : tuple[str, str] = item
        self.label : str = label

    """callback()
    Coroutine callback called when the button is called
    Stop the view when the game is won

    Parameters
    ----------
    interaction: a Discord interaction
    """
    async def callback(self : ScratcherButton, interaction: disnake.Interaction) -> None:
        if not self.disabled and self.view.ownership_check(interaction):
            self.disabled = True
            self.label = self.item[0]
            self.style = disnake.ButtonStyle.primary
            if self.view.check_status(self.item):
                self.view.stopall()
                await interaction.response.edit_message(
                    embed=self.view.bot.embed(
                        author={
                            'name':"{} scratched".format(interaction.user.display_name),
                            'icon_url':interaction.user.display_avatar
                        },
                        description="You won **{}**".format(self.item[0]),
                        thumbnail=self.ENDPOINT + self.item[1],
                        footer=self.view.footer,
                        color=self.view.color
                    ),
                    view=self.view)
                await self.view.bot.channel.clean(interaction, 70)
            else:
                await interaction.response.edit_message(view=self.view)
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)


class Scratcher(BaseView):

    __slots__ = ("grid", "color", "footer", "state", "counter")

    """__init__()
    Constructor

    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    owner_id: the id of the user responsible for the interaction, leave to None to ignore
    grid: a 10 items-list to be hidden behind the buttons
    color: the color to be used for the message embed
    footer: the footer to be used for the message embed
    """
    def __init__(self : Scratcher, bot : DiscordBot, owner_id : int, grid : Grid, color : int, footer : str) -> None:
        super().__init__(bot, owner_id=owner_id, timeout=120.0, enable_timeout_cleanup=False)
        self.grid : Grid = grid
        self.color : int = color
        self.footer : str = footer
        self.state : dict[tuple[str, str], int] = {}
        self.counter : int = 0
        i : int
        for i in range(9):
            self.add_item(ScratcherButton(self.grid[i], i // 3))

    """check_status()
    Function to check the game state

    Parameters
    ----------
    item: the last item revealed behind a button

    Returns
    --------
    bool: True if the game is over, False if not
    """
    def check_status(self : Scratcher, item : tuple) -> bool:
        self.counter += 1
        if item not in self.state:
            self.state[item] = 0
        self.state[item] += 1
        game_over : bool = (self.state[item] == 3)
        c : disnake.ui.Component
        for c in self.children:
            if c.disabled:
                if self.state.get(c.item, 0) == 2:
                    c.style = disnake.ButtonStyle.success
                elif self.state.get(c.item, 0) == 3:
                    c.style = disnake.ButtonStyle.danger
            elif game_over:
                self.state[c.item] = self.state.get(c.item, 0) + 1
                e : disnake.ui.Component
                for e in self.children:
                    e.label = e.item[0]
                    e.disabled = True
        if not game_over and self.counter == 9:
            self.add_item(ScratcherButton(self.grid[9], 3, 'Final Scratch', disnake.ButtonStyle.danger))
        return game_over
