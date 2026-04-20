# 🏡 LavaroneBot

Bot Telegram per la gestione delle prenotazioni di una casa vacanze. Permette di creare, visualizzare, modificare e cancellare prenotazioni direttamente da una chat Telegram, anche in gruppo.

---

## Funzionalità

- **Crea prenotazioni** con selezione date tramite calendario interattivo inline
- **Rilevamento conflitti** automatico: impedisce sovrapposizioni tra prenotazioni
- **Visualizza il calendario** con tutte le prenotazioni attive
- **Esporta in .ics** compatibile con Google Calendar, Apple Calendar e Outlook
- **Modifica prenotazioni** esistenti (date, nome, note)
- **Cancella prenotazioni** con richiesta di conferma
- **Campo note** opzionale per ogni prenotazione
- Funziona in **chat privata e di gruppo**

---

## Comandi disponibili

| Comando | Descrizione |
|---|---|
| `/start` | Avvia il bot e mostra i comandi disponibili |
| `/prenota` | Crea una nuova prenotazione |
| `/calendario` | Visualizza tutte le prenotazioni |
| `/modifica` | Modifica una prenotazione esistente |
| `/cancella` | Cancella una prenotazione |
| `/annulla` | Annulla l'operazione in corso |
| `/salta` | Salta il campo note durante la prenotazione |

---

## Struttura del progetto

```
LavaroneBot/
├── bot.py                    # Entry point — handler Telegram e state machine
├── database.py               # Operazioni CRUD su SQLite
├── utils/
│   ├── calendar_keyboard.py  # Costruzione tastiera calendario inline
│   └── dates.py              # Parsing date e rilevamento sovrapposizioni
├── data/
│   └── bookings.db           # Database SQLite (generato automaticamente)
├── Dockerfile                # Immagine Docker per il bot
├── docker-compose.yml        # Orchestrazione container
├── update.sh                 # Script aggiornamento da GitHub
├── requirements.txt
└── .env.example
```

---

## Tecnologie

- **Python** 3.12
- **python-telegram-bot** v21.6 (polling, no webhook)
- **SQLite** — database locale in `data/bookings.db`
- Nessuna dipendenza esterna cloud (gira ovunque con Python)

---

## Installazione locale

### 1. Clona il repository

```bash
git clone https://github.com/davidemorigi17-arch/LavaroneBot.git
cd LavaroneBot
```

### 2. Installa le dipendenze

```bash
pip install -r requirements.txt
```

### 3. Configura il token

Crea un file `.env` nella root del progetto (vedi `.env.example`):

```
BOT_TOKEN=il_tuo_token_qui
```

Il token si ottiene da [@BotFather](https://t.me/BotFather) su Telegram.

### 4. Avvia il bot

```bash
python bot.py
```

---

## Deploy su Replit

Il progetto è configurato per girare su [Replit](https://replit.com) come VM sempre attiva:

1. Importa il repository su Replit
2. Aggiungi il segreto `BOT_TOKEN` nelle impostazioni del progetto
3. Avvia il workflow `Start application`
4. (Opzionale) Pubblica come **Deployment VM** per il funzionamento 24/7

> Il bot usa il **polling** — contatta i server Telegram autonomamente ogni pochi secondi. Non richiede un indirizzo pubblico o webhook.

---

## Deploy con Docker Compose (server proprio)

Questa è la modalità consigliata per far girare il bot su un tuo server (VPS, Raspberry Pi, NAS, ecc.) con **aggiornamento automatico da GitHub**.

### Primo avvio

```bash
git clone https://github.com/davidemorigi17-arch/LavaroneBot.git
cd LavaroneBot
cp .env.example .env
nano .env          # inserisci il BOT_TOKEN
docker compose up -d --build
```

Il database SQLite viene salvato nella cartella `data/` sul host — persiste tra i riavvii del container.

### Aggiornamento automatico

Ogni volta che vuoi aggiornare il bot all'ultima versione dal repository GitHub, basta eseguire:

```bash
./update.sh
```

Lo script fa tre cose in sequenza:
1. `git pull origin main` — scarica le ultime modifiche da GitHub
2. `docker compose up -d --build` — ricostruisce l'immagine e riavvia il container
3. Mostra lo stato del container

### Aggiornamento completamente automatico (opzionale)

Per aggiornare il bot senza nessun intervento manuale, aggiungi un cron job sul server:

```bash
crontab -e
```

```
# Controlla aggiornamenti ogni ora
0 * * * * cd /percorso/LavaroneBot && ./update.sh >> /var/log/lavaronebot-update.log 2>&1
```

### Comandi utili

```bash
docker compose logs -f          # Vedi i log in tempo reale
docker compose ps               # Stato del container
docker compose down             # Ferma il bot
docker compose up -d --build    # Riavvia e aggiorna
```

---

## Note tecniche

- La gestione degli stati del flusso di prenotazione è implementata tramite una **state machine manuale** in `context.user_data`, senza `ConversationHandler`. Questa scelta garantisce il corretto funzionamento nelle chat di gruppo con python-telegram-bot v21.
- Il polling viene avviato con `allowed_updates=Update.ALL_TYPES` per ricevere i callback inline anche nei gruppi.
- È fondamentale che giri **una sola istanza** del bot alla volta: due istanze in polling simultaneo causano un errore `Conflict` di Telegram.

---

## Configurazione BotFather

Per il corretto funzionamento nei gruppi:
- Disabilita la **Privacy Mode** del bot tramite BotFather (`/setprivacy` → `Disable`)
- Aggiungi il bot al gruppo

---

## Licenza

Progetto privato — uso personale.
