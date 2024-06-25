from . import BaseView
import disnake
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Page View
# ----------------------------------------------------------------------------------------------------------------
# View class used to add Previous and Next buttons to cycle between multiple embeds
# ----------------------------------------------------------------------------------------------------------------

class Page(BaseView):
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    owner_id: the id of the user responsible for the interaction, leave to None to ignore
    embeds: list of embeds (one for each page)
    timeout: timeout in second before the interaction becomes invalid
    enable_timeout_cleanup: set to True to cleanup the interaction once over
    """
    def __init__(self, bot : 'DiscordBot', owner_id : int, embeds : list, timeout : float = 180.0, enable_timeout_cleanup : bool = False) -> None:
        super().__init__(bot, owner_id=owner_id, timeout=timeout, enable_timeout_cleanup=enable_timeout_cleanup)
        self.current = 0
        self.embeds = embeds

    """prev()
    The previous button coroutine callback.
    Change the self.message to the previous embed
    
    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='◀️', style=disnake.ButtonStyle.blurple)
    async def prev(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction):
            if len(self.embeds) > 0:
                self.current = (self.current + len(self.embeds) - 1) % len(self.embeds)
                await interaction.send("\u200b", ephemeral=True, delete_after=0)
                await self.message.edit(embed=self.embeds[self.current])
            else:
                await interaction.send("Impossible to change pages", ephemeral=True)
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)

    """next()
    The next button coroutine callback.
    Change the self.message to the next embed
    
    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='▶️', style=disnake.ButtonStyle.blurple)
    async def next(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction):
            if len(self.embeds) > 0:
                self.current = (self.current + 1) % len(self.embeds)
                await interaction.send("\u200b", ephemeral=True, delete_after=0)
                await self.message.edit(embed=self.embeds[self.current])
            else:
                await interaction.send("Impossible to change pages", ephemeral=True)
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)


# ----------------------------------------------------------------------------------------------------------------
# PageRanking View and dropdown
# ----------------------------------------------------------------------------------------------------------------
# View class used to add Previous and Next buttons to cycle between multiple embeds
# Also add a select
# ----------------------------------------------------------------------------------------------------------------

class RankingDropdown(disnake.ui.StringSelect):
    def __init__(self, placeholder : str, search_results : list) -> None:
        # Define the options that will be presented inside the dropdown
        options = [disnake.SelectOption(label=s[0], description=str(s[1])) for s in search_results]
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        )

    def update_options(self, search_results : list) -> None:
        options = [disnake.SelectOption(label=s[0], description=str(s[1])) for s in search_results]
        self.options=options

    async def callback(self, inter: disnake.MessageInteraction) -> None:
        if not self.disabled and self.view.ownership_check(inter):
            if len(self.view.embeds) >= 2:
                self.view.prev_b.disabled=True
                self.view.prev_b.style=disnake.ButtonStyle.secondary
                self.view.next_b.disabled=True
                self.view.next_b.style=disnake.ButtonStyle.secondary
            self.view.close_b.disabled=True
            self.view.close_b.style=disnake.ButtonStyle.secondary
            self.disabled=True
            await inter.response.defer(ephemeral=True)
            try:
                if self.view.stype:# crew
                    await inter.edit_original_message(embed=self.view.bot.embed(title=self.view.embeds[0].title, description="{} Loading Crew `{}`...".format(self.view.bot.emote.get('time'), self.values[0]), color=self.view.color), view=self.view)
                    await asyncio.sleep(0.5)
                    self.view.close_b.disabled=False
                    self.view.close_b.style=disnake.ButtonStyle.danger
                    self.view.close_b.label = "Close"
                    self.disabled=False
                    await self.view.bot.get_cog('GuildWar')._crew_sub(inter, self.values[0], 2, view=self.view)
                else:
                    await inter.edit_original_message(embed=self.view.bot.embed(title=self.view.embeds[0].title, description="{} Loading Profile `{}`...".format(self.view.bot.emote.get('time'), self.values[0]), color=self.view.color), view=self.view)
                    await asyncio.sleep(0.5)
                    self.view.close_b.disabled=False
                    self.view.close_b.style=disnake.ButtonStyle.danger
                    self.view.close_b.label = "Close"
                    self.disabled=False
                    await self.view.bot.get_cog('GranblueFantasy')._profile(inter, self.values[0], clean=True, color=self.view.color, view=self.view)
            except Exception as e:
                self.view.bot.logger.pushError("[PAGE] Error in dropdown callback with value: `{}` for search type: `{}`:".format(self.values[0], self.view.stype), e)
                self.view.close_b.disabled=False
                self.view.close_b.style=disnake.ButtonStyle.danger
                self.view.close_b.label = "Close"
                self.disabled=False
                await inter.edit_original_message(embed=self.view.bot.embed(title="Error", description="An unexpected error occured.\nMy owner has been notified.\nIf the problem persists, please wait for a fix.", color=self.view.color), view=self.view)
        else:
            await inter.response.send_message("You can't use this dropdown", ephemeral=True)

class PageRanking(BaseView):
    """__init__()
    Constructor
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    owner_id: the id of the user responsible for the interaction, leave to None to ignore
    embeds: list of embeds (one for each page)
    search_results: list of list of options for the dropdown (one list for each page)
    color: embed color
    stype: search type (True for crew, False for player)
    timeout: timeout in second before the interaction becomes invalid
    enable_timeout_cleanup: set to True to cleanup the interaction once over
    """
    def __init__(self, bot : 'DiscordBot', owner_id : int, embeds : list, search_results : list, color, stype : bool, timeout : float = 180.0, enable_timeout_cleanup : bool = False) -> None:
        super().__init__(bot, owner_id=owner_id, timeout=timeout, enable_timeout_cleanup=enable_timeout_cleanup)
        self.current = 0
        self.embeds = embeds
        self.search_results = search_results
        self.color = color
        self.stype = stype
        self.prev_b = self.children[0]
        self.prev_b.disabled=(len(embeds)<2)
        self.close_b = self.children[1]
        self.close_b.disabled=True
        self.next_b = self.children[2]
        self.next_b.disabled=(len(embeds)<2)
        self.add_item(RankingDropdown("Open Crew Page" if self.stype else "Open Profile", search_results[0]))
        self.dropdown = self.children[-1]
        if len(embeds) < 2:
            self.remove_item(self.prev_b).remove_item(self.next_b)

    """prev()
    The previous button coroutine callback.
    Change the self.message to the previous embed
    
    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='◀️', style=disnake.ButtonStyle.blurple)
    async def prev(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        try:
            if not button.disabled and self.ownership_check(interaction):
                if len(self.embeds) > 0:
                    self.current = (self.current + len(self.embeds) - 1) % len(self.embeds)
                    self.close_b.label = "Page {}".format(self.current + 1)
                    await interaction.send("\u200b", ephemeral=True, delete_after=0)
                    self.dropdown.update_options(self.search_results[self.current])
                    await self.message.edit(embed=self.embeds[self.current], view=self)
                else:
                    await interaction.send("Impossible to change pages", ephemeral=True)
            else:
                await interaction.response.send_message("You can't press this button", ephemeral=True)
        except Exception as e:
            await interaction.send("An unexpected error occured, my owner has been notified.", ephemeral=True)
            self.bot.logger.pushError("[VIEW] 'PageRanking' Prev Error (stype: `{}`, current: `{}`, len embeds: `{}`):".format(self.stype, self.current, len(self.embeds)), e)

    """close_profile()
    The close button coroutine callback.
    Allow you to return to the main embed after opening a profile
    
    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='Page 1', style=disnake.ButtonStyle.secondary)
    async def close_profile(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction):
            if len(self.embeds) > 0:
                await interaction.send("\u200b", ephemeral=True, delete_after=0)
                button.disabled=False
                button.style=disnake.ButtonStyle.secondary
                button.label = "Page {}".format(self.current + 1)
                if len(self.embeds) >= 2:
                    self.prev_b.disabled=False
                    self.prev_b.style=disnake.ButtonStyle.blurple
                    self.next_b.disabled=False
                    self.next_b.style=disnake.ButtonStyle.blurple
                await self.message.edit(embed=self.embeds[self.current], view=self)
            else:
                await interaction.send("Impossible to change pages", ephemeral=True)
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)

    """next()
    The next button coroutine callback.
    Change the self.message to the next embed
    
    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='▶️', style=disnake.ButtonStyle.blurple)
    async def next(self, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        try:
            if not button.disabled and self.ownership_check(interaction):
                if len(self.embeds) > 0:
                    self.current = (self.current + 1) % len(self.embeds)
                    self.close_b.label = "Page {}".format(self.current + 1)
                    await interaction.send("\u200b", ephemeral=True, delete_after=0)
                    self.dropdown.update_options(self.search_results[self.current])
                    await self.message.edit(embed=self.embeds[self.current], view=self)
                else:
                    await interaction.send("Impossible to change pages", ephemeral=True)
            else:
                await interaction.response.send_message("You can't press this button", ephemeral=True)
        except Exception as e:
            await interaction.send("An unexpected error occured, my owner has been notified.", ephemeral=True)
            self.bot.logger.pushError("[VIEW] 'PageRanking' Next Error (stype: `{}`, current: `{}`, len embeds: `{}`):".format(self.stype, self.current, len(self.embeds)), e)