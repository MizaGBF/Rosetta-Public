from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot

# ----------------------------------------------------------------------
# Tap View
# ----------------------------------------------------------------------
# View class used by gacha simulations
# It merely adds a "TAP" button which blocks execution until its clicked by the author
# ----------------------------------------------------------------------


class Tap(BaseView):

    __slots__ = ()

    """__init__()
    Constructor

    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    owner_id: the id of the user responsible for the interaction, leave to None to ignore
    timeout: timeout in second before the interaction becomes invalid
    """
    def __init__(self : Tap, bot : DiscordBot, owner_id : int|None = None, timeout : float = 60.0) -> None:
        super().__init__(bot, owner_id=owner_id, timeout=timeout, enable_timeout_cleanup=False)

    """tap()
    The tap button coroutine callback.
    Stop the view when called by the owner.

    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='TAP', style=disnake.ButtonStyle.blurple)
    async def tap(self : Tap, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction): # if not disabled and owner
            self.stopall() # disable itself
            button.disabled = True
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)
