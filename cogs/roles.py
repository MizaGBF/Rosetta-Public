import disnake
from disnake.ext import commands
from typing import TYPE_CHECKING
if TYPE_CHECKING: from ..bot import DiscordBot
from views.page import Page

# ----------------------------------------------------------------------------------------------------------------
# Roles Cog
# ----------------------------------------------------------------------------------------------------------------
# Self-Assignable roles
# ----------------------------------------------------------------------------------------------------------------

class Roles(commands.Cog):
    """Self assignable roles."""
    COLOR : int = 0x17e37a

    def __init__(self, bot : 'DiscordBot') -> None:
        self.bot : 'DiscordBot' = bot

    @commands.slash_command()
    @commands.default_member_permissions(send_messages=True, read_messages=True)
    @commands.cooldown(2, 5, commands.BucketType.user)
    @commands.max_concurrency(10, commands.BucketType.default)
    async def role(self, inter: disnake.GuildCommandInteraction) -> None:
        """Command Group"""
        pass

    """check_role_integrity()
    Check and update the given guild saved self assignable role list
    
    Parameters
    --------
    disnake.Guild: The guild to check
    
    Returns
    --------
    Tuple: Guild ID (as a string) and the updated role list
    """
    def check_role_integrity(self, guild) -> None:
        g = str(guild.id) # guild id (str format)
        roles = self.bot.data.save['assignablerole'].get(g, {}) # saved role dict for that guild
        keys = list(roles.keys()) # list of saved role names
        for k in keys:
            r = guild.get_role(roles[k]) # retrieve role using its id
            if r is not None: # it exists
                if k != r.name.lower(): # check if its name has changed
                    self.bot.data.save['assignablerole'][g].pop(k) # remove old one
                    self.bot.data.save['assignablerole'][g][r.name.lower()] = r.id # re-add id under new name
                    self.bot.data.pending = True
            else: # role doesn't exist
                self.bot.data.save['assignablerole'][g].pop(k) # remove
                self.bot.data.pending = True
        return g, self.bot.data.save['assignablerole'].get(g, {})

    @role.sub_command()
    async def iam(self, inter: disnake.GuildCommandInteraction, role_name : str = commands.Param(description="The self-assignable role you want to get")) -> None:
        """Add a role to yourself. Role must be on the server role list."""
        await inter.response.defer(ephemeral=True)
        g, roles = self.check_role_integrity(inter.guild) # retrieve up to date list
        if role_name.lower() not in roles: # check if the role exists in the self assignable list
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Name `{}` not found in the self-assignable role list\nPlease check {}".format(role_name, self.bot.util.command2mention('role list')), color=self.COLOR))
        else: # it is
            gid = roles[role_name.lower()] # retrieve role id
            r = inter.guild.get_role(gid) # retrieve role
            if r is None: # additional error check
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Role `{}` not found".format(role_name), color=self.COLOR))
            else:
                try: # add role to user
                    await inter.author.add_roles(r)
                    await inter.edit_original_message(embed=self.bot.embed(title="Your roles have been updated", description="Role `{}` has been added to your profile".format(r), color=self.COLOR))
                except:
                    await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Failed to assign the role.\nCheck if you have the role or contact a moderator.", color=self.COLOR))

    @role.sub_command()
    async def iamnot(self, inter: disnake.GuildCommandInteraction, role_name : str = commands.Param(description="The self-assignable role you want to remove")) -> None:
        """Remove a role from yourself. Role must be on the server role list."""
        await inter.response.defer(ephemeral=True)
        g, roles = self.check_role_integrity(inter.guild) # retrieve up to date list
        if role_name.lower() not in roles: # check if the role exists in the self assignable list
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Name `{}` not found in the self-assignable role list\nPlease check {}".format(role_name, self.bot.util.command2mention('role list')), color=self.COLOR))
        else: # it is
            gid = roles[role_name.lower()] # retrieve role id
            r = inter.guild.get_role(gid) # retrieve role
            if r is None: # additional error check
                await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Role `{}` not found".format(role_name), color=self.COLOR))
            else:
                try: # remove role from user
                    await inter.author.remove_roles(r)
                    await inter.edit_original_message(embed=self.bot.embed(title="Your roles have been updated", description="Role `{}` has been removed from your profile".format(r), color=self.COLOR))
                except:
                    await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Failed to remove the role.\nCheck if you have the role or contact a moderator.", color=self.COLOR))

    @role.sub_command(name="list")
    async def _list(self, inter: disnake.GuildCommandInteraction) -> None:
        """List the self-assignable roles available in this server"""
        await inter.response.defer(ephemeral=True)
        g, roles = self.check_role_integrity(inter.guild) # retrieve up to date list
        if len(roles) == 0:
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="No self-assignable roles available on this server", color=self.COLOR))
            return
        embeds = []
        fields = []
        count = 0
        # make a list of embeds containing the list of role (30 per embed/page max)
        for k in sorted(list(roles.keys())):
            if count % 10 == 0: # 3 fields per page, so 10 roles per field.
                fields.append({'name':'{} '.format(self.bot.emote.get(str(len(fields)+1))), 'value':[], 'inline':True})
            r = inter.guild.get_role(roles[k]) # get role
            if r is not None: # add to field
                fields[-1]['value'].append(r.name.lower())
            count += 1
            if count == 30: # reached 30, make new embed
                for field in fields: # join list
                    field['value'] = "\n".join(field['value'])
                embeds.append(self.bot.embed(title="Self Assignable Roles", fields=fields, footer="Page {}/{}".format(len(embeds)+1, 1+len(roles)//30), color=self.COLOR))
                fields = []
                count = 0
        if count != 0: # empty check
            for field in fields: # join list
                field['value'] = "\n".join(field['value'])
            embeds.append(self.bot.embed(title="Self Assignable Roles", fields=fields, footer="Page {}/{}".format(len(embeds)+1, 1+len(roles)//30), color=self.COLOR))
        if len(embeds) > 1: # multiple embed, use the Page view
            view = Page(self.bot, owner_id=inter.author.id, embeds=embeds)
            await inter.edit_original_message(embed=embeds[0], view=view)
            view.message = await inter.original_message()
        else: # single embed, simply send
            await inter.edit_original_message(embed=embeds[0])

    @role.sub_command()
    async def add(self, inter: disnake.GuildCommandInteraction, role_name : str = commands.Param(description="The self-assignable role you want to add to the list")) -> None:
        """Add a role to the list of self-assignable roles (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if not self.bot.isMod(inter): # moderator check
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Only moderators can make a role self-assignable", color=self.COLOR))
            return
        role = None
        for r in inter.guild.roles: # check if the role name corresponds to a name
            if role_name.lower() == r.name.lower():
                role = r
                break
        if role is None: # it doesn't
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Role `{}` not found".format(role_name), color=self.COLOR))
            return
        gid = str(inter.guild.id)
        if gid not in self.bot.data.save['assignablerole']: # create role data for this guild
            self.bot.data.save['assignablerole'][gid] = {}
        if role.name.lower() in self.bot.data.save['assignablerole'][gid]: # the role is already self assignable
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Role `{}` is already a self-assignable role.\nDid you mean `/role remove` ?".format(role_name), color=self.COLOR))
            return
        self.bot.data.save['assignablerole'][gid][role.name.lower()] = role.id # add the role
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Role `{}` added to the self-assignable role list".format(role_name), color=self.COLOR))

    @role.sub_command()
    async def remove(self, inter: disnake.GuildCommandInteraction, role_name : str = commands.Param(description="The self-assignable role you want to remove from the list")) -> None:
        """Remove a role from the list of self-assignable roles (Mod Only)"""
        await inter.response.defer(ephemeral=True)
        if not self.bot.isMod(inter): # moderator check
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Only moderators can make a role self-assignable", color=self.COLOR))
            return
        role = None
        for r in inter.guild.roles: # check if the role name corresponds to a name
            if role_name.lower() == r.name.lower():
                role = r
                break
        if role is None: # it doesn't
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Role `{}` not found".format(role_name), color=self.COLOR))
            return
        gid = str(inter.guild.id)
        if gid not in self.bot.data.save['assignablerole']: # create role data for this guild
            self.bot.data.save['assignablerole'][gid] = {}
        if role.name.lower() not in self.bot.data.save['assignablerole'][gid]: # the role isn't in the self assignable list
            await inter.edit_original_message(embed=self.bot.embed(title="Error", description="Role `{}` isn't a self-assignable role.\nDid you mean `/role add` ?".format(role_name), color=self.COLOR))
            return
        self.bot.data.save['assignablerole'][gid].pop(role.name.lower()) # remove the role
        self.bot.data.pending = True
        await inter.edit_original_message(embed=self.bot.embed(title="Role `{}` removed from the self-assignable role list".format(role_name), color=self.COLOR))