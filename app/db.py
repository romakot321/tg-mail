import sqlite3


class DBService:
    def __init__(self):
        self.connection = sqlite3.connect('data/data.db', check_same_thread=False)
        self.connection.row_factory = sqlite3.Row
        self.cursor = self.connection.cursor()

        self.migrate()

    def migrate(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                id BIGINT PRIMARY KEY
            );
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS mails (
                id INTEGER PRIMARY KEY,
                sender VARCHAR(255),
                date VARCHAR(100),
                text TEXT,
                html TEXT,
                created_at VARCHAR(100) DEFAULT (DATETIME('now'))
            );
        ''')
        self.connection.commit()

    def list_chats_ids(self) -> list[int]:
        self.cursor.execute('SELECT id FROM chats;')
        return list(map(lambda i: list(i)[0], self.cursor.fetchall()))

    def add_chat_id(self, chat_id: int) -> int | None:
        try:
            self.cursor.execute('INSERT INTO chats(id) VALUES (?)', (chat_id,))
            self.connection.commit()
            return self.cursor.lastrowid
        except sqlite3.IntegrityError:
            self.connection.rollback()
            return None

    def list_mails(self) -> list[dict]:
        self.cursor.execute("SELECT * FROM mails;")
        return list(map(dict, self.cursor.fetchall()))

    def get_mail(self, mail_id: int) -> dict:
        self.cursor.execute("SELECT * FROM mails WHERE id=?;", (mail_id,))
        return dict(self.cursor.fetchone())

    def add_mail(self, sender, date: str, text, html) -> int:
        self.cursor.execute(
            "INSERT INTO mails(sender, date, text, html) VALUES (?, ?, ?, ?)",
            (sender, date, text, html)
        )
        self.connection.commit()
        return self.cursor.lastrowid


if __name__ == "__main__":
    service = DBService()
    print(service.list_mails()[-1]["html"])

