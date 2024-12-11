import disnake
from disnake.ext import commands
import asyncio
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
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
    COLOR = 0xeb6b34
    SCRATCHER_LOOT = {
        100 : ['Siero Ticket'],
        300 : ['Sunlight Stone', 'Gold Brick'],
        450 : ['Damascus Ingot'],
        600 : ['Agni', 'Varuna', 'Titan', 'Zephyrus', 'Zeus', 'Hades', 'Shiva', 'Europa', 'Godsworn Alexiel', 'Grimnir', 'Lucifer', 'Bahamut', 'Michael', 'Gabriel', 'Uriel', 'Raphael', 'Metatron', 'Sariel', 'Belial'],
        400 : ['Murgleis', 'Benedia', 'Gambanteinn', 'Love Eternal', 'AK-4A', 'Reunion', 'Ichigo-Hitofuri', 'Taisai Spirit Bow', 'Unheil', 'Sky Ace', 'Ivory Ark', 'Blutgang', 'Eden', 'Parazonium', 'Ixaba', 'Blue Sphere', 'Certificus', 'Fallen Sword', 'Mirror-Blade Shard', 'Galilei\'s Insight', 'Purifying Thunderbolt', 'Vortex of the Void', 'Sacred Standard', 'Bab-el-Mandeb', 'Cute Ribbon', 'Kerak', 'Sunya', 'Fist of Destruction', 'Yahata\'s Naginata', 'Cerastes', 'World Ender', 'Ouroboros Prime'],
        8000 : ['Crystals x3000', 'Damascus Crystal', 'Intricacy Ring', 'Gold Moon x2', 'Brimston Earrings', 'Permafrost Earrings', 'Brickearth Earrings', 'Jetstream Earrings', 'Sunbeam Earrings', 'Nightshade Earrings'],
        11250 : ['Gold Spellbook', 'Moonlight Stone', 'Ultima Unit x3', 'Silver Centrum x5', 'Primeval Horn x3', 'Horn of Bahamut x4', 'Legendary Merit x5', 'Steel Brick'],
        22000: ['Lineage Ring x2', 'Coronation Ring x3', 'Silver Moon x5', 'Bronze Moon x10'],
        33000: ['Elixir x100', 'Soul Berry x300']
    }
    SCRATCHER_THUMBNAIL = {
        'Siero Ticket':'item/article/s/30041.jpg', 'Sunlight Stone':'item/evolution/s/20014.jpg', 'Gold Brick':'item/evolution/s/20004.jpg', 'Damascus Ingot':'item/evolution/s/20005.jpg','Agni':'summon/s/2040094000.jpg', 'Varuna':'summon/s/2040100000.jpg', 'Titan':'summon/s/2040084000.jpg', 'Zephyrus':'summon/s/2040098000.jpg', 'Zeus':'summon/s/2040080000.jpg', 'Hades':'summon/s/2040090000.jpg', 'Shiva':'summon/s/2040185000.jpg', 'Europa':'summon/s/2040225000.jpg', 'Godsworn Alexiel':'summon/s/2040205000.jpg', 'Grimnir':'summon/s/2040261000.jpg', 'Lucifer':'summon/s/2040056000.jpg', 'Bahamut':'summon/s/2040030000.jpg', 'Michael':'summon/s/2040306000.jpg', 'Gabriel':'summon/s/2040311000.jpg', 'Uriel':'summon/s/2040203000.jpg', 'Raphael':'summon/s/2040202000.jpg', 'Metatron':'summon/s/2040330000.jpg', 'Sariel':'summon/s/2040327000.jpg', 'Belial':'summon/s/2040347000.jpg', 'Murgleis':'weapon/s/1040004600.jpg', 'Benedia':'weapon/s/1040502500.jpg',  'Gambanteinn':'weapon/s/1040404300.jpg',  'Love Eternal':'weapon/s/1040105400.jpg',  'AK-4A':'weapon/s/1040004600.jpg',  'Reunion':'weapon/s/1040108200.jpg',  'Ichigo-Hitofuri':'weapon/s/1040910000.jpg',  'Taisai Spirit Bow':'weapon/s/1040708700.jpg',  'Unheil':'weapon/s/1040809100.jpg',  'Sky Ace':'weapon/s/1040911500.jpg',  'Ivory Ark':'weapon/s/1040112500.jpg',  'Blutgang':'weapon/s/1040008700.jpg',  'Eden':'weapon/s/1040207000.jpg',  'Parazonium':'weapon/s/1040108700.jpg',  'Ixaba':'weapon/s/1040906400.jpg',  'Blue Sphere':'weapon/s/1040410000.jpg',  'Certificus':'weapon/s/1040309000.jpg',  'Fallen Sword':'weapon/s/1040014300.jpg',  'Mirror-Blade Shard':'weapon/s/1040110600.jpg',  'Galilei\'s Insight':'weapon/s/1040211600.jpg',  'Purifying Thunderbolt':'weapon/s/1040709000.jpg',  'Vortex of the Void':'weapon/s/1040212700.jpg',  'Sacred Standard':'weapon/s/1040213400.jpg',  'Bab-el-Mandeb':'weapon/s/1040004600.jpg',  'Cute Ribbon':'weapon/s/1040605900.jpg',  'Kerak':'weapon/s/1040812000.jpg',  'Sunya':'weapon/s/1040811800.jpg',  'Fist of Destruction':'weapon/s/1040612700.jpg',  'Yahata\'s Naginata':'weapon/s/1040312900.jpg',  'Cerastes':'weapon/s/1040215300.jpg',  'World Ender':'weapon/s/1040020900.jpg',  'Ouroboros Prime':'weapon/s/1040418600.jpg', 'Crystals x3000':'item/normal/s/gem.jpg', 'Damascus Crystal':'item/article/s/203.jpg', 'Intricacy Ring':'item/npcaugment/s/3.jpg', 'Gold Spellbook':'item/evolution/s/20403.jpg', 'Moonlight Stone':'item/evolution/s/20013.jpg', 'Gold Moon x2':'item/article/s/30033.jpg', 'Ultima Unit x3':'item/article/s/138.jpg', 'Silver Centrum x5':'item/article/s/107.jpg', 'Primeval Horn x3':'item/article/s/79.jpg', 'Horn of Bahamut x4':'item/article/s/59.jpg', 'Legendary Merit x5':'item/article/s/2003.jpg', 'Steel Brick':'item/evolution/s/20003.jpg', 'Brimston Earrings':'item/npcaugment/s/11.jpg', 'Permafrost Earrings':'item/npcaugment/s/12.jpg', 'Brickearth Earrings':'item/npcaugment/s/13.jpg', 'Jetstream Earrings':'item/npcaugment/s/14.jpg', 'Sunbeam Earrings':'item/npcaugment/s/15.jpg', 'Nightshade Earrings':'item/npcaugment/s/16.jpg', 'Lineage Ring x2':'item/npcaugment/s/2.jpg', 'Coronation Ring x3':'item/npcaugment/s/1.jpg', 'Silver Moon x5':'item/article/s/30032.jpg', 'Bronze Moon x10':'item/article/s/30031.jpg', 'Elixir x100':'item/normal/s/2.jpg', 'Soul Berry x300':'item/normal/s/5.jpg'
    }
    SCRATCHER_TOTAL = 0
    SCRATCHER_TOTAL_RARE1 = 0
    SCRATCHER_TOTAL_RARE2 = 0
    for r in SCRATCHER_LOOT:
        SCRATCHER_TOTAL += r * len(SCRATCHER_LOOT[r])
        if SCRATCHER_LOOT[r][0] == 'Murgleis': SCRATCHER_TOTAL_RARE1 = SCRATCHER_TOTAL
        if SCRATCHER_LOOT[r][0] == 'Crystals x3000': SCRATCHER_TOTAL_RARE2 = SCRATCHER_TOTAL
    
    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def roll(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @roll.sub_command()
    async def single(self, inter: disnake.GuildCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a single draw"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("single", banner, self.COLOR)
        await sim.generate(1, legfest)
        await sim.output(inter, 0, ("{} did a single roll...", "{} did a single roll"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def ten(self, inter: disnake.GuildCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate ten draws"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.generate(10, legfest)
        await sim.output(inter, 1, ("{} did ten rolls...", "{} did ten rolls"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command(name="scam")
    async def scam_(self, inter: disnake.GuildCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), scam_index : int = commands.Param(description='Which Scam gacha to use (Default: 1 for the first one)', default=1, ge=1)) -> None:
        """Simulate ten draws and the Scam Gacha"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("scam", "scam", self.COLOR, scamindex=scam_index)
        await sim.generate(10, legfest)
        await sim.output(inter, 1, ("{} is getting Scammed...", "{} got Scammed"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def spark(self, inter: disnake.GuildCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a spark"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.generate(300, legfest)
        await sim.output(inter, 3, ("{} is sparking...", "{} sparked"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def count(self, inter: disnake.GuildCommandInteraction, num : int = commands.Param(description='Number of rolls (2 ~ 600)', ge=2, le=600), legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a specific amount of draw"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.generate(num, legfest)
        await sim.output(inter, 3, ("{}" + " is rolling {} times...".format(num), "{} " + "rolled {} times".format(num)))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def gachapin(self, inter: disnake.GuildCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a Gachapin Frenzy"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("gachapin", banner, self.COLOR)
        await sim.generate(300, legfest)
        await sim.output(inter, 3, ("{} is rolling the Gachapin...", "{} rolled the Gachapin"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def mukku(self, inter: disnake.GuildCommandInteraction, banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a Mukku Frenzy"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("mukku", banner, self.COLOR)
        await sim.generate(300)
        await sim.output(inter, 3, ("{} is rolling the Mukku...", "{} rolled the Mukku"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def supermukku(self, inter: disnake.GuildCommandInteraction, banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate a Super Mukku Frenzy"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("supermukku", banner, self.COLOR)
        await sim.generate(300)
        await sim.output(inter, 3, ("{} is rolling the Supper Mukku...", "{} rolled the Super Mukku"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def memeroll(self, inter: disnake.GuildCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), rateup : str = commands.Param(description='Input anything to roll until a rate up SSR', default=""), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0)) -> None:
        """Simulate rolls until a SSR"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("memerollB" if rateup != "" else "memerollA", banner, self.COLOR)
        await sim.generate(300, legfest)
        await sim.output(inter, 2, ("{} is memerolling...", "{} memerolled {} times"))
        del sim
        await self.bot.util.clean(inter, 40)

    @roll.sub_command()
    async def roulette(self, inter: disnake.GuildCommandInteraction, legfest : int = commands.Param(description='0 to force 3%, 1 to force 6%, leave blank for default', default=-1, ge=-1, le=1), banner : int = commands.Param(description='1~2 for classics, 3  for collab', default=0, ge=0), realist : int = commands.Param(description='1 to set Realist Mode (if allowed by owner)', default=0, ge=0, le=1)) -> None:
        """Imitate the GBF roulette"""
        await inter.response.defer()
        sim = await self.bot.gacha.simulate("ten", banner, self.COLOR)
        await sim.roulette(inter, legfest, (realist==1))
        del sim
        await self.bot.util.clean(inter, 50)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 40, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def game(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @game.sub_command()
    async def scratch(self, inter: disnake.GuildCommandInteraction) -> None:
        """Imitate the GBF scratch game from Anniversary 2020"""
        await inter.response.defer()
        ct = self.bot.util.JST()
        # settings
        fixedS = ct.replace(year=2021, month=3, day=29, hour=19, minute=0, second=0, microsecond=0) # beginning of good scratcher
        fixedE = fixedS.replace(day=31, hour=19) # end of good scratcher
        enableBetterDuringPeriod = True
        betterScratcher = False # if true, only good results possible
        # settings end
        footer = ""
        if enableBetterDuringPeriod and ct >= fixedS and ct < fixedE:
            betterScratcher = True

        # scratcher generation
        if random.randint(1, 100) <= 10:
            betterScratcher = True # to simulate the rare scratcher card thing, currently 10%
        if footer == "" and betterScratcher: footer = "Rare card"
        selected = {}
        nloot = random.randint(4, 5)
        while len(selected) < nloot:
            n = self.SCRATCHER_TOTAL
            if betterScratcher:
                while n > self.SCRATCHER_TOTAL_RARE2: # force a rare, according to settings
                    n = random.randint(1, self.SCRATCHER_TOTAL)
            elif len(selected) == 1:
                while n > self.SCRATCHER_TOTAL_RARE1: # force a rare, for the salt
                    n = random.randint(1, self.SCRATCHER_TOTAL)
            else:
                n = random.randint(1, self.SCRATCHER_TOTAL)
            c = 0
            found = False
            for r in self.SCRATCHER_LOOT:
                for item in self.SCRATCHER_LOOT[r]:
                    if n <= c:
                        if item in selected:
                            n += r
                        else:
                            selected[item] = 0
                            found = True
                        break
                    else:
                        c += r
                if found: break
        
        # build the scratch grid
        grid = []
        keys = list(selected.keys())
        for x in keys: # add all our loots once
            grid.append(x)
            selected[x] = 1
        # add the first one twice (it's the winning one)
        grid.append(keys[0])
        grid.append(keys[0])
        selected[keys[0]] = 3
        nofinal = False
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

        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} is scratching...".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="Click to play the game", footer=footer, color=self.COLOR), view=Scratcher(self.bot, inter.author.id, grid, self.SCRATCHER_THUMBNAIL, self.COLOR, footer))
        await self.bot.util.clean(inter, 45)

    @game.sub_command()
    async def chestrush(self, inter: disnake.GuildCommandInteraction) -> None:
        """Imitate the GBF treasure game from Summer 2020"""
        await inter.response.defer()
        loot = {
            'Murgleis':150, 'Benedia':150, 'Gambanteinn':150, 'Love Eternal':150, 'AK-4A':150, 'Reunion':150, 'Ichigo-Hitofuri':150, 'Taisai Spirit Bow':150, 'Unheil':150, 'Sky Ace':150, 'Ivory Ark':150, 'Blutgang':150, 'Eden':150, 'Parazonium':150, 'Ixaba':150, 'Blue Sphere':150, 'Certificus':150, 'Fallen Sword':150, 'Mirror-Blade Shard':150, 'Galilei\'s Insight':150, 'Purifying Thunderbolt':150, 'Vortex of the Void':150, 'Sacred Standard':150, 'Bab-el-Mandeb':150, 'Cute Ribbon':150, 'Kerak':150, 'Sunya':150, 'Fist of Destruction':150, 'Yahata\'s Naginata':150,
            'Ruler of Fate':150, 'Ancient Bandages':150, 'Gottfried':150, 'Acid Bolt Shooter':150, 'Mystic Spray Gun':150, 'Metal Destroyer':150, 'Gangsta Knife':150, 'Vagabond':150, 'Heavenly Fawn Bow':150, 'Another Sky':150,
            'Agni':150, 'Varuna':150, 'Titan':150, 'Zephyrus':150, 'Zeus':150, 'Hades':150, 'Shiva':150, 'Europa':150, 'Godsworn Alexiel':150, 'Grimnir':150, 'Lucifer':150, 'Bahamut':150, 'Michael':150, 'Gabriel':150, 'Uriel':150, 'Raphael':150, 'Metatron':150, 'Sariel':150, 'Belial':150,
            '10K Crystal':100,
            '3K Crystal':400,'Intricacy Ring x3':400,'Damascus Crystal x3':400, 'Premium 10-Part Ticket':400,
            'Intricacy Ring':500, 'Lineage Ring x2':500, 'Coronation Ring x3':500, 'Gold Moon x2':500,
            'Gold Moon':800, 'Silver Moon x5':800, 'Bronze Moon x10':800, 'Premium Draw Ticket':800, 'Gold Spellbook x3':800,
            'Half Elixir x10':1000, 'Soul Berry x10':1000, 
            "Satin Feather x10":1250, "Zephyr Feather x10":1250, "Untamed Flame x10":1250, "Rough Stone x10":1250, "Fresh Water Jug x10":1250, "Swirling Amber x10":1250, "Falcon Feather x10":1250, "Vermilion Stone x10":1250, "Hollow Soul x10":1250, "Lacrimosa x10":1250, "Foreboding Clover x10":1250, "Blood Amber x10":1250, "Antique Cloth x10":1250, 
            "White Dragon Scale x10":1250, "Champion Merit x10":1250, "Supreme Merit x10":1250, "Blue Sky Crystal x10":1250, "Rainbow Prism x10":1250, "Rubeus Centrum x10":1250, "Indicus Centrum x10":1250, "Luteus Centrum x10":1250, "Galbinus Centrum x10":1250, "Niveus Centrum x10":1250, "Ater Centrum x10":1250, "Fire Urn x10":1250, "Water Urn x10":1250, "Earth Urn x10":1250, "Wind Urn x10":1250, "Light Urn x10":1250, "Dark Urn x10":1250, "Horn of Bahamut x10":1250, "Primeval Horn x10":1250, "Legendary Merit":1250, 
            "Sword Stone x50":1000, "Dagger Stone x50":1000, "Spear Stone x50":1000, "Axe Stone x50":1000, "Staff Stone x50":1000, "Pistol Stone x50":1000, "Melee Stone x50":1000, "Bow Stone x50":1000, "Harp Stone x50":1000, "Katana Stone x50":1000, "Silver Centrum x5":1000, "Ultima Unit x3":1000, "Fire Quartz x50":1000, "Water Quartz x50":1000, "Earth Quartz x50":1000, "Wind Quartz x50":1000, "Light Quartz x50":1000, "Dark Quartz x50":1000, "Shiva Omega Anima x3":1000, "Europa Omega Anima x3":1000, "Alexiel Omega Anima x3":1000, "Grimnir Omega Anima x3":1000, "Metatron Omega Anima x3":1000, "Avatar Omega Anima x3":1000
        }

        mm = 0 # maximum random loot value
        rm = 0 # rare loot value
        for x in loot:
            mm += loot[x] # calculated here
            if x == 'Premium 10-Part Ticket': rm = mm

        results = []
        l = random.randint(1, 9)
        while len(results) < l:
            n = random.randint(1, mm)
            c = 0
            check = ""
            for x in loot:
                if n < c + loot[x]:
                    check = x
                    break
                else:
                    c += loot[x]
            if check != "":
                if n < rm and len(results) == l - 1: results.append("###" + check) # special chest
                elif n < rm: results.append("$$$" + check) # rare loot
                else: results.append(check) # normal loot
        results.reverse()

        await inter.edit_original_message(embed=self.bot.embed(author={'name':'{} is opening...'.format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, color=self.COLOR), view=ChestRush(self.bot, inter.author.id, results, self.COLOR))
        await self.bot.util.clean(inter, 45)

    """genLoto()
    Generate cards and winning numbers for the summer fortune minigame
    
    Returns
    --------
    tuple: Containing:
        - List of cards
        - List of tier winning digits
    """
    async def genLoto(self) -> tuple:
        cards = []
        while len(cards) < 13:
            if len(cards) < 10: c = str(10 * random.randint(0, 99) + len(cards) % 10).zfill(3) # generate unique last digit
            else: c = str(random.randint(0, 999)).zfill(3)
            if c not in cards:
                cards.append(c)
                if len(cards) == 10: random.shuffle(cards)
            await asyncio.sleep(0)
        winning = [[], [], [], []]
        patterns = [[3, 2], [2, 2], [2, 3], [1, 2]]
        for i, v in enumerate(patterns):
            pad = '{:<0' + str(v[0]+1) + 'd}'
            pad = int(pad.format(1))
            for j in range(0, v[1]):
                while True:
                    c = str(random.randint(0, pad-1)).zfill(v[0])
                    if c not in winning[i]:
                        winning[i].append(c)
                        break
                    await asyncio.sleep(0)
        return cards, winning

    """printLoto()
    Generate the string and thumbnail for the summer fortune minigame
    
    Parameters
    ----------
    revealedCards: List of revealed cards
    revealedWinning: List of revealed winning digits
    prize: List of prize won currently
    total: If true, will print the total prize won
    
    Returns
    --------
    tuple: Containing:
        - Description string
        - Thumbnail url
    """
    async def printLoto(self, revealedCards : list, revealedWinning : list, prize : list, total : bool = False) -> tuple:
        desc = []
        thumb = None
        if len(revealedWinning) > 0:
            desc.append("The winning numbers are:\n")
            for i in range(0, len(revealedWinning)):
                desc.append("**Tier {}**▫️".format(4-i))
                match i:
                    case 0: desc.append("Last Digit▫️") # tier 4
                    case 1: desc.append("First Two▫️") # tier 3
                    case 2: desc.append("Last Two▫️") # tier 2
                desc.append("{} ".format(', '.join(revealedWinning[len(revealedWinning)-1-i])))
                for j in range(0, prize[3-i]): desc.append(":confetti_ball:")
                desc.append("\n")
        if len(revealedCards) > 0:
            desc.append("Your cards are: ")
            for c in revealedCards:
                desc.append(c)
                if c is not revealedCards[-1]: desc.append(", ")
        await asyncio.sleep(0)
        if total:
            if sum(prize) == 0: desc.append("\n{} You won nothing".format(self.bot.emote.get('kmr')))
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
                add_comma = False
                for i in range(0, 4):
                    if prize[3-i] > 0:
                        if add_comma: desc.append(", ")
                        desc.append("**{}** Tier {}".format(prize[3-i], 4-i))
                        add_comma = True
                desc.append(" prizes")
        return ''.join(desc), thumb

    """checkLotoWin()
    Check which tier the card is elligible for
    (summer fortune minigame)
    
    Parameters
    ----------
    card: Card to compare
    winning: List of winning digits
    
    Returns
    --------
    int: Prize tier (0 = lost)
    """
    def checkLotoWin(self, card : str, winning : list) -> int:
        for i in range(0, 4):
            match i:
                case 0: x = card
                case 1: x = card[1:]
                case 2: x = card[:2]
                case 3: x = card[2]
            if x in winning[i]:
                return i + 1
        return 0

    @game.sub_command()
    async def fortune(self, inter: disnake.GuildCommandInteraction, usercards : str = commands.Param(description='List your cards here', default="")) -> None:
        """Imitate the GBF summer fortune game from Summer 2021"""
        await inter.response.defer()
        title = '{} is tempting fate...'.format(inter.author.display_name)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description="The winning numbers are...", color=self.COLOR))
        cards, winning = await self.genLoto()
        cvt = []
        usercards = usercards.split(" ")
        for c in usercards:
            try:
                if c == "": continue
                if len(c) > 3 or int(c) < 0: raise Exception()
            except:
                cvt = []
                break
            cvt.append(c.zfill(3))
            if len(cvt) >= 20: break
        if len(cvt) != 0: cards = cvt
        await asyncio.sleep(2)
        prize = [0, 0, 0, 0]
        desc, thumb = await self.printLoto([], winning, prize)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description=desc, thumbnail=thumb, color=self.COLOR))
        title = "{}'s fortune is".format(inter.author.display_name)
        for i in range(0, len(cards)):
            tier = self.checkLotoWin(cards[:i+1][-1], winning)
            if tier != 0:
                prize[tier-1] += 1
                cards[i] = '**'+cards[i]+'**'
            desc, thumb = await self.printLoto(cards[:i+1], winning, prize, (i == len(cards)-1))
            await asyncio.sleep(0.5)
            await inter.edit_original_message(embed=self.bot.embed(author={'name':title, 'icon_url':inter.author.display_avatar}, description=desc, thumbnail=thumb, color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @game.sub_command()
    async def deal(self, inter: disnake.GuildCommandInteraction) -> None:
        """Deal a random poker hand"""
        await inter.response.defer()
        hand = []
        while len(hand) < 5:
            card = str(random.randint(2, 14)) + random.choice(["D", "S", "H", "C"])
            if card not in hand:
                hand.append(card)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s hand".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="🎴, 🎴, 🎴, 🎴, 🎴", color=self.COLOR))
        for x in range(0, 5):
            await asyncio.sleep(1)
            # check result
            msgs = []
            for i in range(len(hand)):
                if i > x: msgs.append("🎴")
                else: msgs.append(Poker.valueNsuit2head(hand[i]))
                if i < 4: msgs.append(", ")
                else: msgs.append("\n")
            if x == 4:
                await asyncio.sleep(2)
                msgs.append((await Poker.checkPokerHand(hand))[1])
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s hand".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="".join(msgs), color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @game.sub_command()
    async def poker(self, inter: disnake.GuildCommandInteraction, max_round : int = commands.Param(description="Number of rounds to play", ge=1, le=5, default=1)) -> None:
        """Play a poker mini-game with other people (2 to 8 players)"""
        await inter.response.defer()
        players = [inter.author]
        view = JoinGame(self.bot, players, 8, 2)
        desc = "**" + str(max_round) + "** Round(s)\nStarting in {}s\n{}/8 players"
        embed = self.bot.embed(title="♠️ Multiplayer Poker ♥️", description=desc.format(60, 1), color=self.COLOR)
        await inter.edit_original_message(embed=embed, view=view)
        msg = await inter.original_message()
        await view.updateTimer(msg, embed, desc, 60)
        await view.wait()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title="♠️ Multiplayer Poker ♥️", description="Error, at least two Players are required", color=self.COLOR))
            await self.bot.util.clean(inter, 60)
        else:
            await msg.delete()
            random.shuffle(players) # randomize the player order
            win_tracker = {} # track how many wins each player got
            for p in players: # initialize
                win_tracker[p.id] = [(p.display_name if len(p.display_name) <= 10 else p.display_name[:10] + "..."), 0]
            for i in range(0, max_round): # for loop, the game is composed of 3 rounds
                embed = self.bot.embed(title="♠️ Multiplayer Poker ♥️ ▫️ Round {}/{}".format(i+1, max_round), description="Initialization", footer="Round limited to 2 minutes", color=self.COLOR)
                view = Poker(self.bot, players, embed, (0 if max_round == 1 else (max_round - i)))
                await view.update(inter, init=True)
                await view.wait()
                await view.final()
                for p in view.winners: # get the winner and increase their counts
                    win_tracker[p.id][1] += 1
                await asyncio.sleep(10)
                if i < max_round - 1: await view.message.delete()
            if max_round > 1:
                win_tracker = dict(sorted(win_tracker.items(), key=lambda item: item[1], reverse=True)) # sort in reverse order
                msgs = []
                for id, s in win_tracker.items(): # make a string
                    msgs.append("**{}** ▫️ **{}** win(s)\n".format(s[0], s[1]))
                await view.message.edit(embed=self.bot.embed(title="♠️ Multiplayer Poker ♥️ ▫️ Results", description="".join(msgs), color=self.COLOR)) # post it
            await self.bot.util.clean((inter, view.message), 60)

    @game.sub_command()
    async def blackjack(self, inter: disnake.GuildCommandInteraction) -> None:
        """Play a blackjack mini-game with other people (1 to 8 players)"""
        await inter.response.defer()
        players = [inter.author]
        view = JoinGame(self.bot, players, 8, 1)
        desc = "Starting in {}s\n{}/8 players"
        embed = self.bot.embed(title="♠️ Multiplayer Blackjack ♥️", description=desc.format(60, 1), color=self.COLOR)
        msg = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 60)
        await view.wait()
        await msg.delete()
        embed = self.bot.embed(title="♠️ Multiplayer Blackjack ♥️", description="Initialization", footer="Game limited to 4 minutes", color=self.COLOR)
        view = Blackjack(self.bot, players, embed)
        await view.update(inter, init=True)
        await view.wait()
        await self.bot.util.clean(inter, 60)

    @game.sub_command()
    async def tictactoe(self, inter: disnake.GuildCommandInteraction) -> None:
        """Play a game of Tic Tac Toe (2 players Only)"""
        await inter.response.defer()
        players = [inter.author]
        view = JoinGame(self.bot, players, 2, 2)
        desc = "Starting in {}s\n{}/2 players"
        embed = self.bot.embed(title=":x: Multiplayer Tic Tac Toe :o:", description=desc.format(45, 1), color=self.COLOR)
        msg = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title=":x: Multiplayer Tic Tac Toe :o:", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            random.shuffle(players)
            embed = self.bot.embed(title=":x: Multiplayer Tic Tac Toe :o:", description=":x: {} :o: {}\nTurn of **{}**".format(view.players[0].display_name, view.players[1].display_name, view.players[0].display_name), footer="Game limited at 3 minutes", color=self.COLOR)
            view = TicTacToe(self.bot, players, embed)
            await inter.edit_original_message(embed=embed, view=view)
            await view.wait()
        await self.bot.util.clean(inter, 60)

    @game.sub_command()
    async def connectfour(self, inter: disnake.GuildCommandInteraction) -> None:
        """Play a game of Connect Four (2 players Only)"""
        await inter.response.defer()
        players = [inter.author]
        view = JoinGame(self.bot, players, 2, 2)
        desc = "Starting in {}s\n{}/2 players"
        embed = self.bot.embed(title=":red_circle: Multiplayer Connect Four :yellow_circle:", description=desc.format(45, 1), color=self.COLOR)
        msg = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title=":red_circle: Multiplayer Connect Four :yellow_circle:", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            random.shuffle(players)
            embed = self.bot.embed(title=":red_circle: Multiplayer Connect Four :yellow_circle:", description=":red_circle: {} :yellow_circle: {}".format(players[0].display_name, players[1].display_name), footer="Game limited to 8 minutes", color=self.COLOR)
            view = ConnectFour(self.bot, players, embed)
            await view.update(inter, init=True)
            await view.wait()
        await self.bot.util.clean(inter, 60)

    @game.sub_command()
    async def battleship(self, inter: disnake.GuildCommandInteraction) -> None:
        """Play a game of Battle Ship (2 players Only)"""
        await inter.response.defer()
        players = [inter.author]
        view = JoinGame(self.bot, players, 2, 2)
        desc = "Starting in {}s\n{}/2 players"
        embed = self.bot.embed(title=":ship: Multiplayer Battle Ship :cruise_ship:", description=desc.format(45, 1), color=self.COLOR)
        msg = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title=":ship: Multiplayer Battle Ship :cruise_ship:", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            random.shuffle(players)
            embed = self.bot.embed(title=":ship: Multiplayer Battle Ship :cruise_ship:", description=":ship: {} :cruise_ship: {}".format(players[0].display_name, players[1].display_name), fields=[{'name':players[0].display_name, 'value':'dummy'}, {'name':players[1].display_name, 'value':'dummy'}], footer="Game limited to 8 minutes", color=self.COLOR, inline=False)
            view = BattleShip(self.bot, players, embed)
            await view.update(inter, init=True)
            await view.wait()
        await self.bot.util.clean(inter, 60)

    @game.sub_command()
    async def rockpaperscissor(self, inter: disnake.GuildCommandInteraction, bestof : int = commands.Param(description="How many rounds to win", ge=1, le=10, default=1)) -> None:
        """Play a Rock Paper Scissor mini-game with other people (2 players Only)"""
        await inter.response.defer()
        players = [inter.author]
        view = JoinGame(self.bot, players, 2, 2)
        desc = "Best of **" + str(bestof) + "**\nStarting in {}s\n{}/2 players"
        embed = self.bot.embed(title="🪨 Multiplayer Rock Paper Scissor ✂️", description=desc.format(45, 1), color=self.COLOR)
        msg = await inter.channel.send(embed=embed, view=view)
        await view.updateTimer(msg, embed, desc, 45)
        await view.wait()
        await msg.delete()
        if len(players) == 1:
            await inter.edit_original_message(embed=self.bot.embed(title="🪨 Multiplayer Rock Paper Scissor ✂️", description="Error, a 2nd Player is required", color=self.COLOR))
        else:
            scores = [0, 0]
            embed = self.bot.embed(title="🪨 Multiplayer Rock Paper Scissor ✂️ ▫️ Best of {}".format(bestof), description="Initialization", footer="Round limited to 60 seconds", color=self.COLOR)
            while True:
                view = RPS(self.bot, players, embed, scores, bestof)
                await view.update(inter, init=True)
                await view.wait()
                await view.timeoutCheck(inter)
                if scores[0] >= bestof or scores[1] >= bestof: break
                await asyncio.sleep(10)
        await self.bot.util.clean(inter, 60)

    @commands.slash_command(name="random")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 50, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def _random(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @_random.sub_command()
    async def dice(self, inter: disnake.GuildCommandInteraction, dice_string : str = commands.Param(description="Format is NdN. Minimum is 1d6, Maximum is 10d100")) -> None:
        """Roll some dies"""
        try:
            await inter.response.defer()
            tmp = dice_string.lower().split('d')
            n = int(tmp[0])
            d = int(tmp[1])
            if n <= 0 or n> 10 or d < 6 or d > 100: raise Exception()
            rolls = []
            for i in range(n):
                rolls.append(random.randint(1, d))
                msgs = []
                for j in range(len(rolls)):
                    msgs.append("{}".format(rolls[j]))
                msgs = ["### ", ", ".join(msgs)]
                if len(rolls) == n:
                    msgs.append("\n**Total**: {:}, **Average**: {:}, **Percentile**: {:.1f}%".format(sum(rolls), round(sum(rolls)/len(rolls)), sum(rolls) * 100 / (n * d)).replace('.0%', '%'))
                await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} rolled {}...".format(inter.author.display_name, dice_string), 'icon_url':inter.author.display_avatar}, description="".join(msgs), color=self.COLOR))
                await asyncio.sleep(1)
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Invalid string `{}`\nFormat must be `NdN` (minimum is `1d6`, maximum is `10d100`)".format(dice_string), color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @_random.sub_command()
    async def coin(self, inter: disnake.GuildCommandInteraction) -> None:
        """Flip a coin"""
        await inter.response.defer()
        coin = random.randint(0, 1)
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} flipped a coin...".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description=(":coin: It landed on **Head**" if (coin == 0) else ":coin: It landed on **Tail**"), color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @_random.sub_command()
    async def quota(self, inter: disnake.GuildCommandInteraction) -> None:
        """Give you your GW quota for the day"""
        await inter.response.defer()
        h = random.randint(2000, 10000)
        m = random.randint(300, 800)
        c = random.randint(1, 100)

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
            await self.bot.util.clean(inter, 40)
            return
        elif c == 4:
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
        h = h * 100000
        m = m * 10

        await inter.edit_original_message(embed=self.bot.embed(title="{} {}'s daily quota".format(self.bot.emote.get('gw'), inter.author.display_name), description="**Honor:** {:,}\n**Meat:** {:,}".format(h, m), thumbnail=inter.author.display_avatar, color=self.COLOR))
        await self.bot.util.clean(inter, 40)

    """randint()
    Generate a simple pseudo random number based on the seed value
    
    Parameters
    ----------
    seed: Integer used as the seed
    
    Returns
    ----------
    int: Pseudo random value which you can use as the next seed
    """
    def randint(self, seed : int) -> int:
        return ((seed * 1103515245) % 4294967296) + 12345

    @_random.sub_command()
    async def character(self, inter: disnake.GuildCommandInteraction) -> None:
        """Generate a random GBF character"""
        await inter.response.defer()
        seed = (inter.author.id + int(self.bot.util.UTC().timestamp()) // 86400) # based on user id + day
        values = {
            'Rarity' : [['SSR', 'SR', 'R'], 3, True, None], # random strings, modulo to use, bool to use emote.get, seed needed to enable
            'Race' : [['Human', 'Erune', 'Draph', 'Harvin', 'Primal', 'Other'], 6, False, None],
            'Element' : [['fire', 'water', 'earth', 'wind', 'light', 'dark'], 6, True, None],
            'Gender' : [['Unknown', '\♂️', '\♀️'], 3, False, None],
            'Series' : [['Summer', 'Yukata', 'Grand', 'Holiday', 'Halloween', 'Valentine'], 30, True, 6]
        }
        msgs = []
        rarity_mod = 0
        for k in values:
            v = seed % values[k][1]
            if k == "Rarity": rarity_mod = 7 - 2 * v
            if values[k][3] is not None and v >= values[k][3]:
                continue
            if values[k][2]: msgs.append("**{}** ▫️ {}\n".format(k, self.bot.emote.get(values[k][0][v])))
            else: msgs.append("**{}** ▫️ {}\n".format(k, values[k][0][v]))
            seed = self.randint(seed)
        msgs.append("**Rating** ▫️ {:.1f}".format(rarity_mod + (seed % 31) / 10))

        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s daily character".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="".join(msgs), color=self.COLOR))
        await self.bot.util.clean(inter, 30)

    @_random.sub_command()
    async def xil(self, inter: disnake.GuildCommandInteraction) -> None:
        """Generate a random element for Xil (Private Joke)"""
        await inter.response.defer()
        g = random.Random()
        elems = ['fire', 'water', 'earth', 'wind', 'light', 'dark']
        g.seed(int((int(self.bot.util.UTC().timestamp()) // 86400) * (1.0 + 1.0/4.2)))
        e = g.choice(elems)

        await inter.edit_original_message(embed=self.bot.embed(title="Today, Xil's main element is", description="### {} **{}**".format(self.bot.emote.get(e), e.capitalize()), color=self.COLOR))
        await self.bot.util.clean(inter, 30)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 15, commands.BucketType.user)
    @commands.max_concurrency(8, commands.BucketType.default)
    async def ask(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @ask.sub_command()
    async def choice(self, inter: disnake.GuildCommandInteraction, choices : str = commands.Param(description="Format is Choice 1;Choice 2;...;Choice N")) -> None:
        """Ask me to pick a choice"""
        try:
            await inter.response.defer()
            possible = choices.split(";")
            while '' in possible:
                possible.remove('')
            if len(possible) < 2: raise Exception()
            await inter.edit_original_message(embed=self.bot.embed(author={'name':"{}'s choice".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="Possible choices: `{}`\n### I pick: `{}`".format('` `'.join(possible), random.choice(possible)), color=self.COLOR))
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Give me a list of something to choose from, separated by `;`", color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @ask.sub_command()
    async def question(self, inter: disnake.GuildCommandInteraction, question : str = commands.Param()) -> None:
        """Ask me a question"""
        await inter.response.defer()
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} asked".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="`{}`\n### {}".format(question, random.choice(["It is Certain.","It is decidedly so.","Without a doubt.","Yes definitely.","You may rely on it.","As I see it, yes.","Most likely.","Outlook good.","Yes.","Signs point to yes.","Reply hazy, try again.","Ask again later.","Better not tell you now.","Cannot predict now.","Concentrate and ask again.","Don't count on it.","My reply is no.","My sources say no.","Outlook not so good.","Very doubtful."])), color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @ask.sub_command()
    async def when(self, inter: disnake.GuildCommandInteraction, question : str = commands.Param()) -> None:
        """Ask me when will something happen"""
        await inter.response.defer()
        if question.lower().startswith("when ") and len(question) > 5: question = question[5:]
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} asked".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="`When {}`\n### {}".format(question, random.choice(["Never", "Soon:tm:", "Ask again tomorrow", "Can't compute", "42", "One day, my friend", "Next year", "It's a secret to everybody", "Soon enough", "When it's ready", "Five minutes", "This week, surely", "My sources say next month", "NOW!", "I'm not so sure", "In three days"])), color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @ask.sub_command()
    async def element(self, inter: disnake.GuildCommandInteraction, question : str = commands.Param()) -> None:
        """Ask for a random gbf element"""
        await inter.response.defer()
        await inter.edit_original_message(embed=self.bot.embed(author={'name':"{} asked".format(inter.author.display_name), 'icon_url':inter.author.display_avatar}, description="`{}`\n# {}".format(question, self.bot.emote.get(random.choice(["fire", "water", "earth", "wind", "light", "dark"]))), color=self.COLOR))
        await self.bot.util.clean(inter, 45)

    @commands.message_command(name="UwU")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(5, 90, commands.BucketType.guild)
    async def uwu(self, inter: disnake.MessageCommandInteraction, message: disnake.Message) -> None:
        """UwU-tize a message"""
        await inter.response.defer()
        msg = message.clean_content.replace("r","w").replace("R","W").replace("than","dan").replace("Than","Dan").replace("THan","Dan").replace("THAn","Dan").replace("THAN","DAN").replace("thaN","daN").replace("thAn","dAn").replace("thAN","dAN").replace("tHAN","DAN").replace("l","w").replace("L","W").replace("oy","oi").replace("oY","oI").replace("Oy","Oi").replace("OY","OI").replace("the","de").replace("The","De").replace("THe","De").replace("THE","DE").replace("thE","dE").replace("tHe","De").replace("you","u").replace("You","U").replace("YOu","U").replace("YOU","U").replace("yoU","u").replace("yOu","u").replace("yOU","U")
        if len(msg) == 0 or len(msg) >= 3800:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="This message can't be converted", color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="UwU", description="[Original Message](https://discord.com/channels/{}/{}/{})\n```\n{}\n```".format(inter.guild.id, inter.channel.id, message.id, msg), color=self.COLOR))