from __future__ import annotations
import disnake
from disnake.ext import commands
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.util import GameCard
    from components.gacha import GachaSimulator
    # Type Aliases
    type ScratcherItem = tuple[str, str]
    type ScratcherTierList = list[ScratcherItem]
    type ScratcherLootTable = dict[int, ScratcherTierList]
    type FortuneCardList = list[str]
    type FortuneWinningNumberList = list[str]
    type FortuneWinningNumberPerTier = tuple[FortuneWinningNumberList, FortuneWinningNumberList, FortuneWinningNumberList, FortuneWinningNumberList]
    type FortuneWinningPattern = tuple[int, int]
    type FortuneWinningPatternPerTier = tuple[FortuneWinningPattern, FortuneWinningPattern, FortuneWinningPattern, FortuneWinningPattern]
    type RandomCharacterStrings = tuple[str, str, str]
    type RandomCharacterContainer = dict[str, tuple[RandomCharacterStrings, int, bool, int|None]]
from datetime import datetime
import random
from views.scratcher import Scratcher
from views.chest_rush import ChestRush
from views.join_game import JoinGame
from views.tictactoe import TicTacToe
from views.connectfour import ConnectFour
from views.battleship import BattleShip
from views.blackjack import Blackjack
from views.poker import Poker
from views.rockpaperscissor import RPS

# ----------------------------------------------------------------------------------------------------------------
# Games Cog
# ----------------------------------------------------------------------------------------------------------------
# Fun commands
# ----------------------------------------------------------------------------------------------------------------

