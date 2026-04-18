import os
import io
import logging
from datetime import date, datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand, ForceReply
from telegram.ext import (
    Application, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)
from dotenv import load_dotenv

from database import init_db, add_booking, get_bookings, delete_booking, update_booking, get_booking_by_id
from utils.dates import parse, overlap
from utils.calendar_keyboard import build_calendar

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")

init_db()

# ─── State keys stored in context.user_data ───────────────────────────────────
# "state": current step (string or None)
# "pren_start", "pren_end": date objects
# "pren_name": string
# "del_id": int
# "mod_id": int
# "mod_field": string
# "mod_new_start": date object


def set_state(ud, state):
    ud["state"] = state


def get_state(ud):
    return ud.get("state")


def clear_state(ud):
    for k in ("state", "pren_start", "pren_end", "pren_name",
              "del_id", "mod_id", "mod_field", "mod_new_start"):
        ud.pop(k, None)


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
    clear_state(context.user_data)
    await update.message.reply_text(
        "🏡 Benvenuto nel bot prenotazioni!\n\n"
        "Comandi disponibili:\n"
        "/prenota — Crea una nuova prenotazione\n"
        "/calendario — Visualizza tutte le prenotazioni\n"
        "/modifica — Modifica una prenotazione esistente\n"
        "/cancella — Cancella una prenotazione\n"
        "/annulla — Annulla l'operazione in corso"
    )


# ─── /annulla ─────────────────────────────────────────────────────────────────

async def annulla(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_state(context.user_data)
    await update.message.reply_text("❌ Operazione annullata.")


# ─── iCal export ──────────────────────────────────────────────────────────────

def generate_ics(bookings) -> bytes:
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LavaroneBot//IT",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]
    for b in bookings:
        start = datetime.strptime(b[2], "%d-%m-%Y").date()
        end = datetime.strptime(b[3], "%d-%m-%Y").date()
        end_excl = end + timedelta(days=1)
        description = (b[4] or "").replace("\n", "\\n").replace(",", "\\,")
        summary = b[1].replace(",", "\\,")
        lines += [
            "BEGIN:VEVENT",
            f"UID:{b[0]}@lavaronebot",
            f"SUMMARY:{summary}",
            f"DTSTART;VALUE=DATE:{start.strftime('%Y%m%d')}",
            f"DTEND;VALUE=DATE:{end_excl.strftime('%Y%m%d')}",
            f"DESCRIPTION:{description}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines).encode("utf-8")


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
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("📥 Esporta calendario (.ics)", callback_data="cal_export")
    ]])
    await update.message.reply_text(msg.strip(), reply_markup=keyboard)


# ─── /prenota ─────────────────────────────────────────────────────────────────

