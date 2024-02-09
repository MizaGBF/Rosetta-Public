import os
import re

func_index = {}

def get_version(): # retrieve the bot version from bot.py
    with open("../bot.py", "r", encoding="utf-8") as f:
        data = f.read()
    return search_interval(data, 0, len(data)-1, 'self.version = "', '"')

def make_parameters(params): # parse the raw parameter list (the list of string) and convert into html
    msg = ""
    # possible parameter formats
    # var_name
    # var_name : var_type
    # var_name : var_type = default_value
    # var_name : var_type = commands.Param(...)
    for p in params:
        pname = None
        ptype = None
        pextra = None
        cmsg = ""
        sp = p.split(':')
        if len(sp) <= 1: # var_name
            pname = sp[0].replace(' ', '')
            sp = p.split('=')
            if len(sp) >= 2:
                pextra = '='.join(sp[1:])
        else: # var_name : var_type and others...
            pname = sp[0].replace(' ', '')
            sp = ':'.join(sp[1:]).split('=')
            if len(sp) == 1:
                ptype = sp[0].replace(' ', '')
            else:
                ptype = sp[0].replace(' ', '')
                pextra = '='.join(sp[1:])
        cmsg += pname
        if ptype is not None: # converting types into more readable stuff for normal people
            cmsg += " ({})".format(ptype.replace('int', 'Integer').replace('str', 'String').replace('disnake.', ''))
        if pextra is not None: # parsing commands.Param(...)
            pos = pextra.find("description")
            if pos != -1:
                a = pextra.find('"', pos)
                b = pextra.find("'", pos)
                if a != -1 and (b == -1 or (b != -1 and a < b)):
                    pos = a + 1
                    a = pextra.find('"', pos)
                else:
                    pos = b + 1
                    a = pextra.find("'", pos)
                cmsg += "&nbsp;:&nbsp;{}".format(pextra[pos:a])

            pos = pextra.find("default")
            if pos != -1:
                cmsg = "<b>(Optional)</b>&nbsp;" + cmsg
        msg += cmsg + "<br>"
    if msg != "":
        msg = msg[:-4]
    return msg

