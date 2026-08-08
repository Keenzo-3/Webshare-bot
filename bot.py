#!/usr/bin/env python3
"""
Webshare.io Account Generator - Telegram Bot
Created for Render Deployment
"""

import os
import sys
import time
import asyncio
import threading
from io import BytesIO
from datetime import datetime

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# Telegram imports
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

# Core modules
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

# Flask for health checks
from flask import Flask

# ===== CONFIGURATION =====
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_IDS = []

if not BOT_TOKEN:
    log_message("BOT_TOKEN not set! Check environment variables.", "CRITICAL")
    sys.exit(1)

admin_ids_str = os.getenv("ADMIN_IDS", "")
if admin_ids_str:
    try:
        ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(",") if id.strip()]
    except ValueError:
        log_message("Invalid ADMIN_IDS format", "ERROR")
        sys.exit(1)

if not ADMIN_IDS:
    log_message("ADMIN_IDS not set! Check environment variables.", "CRITICAL")
    sys.exit(1)

# ===== FLASK APP (For Render Health Checks) =====
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    """Health check endpoint"""
    return {
        "status": "running",
        "bot": "webshare-generator",
        "accounts": count_accounts(),
        "proxies": count_proxies(),
        "timestamp": datetime.now().isoformat()
    }

@flask_app.route('/health')
def health():
    """Render health check"""
    return "OK", 200

def run_flask():
    """Run Flask in background"""
    port = int(os.environ.get("PORT", 10000))
    flask_app.run(host='0.0.0.0', port=port, debug=False)

# ===== TELEGRAM BOT HANDLERS =====

async def is_authorized(user_id: int) -> bool:
    """Check if user is authorized"""
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start command handler"""
    if not await is_authorized(update.effective_user.id):
        await update.message.reply_text("🔒 This bot is private. Access denied.")
        return
    
    accounts = count_accounts()
    proxies = count_proxies()
    
    keyboard = [
        [
            InlineKeyboardButton("🎲 Auto Generate", callback_data="mode_auto"),
            InlineKeyboardButton("📋 Custom", callback_data="mode_manual")
        ],
        [
            InlineKeyboardButton("📊 Statistics", callback_data="stats"),
            InlineKeyboardButton("🗑 Clear Data", callback_data="clear")
        ],
        [
            InlineKeyboardButton("📥 Download Accounts", callback_data="dl_accounts"),
            InlineKeyboardButton("📥 Download Proxies", callback_data="dl_proxies")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "🌟 **Webshare Account Generator**\n\n"
        f"📧 Accounts: `{format_large_number(accounts)}`\n"
        f"🌐 Proxies: `{format_large_number(proxies)}`\n\n"
        "Select an action below:"
    )
    
    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Statistics command"""
    if not await is_authorized(update.effective_user.id):
        return
    
    accounts = count_accounts()
    proxies = count_proxies()
    
    stats_text = (
        "📊 **Bot Statistics**\n\n"
        f"📧 Accounts: `{format_large_number(accounts)}`\n"
        f"🌐 Proxies: `{format_large_number(proxies)}`\n"
        f"🕐 Uptime: `Running...`\n\n"
        "Use buttons or commands to interact."
    )
    
    await update.message.reply_text(stats_text, parse_mode="Markdown")

