import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Arcarum Cog
# ----------------------------------------------------------------------------------------------------------------
# Register and estimate people GBF Spark status
# ----------------------------------------------------------------------------------------------------------------

class Arcarum(commands.Cog):
    """Track your Granblue Spark."""
    COLOR = 0x991c50

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 10, commands.BucketType.user)
    @commands.max_concurrency(4, commands.BucketType.default)
    async def arcarum(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @arcarum.sub_command()
    async def route(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the available Arcarum Routes"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="{} Arcarum Routes".format(self.bot.emote.get('arcarum')), color=self.COLOR, description=":red_square: **Aquila** ▫️ [{} Caim](https://gbf.wiki/Caim),  [{} Fraux](https://gbf.wiki/Fraux), [{} Alanaan](https://gbf.wiki/Alanaan)\n:blue_square: **Bellator** ▫️ [{} Maria Theresa](https://gbf.wiki/Maria_Theresa),  [{} Haaselia](https://gbf.wiki/Haaselia), [{} Katzelia](https://gbf.wiki/Katzelia)\n:green_square: **Celsus** ▫️ [{} Nier](https://gbf.wiki/Nier),  [{} Estarriola](https://gbf.wiki/Estarriola), [{} Lobelia](https://gbf.wiki/Lobelia), [{} Geisenborger](https://gbf.wiki/Geisenborger)".format(self.bot.emote.get('earth'), self.bot.emote.get('fire'), self.bot.emote.get('fire'), self.bot.emote.get('water'), self.bot.emote.get('water'), self.bot.emote.get('wind'), self.bot.emote.get('dark'), self.bot.emote.get('wind'), self.bot.emote.get('earth'), self.bot.emote.get('light')), url="https://game.granbluefantasy.jp/#arcarum2"))

    @arcarum.sub_command()
    async def recruit(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the cost of recruiting an Evoker"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="{} Arcarum Recruit Evoker".format(self.bot.emote.get('arcarum')), color=self.COLOR, description="▫️ **137** Sephira stones\n▫️ **314** Astras\n▫️ **79** Ideans\n▫️ **82** Hazes\n▫️ **30** Fragments\n▫️ **572** Verum Proofs\n▫️ **1** Sunlight Stone", url="https://gbf.wiki/Arcarum_Evokers", footer="From scratch, excluding other materials"))

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 10, commands.BucketType.user)
    @commands.max_concurrency(4, commands.BucketType.default)
    async def sandbox(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @sandbox.sub_command()
    async def zone(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the available Sandbox Zones"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="{} Sandbox Zones".format(self.bot.emote.get('arcarum')), color=self.COLOR, description="{}{} [Eletio](https://game.granbluefantasy.jp/#replicard/stage/2) ▫️ [Invidia](https://game.granbluefantasy.jp/#replicard/stage/6)\n{}{} [Faym](https://game.granbluefantasy.jp/#replicard/stage/3) ▫️ [Joculator](https://game.granbluefantasy.jp/#replicard/stage/7)\n{}{} [Goliath](https://game.granbluefantasy.jp/#replicard/stage/4) ▫️ [Kalendae](https://game.granbluefantasy.jp/#replicard/stage/8)\n{}{} [Harbinger](https://game.granbluefantasy.jp/#replicard/stage/5) ▫️ [Liber](https://game.granbluefantasy.jp/#replicard/stage/9)\n{} [Mundus](https://game.granbluefantasy.jp/#replicard/stage/10)".format(self.bot.emote.get('fire'), self.bot.emote.get('light'), self.bot.emote.get('water'), self.bot.emote.get('dark'), self.bot.emote.get('earth'), self.bot.emote.get('dark'), self.bot.emote.get('wind'), self.bot.emote.get('light'), self.bot.emote.get('misc')), url="https://game.granbluefantasy.jp/#replicard"))

    @sandbox.sub_command()
    async def guide(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the available Sandbox Zones"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="{} Sandbox Guide".format(self.bot.emote.get('arcarum')), color=self.COLOR, description="**All Fights are color coded :red_square::green_square::yellow_square:**\n▫️ Look at the top left corner of the map (the sephira gauges) to see which color corresponds to which arcarum/element.\n▫️ Fight an enemy of a certain color to fill its gauge and the sephira gauge.\n▫️ The sephira gauge drops you a sephira chest.\n▫️ The fight gauge spawns a Defender.\n▫️ Beat a defender of each color to have the Boss Host materials.\n▫️ Colored Heralds can also spawn, providing various buffs to fights of one color.", url="https://game.granbluefantasy.jp/#replicard"))

    @sandbox.sub_command()
    async def domain(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the cost of unlocking an Evoker's domain"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="{} Sandbox Unlock Domain".format(self.bot.emote.get('arcarum')), color=self.COLOR, description="▫️ **50** (50) Sephira stones\n▫️ **110** (290) Astras\n▫️ **110** (210) Ideans\n▫️ **50** (50) Hazes\n▫️ **360** (810) Verum Proofs\n▫️ **30** (30) Arcarum Fragments\n▫️ **80** (400) Veritas\n▫️ **20** (120) Lusters\n▫️ **0** (40) New World Quartz\n▫️ **30** (30) Six-Dragon Advent Items", footer="with NWF 3★ cost between parenthesis"))

    @sandbox.sub_command()
    async def weapon(self, inter: disnake.GuildCommandInteraction) -> None:
        """Show the cost of making a New World Fundation weapon"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(embed=self.bot.embed(title="{} Sandbox New World Fundation weapon".format(self.bot.emote.get('arcarum')), color=self.COLOR, description="▫️ **180**/300/440 Astras\n▫️ **100**/200/300 Ideans\n▫️ **450**/700/700 Proofs\n▫️ **320**/470/640 Veritas\n▫️ **100**/160/230 Lusters\n▫️ **40**/60/90 New World Quartz\n▫️ **0**/0/3 Eternity Sands", footer="0-3★/4★/5★ cost"))