def generate_html(command_list): # main function to generate the html
    # various "blocks" of the page
    ver = get_version()
    metadata = '<!DOCTYPE html>\n<!--This page is automatically generated, please excuse the poor formatting-->\n<html lang="en">\n<head>\n\t<title>Rosetta Online Help v{}</title>\n\t<meta charset="utf-8">\n\t<meta name="title" content="Rosetta Online Help v{}">\n\t<meta name="description" content="Online Help and Command List for the Granblue Fantasy Discord bot Rosetta.">\n\t<meta name="theme-color" content="#5217b0">\n\t<meta property="og:type" content="website">\n\t<meta property="og:url" content="https://mizagbf.github.io/">\n\t<meta property="og:title" content="Rosetta Online Help v{}">\n\t<meta property="og:description" content="Online Help and Command List for the Granblue Fantasy Discord bot Rosetta.">\n\t<meta property="twitter:card" content="summary_large_image">\n\t<meta property="twitter:url" content="https://mizagbf.github.io/">\n\t<meta property="twitter:title" content="Rosetta Online Help v{}">\n\t<meta property="twitter:description" content="Online Help and Command List for the Granblue Fantasy Discord bot Rosetta.">\n\t<link rel="icon" type="image/png" href="assets/boticon.png">\n'.format(ver, ver, ver, ver)
    header = '\t<h1 style="width:630px;margin-left: auto; margin-right: auto;">\n\t\t<img src="assets/boticon.png" alt="icon" style="vertical-align:middle;border-radius: 50%;box-shadow: 0 0 0 2pt #981cd6;width: 120px; height: 120px">&nbsp;Rosetta Online Help<br>&nbsp;<small>v{}</small>\n\t</h1>\n'.format(ver)
    tabs = '''\t<div class="tab">\n\t\t<button class="tablinks" id="tab-commands" onclick="openTab(event, 'Commands')">Commands</button>\n\t\t<button class="tablinks" id="tab-guides" onclick="openTab(event, 'Guides')">Guides</button>\n\t\t<button class="tablinks" id="tab-faq" onclick="openTab(event, 'FAQ')">FAQ</button>\n\t\t<button class="tablinks" id="tab-privacy" onclick="openTab(event, 'Privacy')">Privacy</button>\n\t\t<button class="tablinks" id="tab-tos" onclick="openTab(event, 'tos')">Terms of Service</button>\n\t</div>\n'''
    filters = '\t\t<div id="buttons">\n\t\t\t<button class="btn active" onclick="filterSelection(\'all\')" style="background: #050505;">All</button>\n'
    containers = '\t\t<ul id="commandList">\n'
    # used for command type blocks
    cmd_color_type = ['7e9ccc', '77bf85', 'cc83b1', '7e9ccc']
    cmd_type = ['Slash Command', 'User Command', 'Message Command', 'Slash Command']
    # for debugging
    slash_count = 0
    user_count = 0
    msg_count = 0
    prev_count = 0
    total_count = 0
    sub_count = {}
    cmd_cache = set()
    # loop over the cogs
    for cog in command_list:
        commands = command_list[cog]
        if len(commands) == 0: continue
        # add a block
        filters += '\t\t\t<button class="btn" onclick="filterSelection(\'{}\')" style="background: #{};">{}</button>\n'.format(cog.lower(), commands[0].get('color', '615d5d'), cog)
        # loop over those commands
        for c in commands:
            if c['type'] == 0: slash_count += 1
            elif c['type'] == 1: user_count += 1
            elif c['type'] == 2: msg_count += 1
            if c['comment'] == "Command Group": continue
            total_count += 1
            cn = "" # command name
            if c['type'] == 0:
                cn = "/" # slash command, we add / before
            elif c['type'] == 3:
                cn = "/{} ".format(func_index.get(cog + "_" + c['parent'], c['parent'])) # sub command, we add / and parent(s) before
                sn = func_index.get(cog + "_" + c['parent'], c['parent']).split(' ')
                if len(sn) > 1:
                    sub_count[sn[0]] = sub_count.get(sn[0], 0) + 1
                    sub_count[sn[0] + ' ' + sn[1]] = sub_count.get(sn[0] + ' ' + sn[1], 0) + 1
                else:
                    sub_count[sn[0]] = sub_count.get(sn[0], 0) + 1
            cn += c['name']
            if cn in cmd_cache:
                print("Warning: Command", cn, "is present twice or more")
            else:
                cmd_cache.add(cn)
            # command container
            containers += '\t\t\t<li class="command {}" onclick="copyCommand(\'{}\')">\n\t\t\t\t<div class="command-name"><span style="display: inline-block;background: #{};padding: 5px;text-shadow: 2px 2px 2px rgba(0,0,0,0.75);">{}</span>&nbsp;<span style="display: inline-block;background: #{};padding: 3px;text-shadow: 2px 2px 2px rgba(0,0,0,0.5); font-size: 14px;">{}</span>&nbsp;&nbsp;{}'.format(cog.lower(), cn, c.get('color', '615d5d'), cog, cmd_color_type[c['type']], cmd_type[c['type']], cn)
            if c.get('comment', '') != '': # add description
                containers += '</div>\n\t\t\t\t<div class="command-description"><b>Description :</b>&nbsp;{}'.format(c['comment'].replace('(Mod Only)', '<b>(Mod Only)</b>').replace('((You) Mod Only)', '<b>((You) Mod Only)</b>').replace('(NSFW channels Only)', '<b>(NSFW channels Only)</b>'))
                if len(c['comment']) >= 100:
                    print("Warning: Command", c['name'], "description is too long")
            else:
                print("Warning:", c['name'], "has no description")
            if c['type'] == 0 or c['type'] == 3: # add command type
                out = make_parameters(c['args'])
                if out != '':
                    containers += '</div>\n\t\t\t\t<div class="command-use"><b>Parameters :</b><br>{}'.format(out)
            containers += '\n\t\t\t\t</div>\n\t\t\t</li>\n'
        print(slash_count - prev_count, "slash commands in:", cog, "(", slash_count, "commands)")
        prev_count = slash_count
    print("Total:")
    print(slash_count, "/ 50 slash commands (for", total_count, "commands)")
    if slash_count > 50: print("WARNING, the number of slash commands is too high")
    print(user_count, "/ 5 user commands")
    if user_count > 5: print("WARNING, the number of user commands is too high")
    print(msg_count, "/ 5 message commands")
    if msg_count > 5: print("WARNING, the number of message commands is too high")
    for x in sub_count:
        if sub_count[x] > 25:
            print("WARNING,", x, "sub command count is too high (", sub_count[x],")")
    filters += '\t\t</div>\n\t\t<br>\n\t\t<div class="command-count"><b>{} commands</b></div>\n\t\t<br>\n\t\t<input type="text" id="textSelection" onkeyup="searchSelection()" placeholder="Search a command">\n'.format(total_count+user_count+msg_count)
    containers += '\t\t</ul>\n'
    commandList = '\t<div id="Commands" class="tabcontent">\n' + filters + containers + '\t</div>\n'
    other_tabs = '''
	<div id="Guides" class="tabcontent">
		<h1>Guides</h1>
		<h2>Good practices and recommendations</h2>
		<p>1) Make a channel dedicated to the bot and use the command <b>/mod cleanup toggle</b>.<br>
		<br>
		2) Remove the <b>"send message"</b> permission in the channel where you don't want it to be usable. (<b>Note:</b> Commands will still appear in said channel unless disabled in your Server Integration Permissions.)<br>
		<br>
		3) (Optional) In your Server Settings, under "Integration", you can tune which and how a command is usable (See below for more informations).<br>
		<br>
		4) Make sure the bot has the <b>"use external emoji"</b> permission enabled.<br>
		<br>
		You can use <b>/mod server info</b> or the Message Command <b>Server Info</b> to verify quickly if something is enabled or disabled.<br>
		Keep in mind <b>anyone with the "manage message" permission is considered a moderator by the bot</b>. You can restrict those commands via the Server Integration Permissions if needed.</p>
		
		<h2>Notifications</h2>
		<p>Select a channel where you want the bot to post notifications and use <b>/mod announcement toggle_channel</b>.<br>
		You can see your settings with <b>/mod announcement see</b>.<br>
		Do note, if the channel is an Announcement Channel and you enabled the Auto Publish setting, it will auto publish posts, up to the <b>hourly 10 posts publish limit</b>,.<br>
		</p>
		
		<h2>Pinboard</h2>
		<p>You can setup a pinboard channel. Here are some steps to guide you:<br>
		1) First, make or select the text channel where the pinned messages will appear. Make sure the bot has access to it and do <b>/mod pinboard output_here</b>.<br>
		2) Use <b>/mod pinboard track</b> in all the channels you want the bot to track. Make sure the bot can access those channels. Forum Posts are also supported.<br>
		3) Use <b>/mod pinboard settings</b> to see your settings or change them. Emoji lets you change the emoji used to trigger the pin, Threshold lets you change how many emojis are required, Mod Bypass lets Moderators bypass the threshold.<br>
		<br>
		A pin will occur when people react, with the select emoji, to messages in the tracked channels. The required number of reaction is the threshold you set. If the Mod Bypass is enabled, a mod reacting will instantly trigger the pin.
		Do <b>/help search:pinboard</b> to see all the related commands if you need more help.<br>
		</p>
		
		<h2>Server Integration Permissions</h2>
		<p>Like mentionned at the start, you can disable or restrict certain command groups to specific channels or roles, in your Server Settings, under "Integration".<br>
		If you are a server administrator, all commands will keep working for you regardless of the settings.<br>
		If you want to test your settings, go under "Roles", pick a suitable one and use the "View Server as Role" feature.<br>
		</p>
		
		<h2>Context Menu</h2>
		<p>Right clicking on an user or message lets you access the following Context Menus.<br>
			<img src="assets/discordbot_help_1.png" alt="help 1"><br>
		Such commands are called, in the command list, <span class="command-name" style="display: inline-block;background: #cc83b1;padding: 3px;text-shadow: 2px 2px 2px rgba(0,0,0,0.75); font-size: 14px;">Message Command</span> for message ones, <span class="command-name" style="display: inline-block;background: #77bf85;padding: 3px;text-shadow: 2px 2px 2px rgba(0,0,0,0.75); font-size: 14px;">User Command</span> for user ones.<br>
		</p>
	</div>
	<div id="FAQ" class="tabcontent">
		<h1>Frequently Asked Questions / Troubleshooting</h1>
		<h2>What is Rosetta?</h2>
		<p>Rosetta is a <a href="https://game.granbluefantasy.jp">Granblue Fantasty</a> themed <a href="https://discord.com/">Discord</a> Bot.<br>
		It's a fork of MizaBOT (which was available on <a href="https://github.com/MizaGBF/MizaBOT">GitHub</a>).<br>
		Code source is available <a href="https://github.com/MizaGBF/Rosetta-Public">here</a>.<br>
		It provides various commands, ranging from utilty to recreative ones, related (or not) to the game.<br>
		<b>This page is meant to be a private help page for people with access to this Discord Bot.<br>
		The bot itself isn't open to invitations.</b><br></p>
		
		<h2>Does the bot collect my messages/data?</h2>
		<p>See the <b>Privacy</b> tab.</p>
		
		<h2>Can you explain the various command types?</h2>
		<p>Slash Commands are used by simply typing / in chat.<br>
		User Commands are used by right clicking on an user and going into the Apps context menu.<br>
		Message Commands are used by right clicking a message and going into the Apps context menu.</p>
		
		<h2>How do I report a bug?</h2>
		<p>Errors are usually automatically reported but, if you found an odd behavior or what seems like an error, you can use the <b>/bug_report</b> command or open an issue on <a href="https://github.com/MizaGBF/Rosetta-Public">Github</a>.</p>
		
		<h2>Emotes used by the bot don't work</h2>
		<p>Make sure the bot has the <b>Use External Emojis</b> permission enabled.<br>
		If you thinkered with the invite link or the bot role permissions (which I don't recommend to), you can use the invitation link again to restore them to default (without needing to kick the bot).<br>
		If the problem persists, make sure you didn't give a role, with this permission disabled, to the bot.<br>
		This paragraph is true for other permissions that the bot might need.</p>
		
		<h2>How do I remove my GBF Profile ID?</h2>
		<p>Your linked GBF ID can be removed with the <b>/gbf profile unset</b> command.
		It's also deleted if you leave all servers where the bot is present.</p>
		
		<h2>How do I remove my set Rolls?</h2>
		<p>Your spark data is deleted after 30 days without an update, just leave it alone.</p>
		
		<h2>One or multiple commands don't work</h2>
		<p>If no commands appear when typing /, you might have to wait (it can take up to one hour to register them).<br>
		<br>
		If you get an "Interaction failed" error, either you tried to use a command without the proper permission (example, a mod command without being mod), you or the bot doesn't have the permission to run this command in this channel, OR the bot is down or rebooting.</p>
		
		<h2>My command froze/hanged</h2>
		<p>The bot most likely rebooted or crashed during this timeframe, bad luck for you.</p>
		
		<h2>The command didn't register what I set</h2>
		<p>Again, the bot most likely rebooted and it didn't save in properly. Just wait and do it again.</p>
		
		<h2>When are the Unite and Fight rankings updated?</h2>
		<p>They are updated in-game every 20 minutes.<br>
        To ensure they are properly updated, the bot waits minute 3, 23 or 43 to start fetching the data.<br>
        Commands such as <b>/gw ranking</b> will be updated almost immediatly.<br>
        For other commands such as <b>/gw find crew</b> or <b>/gbfg ranking</b>, it will take around 7 more minutes.<br>
        Do note the bot doesn't update everything in some periods (during breaks or crews during interlude for example).</p>
	</div>
	<div id="Privacy" class="tabcontent">
		<h2>Privacy Policy</h2>
		<p>This tab describes the privacy policy of Rosetta.<br>
		We do not store any personally identifiable data nor do we share any data to a third party.<br>
		When the bot leaves a server, data related to this server is deleted in the next monthly cleanup.<br>
		The following points describe in details what kind of data is accessed or saved by the bot.</p>
		
		<h2>Data Collected Automatically</h2>
		<p>When reacting to a message, this message is processed by the bot, for the purpose of the Pinboard feature. The message itself isn't saved or stored for further use, nor used for any other purpose, and no data is collected from the message itself.</p>
		<p>Same thing applies if you use the <b>vxtwitter</b> feature to convert your twitter links: Message ares read and processed upon received by the bot but nothing is saved or stored for further use.</p>
		
		<h2>Data Collected by Commands</h2>
		<p>The following data is stored: <br>
		</p>
		<ul>
			<li>An user's <a href="https://game.granbluefantasy.jp/">Granblue Fantasy</a> profile ID, associated with its Discord User ID, set by using the command <b>/gbf profile set</b>. The data can be deleted by the user, using <b>/gbf profile unset</b> or by leaving all the servers where the bot is present (This automatic deletion occurs on the third day of each month).</li>
			<li>An user's reminders, set by using the command <b>/remind add</b>. Data can be removed using <b>/remind remove</b> or once the reminders have been triggered.</li>
			<li>An user's current roll count for <a href="https://game.granbluefantasy.jp/">Granblue Fantasy</a>, set by using the <b>/spark</b> command group. This data is deleted after 30 days without any update.</li>
			<li>A server self-assignable roles, registered using the <b>/role</b> command group. The data is deleted if the bot leaves the server.</li>
			<li>A server channel ID used to receive broadcasts/announcements/news from the bot, registered using the <b>/mod announcement togglechannel</b> command. The data is deleted if the bot leaves the server.</li>
			<li>Server settings for the bot auto cleanup feature, using the <b>/mod cleanup</b> command group. The data is deleted if the bot leaves the server.</li>
			<li>Server settings for the bot pinboard feature, using the <b>/mod pinboard</b> command group. The data is deleted if the bot leaves the server.</li>
		</ul>
		
		<h2>Others</h2>
		<p>Your user ID is issued to the developper upon sending a bug report, to contact you back if needed or link the report to a previous error message.<br>
		User and/or server IDs are also issued, along with the command used, when a critical error occurs, for debugging purpose.
		</p>
	</div>

	<div id="tos" class="tabcontent">
		<p>We reserve the right to remove you the possiblity to use this instance of Rosetta if you abuse it (purposely making it crash, for example) or to use it to break <a href="https://discord.com/terms">Discord Terms of Service</a>.<br>
		This software is licensed under the <a href="https://github.com/MizaGBF/Rosetta-Public/blob/main/license">MIT License</a>.<br>
		For anything else, please refer to Discord Terms of Service.</p>
	</div>
'''

    css = """
<style>
html, body {
  background: #040c1c;
  font-family: sans-serif;
  font-size: 16px;
}

h1 {
  text-align: center;
  color: white;
}

h2 {
  color: white;
}

p {
  color: white;
}

ul {
  color: white;
}

a {
  color: #981cd6;
}

a:visited {
  color: #ca1cd6;
}

#textSelection {
  background-image: url('assets/searchicon.png');
  background-position: 10px 12px;
  background-repeat: no-repeat;
  width: 100%;
  font-size: 16px;
  padding: 12px 20px 12px 40px;
  border: 1px solid #ddd;
  margin-bottom: 12px;
}

#commandList {
  list-style-type: none;
  padding: 0;
  margin: 0;
}

.command-count {
  color: white;
}

.command {
  float: left;
  background-color: #101010;
  color: #ffffff;
  width: 100%;
  margin: 2px;
  opacity: 1;
  transition: opacity 0.2s linear;
  display: none; /* Hidden by default */
}

.command:hover {
  background-color: #981cd6;
}

.command-name {
  padding: 10px;
  background: rgba(0, 0, 0, 0.7);
  font-size: 18px;
  font-weight: 700;
}
.command-use {
  padding: 10px;
  background: rgba(0, 0, 0, 0.3);
}
.command-description {
  padding: 10px;
  background: rgba(0, 0, 0, 0.6);
}

.show {
  display: block;
}

.btn {
  border: none;
  outline: none;
  padding: 12px 16px;
  cursor: pointer;
  color: white;
  text-shadow: 2px 2px 2px rgba(0,0,0,0.5);
  margin: 2px;
  font-size: 20px;
}

.btn:hover {
  outline: solid #ca1cd6;
}

.btn.active {
  outline: solid #981cd6;
}

.tab {
  overflow: hidden;
}

.tablinks {
  border: none;
  outline: none;
  padding: 12px 16px;
  cursor: pointer;
  background: #4f4f4f;
  color: white;
  text-shadow: 2px 2px 2px rgba(0,0,0,0.5);
  margin: 2px;
  border-radius: 10%;
  font-size: 25px;
}

.tablinks:hover {
  background-color: #6f6f6f;
}

.tablinks.active {
  background-color: #463254;
}

.tabcontent {
  display: none;
  padding: 6px 12px;
}

.popup {
    border-radius: 25px;
    border: 2px solid #73ff21;
    padding: 20px;
    background-color: #113300;
    position:fixed;
    top:5%;
    left:5%;
    z-index:100;
    text-align: center;
    font-size: 25px;
    width: 12em;
    color: #ffffff;
    align-items: center;
}

</style>"""
    js = """<script>
var lastFilter = "all";
var intervals = [];
function init() {
    try {
        document.getElementById('tab-' + location.hash.substr(1).toLowerCase()).click();
    }catch (e) {}
    let btns = document.getElementsByClassName("btn");
    for (let i = 0; i < btns.length; i++) {
      btns[i].addEventListener("click", function() {
        let current = document.getElementsByClassName("btn active");
        current[0].className = current[0].className.replace(" active", "");
        this.className += " active";
      });
    }
    filterSelection("all");
}

function copyCommand(cmd_string) {
    navigator.clipboard.writeText(cmd_string);
    let div = document.createElement('div');
    div.className = 'popup';
    div.textContent = cmd_string + ' has been copied'
    document.body.appendChild(div)
    intervals.push(setInterval(rmPopup, 2500, div));
}

function rmPopup(popup) {
    popup.parentNode.removeChild(popup);
    clearInterval(intervals[0]);
    intervals.shift();
}

function searchSelection(update=true) {
  let input, filter, ul, li, a, i, txtValue;
  input = document.getElementById('textSelection');
  filter = input.value.toUpperCase();
  ul = document.getElementById("commandList");
  li = ul.getElementsByTagName('li');

  for (i = 0; i < li.length; i++) {
    txtValue = li[i].textContent || li[i].innerText;
    if (txtValue.toUpperCase().indexOf(filter) > -1) {
      if(update)
        addClass(li[i], "show");
    } else {
      rmClass(li[i], "show");
    }
  }
  if(update) filterSelection(lastFilter);
}
function filterSelection(c) {
  let x, i;
  x = document.getElementsByClassName("command");
  if (c == "all") c = "";
  for (i = 0; i < x.length; i++) {
    rmClass(x[i], "show");
    if (x[i].className.indexOf(c) > -1) addClass(x[i], "show");
  }
  lastFilter=c;
  searchSelection(false);
}

function addClass(element, name) {
  let i, arr1, arr2;
  arr1 = element.className.split(" ");
  arr2 = name.split(" ");
  for (i = 0; i < arr2.length; i++) {
    if (arr1.indexOf(arr2[i]) == -1) {
      element.className += " " + arr2[i];
    }
  }
}

function rmClass(element, name) {
  let i, arr1, arr2;
  arr1 = element.className.split(" ");
  arr2 = name.split(" ");
  for (i = 0; i < arr2.length; i++) {
    while (arr1.indexOf(arr2[i]) > -1) {
      arr1.splice(arr1.indexOf(arr2[i]), 1);
    }
  }
  element.className = arr1.join(" ");
}

function openTab(evt, tabName) {
  let i, tabcontent, tablinks;

  window.location.hash = '#' + tabName.toLowerCase();
  tabcontent = document.getElementsByClassName("tabcontent");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
  }

  tablinks = document.getElementsByClassName("tablinks");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }

  document.getElementById(tabName).style.display = "block";
  evt.currentTarget.className += " active";
}
</script>"""
    # write the result to my github page folder
    print("Writing discordbot.html...")
    try:
        with open("../../MizaGBF.github.io/discordbot.html", "w", encoding="utf-8") as f:
            f.write(metadata + css + js + '</head>\n<body onload="init()">\n' + header + tabs + commandList + other_tabs + '\n</body>\n</html>')
    except:
        print("An error occured, discordbot.html generated in the same folder")
        with open("discordbot.html", "w", encoding="utf-8") as f:
            f.write(metadata + css + js + '</head>\n<body onload="init()">\n' + header + tabs + commandList + other_tabs + '\n</body>\n</html>')
    print("Done")

