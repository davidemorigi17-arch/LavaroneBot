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
    """True se d può essere inizio di una nuova prenotazione.
    d == be è permesso (tocco finale OK)."""
    for bs, be in intervals:
        if bs <= d < be:
            return False
    return True


def _get_max_end(new_start, intervals):
    """Minimo bs > new_start: massima data di fine selezionabile."""
    fence = None
    for bs, be in intervals:
        if bs > new_start:
            if fence is None or bs < fence:
                fence = bs
    return fence


def _booking_name_starting_on(d, bookings):
    """Restituisce il nome della prenotazione che inizia esattamente il giorno d."""
    for b in bookings:
        bs = datetime.strptime(b[2], "%d-%m-%Y").date()
        if bs == d:
            return b[1]
    return None


def _short(name):
    """Prima parola del nome, max 6 caratteri."""
    return name.split()[0][:6] if name else "──"


def build_month_summary(year, month, bookings):
    """Testo con le prenotazioni del mese, da mostrare sopra il calendario."""
    if not bookings:
        return ""
    first = date(year, month, 1)
    last = date(year, month, calendar.monthrange(year, month)[1])
    month_bookings = []
    for b in bookings:
        bs = datetime.strptime(b[2], "%d-%m-%Y").date()
        be = datetime.strptime(b[3], "%d-%m-%Y").date()
        if bs <= last and be >= first:
            month_bookings.append(b)
    if not month_bookings:
        return ""
    lines = [f"📋 {MONTHS_IT[month - 1]} {year}:"]
    for b in month_bookings:
        line = f"  🔴 {b[1]}: {b[2]} → {b[3]}"
        if b[4]:
            line += f" ({b[4]})"
        lines.append(line)
    return "\n".join(lines) + "\n\n"


def build_calendar(year: int, month: int, min_date: date = None, prefix: str = "cal",
                   bookings=None, new_start: date = None) -> InlineKeyboardMarkup:
    today = date.today()
    if min_date is None:
        min_date = today

    bk = bookings or []
    intervals = _get_intervals(bk)
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
                continue

            d = date(year, month, day)

            if d < min_date:
                row.append(InlineKeyboardButton("·", callback_data=f"{prefix}|ignore"))

            elif new_start is not None:
                # ── Selezione data di FINE ────────────────────────────────────
                if max_end is not None and d > max_end:
                    name = _booking_name_starting_on(d, bk)
                    label = _short(name) if name else "──"
                    row.append(InlineKeyboardButton(label, callback_data=f"{prefix}|ignore"))
                elif max_end is not None and d == max_end:
                    name = _booking_name_starting_on(d, bk)
                    label = _short(name) if name else str(day)
                    row.append(InlineKeyboardButton(label, callback_data=f"{prefix}|select|{d.isoformat()}"))
                else:
                    row.append(InlineKeyboardButton(str(day), callback_data=f"{prefix}|select|{d.isoformat()}"))

            else:
                # ── Selezione data di INIZIO ──────────────────────────────────
                if not _is_valid_start(d, intervals):
                    name = _booking_name_starting_on(d, bk)
                    label = _short(name) if name else "──"
                    row.append(InlineKeyboardButton(label, callback_data=f"{prefix}|ignore"))
                else:
                    row.append(InlineKeyboardButton(str(day), callback_data=f"{prefix}|select|{d.isoformat()}"))

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
