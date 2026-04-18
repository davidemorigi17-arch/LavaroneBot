from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
import os

from database import init_db, add_booking, get_bookings
from utils.dates import parse, overlap

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

init_db()


def check_conflict(start, end):
    bookings = get_bookings()

    for b in bookings:
        b_start = parse(b[2])
        b_end = parse(b[3])

        if overlap(start, end, b_start, b_end):
            return True, b[1]

    return False, None


async def prenota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    name = args[2]
    start = parse(args[0])
    end = parse(args[1])

    conflict, who = check_conflict(start, end)

    if conflict:
        await update.message.reply_text(f"❌ Occupato da {who}")
        return

    add_booking(name, args[0], args[1])

    await update.message.reply_text(
        f"🏡 Prenotato {name}\n{args[0]} → {args[1]}"
    )


async def calendario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bookings = get_bookings()

    msg = "📅 Prenotazioni:\n\n"

    for b in bookings:
        msg += f"{b[1]}: {b[2]} → {b[3]}\n"

    await update.message.reply_text(msg)


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("prenota", prenota))
    app.add_handler(CommandHandler("calendario", calendario))

    app.run_polling()


if __name__ == "__main__":
    main()
