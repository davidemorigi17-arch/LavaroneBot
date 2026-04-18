import os
import logging
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    ConversationHandler, CallbackQueryHandler, MessageHandler, filters
)
from dotenv import load_dotenv

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from database import init_db, add_booking, get_bookings, delete_booking, update_booking, get_booking_by_id
from utils.dates import parse, overlap
from utils.calendar_keyboard import build_calendar

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

init_db()

(
    PRENOTA_START, PRENOTA_END, PRENOTA_NAME, PRENOTA_NOTES,
    MODIFICA_SELECT, MODIFICA_FIELD, MODIFICA_START, MODIFICA_END, MODIFICA_TEXT,
    CANCELLA_SELECT, CANCELLA_CONFIRM
) = range(11)


def check_conflict(start, end, exclude_id=None):
    for b in get_bookings():
        if exclude_id and b[0] == exclude_id:
            continue
        if overlap(start, end, parse(b[2]), parse(b[3])):
            return True, b[1]
    return False, None


def booking_label(b):
    label = f"{b[1]}: {b[2]} → {b[3]}"
    if b[4]:
        label += f" ({b[4]})"
    return label


# ─── /start ───────────────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🏡 Benvenuto nel bot prenotazioni!\n\n"
        "Comandi disponibili:\n"
        "/prenota — Crea una nuova prenotazione\n"
        "/calendario — Visualizza tutte le prenotazioni\n"
        "/modifica — Modifica una prenotazione esistente\n"
        "/cancella — Cancella una prenotazione"
    )


# ─── /calendario ──────────────────────────────────────────────────────────────

async def calendario(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bookings = get_bookings()
    if not bookings:
        await update.message.reply_text("📅 Nessuna prenotazione trovata.")
        return

    msg = "📅 Prenotazioni:\n\n"
    for b in bookings:
        msg += f"🔹 {b[1]}: {b[2]} → {b[3]}"
        if b[4]:
            msg += f"\n   📝 {b[4]}"
        msg += "\n\n"
    await update.message.reply_text(msg.strip())


# ─── /prenota ─────────────────────────────────────────────────────────────────

async def prenota_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = date.today()
    markup = build_calendar(today.year, today.month, prefix="pren_start")
    await update.message.reply_text("📅 Seleziona la data di inizio:", reply_markup=markup)
    return PRENOTA_START


async def prenota_handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    action = parts[1]

    if action == "ignore":
        return PRENOTA_START
    if action == "cancel":
        await query.edit_message_text("❌ Prenotazione annullata.")
        return ConversationHandler.END
    if action in ("prev", "next"):
        markup = build_calendar(int(parts[2]), int(parts[3]), prefix="pren_start")
        await query.edit_message_reply_markup(markup)
        return PRENOTA_START
    if action == "select":
        selected = date.fromisoformat(parts[2])
        context.user_data["pren_start"] = selected
        markup = build_calendar(selected.year, selected.month, min_date=selected, prefix="pren_end")
        await query.edit_message_text(
            f"✅ Data inizio: {selected.strftime('%d/%m/%Y')}\n\n📅 Seleziona la data di fine:",
            reply_markup=markup
        )
        return PRENOTA_END
    return PRENOTA_START


async def prenota_handle_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    action = parts[1]
    start_date = context.user_data.get("pren_start")

    if action == "ignore":
        return PRENOTA_END
    if action == "cancel":
        await query.edit_message_text("❌ Prenotazione annullata.")
        return ConversationHandler.END
    if action in ("prev", "next"):
        markup = build_calendar(int(parts[2]), int(parts[3]), min_date=start_date, prefix="pren_end")
        await query.edit_message_reply_markup(markup)
        return PRENOTA_END
    if action == "select":
        selected = date.fromisoformat(parts[2])
        context.user_data["pren_end"] = selected
        await query.edit_message_text(
            f"✅ Date: {start_date.strftime('%d/%m/%Y')} → {selected.strftime('%d/%m/%Y')}\n\n"
            "👤 Inserisci il nome del prenotante:"
        )
        return PRENOTA_NAME
    return PRENOTA_END


async def prenota_handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["pren_name"] = update.message.text.strip()
    await update.message.reply_text(
        "📝 Aggiungi una nota (es. chi andrà in casa, contatti, ecc.):\n"
        "Oppure usa /salta per continuare senza nota."
    )
    return PRENOTA_NOTES


async def prenota_skip_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _save_prenota(update, context, notes="")


async def prenota_handle_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return await _save_prenota(update, context, notes=update.message.text.strip())


async def _save_prenota(update: Update, context: ContextTypes.DEFAULT_TYPE, notes: str):
    start_d = context.user_data["pren_start"]
    end_d = context.user_data["pren_end"]
    name = context.user_data["pren_name"]
    start_str = start_d.strftime("%d-%m-%Y")
    end_str = end_d.strftime("%d-%m-%Y")

    conflict, who = check_conflict(parse(start_str), parse(end_str))
    if conflict:
        await update.message.reply_text(f"❌ Date in conflitto con la prenotazione di {who}.")
        return ConversationHandler.END

    add_booking(name, start_str, end_str, notes)
    msg = f"🏡 Prenotazione confermata!\n👤 {name}\n📅 {start_str} → {end_str}"
    if notes:
        msg += f"\n📝 {notes}"
    await update.message.reply_text(msg)
    return ConversationHandler.END


# ─── /cancella ────────────────────────────────────────────────────────────────

async def cancella_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bookings = get_bookings()
    if not bookings:
        await update.message.reply_text("📅 Nessuna prenotazione da cancellare.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(booking_label(b), callback_data=f"del|{b[0]}")]
        for b in bookings
    ]
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="del|cancel")])
    await update.message.reply_text(
        "🗑 Seleziona la prenotazione da cancellare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return CANCELLA_SELECT


async def cancella_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "del|cancel":
        await query.edit_message_text("❌ Operazione annullata.")
        return ConversationHandler.END

    booking_id = int(query.data.split("|")[1])
    context.user_data["del_id"] = booking_id
    b = get_booking_by_id(booking_id)

    detail = f"👤 {b[1]}: {b[2]} → {b[3]}"
    if b[4]:
        detail += f"\n📝 {b[4]}"

    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Sì, cancella", callback_data="del_confirm|yes"),
        InlineKeyboardButton("❌ No", callback_data="del_confirm|no")
    ]])
    await query.edit_message_text(
        f"Vuoi cancellare questa prenotazione?\n\n{detail}",
        reply_markup=keyboard
    )
    return CANCELLA_CONFIRM


