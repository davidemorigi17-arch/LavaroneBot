# LavaroneBot — Telegram Booking Bot

Bot Telegram per la gestione delle prenotazioni di una casa vacanze. Interfaccia interattiva con tastiera inline, rilevamento conflitti, esportazione .ics.

## Tech Stack
- **Language**: Python 3.12
- **Bot Framework**: python-telegram-bot v21.6 (polling)
- **Database**: SQLite (`data/bookings.db`)

## Project Structure
```
bot.py                    # Entry point — handler e state machine manuale
database.py               # CRUD SQLite
utils/calendar_keyboard.py  # Calendario inline con navigazione mesi
utils/dates.py            # Parsing date e overlap detection
data/bookings.db          # Database SQLite (auto-generato)
requirements.txt
.env.example
README.md
```

## Bot Commands
- `/start` — Avvia il bot
- `/prenota` — Crea prenotazione (calendario interattivo)
- `/calendario` — Visualizza prenotazioni + export .ics
- `/modifica` — Modifica date/nome/note di una prenotazione
- `/cancella` — Cancella una prenotazione con conferma
- `/annulla` — Annulla operazione in corso
- `/salta` — Salta il campo note

## Configuration
- `BOT_TOKEN` (secret Replit) — Token del bot da @BotFather

## Running
Workflow `Start application` → `python bot.py`

## Key Design Decisions
- **State machine manuale** in `context.user_data` (no ConversationHandler) — necessario per funzionamento affidabile nei gruppi con PTB v21
- **Polling** con `allowed_updates=Update.ALL_TYPES` — obbligatorio per ricevere callback inline nei gruppi
- **Una sola istanza** alla volta — due istanze in polling causano Telegram Conflict error
- Privacy Mode disabilitata via BotFather per funzionamento nei gruppi