async def prenota(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_state(context.user_data)
    set_state(context.user_data, "prenota_start")
    today = date.today()
    markup = build_calendar(today.year, today.month, prefix="ps")
    await update.message.reply_text("📅 Seleziona la data di inizio:", reply_markup=markup)


# ─── /cancella ────────────────────────────────────────────────────────────────

async def cancella(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_state(context.user_data)
    bookings = get_bookings()
    if not bookings:
        await update.message.reply_text("📅 Nessuna prenotazione da cancellare.")
        return
    keyboard = [
        [InlineKeyboardButton(booking_label(b), callback_data=f"del_sel|{b[0]}")]
        for b in bookings
    ]
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="del_sel|cancel")])
    set_state(context.user_data, "cancella_select")
    await update.message.reply_text(
        "🗑 Seleziona la prenotazione da cancellare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── /modifica ────────────────────────────────────────────────────────────────

async def modifica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_state(context.user_data)
    bookings = get_bookings()
    if not bookings:
        await update.message.reply_text("📅 Nessuna prenotazione da modificare.")
        return
    keyboard = [
        [InlineKeyboardButton(booking_label(b), callback_data=f"mod_sel|{b[0]}")]
        for b in bookings
    ]
    keyboard.append([InlineKeyboardButton("❌ Annulla", callback_data="mod_sel|cancel")])
    set_state(context.user_data, "modifica_select")
    await update.message.reply_text(
        "✏️ Seleziona la prenotazione da modificare:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ─── Callback query handler (all inline buttons) ──────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    ud = context.user_data
    state = get_state(ud)

    logger.info(f"CALLBACK: state={state} data={data}")

    # ── Esporta calendario .ics ───────────────────────────────────────────────
    if data == "cal_export":
        bookings = get_bookings()
        if not bookings:
            await query.answer("Nessuna prenotazione da esportare.", show_alert=True)
            return
        ics_bytes = generate_ics(bookings)
        ics_file = io.BytesIO(ics_bytes)
        ics_file.name = "prenotazioni.ics"
        await query.message.reply_document(
            document=ics_file,
            filename="prenotazioni.ics",
            caption="📅 Importa questo file in Google Calendar, Apple Calendar o Outlook per vedere tutte le prenotazioni."
        )
        return

    # ── Prenota: start date calendar ──────────────────────────────────────────
    if data.startswith("ps|"):
        if state != "prenota_start":
            return
        parts = data.split("|")
        action = parts[1]
        if action == "ignore":
            return
        if action == "cancel":
            clear_state(ud)
            await query.edit_message_text("❌ Prenotazione annullata.")
            return
        if action in ("prev", "next"):
            markup = build_calendar(int(parts[2]), int(parts[3]), prefix="ps")
            await query.edit_message_reply_markup(markup)
            return
        if action == "select":
            selected = date.fromisoformat(parts[2])
            ud["pren_start"] = selected
            set_state(ud, "prenota_end")
            markup = build_calendar(selected.year, selected.month, min_date=selected, prefix="pe")
            await query.edit_message_text(
                f"✅ Data inizio: {selected.strftime('%d/%m/%Y')}\n\n📅 Seleziona la data di fine:",
                reply_markup=markup
            )
            return

    # ── Prenota: end date calendar ────────────────────────────────────────────
    if data.startswith("pe|"):
        if state != "prenota_end":
            return
        parts = data.split("|")
        action = parts[1]
        start_date = ud.get("pren_start")
        if action == "ignore":
            return
        if action == "cancel":
            clear_state(ud)
            await query.edit_message_text("❌ Prenotazione annullata.")
            return
        if action in ("prev", "next"):
            markup = build_calendar(int(parts[2]), int(parts[3]), min_date=start_date, prefix="pe")
            await query.edit_message_reply_markup(markup)
            return
        if action == "select":
            selected = date.fromisoformat(parts[2])
            ud["pren_end"] = selected
            set_state(ud, "prenota_name")
            await query.edit_message_text(
                f"✅ Date: {start_date.strftime('%d/%m/%Y')} → {selected.strftime('%d/%m/%Y')}"
            )
            await query.message.reply_text(
                "👤 Inserisci il nome del prenotante:",
                reply_markup=ForceReply(selective=True)
            )
            return

    # ── Cancella: selezione prenotazione ──────────────────────────────────────
    if data.startswith("del_sel|"):
        if state != "cancella_select":
            return
        val = data.split("|")[1]
        if val == "cancel":
            clear_state(ud)
            await query.edit_message_text("❌ Operazione annullata.")
            return
        booking_id = int(val)
        ud["del_id"] = booking_id
        b = get_booking_by_id(booking_id)
        detail = f"👤 {b[1]}: {b[2]} → {b[3]}"
        if b[4]:
            detail += f"\n📝 {b[4]}"
        set_state(ud, "cancella_confirm")
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("✅ Sì, cancella", callback_data="del_confirm|yes"),
            InlineKeyboardButton("❌ No", callback_data="del_confirm|no")
        ]])
        await query.edit_message_text(
            f"Vuoi cancellare questa prenotazione?\n\n{detail}",
            reply_markup=keyboard
        )
        return

    # ── Cancella: conferma ────────────────────────────────────────────────────
    if data.startswith("del_confirm|"):
        if state != "cancella_confirm":
            return
        val = data.split("|")[1]
        if val == "yes":
            delete_booking(ud["del_id"])
            await query.edit_message_text("✅ Prenotazione cancellata.")
        else:
            await query.edit_message_text("❌ Operazione annullata.")
        clear_state(ud)
        return

    # ── Modifica: selezione prenotazione ──────────────────────────────────────
    if data.startswith("mod_sel|"):
        if state != "modifica_select":
            return
        val = data.split("|")[1]
        if val == "cancel":
            clear_state(ud)
            await query.edit_message_text("❌ Operazione annullata.")
            return
        booking_id = int(val)
        ud["mod_id"] = booking_id
        b = get_booking_by_id(booking_id)
        detail = f"👤 {b[1]}: {b[2]} → {b[3]}"
        if b[4]:
            detail += f"\n📝 {b[4]}"
        set_state(ud, "modifica_field")
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
        return

    # ── Modifica: scelta campo ────────────────────────────────────────────────
    if data.startswith("mod_field|"):
        if state != "modifica_field":
            return
        field = data.split("|")[1]
        if field == "cancel":
            clear_state(ud)
            await query.edit_message_text("❌ Operazione annullata.")
            return
        ud["mod_field"] = field
        if field == "dates":
            set_state(ud, "modifica_start")
            today = date.today()
            markup = build_calendar(today.year, today.month, prefix="ms")
            await query.edit_message_text("📅 Seleziona la nuova data di inizio:", reply_markup=markup)
        elif field == "name":
            set_state(ud, "modifica_text")
            await query.edit_message_text("✏️ Modifica nome:")
            await query.message.reply_text(
                "👤 Inserisci il nuovo nome:",
                reply_markup=ForceReply(selective=True)
            )
        elif field == "notes":
            set_state(ud, "modifica_text")
            await query.edit_message_text("✏️ Modifica nota:")
            await query.message.reply_text(
                "📝 Inserisci la nuova nota (scrivi - per rimuoverla):",
                reply_markup=ForceReply(selective=True)
            )
        return

    # ── Modifica: nuova data inizio ───────────────────────────────────────────
    if data.startswith("ms|"):
        if state != "modifica_start":
            return
        parts = data.split("|")
        action = parts[1]
        if action == "ignore":
            return
        if action == "cancel":
            clear_state(ud)
            await query.edit_message_text("❌ Operazione annullata.")
            return
        if action in ("prev", "next"):
            markup = build_calendar(int(parts[2]), int(parts[3]), prefix="ms")
            await query.edit_message_reply_markup(markup)
            return
        if action == "select":
            selected = date.fromisoformat(parts[2])
            ud["mod_new_start"] = selected
            set_state(ud, "modifica_end")
            markup = build_calendar(selected.year, selected.month, min_date=selected, prefix="me")
            await query.edit_message_text(
                f"✅ Nuova data inizio: {selected.strftime('%d/%m/%Y')}\n\n📅 Seleziona la nuova data di fine:",
                reply_markup=markup
            )
            return

    # ── Modifica: nuova data fine ─────────────────────────────────────────────
    if data.startswith("me|"):
        if state != "modifica_end":
            return
        parts = data.split("|")
        action = parts[1]
        start_date = ud.get("mod_new_start")
        if action == "ignore":
            return
        if action == "cancel":
            clear_state(ud)
            await query.edit_message_text("❌ Operazione annullata.")
            return
        if action in ("prev", "next"):
            markup = build_calendar(int(parts[2]), int(parts[3]), min_date=start_date, prefix="me")
            await query.edit_message_reply_markup(markup)
            return
        if action == "select":
            selected = date.fromisoformat(parts[2])
            booking_id = ud["mod_id"]
            start_str = start_date.strftime("%d-%m-%Y")
            end_str = selected.strftime("%d-%m-%Y")
            conflict, who = check_conflict(parse(start_str), parse(end_str), exclude_id=booking_id)
            if conflict:
                clear_state(ud)
                await query.edit_message_text(f"❌ Date in conflitto con la prenotazione di {who}.")
                return
            update_booking(booking_id, start_date=start_str, end_date=end_str)
            clear_state(ud)
            await query.edit_message_text(f"✅ Date aggiornate: {start_str} → {end_str}")
            return


