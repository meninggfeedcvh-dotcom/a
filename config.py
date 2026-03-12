import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Constants
API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")

# User Settings
DEFAULT_FIRST_NAME = "Admin"
TIMEZONE = "Asia/Tashkent"
UPDATE_INTERVAL = 60  # seconds

# UI Templates
ALIVE_MESSAGE = """
<b>⚡ Userbot is Active!</b>
━━━━━━━━━━━━━━━━━━
<b>👤 User:</b> {user}
<b>⏱ Uptime:</b> {uptime}
<b>📡 Latency:</b> {latency}ms
━━━━━━━━━━━━━━━━━━
<i>Powered by Python & Telethon</i>
"""

PING_MESSAGE = "<b>🏓 Pong!</b> <code>{latency}ms</code>"

HELP_MESSAGE = """
<b>🛠 Userbot Commands:</b>
━━━━━━━━━━━━━━━━━━
• <code>.alive</code> - Check bot status
• <code>.ping</code> - Measure response time
• <code>.help</code> - Show this menu
━━━━━━━━━━━━━━━━━━
"""

# Feature Toggles
AUTO_REPLY_ENABLED = True
AUTO_REPLY_TEXT = "Xozir bandman, bo'shaganimda yozaman!"
AUTO_REPLY_INTERVAL = 3600  # 1 hour in seconds

TRANSLATE_RU_TO_UZ = True
BOLD_OUTGOING = True
