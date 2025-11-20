import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "database.sqlite"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY,
        seen_posts TEXT DEFAULT ''
    )""")
    c.execute("""CREATE TABLE IF NOT EXISTS last_posts(
        id INTEGER PRIMARY KEY,
        post_ids TEXT
    )""")
    conn.commit()
    conn.close()

def update_seen(user_id, message_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users(user_id, seen_posts) VALUES(?, '')", (user_id,))
    c.execute("UPDATE users SET seen_posts = seen_posts || ? || ',' WHERE user_id=?", (str(message_id), user_id))
    conn.commit()
    conn.close()

def get_seen(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = c.execute("SELECT seen_posts FROM users WHERE user_id=?", (user_id,)).fetchone()
    conn.close()
    if row and row[0]:
        return [int(i) for i in row[0].split(',') if i.isdigit()]
    return []

def save_last_posts(post_ids):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    post_ids_str = ','.join(map(str, post_ids))
    c.execute("INSERT OR REPLACE INTO last_posts(id, post_ids) VALUES(1, ?)", (post_ids_str,))
    conn.commit()
    conn.close()

def load_last_posts():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    row = c.execute("SELECT post_ids FROM last_posts WHERE id=1").fetchone()
    conn.close()
    if row and row[0]:
        return [int(i) for i in row[0].split(',') if i.isdigit()]
    return []

def get_all_users():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    rows = c.execute("SELECT user_id FROM users").fetchall()
    conn.close()
    return [row[0] for row in rows]
