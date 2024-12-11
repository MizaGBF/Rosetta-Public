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
    FIGHTS = {
        "1\\⭐": {"token":52.0, "AP":30},
        "2\\⭐": {"token":70.0, "AP":30},
        "3\\⭐": {"token":97.0, "AP":40},
        "4\\⭐": {"token":145.0, "AP":50},
        "5\\⭐": {"token":243.0, "AP":50}
    }

    BOX_COST = [
        (1, 1800),
        (4, 2400),
        (20, 2002),
        (40, 10000),
        (None, 15000)
    ]

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
                it = ['End', 'Day 8', 'Day 7', 'Day 6', 'Day 5', 'Day 4', 'Day 3', 'Day 2', 'Day 1']
                for i in range(1, len(it)):
                    if it[i] in self.bot.data.save['valiant']['dates'] and current_time > self.bot.data.save['valiant']['dates'][it[i]]:
                        msgs = ["{} Barrage {} is on going (Time left: **{}**)".format(self.bot.emote.get('mark_a'), it[i], self.bot.util.delta2str(self.bot.data.save['valiant']['dates'][it[i-1]] - current_time))]
                        if current_time < self.bot.data.save['valiant']['dates']['NM135']:
                            msgs.append("\n{} NM135 available in **{}**".format(self.bot.emote.get('mark'), self.bot.util.delta2str(self.bot.data.save['valiant']['dates']['NM135'] - current_time, 2)))
                        elif current_time < self.bot.data.save['valiant']['dates']['NM175']:
                            msgs.append("\n{} NM175 & Valiants available in **{}**".format(self.bot.emote.get('mark'), self.bot.util.delta2str(self.bot.data.save['valiant']['dates']['NM175'] - current_time, 2)))
                        else:
                            msgs.append("\n{} Barrage is ending in **{}**".format(self.bot.emote.get('time'), self.bot.util.delta2str(self.bot.data.save['valiant']['dates'][it[0]] - current_time, 2)))
                        return "".join(msgs)
            else:
                return ""
        else:
            return ""

    """isDBRunning()
    Check the DB state and returns if the DB is on going.
    Clear the data if it ended.
    
    Returns
    --------
    bool: True if it's running, False if it's not
    """
    def isDBRunning(self) -> bool:
        if self.bot.data.save['valiant']['state'] is True:
            current_time = self.bot.util.JST()
            if current_time < self.bot.data.save['valiant']['dates']["Day 1"]:
                return False
            elif current_time >= self.bot.data.save['valiant']['dates']["End"]:
                self.bot.data.save['valiant']['state'] = False
                self.bot.data.save['valiant']['dates'] = {}
                self.bot.data.pending = True
                return False
            else:
                return True
        else:
            return False

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
                title = "{} **Dread Barrage {}** {} **{}**\n".format(self.bot.emote.get('crew'), self.bot.data.save['valiant']['id'], em, self.bot.util.time(current_time, removejst=True))
                description = []
                if current_time < self.bot.data.save['valiant']['dates']["End"]:
                    if current_time < self.bot.data.save['valiant']['dates']["Day 2"]:
                        description.append("▫️ Start: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates']['Day 1'], removejst=True)))
                    if current_time < self.bot.data.save['valiant']['dates']["Day 4"]:
                        description.append("▫️ NM135: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates']['NM135'], removejst=True)))
                    if current_time < self.bot.data.save['valiant']['dates']["Day 6"]:
                        description.append("▫️ NM175 & Valiants: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates']['NM175'], removejst=True)))
                    days = [d for d in list(self.bot.data.save['valiant']['dates'].keys()) if d.startswith('Day')]
                    days.sort()
                    description.append("▫️ Last day: **{}**\n".format(self.bot.util.time(self.bot.data.save['valiant']['dates'][days[-1]], removejst=True)))
                else:
                    await inter.edit_original_message(embed=self.bot.embed(title="{} **Dread Barrage**".format(self.bot.emote.get('crew')), description="Not available", color=self.COLOR))
                    self.bot.data.save['valiant']['state'] = False
                    self.bot.data.save['valiant']['dates'] = {}
                    self.bot.data.pending = True
                    await self.bot.util.clean(inter, 40)
                    return
                try:
                    description.append(self.getBarrageState())
                except Exception as e:
                    self.bot.logger.pushError("[DREAD] 'getBarrageState' error:", e)

                await inter.edit_original_message(embed=self.bot.embed(title=title, description="".join(description), color=self.COLOR))
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
            i = 0
            while True:
                if tok < self.BOX_COST[i][1]:
                    break
                tok -= self.BOX_COST[i][1]
                b += 1
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    i += 1
            msgs = ["**{:,}** box(s) and **{:,}** leftover tokens\n\n".format(b, tok)]
            for f, d in self.FIGHTS.items():
                n = math.ceil(t / d["token"])
                msgs.append("**{:,}** {:} (**{:,}** pots)\n".format(n, f, n*d["AP"]//75))
            await inter.edit_original_message(embed=self.bot.embed(title="{} Dread Barrage Token Calculator ▫️ {} tokens".format(self.bot.emote.get('crew'), t), description="".join(msgs), color=self.COLOR))
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
            i = 0
            for b in range(box_done+1, box+1):
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    i += 1
                t += self.BOX_COST[i][1]
            t = max(0, t-with_token)
            msgs = ["**{:,}** tokens needed{:}{:}\n\n".format(t, ("" if box_done == 0 else " from box **{}**".format(box_done+1)), ("" if with_token == 0 else " with **{:,}** tokens".format(with_token)))]
            for f, d in self.FIGHTS.items():
                n = math.ceil(t/d["token"])
                msgs.append("**{:,}** {:} (**{:,}** pots)\n".format(n, f, n*d["AP"]//75))
            await inter.edit_original_message(embed=self.bot.embed(title="{} Dread Barrage Token Calculator ▫️ Box {}".format(self.bot.emote.get('crew'), box), description="".join(msgs), color=self.COLOR))
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description=str(e), color=self.COLOR))