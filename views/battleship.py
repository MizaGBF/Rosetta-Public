from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import random

# ----------------------------------------------------------------------------------------------------------------
# BattleShip View
# ----------------------------------------------------------------------------------------------------------------
# View class used to play Battle Ship
# ----------------------------------------------------------------------------------------------------------------

class BattleShipButton(disnake.ui.Button):
    """__init__()
    Button Constructor
    A button the user can press
    
    Parameters
    ----------
    btype: 0 for column buttons, 1 for row buttons
    target: string, target of the button (ABCDE or 12345)
    row: an integer indicating on what row to set the button on
    """
    def __init__(self, btype : int, target : str, row : int) -> None:
        super().__init__(style=(disnake.ButtonStyle.success if btype == 0 else disnake.ButtonStyle.danger), label=target, row=row)
        self.btype = btype
        self.target = target

    """callback()
    Coroutine callback called when the button is used
    Stop the view when the game is over
    
    Parameters
    ----------
    interaction: a disnake interaction
    """
    async def callback(self, interaction: disnake.Interaction) -> None:
        if self.view.state >= 0 and self.view.players[self.view.state].id == interaction.user.id: # if state is valid (0 or 1) and the player turn corresponds to whoever triggered this callback
            self.view.input[self.btype] = self.target # put the letter we pressed in the input slot
            if None not in self.view.input: # if both input slots are full
                res = self.view.shoot("".join(self.view.input)) # we "shoot" on the targeted cell and get the result
                if res == 0: # invalid target
                    await interaction.response.send_message("You can't shoot at {}".format("".join(self.view.input)), ephemeral=True)
                    self.view.input[self.btype] = None # cancel the last input
                else: # good target
                    self.view.notification = "{} shot at **{}**\n".format(self.view.players[self.view.state].display_name, "".join(self.view.input))
                    self.view.input = [None, None] # reset input
                    if res == 2: # the game is over
                        self.view.notification += "**{}** is the winner".format(self.view.players[self.view.state].display_name)
                        self.view.state = -1 # put the game in over mode
                    else: # the game continues
                        self.view.state = (self.view.state + 1) & 1 # cycle to other player (0->1 or 1->0)
                        self.view.notification += "Turn of **{}**".format(self.view.players[self.view.state].display_name)
                    if self.view.state < 0: # stop view if game is over
                        self.view.stopall()
                        self.disabled = True
                    # update the message
                    await self.view.update(interaction)
            else: # else, update the selection
                extra_notif = ["\n{} is selecting **".format(self.view.players[self.view.state].display_name)]
                extra_notif.append('?' if self.view.input[0] is None else self.view.input[0])
                extra_notif.append('?' if self.view.input[1] is None else self.view.input[1])
                extra_notif.append("**...")
                # update the message
                await self.view.update(interaction, extra_notif="".join(extra_notif))
        else: # this user isn't a player OR it's not their turn
            await interaction.response.send_message("It's not your turn to play or you aren't a player", ephemeral=True)

class BattleShip(BaseView):
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    players: list of Players
    embed: disnake.Embed to edit
    """
    def __init__(self, bot : 'DiscordBot', players : list, embed : disnake.Embed) -> None:
        super().__init__(bot, timeout=480)
        # the player battleship grids (two of them, 5x5). 0 = empty space, 1 = empty space + shot, 10 = ship, 11 = ship + shot
        self.grids = [[0 for i in range(20)] + [10 for i in range(5)], [0 for i in range(20)] + [10 for i in range(5)]]
        # randomize them
        random.shuffle(self.grids[0])
        random.shuffle(self.grids[1])
        # the game state. -1 = game over, 0 = player 1 turn, 1 = player 2 turn
        self.state = 0
        # player list
        self.players = players
        # the message embed
        self.embed = embed
        # the current player inputs (first and second button. Will fill with strings. Example: ["C", "4"] to fire on C4)
        self.input = [None, None]
        # add letter buttons
        for i in ['A', 'B', 'C', 'D', 'E']:
            self.add_item(BattleShipButton(0, i, 0))
        # add digit buttons
        for i in range(5):
            self.add_item(BattleShipButton(1, str(i+1), 1))
        # set notification to player 1 turn
        self.notification = "Turn of **{}**".format(self.players[self.state].display_name)

    """update()
    Update the embed
    
    Parameters
    ----------
    inter: an interaction
    init: if True, it uses a different method (only used from the command call itself)
    extra_notif: optional string to append to the embed description
    """
    async def update(self, inter : disnake.Interaction, init : bool = False, extra_notif : str = "") -> None:
        # update the description
        self.embed.description = ":ship: {} :cruise_ship: {}\n".format(self.players[0].display_name, self.players[1].display_name) + self.notification + extra_notif
        # render both player grids, each in a field
        for i in range(0, 2):
            self.embed.set_field_at(i, name=(self.players[i].display_name if len(self.players[i].display_name) <= 10 else self.players[i].display_name[:10] + '...'), value=self.render(i))
        # set message
        if init:
            await inter.edit_original_message(embed=self.embed, view=self) # init is true, we edit
        elif self.state >= 0:
            await inter.response.edit_message(embed=self.embed, view=self) # game is on going
        else:
            await inter.response.edit_message(embed=self.embed, view=None) # game is over, remove the view

    """shoot()
    Try to shoot at the location
    
    Parameters
    ----------
    value: string value sent by the dropdown (example: "C3")
    
    Return
    ----------
    int: 2 if the game is won, 1 if the value is valid, 0 if not
    """
    def shoot(self, value : str) -> int:
        # coordinates
        x = 0
        y = int(value[1]) - 1
        # opponent id
        opponent = (self.state + 1) & 1
        # convert letter to X coordinate
        match value[0]:
            case 'A': x = 0
            case 'B': x = 1
            case 'C': x = 2
            case 'D': x = 3
            case 'E': x = 4
        # check result
        if self.grids[opponent][x + y * 5] & 1 == 0: # check if it the cell has already been shot (i.e. equal to 1 or 11)
            # it hasn't, so we add 1
            self.grids[opponent][x + y * 5] += 1
            # If no more 10 left in the opponent grid, all ships have been touched
            if 10 not in self.grids[opponent]:
                return 2 # game over, this player won
            return 1 # player shot with success
        return 0 # couldn't shoot

    """render()
    Render one of the grid into a string
    
    Parameters
    ----------
    grid_id: integer, either 0 (first player) or 1 (second)
    
    Return
    ----------
    str: resulting string
    """
    def render(self, grid_id : int) -> str:
        # Line by line
        # The top line are the letter indicators
        msgs = [":white_square_button::regional_indicator_a::regional_indicator_b::regional_indicator_c::regional_indicator_d::regional_indicator_e:\n"]
        # Next, for each line of the grid
        for r in range(5):
            match r: # the number on the left
                case 0: msgs.append(":one:")
                case 1: msgs.append(":two:")
                case 2: msgs.append(":three:")
                case 3: msgs.append(":four:")
                case 4: msgs.append(":five:")
            # then add the 5 cells
            for c in range(5):
                match self.grids[grid_id][c + r * 5]: # depending on content:
                    case 0: # empty
                        msgs.append(":blue_square:")
                    case 10: # ship
                        if self.state >= 0: # show an empty square if the game is on going 
                            msgs.append(":blue_square:")
                        else: # else show the ship if the game is over
                            msgs.append(":cruise_ship:")
                    case 1: # has been shot but empty
                        msgs.append(":purple_square:")
                    case 11: # ship has been shot
                        msgs.append(":boom:")
            # new line
            msgs.append("\n")
        return "".join(msgs)