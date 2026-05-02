import calendar
from datetime import date, datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MONTHS_IT = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
]
DAYS_IT = ["Lu", "Ma", "Me", "Gi", "Ve", "Sa", "Do"]


def _get_intervals(bookings):
    intervals = []
    for b in bookings:
        bs = datetime.strptime(b[2], "%d-%m-%Y").date()
        be = datetime.strptime(b[3], "%d-%m-%Y").date()
        intervals.append((bs, be))
    return intervals


def _is_booked(d, intervals):
    for bs, be in intervals:
        if bs <= d <= be:
            return True
    return False


def _is_valid_start(d, intervals):
    """
    True se d può essere usato come data di inizio.
    Valido se NON è strettamente dentro nessuna prenotazione [bs, be).
    d == be è permesso: toccare la fine di una prenotazione precedente è OK.
    """
    for bs, be in intervals:
        if bs <= d < be:
            return False
    return True


def _get_max_end(new_start, intervals):
    """
    Restituisce la massima data di fine valida dato new_start.
    È il minimo bs tra le prenotazioni che iniziano dopo new_start.
    Selezionare esattamente questo giorno è permesso (tocco).
    Restituisce None se non ci sono vincoli.
    """
    fence = None
    for bs, be in intervals:
        if bs > new_start:
            if fence is None or bs < fence:
                fence = bs
    return fence


def build_calendar(year: int, month: int, min_date: date = None, prefix: str = "cal",
                   bookings=None, new_start: date = None) -> InlineKeyboardMarkup:
    today = date.today()
    if min_date is None:
        min_date = today

    intervals = _get_intervals(bookings) if bookings else []
    max_end = _get_max_end(new_start, intervals) if new_start is not None else None

    keyboard = []

    keyboard.append([
        InlineKeyboardButton(f"📅 {MONTHS_IT[month - 1]} {year}", callback_data=f"{prefix}|ignore")
    ])

    keyboard.append([
        InlineKeyboardButton(d, callback_data=f"{prefix}|ignore") for d in DAYS_IT
    ])

    for week in calendar.monthcalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(" ", callback_data=f"{prefix}|ignore"))
            else:
                d = date(year, month, day)
                if d < min_date:
                    row.append(InlineKeyboardButton("·", callback_data=f"{prefix}|ignore"))
                elif new_start is not None:
                    # ── Selezione data di FINE ────────────────────────────────
                    if max_end is not None and d > max_end:
                        # Oltre la prossima prenotazione: conflitto garantito
                        row.append(InlineKeyboardButton("🔴", callback_data=f"{prefix}|ignore"))
                    elif max_end is not None and d == max_end:
                        # Inizio della prossima prenotazione: selezionabile (tocco OK)
                        row.append(InlineKeyboardButton("🔴", callback_data=f"{prefix}|select|{d.isoformat()}"))
                    else:
                        # Giorno libero nel range valido
                        row.append(InlineKeyboardButton(str(day), callback_data=f"{prefix}|select|{d.isoformat()}"))
                else:
                    # ── Selezione data di INIZIO ──────────────────────────────
                    if _is_valid_start(d, intervals):
                        if _is_booked(d, intervals):
                            # Fine di una prenotazione: rosso ma selezionabile come inizio
                            row.append(InlineKeyboardButton("🔴", callback_data=f"{prefix}|select|{d.isoformat()}"))
                        else:
                            row.append(InlineKeyboardButton(str(day), callback_data=f"{prefix}|select|{d.isoformat()}"))
                    else:
                        # Interno o inizio di prenotazione: rosso, non selezionabile
                        row.append(InlineKeyboardButton("🔴", callback_data=f"{prefix}|ignore"))
        keyboard.append(row)

    first_of_month = date(year, month, 1)
    prev = (first_of_month - timedelta(days=1)).replace(day=1)
    nxt = (first_of_month.replace(day=28) + timedelta(days=4)).replace(day=1)

    nav = []
    if first_of_month > date(today.year, today.month, 1):
        nav.append(InlineKeyboardButton("◀", callback_data=f"{prefix}|prev|{prev.year}|{prev.month}"))
    else:
        nav.append(InlineKeyboardButton(" ", callback_data=f"{prefix}|ignore"))
    nav.append(InlineKeyboardButton("❌ Annulla", callback_data=f"{prefix}|cancel"))
    nav.append(InlineKeyboardButton("▶", callback_data=f"{prefix}|next|{nxt.year}|{nxt.month}"))
    keyboard.append(nav)

    return InlineKeyboardMarkup(keyboard)
