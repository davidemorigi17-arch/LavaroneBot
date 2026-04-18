import calendar
from datetime import date, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MONTHS_IT = [
    "Gennaio", "Febbraio", "Marzo", "Aprile", "Maggio", "Giugno",
    "Luglio", "Agosto", "Settembre", "Ottobre", "Novembre", "Dicembre"
]
DAYS_IT = ["Lu", "Ma", "Me", "Gi", "Ve", "Sa", "Do"]


def build_calendar(year: int, month: int, min_date: date = None, prefix: str = "cal") -> InlineKeyboardMarkup:
    today = date.today()
    if min_date is None:
        min_date = today

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
                else:
                    row.append(InlineKeyboardButton(
                        str(day),
                        callback_data=f"{prefix}|select|{d.isoformat()}"
                    ))
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