# ─── Text message handler ──────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    state = get_state(ud)
    text = update.message.text.strip()

    logger.info(f"MESSAGE: state={state} text={text[:30]}")

    if state == "prenota_name":
        ud["pren_name"] = text
        set_state(ud, "prenota_notes")
        await update.message.reply_text(
            "📝 Aggiungi una nota (es. chi andrà in casa):\n"
            "Oppure /salta per continuare senza nota.",
            reply_markup=ForceReply(selective=True)
        )
        return

    if state == "prenota_notes":
        await _save_prenota(update, context, notes=text)
        return

    if state == "modifica_text":
        field = ud.get("mod_field")
        booking_id = ud.get("mod_id")
        if field == "name":
            update_booking(booking_id, name=text)
            await update.message.reply_text(f"✅ Nome aggiornato: {text}")
        elif field == "notes":
            notes = "" if text == "-" else text
            update_booking(booking_id, notes=notes)
            await update.message.reply_text("✅ Nota aggiornata.")
        clear_state(ud)
        return


async def salta(update: Update, context: ContextTypes.DEFAULT_TYPE):
    ud = context.user_data
    state = get_state(ud)
    if state == "prenota_notes":
        await _save_prenota(update, context, notes="")
    else:
        await update.message.reply_text("Nessuna operazione in corso da saltare.")


