import disnake
from typing import Optional, TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Base View
# ----------------------------------------------------------------------------------------------------------------
# Base View class used as parent for the bot views
# ----------------------------------------------------------------------------------------------------------------

class BaseView(disnake.ui.View):
    """__init__()
    Constructor
    Base class used for our Bot views.
    
    Parameters
    ----------
    bot: a pointer to the bot for ease of access
    owner_id: the id of the user responsible for the interaction, leave to None to ignore
    timeout: timeout in second before the interaction becomes invalid
    enable_timeout_cleanup: if True, the original message will be cleaned up (if possible), if the time out is triggered
    """
    def __init__(self, bot : 'DiscordBot', owner_id : Optional[int] = None, timeout : float = 60.0, enable_timeout_cleanup : bool = True) -> None:
        super().__init__(timeout=timeout)
        self.bot : 'DiscordBot' = bot # reference to the bot
        self.owner_id = owner_id # id of whoever was the cause of this View creation
        self.message = None # used to store messages to display
        self.enable_timeout_cleanup = enable_timeout_cleanup # flag for the timeout auto cleanup

    """ownership_check()
    Check if the interaction user id matches the owner_id set in the constructor
    
    Parameters
    ----------
    interaction: a Discord interaction
    
    Returns
    --------
    bool: True if it matches, False if not
    """
    def ownership_check(self, interaction: disnake.Interaction) -> bool:
        return (self.owner_id is None or interaction.user.id == self.owner_id)

    """on_timeout()
    Coroutine callback
    Called when the view times out
    """
    async def on_timeout(self) -> None:
        self.stopall() # disable all children
        if self.enable_timeout_cleanup: # if auto cleanup is enabled
            if self.bot.channel.interaction_must_be_cleaned(self.message): # replace message by Lyria emote if authorized to
                try: await self.message.edit(content="{}".format(self.bot.emote.get('lyria')), embed=None, view=None, attachments=[])
                except: pass
            else: # else just remove the view
                try: await self.message.edit(view=None)
                except: pass
        else: # else simply update the view, to show it as disabled
            try: await self.message.edit(view=self)
            except: pass

    """stop()
    Override disnake.ui.View.stopall()
    """
    def stopall(self) -> None:
        for c in self.children: # iterate over view children
            try: c.disabled = True # and disable them
            except: pass
        self.stop() # then disable this view

    """on_error()
    Coroutine callback
    Called when the view triggers an error
    """
    async def on_error(self, error: Exception, item: disnake.ui.Item, interaction: disnake.Interaction) -> None:
        await self.bot.send('debug', embed=self.bot.embed(title="⚠ Error caused by {}".format(interaction.user), description="{} Exception\n{}".format(item, self.bot.pexc(error)), thumbnail=interaction.user.display_avatar, footer='{}'.format(interaction.user.id), timestamp=self.bot.util.UTC()))