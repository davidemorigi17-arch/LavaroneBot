# Telegram Booking Bot

A Telegram bot for managing vacation home bookings. Users can create reservations, check for conflicts, and view the booking calendar through Telegram commands.

## Tech Stack
- **Language**: Python 3.12
- **Bot Framework**: python-telegram-bot v21.6
- **Database**: SQLite (stored at `data/bookings.db`)
- **APIs**: Google Calendar (optional sync), ReportLab (PDF export)

## Project Structure
```
bot.py             # Main entry point - Telegram bot handlers
database.py        # SQLite CRUD operations (data/bookings.db)
calendar_sync.py   # Google Calendar integration
pdf_export.py      # PDF report generation
utils/dates.py     # Date parsing and overlap detection
data/              # SQLite database directory
```

## Bot Commands
- `/prenota <start_date> <end_date> <name>` - Create a booking (dates in DD-MM-YYYY format)
- `/calendario` - View all bookings

## Configuration
- `BOT_TOKEN` (secret) - Telegram bot token from @BotFather
- `GOOGLE_CALENDAR_ID` (optional) - Google Calendar ID for sync
- `GOOGLE_CREDENTIALS_FILE` (optional) - Path to Google credentials JSON

## Running
The bot runs as a console workflow with `python bot.py`. Start the "Start application" workflow after setting the BOT_TOKEN secret.