async def _save_prenota(update: Update, context: ContextTypes.DEFAULT_TYPE, notes: str):
    ud = context.user_data
    start_d = ud["pren_start"]
    end_d = ud["pren_end"]
    name = ud["pren_name"]
    start_str = start_d.strftime("%d-%m-%Y")
    end_str = end_d.strftime("%d-%m-%Y")
    conflict, who = check_conflict(parse(start_str), parse(end_str))
    if conflict:
        await update.message.reply_text(f"❌ Date in conflitto con la prenotazione di {who}.")
        clear_state(ud)
        return
    add_booking(name, start_str, end_str, notes)
    msg = f"🏡 Prenotazione confermata!\n👤 {name}\n📅 {start_str} → {end_str}"
    if notes:
        msg += f"\n📝 {notes}"
    await update.message.reply_text(msg)
    clear_state(ud)


# ─── Error handler ─────────────────────────────────────────────────────────────

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Eccezione durante l'elaborazione dell'update:", exc_info=context.error)


# ─── post_init ─────────────────────────────────────────────────────────────────

async def post_init(application: Application):
    await application.bot.set_my_commands([
        BotCommand("start", "Avvia il bot"),
        BotCommand("prenota", "Crea una nuova prenotazione"),
        BotCommand("calendario", "Visualizza tutte le prenotazioni"),
        BotCommand("modifica", "Modifica una prenotazione esistente"),
        BotCommand("cancella", "Cancella una prenotazione"),
        BotCommand("annulla", "Annulla l'operazione in corso"),
    ])


# ─── Main ──────────────────────────────────────────────────────────────────────

def main():
    app = Application.builder().token(TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("prenota", prenota))
    app.add_handler(CommandHandler("cancella", cancella))
    app.add_handler(CommandHandler("modifica", modifica))
    app.add_handler(CommandHandler("calendario", calendario))
    app.add_handler(CommandHandler("annulla", annulla))
    app.add_handler(CommandHandler("salta", salta))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