async def accounts_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send accounts file"""
    if not await is_authorized(update.effective_user.id):
        return
    
    accounts_data = get_accounts()
    
    if accounts_data:
        file_bytes = BytesIO(accounts_data.encode())
        await update.message.reply_document(
            document=file_bytes,
            filename=f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            caption=f"📧 {count_accounts()} accounts"
        )
    else:
        await update.message.reply_text("❌ No accounts generated yet!")

async def proxies_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send proxies file"""
    if not await is_authorized(update.effective_user.id):
        return
    
    proxies_data = get_proxies()
    
    if proxies_data:
        file_bytes = BytesIO(proxies_data.encode())
        await update.message.reply_document(
            document=file_bytes,
            filename=f"proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            caption=f"🌐 {count_proxies()} proxies"
        )
    else:
        await update.message.reply_text("❌ No proxies generated yet!")

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Clear all data"""
    if not await is_authorized(update.effective_user.id):
        return
    
    try:
        if os.path.exists("data/accounts.txt"):
            os.remove("data/accounts.txt")
        if os.path.exists("data/proxy.txt"):
            os.remove("data/proxy.txt")
        await update.message.reply_text("✅ All data cleared successfully!")
    except Exception as e:
        await update.message.reply_text(f"❌ Error clearing data: {e}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Help command"""
    if not await is_authorized(update.effective_user.id):
        return
    
    help_text = (
        "🤖 **Bot Commands**\n\n"
        "/start - Main menu\n"
        "/stats - View statistics\n"
        "/accounts - Download accounts file\n"
        "/proxies - Download proxies file\n"
        "/clear - Clear all data\n"
        "/cancel - Cancel current operation\n"
        "/help - Show this help\n\n"
        "**How to use:**\n"
        "1. Use /start to see menu\n"
        "2. Choose Auto or Manual mode\n"
        "3. Follow prompts\n\n"
        "**Note:** Bot creates fake emails for registration."
    )
    
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel current operation"""
    if not await is_authorized(update.effective_user.id):
        return
    
    context.user_data.clear()
    await update.message.reply_text("❌ Operation cancelled. /start to begin again.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all button callbacks"""
    query = update.callback_query
    await query.answer()
    
    if not await is_authorized(query.from_user.id):
        await query.edit_message_text("🔒 Unauthorized!")
        return
    
    data = query.data
    
    if data == "mode_auto":
        context.user_data["mode"] = "auto"
        await query.edit_message_text(
            "🎲 **Auto Generate Mode**\n\n"
            "Send the number of accounts to create (1-5):\n\n"
            "Example: `3`\n\n"
            "/cancel to abort",
            parse_mode="Markdown"
        )
    
    elif data == "mode_manual":
        context.user_data["mode"] = "manual"
        await query.edit_message_text(
            "📋 **Custom Account Mode**\n\n"
            "Send account details in this format:\n"
            "`email@outlook.com:Password123x`\n\n"
            "Example:\n"
            "`myproxy@outlook.com:MyPass123x`\n\n"
            "/cancel to abort",
            parse_mode="Markdown"
        )
    
    elif data == "stats":
        accounts = count_accounts()
        proxies = count_proxies()
        await query.edit_message_text(
            f"📊 **Statistics**\n\n"
            f"📧 Accounts: `{format_large_number(accounts)}`\n"
            f"🌐 Proxies: `{format_large_number(proxies)}`",
            parse_mode="Markdown"
        )
    
    elif data == "dl_accounts":
        accounts_data = get_accounts()
        if accounts_data:
            file_bytes = BytesIO(accounts_data.encode())
            await query.message.reply_document(
                document=file_bytes,
                filename=f"accounts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                caption=f"📧 {count_accounts()} accounts"
            )
        else:
            await query.edit_message_text("❌ No accounts yet!")
    
    elif data == "dl_proxies":
        proxies_data = get_proxies()
        if proxies_data:
            file_bytes = BytesIO(proxies_data.encode())
            await query.message.reply_document(
                document=file_bytes,
                filename=f"proxies_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                caption=f"🌐 {count_proxies()} proxies"
            )
        else:
            await query.edit_message_text("❌ No proxies yet!")
    
    elif data == "clear":
        try:
            if os.path.exists("data/accounts.txt"):
                os.remove("data/accounts.txt")
            if os.path.exists("data/proxy.txt"):
                os.remove("data/proxy.txt")
            await query.edit_message_text("✅ All data cleared!")
        except Exception as e:
            await query.edit_message_text(f"❌ Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages"""
    if not await is_authorized(update.effective_user.id):
        return
    
    user_id = update.effective_user.id
    text = update.message.text.strip()
    mode = context.user_data.get("mode")
    
    if not mode:
        await start(update, context)
        return
    
    if mode == "auto":
        # Parse count
        try:
            count = int(text)
            if count < 1 or count > 5:
                await update.message.reply_text("❌ Please enter 1-5 only!")
                return
        except ValueError:
            await update.message.reply_text("❌ Invalid number! Enter 1-5.")
            return
        
        # Clear mode
        context.user_data.clear()
        
        # Start progress message
        progress_msg = await update.message.reply_text(
            f"🚀 **Creating {count} account(s)...**\n\n"
            "⏳ Initializing...",
            parse_mode="Markdown"
        )
        
        # Run in background thread
        thread = threading.Thread(
            target=process_auto_mode,
            args=(count, user_id, progress_msg.message_id, context)
        )
        thread.daemon = True
        thread.start()
    
    elif mode == "manual":
        # Parse email:password
        if ":" not in text:
            await update.message.reply_text("❌ Format: `email:password`")
            return
        
        parts = text.split(":", 1)
        email = parts[0].strip()
        password = parts[1].strip()
        
        # Validate
        if "@" not in email:
            await update.message.reply_text("❌ Invalid email address!")
            return
        if len(password) < 8:
            await update.message.reply_text("❌ Password must be at least 8 characters!")
            return
        
        # Clear mode
        context.user_data.clear()
        
        # Start progress
        progress_msg = await update.message.reply_text(
            f"🔧 **Creating account...**\n\n"
            f"📧 `{email}`\n"
            "⏳ Processing...",
            parse_mode="Markdown"
        )
        
        # Run in background thread
        thread = threading.Thread(
            target=process_single_account,
            args=(email, password, user_id, progress_msg.message_id, context)
        )
        thread.daemon = True
        thread.start()

def process_auto_mode(count, user_id, message_id, context):
    """Background processing for auto mode"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    results = []
    
    for i in range(count):
        email = unique_email()
        password = generate_password()
        
        # Update progress
        loop.run_until_complete(
            context.bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=(
                    f"⏳ **Creating account {i+1}/{count}...**\n\n"
                    f"📧 `{email}`\n"
                    f"🔄 Processing..."
                ),
                parse_mode="Markdown"
            )
        )
        
        # Create account
        result = create_webshare_account(email, password)
        results.append(result)
        
        # Send individual result
        if result["success"]:
            status = "✅"
            detail = f"Proxies: {result['proxies']}"
        else:
            status = "❌"
            detail = result.get("error", "Unknown error")
        
        loop.run_until_complete(
            context.bot.send_message(
                chat_id=user_id,
                text=(
                    f"{status} **Account {i+1}/{count}**\n\n"
                    f"📧 `{email}`\n"
                    f"🔑 `{password}`\n"
                    f"📊 {detail}"
                ),
                parse_mode="Markdown"
            )
        )
        
        # Delay between accounts
        if i < count - 1:
            time.sleep(3)
    
    # Final summary
    success_count = sum(1 for r in results if r["success"])
    total_proxies = sum(r["proxies"] for r in results if r["success"])
    
    loop.run_until_complete(
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=(
                "✅ **All Done!**\n\n"
                f"📧 Success: `{success_count}/{count}` accounts\n"
                f"🌐 Proxies: `{total_proxies}` total\n\n"
                "Use /accounts or /proxies to download files."
            ),
            parse_mode="Markdown"
        )
    )
    
    loop.close()

def process_single_account(email, password, user_id, message_id, context):
    """Background processing for single custom account"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # Create account
    result = create_webshare_account(email, password)
    
    # Update message
    if result["success"]:
        text = (
            "✅ **Account Created!**\n\n"
            f"📧 `{email}`\n"
            f"🔑 `{password}`\n"
            f"🌐 Proxies: `{result['proxies']}`"
        )
    else:
        text = (
            f"❌ **Failed**\n\n"
            f"📧 `{email}`\n"
            f"Error: `{result.get('error', 'Unknown')}`"
        )
    
    loop.run_until_complete(
        context.bot.edit_message_text(
            chat_id=user_id,
            message_id=message_id,
            text=text,
            parse_mode="Markdown"
        )
    )
    
    loop.close()

# ===== MAIN FUNCTION =====
def main():
    """Start the Telegram bot"""
    
    # Create data directory
    os.makedirs("data", exist_ok=True)
    
    log_message("Starting Webshare Bot...")
    
    # Build application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("accounts", accounts_command))
    app.add_handler(CommandHandler("proxies", proxies_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    
    # Add callback handler for buttons
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Add message handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Log startup
    log_message(f"Bot started with {len(ADMIN_IDS)} admin(s)")
    
    # Start bot
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    # Start Flask in background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    log_message("Flask health check server started")
    
    # Start Telegram bot
    main()
