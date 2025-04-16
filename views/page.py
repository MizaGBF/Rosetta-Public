from __future__ import annotations
from . import BaseView
import disnake
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    # Type Aliases
    type PageResult = list[tuple[int|str, str]]
    type PageResultList = list[PageResult]

# ----------------------------------------------------------------------
# Page View
# ----------------------------------------------------------------------
# View class used to add Previous and Next buttons to cycle between multiple embeds
# ----------------------------------------------------------------------


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
    def __init__(
        self : Page,
        bot : DiscordBot,
        owner_id : int,
        embeds : list[disnake.Embed],
        timeout : float = 180.0,
        enable_timeout_cleanup : bool = False
    ) -> None:
        super().__init__(bot, owner_id=owner_id, timeout=timeout, enable_timeout_cleanup=enable_timeout_cleanup)
        self.current : int = 0 # current selected embed
        self.embeds : list[disnake.Embed] = embeds # list of embeds, one embed = one page

    """prev()
    The previous button coroutine callback.
    Change the self.message to the previous embed

    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='◀️', style=disnake.ButtonStyle.blurple)
    async def prev(self : Page, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction): # check if enabled and is view author
            if len(self.embeds) > 0:
                # cycle to previous page/embed
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
    async def next(self : Page, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction): # check if enabled and is view author
            if len(self.embeds) > 0:
                # cycle to next page/embed
                self.current = (self.current + 1) % len(self.embeds)
                await interaction.send("\u200b", ephemeral=True, delete_after=0)
                await self.message.edit(embed=self.embeds[self.current])
            else:
                await interaction.send("Impossible to change pages", ephemeral=True)
        else:
            await interaction.response.send_message("You can't press this button", ephemeral=True)


# ----------------------------------------------------------------------
# PageRanking View and dropdown
# ----------------------------------------------------------------------
# View class used to add Previous and Next buttons to cycle between multiple embeds
# Also add a select to browser player or crew profiles
# ----------------------------------------------------------------------

class RankingDropdown(disnake.ui.StringSelect):
    # The drop down
    def __init__(self : RankingDropdown, placeholder : str, search_results : PageResultList) -> None:
        # Define the options that will be presented inside the dropdown
        self.current_option_count = len(search_results)
        options : list[disnake.SelectOption]
        if len(search_results) == 0:
            options = [disnake.SelectOption(label="None", description="No data")]
        else:
            # List of selectable elements
            options = [disnake.SelectOption(label=s[0], description=str(s[1])) for s in search_results]
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=options
        ) # init the disnake.ui.StringSelect

    def update_options(self : RankingDropdown, search_results : PageResultList) -> None:
        self.current_option_count = len(search_results)
        if len(search_results) == 0:
            self.options = [disnake.SelectOption(label="None", description="No data")]
        else:
            # update the list of selectable elements
            options = [disnake.SelectOption(label=s[0], description=str(s[1])) for s in search_results]
            self.options = options # update the disnake.ui.StringSelect

    async def callback(self : RankingDropdown, inter : disnake.MessageInteraction) -> None:
        # called when a choice is made
        if not self.disabled and self.view.ownership_check(inter): # check if enabled and the view author
            if self.current_option_count == 0:
                await inter.response.send_message("No data selectable on this page", ephemeral=True)
                return
            # enable previous and next buttons if there are at least 2 pages
            if len(self.view.embeds) >= 2:
                self.view.prev_b.disabled = True
                self.view.prev_b.style = disnake.ButtonStyle.secondary
                self.view.next_b.disabled = True
                self.view.next_b.style = disnake.ButtonStyle.secondary
            self.view.close_b.disabled = True # disable the close button
            self.view.close_b.style = disnake.ButtonStyle.secondary
            self.disabled = True # disable this dropdown
            await inter.response.defer(ephemeral=True) # defer (for lag reasons)
            try:
                if self.view.stype: # crew profile
                    # set loading message
                    await inter.edit_original_message(
                        embed=self.view.bot.embed(
                            title=self.view.embeds[0].title,
                            description="{} Loading Crew `{}`...".format(
                                self.view.bot.emote.get('time'),
                                self.values[0]
                            ),
                            color=self.view.color
                        ),
                        view=self.view
                    )
                    await asyncio.sleep(0.5) # add delay to temper user expectation and keep them from spamming
                    # enable close button
                    self.view.close_b.disabled = False
                    self.view.close_b.style = disnake.ButtonStyle.danger
                    self.view.close_b.label = "Close"
                    self.disabled = False
                    # call GuildWar cog _crew_sub to open the crew profile in this interaction
                    await self.view.bot.get_cog('GuildWar')._crew_sub(inter, self.values[0], 2, view=self.view)
                else: # player profile
                    # set loading message
                    await inter.edit_original_message(
                        embed=self.view.bot.embed(
                            title=self.view.embeds[0].title,
                            description="{} Loading Profile `{}`...".format(
                                self.view.bot.emote.get('time'),
                                self.values[0]
                            ),
                            color=self.view.color
                        ),
                        view=self.view
                    )
                    await asyncio.sleep(0.5) # add delay to temper user expectation and keep them from spamming
                    # enable close button
                    self.view.close_b.disabled = False
                    self.view.close_b.style = disnake.ButtonStyle.danger
                    self.view.close_b.label = "Close"
                    self.disabled = False
                    # call GranblueFantasy cog _profile to open the player profile in this interaction
                    await self.view.bot.get_cog('GranblueFantasy')._profile(
                        inter,
                        self.values[0],
                        clean=True,
                        color=self.view.color,
                        view=self.view
                    )
            except Exception as e:
                self.view.bot.logger.pushError(
                    "[PAGE] Error in dropdown callback with value: `{}` for search type: `{}`:".format(
                        self.values[0],
                        self.view.stype
                    ),
                    e
                )
                # enable close button if it hasn't been enabled, so the user can return to pages
                self.view.close_b.disabled = False
                self.view.close_b.style = disnake.ButtonStyle.danger
                self.view.close_b.label = "Close"
                self.disabled = False
                # set error message
                await inter.edit_original_message(
                    embed=self.view.bot.embed(
                        title="Error",
                        description="An unexpected error occured.\n"
                        "My owner has been notified.\n"
                        "If the problem persists, please wait for a fix.",
                        color=self.view.color
                    ),
                    view=self.view
                )
        else:
            await inter.response.send_message("You can't use this dropdown", ephemeral=True)


class PageRanking(BaseView):
    """__init__()
    Constructor
    Note: contrary to its name, it's not an inheritor of the Page class

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
    def __init__(
        self : PageRanking,
        bot : DiscordBot,
        owner_id : int,
        embeds : list,
        search_results : PageResultList,
        color, stype : bool,
        timeout : float = 180.0,
        enable_timeout_cleanup : bool = False
    ) -> None:
        super().__init__(bot, owner_id=owner_id, timeout=timeout, enable_timeout_cleanup=enable_timeout_cleanup)
        self.current : int = 0 # current page/embed
        self.embeds : list[disnake.Embed] = embeds # list of pages/embeds
        # list of list for each pages. A list = dropdown selections for that page
        self.search_results : PageResultList = search_results
        self.color : int = color # embeds color
        self.stype : bool = stype # type of content, True for crews, False for players
        # buttons
        # Note: buttons are in order of the callback definitions below
        self.prev_b : disnake.ui.Component|None = self.children[0]
        self.prev_b.disabled = (len(embeds) < 2) # disable if single page
        self.close_b : disnake.ui.Component|None = self.children[1]
        self.close_b.disabled = True
        self.next_b : disnake.ui.Component|None = self.children[2]
        self.next_b.disabled = (len(embeds) < 2) # disable if single page
        # dropdown
        self.add_item(RankingDropdown("Open Crew Page" if self.stype else "Open Profile", search_results[0]))
        self.dropdown : disnake.ui.Component|None = self.children[-1]
        # remove previous and next buttons if single page
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
    async def prev(self : PageRanking, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        try:
            if not button.disabled and self.ownership_check(interaction): # check if enabled and author is view owner
                if len(self.embeds) > 0:
                    # cycle to previous page
                    self.current = (self.current + len(self.embeds) - 1) % len(self.embeds)
                    self.close_b.label = "Page {}".format(self.current + 1)
                    await interaction.send("\u200b", ephemeral=True, delete_after=0)
                    # update dropdown
                    self.dropdown.update_options(self.search_results[self.current])
                    # update message
                    await self.message.edit(embed=self.embeds[self.current], view=self)
                else:
                    await interaction.send("Impossible to change pages", ephemeral=True)
            else:
                await interaction.response.send_message("You can't press this button", ephemeral=True)
        except Exception as e:
            await interaction.send("An unexpected error occured, my owner has been notified.", ephemeral=True)
            self.bot.logger.pushError(
                "[VIEW] 'PageRanking' Prev Error (stype: `{}`, current: `{}`, len embeds: `{}`):".format(
                    self.stype,
                    self.current,
                    len(self.embeds)
                ),
                e
            )

    """close_profile()
    The close button coroutine callback.
    Allow you to return to the main embed after opening a profile

    Parameters
    ----------
    button: the Discord button
    button: a Discord interaction
    """
    @disnake.ui.button(label='Page 1', style=disnake.ButtonStyle.secondary)
    async def close_profile(self : PageRanking, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        if not button.disabled and self.ownership_check(interaction): # check if enabled and author is view owner
            if len(self.embeds) > 0:
                await interaction.send("\u200b", ephemeral=True, delete_after=0)
                # disable this button
                button.disabled = True
                button.style = disnake.ButtonStyle.secondary
                button.label = "Page {}".format(self.current + 1)
                # enable prev and next buttons if they exist
                if len(self.embeds) >= 2:
                    self.prev_b.disabled = False
                    self.prev_b.style = disnake.ButtonStyle.blurple
                    self.next_b.disabled = False
                    self.next_b.style = disnake.ButtonStyle.blurple
                # update message
                await self.message.edit(embed=self.embeds[self.current], view=self)
            else:
                await interaction.send("Impossible to close this Profile", ephemeral=True)
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
    async def next(self : PageRanking, button: disnake.ui.Button, interaction: disnake.Interaction) -> None:
        try:
            if not button.disabled and self.ownership_check(interaction): # check if enabled and author is view owner
                if len(self.embeds) > 0:
                    # cycle to previous page
                    self.current = (self.current + 1) % len(self.embeds)
                    self.close_b.label = "Page {}".format(self.current + 1)
                    await interaction.send("\u200b", ephemeral=True, delete_after=0)
                    # update dropdown
                    self.dropdown.update_options(self.search_results[self.current])
                    # update message
                    await self.message.edit(embed=self.embeds[self.current], view=self)
                else:
                    await interaction.send("Impossible to change pages", ephemeral=True)
            else:
                await interaction.response.send_message("You can't press this button", ephemeral=True)
        except Exception as e:
            await interaction.send("An unexpected error occured, my owner has been notified.", ephemeral=True)
            self.bot.logger.pushError(
                "[VIEW] 'PageRanking' Next Error (stype: `{}`, current: `{}`, len embeds: `{}`):".format(
                    self.stype,
                    self.current,
                    len(self.embeds)
                ),
                e
            )