async def cancella_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "del_confirm|yes":
        delete_booking(context.user_data["del_id"])
        await query.edit_message_text("✅ Prenotazione cancellata.")
    else:
        await query.edit_message_text("❌ Operazione annullata.")
    return ConversationHandler.END


# ─── /modifica ────────────────────────────────────────────────────────────────

async def modifica_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bookings = get_bookings()
    if not bookings:
        await update.message.reply_text("📅 Nessuna prenotazione da modificare.")
        return ConversationHandler.END

    keyboard = [
        [InlineKeyboardButton(booking_label(b), callback_data=f"mod_sel|{b[0]}")]
        for b in bookings
    ]
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="mod_sel|cancel")])
    await update.message.reply_text(
        "✏️ Seleziona la prenotazione da modificare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return MODIFICA_SELECT


async def modifica_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "mod_sel|cancel":
        await query.edit_message_text("❌ Operazione annullata.")
        return ConversationHandler.END

    booking_id = int(query.data.split("|")[1])
    context.user_data["mod_id"] = booking_id
    b = get_booking_by_id(booking_id)

    detail = f"👤 {b[1]}: {b[2]} → {b[3]}"
    if b[4]:
        detail += f"\n📝 {b[4]}"

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📅 Date", callback_data="mod_field|dates"),
            InlineKeyboardButton("👤 Nome", callback_data="mod_field|name"),
        ],
        [
            InlineKeyboardButton("📝 Note", callback_data="mod_field|notes"),
            InlineKeyboardButton("❌ Annulla", callback_data="mod_field|cancel"),
        ]
    ])
    await query.edit_message_text(
        f"Prenotazione selezionata:\n{detail}\n\nCosa vuoi modificare?",
        reply_markup=keyboard
    )
    return MODIFICA_FIELD


