# Rosetta  
* [Granblue Fantasy](https://game.granbluefantasy.jp) Discord Bot.  
* Command List and Help available [Here](https://mizagbf.github.io/discordbot.html).  
  
### Requirements  
* Python 3.11.
* See [requirements.txt](https://github.com/MizaGBF/Rosetta-Public/blob/master/requirements.txt) for a list of third-party modules.  
  
### General Informations  
* Rosetta is a Discord Bot themed around the game [Granblue Fantasy](https://game.granbluefantasy.jp), providing utility commands and advanced features to the users, along with moderation and more generalistic commands.  
* This project is a fork of [MizaBOT latest version](https://github.com/MizaGBF/MizaBOT) featuring massive improvements, bugfixes and so on.  
* Like MizaBOT, saving is still done on Google Drive. If you want to use something else, you'll have to rewrite the `drive.py` component.  
* System requirements are pretty low. The bot only uses around a hundred megabytes of memory (it will obviously increases with more servers). The single threaded performance of your CPU is what matters most.  
* Additional tools can be found in the `tools` folder:  
* `generate_help.py` generates the [help page](https://mizagbf.github.io/discordbot.html) html. **IT DOESN'T WRITE IN THE CURRENT DIRECTORY**, you might want to change where it writes before using it.  
* `save_gzip.py` and `save_lzma.py` can be used to decompress/compress a save file. Current save data are saved to the drive in the LZMA format. `save_gzip.py` is technically not used anymore.  
  
### Usage  
- **Method 1 (for Linux systems):**  
  
The main intended way is to run the [Dockerfile](https://github.com/MizaGBF/Rosetta-Public/blob/master/Dockerfile).  
Note that it will install [jemalloc](https://github.com/jemalloc/jemalloc) to use as Python malloc. This was the solution found to fix MizaBOT increasing Memory Usage due to memory fragmentation over long runs.  
  
- **Method 2:**  
  
Open a command prompt (Windows) or terminal (Linux) and run `pip install -r requirements.txt` in the bot folder, to install the third-party modules. You only need to do it once or if it gets updated.  
Then, you can run the bot with `python -O bot.py -run` to start the bot (`-O` is optional).  
  
There are three ways to start the bot:  
`-run`: Start the bot.  
`-test`: Start the bot but stop before connecting to Discord. Used to test if bot can start properly.  
`-remove`: Start the bot without loading any commands. Mainly used to desync and remove a test bot commands from a server.  
  
You can also add the following to change its behavior:  
`-debug`: Start the bot in debug mode. `config-test.json` will be loaded and will partially overwrite `config.json` in **memory**, so you can use a different Discord token. The bot won't write on the Google Drive in this state, nor load all the tasks.  
  
- **Stop Rosetta**  
  
A simple CTRL+C or sending a SIGTERM or SIGINT signal will make the bot saves and exits gracefully.  
The bot returns the following codes upong exiting:  
- 0: Exited properly.  
- 1: Failed to load `config.json` on boot. Check if the file is missing or corrupted.  
- 2: Failed to load `save.json` on boot. Check if the file is corrupted.  
- 3: Failed to load the save data from Google Drive. Maybe Google is having troubles or the save file is missing from the folder.  
- 4: Failed to connect to Google Drive with your Service account.  
- 5: Failed to initialize the bot components.  
- 6: Bot instance initialization failure.  
  
As a side note, the `/owner bot reboot` command doesn't actually reboot the bot, it's a simple shutdown with the code **0**.  
My instance is setup with Watchtower and automatically reboot once stopped, hence why it's called reboot.  
  
### Setup  
  
The bot is configured with a file called `config.json`. Create one in its folder and paste the following:  
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
        "owner" : YOUR_USER_ID_ID,
        "you_server" : YOUR_CREW_OR_THE_BOT_SERVER_ID,
        "you_announcement" : YOUR_CREW_ANNOUNCEMENT_CHANNEl_ID,
        "you_meat" : YOUR_CREW_MEAT_CHANNEl_ID,
        "you_member" : YOUR_CREW_MEMBER_ROLE_ID,
        "atkace" : YOUR_CREW_ATK_ACE_ROLE_ID,
        "deface" : YOUR_CREW_DEF_ACE_ROLE_ID,
        "fo" : YOUR_CREW_FIRST_OFFICER_ROLE_ID,
        "gl" : YOUR_CREW_LEADER_ROLE_ID,
        "wawi" : 163566477138591744,
        "gbfg" : 339155308767215618,
        "gbfg_new" : 402973729942142988,
        "chen" : 271896927463800835
    },
    "games" : [
        "Granblue Fantasy",
        "Granblue Fantasy: Versus Rising",
        "Granblue Fantasy: Relink"
    ],
    "emotes" : {
        "fire" : 614733962736042005,
        "water" : 614733963399004170,
        "earth" : 614733962937630752,
        "wind" : 614733962991894529,
        "dark" : 614733962937499648,
        "light" : 614733963054809098,
        "R" : 614733962807607316,
        "SR" : 614733962543366155,
        "SSR" : 614733962832773120,
        "sword" : 614733962744561675,
        "dagger" : 614733962899750912,
        "spear" : 614733963105140736,
        "axe" : 614733963076042762,
        "staff" : 614733962979442688,
        "gun" : 614733963105271809,
        "melee" : 614733963008933888,
        "bow" : 614733962924916751,
        "harp" : 614733962669064205,
        "katana" : 614733962790567938,
        "skill1" : 614733961717088257,
        "skill2" : 614733962681647124,
        "atk" : 614733962719395850,
        "hp" : 614733962966728714,
        "summon" : 614733962555686984,
        "kmr" : 614735088391028737,
        "gw" : 614733962996350977,
        "st" : 614733962937630764,
        "time" : 614733963222843392,
        "1" : 614733962178330665,
        "2" : 614733962643767322,
        "3" : 614733962698555392,
        "4" : 614733962711138314,
        "5" : 614733962476257292,
        "6" : 614733962601824257,
        "red" : 614733963017060363,
        "gold" : 614733962983768094,
        "wood" : 614733963092688896,
        "loot" : 614733962622926849,
        "mark" : 614733962698555415,
        "mark_a" : 614736075272880139,
        "clock" : 614733962652155906,
        "question" : 614733963004477445,
        "cog" : 614736426516480009,
        "ensign" : 700731360012271616,
        "captain" : 700732615879032842,
        "atkace" : 614733963071586344,
        "deface" : 614733963029643264,
        "foace" : 614733962870259713,
        "crystal" : 614733963067392015,
        "crown" : 614733963046551561,
        "misc" : 653259257998999584,
        "singledraw" : 734795587207299094,
        "tendraw" : 734795587630661752,
        "crystal0" : 756821583636725780,
        "crystal0+" : 756821618139070575,
        "crystal1" : 756822019491758160,
        "crystal2": 756821671230439424,
        "crew": 766297948467494924,
        "lyria" : 920696070764376084,
        "shrimp": 959392828847448124,
        "star0": 1050429257995792424,
        "star1": 1050429259593830400,
        "star2": 1050429261435117598,
        "star3": 1050429263217692714,
        "star4": 1056646303527997450,
        "arcarum": 1052232990727622706
    },
    "granblue": {
        "gbfgcrew" : {"aion no me":"645927", "aion":"645927", "bellabarca":"977866", "bullies":"745085", "bullied":"1317803", "chococat":"940560", "chococats":"940560", "cogfriends":"1049216", "cog":"1049216", "cowfag":"841064", "cowfags":"841064", "\u4e2d\u51fa\u3057\u306e\u5e78\u305b":"1036007", "cumshot":"1036007", "cumshot happiness":"1036007", "dem bois":"705648", "ded bois":"705648", "dembois":"705648", "demboi":"705648", "dedbois":"705648", "fleet":"599992", "haruna":"472465", "cug":"1161924", "lilypals":"1161924", "lilypal":"1161924", "\u5c0f\u3055\u306a\u5973\u306e\u5b50":"432330", "little girls":"432330", "lg":"432330", "little girl":"432330", "sixters":"1380234", "sixter":"1380234", "soy":"1601132", "onion":"1601132", "onions":"1601132", "oppaisuki":"678459", "oppai":"678459", "pcs":"632242", "quatrebois":"1141898", "quatreboi":"1141898", "the bathtub":"1580990", "thebathtub":"1580990", "bathtub":"1580990", "(you)":"581111", "you":"581111", "(you) too":"1010961", "(you)too":"1010961", "u2":"1010961", "youtoo":"1010961", "you too":"1010961", "a-team":"1744673", "ateam":"1744673", "a":"1744673", "grape":"1807204", "grapes":"1807204", "toot":"844716", "nier":"1837508", "nier2":"1880420"},
        "othercrew" : {"ssf":"677159", "hsp":"147448", "kingdom":"1377462", "atelier":"418206", "lum1":"388489", "lum2":"401211", "beafriends":"940700", "waifuanon":"588156", "lolibabas":"1593480", "lolibaba":"1593480", "hagchads":"1593480", "hagchad":"1593480", "mesugaki":"1593480", "lazytown":"1586134", "mavericks":"1629318", "maverick":"1629318"}
    }
}
```  
Go to the [Discord Developer Portal](https://discord.com/developers/docs/game-sdk/applications) > *Applications* > *New Application* and create your application.  
Go to *Bot* on the left and click **Reset Token**. Your Bot Token will appear, copy it and replace DISCORD_TOKEN with it in `config.json` (don't forget to put it between quotes **"**, it's a string).  
Next, turn on the **Message Content Intent**, below.  
  
Now to configure your Google account.  
**The [Google API website](https://console.cloud.google.com/apis/dashboard) is a pain in the butt to use, so I'll only give general steps.**  
- Find a way to create an application.  
- Go to *Credentials* on the left, create a new **Service account**.  
- Copy the email associated with this service account (it should be something like `XXX@YYYY.iam.gserviceaccount.com` ).  
- You might need to give it some permissions (*Permissions* tab, *Grant Access*, use the application email.).  
- Add a new key (*Key* tab), pick the *JSON* format and accept. Rename this file to `service-secrets.json` and put it in the bot folder, alongside `config.json`.  
  
Go to your Google Drive and create two folders, one for the bot save data and one for GW related files.  
Open the save data one and copy the url. It should be something like `https://drive.google.com/drive/folders/AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA`. Copy the `AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA` part and replace SAVE_FOLDER_ID in `config.json` (don't forget to put it between quotes **"**, it's a string).  
Do the same thing for the other folder and FILE_FOLDER_ID.  
The third folder ID is unused but you are free to create one and set the key in `config.json` too.  
  
Then, **for each of those folders**, right click on them and select *Share*. Add your service account (again, using the email you copied) to each of them.  

Next, create a Discord Server for your bot.  
On the [Discord Developer Portal](https://discord.com/developers/docs/game-sdk/applications), copy the *Application ID* (under *General Information).  
In the following: `https://discord.com/api/oauth2/authorize?client_id=XXXXXXXXXXXXXXXX&permissions=1644905889015&scope=bot%20applications.commands`, replace `XXXXXXXXXXXXXXXX` by this ID. This will be your bot invite link.  
Use it now and invite your bot to the server (no need to start the bot). If you did it right, it should show up in the member list.
  
The bot requires three text channels to be created:
- One to output debug infos.  
- One to upload images.  
- One to post updates.  
  
Create them.  
If you haven't yet, go to your Discord account settings, *Advanced* and turn on *Developer Mode*. Now you can right click on anything to copy their IDs.  
  
Right click on the debug channel, copy the ID and replace BOT_DEBUG_CHANNEL_ID in `config.json`.  
Same for the second and BOT_IMAGE_UPLOAD_CHANNEL_ID.  
Same for the third and BOT_SERVER_UPDATE_CHANNEL_ID.  
  
Right click on the Server itself (in your server list), same thing and replace BOT_SERVER_ID.  
Next, post a message, right click on your avatar and copy your own ID to replace YOUR_USER_ID_ID.  
  
Do the same thing to fill the remaining IDs.  
The four last IDs are related to the /gbfg/ server and are already set.  
  
The final step is to upload the various emotes in `assets/emojis` to your server.  
Once done, you'll need to retrieve their IDs one by one to set them in `config.json`.  
A way is to add a slash before the emote. Example, type `\:whatever_your_emote_is:` and it will show `<:whatever_your_emote_is:0000000000000>` where `0000000000000` is the emote ID.  
  
If you did everything properly, you're set. See below for additional informations.  
  
### Other config.json keys
`games`: The list of game which will appear in the bot status. Feel free to modify it. At least one game is required.  
  
`granblue`: The bot has been historically used by the **/gbfg/ Discord Server** and its crews are set here as shortcut for certain commands.  
You are free to remove it if you want but don't leave it empty.  
  
All the remaining setup is done via the `/owner` commands.  
  
### Debug Mode  
**(Skip this if you don't plan to use it)**  
Using the `-debug` argument requires to set up `config-test.json`.  
Same principle:  
```json
{
    "tokens" : {
        "discord" : "DISCORD_TOKEN",
        "drive" : "SAVE_FOLDER_ID",
        "upload" : "",
        "files" : "FILE_FOLDER_ID"
    },
    "debug" : null
}
```  
For DISCORD_TOKEN, simply create a second application and bot and put its token here.  
For the folders, either reuse the existing ones or make new ones if you want to use separate data.  
Do note the bot is unable to write to your Google Drive in this mode.  
  
### First Boot
  
If Rosetta is starting properly, you should get a **Rosetta is Ready** message in the channel that you set as your debug one.  
The logs should also look similar to this:  
  
```
INFO:Rosetta:2024-02-18 17:43:39 | [BOOT] Loading the config file...
INFO:Rosetta:2024-02-18 17:43:39 | [BOOT] Downloading the save file...
INFO:Rosetta:2024-02-18 17:43:40 | [BOOT] Reading the save file...
WARNING:disnake.client:PyNaCl is not installed, voice will NOT be supported
INFO:Rosetta:2024-02-18 17:43:40 | [BOOT] Initialization complete
INFO:Rosetta:2024-02-18 17:43:40 | [MAIN] Loading cogs...
INFO:Rosetta:2024-02-18 17:43:41 | [MAIN] All cogs loaded
INFO:Rosetta:2024-02-18 17:43:41 | [MAIN] v11.1.5 starting up...
INFO:Rosetta:2024-02-18 17:43:47 | [MAIN] Rosetta is ready
```  
  
If it doesn't, be sure to check for error messages, etc...  
  
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
* `/owner account`: Commands to set a GBF account on the bot. I won't provide any help with this.  
* `/owner db`: Commands to manually set a Dread Barrage event.  
* `/owner gw`: Commands to manually set and edit an Unite and Fight event.  
* `/owner buff`: Commands to debug the GW buff data used by my crew. I haven't used it in a long while.  
* `/owner gacha`: Commands to clear the gacha banner and change the `/roll roulette` command settings.  
  
I rarely use most of those commands, there is a small chance it might be hiding some bugs.  
  
Additionally, if you want a GW.sql file for the ranking commands, you can go grab the most recent one [here](https://drive.google.com/drive/folders/11DcUKeO6Szd5ZEJN9q57MQl772v64_R2), rename it to `GW.sql` and put it in the "files" drive folder.  