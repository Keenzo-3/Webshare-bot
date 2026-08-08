#!/usr/bin/env python3
"""
Webshare.io Account Generator - Telegram Bot
"""

import os
import sys
import time
import asyncio
import threading
from io import BytesIO
from datetime import datetime

from dotenv import load_dotenv
load_dotenv()

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

from core.account import create_webshare_account
from core.utils import (
    unique_email,
    generate_password,
    get_accounts,
    get_proxies,
    count_accounts,
    count_proxies,
    format_large_number,
    log_message
)

from flask import Flask

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = []

if not BOT_TOKEN:
    log_message("BOT_TOKEN not set!", "CRITICAL")
    sys.exit(1)

admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
    except ValueError:
        log_message("Invalid ADMIN_IDS", "ERROR")
        sys.exit(1)

if not ADMIN_IDS:
    log_message("ADMIN_IDS not set!", "CRITICAL")
    sys.exit(1)

# ===== FLASK APP =====
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    return {
        "status": "running",
        "accounts": count_accounts(),
        "proxies": count_proxies()
    }

@flask_app.route('/health')
def health():
    return "OK", 200

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ===== BOT HANDLERS =====

async def is_authorized(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update.effective_user.id):
        await update.message.reply_text("🔒 Private bot. Access denied.")
        return
    
    accounts = count_accounts()
    proxies = count_proxies()
    
    keyboard = [
        [
            InlineKeyboardButton("🎲 Auto Generate", callback_data="mode_auto"),
            InlineKeyboardButton("📋 Custom", callback_data="mode_manual")
        ],
        [
            InlineKeyboardButton("📊 Stats", callback_data="stats"),
            InlineKeyboardButton("🗑 Clear", callback_data="clear")
        ],
        [
            InlineKeyboardButton("📥 Accounts", callback_data="dl_accounts"),
            InlineKeyboardButton("📥 Proxies", callback_data="dl_proxies")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🌟 **Webshare Generator**\n\n"
        f"📧 Accounts: `{accounts}`\n"
        f"🌐 Proxies: `{proxies}`\n\n"
        "Select action:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update.effective_user.id):
        return
    await update.message.reply_text(
        f"📊 **Stats**\n📧 `{count_accounts()}` accounts\n🌐 `{count_proxies()}` proxies",
        parse_mode="Markdown"
    )

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update.effective_user.id):
        return
    data = get_accounts()
    if data:
        await update.message.reply_document(
            document=BytesIO(data.encode()),
            filename=f"accounts_{datetime.now().strftime('%Y%m%d')}.txt",
            caption=f"📧 {count_accounts()} accounts"
        )
    else:
        await update.message.reply_text("❌ No accounts yet!")

async def proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update.effective_user.id):
        return
    data = get_proxies()
    if data:
        await update.message.reply_document(
            document=BytesIO(data.encode()),
            filename=f"proxies_{datetime.now().strftime('%Y%m%d')}.txt",
            caption=f"🌐 {count_proxies()} proxies"
        )
    else:
        await update.message.reply_text("❌ No proxies yet!")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update.effective_user.id):
        return
    try:
        if os.path.exists("data/accounts.txt"):
            os.remove("data/accounts.txt")
        if os.path.exists("data/proxy.txt"):
            os.remove("data/proxy.txt")
        await update.message.reply_text("✅ Cleared!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update.effective_user.id):
        return
    context.user_data.clear()
    await update.message.reply_text("❌ Cancelled. /start to begin.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(query.from_user.id):
        return
    
    data = query.data
    
    if data == "mode_auto":
        context.user_data["mode"] = "auto"
        await query.edit_message_text(
            "🎲 **Auto Mode**\nSend number (1-5):\n/cancel to abort",
            parse_mode="Markdown"
        )
    elif data == "mode_manual":
        context.user_data["mode"] = "manual"
        await query.edit_message_text(
            "📋 **Manual Mode**\nSend `email:password`\n/cancel to abort",
            parse_mode="Markdown"
        )
    elif data == "stats":
        await query.edit_message_text(
            f"📊 Accounts: `{count_accounts()}`\n🌐 Proxies: `{count_proxies()}`",
            parse_mode="Markdown"
        )
    elif data == "dl_accounts":
        data = get_accounts()
        if data:
            await query.message.reply_document(
                document=BytesIO(data.encode()),
                filename="accounts.txt",
                caption=f"📧 {count_accounts()} accounts"
            )
        else:
            await query.edit_message_text("❌ No accounts!")
    elif data == "dl_proxies":
        data = get_proxies()
        if data:
            await query.message.reply_document(
                document=BytesIO(data.encode()),
                filename="proxies.txt",
                caption=f"🌐 {count_proxies()} proxies"
            )
        else:
            await query.edit_message_text("❌ No proxies!")
    elif data == "clear":
        try:
            if os.path.exists("data/accounts.txt"):
                os.remove("data/accounts.txt")
            if os.path.exists("data/proxy.txt"):
                os.remove("data/proxy.txt")
            await query.edit_message_text("✅ Cleared!")
        except Exception as e:
            await query.edit_message_text(f"❌ {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update.effective_user.id):
        return
    
    text = update.message.text.strip()
    mode = context.user_data.get("mode")
    
    if not mode:
        await start(update, context)
        return
    
    if mode == "auto":
        try:
            count = int(text)
            if count < 1 or count > 5:
                await update.message.reply_text("❌ 1-5 only!")
                return
        except ValueError:
            await update.message.reply_text("❌ Invalid number!")
            return
        
        context.user_data.clear()
        msg = await update.message.reply_text(f"🚀 Creating {count} accounts...")
        
        # RUN IN BACKGROUND THREAD WITH NEW EVENT LOOP
        threading.Thread(
            target=run_auto_mode,
            args=(count, update.effective_user.id, msg.message_id),
            daemon=True
        ).start()
    
    elif mode == "manual":
        if ":" not in text:
            await update.message.reply_text("❌ Format: email:password")
            return
        
        email, password = text.split(":", 1)
        email, password = email.strip(), password.strip()
        
        if "@" not in email or len(password) < 8:
            await update.message.reply_text("❌ Invalid email or short password (min 8)")
            return
        
        context.user_data.clear()
        msg = await update.message.reply_text(f"🔧 Creating...\n📧 `{email}`", parse_mode="Markdown")
        
        threading.Thread(
            target=run_single_account,
            args=(email, password, update.effective_user.id, msg.message_id),
            daemon=True
        ).start()

def run_auto_mode(count, user_id, message_id):
    """Background auto mode with OWN event loop"""
    import telegram
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _run():
        bot = telegram.Bot(token=BOT_TOKEN)
        results = []
        
        for i in range(count):
            email = unique_email()
            password = generate_password()
            
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=message_id,
                    text=f"⏳ {i+1}/{count}...\n📧 `{email}`",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            result = create_webshare_account(email, password)
            results.append(result)
            
            status = "✅" if result["success"] else "❌"
            detail = f"Proxies: {result['proxies']}" if result["success"] else result.get("error", "Failed")
            
            try:
                await bot.send_message(
                    chat_id=user_id,
                    text=f"{status} **{i+1}/{count}**\n📧 `{email}`\n🔑 `{password}`\n{detail}",
                    parse_mode="Markdown"
                )
            except:
                pass
            
            if i < count - 1:
                time.sleep(3)
        
        success = sum(1 for r in results if r["success"])
        total_proxies = sum(r["proxies"] for r in results)
        
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=f"✅ Done!\n📧 `{success}/{count}` accounts\n🌐 `{total_proxies}` proxies",
                parse_mode="Markdown"
            )
        except:
            pass
    
    loop.run_until_complete(_run())
    loop.close()

def run_single_account(email, password, user_id, message_id):
    """Background single account with OWN event loop"""
    import telegram
    import asyncio
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    async def _run():
        bot = telegram.Bot(token=BOT_TOKEN)
        result = create_webshare_account(email, password)
        
        if result["success"]:
            text = f"✅ **Done!**\n📧 `{email}`\n🔑 `{password}`\n🌐 Proxies: `{result['proxies']}`"
        else:
            text = f"❌ **Failed**\n📧 `{email}`\nError: `{result.get('error')}`"
        
        try:
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=text,
                parse_mode="Markdown"
            )
        except:
            pass
    
    loop.run_until_complete(_run())
    loop.close()

# ===== MAIN =====
def main():
    os.makedirs("data", exist_ok=True)
    log_message("Starting Webshare Bot...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("accounts", accounts_command))
    app.add_handler(CommandHandler("proxies", proxies_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    log_message(f"Bot running with {len(ADMIN_IDS)} admin(s)")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    log_message("Flask started")
    main()
