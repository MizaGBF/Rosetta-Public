from __future__ import annotations
import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
from datetime import datetime, timedelta
import math

# ----------------------------------------------------------------------
# DreadBarrage Cog
# ----------------------------------------------------------------------
# Commands related to Dread Barrage events
# ----------------------------------------------------------------------


class DreadBarrage(commands.Cog):
    """Dread Barrage commands."""
    COLOR : int = 0x0062ff
    FIGHTS : dict[str, dict[str, float|int]] = {
        "1\\⭐": {"token":52.0, "AP":30},
        "2\\⭐": {"token":70.0, "AP":30},
        "3\\⭐": {"token":97.0, "AP":40},
        "4\\⭐": {"token":145.0, "AP":50},
        "5\\⭐": {"token":243.0, "AP":50}
    }

    BOX_COST : tuple[int|None, int] = [
        (1, 1800),
        (4, 2400),
        (20, 2002),
        (40, 10000),
        (None, 15000)
    ]

    __slots__ = ("bot")

    def __init__(self : DreadBarrage, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    def startTasks(self : DreadBarrage) -> None:
        pass

    """getBarrageState()
    Return the state of the Dread Barrage event

    Returns
    --------
    str: Dread Barrage state
    """
    def getBarrageState(self : DreadBarrage) -> str:
        if self.bot.data.save['dread']['state'] is True: # if enabled
            current_time : datetime = self.bot.util.JST()
            if current_time < self.bot.data.save['dread']['dates']["Day 1"]: # hasn't started
                d : timedelta = self.bot.data.save['dread']['dates']["Day 1"] - current_time
                return "{} Dread Barrage starts in **{}**".format(
                    self.bot.emote.get('crew'),
                    self.bot.util.delta2str(d, 2)
                )
            elif current_time >= self.bot.data.save['dread']['dates']["End"]: # has ended
                # we clear the data
                self.bot.data.save['dread']['state'] = False
                self.bot.data.save['dread']['dates'] = {}
                self.bot.data.pending = True
                return ""
            elif current_time >= self.bot.data.save['dread']['dates']["Day 1"]: # on going
                it : list[str] = ['End', 'Day 8', 'Day 7', 'Day 6', 'Day 5', 'Day 4', 'Day 3', 'Day 2', 'Day 1']
                # iterate from Day 8 to Day 1
                i : int
                for i in range(1, len(it)):
                    # check if we have passed this date
                    if (it[i] in self.bot.data.save['dread']['dates']
                            and current_time > self.bot.data.save['dread']['dates'][it[i]]):
                        next_it : str = it[i - 1]
                        # then check remaining time to next date (i-1)
                        if next_it not in self.bot.data.save['dread']['dates']:
                            # Add checks for optional days
                            next_it = 'End'
                        msgs : list[str] = [
                            "{} Barrage {} is on going (Time left: **{}**)".format(
                                self.bot.emote.get('mark_a'),
                                it[i],
                                self.bot.util.delta2str(
                                    self.bot.data.save['dread']['dates'][next_it] - current_time
                                )
                            )
                        ]
                        if current_time < self.bot.data.save['dread']['dates']['NM135']: # add NM135 timer if not passed
                            msgs.append(
                                "\n{} NM135 available in **{}**".format(
                                    self.bot.emote.get('mark'),
                                    self.bot.util.delta2str(
                                        self.bot.data.save['dread']['dates']['NM135'] - current_time,
                                        2
                                    )
                                )
                            )
                        elif current_time < self.bot.data.save['dread']['dates']['NM175']:
                            # add NM175 timer if not passed
                            msgs.append(
                                "\n{} NM175 available in **{}**".format(
                                    self.bot.emote.get('mark'),
                                    self.bot.util.delta2str(
                                        self.bot.data.save['dread']['dates']['NM175'] - current_time,
                                        2
                                    )
                                )
                            )
                        elif current_time < self.bot.data.save['dread']['dates']['NM215']:
                            # add NM175 timer if not passed
                            msgs.append(
                                "\n{} NM215 & Valiants available in **{}**".format(
                                    self.bot.emote.get('mark'),
                                    self.bot.util.delta2str(
                                        self.bot.data.save['dread']['dates']['NM215'] - current_time,
                                        2
                                    )
                                )
                            )
                        else:
                            # else add time to end
                            msgs.append(
                                "\n{} Barrage is ending in **{}**".format(
                                    self.bot.emote.get('time'),
                                    self.bot.util.delta2str(
                                        self.bot.data.save['dread']['dates'][it[0]] - current_time,
                                        2
                                    )
                                )
                            )
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
    def isDBRunning(self : DreadBarrage) -> bool:
        if self.bot.data.save['dread']['state'] is True:
            current_time : datetime = self.bot.util.JST()
            if current_time < self.bot.data.save['dread']['dates']["Day 1"]:
                return False
            elif current_time >= self.bot.data.save['dread']['dates']["End"]:
                # clear the data if ended
                self.bot.data.save['dread']['state'] = False
                self.bot.data.save['dread']['dates'] = {}
                self.bot.data.pending = True
                return False
            else:
                return True
        else:
            return False

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.max_concurrency(8, commands.BucketType.default)
    async def db(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @db.sub_command()
    async def time(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the Dread Barrage schedule"""
        await inter.response.defer()
        if self.bot.data.save['dread']['state'] is True:
            try:
                current_time : datetime = self.bot.util.JST()
                em : str = self.bot.util.formatElement(self.bot.data.save['dread']['element'])
                title : str = "{} **Dread Barrage {}** {} **{}**\n".format(
                    self.bot.emote.get('crew'),
                    self.bot.data.save['dread']['id'],
                    em,
                    self.bot.util.time(current_time, removejst=True)
                )
                description : list[str] = []
                # if on going
                if current_time < self.bot.data.save['dread']['dates']["End"]:
                    # add various dates based on progress
                    if current_time < self.bot.data.save['dread']['dates']["Day 2"]:
                        description.append(
                            "▫️ Start: **{}**\n".format(
                                self.bot.util.time(
                                    self.bot.data.save['dread']['dates']['Day 1'],
                                    removejst=True
                                )
                            )
                        )
                    if current_time < self.bot.data.save['dread']['dates']["Day 4"]:
                        description.append(
                            "▫️ NM135: **{}**\n".format(
                                self.bot.util.time(
                                    self.bot.data.save['dread']['dates']['NM135'],
                                    removejst=True
                                )
                            )
                        )
                    if current_time < self.bot.data.save['dread']['dates']["Day 5"]:
                        description.append(
                            "▫️ NM175: **{}**\n".format(
                                self.bot.util.time(
                                    self.bot.data.save['dread']['dates']['NM175'],
                                    removejst=True
                                )
                            )
                        )
                    if current_time < self.bot.data.save['dread']['dates']["Day 6"]:
                        description.append(
                            "▫️ NM215 & Valiants: **{}**\n".format(
                                self.bot.util.time(
                                    self.bot.data.save['dread']['dates']['NM215'],
                                    removejst=True
                                )
                            )
                        )
                    days : list[str] = [
                        d for d in list(self.bot.data.save['dread']['dates'].keys())
                        if d.startswith('Day')
                    ]
                    days.sort()
                    description.append(
                        "▫️ Last day: **{}**\n".format(
                            self.bot.util.time(
                                self.bot.data.save['dread']['dates'][days[-1]],
                                removejst=True
                            )
                        )
                    )
                else: # ended
                    await inter.edit_original_message(
                        embed=self.bot.embed(
                            title=f"{self.bot.emote.get('crew')} **Dread Barrage**",
                            description="Not available",
                            color=self.COLOR
                        )
                    )
                    # clear the data
                    self.bot.data.save['dread']['state'] = False
                    self.bot.data.save['dread']['dates'] = {}
                    self.bot.data.pending = True
                    await self.bot.channel.clean(inter, 40)
                    return
                try:
                    description.append(self.getBarrageState())
                except Exception as e:
                    self.bot.logger.pushError("[DREAD] 'getBarrageState' error:", e)

                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title=title,
                        description="".join(description),
                        color=self.COLOR
                    )
                )
            except Exception as e:
                self.bot.logger.pushError("[DREAD] In 'db time' command:", e)
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description="An unexpected error occured",
                        color=self.COLOR
                    )
                )
                await self.bot.channel.clean(inter, 40)
        else:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title=f"{self.bot.emote.get('crew')} **Dread Barrage**",
                    description="Not available",
                    color=self.COLOR
                )
            )
            await self.bot.channel.clean(inter, 40)

    @db.sub_command()
    async def token(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        value : str = commands.Param(description="Value to convert (support T, B, M and K)")
    ) -> None:
        """Convert Dread Barrage token values"""
        try:
            await inter.response.defer(ephemeral=True)
            tok : int = self.bot.util.strToInt(value)
            if tok < 1 or tok > 9999999999:
                raise Exception()
            b : int = 0 # box count
            t : int = tok # copy of token
            i : int = 0 # BOX_COST index
            # increase b (box count) until we run out of tok (tokens)
            while True:
                if tok < self.BOX_COST[i][1]: # not enough to empty box, we stop
                    break
                tok -= self.BOX_COST[i][1] # remove token cost
                b += 1 # increase box
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    # move BOX_COST index to next if it exists
                    i += 1
            # create message
            msgs : list[str] = [f"**{b:,}** box(s) and **{tok:,}** leftover tokens\n\n"]
            for f, d in self.FIGHTS.items():
                n : int = math.ceil(t / d["token"]) # number of fights needed
                # number of fight, fight name, half elixir count
                msgs.append(f"**{n:,}** {f} (**{n * d['AP'] // 75:,}** pots)\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Dread Barrage Token Calculator ▫️ {} tokens".format(
                        self.bot.emote.get('crew'),
                        t
                    ),
                    description="".join(msgs),
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Invalid token number",
                    color=self.COLOR
                )
            )

    @db.sub_command()
    async def box(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        box : int = commands.Param(
            description="Number of box to clear",
            ge=1,
            le=1000
        ),
        box_done : int = commands.Param(
            description="Your current box progress, default 0 (Will be ignored if equal or higher than target)",
            ge=0,
            default=0
        ),
        with_token : str = commands.Param(
            description="Your current token amount (support T, B, M and K)",
            default="0"
        )
    ) -> None:
        """Convert Dread Barrage box values"""
        try:
            await inter.response.defer(ephemeral=True)
            with_token_int : int = 0
            try:
                with_token_int = max(0, self.bot.util.strToInt(with_token))
            except:
                raise Exception(f"Your current token amount `{with_token}` isn't a valid number")
            if box_done >= box:
                raise Exception(
                    "Your current box count `{}` is higher or equal to your target `{}`".format(
                        box_done,
                        box
                    )
                )
            t : int = 0 # token needed
            i : int = 0 # BOX_COST index
            # we increase t (token needed) until we reach the targeted box count
            for b in range(box_done + 1, box + 1):
                while self.BOX_COST[i][0] is not None and b > self.BOX_COST[i][0]:
                    i += 1
                t += self.BOX_COST[i][1]
            # we remove with_token
            t : int = max(0, t - with_token_int)
            # create message
            msgs : list[str] = [
                "**{:,}** tokens needed{:}{:}\n\n".format(
                    t,
                    ("" if box_done == 0 else " from box **{}**".format(box_done + 1)),
                    ("" if with_token_int == 0 else " with **{:,}** tokens".format(with_token_int))
                )
            ]
            for f, d in self.FIGHTS.items():
                n : int = math.ceil(t / d["token"]) # number of fights needed
                msgs.append(f"**{n:,}** {f} (**{n * d['AP'] // 75:,}** pots)\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} Dread Barrage Token Calculator ▫️ Box {}".format(
                        self.bot.emote.get('crew'),
                        box
                    ),
                    description="".join(msgs),
                    color=self.COLOR
                )
            )
        except Exception as e:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description=str(e), color=self.COLOR))
