import discord
from discord import app_commands
from discord.ext import commands
from src.Interfaces import IConfigurationManager, IAlbionApiManager
from src.Model import Configuration, Guild


class ConfigurationCog(commands.Cog):
    def __init__(
        self,
        bot: commands.Bot,
        configuration_manager: IConfigurationManager,
        albion_api_manager: IAlbionApiManager,
    ):
        self.bot = bot
        self.configuration_manager = configuration_manager
        self.albion_api_manager = albion_api_manager

    # -------------------------------------------------------------------------
    # Helper
    # -------------------------------------------------------------------------

    async def _get_config(self, interaction: discord.Interaction) -> Configuration:
        return await self.configuration_manager.get_config(str(interaction.guild_id))

    async def _save_config(self, config: Configuration) -> None:
        await self.configuration_manager.update_config(config)

    # -------------------------------------------------------------------------
    # /config-view
    # -------------------------------------------------------------------------

    @app_commands.command(name="config-view", description="[Admin] View the current server configuration.")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_view(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        config = await self._get_config(interaction)
        embed = _build_config_embed(config, interaction.guild)
        await interaction.followup.send(embed=embed, ephemeral=True)

    # -------------------------------------------------------------------------
    # /config-set-guild
    # -------------------------------------------------------------------------

    @app_commands.command(name="config-set-guild", description="[Admin] Link this server to an Albion Online guild.")
    @app_commands.describe(guild_name="The exact Albion Online guild name")
    @app_commands.checks.has_permissions(administrator=True)
    async def config_set_guild(self, interaction: discord.Interaction, guild_name: str):
        await interaction.response.defer(ephemeral=True)

        guild_data = await self.albion_api_manager.get_guild_by_name(guild_name)
        if guild_data is None:
            await interaction.followup.send(
                f"❌ Could not find an Albion guild named **{guild_name}**.", ephemeral=True
            )
            return

        config = await self._get_config(interaction)
        config.guild = Guild(name=guild_data.name, id=guild_data.id)
        await self._save_config(config)

        await interaction.followup.send(
            f"✅ Guild linked to **{guild_data.name}** (`{guild_data.id}`).", ephemeral=True
        )

    # -------------------------------------------------------------------------
    # /config-set-roles
    # -------------------------------------------------------------------------

    @app_commands.command(name="config-set-roles", description="[Admin] Configure server roles.")
    @app_commands.describe(
        admin_role="The admin role",
        member_role="The guild member role",
        ally_role="The ally role",
        lootsplit_buyer_role="The lootsplit buyer role",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_set_roles(
        self,
        interaction: discord.Interaction,
        admin_role: discord.Role | None = None,
        member_role: discord.Role | None = None,
        ally_role: discord.Role | None = None,
        lootsplit_buyer_role: discord.Role | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if not any([admin_role, member_role, ally_role, lootsplit_buyer_role]):
            await interaction.followup.send(
                "❌ Please provide at least one role to update.", ephemeral=True
            )
            return

        config = await self._get_config(interaction)

        if admin_role:
            config.admin_role_id = str(admin_role.id)
        if member_role:
            config.member_role_id = str(member_role.id)
        if ally_role:
            config.ally_role_id = str(ally_role.id)
        if lootsplit_buyer_role:
            config.lootsplit_buyer_role_id = str(lootsplit_buyer_role.id)

        await self._save_config(config)

        updated = []
        if admin_role:
            updated.append(f"Admin → {admin_role.mention}")
        if member_role:
            updated.append(f"Member → {member_role.mention}")
        if ally_role:
            updated.append(f"Ally → {ally_role.mention}")
        if lootsplit_buyer_role:
            updated.append(f"Lootsplit Buyer → {lootsplit_buyer_role.mention}")

        await interaction.followup.send(
            "✅ Roles updated:\n" + "\n".join(updated), ephemeral=True
        )

    # -------------------------------------------------------------------------
    # /config-set-lootsplit
    # -------------------------------------------------------------------------

    @app_commands.command(name="config-set-lootsplit", description="[Admin] Configure lootsplit settings.")
    @app_commands.describe(
        guild_tax_percent="Guild tax percentage (0–100)",
        sale_tax_percent="Albion sale tax percentage (0–100)",
        sale_timer_minutes="Minutes players have to sell items",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def config_set_lootsplit(
        self,
        interaction: discord.Interaction,
        guild_tax_percent: int | None = None,
        sale_tax_percent: int | None = None,
        sale_timer_minutes: int | None = None,
    ):
        await interaction.response.defer(ephemeral=True)

        if not any([guild_tax_percent, sale_tax_percent, sale_timer_minutes]):
            await interaction.followup.send(
                "❌ Please provide at least one value to update.", ephemeral=True
            )
            return

        for name, val in [
            ("guild_tax_percent", guild_tax_percent),
            ("sale_tax_percent", sale_tax_percent),
        ]:
            if val is not None and not (0 <= val <= 100):
                await interaction.followup.send(
                    f"❌ `{name}` must be between 0 and 100.", ephemeral=True
                )
                return

        if sale_timer_minutes is not None and sale_timer_minutes <= 0:
            await interaction.followup.send(
                "❌ `sale_timer_minutes` must be a positive number.", ephemeral=True
            )
            return

        config = await self._get_config(interaction)

        if guild_tax_percent is not None:
            config.guild_tax_percent = guild_tax_percent
        if sale_tax_percent is not None:
            config.lootsplit_sale_tax_percent = sale_tax_percent
        if sale_timer_minutes is not None:
            config.lootsplit_sale_timer_minutes = sale_timer_minutes

        await self._save_config(config)

        updated = []
        if guild_tax_percent is not None:
            updated.append(f"Guild Tax → **{guild_tax_percent}%**")
        if sale_tax_percent is not None:
            updated.append(f"Sale Tax → **{sale_tax_percent}%**")
        if sale_timer_minutes is not None:
            updated.append(f"Sale Timer → **{sale_timer_minutes} min**")

        await interaction.followup.send(
            "✅ Lootsplit settings updated:\n" + "\n".join(updated), ephemeral=True
        )

    # -------------------------------------------------------------------------
    # Error handlers
    # -------------------------------------------------------------------------

    @config_view.error
    @config_set_guild.error
    @config_set_roles.error
    @config_set_lootsplit.error
    async def config_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command.", ephemeral=True
            )


def _build_config_embed(config: Configuration, guild: discord.Guild | None) -> discord.Embed:
    embed = discord.Embed(
        title="⚙️ Server Configuration",
        color=discord.Color.blurple(),
    )

    # Guild linkage
    if config.guild:
        embed.add_field(
            name="🏰 Albion Guild",
            value=f"{config.guild.name} (`{config.guild.id}`)",
            inline=False,
        )
    else:
        embed.add_field(name="🏰 Albion Guild", value="Not set — use `/config-set-guild`", inline=False)

    # Roles
    def role_str(role_id: str | None) -> str:
        if not role_id:
            return "Not set"
        return f"<@&{role_id}>"

    embed.add_field(name="👑 Admin Role",          value=role_str(config.admin_role_id),          inline=True)
    embed.add_field(name="⚔️ Member Role",          value=role_str(config.member_role_id),         inline=True)
    embed.add_field(name="🤝 Ally Role",            value=role_str(config.ally_role_id),           inline=True)
    embed.add_field(name="🛒 Lootsplit Buyer Role", value=role_str(config.lootsplit_buyer_role_id), inline=True)

    # Lootsplit settings
    embed.add_field(name="🏦 Guild Tax",      value=f"{config.guild_tax_percent}%",             inline=True)
    embed.add_field(name="💸 Sale Tax",       value=f"{config.lootsplit_sale_tax_percent}%",    inline=True)
    embed.add_field(name="⏱️ Sale Timer",     value=f"{config.lootsplit_sale_timer_minutes} min", inline=True)

    return embed