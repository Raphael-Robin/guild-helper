import discord
from discord import app_commands
from discord.ext import commands
from src.Interfaces import IPermissionManager


class RegistrationCog(commands.Cog):
    def __init__(self, bot: commands.Bot, permission_manager: IPermissionManager):
        self.bot = bot
        self.permission_manager = permission_manager

    @app_commands.command(
        name="register", description="Register your Albion Online character."
    )
    @app_commands.describe(character_name="Your Albion Online character name")
    async def register(self, interaction: discord.Interaction, character_name: str):
        await interaction.response.defer(ephemeral=True)

        already_registered = await self.permission_manager.is_character_already_registered(character_name)
        if already_registered:
            await interaction.followup.send(
                f"⚠️ **{character_name}** is already registered to an account.\n"
                "If you believe this is an error, please contact an admin to use `/force-register`.",
                ephemeral=True,
            )
            return

        character_info = await self.permission_manager.get_character_info(character_name)
        if character_info is None:
            await interaction.followup.send(
                f"❌ Could not find a character named **{character_name}**. Please check the name and try again.",
                ephemeral=True,
            )
            return

        embed = _build_character_embed(character_info)
        view = ConfirmRegistrationView(
            discord_user_id=str(interaction.user.id),
            character_name=character_info["name"],
            permission_manager=self.permission_manager,
            force=False,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @app_commands.command(
        name="force-register",
        description="[Admin] Force register an Albion Online character, overwriting any existing registration.",
    )
    @app_commands.describe(
        character_name="The Albion Online character name to force register",
        user="The Discord user to link this character to",
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def force_register(self, interaction: discord.Interaction, character_name: str, user: discord.Member):
        await interaction.response.defer(ephemeral=True)

        character_info = await self.permission_manager.get_character_info(character_name)
        if character_info is None:
            await interaction.followup.send(
                f"❌ Could not find a character named **{character_name}**. Please check the name and try again.",
                ephemeral=True,
            )
            return

        embed = _build_character_embed(character_info, force=True, target_user=user)
        view = ConfirmRegistrationView(
            discord_user_id=str(user.id),
            character_name=character_info["name"],
            permission_manager=self.permission_manager,
            force=True,
            target_user=user,
        )
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    @force_register.error
    async def force_register_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message(
                "❌ You don't have permission to use this command. Please contact an admin.",
                ephemeral=True,
            )


def _build_character_embed(character_info: dict, force: bool = False, target_user: discord.Member | None = None) -> discord.Embed:
    embed = discord.Embed(
        title="⚠️ Force Register — Character Found!" if force else "Character Found!",
        description=(
            f"This will **overwrite** the existing registration and link the character to {target_user.mention}. Are you sure?"
            if force else
            "Is this your character?"
        ),
        color=discord.Color.orange() if force else discord.Color.blue(),
    )
    embed.add_field(name="Name", value=character_info["name"], inline=True)
    embed.add_field(name="Guild", value=character_info.get("guild", "N/A"), inline=True)
    embed.add_field(name="Alliance", value=character_info.get("alliance", "N/A"), inline=True)
    return embed


class ConfirmRegistrationView(discord.ui.View):
    def __init__(
        self,
        discord_user_id: str,
        character_name: str,
        permission_manager: IPermissionManager,
        force: bool = False,
        target_user: discord.Member | None = None,
    ):
        super().__init__(timeout=60)
        self.discord_user_id = discord_user_id
        self.character_name = character_name
        self.permission_manager = permission_manager
        self.force = force
        self.target_user = target_user

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        await self.permission_manager.register_albion_character(
            discord_user_id=self.discord_user_id,
            albion_character_name=self.character_name,
        )
        self.clear_items()
        prefix = "🔧 Force registered" if self.force else "✅ Registered"
        target = self.target_user.mention if self.target_user else "your account"
        await interaction.edit_original_response(
            content=f"{prefix}: **{self.character_name}** has been successfully registered to {target}!",
            embed=None,
            view=self,
        )

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.clear_items()
        await interaction.response.edit_message(
            content="Registration cancelled.",
            embed=None,
            view=self,
        )