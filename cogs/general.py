﻿from __future__ import annotations
import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.util import BotCommandSearch, BotCommand
import math

# ----------------------------------------------------------------------
# General Cog
# ----------------------------------------------------------------------
# Bot general-themed commands
# ----------------------------------------------------------------------


class General(commands.Cog):
    """Rosetta commands."""
    COLOR : int = 0xd9d927

    __slots__ = ("bot")

    def __init__(self : General, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    """bug_report_callback()
    CustomModal callback
    """
    async def bug_report_callback(self : General, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        await inter.response.defer(ephemeral=True)
        # send the user report to the debug channel
        await self.bot.send(
            'debug',
            embed=self.bot.embed(
                title="Bug Report ▫️ " + inter.text_values['title'],
                description=inter.text_values['description'],
                footer="{} ▫️ User ID: {}".format(inter.author.name, inter.author.id),
                thumbnail=inter.author.display_avatar,
                color=self.COLOR
            )
        )
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Information",
                description='Thank you, your report has been sent with success',
                color=self.COLOR
            )
        )

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def bug_report(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Send a bug report or feedback to the developer"""
        await self.bot.singleton.make_and_send_modal(
            inter,
            "bug_report-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()),
            "Send a Bug / Feedback Report",
            self.bug_report_callback, [
                disnake.ui.TextInput(
                    label="Subject",
                    placeholder="Title of your issue",
                    custom_id="title",
                    style=disnake.TextInputStyle.short,
                    min_length=1,
                    max_length=140,
                    required=True
                ),
                disnake.ui.TextInput(
                    label="Description",
                    placeholder="Write your issue / feedback.",
                    custom_id="description",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=1,
                    max_length=800,
                    required=True
                )
            ]
        )

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(
        self : commands.slash_command,
        inter : disnake.ApplicationCommandInteraction,
        terms : str = commands.Param(description="What are you searching for?", default="")
    ) -> None:
        """Get the bot help or search global commands."""
        await inter.response.defer(ephemeral=True)
        msgs : list[str]
        if len(terms) == 0: # empty user input
            msgs = ["Online Help [here](https://mizagbf.github.io/discordbot.html)"]
        else:
            # geet bot slash command list
            global_slash_commands : list[BotCommand] = self.bot.global_slash_commands
            # breakdown user input
            search : list[str] = terms.split(' ')
            results = []
            # check if user is a mod (to show mod commands or not)
            is_mod : bool = self.bot.isMod(inter)
            # loop over commands
            command : disnake.APISlashCommand
            for command in global_slash_commands:
                # if /owner command or /mod command and user isn't mod, go to next command
                if command.name.lower() == "owner" or (command.name.lower() == "mod" and not is_mod):
                    continue
                # retrieve command name, description...
                rs : list[BotCommandSearch] = self.bot.util.process_command(command)
                # Search user terms inside these strings
                s : str
                r : list[None|int|str]
                for s in search:
                    for r in rs:
                        if (s in r[0] or s in r[2]) and r[2] != "Command Group": # ignore Command Groups
                            results.append(r)
            if len(results) == 0: # no results
                msgs = [
                    "No results found for `{}`\n".format(' '.join(search)),
                    "**For more help:**\n",
                    "Online Help [here](https://mizagbf.github.io/discordbot.html)"
                ]
            else:
                msgs = []
                length : int = 0
                count : int = len(results)
                # print matching commands
                for r in results:
                    msgs.append("</{}:{}> ▫️ *{}*\n".format(r[0], r[1], r[2]))
                    length += len(msgs[-1])
                    count -= 1
                    if length > 1500 and count > 0:
                        # if message too big, stop and put how many remaining commands were found
                        msgs.append(
                            (
                                "**And {} more commands...**\n**For more help:**\n"
                                "Online Help [here](https://mizagbf.github.io/discordbot.html)"
                            ).format(count)
                        )
                        break
        await inter.edit_original_message(
            embed=self.bot.embed(
                title=self.bot.user.name + " Help",
                description="".join(msgs),
                thumbnail=self.bot.user.display_avatar,
                color=self.COLOR,
                url="https://mizagbf.github.io/discordbot.html"
            )
        )

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(3, 10, commands.BucketType.guild)
    @commands.max_concurrency(6, commands.BucketType.default)
    async def rosetta(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @rosetta.sub_command()
    async def status(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the bot status"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="{} is Ready".format(
                    self.bot.user.display_name
                ),
                description=self.bot.util.statusString(),
                thumbnail=self.bot.user.display_avatar,
                timestamp=self.bot.util.UTC(),
                color=self.COLOR
            )
        )

    @rosetta.sub_command()
    async def changelog(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the bot changelog"""
        await inter.response.defer(ephemeral=True)
        msgs : list[str] = []
        # loop over changelog
        c : str
        for c in self.bot.CHANGELOG:
            # add command mentions
            # ` is the character used as delimiter
            e : list[str] = c.split('`')
            for i in range(1, len(e), 2):
                e[i] = self.bot.util.command2mention(e[i])
                if not e[i].startswith('<'):
                    e[i] = '`' + e[i] + '`'
            # add resulting line
            msgs.append("- ")
            msgs.extend(e)
            msgs.append("\n")
        if len(msgs) > 0:
            msgs.insert(0, "### Changelog\n")
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="{} ▫️ v{}".format(
                        inter.me.display_name,
                        self.bot.VERSION
                    ),
                    description="".join(msgs),
                    thumbnail=inter.me.display_avatar,
                    color=self.COLOR
                )
            )
        else:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="No Changelog available",
                    color=self.COLOR
                )
            )

    @rosetta.sub_command()
    async def pinboard(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the bot pinboard settings for this server"""
        await inter.response.defer(ephemeral=True)
        await self.bot.pinboard.render(inter, self.COLOR)

    @rosetta.sub_command()
    async def github(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the bot public github"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Rosetta",
                description=(
                    "Source code and issue tracker can be found "
                    "[here](https://github.com/MizaGBF/Rosetta-Public)."
                ),
                color=self.COLOR
            )
        )

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(5, 10, commands.BucketType.guild)
    @commands.max_concurrency(8, commands.BucketType.default)
    async def utility(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @utility.sub_command()
    async def calc(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        expression : str = commands.Param(description='Mathematical Expression')
    ) -> None:
        """Process a mathematical expression. Support variables (Example: cos(a + b) / c, a = 1, b=2,c = 3)."""
        try:
            await inter.response.defer()
            m : list[str] = expression.split(",") # split to separate variable definitions
            d : dict[str, float] = {} # variable container
            for i in range(1, len(m)): # process the variables if any
                x = m[i].replace(" ", "").split("=") # remove spaces and split around the equal
                if len(x) == 2:
                    d[x[0]] = float(x[1])
                else:
                    raise Exception('')
            # expression and result (using Calc singleton)
            msgs : list[str] = ["`{}` = **{}**".format(m[0], self.bot.singleton.make_calc(m[0], d))]
            if len(d) > 0: # add variables
                msgs.append("\nwith:\n")
                k : str
                for k in d:
                    msgs.append("{}".format(k))
                    msgs.append(" = ")
                    msgs.append("{}\n".format(d[k]))
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Calculator",
                    description="".join(msgs),
                    color=self.COLOR
                )
            )
        except Exception as e:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="Error\n{}".format(e),
                    color=self.COLOR
                )
            )
        await self.bot.channel.clean(inter, 60)

    @utility.sub_command()
    async def jst(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Post the current time, JST timezone"""
        await inter.response.defer(ephemeral=True)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="{} {:%Y/%m/%d %H:%M} JST".format(
                    self.bot.emote.get('clock'),
                    self.bot.util.JST()
                ),
                timestamp=self.bot.util.UTC(),
                color=self.COLOR
            )
        )

    @utility.sub_command()
    async def rollchance(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        count : str = commands.Param(
            description="Amount of rolls. Leave empty to use your set spark count",
            default=""
        ),
        banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)
    ) -> None:
        """Calculate your chance of rolling the rate up for a given amount of rolls."""
        await inter.response.defer(ephemeral=True)
        try:
            if count == '': # retrieve user roll count if they didn't pass a number
                if str(inter.author.id) in self.bot.data.save['spark']:
                    s : list[int] = self.bot.data.save['spark'][str(inter.author.id)]
                    count = (s[0] // 300) + s[1] + s[2] * 10
                else:
                    raise Exception("Please specify a valid number of rolls")
            elif int(count) <= 0:
                raise Exception("Please specify a valid number of rolls")
            else:
                count = int(count)
            msgs : list[str] = []
            ssrrate : float
            rateups : list[float]
            ssrrate, rateups = self.bot.gacha.allRates(banner) # retrieve rates
            if ssrrate is None:
                raise Exception(
                    (
                        "An error occured or no GBF gacha data is available.\n"
                        "Consider using {} instead in the meantime."
                    ).format(
                        self.bot.util.command2mention('utility dropchance')
                    )
                )
            # for each rate, we do a simple binomial calcul to determine the chance
            r : float
            for r in rateups:
                msgs.append(
                    "{:} **{:.3f}%** ▫️ {:.3f}%\n".format(
                        self.bot.emote.get('SSR'),
                        r,
                        100 * (1 - math.pow(1 - r * 0.01, count))
                    )
                )
            if len(msgs) > 0:
                msgs.insert(
                    0,
                    "Your chances of getting at least one SSR of the following rates with {} rolls:\n".format(
                        count
                    )
                )
            msgs.append("Your chances of getting at least one SSR with {} rolls:\n".format(count))
            msgs.append(
                "{:} **{:.2f}%** ▫️ {:.3f}%\n".format(
                    self.bot.emote.get('SSR'),
                    ssrrate,
                    100 * (1 - math.pow(1 - ssrrate * 0.01, count))
                )
            )
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Roll Chance Calculator",
                    description="".join(
                        msgs
                    ).replace(
                        '100.000%',
                        '99.999%'
                    ),
                    color=self.COLOR
                )
            ) # replace 100% by 99%. We assume 100% doesn't exist.
        except Exception as e:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Roll Chance Calculator Error",
                    description=str(e),
                    color=self.COLOR
                )
            )

    @utility.sub_command()
    async def dropchance(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        chance : str = commands.Param(description="Drop rate of the item (Format: Either XX% or 0.X)"),
        tries : int = commands.Param(description="Amount of tries, default is 1", default=1, ge=1, le=10000000)
    ) -> None:
        """Calculate your chance of dropping an item."""
        await inter.response.defer(ephemeral=True)
        try:
            chance : float
            # parse chance (we support either 10% or 0.1 for example)
            if chance.endswith('%'):
                chance = float(chance[:-1]) / 100
            else:
                chance = float(chance)
            # process
            if chance >= 1:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Drop Chance Calculator Error",
                        description="Chance can't be higher or equal than 100% or 1",
                        color=self.COLOR
                    )
                )
            else:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Drop Chance Calculator",
                        description=(
                            "Your chance of getting at least one {:.3f}% chance item"
                            "with **{:}** tries is **{:.3f}%**"
                        ).format(
                            chance * 100,
                            tries,
                            100 * (1 - math.pow(1 - chance, tries))
                        ).replace(
                            '100.000%',
                            '99.999%'
                        ),
                        color=self.COLOR
                    )
                ) # simple binomial calcul here
        except Exception as e:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Drop Chance Calculator Error",
                    description=str(e),
                    color=self.COLOR
                )
            )

    @utility.sub_command()
    async def fortunechance(
        self : commands.SubCommand,
        inter : disnake.ApplicationCommandInteraction,
        cards : str = commands.Param(description="Your list of cards, separated by spaces")
    ) -> None:
        """Calculate your chance at the GBF summer fortune game from Summer 2021"""
        await inter.response.defer(ephemeral=True)
        card_list : list[str] = cards.split(" ")
        tier3 : list[str] = []
        tier2 : list[str] = []
        tier1 : list[str] = []
        # we don't check tier 4 as at least 2 were guaranted
        c : str
        for c in card_list:
            try:
                if c == "":
                    continue
                if len(c) > 3 or int(c) < 0 or not c.isdigit():
                    raise Exception()
            except:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Error",
                        description="Invalid card number `{}`".format(c),
                        color=self.COLOR
                    )
                )
                return
            # convert card number to string
            sc : str = c.zfill(3)
            # retrieve relevant part of the card number for each tier
            if sc[:2] not in tier3:
                tier3.append(sc[:2])
            if sc[1:] not in tier2:
                tier2.append(sc[1:])
            if sc not in tier1:
                tier1.append(sc)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="Summer Fortune Calculator",
                description=(
                    "Your chances of winning at least one\n"
                    "**Tier 3** ▫️ {:.2f}%\n"
                    "**Tier 2** ▫️ {:.2f}%\n"
                    "**Tier 1** ▫️ {:.2f}%"
                ).format(
                    100 * (1 - math.pow(1 - 0.03, len(tier3))),
                    100 * (1 - math.pow(1 - 0.02, len(tier2))),
                    100 * (1 - math.pow(1 - 0.002, len(tier1)))
                ),
                color=self.COLOR
            )
        ) # simple binomial calcul for each tier

    @utility.sub_command()
    async def yen(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Retrieve the current yen conversion rate"""
        await inter.response.defer(ephemeral=True)
        try:
            # retrieve currency details
            data : str = (
                await self.bot.net.request(
                    "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist-90d.xml"
                )
            ).decode('utf-8').split('<Cube time="')
            # calcul yen, euro and dollar rates
            rates : tuple[list[None|float], list[None|float]] = (
                [None, None],
                [None, None]
            )
            date : str = data[1].split('">', 1)[0]
            i : int
            for i in range(0, 2):
                rates[0][i] = float(data[i + 1].split(
                    '<Cube currency="JPY" rate="',
                    1
                )[1].split(
                    '"/>',
                    1
                )[0])
                rates[1][i] = rates[0][i] / float(data[i + 1].split(
                    '<Cube currency="USD" rate="',
                    1
                )[1].split(
                    '"/>',
                    1
                )[0])
            for i in range(0, 2):
                rates[i][1] = 100 * rates[i][0] / rates[i][1] - 100
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title=":coin: Yen Rate ▫️ " + date,
                    description="▫️ 1 EUR \\↔️ {:.2f} JPY ({:+.2f}%)\n▫️ 1 USD \\↔️ {:.2f} JPY ({:+.2f}%)".format(
                        rates[0][0],
                        rates[0][1],
                        rates[1][0],
                        rates[1][1]
                    ),
                    color=self.COLOR
                )
            )
        except:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An unexpected error occured",
                    color=self.COLOR
                ),
                ephemeral=True
            )

    """translate_callback()
    CustomModal callback
    """
    async def translate_callback(self : General, modal : disnake.ui.Modal, inter : disnake.ModalInteraction) -> None:
        try:
            await inter.response.defer(ephemeral=True)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Google Translate",
                    description="```\n{}\n```".format(
                        self.bot.net.translate(inter.text_values['text'])
                    ),
                    color=self.COLOR
                )
            )
        except Exception as e:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An unexpected error occured:\n{}".format(e),
                    color=self.COLOR
                )
            )

    @utility.sub_command()
    async def translate(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Translate a text to english"""
        await self.bot.singleton.make_and_send_modal(
            inter,
            "translate-{}-{}".format(inter.id, self.bot.util.UTC().timestamp()),
            "Translate Text",
            self.translate_callback, [
                disnake.ui.TextInput(
                    label="Text",
                    placeholder="Text to translate",
                    custom_id="text",
                    style=disnake.TextInputStyle.paragraph,
                    min_length=1,
                    max_length=2000,
                    required=True
                )
            ]
        )

    @commands.message_command(name="Translate to English")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(1, 15, commands.BucketType.guild)
    async def translate_(
        self : commands.message_command,
        inter : disnake.MessageCommandInteraction,
        message: disnake.Message
    ) -> None:
        """Translate a message embed or content to english"""
        try:
            await inter.response.defer()
            # read message
            msg : str
            if len(message.embeds) > 0 and 'description' in message.embeds[0].to_dict():
                msg = message.embeds[0].description # read embed description if it got one
            elif len(message.content) > 0:
                msg = message.content
            else:
                raise Exception('Empty Message')
            if len(msg) > 3500:
                raise Exception('Message too long')
            # translate
            t : str = self.bot.net.translate(msg)
            if len(t) > 3800:
                raise Exception('Message too long')
            if inter.context.bot_dm or inter.guild is None:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Google Translate",
                        description="[Original Message](https://discord.com/channels/@me/{}/{})\n```\n{}\n```".format(
                            inter.channel.id,
                            message.id,
                            t
                        ),
                        color=self.COLOR
                    )
                )
            else:
                await inter.edit_original_message(
                    embed=self.bot.embed(
                        title="Google Translate",
                        description="[Original Message](https://discord.com/channels/{}/{}/{})\n```\n{}\n```".format(
                            inter.guild.id,
                            inter.channel.id,
                            message.id,
                            t
                        ),
                        color=self.COLOR
                    )
                )
        except Exception as e:
            if str(e) != 'Empty Message' and str(e) != 'Message too long':
                self.bot.logger.pushError('[TRANSLATE] Error:', e)
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="An unexpected error occured:\n`{}`".format(e),
                    color=self.COLOR
                )
            )
