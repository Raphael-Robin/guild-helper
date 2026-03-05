import discord
from discord import app_commands
from discord.ext import commands


COMMANDS = {
    "Registration": [
        {
            "name": "/register",
            "usage": "/register character_name: <name>",
            "description": "Register your Albion Online character to your Discord account.",
        },
        {
            "name": "/force-register",
            "usage": "/force-register character_name: <name> user: @mention",
            "description": "[Admin] Force register a character to a user, overwriting any existing registration.",
        },
    ],
    "Economy": [
        {
            "name": "/balance",
            "usage": "/balance [user: @mention]",
            "description": "Display the current and all-time balance of a user. Defaults to yourself if no user is provided.",
        },
        {
            "name": "/remove-balance",
            "usage": "/remove-balance user: @mention [amount: <int>]",
            "description": "[Admin] Remove balance from a user. Omit amount to zero out their balance entirely.",
        },
        {
            "name": "/leaderboard",
            "usage": "/leaderboard",
            "description": "Display a paginated leaderboard of players ranked by current balance.",
        },
        {
            "name": "/leaderboard-alltime",
            "usage": "/leaderboard-alltime",
            "description": "Display a paginated leaderboard of players ranked by all-time balance.",
        },
    ],
    "Loot Splits": [
        {
            "name": "/lootsplit",
            "usage": "/lootsplit item_value: <int> silver: <int> repair_cost: <int>",
            "description": "[Admin] Create a new loot split panel. Use the buttons to add players, edit values, pay out, or reopen the split.",
        },
    ],
    "Logs": [
        {
            "name": "/logs-dump",
            "usage": "/logs-dump",
            "description": "[Admin] Export all economy logs as a CSV file.",
        },
        {
            "name": "/logs-character",
            "usage": "/logs-character character_name: <name>",
            "description": "[Admin] View a paginated economy log history for a specific character.",
        },
    ],
    "Configuration": [
        {
            "name": "/config-view",
            "usage": "/config-view",
            "description": "[Admin] View the current server configuration.",
        },
        {
            "name": "/config-set-guild",
            "usage": "/config-set-guild guild_name: <name>",
            "description": "[Admin] Link this Discord server to an Albion Online guild.",
        },
        {
            "name": "/config-set-roles",
            "usage": "/config-set-roles [admin_role: @role] [member_role: @role] [ally_role: @role] [lootsplit_buyer_role: @role]",
            "description": "[Admin] Configure server roles. All parameters are optional — only provided roles will be updated.",
        },
        {
            "name": "/config-set-lootsplit",
            "usage": "/config-set-lootsplit [guild_tax_percent: <int>] [sale_tax_percent: <int>] [sale_timer_minutes: <int>]",
            "description": "[Admin] Configure lootsplit settings. All parameters are optional.",
        },
    ],
    "Help": [
        {
            "name": "/commands",
            "usage": "/commands",
            "description": "Display this help message.",
        },
    ],
}


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="commands", description="List all available commands and how to use them."
    )
    async def help(self, interaction: discord.Interaction):
        is_admin = (
            isinstance(interaction.user, discord.Member)
            and interaction.user.guild_permissions.administrator
        )

        view = HelpView(is_admin=is_admin)
        embed = _build_help_embed(list(COMMANDS.keys())[0], is_admin=is_admin)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)


def _build_help_embed(category: str, is_admin: bool) -> discord.Embed:
    embed = discord.Embed(
        title=f"Commands — {category}",
        color=discord.Color.blurple(),
    )

    for cmd in COMMANDS[category]:
        is_admin_command = cmd["description"].startswith("[Admin]")

        # Hide admin commands from non-admins
        if is_admin_command and not is_admin:
            continue

        embed.add_field(
            name=cmd["name"],
            value=f"```{cmd['usage']}```{cmd['description']}",
            inline=False,
        )

    if not embed.fields:
        embed.description = "No commands available in this category."

    categories = list(COMMANDS.keys())
    current_index = categories.index(category) + 1
    embed.set_footer(
        text=f"Category {current_index}/{len(categories)}  •  [ ] = optional"
    )

    return embed


class HelpView(discord.ui.View):
    def __init__(self, is_admin: bool):
        super().__init__(timeout=120)
        self.is_admin = is_admin
        self.categories = list(COMMANDS.keys())
        self.current_index = 0
        self._update_buttons()

    def _update_buttons(self):
        self.prev_button.disabled = self.current_index == 0
        self.next_button.disabled = self.current_index == len(self.categories) - 1

    @discord.ui.button(label="◀ Prev", style=discord.ButtonStyle.secondary)
    async def prev_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_index -= 1
        await self._update_help(interaction)

    @discord.ui.button(label="Next ▶", style=discord.ButtonStyle.secondary)
    async def next_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        self.current_index += 1
        await self._update_help(interaction)

    async def _update_help(self, interaction: discord.Interaction):
        self._update_buttons()
        embed = _build_help_embed(
            self.categories[self.current_index], is_admin=self.is_admin
        )
        await interaction.response.edit_message(embed=embed, view=self)