def breakdown_parameters(raw_args): # breakdown the command definitions and retrieve the parameters
    args = []
    lvl = 0
    buf = ""
    for c in raw_args:
        if c == '(': lvl += 1
        elif c == ')': lvl -= 1
        if lvl == 0 and c == ',' :
            args.append(buf)
            buf = ""
        else:
            buf += c
    if buf != "": args.append(buf)
    return args # result is a list of string, each string being the full parameter declaration

def search_interval(data, pos, max_pos, start, end): # search a string between specific positions and strings
    s = data.find(start, pos, max_pos)
    if s == -1: return None
    e = data.find(end, s+len(start), max_pos)
    if e == -1: return None
    return data[s+len(start):e]

def retrieve_command_list(cog, data, pos_list): # use the position list to retrieve the command datas
    cl = []
    i = data.find(' COLOR = 0x') # retrieve the cog color
    if i != -1:
        color = data[i+len(' COLOR = 0x'):i+len(' COLOR = 0x')+6]
    else:
        color = None
    # iterate over the cog file
    for i in range(len(pos_list)):
        pos = pos_list[i][0]
        if i == len(pos_list) - 1: # if it's the last command in the list
            fp = data.find('async def ', pos)
            max_pos = len(data) - 1 # search range end
        else: # if not
            fp = data.find('async def ', pos, pos_list[i+1][0]) # we search between current position and next one
            max_pos = pos_list[i+1][0] # search range end
        if fp != -1: # if found
            c = {}
            # before anything else
            tmp = search_interval(data, pos, fp, 'name=', ')') # check if the name parameter is in the command decorator
            if tmp is not None:
                c['name'] = tmp.replace('"', '').replace("'", "") # and store it
                alias = c['name'] # take note we found a renaming
            else:
                alias = None
            base_name = ""
            # now we check the command definition
            fp += len('async def ')
            tmp = search_interval(data, pos, max_pos, ' def ', '(') # search the function name
            if tmp is None: continue # not found? (it shouldn't happen) skip to next one
            base_name = tmp
            if alias is None: # if no renaming
                c['name'] = tmp # just store it as it is
                if c['name'].startswith('_'): c['name'] = c['name'][1:]
            else: # if it's a renamed command, store the relation in the index
                func_index[cog + "_" + tmp] = alias
            # now parse the command parameters
            args = breakdown_parameters(search_interval(data, fp, max_pos, '(', ') ->'))
            # remove the first two (self, inter)
            args.pop(0)
            args.pop(0)
            c['args'] = args # and store
            # retrieve the doc string (the command description)
            tmp = search_interval(data, fp, max_pos, '"""', '"""')
            if tmp is not None:
                c['comment'] = tmp.replace("        ", "").replace('\n', '<br>')
            else:
                c['comment'] = ""
            if pos_list[i][1] == 4: # setting up sub_command_group name translation
                if alias is not None:
                    func_index[cog + "_" + base_name] = pos_list[i][2] + " " + c['name']
                else:
                    func_index[cog + "_" + c['name']] = pos_list[i][2] + " " + c['name']
            # IF AND ONLY IF the word "owner" or "hidden" are present in the description, we actually don't store the command
            # for that reason, the word owner shouldn't be used in regular command descriptions
            if 'owner' not in c['comment'].lower() and 'hidden' not in c['comment'].lower():
                c['color'] = color # color
                c['type'] = pos_list[i][1] # function type
                if pos_list[i][1] == 3:
                    c['parent'] = pos_list[i][2] # the parent if it's a sub command
                if pos_list[i][1] != 4: # don't put sub_command_group
                    cl.append(c) # add to list
    return cl

