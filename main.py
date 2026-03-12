import asyncio
import random
import time
import signal
from datetime import datetime
import pytz
from telethon import TelegramClient, events, functions, types
from telethon.errors import FloodWaitError
from telethon.tl.functions.account import UpdateProfileRequest
from deep_translator import GoogleTranslator
from langdetect import detect, DetectorFactory

# Stable results for langdetect
DetectorFactory.seed = 0

import config

# Configuration
API_ID = config.API_ID
API_HASH = config.API_HASH
SESSION_NAME = "userbot_session"
UZ_TZ = pytz.timezone(config.TIMEZONE)

client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

# Global Variables
START_TIME = time.time()
current_name = None
original_base_name = None
REPLIES_SENT = {} # {user_id: last_reply_timestamp}
LAST_OUTGOING_TIME = {} # {chat_id: timestamp}

def to_bold(text):
    """Converts a string to bold mathematical alphanumeric characters."""
    normal = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789:& "
    bold   = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵:& "
    return text.translate(str.maketrans(normal, bold))

def get_uptime():
    """Returns the bot's uptime in a readable format."""
    uptime_seconds = int(time.time() - START_TIME)
    days, remainder = divmod(uptime_seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    parts = []
    if days > 0: parts.append(f"{days}d")
    if hours > 0: parts.append(f"{hours}h")
    if minutes > 0: parts.append(f"{minutes}m")
    parts.append(f"{seconds}s")
    return " ".join(parts)

async def restore_name():
    """Restores the profile name to original on exit."""
    global original_base_name
    if original_base_name:
        try:
            print(f"Restoring profile name to: {original_base_name}")
            await client(UpdateProfileRequest(
                first_name=original_base_name,
                last_name=""
            ))
        except Exception as e:
            print(f"Failed to restore name: {e}")

@client.on(events.NewMessage(pattern=r"\.ping", outgoing=True))
async def ping_handler(event):
    start = time.time()
    msg = await event.edit("<code>Pinging...</code>")
    end = time.time()
    latency = round((end - start) * 1000)
    await msg.edit(config.PING_MESSAGE.format(latency=latency), parse_mode="html")

@client.on(events.NewMessage(pattern=r"\.alive", outgoing=True))
async def alive_handler(event):
    start = time.time()
    msg = await event.edit("<code>Checking system...</code>")
    end = time.time()
    latency = round((end - start) * 1000)
    
    me = await client.get_me()
    full_name = f"{me.first_name or ''} {me.last_name or ''}".strip()
    
    await msg.edit(
        config.ALIVE_MESSAGE.format(
            user=full_name,
            uptime=get_uptime(),
            latency=latency
        ),
        parse_mode="html"
    )

@client.on(events.NewMessage(pattern=r"\.help", outgoing=True))
async def help_handler(event):
    await event.edit(config.HELP_MESSAGE, parse_mode="html")

@client.on(events.NewMessage(pattern=r"^\.(tr|)(\s*)$", outgoing=True))
async def translate_interactive_handler(event):
    """
    Triggers on '.tr' or '.' (with or without space).
    Translates the replied xabar, sets it as a draft, and deletes the trigger.
    """
    print(f"DEBUG: Translate handler triggered by: '{event.text}'")
    if not event.is_reply:
        return

    reply_msg = await event.get_reply_message()
    if not reply_msg or not reply_msg.text:
        return

    try:
        # Detect language and translate
        lang = detect(reply_msg.text)
        target = 'uz' if lang != 'uz' else 'en'
        translated = GoogleTranslator(source='auto', target=target).translate(reply_msg.text)
        
        print(f"Translating to {target}: '{translated[:30]}...' (Setting as draft)")
        
        # 1. Update Draft (so it appears in the input area)
        print(f"DEBUG: Saving draft to {event.peer_id}: {translated[:20]}...")
        await client(functions.messages.SaveDraftRequest(
            peer=event.peer_id,
            message=translated,
            reply_to_msg_id=reply_msg.id
        ))
        
        # Small sleep to give the client time to sync
        await asyncio.sleep(0.3)
        
        # 2. Delete the trigger message
        await event.delete()
        print("DEBUG: Draft set and trigger deleted.")
        
    except Exception as e:
        print(f"Interactive translation error: {e}")

@client.on(events.NewMessage(pattern=r"^\.b\s+$", outgoing=True))
async def bold_draft_handler(event):
    """
    Triggers on '.b ' (space).
    Bolds the current draft text so it can be sent without 'edited' tag.
    """
    try:
        # Get the current draft
        result = await client(functions.messages.GetDraftRequest(peer=event.peer_id))
        if isinstance(result, types.DraftMessage) and result.message:
            bold_text = to_bold(result.message)
            
            # Update Draft
            await client(functions.messages.SaveDraftRequest(
                peer=event.peer_id,
                message=bold_text
            ))
        
        # Delete the trigger
        await event.delete()
    except Exception as e:
        print(f"Bold draft error: {e}")

@client.on(events.NewMessage(incoming=True))
async def incoming_handler(event):
    if event.is_private:
        sender = await event.get_sender()
        if not sender or sender.bot: # Ignore bots to prevent loops
            return
            
        # 1. Translation RU -> UZ (Passive)
        if config.TRANSLATE_RU_TO_UZ and event.text:
            try:
                # Basic detection
                lang = detect(event.text)
                if lang == 'ru':
                    translated = GoogleTranslator(source='ru', target='uz').translate(event.text)
                    await event.reply(f"<i>{translated}</i>", parse_mode="html")
            except Exception as e:
                print(f"Translation error: {e}")

        # 2. Auto-reply (Every 40 minutes + Suppression if active)
        if config.AUTO_REPLY_ENABLED:
            chat_id = event.chat_id
            user_id = event.sender_id
            now = time.time()
            
            # Suppression: If we sent a message to this chat in the last 5 minutes, SKIP auto-reply
            if (now - LAST_OUTGOING_TIME.get(chat_id, 0)) < 300:
                return
                
            last_reply = REPLIES_SENT.get(user_id, 0)
            if (now - last_reply) >= config.AUTO_REPLY_INTERVAL:
                await event.reply(config.AUTO_REPLY_TEXT)
                REPLIES_SENT[user_id] = int(now)

@client.on(events.NewMessage(outgoing=True))
async def outgoing_handler(event):
    # Track activity to suppress auto-replies
    LAST_OUTGOING_TIME[event.chat_id] = int(time.time())
    
    # Skip if it's a command
    if event.text.startswith('.'):
        return

    # 3. Bold Outgoing
    if config.BOLD_OUTGOING and event.text:
        # Use the to_bold function already defined
        bold_text = to_bold(event.text)
        if bold_text != event.text:
            try:
                await event.edit(bold_text)
            except Exception as e:
                print(f"Bold edit error: {e}")

async def update_profile_loop():
    global current_name, original_base_name
    
    print("Profile update loop started.")
    me = await client.get_me()
    base_name = config.DEFAULT_FIRST_NAME if not me.first_name else me.first_name
    
    # Try to clean base name if it already has time
    if " " in base_name:
        parts = base_name.split()
        if ":" in parts[-1] and len(parts[-1]) <= 5: # likely a time
            base_name = " ".join(parts[:-1])
    
    original_base_name = base_name

    while True:
        try:
            time_now = datetime.now(UZ_TZ).strftime("%H:%M")
            new_name = to_bold(f"{base_name} {time_now}")
            
            # Only update if the string has actually changed
            if new_name != current_name:
                print(f"Updating profile name to: {new_name}")
                await client(UpdateProfileRequest(
                    first_name=new_name,
                    last_name=""
                ))
                current_name = new_name
            
            # Randomized sleep to look more human 
            sleep_time = config.UPDATE_INTERVAL + random.uniform(1, 15)
            await asyncio.sleep(sleep_time)
            
        except FloodWaitError as e:
            print(f"FloodWait! Sleeping for {e.seconds} seconds.")
            await asyncio.sleep(e.seconds)
        except Exception as e:
            print(f"Error in profile loop: {e}")
            await asyncio.sleep(60)

async def main():
    await client.start()
    print("Userbot started successfully.")
    
    # Run the profile update loop in the background
    asyncio.create_task(update_profile_loop())
    
    try:
        # Wait for the client to disconnect
        await client.run_until_disconnected()
    finally:
        # Restore name on exit
        await restore_name()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot stopped by user.")