class Games(commands.Cog):
    """Granblue-themed (or not) Games and more."""
    COLOR : int = 0xeb6b34
    # Scratcher constants
    SCRATCHER_LOOT : ScratcherLootTable = {
        100 : [('Siero Ticket', 'item/article/s/30041.jpg')],
        1000 : [('Sunlight Stone', 'item/evolution/s/20014.jpg'), ('Gold Brick', 'item/evolution/s/20004.jpg'), ('Damascus Ingot', 'item/evolution/s/20005.jpg')],
        24000 : [('Murgleis', 'weapon/s/1040004600.jpg'), ('Benedia', 'weapon/s/1040502500.jpg'), ('Gambanteinn', 'weapon/s/1040404300.jpg'), ('Love Eternal', 'weapon/s/1040105400.jpg'), ('AK-4A', 'weapon/s/1040004600.jpg'), ('Reunion', 'weapon/s/1040108200.jpg'), ('Ichigo-Hitofuri', 'weapon/s/1040910000.jpg'), ('Taisai Spirit Bow', 'weapon/s/1040708700.jpg'), ('Unheil', 'weapon/s/1040809100.jpg'), ('Sky Ace', 'weapon/s/1040911500.jpg'), ('Ivory Ark', 'weapon/s/1040112500.jpg'), ('Blutgang', 'weapon/s/1040008700.jpg'), ('Eden', 'weapon/s/1040207000.jpg'), ('Parazonium', 'weapon/s/1040108700.jpg'), ('Ixaba', 'weapon/s/1040906400.jpg'), ('Blue Sphere', 'weapon/s/1040410000.jpg'), ('Certificus', 'weapon/s/1040309000.jpg'), ('Fallen Sword', 'weapon/s/1040014300.jpg'), ('Mirror-Blade Shard', 'weapon/s/1040110600.jpg'), ('Galilei\'s Insight', 'weapon/s/1040211600.jpg'), ('Purifying Thunderbolt', 'weapon/s/1040709000.jpg'), ('Vortex of the Void', 'weapon/s/1040212700.jpg'), ('Sacred Standard', 'weapon/s/1040213400.jpg'), ('Bab-el-Mandeb', 'weapon/s/1040004600.jpg'), ('Cute Ribbon', 'weapon/s/1040605900.jpg'), ('Kerak', 'weapon/s/1040812000.jpg'), ('Sunya', 'weapon/s/1040811800.jpg'), ('Fist of Destruction', 'weapon/s/1040612700.jpg'), ('Yahata\'s Naginata', 'weapon/s/1040312900.jpg'), ('Cerastes', 'weapon/s/1040215300.jpg'), ('World Ender', 'weapon/s/1040020900.jpg'), ('Ouroboros Prime', 'weapon/s/1040418600.jpg'), ('Evanescence', 'weapon/s/1040022000.jpg'), ('Knight of Ice', 'weapon/s/1040115600.jpg'), ('Atlantis', 'weapon/s/1040115600.jpg'), ('Skeletal Eclipse', 'weapon/s/1040216900.jpg'), ('Pain and Suffering', 'weapon/s/1040314300.jpg'), ('Radiant Rinne', 'weapon/s/1040813700.jpg'), ('Lord of Flames', 'weapon/s/1040023700.jpg'), ('Claíomh Solais Díon', 'weapon/s/1040024200.jpg'), ('Firestorm Scythe', 'weapon/s/1040314900.jpg'), ('Calamitous Aquashade', 'weapon/s/1040315500.jpg'), ('Crimson Scale', 'weapon/s/1040315900.jpg'), ('Landslide Scepter', 'weapon/s/1040420500.jpg'), ('Harmonia', 'weapon/s/1040814500.jpg'), ('Eternal Signature', 'weapon/s/1040116600.jpg'), ('Piercing Galewing', 'weapon/s/1040116800.jpg'), ('Kaguya\'s Folding Fan', 'weapon/s/1040117200.jpg'), ('Gospel Of Water And Sky', 'weapon/s/1040117800.jpg'), ('Overrider', 'weapon/s/1040218900.jpg'), ('Imperious Fury', 'weapon/s/1040617300.jpg'), ('Pillardriver', 'weapon/s/1040618200.jpg'), ('Diaitesia', 'weapon/s/1040815700.jpg'), ('Efes', 'weapon/s/1040025900.jpg'), ('Swan', 'weapon/s/1040318400.jpg'), ('Phoenix\'s Torch', 'weapon/s/1040422700.jpg'), ('Causality Driver', 'weapon/s/1040916700.jpg'), ('Bloodwrought Coral', 'weapon/s/1040916800.jpg'), ('Agni', 'summon/s/2040094000.jpg'), ('Varuna', 'summon/s/2040100000.jpg'), ('Titan', 'summon/s/2040084000.jpg'), ('Zephyrus', 'summon/s/2040098000.jpg'), ('Zeus', 'summon/s/2040080000.jpg'), ('Hades', 'summon/s/2040090000.jpg'), ('Shiva', 'summon/s/2040185000.jpg'), ('Europa', 'summon/s/2040225000.jpg'), ('Godsworn Alexiel', 'summon/s/2040205000.jpg'), ('Grimnir', 'summon/s/2040261000.jpg'), ('Lucifer', 'summon/s/2040056000.jpg'), ('Bahamut', 'summon/s/2040030000.jpg'), ('Michael', 'summon/s/2040306000.jpg'), ('Gabriel', 'summon/s/2040311000.jpg'), ('Uriel', 'summon/s/2040203000.jpg'), ('Raphael', 'summon/s/2040202000.jpg'), ('Metatron', 'summon/s/2040330000.jpg'), ('Sariel', 'summon/s/2040327000.jpg'), ('Belial', 'summon/s/2040347000.jpg'), ('Beelzebub', 'summon/s/2040408000.jpg'), ('Yatima', 'summon/s/2040417000.jpg'), ('Triple Zero', 'summon/s/2040425000.jpg')],
        80000 : [('Crystals x3000', 'item/normal/s/gem.jpg'), ('Damascus Crystal', 'item/article/s/203.jpg'), ('Intricacy Ring', 'item/npcaugment/s/3.jpg'), ('Gold Moon x2', 'item/article/s/30033.jpg'), ('Brimston Earrings', 'item/npcaugment/s/11.jpg'), ('Permafrost Earrings', 'item/npcaugment/s/12.jpg'), ('Brickearth Earrings', 'item/npcaugment/s/13.jpg'), ('Jetstream Earrings', 'item/npcaugment/s/14.jpg'), ('Sunbeam Earrings', 'item/npcaugment/s/15.jpg'), ('Nightshade Earrings', 'item/npcaugment/s/16.jpg')],
        90000 : [('Gold Spellbook', 'item/evolution/s/20403.jpg'), ('Moonlight Stone', 'item/evolution/s/20013.jpg'), ('Ultima Unit x3', 'item/article/s/138.jpg'), ('Silver Centrum x5', 'item/article/s/107.jpg'), ('Primeval Horn x3', 'item/article/s/79.jpg'), ('Horn of Bahamut x4', 'item/article/s/59.jpg'), ('Legendary Merit x5', 'item/article/s/2003.jpg'), ('Steel Brick', 'item/evolution/s/20003.jpg')],
        85000 : [('Lineage Ring x2', 'item/npcaugment/s/2.jpg'), ('Coronation Ring x3', 'item/npcaugment/s/1.jpg'), ('Silver Moon x5', 'item/article/s/30032.jpg'), ('Bronze Moon x10', 'item/article/s/30031.jpg')],
        70000: [('Elixir x100', 'item/normal/s/2.jpg'), ('Soul Berry x300', 'item/normal/s/5.jpg')]
    }
    SCRATCHER_TOTAL : int = sum([r for r in SCRATCHER_LOOT]) # sum of all rates
    SCRATCHER_THRESHOLD_GRAND : int = 100+1000+24000 # rarity threshold of super rare items (Murgleis or rarer)
    SCRATCHER_THRESHOLD_GOOD : int = SCRATCHER_THRESHOLD_GRAND+80000 # rarity threshold of rare items (Crystals or rarer)
    # Chestrush constants
    CHESTRUSH_LOOT : dict[str, int] = {
        'Murgleis':105, 'Benedia':105, 'Gambanteinn':105, 'Love Eternal':105, 'AK-4A':105, 'Reunion':105, 'Ichigo-Hitofuri':105, 'Taisai Spirit Bow':105, 'Unheil':105, 'Sky Ace':105, 'Ivory Ark':105, 'Blutgang':105, 'Eden':105, 'Parazonium':105, 'Ixaba':105, 'Blue Sphere':105, 'Certificus':105, 'Fallen Sword':105, 'Mirror-Blade Shard':105, 'Galilei\'s Insight':105, 'Purifying Thunderbolt':105, 'Vortex of the Void':105, 'Sacred Standard':105, 'Bab-el-Mandeb':105, 'Cute Ribbon':105, 'Kerak':105, 'Sunya':105, 'Fist of Destruction':105, 'Yahata\'s Naginata':105, 'Cerastes':105, 'World Ender':105, 'Ouroboros Prime':105, 'Evanescence':105, 'Knight of Ice':105, 'Atlantis':105, 'Skeletal Eclipse':105, 'Pain and Suffering':105, 'Radiant Rinne':105, 'Lord of Flames':105, 'Claíomh Solais Díon':105, 'Firestorm Scythe':105, 'Calamitous Aquashade':105, 'Crimson Scale':105, 'Landslide Scepter':105, 'Harmonia':105, 'Eternal Signature':105, 'Piercing Galewing':105, 'Kaguya\'s Folding Fan':105, 'Gospel Of Water And Sky':105, 'Overrider':105, 'Imperious Fury':105, 'Pillardriver':105, 'Diaitesia':105, 'Efes':105, 'Swan':105, 'Phoenix\'s Torch':105, 'Causality Driver':105, 'Bloodwrought Coral':105,
        'Agni':105, 'Varuna':105, 'Titan':105, 'Zephyrus':105, 'Zeus':105, 'Hades':105, 'Shiva':105, 'Europa':105, 'Godsworn Alexiel':105, 'Grimnir':105, 'Lucifer':105, 'Bahamut':105, 'Michael':105, 'Gabriel':105, 'Uriel':105, 'Raphael':105, 'Metatron':105, 'Sariel':105, 'Belial':105, 'Beelzebub':105, 'Yatima':105, 'Triple Zero':105,
        '10K Crystal':100,
        '3K Crystal':400,'Intricacy Ring x3':400,'Damascus Crystal x3':400, 'Premium 10-Part Ticket':400,
        'Intricacy Ring':500, 'Lineage Ring x2':500, 'Coronation Ring x3':500, 'Gold Moon x2':500,
        'Gold Moon':800, 'Silver Moon x5':800, 'Bronze Moon x10':800, 'Premium Draw Ticket':800, 'Gold Spellbook x3':800,
        'Half Elixir x10':1000, 'Soul Berry x10':1000, 
        "Satin Feather x10":1250, "Zephyr Feather x10":1250, "Untamed Flame x10":1250, "Rough Stone x10":1250, "Fresh Water Jug x10":1250, "Swirling Amber x10":1250, "Falcon Feather x10":1250, "Vermilion Stone x10":1250, "Hollow Soul x10":1250, "Lacrimosa x10":1250, "Foreboding Clover x10":1250, "Blood Amber x10":1250, "Antique Cloth x10":1250, 
        "White Dragon Scale x10":1250, "Champion Merit x10":1250, "Supreme Merit x10":1250, "Blue Sky Crystal x10":1250, "Rainbow Prism x10":1250, "Rubeus Centrum x10":1250, "Indicus Centrum x10":1250, "Luteus Centrum x10":1250, "Galbinus Centrum x10":1250, "Niveus Centrum x10":1250, "Ater Centrum x10":1250, "Fire Urn x10":1250, "Water Urn x10":1250, "Earth Urn x10":1250, "Wind Urn x10":1250, "Light Urn x10":1250, "Dark Urn x10":1250, "Horn of Bahamut x10":1250, "Primeval Horn x10":1250, "Legendary Merit":1250, 
        "Sword Stone x50":1000, "Dagger Stone x50":1000, "Spear Stone x50":1000, "Axe Stone x50":1000, "Staff Stone x50":1000, "Pistol Stone x50":1000, "Melee Stone x50":1000, "Bow Stone x50":1000, "Harp Stone x50":1000, "Katana Stone x50":1000, "Silver Centrum x5":1000, "Ultima Unit x3":1000, "Fire Quartz x50":1000, "Water Quartz x50":1000, "Earth Quartz x50":1000, "Wind Quartz x50":1000, "Light Quartz x50":1000, "Dark Quartz x50":1000, "Shiva Omega Anima x3":1000, "Europa Omega Anima x3":1000, "Alexiel Omega Anima x3":1000, "Grimnir Omega Anima x3":1000, "Metatron Omega Anima x3":1000, "Avatar Omega Anima x3":1000
    }
    
    def __init__(self : Games, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def roll(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @roll.sub_command()
    async def single(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a single draw"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("single", banner, self.COLOR)
        await sim.generate(1, legfest)
        await sim.render(inter, 0, ("{} did a single roll...", "{} did a single roll"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def ten(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate ten draws"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.generate(10, legfest)
        await sim.render(inter, 1, ("{} did ten rolls...", "{} did ten rolls"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command(name="scam")
    async def scam_(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), scam_index : int = commands.Param(description='Which Scam gacha to use (Default: 1 for the first one)', default=1, ge=1)) -> None:
        """Simulate ten draws and the Scam Gacha"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("scam", "scam", self.COLOR, scamindex=scam_index)
        await sim.generate(10, legfest)
        await sim.render(inter, 1, ("{} is getting Scammed...", "{} got Scammed"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def spark(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a spark"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.generate(300, legfest)
        await sim.render(inter, 3, ("{} is sparking...", "{} sparked"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def count(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, num : int = commands.Param(description='Number of rolls (2 ~ 600)', ge=2, le=600), legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a specific amount of draw"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.generate(num, legfest)
        await sim.render(inter, 3, ("{}" + " is rolling {} times...".format(num), "{} " + "rolled {} times".format(num)))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def gachapin(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a Gachapin Frenzy"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("gachapin", banner, self.COLOR)
        await sim.generate(300, legfest)
        await sim.render(inter, 3, ("{} is rolling the Gachapin...", "{} rolled the Gachapin"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def mukku(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a Mukku Frenzy"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("mukku", banner, self.COLOR)
        await sim.generate(300)
        await sim.render(inter, 3, ("{} is rolling the Mukku...", "{} rolled the Mukku"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def supermukku(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a Super Mukku Frenzy"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("supermukku", banner, self.COLOR)
        await sim.generate(300)
        await sim.render(inter, 3, ("{} is rolling the Supper Mukku...", "{} rolled the Super Mukku"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def memeroll(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), rateup : str = commands.Param(description='Input anything to roll until a rate up SSR', default=""), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate rolls until a SSR"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("memerollB" if rateup != "" else "memerollA", banner, self.COLOR)
        await sim.generate(300, legfest)
        await sim.render(inter, 2, ("{} is memerolling...", "{} memerolled {} times"))
        await self.bot.channel.clean(inter, 40)

    @roll.sub_command()
    async def roulette(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0), realist : int = commands.Param(description='1 to set Realist Mode (if allowed by owner)', default=0, ge=0, le=1)) -> None:
        """Imitate the GBF roulette"""
        await inter.response.defer()
        sim : GachaSimulator = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.roulette(inter, legfest, (realist==1))
        await self.bot.channel.clean(inter, 50)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 40, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def game(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @game.sub_command()
    async def scratch(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Imitate the GBF scratch game from Anniversary 2020"""
        await inter.response.defer()
        ct : datetime = self.bot.util.JST()
        # settings
        # these settings are here to set a period, during which, the scratcher loot is boosted, to emulate what was done in march 2021
        fixedS : datetime = ct.replace(year=2021, month=3, day=29, hour=19, minute=0, second=0, microsecond=0) # beginning of good scratcher
        fixedE : datetime = fixedS.replace(day=31, hour=19) # end of good scratcher
        enableBetterDuringPeriod : bool = True
        betterScratcher : bool = False # if true, only good results possible (set to True below if the some conditions are fulfilled)
        # settings end
        
        # check for better scratcher loot
        if enableBetterDuringPeriod and ct >= fixedS and ct < fixedE:
            betterScratcher = True
        if random.randint(1, 100) <= 10: # to simulate the rare scratcher card thing, currently 10%
            betterScratcher = True

        # scratcher generation
        footer : str = "Rare card" if betterScratcher else ""
        selected : dict[tuple[str, str], int] = {}
        nloot : int = random.randint(4, 5) # number of different items (4 or 5)
        n : int
        item : ScratcherItem
        while len(selected) < nloot:
            # dice roll
            if betterScratcher:
                n = random.randint(1, self.SCRATCHER_THRESHOLD_GOOD) - 1
            elif len(selected) == 1: # Force a rare item in the list, for extra salt
                n = random.randint(1, self.SCRATCHER_THRESHOLD_GRAND) - 1
            else:
                n = random.randint(1, self.SCRATCHER_TOTAL) - 1
            # search corresponding loot category
            rate : int
            for rate in self.SCRATCHER_LOOT:
                if n >= rate:
                    n -= rate
                else:
                    n = rate
                    break
            # validate
            can_continue : bool = False
            if len(self.SCRATCHER_LOOT[n]) < nloot: # check if category has enough remaining items
                for item in self.SCRATCHER_LOOT[n]:
                    if item not in selected:
                        can_continue = True
                        break
            else:
                can_continue = True
            if not can_continue:
                continue
            # roll items
            item = random.choice(self.SCRATCHER_LOOT[n])
            while item in selected:
                item = random.choice(self.SCRATCHER_LOOT[n])
            selected[item] = 0
        
        # build the scratch grid
        grid : list[ScratcherItem] = []
        keys : list[ScratcherItem] = list(selected.keys())
        for item in keys: # add all our loots once
            grid.append(item)
            selected[item] = 1
        # add the first one twice (it's the winning one)
        grid.append(keys[0])
        grid.append(keys[0])
        selected[keys[0]] = 3
        nofinal : bool = False
        while len(grid) < 10: # fill the grid up to TEN times
            n = random.randint(1, len(keys)-1)
            if selected[keys[n]] < 2:
                grid.append(keys[n])
                selected[keys[n]] += 1
            elif len(grid) == 9: # 10 means final scratch so we stop at 9 and raise a flag if the chance arises
                grid.append('')
                nofinal = True
                break
        while True: # shuffle the grid until we get a valid one
            random.shuffle(grid)
            if nofinal and grid[-1] == "":
                break
            elif not nofinal and grid[-1] == keys[0]:
                break
            await asyncio.sleep(0)
        # call the game view
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} is scratching...".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="Click to play the game", footer=footer, color=self.COLOR), view=Scratcher(self.bot, inter.author.id, grid, self.COLOR, footer))
        await self.bot.channel.clean(inter, 45)

    @game.sub_command()
    async def chestrush(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Imitate the GBF treasure game from Summer 2020"""
        await inter.response.defer()
        mm : int = 0 # maximum random loot value
        rm : int = 0 # rare loot value
        item : str
        for item in self.CHESTRUSH_LOOT:
            mm += self.CHESTRUSH_LOOT[item] # calculated here
            if item == 'Premium 10-Part Ticket': rm = mm

        # roll items
        results : list[str] = []
        l : int = random.randint(1, 9) # number if items
        while len(results) < l:
            n : int = random.randint(1, mm)
            c : int = 0
            check : str = ""
            for item in self.CHESTRUSH_LOOT:
                if n < c + self.CHESTRUSH_LOOT[item]:
                    check = item
                    break
                else:
                    c += self.CHESTRUSH_LOOT[item]
            if check != "":
                if n < rm and len(results) == l - 1:
                    results.append("###" + check) # special chest
                elif n < rm:
                    results.append("$$$" + check) # rare self.CHESTRUSH_LOOT
                else:
                    results.append(check) # normal self.CHESTRUSH_LOOT
        results.reverse()
        # call the game view
        await inter.edit_original_message(embed=self.bot.embed(author={'name':'{} is opening chests...'.format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, color=self.COLOR), view=ChestRush(self.bot, inter.author.id, results, self.COLOR))
        await self.bot.channel.clean(inter, 45)

    """genLoto()
    Generate cards and winning numbers for the summer fortune minigame
    
    Returns
    --------
    tuple: Containing:
        - List of cards
        - List of tier winning digits
    """
    async def genLoto(self : Games) -> tuple[FortuneCardList, FortuneWinningNumberPerTier]:
        # generate 13 cards
        cards : FortuneCardList = []
        while len(cards) < 13:
            if len(cards) < 10:
                c : str = str(10 * random.randint(0, 99) + len(cards) % 10).zfill(3) # generate unique last digit
            else:
                c : str = str(random.randint(0, 999)).zfill(3)
            if c not in cards:
                cards.append(c)
                if len(cards) == 10:
                    random.shuffle(cards)
            await asyncio.sleep(0)
        # generate winning numbers for each tiers
        winning : FortuneWinningNumberPerTier = ([], [], [], []) # tier 1 to 4
        patterns : FortuneWinningPatternPerTier = ((3, 2), (2, 2), (2, 3), (1, 2)) # (number of digits, number of winning numbers)
        tier : int
        pattern : tuple[int, int]
        for tier, pattern in enumerate(patterns):
            # generate the max number according to the pattern, for the rng roll
            # for example 1000 for a 3 digits number (000 to 999)
            pad : str = '{:<0' + str(pattern[0]+1) + 'd}'
            pad = int(pad.format(1))
            # roll winning numbers for that pattern
            i : int
            for i in range(0, pattern[1]):
                while True:
                    card : str = str(random.randint(0, pad-1)).zfill(pattern[0]) # random and pad string
                    if card not in winning[tier]: # check if already rolled
                        winning[tier].append(card)
                        break
                    await asyncio.sleep(0)
        return cards, winning

    """printLoto()
    Generate the string and thumbnail for the summer fortune minigame
    
    Parameters
    ----------
    revealedCards: List of revealed cards
    revealedWinning: Tuple of list of revealed winning digits
    prize: List of prize won currently
    total: If true, will print the total prize won
    
    Returns
    --------
    tuple: Containing:
        - Description string
        - Thumbnail url
    """
    async def printLoto(self : Games, revealedCards : FortuneCardList, revealedWinning : FortuneWinningNumberPerTier, prize : list[int], total : bool = False) -> tuple[str, str|None]:
        desc : list[str] = []
        thumb : str|None = None
        i : int
        # show winning numbers
        if len(revealedWinning) > 0:
            desc.append("The winning numbers are:\n")
            for i in range(0, len(revealedWinning)):
                desc.append("**Tier {}**▫️".format(4-i))
                match i:
                    case 0: desc.append("Last Digit▫️") # tier 4
                    case 1: desc.append("First Two▫️") # tier 3
                    case 2: desc.append("Last Two▫️") # tier 2
                desc.append("{} ".format(', '.join(revealedWinning[len(revealedWinning)-1-i])))
                # show emote for won prizes
                j : int
                for j in range(0, prize[3-i]):
                    desc.append(":confetti_ball:")
                desc.append("\n")
        # show revealed cards
        if len(revealedCards) > 0:
            desc.append("Your cards are: ")
            for card in revealedCards:
                desc.append(card)
                if card is not revealedCards[-1]:
                    desc.append(", ")
        await asyncio.sleep(0)
        # add prize thumbnail
        if total:
            if sum(prize) == 0:
                desc.append("\n{} You won nothing".format(self.bot.emote.get('kmr')))
            else:
                if prize[0] > 0:
                    desc.append('\n:confetti_ball: ')
                    thumb = 'https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/item/article/m/30041.jpg'
                elif prize[1] > 0:
                    desc.append('\n:clap: ')
                    thumb = 'https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/item/normal/m/gem.jpg'
                elif prize[2] > 0:
                    desc.append('\n:hushed: ')
                    thumb = 'https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/weapon/m/1040004600.jpg'
                elif prize[3] > 0:
                    desc.append('\n:pensive: ')
                    thumb = 'https://prd-game-a1-granbluefantasy.akamaized.net/assets_en/img/sp/assets/item/article/m/30033.jpg'
                add_comma : bool = False
                for i in range(0, 4):
                    if prize[3-i] > 0:
                        if add_comma: desc.append(", ")
                        desc.append("**{}** Tier {}".format(prize[3-i], 4-i))
                        add_comma : bool = True
                desc.append(" prizes")
        return ''.join(desc), thumb

    """checkLotoWin()
    Check which tier the card is elligible for
    (summer fortune minigame)
    
    Parameters
    ----------
    card: Card to compare
    winning: Tuple of list of winning digits per tier
    
    Returns
    --------
    int: Prize tier (0 = lost)
    """
    def checkLotoWin(self : Games, card : str, winning : FortuneWinningNumberPerTier) -> int:
        tier : int
        for tier in range(0, 4): # tier (0=t1, 1=t2, etc...)
            match tier:
                case 0: x = card
                case 1: x = card[1:]
                case 2: x = card[:2]
                case 3: x = card[2]
            if x in winning[tier]:
                return tier + 1
        return 0

    @game.sub_command()
    async def fortune(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, usercards : str = commands.Param(description='List your cards here', default="")) -> None:
        """Imitate the GBF summer fortune game from Summer 2021"""
        await inter.response.defer()
        # Starting message
        title = '{} is tempting fate...'.format(inter.author.display_name)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description="The winning numbers are...", color=self.COLOR))
        # generate loto
        cards, winning = await self.genLoto()
        # read and parse user cards
        cvt : list[str] = []
        usercards : list[str] = usercards.split(" ")
        card : str
        for card in usercards:
            try:
                if card == "":
                    continue
                if len(card) > 3 or int(card) < 0:
                    raise Exception()
            except:
                cvt = []
                break
            cvt.append(card.zfill(3))
            if len(cvt) >= 20:
                break # limited to 20 cards
        # if 1 or more usercards, we use these cards instead of loto ones
        if len(cvt) > 0:
            cards = cvt
        await asyncio.sleep(2)
        # show default numbers
        prize : list[int] = [0, 0, 0, 0]
        desc : str
        thumb : str|None
        desc, thumb = await self.printLoto([], winning, prize)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description=desc, thumbnail=thumb, color=self.COLOR))
        # reveal result, one by one
        title = "{}'s fortune is".format(inter.author.display_name)
        i : int
        for i in range(0, len(cards)):
            tier : int = self.checkLotoWin(cards[:i+1][-1], winning)
            if tier != 0:
                prize[tier-1] += 1
                cards[i] = '**'+cards[i]+'**'
            desc, thumb = await self.printLoto(cards[:i+1], winning, prize, (i == len(cards)-1))
            await asyncio.sleep(0.5)
            await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description=desc, thumbnail=thumb, color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @game.sub_command()
    async def deal(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Deal a random poker hand"""
        await inter.response.defer()
        # generate cards
        hand_table : dict[str, GameCard] = {}
        while len(hand_table) < 5:
            card : GameCard = self.bot.singleton.get_GameCard(random.randint(2, 14), random.randint(0, 3))
            if str(card) not in hand_table:
                hand_table[str(card)] = card
        hand : list[GameCard] = list(hand_table.values())
        # default message
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s hand".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="🎴, 🎴, 🎴, 🎴, 🎴", color=self.COLOR))
        # reveal cards one by one (Use Poker view for parsing)
        x : int
        for x in range(0, 5):
            await asyncio.sleep(1)
            # check result
            msgs : list[str] = []
            i : int
            for i in range(len(hand)):
                if i > x:
                    msgs.append("🎴")
                else:
                    msgs.append(str(hand[i]))
                if i < 4:
                    msgs.append(", ")
                else:
                    msgs.append("\n")
            if x == 4:
                await asyncio.sleep(2)
                msgs.append(Poker.checkPokerHand(hand)[1])
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s hand".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="".join(msgs), color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @game.sub_command()
    async def poker(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, max_round : int = commands.Param(description="Number of rounds to play", ge=1, le=5, default=1)) -> None:
        """Play a poker mini-game with other people (2 to 8 players)"""
        await inter.response.defer()
        if inter.context.bot_dm:
            await inter.edit_original_message(embed=self.bot.embed(title="♠️ Multiplayer Poker ♥️", description="Unavailable in Direct Messages.", color=self.COLOR))
            return
        # creating game
        players : list[disnake.Member] = [inter.author]
        view : JoinGame = JoinGame(self.bot, players, 8, 2)
        desc : str = "**" + str(max_round) + "** Round(s)\nStarting in {}s\n{}/8 players"
        embed : disnake.Embed = self.bot.embed(title="♠️ Multiplayer Poker ♥️", description=desc.format(60, 1), color=self.COLOR)
        await inter.edit_original_message(embed=embed, view=view)
        msg : disnake.Message = await inter.original_message()
        await view.updateTimer(msg, embed, desc, 60)
        # wait players
        await view.wait()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title="♠️ Multiplayer Poker ♥️", description="Error, at least two Players are required", color=self.COLOR))
            await self.bot.channel.clean(inter, 60)
        else:
            await msg.delete()
            random.shuffle(players) # randomize the player order
            win_tracker : dict[int, int] = {} # track how many wins each player got
            p : disnake.Member
            for p in players: # initialize
                win_tracker[p.id] = [(p.display_name if len(p.display_name) <= 10 else p.display_name[:10] + "..."), 0]
            i : int
            for i in range(0, max_round): # for loop, the game is composed of 3 rounds
                embed = self.bot.embed(title="♠️ Multiplayer Poker ♥️ ▫️ Round {}/{}".format(i+1, max_round), description="Initialization", footer="Round limited to 2 minutes", color=self.COLOR)
                gview = Poker(self.bot, players, embed, (0 if max_round == 1 else (max_round - i)))
                await gview.update(inter, init=True)
                await gview.wait()
                await gview.playRound()
                for p in gview.winners: # get the winner and increase their counts
                    win_tracker[p.id][1] += 1
                await asyncio.sleep(10)
                if i < max_round - 1: await gview.message.delete()
            if max_round > 1:
                win_tracker = dict(sorted(win_tracker.items(), key=lambda item: item[1], reverse=True)) # sort in reverse order
                msgs : list[str] = []
                for id, s in win_tracker.items(): # make a string
                    msgs.append("**{}** ▫️ **{}** win(s)\n".format(s[0], s[1]))
                await gview.message.edit(embed=self.bot.embed(title="♠️ Multiplayer Poker ♥️ ▫️ Results", description="".join(msgs), color=self.COLOR)) # post it
            await self.bot.channel.clean((inter, gview.message), 60)

    @game.sub_command()
    async def blackjack(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Play a blackjack mini-game with other people (1 to 8 players)"""
        await inter.response.defer()
        # creating game
        players : list[disnake.Member] = [inter.author]
        if inter.guild is not None:
            view : JoinGame = JoinGame(self.bot, players, 8, 1)
            desc : str = "Starting in {}s\n{}/8 players"
            embed : disnake.Embed = self.bot.embed(title="♠️ Multiplayer Blackjack ♥️", description=desc.format(60, 1), color=self.COLOR)
            msg : disnake.Message = await inter.channel.send(embed=embed, view=view)
            await view.updateTimer(msg, embed, desc, 60)
            # wait players
            await view.wait()
            await msg.delete()
        embed = self.bot.embed(title="♠️ Multiplayer Blackjack ♥️", description="Initialization", footer="Game limited to 4 minutes", color=self.COLOR)
        gview : Blackjack = Blackjack(self.bot, players, embed)
        await gview.update(inter, init=True)
        await gview.wait()
        await self.bot.channel.clean(inter, 60)

    @game.sub_command()
    async def tictactoe(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Play a game of Tic Tac Toe (2 players Only)"""
        await inter.response.defer()
        if inter.context.bot_dm:
            await inter.edit_original_message(embed=self.bot.embed(title=":x: Multiplayer Tic Tac Toe :o:", description="Unavailable in Direct Messages.", color=self.COLOR))
            return
        # creating game
        players : list[disnake.Member] = [inter.author]
        view : JoinGame = JoinGame(self.bot, players, 2, 2)
        desc : str = "Starting in {}s\n{}/2 players"
        embed : disnake.Embed = self.bot.embed(title=":x: Multiplayer Tic Tac Toe :o:", description=desc.format(45, 1), color=self.COLOR)
        msg : disnake.Message = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        # wait players
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title=":x: Multiplayer Tic Tac Toe :o:", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            random.shuffle(players)
            embed = self.bot.embed(title=":x: Multiplayer Tic Tac Toe :o:", description=":x: {} :o: {}\nTurn of **{}**".format(view.players[0].display_name, view.players[1].display_name, view.players[0].display_name), footer="Game limited at 3 minutes", color=self.COLOR)
            gview : TicTacToe = TicTacToe(self.bot, players, embed)
            await inter.edit_original_message(embed=embed, view=gview)
            await gview.wait()
        await self.bot.channel.clean(inter, 60)

    @game.sub_command()
    async def connectfour(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Play a game of Connect Four (2 players Only)"""
        await inter.response.defer()
        if inter.context.bot_dm:
            await inter.edit_original_message(embed=self.bot.embed(title=":red_circle: Multiplayer Connect Four :yellow_circle:", description="Unavailable in Direct Messages.", color=self.COLOR))
            return
        # creating game
        players : list[disnake.Member] = [inter.author]
        view : JoinGame = JoinGame(self.bot, players, 2, 2)
        desc : str = "Starting in {}s\n{}/2 players"
        embed : disnake.Embed = self.bot.embed(title=":red_circle: Multiplayer Connect Four :yellow_circle:", description=desc.format(45, 1), color=self.COLOR)
        msg : disnake.Message = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        # wait players
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title=":red_circle: Multiplayer Connect Four :yellow_circle:", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            random.shuffle(players)
            embed = self.bot.embed(title=":red_circle: Multiplayer Connect Four :yellow_circle:", description=":red_circle: {} :yellow_circle: {}".format(players[0].display_name, players[1].display_name), footer="Game limited to 8 minutes", color=self.COLOR)
            gview : ConnectFour = ConnectFour(self.bot, players, embed)
            await gview.update(inter, init=True)
            await gview.wait()
        await self.bot.channel.clean(inter, 60)

    @game.sub_command()
    async def battleship(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Play a game of Battle Ship (2 players Only)"""
        await inter.response.defer()
        if inter.context.bot_dm:
            await inter.edit_original_message(embed=self.bot.embed(title=":ship: Multiplayer Battle Ship :cruise_ship:", description="Unavailable in Direct Messages.", color=self.COLOR))
            return
        # creating game
        players : list[disnake.Member] = [inter.author]
        view : JoinGame = JoinGame(self.bot, players, 2, 2)
        desc : str = "Starting in {}s\n{}/2 players"
        embed : disnake.Embed = self.bot.embed(title=":ship: Multiplayer Battle Ship :cruise_ship:", description=desc.format(45, 1), color=self.COLOR)
        msg : disnake.Message = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        # wait players
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title=":ship: Multiplayer Battle Ship :cruise_ship:", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            random.shuffle(players)
            embed = self.bot.embed(title=":ship: Multiplayer Battle Ship :cruise_ship:", description=":ship: {} :cruise_ship: {}".format(players[0].display_name, players[1].display_name), fields=[{'name':players[0].display_name, 'value':'dummy'}, {'name':players[1].display_name, 'value':'dummy'}], footer="Game limited to 8 minutes", color=self.COLOR, inline=False)
            gview : BattleShip = BattleShip(self.bot, players, embed)
            await gview.update(inter, init=True)
            await gview.wait()
        await self.bot.channel.clean(inter, 60)

    @game.sub_command()
    async def rockpaperscissor(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, bestof : int = commands.Param(description="How many rounds to win", ge=1, le=10, default=1)) -> None:
        """Play a Rock Paper Scissor mini-game with other people (2 players Only)"""
        await inter.response.defer()
        if inter.context.bot_dm:
            await inter.edit_original_message(embed=self.bot.embed(title="🪨 Multiplayer Rock Paper Scissor ✂️", description="Unavailable in Direct Messages.", color=self.COLOR))
            return
        # creating game
        players : list[disnake.Member] = [inter.author]
        view : JoinGame = JoinGame(self.bot, players, 2, 2)
        desc : str = "Best of **" + str(bestof) + "**\nStarting in {}s\n{}/2 players"
        embed : disnake.Embed = self.bot.embed(title="🪨 Multiplayer Rock Paper Scissor ✂️", description=desc.format(45, 1), color=self.COLOR)
        msg : disnake.Message = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        # wait players
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title="🪨 Multiplayer Rock Paper Scissor ✂️", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            scores : list[int] = [0, 0]
            embed = self.bot.embed(title="🪨 Multiplayer Rock Paper Scissor ✂️ ▫️ Best of {}".format(bestof), description="Initialization", footer="Round limited to 60 seconds", color=self.COLOR)
            while True:
                gview : RPS = RPS(self.bot, players, embed, scores, bestof)
                await gview.update(inter, init=True)
                await gview.wait()
                await gview.timeoutCheck(inter)
                if scores[0] >= bestof or scores[1] >= bestof:
                    break
                await asyncio.sleep(10)
        await self.bot.channel.clean(inter, 60)

    @commands.slash_command(name="random")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 50, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def _random(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @_random.sub_command()
    async def dice(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, dice_string : str = commands.Param(description="Format is NdN. Minimum is 1d4, Maximum is 10d100")) -> None:
        """Roll some dies"""
        try:
            await inter.response.defer()
            # parse dice
            tmp : list[str] = dice_string.lower().split('d')
            n : int = int(tmp[0]) # number of dice
            d : int = int(tmp[1]) # dice strength
            # check limits
            if n <= 0 or n> 10 or d < 4 or d > 100:
                raise Exception()
            # roll and reveal, one by one
            rolls : list = []
            i : int
            for i in range(n):
                # add roll
                rolls.append(random.randint(1, d))
                msgs : list[str] = []
                j : int
                for j in range(len(rolls)):
                    msgs.append("{}".format(rolls[j]))
                msgs = ["### ", ", ".join(msgs)]
                # print message
                if len(rolls) == n:
                    msgs.append("\n**Total**: {:}, **Average**: {:}, **Percentile**: {:.1f}%".format(sum(rolls), round(sum(rolls)/len(rolls)), sum(rolls) * 100 / (n * d)).replace('.0%', '%'))
                await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} rolled {}...".format(inter.author.display_name, dice_string), 'icon_url':inter.author.display_avatar}, description="".join(msgs), color=self.COLOR))
                await asyncio.sleep(1)
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid string `{}`\nFormat must be `NdN` (minimum is `1d6`, maximum is `10d100`)".format(dice_string), color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @_random.sub_command()
    async def coin(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Flip a coin"""
        await inter.response.defer()
        coin : int = random.randint(0, 1) # roll 0 or 1
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} flipped a coin...".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=(":coin: It landed on **Head**" if (coin == 0) else ":coin: It landed on **Tail**"), color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @_random.sub_command()
    async def quota(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Give you your GW quota for the day"""
        await inter.response.defer()
        h : int = random.randint(2000, 20000) # honor roll
        m : int = random.randint(400, 1200) # meat roll
        c : int = random.randint(1, 100) # rng roll

        # process rng roll
        if c < 4:
            c = random.randint(1, 110)
            if c <= 3:
                await inter.edit_original_message(embed=self.bot.embed(title="{} {}'s daily quota".format(self.bot.emote.get('gw'), inter.author.display_name), description="You got the **Eternal Battlefield Pass** 🤖\nCongratulations!!!\nYou will now relive GW over and ovḛ̸̛̠͕̑̋͌̄̎̍͆̆͑̿͌̇̇̕r̸̛̗̥͆͂̒̀̈́͑̑̊͐̉̎̚̚͝ ̵̨̛͔͎͍̞̰̠́͛̒̊̊̀̃͘ư̷͎̤̥̜̘͈̪̬̅̑͂̂̀̃̀̃̅̊̏̎̚͜͝ͅņ̴̢̛̛̥̮͖͉̻̩͍̱̓̽̂̂͌́̃t̵̞̦̿͐̌͗͑̀͛̇̚͝͝ỉ̵͉͕̙͔̯̯͓̘̬̫͚̬̮̪͋̉͆̎̈́́͛̕͘̚͠ͅļ̸̧̨̛͖̹͕̭̝͉̣̜͉̘͙̪͙͔͔̫̟̹̞̪̦̼̻̘͙̮͕̜̼͉̦̜̰̙̬͎͚̝̩̥̪̖͇̖̲̣͎̖̤̥͖͇̟͎̿̊͗̿̈̊͗̆̈́͋͊̔͂̏̍̔̒̐͋̄̐̄̅̇͐̊̈́̐͛͑̌͛̔͗̈́͌̀͑̌̅̉́̔̇́̆̉͆̄̂͂̃̿̏̈͛̇̒͆͗̈́̀̃̕̕͘̚̚͘͘͠͠͠͝͝͠͝͝ͅͅ ̴̢̛̛̛̯̫̯͕̙͙͇͕͕̪̩̗̤̗̺̩̬̞̞͉̱̊̽̇̉̏̃̑̋̋̌̎̾́̉́͌̿̐̆̒̾̆͒͛͌́͒̄͗͊͑̈́̑̐̂̿̋̊͊̈́̃̋̀̀̈̏̅̍̈͆̊̋͋̀̽͑̉̈́͘͘̕̕͝y̷̧̧̨̢̧̮̭̝̦͙͈͉̜͈̳̰̯͔͓̘͚̳̭͎̳̯͈͓̣͕͙̳̭̱͍͎͖̋͊̀͋͘͘ơ̸̢̗̖̹̹͖̣̫̝̞̦̘̙̭̮͕̘̱̆͋̓͗̾͐̉̏̀͂̄̎̂̈́͌͑̅̆̉̈̒͆̈̈̊͐̔̓̀̿̓̈́͝͝͝͠͝u̶̡̧̡̧̨̧̡̡̢̢̢̪̯͙͍̱̦̠̗̹̼̠̳̣͉̞̩̹͕̫͔͚̬̭̗̳̗̫̥̞̰̘̖̞̤͖̳̮̙͎͎̗̙̳͙͖͓̪̱̞͖̠̣̮̘͍̱̥̹͎͎̦̬̹̼̜͕͙͖̫̝̰̯̜̹̬̯͚͕̰̪̼͓̞̫̖̘͙̞͖̺̩͓̹̘̙̫̩̲̻̪̠̞̺͚̫̰̠̼̖̬͔̗̮͙̱̬̩̮̟͓̫̭̲̘̤͎̱̓̊̇́̀̏̏̾̀̄̆̒̂͐̌͂̈̂̓͋̌̓͘̕̕̚͜͜͜͝ͅͅͅͅŗ̷̡̧̨̢̢̢̧̡̡̧̡̢̧̨̨̡̧̛̛̛̬͚̮̜̟̣̤͕̼̫̪̗̙͚͉̦̭̣͓̩̫̞͚̤͇̗̲̪͕̝͍͍̫̞̬̣̯̤̮͉̹̫̬͕̫̥̱̹̲͔͔̪̖̱͔̹͈͔̳͖̩͕͚͓̤̤̪̤̩̰̬͙̞͙̘̯̮̫͕͚̙̜̼̩̰̻̞̺͈̝̝̖͎̻̹̞̥̰̮̥̙̠͔͎̤̲͎͍̟̥̞̗̰͓͍̞̹͍̬͎̲̬̞͈͉̼̥̝͈̼̠̫̙͖̪̼̲̯̲̫̼̺̘̗̘͚̤͓̯̦̣̬͒̑̒́͑͊̍̿̉̇̓̒̅̎͌̈́̐̽͋̏̒͂̈̒̃̿̓̇̈̿̊̎̈́͐̒͂͊̿̈́̿̅̏̀͐͛̎̍͑͂̈́̃̇̀̈͋̾̔̈́̽͌̿̍̇̅̏̋̑̈́̾̊͐̉̊̅͑̀͊̽̂̈́̽̓͗́̄͆̄͑͒̈́́͋̏͊͋̒͗̆̋̌̈̀͑͗̽͂̄̌̕͘͘̚͘̕̕͜͜͜͜͜͜͜͠͝͝͝͝͝͝ͅͅͅ ̷̧̡̧̨̢̧̨̡̨̧̛̛̛̛̮̭͇̣͓̙̺͍̟̜̞̫̪̘̼̞̜̠͇̗̮͕̬̥͓͔͈̟̦͇̥̖̭̝̱̗̠̘̝̹̖͓̝͇̖̫̯̩̞̞̯̲̤̱̻̤͇̲͍͈͓͖̹̗̟̲̪̪̟̩͙̪̝̮̘̽̋̍́̔̊̍̈́͂̌̽͒̆͐͊̏̐͑͛̓̆̈́͌̂͒͆̔̅̓̽͊̅́̾̽̓̏̆̀̀͌̾̀͒̓̇̊̀̐͛̌̋̈͑̇́̂̆̽̈̕̕̚̚͜͠ͅͅͅͅḑ̶̛̛̯͓̠̖͎̭̞̫͑̋̄̄̈̽̎̊͛̽͌̾̋̔̽̔̀̀͐̿̈́̀̃͐͂͆̈̃͑̀̋̑͊̃̆̓̾̎̅̀̆̓̏͊̆̔̈̅͛̍̎̓̀͛͒́̐͆̂̋̋͛̆̈͐͂̏̊̏̏̓̿̔͆̓̽̂̅͆̔͑̔̈̾̈̽̂̃̋̈́̾̎̈́̂̓̃̒͐͆̌̍̀͗̈́̑̌̚̕̕̚͠͠͝ę̴̧̨̨̨̢̨̢̧̧̧̨̧̛̛̛̛̛̛̛̺̪̹̘͈̣͔̜͓̥̥̟͇̱͚͖̠͙͙̱̞̣̤͚̣̟̫̬̟͓̺͙̬͚̹͓̗̬̼͇͙̻͍̖̙̥̩͔̜͕̖͕͔͚̳͙̩͇͙̺͔̲̱̙͉̝̠̤̝̭̮̩̦͇̖̳̞̞̖͎̙͙̲̮̠̣͍̪͙̰̣͉̘͉̦̖̳̫͖͖̘̖̮̲̱̪͕̳̫̫̞̪̜̞̬͙͖͍͖̦͉̯̟̖͇̩͚͙͔̳̫͗̈́̒̎͂̇̀͒̈́̃͐̉͛̾̑̆̃͐̈́̉͒̇̓̏̀͌̐͌̅̓͐́̿͒̅͑̍̓̈́̉̊́̉̀̔̊̍̽͛͛͆̓̈͋̉͋̿̉́̋̈̓̐̈́̔̃͆͗͛̏́̀̑͋̀̽̔̓̎̒̆̌̐̈́̓͂̐̋͊̌͑̓̈́̊̿͋̈́́̃̏̓̉͛͆̂͐͗͗̾̅̌̾͌̈́͊͘̕̚̕̚̚̕͘̕͜͜͜͜͜͜͜͠͝͝͠͝͝͠ͅͅa̸̡͔̯͎̟͙̖̗͔̺̰͇͚̭̲̭͕̫̜͉̯͕̅̈͋̒͋͂̐̕ͅţ̶̡̨̢̢̡̡̡̨̢̡̧̨̢̛̥̭̞͈̼̖͙͇̝̳͇̞̬͎̲̙̰̙̱̳̟̣̗̫̣͉͖̪̩͙̲͇͙̫̘͖̖̜̝̦̥̟̜̠͔̠͎̭͔̘͓͚̩͇͙͎͎̰̘̟̳̪͖̠̪̦̦̫̞̟̗̹̹̤͓͍̜̯͔̼̱̮̹͎͖͍̲͎̠͉̟͈̠̦̯̲̼̥̱̬̜͙̘͕̣̳͇̞͓̝͈̼̞̻͚̘̩̟̩̖̼͍̯̘͉͔̤̘̥̦͑̒͗̅̉̾͗̾̓̈́̍̉̈́͛̀͊̋̀͐̏̈́̀̀̍̇̀̀̈́̃̀̅͛̅̈́̇̽̆̌̈̄͆̄̂͂̔͗͌͊̽̿́͑̒̾̑̊̿͗́̇̋̊̄̀̍̓̆͂̆̔̏̍̑̔̊̾̎̆͛͑̓͒̈̎͌̓͗̀̿̓̃̔̈́͗̃̓̽̓̉̀͛͂̿́̀̌͊̆̋̀̓̇́̔̓͆̋̊̀̋͑́̔́̌̒̾̂̎̋̈́́̀͗̈́̈́́̾̈́͑͋̇͒̀͋͆͗̾͐̆̈́͂͐̈̐̓̍̈́̈̅̓͐̚̚̚̚̕͘̕͘̚̚̚͘͜͜͜͜͜͜͝͠͠͠͝͠ͅͅḥ̴̨̧̧̢̧̢̢̛̛̙̱͚̺̬̖̮̪͈̟͉̦̪̘̰̺̳̱̲͔̲̮̦̦̪̪̲̠͓͎͇͕̯̥͉͍̱̥͓̲̤̫̳̠̝͖̺̙͖͎͙̠͓̺̗̝̩͍͕͎̞͕̤̻̰̘͇͕̟̹̳͇͈͇̳̳̞̗̣͖̙͓̼̬̯͚͎̮͚̳̰͙̙̟̊͆͒͆͌̂̈́̀́̽̿͌̓́̐̑͌͋͆͊͑͛͑̀̋͐̏͌̑̀͛͗̀́̈̀̓̽̇̐̋͊̅͑̊͒̈́̀̀̔̀̇͗̆͑̅̌̑̈́͌̒̅̌̓͋͂̀̍̈́͐̈́̆̐̈́̍͛͂̔̐̎͂̎̇͑̈́̈́̎̉̈́́̒̒̆̌̃̓̈́͂̽̓̆̋̈̂̽̆̓̔͗̓̀̄̈́̂̏͗̐̔͘̕͘͘͜͜͜͜͠͠͝͠͠͝͝͝͠͠͝ͅͅ", thumbnail=inter.author.display_avatar, color=self.COLOR))
            elif c <= 10:
                await inter.edit_original_message(embed=self.bot.embed(title="{} {}'s daily quota".format(self.bot.emote.get('gw'), inter.author.display_name), description="You got a **Slave Pass** 🤖\nCongratulations!!!\nCall your boss and take a day off now!", footer="Full Auto and Botting are forbidden", thumbnail=inter.author.display_avatar, color=self.COLOR))
            elif c <= 15:
                await inter.edit_original_message(embed=self.bot.embed(title="{} {}'s daily quota".format(self.bot.emote.get('gw'), inter.author.display_name), description="You got a **Carry Pass** 😈\nDon't stop grinding, continue until your Crew gets the max rewards!", thumbnail=inter.author.display_avatar, color=self.COLOR))
            elif c <= 24:
                await inter.edit_original_message(embed=self.bot.embed(title="{} {}'s daily quota".format(self.bot.emote.get('gw'), inter.author.display_name), description="You got a **Relief Ace Pass** 😈\nPrepare to relieve carries of their 'stress' after the day!!!", footer="wuv wuv", thumbnail=inter.author.display_avatar, color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="{} {}'s daily quota".format(self.bot.emote.get('gw'), inter.author.display_name), description="You got a **Free Leech Pass** 👍\nCongratulations!!!", thumbnail=inter.author.display_avatar, color=self.COLOR))
            await self.bot.channel.clean(inter, 40)
            return
        elif c == 4: # below are extra random multipliers
            h = h * random.randint(50, 80)
            m = m * random.randint(50, 80)
        elif c <= 7:
            h = h * random.randint(20, 30)
            m = m * random.randint(20, 30)
        elif c <= 9:
            h = h * random.randint(8, 15)
            m = m * random.randint(8, 15)
        elif c == 10:
            h = h // random.randint(30, 50)
            m = m // random.randint(30, 50)
        elif c <= 12:
            h = h // random.randint(10, 20)
            m = m // random.randint(10, 20)
        elif c <= 14:
            h = h // random.randint(3, 6)
            m = m // random.randint(3, 6)
        h = h * 100000 # x100k
        m = m * 10 # x10

        await inter.edit_original_message(embed=self.bot.embed(title="{} {}'s daily quota".format(self.bot.emote.get('gw'), inter.author.display_name), description="**Honor:** {:,}\n**Meat:** {:,}".format(h, m), thumbnail=inter.author.display_avatar, color=self.COLOR))
        await self.bot.channel.clean(inter, 40)

    """randint()
    Generate a simple pseudo random number based on a seed value.
    Used by character().
    
    Parameters
    ----------
    seed: Integer used as the seed
    
    Returns
    ----------
    int: Pseudo random value which you can use as the next seed
    """
    def randint(self : Games, seed : int) -> int:
        return ((seed * 1103515245) % 4294967296) + 12345

    @_random.sub_command()
    async def character(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Generate a random GBF character"""
        await inter.response.defer()
        seed : int = (inter.author.id + int(self.bot.util.UTC().timestamp()) // 86400) # create seed based on user id + day
        values : RandomCharacterContainer = {
            'Rarity' : (('SSR', 'SR', 'R'), 3, True, None), # random strings, modulo to use, bool to use emote.get, seed needed to enable
            'Race' : (('Human', 'Erune', 'Draph', 'Harvin', 'Primal', 'Other'), 6, False, None),
            'Element' : (('fire', 'water', 'earth', 'wind', 'light', 'dark'), 6, True, None),
            'Gender' : (('Unknown', '\♂️', '\♀️'), 3, False, None),
            'Series' : (('Summer', 'Yukata', 'Grand', 'Holiday', 'Halloween', 'Valentine'), 30, True, 6)
        }
        msgs : list[str] = []
        rarity_mod : int = 0
        # roll for each values
        k : str
        for k in values:
            v : int = seed % values[k][1]
            if k == "Rarity":
                rarity_mod = 7 - 2 * v
            if values[k][3] is not None and v >= values[k][3]:
                continue
            if values[k][2]:
                msgs.append("**{}** ▫️ {}\n".format(k, self.bot.emote.get(values[k][0][v])))
            else:
                msgs.append("**{}** ▫️ {}\n".format(k, values[k][0][v]))
            seed = self.randint(seed)
        msgs.append("**Rating** ▫️ {:.1f}".format(rarity_mod + (seed % 31) / 10))

        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s daily character".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="".join(msgs), color=self.COLOR))
        await self.bot.channel.clean(inter, 30)

    @_random.sub_command()
    async def xil(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction) -> None:
        """Generate a random element for Xil (Private Joke)"""
        await inter.response.defer()
        g : random.Random = random.Random()
        elems : list[str] = ['fire', 'water', 'earth', 'wind', 'light', 'dark']
        g.seed(int((int(self.bot.util.UTC().timestamp()) // 86400) * (1.0 + 1.0/4.2)))
        e : str = g.choice(elems)

        await inter.edit_original_message(embed=self.bot.embed(title="Today, Xil's main element is", description="### {} **{}**".format(self.bot.emote.get(e), e.capitalize()), color=self.COLOR))
        await self.bot.channel.clean(inter, 30)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.max_concurrency(8, commands.BucketType.default)
    async def ask(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """Command Group"""
        pass

    @ask.sub_command()
    async def choice(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, choices : str = commands.Param(description="Format is Choice 1;Choice 2;...;Choice N")) -> None:
        """Ask me to pick a choice"""
        try:
            await inter.response.defer()
            # parse choices
            possible : list[str] = choices.split(";")
            while '' in possible:
                possible.remove('')
            # 2 are required at the minimum
            if len(possible) < 2: raise Exception()
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s choice".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="Possible choices: `{}`\n### I pick: `{}`".format('` `'.join(possible), random.choice(possible)), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Give me a list of something to choose from, separated by `;`", color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @ask.sub_command()
    async def question(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, question : str = commands.Param()) -> None:
        """Ask me a question"""
        await inter.response.defer()
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} asked".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="`{}`\n### {}".format(question, random.choice(["It is Certain.","It is decidedly so.","Without a doubt.","Yes definitely.","You may rely on it.","As I see it, yes.","Most likely.","Outlook good.","Yes.","Signs point to yes.","Reply hazy, try again.","Ask again later.","Better not tell you now.","Cannot predict now.","Concentrate and ask again.","Don't count on it.","My reply is no.","My sources say no.","Outlook not so good.","Very doubtful."])), color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @ask.sub_command()
    async def when(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, question : str = commands.Param()) -> None:
        """Ask me when will something happen"""
        await inter.response.defer()
        if question.lower().startswith("when ") and len(question) > 5: question = question[5:]
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} asked".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="`When {}`\n### {}".format(question, random.choice(["Never", "Soon:tm:", "Ask again tomorrow", "Can't compute", "42", "One day, my friend", "Next year", "It's a secret to everybody", "Soon enough", "When it's ready", "Five minutes", "This week, surely", "My sources say next month", "NOW!", "I'm not so sure", "In three days"])), color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @ask.sub_command()
    async def element(self : commands.SubCommand, inter : disnake.ApplicationCommandInteraction, question : str = commands.Param()) -> None:
        """Ask for a random gbf element"""
        await inter.response.defer()
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} asked".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="`{}`\n# {}".format(question, self.bot.emote.get(random.choice(["fire", "water", "earth", "wind", "light", "dark"]))), color=self.COLOR))
        await self.bot.channel.clean(inter, 45)

    @commands.message_command(name="UwU")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(5, 90, commands.BucketType.guild)
    async def uwu(self : commands.message_command, inter : disnake.MessageCommandInteraction, message: disnake.Message) -> None:
        """UwU-tize a message"""
        await inter.response.defer()
        msg : str = message.clean_content.replace("r","w").replace("R","W").replace("than","dan").replace("Than","Dan").replace("THan","Dan").replace("THAn","Dan").replace("THAN","DAN").replace("thaN","daN").replace("thAn","dAn").replace("thAN","dAN").replace("tHAN","DAN").replace("l","w").replace("L","W").replace("oy","oi").replace("oY","oI").replace("Oy","Oi").replace("OY","OI").replace("the","de").replace("The","De").replace("THe","De").replace("THE","DE").replace("thE","dE").replace("tHe","De").replace("you","u").replace("You","U").replace("YOu","U").replace("YOU","U").replace("yoU","u").replace("yOu","u").replace("yOU","U")
        if len(msg) == 0 or len(msg) >= 3800:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="This message can't be converted", color=self.COLOR))
        else:
            if inter.context.bot_dm:
                await inter.edit_original_message(embed=self.bot.embed(title="UwU", description="[Original Message](https://discord.com/channels/@me/{}/{})\n```\n{}\n```".format(inter.channel.id, message.id, msg), color=self.COLOR))
            else:
                await inter.edit_original_message(embed=self.bot.embed(title="UwU", description="[Original Message](https://discord.com/channels/{}/{}/{})\n```\n{}\n```".format(inter.guild.id, inter.channel.id, message.id, msg), color=self.COLOR))