import re
from datetime import timedelta
from collections import defaultdict
from telegram import Update, ChatPermissions, BotCommand
from telegram.ext import (
    Application, MessageHandler, CommandHandler,
    filters, ContextTypes
)

BOT_TOKEN = "8821935984:AAFBGU2Ge3fVa_qyhrySo3eqw7akgS64Ldw"

# Storage
link_count = defaultdict(int)
senders = {}
total_links = 0
user_id_map = {}
tracked_messages = []

URL_REGEX = re.compile(r'https?://\S+|www\.\S+')

def extract_links(text):
    return URL_REGEX.findall(text or "")

def parse_duration(s):
    s = s.lower().strip()
    try:
        if s.endswith("d"): return timedelta(days=int(s[:-1]))
        if s.endswith("h"): return timedelta(hours=int(s[:-1]))
        if s.endswith("m"): return timedelta(minutes=int(s[:-1]))
    except ValueError:
        pass
    return None

async def is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(
            update.effective_chat.id,
            update.effective_user.id
        )
        print(f"[DEBUG] @{update.effective_user.username} status: {member.status}")
        return member.status in ("administrator", "creator")
    except Exception as e:
        print(f"[ERROR] is_admin failed: {e}")
        return False


# ── Track every message ──────────────────────────────────────────────────────

async def track_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user:
        if user.username:
            user_id_map[user.username.lower()] = user.id
        user_id_map[str(user.id)] = user.id
    msg = update.effective_message
    if msg:
        tracked_messages.append((msg.chat_id, msg.message_id))


# ── Link handler ─────────────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global total_links
    msg = update.message
    if not msg:
        return

    user = msg.from_user
    username = user.username or str(user.id)
    display = f"@{username}" if user.username else user.full_name
    text = msg.text or msg.caption or ""

    if msg.video:
        if text.lower().strip() in ("ad", "add"):
            if username in senders:
                del senders[username]
                link_count.pop(username, None)
                await msg.reply_text(f"✅ {display} removed from the sender list.")
            else:
                await msg.reply_text(f"ℹ️ {display} was not in the sender list.")
        return

    links = extract_links(text)
    if not links:
        return

    try:
        await msg.delete()
    except Exception:
        pass

    total_links += len(links)
    link_count[username] += len(links)
    senders[username] = display

    sent = await context.bot.send_message(
        chat_id=msg.chat_id,
        text=(
            f"🔗 Link shared by {display}:\n"
            + "\n".join(links)
            + f"\n\n📊 Total links: {total_links}"
        )
    )
    tracked_messages.append((sent.chat_id, sent.message_id))


# ── /dall ─────────────────────────────────────────────────────────────────────

async def dall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return

    try:
        await update.message.delete()
    except Exception:
        pass

    deleted = 0
    failed = 0
    chat_id = update.effective_chat.id

    for c_id, m_id in list(tracked_messages):
        if c_id != chat_id:
            continue
        try:
            await context.bot.delete_message(chat_id=c_id, message_id=m_id)
            deleted += 1
        except Exception:
            failed += 1

    tracked_messages.clear()

    confirm = await context.bot.send_message(
        chat_id=chat_id,
        text=f"🗑️ Deleted {deleted} messages. ({failed} were too old or already gone)"
    )
    tracked_messages.append((confirm.chat_id, confirm.message_id))


# ── /ban ──────────────────────────────────────────────────────────────────────

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return

    args = context.args
    if len(args) < 2:
        await update.message.reply_text("⚠️ Usage:\n/ban all 3d\n/ban @username 2d")
        return

    target = args[0].lower()
    duration = parse_duration(args[1])
    if not duration:
        await update.message.reply_text("⚠️ Invalid duration. Use: 3d, 6h, or 30m")
        return

    muted = ChatPermissions(can_send_messages=False)
    chat_id = update.effective_chat.id
    results = []

    targets = dict(senders) if target == "all" else {
        target.lstrip("@"): senders.get(target.lstrip("@"), f"@{target.lstrip('@')}")
    }

    for uname, display in targets.items():
        member_id = user_id_map.get(uname.lower())
        if not member_id:
            results.append(f"⚠️ {display} — ID unknown, skipped")
            continue
        try:
            until = update.message.date + duration
            await context.bot.restrict_chat_member(chat_id, member_id, muted, until_date=until)
            results.append(f"🔇 {display} muted for {args[1]}")
        except Exception as e:
            results.append(f"⚠️ {display} — failed: {e}")

    await update.message.reply_text("\n".join(results) or "No actions taken.")


# ── /unban ────────────────────────────────────────────────────────────────────

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return

    args = context.args
    if not args:
        await update.message.reply_text("⚠️ Usage: /unban @username")
        return

    uname = args[0].lstrip("@").lower()
    member_id = user_id_map.get(uname)
    display = senders.get(uname, f"@{uname}")

    if not member_id:
        await update.message.reply_text(f"⚠️ Can't find {display}.")
        return

    try:
        await context.bot.restrict_chat_member(
            chat_id=update.effective_chat.id,
            user_id=member_id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_polls=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True,
            )
        )
        await update.message.reply_text(f"✅ {display} can send messages again.")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Failed: {e}")


# ── /list, /stats, /help ──────────────────────────────────────────────────────

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    if not senders:
        await update.message.reply_text("📭 No link senders yet.")
        return
    lines = [f"{name} — {link_count[u]} link(s)" for u, name in senders.items()]
    await update.message.reply_text(
        f"📋 Link Senders ({len(senders)} users | {total_links} total):\n\n" + "\n".join(lines)
    )

async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    await update.message.reply_text(f"📊 Total links shared: *{total_links}*", parse_mode="Markdown")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await update.message.reply_text("❌ Only admins can use this command.")
        return
    await update.message.reply_text(
        "🤖 *Link Manager Bot — Admin Commands*\n\n"
        "*/list* — Show all link senders\n"
        "*/stats* — Show total link count\n"
        "*/ban all 3d* — Mute everyone on the list\n"
        "*/ban @user 2d* — Mute a specific user\n"
        "*/unban @user* — Restore messaging rights\n"
        "*/dall* — Delete all tracked messages\n\n"
        "⏱ Duration: `3d` days · `6h` hours · `30m` minutes\n"
        "📌 Members remove themselves: send a video captioned `ad` or `add`",
        parse_mode="Markdown"
    )


# ── Setup bot commands menu ───────────────────────────────────────────────────

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("list", "Show all link senders"),
        BotCommand("stats", "Show total link count"),
        BotCommand("ban", "Mute users - usage: /ban all 3d or /ban @user 2d"),
        BotCommand("unban", "Restore user messaging - usage: /unban @user"),
        BotCommand("dall", "Delete all tracked messages"),
        BotCommand("help", "Show all commands"),
    ])


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    app.add_handler(MessageHandler(filters.ALL, track_user), group=0)

    app.add_handler(CommandHandler("list", list_command))
    app.add_handler(CommandHandler("stats", stats_command))
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("dall", dall_command))
    app.add_handler(CommandHandler("help", help_command))

    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message), group=1)

    print("✅ Bot is running...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
