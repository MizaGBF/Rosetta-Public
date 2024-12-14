import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot

# ----------------------------------------------------------------------------------------------------------------
# Moderation Cog
# ----------------------------------------------------------------------------------------------------------------
# Mod Commands to set the bot
# ----------------------------------------------------------------------------------------------------------------

class Moderation(commands.Cog):
    """Settings for server moderators."""
    COLOR = 0x2eced1

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot = bot

    @commands.user_command(name="Profile Picture")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    async def avatar(self, inter: disnake.UserCommandInteraction, user: disnake.User) -> None:
        """Retrieve the profile picture of an user"""
        await inter.response.send_message(user.display_avatar.url, ephemeral=True)

    """
    _serverinfo()
    Called by Server Info and /mod server info
    List the server infos and settings
    
    Parameters
    ----------
    inter: Disnake Interaction
    is_mod: Boolean for mod informations
    """
    async def _serverinfo(self, inter: disnake.UserCommandInteraction, is_mod : bool) -> None:
        await inter.response.defer(ephemeral=True)
        guild = inter.guild
        try: icon = guild.icon.url
        except: icon = None
        owner = await self.bot.get_or_fetch_user(guild.owner_id)
        # server infos
        msgs = [":crown: Owned by {}\n:people_holding_hands: **{}** members\n".format(owner.mention, guild.member_count)]
        if len(guild.categories) > 0: msgs.append(":file_folder: **{}** Categories\n".format(len(guild.categories)))
        if len(guild.text_channels) > 0: msgs.append(":printer: **{}** Text Channels\n".format(len(guild.text_channels)))
        if len(guild.voice_channels) > 0: msgs.append(":speaker: **{}** Voice Channels\n".format(len(guild.voice_channels)))
        if len(guild.forum_channels) > 0: msgs.append(":speaking_head: **{}** Forum Channels\n".format(len(guild.forum_channels)))
        if len(guild.stage_channels) > 0: msgs.append(":loudspeaker: **{}** Stage Channels\n".format(len(guild.stage_channels)))
        if guild.safety_alerts_channel is not None: msgs.append(":triangular_flag_on_post: Safety Channel **[#{}]({})**\n".format(guild.safety_alerts_channel.name, guild.safety_alerts_channel.jump_url))
        msgs.append(":sound: Max Bitrate of **{}** kbps\n".format(int(guild.bitrate_limit / 1000)))
        if len(guild.roles) > 0: msgs.append(":scroll: **{}** Roles\n".format(len(guild.roles)))
        if len(guild.emojis) > 0: msgs.append("🙂 **{}** / **{}** Emojis\n".format(len(guild.emojis), guild.emoji_limit*2))
        if len(guild.stickers) > 0: msgs.append("🌠 **{}** / **{}** Stickers\n".format(len(guild.stickers), guild.sticker_limit))
        if len(guild.scheduled_events) > 0: msgs.append(":clock1130: **{}** scheduled Events\n".format(len(guild.scheduled_events)))
        if guild.premium_tier > 0: msgs.append(":diamonds: Boost Tier **{}** (**{}** Boosts)\n".format(guild.premium_tier, guild.premium_subscription_count))
        if guild.vanity_url_code: msgs.append(":wave: Has Vanity Invite\n")
        # rosetta settings
        rosetta = []
        gid = str(guild.id)
        if is_mod and not inter.me.guild_permissions.external_emojis: rosetta.append(":x: **External Emoji** permission is **Missing**\n")
        if len(self.bot.data.save['permitted'].get(gid, [])) > 0: rosetta.append("{} **Auto cleanup** enabled\n".format(self.bot.emote.get('lyria')))
        elif is_mod: rosetta.append(":warning: **Auto cleanup** disabled\n")
        if self.bot.pinboard.is_enabled(gid): rosetta.append(":star: **Pinboard** enabled\n")
        elif is_mod: rosetta.append(":warning: **Pinboard** disabled.\n")
        if gid in self.bot.data.save['announcement']: rosetta.append(":new: **Announcements** enabled\n")
        elif is_mod: rosetta.append(":warning: **Announcements** disabled\n")
        if gid in self.bot.data.save['assignablerole']: rosetta.append(":people_with_bunny_ears_partying: **{}** self-assignable roles\n".format(len(self.bot.data.save['assignablerole'][gid].keys())))
        # append rosetta setting messages if any
        if len(rosetta) > 0:
            msgs.append("\n**Rosetta Settings**\n")
            msgs.extend(rosetta)
        await inter.edit_original_message(embed=self.bot.embed(title=guild.name + " status", description="".join(msgs), thumbnail=icon, footer="creation date", timestamp=guild.created_at, color=self.COLOR))

    @commands.message_command(name="Server Info")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def serverinfo(self, inter: disnake.MessageCommandInteraction, message: disnake.Message) -> None:
        """Get informations on the current guild"""
        await self._serverinfo(inter, self.bot.isMod(inter))

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True, manage_messages=True)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def mod(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group (Mod Only)"""
        pass

    @mod.sub_command_group()
    async def ban(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @ban.sub_command(name="spark")
    async def banspark(self, inter: disnake.GuildCommandInteraction, member: disnake.Member) -> None:
        """Ban an user from the spark ranking (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.set(member.id, self.bot.ban.SPARK)
        await inter.edit_original_message(embed=self.bot.embed(title="The user has been banned from the spark ranking", description="My owner has been notified", color=self.COLOR))
        await self.bot.send('debug', embed=self.bot.embed(title="{} ▫️ {}".format(member.display_name, member.id), description="Banned from all spark rankings by {}\nValues: `{}`".format(inter.author.display_name, self.bot.data.save['spark'].get(str(member.id), 'No Data')), thumbnail=member.display_avatar, color=self.COLOR, footer=inter.guild.name))

    @mod.sub_command_group()
    async def cleanup(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    """_seeCleanupSetting()
    Output the server cleanup settings
    
    Parameters
    --------
    inter: A command interaction. Must have been deferred beforehand.
    """
    async def _seeCleanupSetting(self, inter: disnake.GuildCommandInteraction) -> None:
        gid = str(inter.guild.id)
        if gid in self.bot.data.save['permitted'] and len(self.bot.data.save['permitted'][gid]) > 0: # check if guild has autocleanup setup for any channel
            msgs = []
            for c in inter.guild.channels: # for each channel
                if c.id in self.bot.data.save['permitted'][gid]: # add to list
                    try:
                        msgs.append(c.name)
                    except:
                        pass
            await inter.edit_original_message(embed=self.bot.embed(title="Auto Cleanup is enable in all channels but the following ones:", description="\n".join(msgs), footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Auto Cleanup is disabled in all channels", footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))

    @cleanup.sub_command(name="toggle")
    async def toggleautocleanup(self, inter: disnake.GuildCommandInteraction) -> None:
        """Toggle the auto-cleanup in this channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        gid = str(inter.guild.id)
        if not isinstance(inter.channel, disnake.TextChannel): # only valid for text channels
            await inter.edit_original_message(embed=self.bot.embed(title="This command is only usable in text channels", footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))
            return
        cid = inter.channel.id # get id
        if gid not in self.bot.data.save['permitted']:
            self.bot.data.save['permitted'][gid] = []
        for i, v in enumerate(self.bot.data.save['permitted'][gid]):
            if v == cid: # if channel id already present
                self.bot.data.save['permitted'][gid].pop(i) # we remove (disable)
                self.bot.data.pending = True
                await self._seeCleanupSetting(inter)
                return
        # if channel id hasn't been found
        self.bot.data.save['permitted'][gid].append(cid) # we add (enable)
        self.bot.data.pending = True
        await self._seeCleanupSetting(inter)

    @cleanup.sub_command(name="reset")
    async def resetautocleanup(self, inter: disnake.GuildCommandInteraction) -> None:
        """Reset the auto-cleanup settings (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        gid = str(inter.guild.id)
        if gid in self.bot.data.save['permitted']: # simply clear guild autocleanup data
            self.bot.data.save['permitted'].pop(gid)
            self.bot.data.pending = True
            await inter.edit_original_message(embed=self.bot.embed(title="Auto Cleanup is disabled in all channels", footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Auto Cleanup is already disabled in all channels", footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))

    @cleanup.sub_command(name="see")
    async def seecleanupsetting(self, inter: disnake.GuildCommandInteraction) -> None:
        """See all channels where no clean up is performed (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        await self._seeCleanupSetting(inter)

    @mod.sub_command_group()
    async def announcement(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    """_announcement_see()
    Output the server cleanup settings
    
    Parameters
    --------
    inter: A command interaction. Must have been deferred beforehand.
    msg: String, message to display
    settings: current setting
    """
    async def _announcement_see(self, inter: disnake.GuildCommandInteraction, msg : str, settings : list) -> None:
        c = self.bot.get_channel(settings[0])
        await inter.edit_original_message(embed=self.bot.embed(title="Announcement Setting", description=msg, fields=[{'name':'Channel', 'value':'[{}](https://discord.com/channels/{}/{})'.format(c.name, inter.guild.id, c.id), 'inline':True}, {'name':'Auto Publish to followers', 'value':('Enabled' if settings[1] else "Disabled"), 'inline':True}], footer=inter.guild.name + " ▫️ " + str(inter.guild.id), inline=True, color=self.COLOR))

    @announcement.sub_command()
    async def toggle_channel(self, inter: disnake.GuildCommandInteraction) -> None:
        """Enable/Disable game announcements in the specified channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if not isinstance(inter.channel, disnake.TextChannel) and not isinstance(inter.channel, disnake.NewsChannel) and not isinstance(inter.channel, disnake.threads.Thread) and not isinstance(inter.channel, disnake.ForumChannel): # check channel type
            await inter.edit_original_message(embed=self.bot.embed(title="Announcement Setting Error", description="This command is only usable in text channels or equivalents", footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))
            return
        cid = inter.channel.id
        gid = str(inter.guild.id)
        b = True
        if self.bot.data.save['announcement'].get(gid, [-1, False])[0] == cid: # index 0 is the channel id.
            b = False
            self.bot.data.save['announcement'].pop(gid) # simply remove to disable
        else:
            self.bot.data.save['announcement'][gid] = [cid, True] # else we enable by initializing new data
        self.bot.channel.update_announcement_channels() # update bot announcement channel list
        self.bot.data.pending = True
        if b:
            await self._announcement_see(inter, "Announcement enabled and channel updated", self.bot.data.save['announcement'][gid])
        else:
            await inter.edit_original_message(embed=self.bot.embed(title="Announcement Setting", description="Announcements have been disabled", footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))

    @announcement.sub_command()
    async def auto_publish(self, inter: disnake.GuildCommandInteraction, value : int = commands.Param(description="0 to disable, 1 to enable", ge=0, le=1)) -> None:
        """Enable/Disable auto publishing for Announcement channels (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        gid = str(inter.guild.id)
        if gid not in self.bot.data.save['announcement']:
            await inter.edit_original_message(embed=self.bot.embed(title="Announcement Setting Error", description="Announcements aren't enabled on this server.\nCheck out {}".format(self.bot.util.command2mention('mod announcement toggle_channel')), footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))
        else:
            self.bot.data.save['announcement'][gid][1] = (value != 0) # index 1 is the publish flag. We simply flip it.
            self.bot.data.pending = True
            self.bot.channel.update_announcement_channels()
            await self._announcement_see(inter, "Auto Publish setting updated", self.bot.data.save['announcement'][gid])

    @announcement.sub_command()
    async def see(self, inter: disnake.GuildCommandInteraction) -> None:
        """Display the announcement settings (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        gid = str(inter.guild.id)
        try:
            await self._announcement_see(inter, "", self.bot.data.save['announcement'][gid])
        except:
            await inter.edit_original_message(embed=self.bot.embed(title="Announcement Setting", description="Announcements aren't enabled on this server.\nCheck out {}".format(self.bot.util.command2mention('mod announcement toggle_channel')), footer=inter.guild.name + " ▫️ " + str(inter.guild.id), color=self.COLOR))

    @mod.sub_command_group()
    async def pinboard(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @pinboard.sub_command(name="enable")
    async def enablepinboard(self, inter: disnake.GuildCommandInteraction) -> None:
        """Enable the pinboard on your server (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if self.bot.pinboard.get(str(inter.guild.id)) is None:
            self.bot.pinboard.initialize(str(inter.guild.id))
        else:
            self.bot.pinboard.enable(str(inter.guild.id))
        await self.bot.pinboard.display(inter, self.COLOR, "Pinboard is enabled on this server")

    @pinboard.sub_command(name="disable")
    async def disablepinboard(self, inter: disnake.GuildCommandInteraction) -> None:
        """Disable the pinboard on your server (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if self.bot.pinboard.get(str(inter.guild.id)) is None:
            pass
        else:
            self.bot.pinboard.disable(str(inter.guild.id))
        await self.bot.pinboard.display(inter, self.COLOR, "Pinboard is disabled on this server")

    @pinboard.sub_command()
    async def track(self, inter: disnake.GuildCommandInteraction) -> None:
        """Toggle pinboard tracking for the current text or forum channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.pinboard.initialize(str(inter.guild.id))
        # check for different channel types (some aren't supported)
        if isinstance(inter.channel, disnake.TextChannel):
            r = self.bot.pinboard.track_toggle(str(inter.guild.id), int(inter.channel.id))
            await self.bot.pinboard.display(inter, self.COLOR, "This channel is now tracked" if r is True else "This channel isn't tracked anymore")
        elif isinstance(inter.channel, disnake.Thread):
            try:
                c = inter.channel.parent
                if not isinstance(c, disnake.ForumChannel): raise Exception()
                r = self.bot.pinboard.track_toggle(str(inter.guild.id), int(c.id))
                await self.bot.pinboard.display(inter, self.COLOR, "This channel is now tracked" if r is True else "This channel isn't tracked anymore")
            except:
                await self.bot.pinboard.display(inter, self.COLOR, "This command can only be used in a text or forum channel")
        else:
            await self.bot.pinboard.display(inter, self.COLOR, "This command can only be used in a text or forum channel")

    @pinboard.sub_command()
    async def output_here(self, inter: disnake.GuildCommandInteraction) -> None:
        """Set the current channel as the output channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if isinstance(inter.channel, disnake.TextChannel):
            self.bot.pinboard.initialize(str(inter.guild.id))
            self.bot.pinboard.set(str(inter.guild.id), output=int(inter.channel.id))
            await self.bot.pinboard.display(inter, self.COLOR, "This channel is where future pinned messages will appear")
        else:
            await self.bot.pinboard.display(inter, self.COLOR, "This command can only be used in a text channel")

    @pinboard.sub_command()
    async def settings(self, inter: disnake.GuildCommandInteraction, emoji : str = commands.Param(description="The emoji used as a pin trigger", default=""), threshold : int = commands.Param(description="Number of reactions needed to trigger the pin", default=0, ge=0), mod_bypass : int = commands.Param(description="If 1, a moderator can force the pin with a single reaction", ge=-1, le=1, default=-1)) -> None:
        """See or Change pinboard settings for this server (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.pinboard.initialize(str(inter.guild.id))
        updated = False
        emoji = emoji.strip()
        # process parameters and set accordingly
        if self.bot.emote.isValid(emoji):
            self.bot.pinboard.set(str(inter.guild.id), emoji=emoji)
            updated = True
        if threshold > 0:
            self.bot.pinboard.set(str(inter.guild.id), threshold=threshold)
            updated = True
        if mod_bypass != -1:
            self.bot.pinboard.set(str(inter.guild.id), mod_bypass=(mod_bypass != 0))
            updated = True
        await self.bot.pinboard.display(inter, self.COLOR, "Settings have been updated" if updated else "")

    @pinboard.sub_command()
    async def reset_tracked(self, inter: disnake.GuildCommandInteraction) -> None:
        """Reset the tracked channel list of this server pinboard settings (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.pinboard.set(str(inter.guild.id), tracked=[])
        await self.bot.pinboard.display(inter, self.COLOR, "Settings have been updated")

    @mod.sub_command_group()
    async def server(self, inter: disnake.GuildCommandInteraction) -> None:
        pass

    @server.sub_command(name="info")
    async def serverinfo_cmd(self, inter: disnake.GuildCommandInteraction) -> None:
        """Get informations on the current guild (Mod Only)"""
        await self._serverinfo(inter, True)