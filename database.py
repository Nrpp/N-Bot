import sqlite3
from datetime import datetime, timezone

DB_NAME = "pulse.db"

def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    conn = get_connection()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            xp INTEGER DEFAULT 0,
            level INTEGER DEFAULT 1,
            coins INTEGER DEFAULT 100,
            streak INTEGER DEFAULT 0,
            last_daily TEXT,
            PRIMARY KEY (user_id, guild_id)
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            task TEXT NOT NULL,
            completed INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            guild_id INTEGER NOT NULL,
            channel_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            remind_at TEXT NOT NULL
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS pets (
            guild_id INTEGER PRIMARY KEY,
            name TEXT DEFAULT 'Pulse',
            hunger INTEGER DEFAULT 80,
            happiness INTEGER DEFAULT 80,
            energy INTEGER DEFAULT 80
        )
    """)

    conn.commit()
    conn.close()

def get_user(user_id, guild_id):
    conn = get_connection()

    user = conn.execute(
        """
        SELECT *
        FROM users
        WHERE user_id = ? AND guild_id = ?
        """,
        (user_id, guild_id)
    ).fetchone()

    if user is None:
        conn.execute(
            """
            INSERT INTO users
            (user_id, guild_id, xp, level, coins, streak)
            VALUES (?, ?, 0, 1, 100, 0)
            """,
            (user_id, guild_id)
        )
        conn.commit()

        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE user_id = ? AND guild_id = ?
            """,
            (user_id, guild_id)
        ).fetchone()

    conn.close()
    return user

def add_xp(user_id, guild_id, amount):
    user = get_user(user_id, guild_id)

    xp = user["xp"] + amount
    level = user["level"]
    coins = user["coins"]

    leveled_up = False

    while xp >= level * 100:
        xp -= level * 100
        level += 1
        coins += 50
        leveled_up = True

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET xp = ?, level = ?, coins = ?
        WHERE user_id = ? AND guild_id = ?
        """,
        (xp, level, coins, user_id, guild_id)
    )

    conn.commit()
    conn.close()

    return level, leveled_up

def add_coins(user_id, guild_id, amount):
    get_user(user_id, guild_id)

    conn = get_connection()

    conn.execute(
        """
        UPDATE users
        SET coins = coins + ?
        WHERE user_id = ? AND guild_id = ?
        """,
        (amount, user_id, guild_id)
    )

    conn.commit()
    conn.close()

def get_leaderboard(guild_id, limit=10):
    conn = get_connection()

    users = conn.execute(
        """
        SELECT *
        FROM users
        WHERE guild_id = ?
        ORDER BY level DESC, xp DESC, coins DESC
        LIMIT ?
        """,
        (guild_id, limit)
    ).fetchall()

    conn.close()

    return users

def add_task(user_id, guild_id, task):
    conn = get_connection()

    cursor = conn.execute(
        """
        INSERT INTO tasks
        (user_id, guild_id, task, created_at)
        VALUES (?, ?, ?, ?)
        """,
        (
            user_id,
            guild_id,
            task,
            datetime.now(timezone.utc).isoformat()
        )
    )

    conn.commit()
    task_id = cursor.lastrowid
    conn.close()

    return task_id

def get_tasks(user_id, guild_id):
    conn = get_connection()

    tasks = conn.execute(
        """
        SELECT *
        FROM tasks
        WHERE user_id = ?  AND guild_id = ?
        ORDER BY completed ASC, id DESC
        """,
        (user_id, guild_id)
    ).fetchall()

    conn.close()
    return tasks

def complete_task(task_id, user_id, guild_id):
    conn = get_connection()

    task = conn.execute(
        """
        SELECT *
        FROM tasks
        WHERE id = ? AND user_id = ? AND guild_id = ?
        """,
        (task_id, user_id, guild_id)
    ).fetchone()

    if task is None:
        conn.close()
        return False

    if task["completed"]:
        conn.close()
        return False

    conn.execute(
        """
        UPDATE tasks
        SET completed = 1
        WHERE id = ?
        """,
        (task_id,)
    )

    conn.commit()
    conn.close()

    return True

def delete_task(task_id, user_id, guild_id):
    conn =  get_connection()

    cursor = conn.execute(
        """
        DELETE FROM tasks
        WHERE id = ? AND user_id = ? AND guild_id = ?
        """,
        (task_id, user_id, guild_id)
    )

    conn.commit()

    deleted = cursor.rowcount > 0

    conn.close()

    return deleted

def get_pet(guild_id):
    conn = get_connection()

    pet = conn.execute(
        """
        SELECT *
        FROM pets
        WHERE guild_id = ?
        """,
        (guild_id,)
    ).fetchone()

    if pet is None:
        conn.execute(
            """
            INSERT INTO pets
            (guild_id, name, hunger, happiness, energy)
            VALUES (?, 'Pulse', 80, 80, 80)
            """,
            (guild_id,)
        )

        conn.commit()

        pet = conn.execute(
            """
            SELECT *
            FROM pets
            WHERE guild_id = ?
            """,
            (guild_id,)
        ).fetchone()

    conn.close()
    return pet

def update_pet(guild_id, hunger=0, happiness=0, energy=0):
    pet = get_pet(guild_id)

    new_hunger = max(0,min(100, pet["hunger"] + hunger))
    new_happiness = max(0, min(100, pet["happiness"] + happiness))
    new_energy = max(0, min(100, pet["energy"] + energy))

    conn = get_connection()

    conn.execute(
        """
        UPDATE pets
        SET hunger = ?, happiness = ?, energy = ?
        WHERE guild_id = ?
        """,
        (
            new_hunger,
            new_happiness,
            new_energy,
            guild_id
        )
    )

    conn.commit()
    conn.close()

    return get_pet(guild_id)