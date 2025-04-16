from __future__ import annotations
from . import BaseView
import disnake
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot

# ----------------------------------------------------------------------
# Url Button View
# ----------------------------------------------------------------------
# View class used to open urls
# ----------------------------------------------------------------------


class UrlButton(BaseView):
    """__init__()
    Constructor

    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    urls: list of urls and their corresponding button label
    """
    def __init__(self : UrlButton, bot: DiscordBot, urls : list[list[str]]) -> None:
        super().__init__(bot)
        if len(urls) == 0:
            raise Exception("Empty url list")
        u: list[str]
        for u in urls: # add link buttons for each url
            self.add_item(
                disnake.ui.Button(
                    style=disnake.ButtonStyle.link,
                    label=u[0],
                    url=u[1]
                )
            )
