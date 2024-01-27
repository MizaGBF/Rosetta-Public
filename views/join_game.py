from . import BaseView
import disnake
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from datetime import timedelta

# ----------------------------------------------------------------------------------------------------------------
# JoinGame View
# ----------------------------------------------------------------------------------------------------------------
# View class used to join games
# ----------------------------------------------------------------------------------------------------------------

class JoinGame(BaseView):
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    players: list of disnake.User/Member participating
    limit: player count limit
    min_p: required participants
    callback: coroutine to be called on button press (optional)
    """
    def __init__(self, bot : 'DiscordBot', players : list, limit : int, min_p : int, callback = None) -> None:
        super().__init__(bot)
        self.players = players
        self.limit = limit
        self.min_p = 1 if bot.debug_mode else min_p
        self.callback = (self.default_callback if callback is None else callback)
        self.timer = None

    """updateTimer()
    Coroutine to update the waiting message
    
    Parameters
    ----------
    msg: disnake.Message to update
    embed: embed to update and put in msg
    desc: description of the embed to update, must contains two {} for the formatting
    limit: time limit in seconds
    """
    async def updateTimer(self, msg : disnake.Message, embed : disnake.Embed, desc : str, limit : int) -> None:
        self.timer = self.bot.util.JST() + timedelta(seconds=limit)
        while True:
            await asyncio.sleep(1)
            c = self.bot.util.JST()
            if c >= self.timer or len(self.players) >= self.limit:
                break
            embed.description = desc.format((self.timer - c).seconds, len(self.players))
            await msg.edit(embed=embed)
        await msg.edit(view=None)
        self.stopall()

    """isParticipating()
    Check if the given id is from a participating user
    
    Parameters
    ----------
    pid: disnake.User/Member id
    
    Returns
    ----------
    bool: True if participating, False if not
    """
    def isParticipating(self, pid : int) -> bool:
        for p in self.players:
            if p.id == pid:
                return True
        return False

    """default_callback()
    Default and example of a callback to use on button press
    
    Parameters
    ----------
    interaction: a disnake interaction
    """
    async def default_callback(self, interaction : disnake.Interaction):
        await interaction.response.send_message("You are registered", ephemeral=True)

    """joinbutton()
    The Join button coroutine callback.
    
    Parameters
    ----------
    button: the disnake button
    interaction: a disnake interaction
    """
    @disnake.ui.button(label='Join', style=disnake.ButtonStyle.blurple)
    async def joinbutton(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and not self.isParticipating(interaction.user.id):
            self.players.append(interaction.user)
            await self.callback(interaction)
            if len(self.players) >= self.limit:
                self.stopall()
                button.disabled = True
        else:
            await interaction.response.send_message("You are already participating OR the game started", ephemeral=True)

    """startbutton()
    The Start button coroutine callback.
    
    Parameters
    ----------
    button: the disnake button
    interaction: a disnake interaction
    """
    @disnake.ui.button(label='Start', style=disnake.ButtonStyle.blurple)
    async def startbutton(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.players[0].id == interaction.user.id:
            if len(self.players) >= self.min_p:
                self.timer = self.bot.util.JST()
                await interaction.response.send_message("Starting the game...", ephemeral=True)
            else:
                await interaction.response.send_message("Not enough players entered the game yet", ephemeral=True)
        else:
            await interaction.response.send_message("Only the game creator can start the game", ephemeral=True)