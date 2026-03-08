import discord
from src.Interfaces import IConfigurationManager


async def is_admin(
    interaction: discord.Interaction,
    configuration_manager: IConfigurationManager,
) -> bool:
    """Discord administrator OR configured admin role."""
    if not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    config = await configuration_manager.get_config(str(interaction.guild_id))
    if not config.admin_role_id:
        return False
    return any(str(r.id) == config.admin_role_id for r in interaction.user.roles)


async def is_lootsplit_manager(
    interaction: discord.Interaction,
    configuration_manager: IConfigurationManager,
) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    if await is_admin(interaction, configuration_manager):
        return True
    config = await configuration_manager.get_config(str(interaction.guild_id))
    if not config.lootsplit_manager_id:
        return False
    return any(str(r.id) == config.lootsplit_manager_id for r in interaction.user.roles)


async def is_balance_manager(
    interaction: discord.Interaction,
    configuration_manager: IConfigurationManager,
) -> bool:
    if not isinstance(interaction.user, discord.Member):
        return False
    if await is_admin(interaction, configuration_manager):
        return True
    config = await configuration_manager.get_config(str(interaction.guild_id))
    if not config.balance_manager_id:
        return False
    return any(str(r.id) == config.balance_manager_id for r in interaction.user.roles)


async def is_member_or_ally(
    interaction: discord.Interaction,
    configuration_manager: IConfigurationManager,
) -> bool:
    """Member role, ally role, admin role, or Discord administrator."""
    if not isinstance(interaction.user, discord.Member):
        return False
    if await is_admin(interaction, configuration_manager):
        return True
    config = await configuration_manager.get_config(str(interaction.guild_id))
    user_role_ids = {str(r.id) for r in interaction.user.roles}
    allowed = {config.admin_role_id, config.member_role_id, config.ally_role_id}
    allowed.discard(None)
    # If no roles configured at all, allow everyone
    if not allowed:
        return True
    return bool(user_role_ids & allowed)


async def can_join_sale(
    interaction: discord.Interaction,
    configuration_manager: IConfigurationManager,
) -> bool:
    """Buyer role, admin role, or Discord administrator."""
    if not isinstance(interaction.user, discord.Member):
        return False
    if interaction.user.guild_permissions.administrator:
        return True
    config = await configuration_manager.get_config(str(interaction.guild_id))
    if not config.lootsplit_buyer_role_id:
        return True  # No buyer role configured — allow everyone
    user_role_ids = {str(r.id) for r in interaction.user.roles}
    allowed = {config.admin_role_id, config.lootsplit_buyer_role_id}
    allowed.discard(None)
    return bool(user_role_ids & allowed)


async def send_permission_error(interaction: discord.Interaction) -> None:
    msg = "❌ You don't have permission to use this command."
    if interaction.response.is_done():
        await interaction.followup.send(msg, ephemeral=True)
    else:
        await interaction.response.send_message(msg, ephemeral=True)
