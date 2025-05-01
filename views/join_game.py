from __future__ import annotations
from . import BaseView
import disnake
import asyncio
from typing import Callable, TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from . import User
from datetime import datetime, timedelta

# ----------------------------------------------------------------------
# JoinGame View
# ----------------------------------------------------------------------
# View class used to join games
# ----------------------------------------------------------------------


class JoinGame(BaseView):

    __slots__ = ("players", "limit", "min_p", "players", "callback", "timer")

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
    def __init__(
        self : JoinGame,
        bot : DiscordBot,
        players : list[User],
        limit : int,
        min_p : int,
        callback : Callable|None = None
    ) -> None:
        super().__init__(bot)
        self.players : list[User] = players
        self.limit : int = limit # player limit
        self.min_p : int = min_p # minimum player requirement
        if bot.debug_mode and len(self.players) > 0: # in debug mode, the author can play against itself
            while len(self.players) < self.min_p:
                self.players.append(self.players[0])
        # callback
        self.callback = (self.default_callback if callback is None else callback)
        # timer tracker
        self.timer : datetime|None = None

    """updateTimer()
    Coroutine to update the waiting message

    Parameters
    ----------
    msg: disnake.Message to update
    embed: embed to update and put in msg
    desc: description of the embed to update, must contains two {} for the formatting
    limit: time limit in seconds
    """
    async def updateTimer(
        self : JoinGame,
        msg : disnake.Message,
        embed : disnake.Embed,
        desc : str,
        limit : int
    ) -> None:
        self.timer = self.bot.util.JST() + timedelta(seconds=limit) # initialize the timer to now + the timer duration
        while True:
            await asyncio.sleep(1) # wait a second
            c : datetime = self.bot.util.JST() # get current time
            # check if we reached the timer OR if the player limit is reached
            if c >= self.timer or len(self.players) >= self.limit:
                break # if so, exit the loop
            # update timer and player cout message
            embed.description = desc.format((self.timer - c).seconds, len(self.players))
            await msg.edit(embed=embed)
        # remove the view
        await msg.edit(view=None)
        # and stop everything
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
    def isParticipating(self : JoinGame, pid : int) -> bool:
        p : User
        for p in self.players:
            if p.id == pid: # ids match
                return True
        return False

    """default_callback()
    Default and example of a callback to use on button press

    Parameters
    ----------
    interaction: a disnake interaction
    """
    async def default_callback(self : JoinGame, interaction : disnake.Interaction):
        await interaction.response.send_message("You are registered", ephemeral=True)

    """joinbutton()
    The Join button coroutine callback.

    Parameters
    ----------
    button: the disnake button
    interaction: a disnake interaction
    """
    @disnake.ui.button(label='Join', style=disnake.ButtonStyle.blurple)
    async def joinbutton(self : JoinGame, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        # check if the button is enabled and the user isn't already in the player list
        if not button.disabled and not self.isParticipating(interaction.user.id):
            self.players.append(interaction.user) # add the user
            if len(self.players) >= self.limit: # disable everything if the player limit is full
                self.stopall()
                button.disabled = True
            await self.callback(interaction) # call the callback
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
    async def startbutton(self : JoinGame, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        # check if the button is enabled and the user if the game initiator
        if not button.disabled and self.players[0].id == interaction.user.id:
            if len(self.players) >= self.min_p: # if minimum requirement is met
                self.timer = self.bot.util.JST() # set timer to now to stop the wait
                await interaction.response.send_message("Starting the game...", ephemeral=True)
            else:
                await interaction.response.send_message("Not enough players entered the game yet", ephemeral=True)
        else:
            await interaction.response.send_message("Only the game creator can start the game", ephemeral=True)
