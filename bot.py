import re
from collections import defaultdict
from telegram import Update
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    filters, ContextTypes
)

# =============================================
# CONFIGURATION
# =============================================
BOT_TOKEN = "8821935984:AAFBGU2Ge3fVa_qyhrySo3eqw7akgS64Ldw"

# =============================================
# STORAGE (in-memory, resets on bot restart)
# =============================================
link_count = defaultdict(int)   # username -> number of links sent
senders = {}                     # username -> display name
total_links = 0                  # total links across all users

URL_REGEX = re.compile(r'https?://\S+|www\.\S+')

def extract_links(text):
    """Extract all URLs from a text string."""
    return URL_REGEX.findall(text or "")


# =============================================
# HANDLERS
# =============================================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all non-command messages in the group."""
    global total_links

    msg = update.message
    if not msg:
        return

    user = msg.from_user
    username = user.username or str(user.id)
    display = f"@{username}" if user.username else user.full_name
    text = msg.text or msg.caption or ""

    # --- Handle video with "ad" or "add" caption ---
    if msg.video:
        lower = text.lower().strip()
        if lower in ("ad", "add"):
            if username in senders:
                del senders[username]
                link_count.pop(username, None)
                await msg.reply_text(f"✅ {display} has been removed from the sender list.")
            else:
                await msg.reply_text(f"ℹ️ {display} was not in the sender list.")
        return

    # --- Handle messages with links ---
    links = extract_links(text)
    if not links:
        return

    # Delete the original message
    try:
        await msg.delete()
    except Exception as e:
        print(f"[WARN] Could not delete message: {e}")
        # Bot may not have delete permissions

    # Update stats
    total_links += len(links)
    link_count[username] += len(links)
    senders[username] = display

    # Repost the link(s) with attribution
    link_text = "\n".join(links)
    await context.bot.send_message(
        chat_id=msg.chat_id,
        text=(
            f"🔗 Link shared by {display}:\n"
            f"{link_text}\n\n"
            f"📊 Total links in this group: {total_links}"
        ),
        disable_web_page_preview=False
    )


async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/list — Show all users who have sent links and their counts."""
    if not senders:
        await update.message.reply_text("📭 No one has sent a link yet.")
        return

    lines = [
        f"{name} — {link_count[u]} link(s)"
        for u, name in senders.items()
    ]
    text = (
        f"📋 Link Senders ({len(senders)} users | {total_links} total links):\n\n"
        + "\n".join(lines)
    )
    await update.message.reply_text(text)


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/stats — Show total link count."""
    await update.message.reply_text(
        f"📊 Total links shared in this group: *{total_links}*",
        parse_mode="Markdown"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/help — Show usage instructions."""
    await update.message.reply_text(
        "🤖 *Link Manager Bot*\n\n"
        "📌 *How it works:*\n"
        "• Send a link → Bot deletes it and reposts it with your name\n"
        "• Send a video with caption `ad` or `add` → Bot removes you from the list\n\n"
        "📌 *Commands:*\n"
        "/list — Show all link senders\n"
        "/stats — Show total link count\n"
        "/help — Show this message",
        parse_mode="Markdown"
    )


# =============================================
# MAIN
# =============================================

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("help", help_command))

    # Message handler (all non-command messages)
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))

    print("✅ Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
