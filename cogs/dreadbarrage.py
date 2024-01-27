import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
import math

# ----------------------------------------------------------------------------------------------------------------
# DreadBarrage Cog
# ----------------------------------------------------------------------------------------------------------------
# Commands related to Dread Barrage events
# ----------------------------------------------------------------------------------------------------------------

class DreadBarrage(commands.Cog):
    """Dread Barrage commands."""
    COLOR = 0x0062ff

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    def startTasks(self) -> None:
        pass

    """getBarrageState()
    Return the state of the Dread Barrage event
    
    Returns
    --------
    str: Dread Barrage state
    """
    def getBarrageState(self) -> str: # return the current state of the valiant in string format (which day is on going, etc...)
        if self.bot.data.save['valiant']['state'] is True:
            current_time = self.bot.util.JST()
            if current_time < self.bot.data.save['valiant']['dates']["Day 1"]:
                d = self.bot.data.save['valiant']['dates']["Day 1"] - current_time
                return "{} Dread Barrage starts in **{}**".format(self.bot.emote.get('crew'), self.bot.util.delta2str(d, 2))
            elif current_time >= self.bot.data.save['valiant']['dates']["End"]:
                self.bot.data.save['valiant']['state'] = False
                self.bot.data.save['valiant']['dates'] = {}
                self.bot.data.pending = True
                return ""
            elif current_time >= self.bot.data.save['valiant']['dates']["Day 1"]:
                it = ['End', 'Day 6', 'Day 5', 'Day 4', 'Day 3', 'Day 2', 'Day 1']
                for i in range(1, len(it)):
                    if it[i] in self.bot.data.save['valiant']['dates'] and current_time > self.bot.data.save['valiant']['dates'][it[i]]:
                        msg = "{} Barrage {} is on going (Time left: **{}**)".format(self.bot.emote.get('mark_a'), it[i], self.bot.util.delta2str(self.bot.data.save['valiant']['dates'][it[i-1]] - current_time))
                        if current_time < self.bot.data.save['valiant']['dates']['NM135']:
                            msg += "\n{} NM135 available in **{}**".format(self.bot.emote.get('mark'), self.bot.util.delta2str(self.bot.data.save['valiant']['dates']['NM135'] - current_time, 2))
                        elif current_time < self.bot.data.save['valiant']['dates']['NM175']:
                            msg += "\n{} NM175 & Valiants available in **{}**".format(self.bot.emote.get('mark'), self.bot.util.delta2str(self.bot.data.save['valiant']['dates']['NM175'] - current_time, 2))
                        else:
                            msg += "\n{} Barrage is ending in **{}**".format(self.bot.emote.get('time'), self.bot.util.delta2str(self.bot.data.save['valiant']['dates'][it[0]] - current_time, 2))
                        return msg
            else:
                return ""
        else:
            return ""

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(8, commands.BucketType.default)
    async def db(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @db.sub_command()
    async def time(self, inter: disnake.GuildCommandInteraction) -> None:
        """Post the Dread Barrage schedule"""
        await inter.response.defer()
        if self.bot.data.save['valiant']['state'] is True:
            try:
                current_time = self.bot.util.JST()
                em = self.bot.util.formatElement(self.bot.data.save['valiant']['element'])
                title = "{} **Dread Barrage {}** {} **{}**\n".format(self.bot.emote.get('crew'), self.bot.data.save['valiant']['id'], em, self.bot.util.time(current_time, style='f', removejst=True))
                description = ""
                if current_time < self.bot.data.save['valiant']['dates']["End"]:
                    if current_time < self.bot.data.save['valiant']['dates']["Day 2"]:
                        description += "▫️ Start: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates']['Day 1'], style='f', removejst=True))
                    if current_time < self.bot.data.save['valiant']['dates']["Day 4"]:
                        description += "▫️ NM135: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates']['NM135'], style='f', removejst=True))
                    if current_time < self.bot.data.save['valiant']['dates']["Day 6"]:
                        description += "▫️ NM175 & Valiants: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates']['NM175'], style='f', removejst=True))
                    description += "▫️ Last day: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates']['Day 6'], style='f', removejst=True))
                else:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Dread Barrage**".format(self.bot.emote.get('crew')), description="Not available", color=self.COLOR))
                    self.bot.data.save['valiant']['state'] = False
                    self.bot.data.save['valiant']['dates'] = {}
                    self.bot.data.pending = True
                    await self.bot.util.clean(inter, 40)
                    return
                try:
                    description += self.getBarrageState()
                except Exception as e:
                    self.bot.logger.pushError("[DREAD] 'getBarrageState' error:", e)

                await inter.edit_original_message(embed=self.bot.embed(title=title, description=description, color=self.COLOR))
            except Exception as e:
                self.bot.logger.pushError("[DREAD] In 'db time' command:", e)
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="An unexpected error occured", color=self.COLOR))
                await self.bot.util.clean(inter, 40)
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="{} **Dread Barrage**".format(self.bot.emote.get('crew')), description="Not available", color=self.COLOR))
            await self.bot.util.clean(inter, 40)

    @db.sub_command()
    async def token(self, inter: disnake.GuildCommandInteraction, value : str = commands.Param(description="Value to convert (support T, B, M and K)")) -> None:
        """Convert Dread Barrage token values"""
        try:
            await inter.response.defer(ephemeral=True)
            tok = self.bot.util.strToInt(value)
            if tok < 1 or tok > 9999999999: raise Exception()
            b = 0
            t = tok
            if tok >= 1800:
                tok -= 1800
                b += 1
            while b < 4 and tok >= 2400:
                tok -= 2400
                b += 1
            while b < 20 and tok >= 2002:
                tok -= 2002
                b += 1
            while b < 40 and tok >= 10000:
                tok -= 10000
                b += 1
            while tok >= 15000:
                tok -= 15000
                b += 1
            s1 = math.ceil(t / 52.0)
            s2 = math.ceil(t / 70.0)
            s3 = math.ceil(t / 97.0)
            s4 = math.ceil(t / 146.0)
            s5 = math.ceil(t / 243.0)
            await inter.edit_original_message(embed=self.bot.embed(title="{} Dread Barrage Token Calculator ▫️ {} tokens".format(self.bot.emote.get('crew'), t), description="**{:,}** box(s) and **{:,}** leftover tokens\n**{:,}** 1⭐ (**{:,}** pots)\n**{:,}** 2⭐ (**{:,}** pots)\n**{:,}** 3⭐ (**{:,}** pots)\n**{:,}** 4⭐ (**{:,}** pots)\n**{:,}** 5⭐ (**{:,}** pots)".format(b, tok, s1, math.ceil(s1*30/75), s2, math.ceil(s2*30/75), s3, math.ceil(s3*40/75), s4, math.ceil(s4*50/75), s5, math.ceil(s5*50/75)), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid token number", color=self.COLOR))

    @db.sub_command()
    async def box(self, inter: disnake.GuildCommandInteraction, box : int = commands.Param(description="Number of box to clear", ge=1, le=1000), box_done : int = commands.Param(description="Your current box progress, default 0 (Will be ignored if equal or higher than target)", ge=0, default=0), with_token : str = commands.Param(description="Your current token amount (support T, B, M and K)", default="0")) -> None:
        """Convert Dread Barrage box values"""
        try:
            await inter.response.defer(ephemeral=True)
            t = 0
            try: with_token = max(0, self.bot.util.strToInt(with_token))
            except: raise Exception("Your current token amount `{}` isn't a valid number".format(with_token))
            if box_done >= box: raise Exception("Your current box count `{}` is higher or equal to your target `{}`".format(box_done, box))
            for b in range(box_done+1, box+1):
                if b == 1: t+= 1800
                elif b <= 4: t+= 2400
                elif b <= 20: t+= 2002
                elif b <= 40: t+= 10000
                else: t+= 15000
            t = max(0, t-with_token)
            s1 = math.ceil(t / 52.0)
            s2 = math.ceil(t / 70.0)
            s3 = math.ceil(t / 97.0)
            s4 = math.ceil(t / 146.0)
            s5 = math.ceil(t / 243.0)
            await inter.edit_original_message(embed=self.bot.embed(title="{} Dread Barrage Token Calculator ▫️ Box {}".format(self.bot.emote.get('crew'), box), description="**{:,}** tokens needed{}{}\n\n**{:,}** 1⭐ (**{:,}** pots)\n**{:,}** 2⭐ (**{:,}** pots)\n**{:,}** 3⭐ (**{:,}** pots)\n**{:,}** 4⭐ (**{:,}** pots)\n**{:,}** 5⭐ (**{:,}** pots)".format(t, ("" if box_done == 0 else " from box **{}**".format(box_done+1)), ("" if with_token == 0 else " with **{:,}** tokens".format(with_token)), s1, math.ceil(s1*30/75), s2, math.ceil(s2*30/75), s3, math.ceil(s3*40/75), s4, math.ceil(s4*50/75), s5, math.ceil(s5*50/75)), color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description=str(e), color=self.COLOR))