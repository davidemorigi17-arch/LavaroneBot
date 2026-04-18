import sqlite3

DB_PATH = "data/bookings.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        start_date TEXT,
        end_date TEXT,
        notes TEXT DEFAULT '',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    try:
        c.execute("ALTER TABLE bookings ADD COLUMN notes TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass
    conn.commit()
    conn.close()


def add_booking(name, start, end, notes=""):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO bookings (name, start_date, end_date, notes) VALUES (?, ?, ?, ?)",
        (name, start, end, notes)
    )
    conn.commit()
    conn.close()


def get_bookings():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, start_date, end_date, notes FROM bookings ORDER BY start_date")
    rows = c.fetchall()
    conn.close()
    return rows


def get_booking_by_id(booking_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name, start_date, end_date, notes FROM bookings WHERE id=?", (booking_id,))
    row = c.fetchone()
    conn.close()
    return row


def update_booking(booking_id, **fields):
    allowed = {"name", "start_date", "end_date", "notes"}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return
    set_clause = ", ".join(f"{k}=?" for k in updates)
    values = list(updates.values()) + [booking_id]
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE bookings SET {set_clause} WHERE id=?", values)
    conn.commit()
    conn.close()


def delete_booking(booking_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM bookings WHERE id=?", (booking_id,))
    conn.commit()
    conn.close()
