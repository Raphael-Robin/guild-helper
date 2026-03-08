import logging

# 1. Global config (catches everything else, like library warnings)
logging.basicConfig(
    level=logging.CRITICAL, # Set global higher so you don't see every library 'INFO'
    format="%(asctime)s [%(levelname)s] %(message)s",
)

# 2. Your specific logger
logger = logging.getLogger("guild-helper")
logger.setLevel(logging.INFO) # Use 20 (INFO) or 10 (DEBUG)
logger.propagate = False      # Don't send logs "up" to the basicConfig handler

# 3. Dedicated handler for ONLY this logger
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s [GUILD-HELPER] %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)

# 1. Target the discord library's specific logger
discord_logger = logging.getLogger("discord")
discord_logger.setLevel(logging.CRITICAL)

# 2. Target the specific gateway logger (sometimes needed for the shard info)
logging.getLogger("discord.gateway").setLevel(logging.WARNING)