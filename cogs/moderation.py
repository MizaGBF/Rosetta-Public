from __future__ import annotations
import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..bot import DiscordBot
    from components.channel import CleanupSetting, AnnouncementSetting

# ----------------------------------------------------------------------
# Moderation Cog
# ----------------------------------------------------------------------
# Mod Commands to set the bot
# ----------------------------------------------------------------------


class Moderation(commands.Cog):
    """Settings for server moderators."""
    COLOR : int = 0x2eced1

    __slots__ = ("bot")

    def __init__(self : Moderation, bot : DiscordBot) -> None:
        self.bot : DiscordBot = bot

    @commands.user_command(name="Profile Picture")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=True)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    async def avatar(self : commands.user_command, inter : disnake.UserCommandInteraction, user: disnake.User) -> None:
        """Retrieve the profile picture of an user"""
        await inter.response.send_message(user.display_avatar.url, ephemeral=True)

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True, manage_messages=True)
    @commands.install_types(guild=True, user=False)
    @commands.contexts(guild=True, bot_dm=False, private_channel=False)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def mod(self : commands.slash_command, inter : disnake.GuildCommandInteraction) -> None:
        """Command Group (Mod Only)"""
        pass

    @mod.sub_command_group()
    async def ban(self : commands.SubCommandGroup, inter : disnake.GuildCommandInteraction) -> None:
        pass

    @ban.sub_command(name="spark")
    async def banspark(
        self : commands.SubCommand,
        inter : disnake.GuildCommandInteraction,
        member: disnake.Member
    ) -> None:
        """Ban an user from the spark ranking (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.ban.set(str(member.id), self.bot.ban.SPARK)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title="The user has been banned from the spark ranking",
                description="My owner has been notified",
                color=self.COLOR
            )
        )
        await self.bot.send(
            'debug',
            embed=self.bot.embed(
                title="{} ▫️ {}".format(member.display_name, member.id),
                description="Banned from all spark rankings by {:}\nMask: `{:b}`".format(
                    inter.author.display_name,
                    self.bot.ban.get(str(member.id))
                ),
                thumbnail=member.display_avatar,
                color=self.COLOR,
                footer=inter.guild.name
            )
        )

    @mod.sub_command_group()
    async def cleanup(self : commands.SubCommandGroup, inter : disnake.GuildCommandInteraction) -> None:
        pass

    @cleanup.sub_command(name="toggle")
    async def toggleautocleanup(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Toggle the auto-cleanup on this server (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if not isinstance(inter.channel, disnake.TextChannel): # only valid for text channels
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="This command is only usable in text channels",
                    footer=inter.guild.name + " ▫️ " + str(inter.guild.id),
                    color=self.COLOR
                )
            )
            return
        self.bot.channel.toggle_cleanup(str(inter.guild.id))
        await self.bot.channel.render_cleanup_settings(inter, self.COLOR)

    @cleanup.sub_command(name="channel")
    async def toggleautocleanupchannel(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Toggle the auto-cleanup exclusion of this channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if not isinstance(inter.channel, disnake.TextChannel):
            # only valid for text channels
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="This command is only usable in text channels",
                    footer=inter.guild.name + " ▫️ " + str(inter.guild.id),
                    color=self.COLOR
                )
            )
            return
        self.bot.channel.toggle_cleanup_channel(str(inter.guild.id), inter.channel.id)
        await self.bot.channel.render_cleanup_settings(inter, self.COLOR)

    @cleanup.sub_command(name="reset")
    async def resetautocleanup(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Reset the auto-cleanup settings (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.channel.reset_cleanup(str(inter.guild.id))
        await self.bot.channel.render_cleanup_settings(inter, self.COLOR)

    @cleanup.sub_command(name="see")
    async def seecleanupsetting(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """See all channels where no clean up is performed (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.channel.render_cleanup_settings(inter, self.COLOR)

    @mod.sub_command_group()
    async def announcement(self : commands.SubCommandGroup, inter : disnake.GuildCommandInteraction) -> None:
        pass

    @announcement.sub_command(name="channel")
    async def announcementchannel(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Enable/Disable game announcements in the specified channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if (not isinstance(inter.channel, disnake.TextChannel)
                and not isinstance(inter.channel, disnake.NewsChannel)
                and not isinstance(inter.channel, disnake.threads.Thread)
                and not isinstance(inter.channel, disnake.ForumChannel)): # check channel type
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Announcement Setting Error",
                    description="This command is only usable in text channels or equivalents",
                    footer=inter.guild.name + " ▫️ " + str(inter.guild.id),
                    color=self.COLOR
                )
            )
        else:
            self.bot.channel.toggle_announcement_channel(str(inter.guild.id), inter.channel.id)
            await self.bot.channel.render_announcement_settings(inter, self.COLOR)

    @announcement.sub_command(name="publish")
    async def announcementautopublish(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Toggle auto publishing for Announcement channels (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        self.bot.channel.toggle_announcement_publish(str(inter.guild.id))
        await self.bot.channel.render_announcement_settings(inter, self.COLOR)

    @announcement.sub_command()
    async def see(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Display the announcement settings (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.channel.render_announcement_settings(inter, self.COLOR)

    @mod.sub_command_group()
    async def pinboard(self : commands.SubCommandGroup, inter : disnake.GuildCommandInteraction) -> None:
        pass

    @pinboard.sub_command(name="toggle")
    async def togglepinboard(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Toggle the pinboard on your server (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.pinboard.toggle(inter, self.COLOR)

    @pinboard.sub_command(name="track")
    async def trackpinboard(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Toggle pinboard tracking for the current text or forum channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.pinboard.track_toggle(inter, self.COLOR)

    @pinboard.sub_command(name="output")
    async def outputpinboard(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Set the current channel as the output channel (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.pinboard.set(inter, self.COLOR, {"set_output":True})

    @pinboard.sub_command(name="settings")
    async def settingspinboard(
        self : commands.SubCommand,
        inter : disnake.GuildCommandInteraction,
        emoji : str = commands.Param(description="The emoji used as a pin trigger", default=""),
        threshold : int = commands.Param(description="Number of reactions needed to trigger the pin", default=0, ge=0),
        mod_bypass : int = commands.Param(
            description="If 1, a moderator can force the pin with a single reaction",
            ge=-1,
            le=1,
            default=-1
        )
    ) -> None:
        """See or Change pinboard settings for this server (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        options : dict[str, str|bool|int] = {}
        if self.bot.emote.isValid(emoji):
            options["emoji"] = emoji
        if threshold > 0:
            options["threshold"] = threshold
        if mod_bypass != -1:
            options["mod_bypass"] = mod_bypass != 0
        await self.bot.pinboard.set(inter, self.COLOR, options)

    @pinboard.sub_command(name="reset")
    async def resetpinboard(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Reset the tracked channel list of this server pinboard settings (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        await self.bot.pinboard.reset(inter, self.COLOR)

    """
    _serverinfo()
    Called by Server Info and /mod server info
    List the server infos and settings

    Parameters
    ----------
    inter: disnake Interaction
    is_mod: Boolean for mod informations
    """
    async def _serverinfo(self : Moderation, inter : disnake.UserCommandInteraction, is_mod : bool) -> None:
        await inter.response.defer(ephemeral=True)
        if inter.context.bot_dm or inter.guild is None:
            await inter.edit_original_message(
                embed=self.bot.embed(
                    title="Error",
                    description="This command is only usable when Rosetta is present in the Server.",
                    color=self.COLOR
                )
            )
            return
        guild : disnake.Guild = inter.guild
        icon : str|None
        try:
            icon = guild.icon.url
        except:
            icon = None
        owner : disnake.User|None = await self.bot.get_or_fetch_user(guild.owner_id)
        # server infos
        msgs : list[str] = [
            ":crown: Owned by {}\n:people_holding_hands: **{}** members\n".format(
                owner.mention,
                guild.member_count
            )
        ]
        if len(guild.categories) > 0:
            msgs.append(":file_folder: **{}** Categories\n".format(len(guild.categories)))
        if len(guild.text_channels) > 0:
            msgs.append(":printer : **{}** Text Channels\n".format(len(guild.text_channels)))
        if len(guild.voice_channels) > 0:
            msgs.append(":speaker: **{}** Voice Channels\n".format(len(guild.voice_channels)))
        if len(guild.forum_channels) > 0:
            msgs.append(":speaking_head: **{}** Forum Channels\n".format(len(guild.forum_channels)))
        if len(guild.stage_channels) > 0:
            msgs.append(":loudspeaker: **{}** Stage Channels\n".format(len(guild.stage_channels)))
        if guild.safety_alerts_channel is not None:
            msgs.append(":triangular_flag_on_post: Safety Channel **[#{}]({})**\n".format(
                guild.safety_alerts_channel.name,
                guild.safety_alerts_channel.jump_url
            ))
        msgs.append(":sound: Max Bitrate of **{}** kbps\n".format(int(guild.bitrate_limit / 1000)))
        if len(guild.roles) > 0:
            msgs.append(":scroll: **{}** Roles\n".format(len(guild.roles)))
        if len(guild.emojis) > 0:
            msgs.append("🙂 **{}** / **{}** Emojis\n".format(len(guild.emojis), guild.emoji_limit * 2))
        if len(guild.stickers) > 0:
            msgs.append("🌠 **{}** / **{}** Stickers\n".format(len(guild.stickers), guild.sticker_limit))
        if guild.soundboard_limit > 0:
            msgs.append(":loud_sound: Up to **{}** Soundboard elements\n".format(guild.soundboard_limit))
        if len(guild.scheduled_events) > 0:
            msgs.append(":clock1130: **{}** scheduled Events\n".format(len(guild.scheduled_events)))
        if guild.premium_tier > 0:
            msgs.append(":diamonds: Boost Tier **{}** (**{}** Boosts)\n".format(
                guild.premium_tier, guild.premium_subscription_count
            ))
        if guild.vanity_url_code:
            msgs.append(":wave: Has Vanity Invite\n")
        # rosetta settings
        rosetta : list[str] = []
        gid : str = str(guild.id)
        if is_mod and not inter.me.guild_permissions.external_emojis:
            rosetta.append(":x: **External Emoji** permission is **Missing**\n")
        cleanup_settings : CleanupSetting = self.bot.channel.get_cleanup_settings(gid)
        if cleanup_settings[0]:
            rosetta.append("{} **Auto cleanup** enabled".format(self.bot.emote.get('lyria')))
            if len(cleanup_settings[1]) > 0:
                rosetta.append(", {} channel(s) are excluded".format(len(cleanup_settings[1])))
            rosetta.append("\n")
        elif is_mod:
            rosetta.append(":warning: **Auto cleanup** disabled\n")
        if self.bot.pinboard.is_enabled(gid):
            rosetta.append(":star: **Pinboard** enabled\n")
        elif is_mod:
            rosetta.append(":warning: **Pinboard** disabled.\n")
        announcement_settings : AnnouncementSetting = self.bot.channel.get_announcement_settings(gid)
        if announcement_settings[0] > 0:
            rosetta.append(":new: **Announcements** enabled")
            if announcement_settings[1]:
                rosetta.append(", along with *auto-publish*")
            rosetta.append("\n")
        elif is_mod:
            rosetta.append(":warning: **Announcements** disabled\n")
        if gid in self.bot.data.save['assignablerole']:
            rosetta.append(
                ":people_with_bunny_ears_partying: **{}** self-assignable roles\n".format(
                    len(self.bot.data.save['assignablerole'][gid].keys())
                )
            )
        # append rosetta setting messages if any
        if len(rosetta) > 0:
            msgs.append("\n**Rosetta Settings**\n")
            msgs.extend(rosetta)
        await inter.edit_original_message(
            embed=self.bot.embed(
                title=guild.name + " status",
                description="".join(msgs),
                thumbnail=icon,
                footer="creation date",
                timestamp=guild.created_at,
                color=self.COLOR
            )
        )

    @commands.message_command(name="Server Info")
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.install_types(guild=True, user=False)
    @commands.contexts(guild=True, bot_dm=True, private_channel=True)
    @commands.cooldown(1, 10, commands.BucketType.user)
    async def serverinfo(
        self : commands.message_command,
        inter : disnake.MessageCommandInteraction,
        message: disnake.Message
    ) -> None:
        """Get informations on the current guild"""
        await self._serverinfo(inter, self.bot.isMod(inter))

    @mod.sub_command_group()
    async def server(self : commands.SubCommandGroup, inter : disnake.GuildCommandInteraction) -> None:
        pass

    @server.sub_command(name="info")
    async def serverinfo_cmd(self : commands.SubCommand, inter : disnake.GuildCommandInteraction) -> None:
        """Get informations on the current guild (Mod Only)"""
        await self._serverinfo(inter, True)
