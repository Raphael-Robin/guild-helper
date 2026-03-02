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
        # Defer while we look up the character
        await interaction.response.defer(ephemeral=True)

        # TODO: replace this with your actual character lookup logic
        character_info = await self._lookup_character(character_name)

        if character_info is None:
            await interaction.followup.send(
                f"❌ Could not find a character named **{character_name}**. Please check the name and try again.",
                ephemeral=True,
            )
            return

        # Send confirmation embed with a Confirm button
        embed = discord.Embed(
            title="Character Found!",
            description="Is this your character?",
            color=discord.Color.blue(),
        )
        embed.add_field(name="Name", value=character_info["name"], inline=True)
        embed.add_field(
            name="Guild", value=character_info.get("guild", "N/A"), inline=True
        )
        embed.add_field(
            name="Alliance", value=character_info.get("alliance", "N/A"), inline=True
        )

        view = ConfirmRegistrationView(
            discord_user_id=str(interaction.user.id),
            character_name=character_info["name"],
            permission_manager=self.permission_manager,
        )

        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def _lookup_character(self, character_name: str) -> dict | None:
        return await self.permission_manager.get_character_info(character_name)


class ConfirmRegistrationView(discord.ui.View):
    def __init__(
        self,
        discord_user_id: str,
        character_name: str,
        permission_manager: IPermissionManager,
    ):
        super().__init__(timeout=60)
        self.discord_user_id = discord_user_id
        self.character_name = character_name
        self.permission_manager = permission_manager

    @discord.ui.button(label="✅ Confirm", style=discord.ButtonStyle.success)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        await self.permission_manager.register_albion_character(
            discord_user_id=self.discord_user_id,
            albion_character_name=self.character_name,
        )
        self.clear_items()
        await interaction.edit_original_response(
            content=f"✅ **{self.character_name}** has been successfully registered to your account!",
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