def find_command_pos(data): # loop over a file and note the position of all commands
    pos_list = [] # will contain the resulting list
    cur = 0 # cursor
    while True:
        poss = [data.find('@commands.slash_command', cur), data.find('@commands.user_command', cur), data.find('@commands.message_command', cur), data.find('.sub_command(', cur), data.find('.sub_command_group(', cur)] # different command types we are searching for
        idx = -1
        while True: # messy loop used to find the lowest position in the list
            idx += 1
            if idx == 5: break
            if poss[idx] == -1: continue
            # compare other in the list with current one, continue if they are better (aka lower)
            if poss[(idx+1)%5] != -1 and poss[(idx+1)%5] <= poss[idx]: continue
            if poss[(idx+2)%5] != -1 and poss[(idx+2)%5] <= poss[idx]: continue
            if poss[(idx+3)%5] != -1 and poss[(idx+3)%5] <= poss[idx]: continue
            if poss[(idx+4)%5] != -1 and poss[(idx+4)%5] <= poss[idx]: continue
            break
        if idx == 5: break # no more command found, we stop
        if idx >= 3: # we found a sub command
            x = data.find('@', poss[idx]-15) # we retrieve the name of the parent
            pos_list.append((poss[idx], idx, data[x+1:poss[idx]])) # and add it in the tuple
        else:
            pos_list.append((poss[idx], idx)) # position and command type (0 = slash, 1 = user, 2 = message, 3 = sub_command, 4 is always ignored)
        cur = poss[idx] + 10 # update the cursor
    return pos_list

