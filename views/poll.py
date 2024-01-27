from . import BaseView
import disnake
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from datetime import timedelta

# ----------------------------------------------------------------------------------------------------------------
# Poll View
# ----------------------------------------------------------------------------------------------------------------
# View class used to make polls
# ----------------------------------------------------------------------------------------------------------------

class PollDropdown(disnake.ui.Select):
    """__init__()
    Constructor
    
    Parameters
    ----------
    title: poll title string
    choices: list of the poll choices (strings)
    """
    def __init__(self, title : str = "", choices : list = []) -> None:
        options = []
        for c in choices:
            options.append(disnake.SelectOption(label=c))
        if len(options) < 2: raise Exception('Please specify what to poll for\nFormat: `duration title;choice1;choice2;...;choiceN`')
        super().__init__(placeholder=title, min_values=1, max_values=1, options=options)

    """callback()
    Coroutine callback called when the dropdown is used
    
    Parameters
    ----------
    interaction: a Discord interaction
    """
    async def callback(self, interaction: disnake.Interaction) -> None:
        self.view.votes[interaction.user.id] = self.values[0]
        await interaction.response.send_message(f'Your vote has been updated to `{self.values[0]}`', ephemeral=True)


class Poll(BaseView):
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    author: user object of the poll creator
    embed: disnake.Embed object to edit
    title: pool title string
    choices: list of the poll choices (strings)
    """
    def __init__(self, bot : 'DiscordBot', author : disnake.Member, embed : disnake.Embed, title : str = "", choices : list = []) -> None:
        super().__init__(bot, timeout=None, enable_timeout_cleanup=False)
        self.author = author
        self.embed = embed
        self.title = title
        self.votes = {}
        self.choices = []
        choices.reverse()
        while len(choices) > 0:
            c = choices.pop()
            if c in choices or c == "": continue
            self.choices.append(c)

        self.add_item(PollDropdown(title, self.choices))

    """run_poll()
    Countdown for X seconds before returning the poll result
    
    Parameters
    ----------
    duration: poll duration in seconds
    message: original message to update
    channel: where to post the results
    """
    async def run_poll(self, duration : int, message : disnake.Message, channel : disnake.TextChannel) -> None:
        timer = self.bot.util.JST() + timedelta(seconds=duration)
        while True:
            await asyncio.sleep(1)
            c = self.bot.util.JST()
            if c >= timer: break
            self.embed.description = "**{}** seconds remaining to vote\n".format((timer - c).seconds)
            if len(self.votes) > 0:
                self.embed.description += "**{}** vote".format(len(self.votes))
                if len(self.votes) > 1: self.embed.description += "s"
            await message.edit(embed=self.embed)
        self.stopall()
        await message.delete()
        msg = "**{}** vote(s)\n".format(len(self.votes))
        count = {}
        for c in self.choices:
            count[c] = 0
        for id, v in self.votes.items():
            if v in count: count[v] += 1
        winner = max(count.values())
        for v in count:
            bold = '**' if count[v] == winner else ''
            percent = ('({:.1f}%)'.format(100 * count[v] / len(self.votes)) if count[v]> 0 else '').replace('.0', '')
            msg += "`{}`{} ▫️ {} {}{}\n".format(v, bold, count[v], percent, bold)
        await channel.send(embed=self.bot.embed(author={'name':"{}'s poll ended".format(self.author.display_name), 'icon_url':self.author.display_avatar}, title=self.title, description=msg, color=self.embed.color))