async def modifica_field(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    field = query.data.split("|")[1]

    if field == "cancel":
        await query.edit_message_text("❌ Operazione annullata.")
        return ConversationHandler.END

    context.user_data["mod_field"] = field

    if field == "dates":
        today = date.today()
        markup = build_calendar(today.year, today.month, prefix="mod_start")
        await query.edit_message_text("📅 Seleziona la nuova data di inizio:", reply_markup=markup)
        return MODIFICA_START
    elif field == "name":
        await query.edit_message_text("👤 Inserisci il nuovo nome:")
        return MODIFICA_TEXT
    elif field == "notes":
        await query.edit_message_text("📝 Inserisci la nuova nota (scrivi - per rimuoverla):")
        return MODIFICA_TEXT

    return ConversationHandler.END


async def modifica_handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    action = parts[1]

    if action == "ignore":
        return MODIFICA_START
    if action == "cancel":
        await query.edit_message_text("❌ Operazione annullata.")
        return ConversationHandler.END
    if action in ("prev", "next"):
        markup = build_calendar(int(parts[2]), int(parts[3]), prefix="mod_start")
        await query.edit_message_reply_markup(markup)
        return MODIFICA_START
    if action == "select":
        selected = date.fromisoformat(parts[2])
        context.user_data["mod_new_start"] = selected
        markup = build_calendar(selected.year, selected.month, min_date=selected, prefix="mod_end")
        await query.edit_message_text(
            f"✅ Nuova data inizio: {selected.strftime('%d/%m/%Y')}\n\n📅 Seleziona la nuova data di fine:",
            reply_markup=markup
        )
        return MODIFICA_END
    return MODIFICA_START


async def modifica_handle_end(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts = query.data.split("|")
    action = parts[1]
    start_date = context.user_data.get("mod_new_start")

    if action == "ignore":
        return MODIFICA_END
    if action == "cancel":
        await query.edit_message_text("❌ Operazione annullata.")
        return ConversationHandler.END
    if action in ("prev", "next"):
        markup = build_calendar(int(parts[2]), int(parts[3]), min_date=start_date, prefix="mod_end")
        await query.edit_message_reply_markup(markup)
        return MODIFICA_END
    if action == "select":
        selected = date.fromisoformat(parts[2])
        booking_id = context.user_data["mod_id"]
        start_str = start_date.strftime("%d-%m-%Y")
        end_str = selected.strftime("%d-%m-%Y")
        conflict, who = check_conflict(parse(start_str), parse(end_str), exclude_id=booking_id)
        if conflict:
            await query.edit_message_text(f"❌ Date in conflitto con la prenotazione di {who}.")
            return ConversationHandler.END
        update_booking(booking_id, start_date=start_str, end_date=end_str)
        await query.edit_message_text(f"✅ Date aggiornate: {start_str} → {end_str}")
        return ConversationHandler.END
    return MODIFICA_END


async def modifica_handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    field = context.user_data["mod_field"]
    booking_id = context.user_data["mod_id"]
    value = update.message.text.strip()

    if field == "name":
        update_booking(booking_id, name=value)
        await update.message.reply_text(f"✅ Nome aggiornato: {value}")
    elif field == "notes":
        notes = "" if value == "-" else value
        update_booking(booking_id, notes=notes)
        await update.message.reply_text("✅ Nota aggiornata.")
    return ConversationHandler.END


# ─── Main ─────────────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Eccezione durante l'elaborazione dell'update:", exc_info=context.error)


async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Avvia il bot"),
        BotCommand("prenota", "Crea una nuova prenotazione"),
        BotCommand("calendario", "Visualizza tutte le prenotazioni"),
        BotCommand("modifica", "Modifica una prenotazione esistente"),
        BotCommand("cancella", "Cancella una prenotazione"),
    ])


def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    prenota_conv = ConversationHandler(
        entry_points=[CommandHandler("prenota", prenota_start)],
        states={
            PRENOTA_START: [CallbackQueryHandler(prenota_handle_start, pattern=r"^pren_start\|")],
            PRENOTA_END: [CallbackQueryHandler(prenota_handle_end, pattern=r"^pren_end\|")],
            PRENOTA_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, prenota_handle_name)],
            PRENOTA_NOTES: [
                CommandHandler("salta", prenota_skip_notes),
                MessageHandler(filters.TEXT & ~filters.COMMAND, prenota_handle_notes),
            ],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    cancella_conv = ConversationHandler(
        entry_points=[CommandHandler("cancella", cancella_start)],
        states={
            CANCELLA_SELECT: [CallbackQueryHandler(cancella_select, pattern=r"^del\|")],
            CANCELLA_CONFIRM: [CallbackQueryHandler(cancella_confirm, pattern=r"^del_confirm\|")],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    modifica_conv = ConversationHandler(
        entry_points=[CommandHandler("modifica", modifica_start)],
        states={
            MODIFICA_SELECT: [CallbackQueryHandler(modifica_select, pattern=r"^mod_sel\|")],
            MODIFICA_FIELD: [CallbackQueryHandler(modifica_field, pattern=r"^mod_field\|")],
            MODIFICA_START: [CallbackQueryHandler(modifica_handle_start, pattern=r"^mod_start\|")],
            MODIFICA_END: [CallbackQueryHandler(modifica_handle_end, pattern=r"^mod_end\|")],
            MODIFICA_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, modifica_handle_text)],
        },
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("calendario", calendario))
    app.add_handler(prenota_conv)
    app.add_handler(cancella_conv)
    app.add_handler(modifica_conv)
    app.add_error_handler(error_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