def generate_help(): # main function
    global func_index # dictionnary for translating command groups to their names (IF renamed)
    print("Generating discordbot.html...")
    func_index = {}
    r = re.compile("^class ([a-zA-Z0-9_]*)\\(commands\\.Cog\\):", re.MULTILINE) # regex to find Cog
    command_list = {}
    for f in os.listdir('../cogs/'): # list all files (note: we don't parse the bot, debuf and test files)
        p = os.path.join('../cogs/', f) # path of the current file
        if f not in ['__init__.py'] and f.endswith('.py') and os.path.isfile(p): # search for valid python file (ignore init and other files)
            try:
                with open(p, mode='r', encoding='utf-8') as py: # open it
                    data = str(py.read())
                    all = r.findall(data) # apply the regex
                    for group in all: # for all valid results
                        try:
                            class_name = group # the cog Class name
                            if class_name.lower() == "private": continue
                            cl = retrieve_command_list(class_name, data, find_command_pos(data)) # parse the content
                            if len(cl) > 0: # if at least one public command found
                                command_list[class_name] = cl # store it
                        except Exception as e:
                            print("Error in", p)
                            print(e)
            except:
                pass
    generate_html(command_list) # generate the html using the stored data on found commands

if __name__ == "__main__": # entry point
    generate_help()