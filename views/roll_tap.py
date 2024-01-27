from . import BaseView
import disnake
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Tap View
# ----------------------------------------------------------------------------------------------------------------
# View class used by gacha simulations
# It merely adds a "TAP" button
# ----------------------------------------------------------------------------------------------------------------

class Tap(BaseView):
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    owner_id: the id of the user responsible for the interaction, leave to None to ignore
    timeout: timeout in second before the interaction becomes invalid
    """
    def __init__(self, bot : 'DiscordBot', owner_id : Optional[int] = None, timeout : float = 60.0) -> None:
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
    async def tap(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction):
            self.stopall()
            button.disabled = True
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)