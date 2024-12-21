# Rosetta  
  
* **[Granblue Fantasy](https://game.granbluefantasy.jp) Discord Bot**.  
* **Command List** and **Help** available [Here](https://mizagbf.github.io/discordbot.html).  
  
![image](https://raw.githubusercontent.com/MizaGBF/Rosetta-Public/main/assets/banners/standard.png)
> [!CAUTION]  
> If you're looking for an invite for my instance, it's **not open to public**.  
> Use this repo if you have the how-to to host your own instance.  
> If you're somehow close to me in some way however, feel free to ask and I'll see if it's possible.  
  
## Table of contents  
  
* [Requirements](#requirements)  
* [General Overview](#general-overview)  
* [Usage](#usage)  
* [Setup](#setup)  
* [Emojis](#emojis)  
* [Debug Mode](#debug-mode)  
* [Updating](#updating)  
* [Additional Informations](#additional-informations)  
* [Customize](#customize)  
  
## Requirements  
  
* **Operating System**: Anything supported by the required Python version and third-party modules.  
* **Hardware**: A few hundred MB of RAM, 100 MB of disk space for the bot itself.  
* **Software**: [Python 3.11](https://www.python.org/downloads/).  
* **Third-Party Python packages**: See [below](#third-party-packages) for details. 
  
### Third-party packages  
  
Here's the list of third-party python modules installed from [requirements.txt](https://github.com/MizaGBF/Rosetta-Public/blob/master/requirements.txt).  
* **[Disnake](https://github.com/DisnakeDev/disnake)**, a Discord API wrapper.  
* **[Pydrive2](https://github.com/iterative/PyDrive2)**, a Google Drive API wrapper.  
* **[psutil](https://github.com/giampaolo/psutil)**, a library to retrieve system and process informations.  
* **[Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/)**, a library for HTML parsing.  
* **[Pillow](https://github.com/python-pillow/Pillow)**, a PIL fork for image processing. Only used by the optional [YouCrew](https://github.com/MizaGBF/Rosetta-Public/blob/main/cogs/youcrew.py) Command Cog.  
* **[deep-translator](https://github.com/nidhaloff/deep-translator)**, a library to access many online translator tools.  
  
### Additional Considerations  
  
* The bot is designed to run on Linux but it has been tested to run on Windows.  
* [jemalloc](https://github.com/jemalloc/jemalloc) is recommended to install if you plan to run it for long periods of time. It's to avoid the high Memory Usage problem encountered on its predecessor, [MizaBOT](https://github.com/MizaGBF/MizaBOT), which was caused by memory fragmentation (although, Rosetta evolved a lot since, I don't know if it's still victim of this issue).  
Refer to the [jemalloc repository](https://github.com/jemalloc/jemalloc), my [Dockerfile](https://github.com/MizaGBF/Rosetta-Public/blob/master/Dockerfile) for how I set it up, and the [Python documentation](https://docs.python.org/3/using/cmdline.html#envvar-PYTHONMALLOC) for details.  
  
## General Overview  
  
* Rosetta is a Discord Bot themed around the Browser Game [Granblue Fantasy](https://game.granbluefantasy.jp), providing utility commands and advanced features to the users, along with moderation and more generalistic commands.  
* This project is a fork of [MizaBOT v9.31b](https://github.com/MizaGBF/MizaBOT) featuring massive improvements, bug fixes, security fixes and so on.  
* Saving is done simply on Google Drive. If you want to use something else, you'll have to rewrite the `drive.py` component. Compressed Save Files only weight around 13~14 KB but that number can grow, the more Discord Servers that Rosetta has access to.  
  
### Folder structure  
  
> [!IMPORTANT]  
> The folders below are required for the Rosetta to function properly and shouldn't be deleted unless mentioned otherwise.  
> The `__init__.py` files found in some of those folders shouldn't be deleted either.  

The `assets` folder contains various images and other files used by the bot:  
* The various **icon.png** files are automatically set as the bot avatar at the beginning of related months.  
* The content of the `emojis` folder is automatically used during the boot to update the bot Application Emojis list. Refer to [Emojis](#emojis) for details.  
* The content of the `hosted` folder is merely a backup of some files I host on a github page. In the advent I disappear, you must rehost them somewhere, and update their links in the code.  
* `font.ttf` is used by one command specific to my crew. You can remove it if you remove the corresponding cog.  
  
The `cogs` folder contains the bot Command Cogs, which can summarize as multiple Command groups and their associated functions:  
* You can delete the cogs you don't want to use (be careful that they don't run some critical task) or add your own cogs.  
* In particular, `youcrew.py` contains commands specific to my crew. You can remove it if you don't wish to use it, as it'll likely need some tweaks to use. Refer to [YouCrew IDs](#youcrew-ids) for details.  
* Most **cogs** are standalone and should work even if others are missing. However, I suggest to never remove `admin.py`, `moderation.py`, `gw.py` and `granblue.py` at the minimum.
  
The `components` folder contains the bot components, which are piece of codes needed for it to work. These files can't be removed.  
  
The `views` folder contains the bot interactions to make interfaces and such for some commands. Unused ones can be removed, if you are sure they aren't referenced anywhere in the code.  

The `tools` folder contains a few standalone pieces of code which might help you:  
* `save_gzip.py` and `save_lzma.py` can be used to decompress/compress a save file. You can drag and drop a file on them but I suggest using them in a terminal/command prompt. Current save data are saved to the drive in the LZMA format. `save_gzip.py` is technically not used anymore.  
  
> [!CAUTION]  
> It's a good practice to **always** make a copy of your save data before attempting any manipulation on it.
  
* `avatar_to_gif.py` was used to generate the GIF versions of the bot avatars, in the assets folder. It's a bit rudimentary but not hard to use, if you wish. Add a [Gifsicle](https://github.com/kohler/gifsicle) executable in the same folder for a better result.  
  
## Usage  
  
### Method 1:  

> [!IMPORTANT]  
> This is the intended way to use the bot.
  
Simply build and run the [Dockerfile](https://github.com/MizaGBF/Rosetta-Public/blob/master/Dockerfile). Refer to the Docker Documentation for details.
  
### Method 2:   
  
> [!IMPORTANT]  
> This method is mostly used for testing, although the end result should be analog to method 1.
  
Open a command prompt (Windows) or terminal (Linux) and run `pip install -r requirements.txt` in the bot folder, to install the third-party modules. You only need to do it once or if it gets updated.  
Then, you can run the bot with `python -O bot.py -r` to start the bot (`-O` is optional).  
  
Here are the possible usages, taken from the **help** (obtained from `python bot.py -h`):
```
usage: bot.py [-h] [-r] [-d] [-t] [-c] [-g [PATH]]

options:
  -h, --help            show this help message and exit
  -r, --run             run Rosetta.
  -d, --debug           set Rosetta to the Debug mode ('config_test.json' will be loaded, some operations such as saving will be disabled).
  -t, --test            attempt to boot Rosetta and load the command cogs, in Debug mode.
  -c, --clean           desync Guild slash commands (to remove commands from a Debug mode instance, from all server).
  -g [PATH], --generatehelp [PATH]
                        generate the discordbot.html help file (the destination PATH can be set).
```
  
Except `-d`/`--debug`, all arguments are mutually exclusive.  
Check the **Debug Mode** section for more infos on the `-d`/`--debug` argument.   
  
### Stop Rosetta   
  
A simple CTRL+C or sending a SIGTERM or SIGINT signal will make the bot saves and exits gracefully.  
The bot returns the following codes upong exiting:  
- 0: Exited properly.  
- 1: Failed to load `config.json` on boot. Check if the file is missing or corrupted.  
- 2: Failed to load `save.json` on boot. Check if the file is corrupted.  
- 3: Failed to load the save data from Google Drive. Maybe Google is having troubles or the save file is missing from the folder.  
- 4: Failed to connect to Google Drive with your Service account.  
- 5: Failed to initialize a bot component.  
- 6: Bot instance initialization failure.  
  
> [!NOTE]  
> The `/owner bot reboot` command doesn't actually reboot the bot, it's a simple shutdown with the exit code **0**.  
> My instance is setup with Watchtower and automatically reboot once stopped, hence why it's called reboot.  
  
## Setup  
  
### Creating config.json  
  
> [!IMPORTANT]  
> If you haven't yet, go to your Discord account settings, *Advanced* and turn on *Developer Mode*.  
> Now you can right click on anything to copy their IDs.  
  
The bot is configured with a simple file called `config.json`. Create one in its folder and paste the following:  
```json
{
    "tokens" : {
        "discord" : "DISCORD_TOKEN",
        "drive" : "SAVE_FOLDER_ID",
        "upload" : "",
        "files" : "FILE_FOLDER_ID"
    },
    "ids" : {
        "debug_channel" : BOT_DEBUG_CHANNEL_ID,
        "image_upload" : BOT_IMAGE_UPLOAD_CHANNEL_ID,
        "debug_server" : BOT_SERVER_ID,
        "you_server" : YOUR_CREW_OR_THE_BOT_SERVER_ID,
        "you_announcement" : YOUR_CREW_ANNOUNCEMENT_CHANNEl_ID,
        "you_meat" : YOUR_CREW_MEAT_CHANNEl_ID,
        "you_member" : YOUR_CREW_MEMBER_ROLE_ID,
        "you_atkace" : YOUR_CREW_ATK_ACE_ROLE_ID,
        "you_deface" : YOUR_CREW_DEF_ACE_ROLE_ID,
        "you_fo" : YOUR_CREW_FIRST_OFFICER_ROLE_ID,
        "you_gl" : YOUR_CREW_LEADER_ROLE_ID
    },
    "games" : [
        "Granblue Fantasy",
        "Granblue Fantasy: Versus Rising",
        "Granblue Fantasy: Relink"
    ],
    "granblue": {
        "gbfgcrew" : {"aion no me":"645927", "aion":"645927", "bellabarca":"977866", "bullies":"745085", "bullied":"1317803", "chococat":"940560", "chococats":"940560", "cogfriends":"1049216", "cog":"1049216", "cowfag":"841064", "cowfags":"841064", "\u4e2d\u51fa\u3057\u306e\u5e78\u305b":"1036007", "cumshot":"1036007", "cumshot happiness":"1036007", "dem bois":"705648", "ded bois":"705648", "dembois":"705648", "demboi":"705648", "dedbois":"705648", "fleet":"599992", "haruna":"472465", "cug":"1161924", "lilypals":"1161924", "lilypal":"1161924", "\u5c0f\u3055\u306a\u5973\u306e\u5b50":"432330", "little girls":"432330", "lg":"432330", "little girl":"432330", "sixters":"1380234", "sixter":"1380234", "soy":"1601132", "onion":"1601132", "onions":"1601132", "oppaisuki":"678459", "oppai":"678459", "pcs":"632242", "quatrebois":"1141898", "quatreboi":"1141898", "the bathtub":"1580990", "thebathtub":"1580990", "bathtub":"1580990", "(you)":"581111", "you":"581111", "(you) too":"1010961", "(you)too":"1010961", "u2":"1010961", "youtoo":"1010961", "you too":"1010961", "a-team":"1744673", "ateam":"1744673", "a":"1744673", "grape":"1807204", "grapes":"1807204", "toot":"844716", "nier":"1837508", "nier2":"1880420"},
        "othercrew" : {"ssf":"677159", "hsp":"147448", "kingdom":"1377462", "atelier":"418206", "lum1":"388489", "lum2":"401211", "beafriends":"940700", "waifuanon":"588156", "lolibabas":"1593480", "lolibaba":"1593480", "hagchads":"1593480", "hagchad":"1593480", "mesugaki":"1593480", "lazytown":"1586134", "mavericks":"1629318", "maverick":"1629318"}
    }
}
```  
  
* `"tokens"` contains the tokens and IDs used by the Discord and Google Drive clients.  
* `"ids"` contains various Discord IDs (user, server, channel...) required for the bot to work. In Discord, with *Developer Mode* enabled, you can right-click on anything to copy an ID. **IDs are integers**, i.e. numbers. Don't put them between quotes `"` like tokens.  
* `"games"` contains a list of games to be displayed in the bot activity status.  
* `"granblue"` contains shorthands to crew ids, separated in two categories: `"gbfgcrew"`, crews from the the [/gbfg/ 4chan community](https://boards.4chan.org/vg/catalog#s=gbfg) and "`othercrew`", related crews or crews with access to Rosetta.  
  
The following sections will explain how to fill the tokens and IDs.  
  
### Creating your Discord Application  
  
Go to the [Discord Developer Portal](https://discord.com/developers/docs/game-sdk/applications) > *Applications* > *New Application* and create your application.  
Go to *Bot* on the left and click **Reset Token**. Your Bot Token will appear, copy it and replace `DISCORD_TOKEN` with it in `config.json` (don't forget to put it between quotes **"**, it's a string).  
Next, turn on the **Message Content Intent**, below.  
  
> [!NOTE]  
> If you ever change the Intents used by your bot instance, you'll also need to update them in `bot.py` at the end of the `_init_()` function, or **it won't take effect**. Refer to the [documentation](https://docs.disnake.dev/en/stable/intents.html) for details.  
  
### Configuring your Google Service Account  
  
**The [Google API website](https://console.cloud.google.com/apis/dashboard) is a pain in the butt to navigate and use, so I'll only give general steps.**  
  
* Find a way to create an application.  
* Go to *Credentials* on the left, create a new **Service account**.  
* Copy the email associated with this service account (it should be something like `XXX@YYYY.iam.gserviceaccount.com` ).  
* You might need to give it some permissions (*Permissions* tab, *Grant Access*, use the application email.).  
* Add a new key (*Key* tab), pick the *JSON* format and accept. Rename this file to `service-secrets.json` and put it in the bot folder, alongside `config.json`.  
  
Go to your Google Drive and create two folders, one for the bot save data and one for GW related files.  
Open the save data one and copy the url. It should be something like `https://drive.google.com/drive/folders/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`. Copy the `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` part and replace `SAVE_FOLDER_ID` in `config.json` (don't forget to put it between quotes **"**, it's a string).  
Do the same thing for the other folder and `FILE_FOLDER_ID`.  
The third folder ID is currently unused but you are free to create one and set the key in `config.json` too, for possible future uses.  
  
Then, **for each of those folders**, right click on them and select *Share*. Add your service account (again, using the email you copied) to each of them.  
  
### Setup a Server for the Bot and invite it  
  
Create a Discord Server for your bot.  
The bot requires three text channels to be created:
- One to output debug infos.  
- One to upload images.  
  
Create them.  
  
Right click on the debug channel, copy the ID and replace BOT_DEBUG_CHANNEL_ID in `config.json`.  
Same for the second and `BOT_IMAGE_UPLOAD_CHANNEL_ID`.  
  
Right click on the Server itself (in your server list), same thing and replace `BOT_SERVER_ID`.  
  
Do the same thing to fill the remaining IDs.  
  
If you did everything properly, you're set. 
On the [Discord Developer Portal](https://discord.com/developers/docs/game-sdk/applications), copy the *Application ID* (under *General Information).  
In the following: `https://discord.com/api/oauth2/authorize?client_id=XXXXXXXXXXXXXXXX&permissions=1644905889015&scope=bot%20applications.commands`, replace `XXXXXXXXXXXXXXXX` by this ID. This will be your bot invite link.  
Use it now and invite your bot to the server (no need to start the bot). If you did it right, it should show up in the member list.  
  
### YouCrew IDs  
  
The IDs whose names start with `you_` such as "you_server" are for my crew.  
If you plan to use your bot in your own crew, set the corresponding IDs to the channels and roles you wish.  
These IDs are mostly used by the [YouCrew Command Cog](https://github.com/MizaGBF/Rosetta-Public/blob/main/cogs/youcrew.py).  
If you don't plan to use it, you might remove this Cog file from the `cogs` folder, along with the related IDs in `config.json`.  
  
### First Boot

Use whatever method you chose in [Usage](#usage) to run the Bot.  
If Rosetta is starting properly, you should get a **Rosetta is Ready** message in the channel that you set as your debug one.  
The logs should also look similar to this:  
  
```
INFO:Rosetta:2024-12-20 12:00:16 | [BOOT] Logger started up. Loading components...
INFO:Rosetta:2024-12-20 12:00:16 | [BOOT] Components loaded
INFO:Rosetta:2024-12-20 12:00:16 | [BOOT] Initializing important components...
INFO:Rosetta:2024-12-20 12:00:16 | [BOOT] Important components initialized
INFO:Rosetta:2024-12-20 12:00:16 | [BOOT] Loading the config file...
INFO:Rosetta:2024-12-20 12:00:16 | [BOOT] Downloading the save file...
INFO:Rosetta:2024-12-20 12:00:19 | [BOOT] Reading the save file...
INFO:Rosetta:2024-12-20 12:00:19 | [BOOT] Initializing remaining components...
INFO:Rosetta:2024-12-20 12:00:19 | [BOOT] Remaining components initialized
INFO:Rosetta:2024-12-20 12:00:19 | [BOOT] Initializing disnake.InteractionBot with Intent flags: 0b1100011111111011111101
WARNING:disnake.client:PyNaCl is not installed, voice will NOT be supported
INFO:Rosetta:2024-12-20 12:00:19 | [BOOT] Initialization complete
INFO:Rosetta:2024-12-20 12:00:19 | [MAIN] Loading cogs...
WARNING:Rosetta:2024-12-20 12:00:20 | [COG] test.py is missing and will be ignored.
Ignore this message if it's intended.
INFO:Rosetta:2024-12-20 12:00:20 | [MAIN] All cogs loaded
INFO:Rosetta:2024-12-20 12:00:20 | [MAIN] v12.0.0 starting up...
INFO:Rosetta:2024-12-20 12:00:20 | [NET] Default user-agent set to `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Rosetta/12.0.0`
INFO:Rosetta:2024-12-20 12:00:23 | [CHANNEL] Channel 'debug' registered
INFO:Rosetta:2024-12-20 12:00:23 | [CHANNEL] Channel 'image' registered
INFO:Rosetta:2024-12-20 12:00:23 | [MAIN] Rosetta is ready
```  
  
> [!CAUTION]  
> If it doesn't start, be sure to check for error messages and so on, before reporting to me.   
  
> [!IMPORTANT]  
> If it starts, congratulations.  
> All the remaining setup is done via the `/owner` commands.  
> Refer to [Additional Informations](#additional-informations) below if you need more help.  
  
You can stop the bot with a CTRL+C or by sending a SIGTERM or SIGINT signal.  
  
> [!TIP]  
> On Windows, the Task Manager sends a SIGKILL, so CTRL+C is preferred.  
> On Linux, you can do something like `kill -INT <bot_pid>` in a terminal.  
  
## Emojis  
  
The emotes found in `assets/emojis` folder will be automatically loaded and uploaded on boot to your bot **Emojis** list.  
It can take some time, so it's normal if emotes don't display right away at the start.  
  
> [!IMPORTANT]
> You can add more to the folder if you wish to use them in your own commands, but you're limited to **2000** emojis par application.  
> You can find them on your [dashboard](https://discord.com/developers/applications), under the corresponding application, then **Emojis**.  
> If you remove an emoji from `assets/emojis`, it'll automatically be deleted from the **Emojis** list on the next boot.  

To use them in the code, you must call the `emote` component `get` method with the emoji name, without its extension.  
For example, for `fire.png`, call `self.bot.emote.get('fire')`.  
If you decide to add more emojis for custom commands, make sure they don't have special characters or the upload might fail.  
  
## Debug Mode  
> [!IMPORTANT]
> In Debug mode, the bot is unable to write to your Google Drive.  
> Also, multiplayer game commands will let you play against yourself, for testing purpose (but not all games behave properly in this scenario).  
> This mode is intended for testing and debugging, on a second, separate, Bot instance.  
  
> [!TIP]  
> You can skip this section if you don't plan to use it.
   
Using the `-d`/`--debug` argument requires to set up `config_test.json`.  
Same principle, but shorter:  
```json
{
    "tokens" : {
        "discord" : "DISCORD_TOKEN",
        "drive" : "SAVE_FOLDER_ID",
        "upload" : "",
        "files" : "FILE_FOLDER_ID"
    }
}
```  
For DISCORD_TOKEN, simply create a second application and bot and put its token here.  
For the folders, either reuse the existing ones (recommended if you wish to load an existing save file) or make new ones if you want to use separate data.  
  
## Updating  
  
First and foremost, if you want to run some sort of automation on this repo to always have the latest version, **DON'T**.  
While I test the bot before pushing changes to this repository, I'm alone on this project and can't guarantee some bugs or mistakes haven't slipped in.  
So here's my recommendations:  
1. Run and update your own copy. It can be a fork, a manual download, etc... Whatever you prefer.  
2. Read the [commit list](https://github.com/MizaGBF/Rosetta-Public/commits/main/). If I just pushed a new version a few hours ago, maybe wait tomorrow. If it's a bugfix, it might be fine. The project is fairly mature, there shouldn't be a need to hurry to a new version.  
3. If the save file format is updated, your save file will automatically be converted to the new one. However, it won't be usable on old versions if, for some reason, you plan to downgrade. So, while it shouldn't be necessary, feel free to make a backup beforehand.  
4. If `config.json` is updated, so should be the example at the beginning of this readme. Make a backup, compare the differences, add what got added and remove what's not needed anymore.  
5. Check changes to `cogs/admin.py` for new Owner commands you might need ro run, to setup new features.  
6. If `requirements.txt` got updated and you aren't running the bot via a Dockerfile, you should run `pip install -r requirements.txt` again.  
7. If you developped your own Custom Cogs, you'll have to read the code and make sure no breaking changes got introduced. Major enough changes are usually when the first or second version number is increased (for example, `1.0.0` to `2.0.0` or `1.0.0` to `1.1.0`).  
  
> [!TIP]  
> If you're new to Github, you can see, on the page, when each files got modified for the last time on the right of their names.  
  
### Migrating from v11 to v12  
  
If you plan to update Rosetta from version `11.X.X` to version `12.X.X`, here are a few things to care for:  
* Don't blindly overwrite your previous version with the new one. Instead, get a clean copy and copy over your JSON files (`config.json`, `save.json`, `service-secrets.json`, etc...), SQL files (`GW.sql`, `GW_old.sql`...), your custom Cogs and codes (if any), custom Emojis (if any) and custom avatars (if any).  
* Cogs and Views developped for a version `11.X.X` should work fine on version `12.X.X`.  
* `config.json` has been slimed down consiberably. Check out [Creating config.json](#creating-config.json) to see what keys remain. You can remove the ones not here anymore (unless you use them in a custom Cog or View).  
* `config_test.json` has also lost the `"debug"` key. You can remove it, if you were using the [Debug Mode](#debug-mode).  
  
## Additional Informations  
  
Further setup might be required to use some features.  
The `/owner` command group from the `admin.py` cog should contain what you need to set/edit some of the bot data.  
Here's a quick overview of the sub command groups:  
* `/owner utility`: A bunch of small utility commands to execute code on the fly, answer a bug report, leave the server, etc... You should rarely need those.  
* `/owner ban`: Commands to ban/unban an user from using certain features from the bot.  
* `/owner bot`: Commands to stop the bot, get its invite link, list its guilds or change it's avatar with one in the `assets` folder.  
* `/owner data`: Commands related to the save data. You can trigger a save manually, retrieve a file, clean some data and so on. While you can technically load a save with the `/owner data load` command, a reboot is usually preferred.  
* `/owner maintenance`: Commands to manually set or clear a GBF maintenance date.  
* `/owner stream`: Commands to manually set a GBF upcoming stream date and infos.  
* `/owner schedule`: Commands to manually edit the GBF schedule or to force an update.  
* `/owner account`: Commands to set a GBF account on the bot. I won't provide any help with this and the commands are self-explanatory.  
* `/owner db`: Commands to manually set a Dread Barrage event.  
* `/owner gw`: Commands to manually set and edit an Unite and Fight event.  
* `/owner buff`: Commands to debug the GW buff data used by my crew. I haven't used it in a long while.  
* `/owner gacha`: Commands to clear the gacha banner and change the `/roll roulette` command settings.  

> [!WARNING]  
> I rarely use most of those commands, there is a small chance they might be hiding some bugs.  
  
If you want a GW.sql file for the ranking commands, you can go grab the most recent one [here](https://drive.google.com/drive/folders/11DcUKeO6Szd5ZEJN9q57MQl772v64_R2), rename it to `GW.sql` and put it in the `"files"` drive folder.  
  
## Customize  
  
> [!TIP]  
> The following sections are for customizing the bots with your own Command Cogs, and so on.  
> You can skip if you don't plan to do so.  
  
### Adding a new Command Cog  
  
> [!TIP]  
> Check existing cogs if you need examples of more advanced behaviors.  
  
The following is a template to make your own Command Cog, with comments:  
```python
from __future__ import annotations # used for Type Hints
import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING: # used for Type Hints
    from ..bot import DiscordBot

class Example(commands.Cog):
    """The cog description"""
    COLOR : int = 0xffffff # The color used by the Embed in this cog commands and in the online help

    def __init__(self : Example, bot : DiscordBot) -> None:
        self.bot = bot

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    async def helloworld(self : commands.slash_command, inter : disnake.ApplicationCommandInteraction) -> None:
        """This is this command description"""
        await inter.response.defer(ephemeral=True) # good practice to always defer first. Ephemeral flag is if you want your command to only show to the user
        # This command will be usable by doing /helloworld
        #
        # Do stuff...
        #
        await inter.edit_original_message(embed=self.bot.embed(title="This is the hello world command!", description="Hello world!", color=self.COLOR)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    async def group(self : commands.slash_command, inter : disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    @group.sub_command()
    async def subcommand(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """This is this command description"""
        await inter.response.defer(ephemeral=True)
        # This command will be usable by doing /group subcommand
        #
        # Do stuff...
        #
        await inter.edit_original_message(embed=self.bot.embed(title="This is the sub command!", description="You called me using `/group subcommand`!", color=self.COLOR)
```  
  
* For command descriptions to be parsed properly by the `/help` command and the [Online Help](https://mizagbf.github.io/discordbot.html), make sure to put them under the command definition, as a single line docstring, between `"""`.  
* Commands whose Interaction are from the type `disnake.GuildCommandInteraction` will only be usable in guilds (i.e. Discord Servers).  
* Commands whose Interaction are from the type `disnake.ApplicationCommandInteraction` will be usable in guilds (i.e. Discord Servers) **and** Direct Messages. Be sure to check if `inter.guild is None` if you plan to do guild specific things within a command usable in DMs.  
* A sub command interaction type is determined by its parent or grandparent. If `subcommand` is a guild command but its parent `group` is usable in both guilds and DMs, then `/group subcommand` will work in both guilds and DMs.  
  
Once your Cog is ready, place it in the `cogs` folder.  
Run `python bot.py -t` to test if the bot boots and the Cog loads.  
If it doesn't, fix any error, else you're good to go!  
Errors might still pop-up later during runtime but nothing which will should cause an actual crash. Rosetta will report all errors to you.  
  
### Tasks  
  
Tasks are functions running in the background, periodically executing some code to achieve some purpose.  
It uses [asyncio.create_task](https://docs.python.org/3/library/asyncio-task.html#creating-tasks) under the hood, hence the name.  
Realistically, a Task can be located anywhere in the codebase but, for consistency, they are located in their respective Cogs or Components.  
  
Here's an example of how to write a Task:  
  
```python
    async def mytask(self : Example) -> None:
        while True:
            try:
                await self.bot.send('debug', "Hello world from the task!")
                await asyncio.sleep(300)
            except asyncio.CancelledError:
                self.bot.logger.push("[TASK] 'mytask' Task Cancelled")
                #
                # Do stuff related to cancellation here
                #
                return
            except Exception as e:
                self.bot.logger.pushError("[TASK] 'mytask' Task Error:", e)
                #
                # Do error handling here
                #
                return # you don't have to return if you want your task to keep running
```  
  
In this example, we add a simple Task to our `Example` Cog from above.  
It'll run forever (`while True:`), send a message to the Debug server channel saying `Hello world from the task!` and then sleep for 5 minutes before repeating.  
If it encounters an error or if it gets cancelled, the Task will stop.  
  
Now to have a Task runs automatically on the bot startup:  
* Check if the Cog or Component has a `startTasks` function and add it if it doesn't:  
  
```python
    def startTasks(self : Example) -> None:
        pass
```  
  
Then, call `runTask` with the given name of your choice and your Task function to start it:  
  
```python
    def startTasks(self : Example) -> None:
        self.bot.runTask('mytask!', self.mytask)
```  
  
If you wish to not execute the Task in Debug mode, use `isProduction()`:  
  
```python
    def startTasks(self : Example) -> None:
        if self.bot.isProduction():
            self.bot.runTask('mytask!', self.mytask)
```  
  
Finally, if, at some point, you want to cancel a Task, use `cancelTask` in whatever place you wish, with the name of your task:  
  
```python
        self.bot.cancelTask('mytask!')
```  
  
It will trigger the `asyncio.CancelledError` exception seen above and remove the Task from the bot Task list.  