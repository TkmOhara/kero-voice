import sqlite3
from contextlib import contextmanager


class Database:
    def __init__(self, db_path: str = "kero_voice.db"):
        self.db_path = db_path
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """コネクションのコンテキストマネージャー"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_db(self):
        """データベースの初期化"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # speakersテーブル（音声ファイル一覧）
            # name: 表示名（ボタンラベル）、filepath: 実際のファイルパス
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    filepath TEXT NOT NULL
                )
            """)

            # user_speakersテーブル（ユーザーと話者の紐付け）
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_speakers (
                    user_id INTEGER PRIMARY KEY,
                    speaker_id INTEGER NOT NULL,
                    FOREIGN KEY (speaker_id) REFERENCES speakers(id)
                )
            """)

    def get_speakers(self) -> list[dict]:
        """スピーカー一覧を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, filepath FROM speakers ORDER BY name")
            return [dict(row) for row in cursor.fetchall()]

    def get_speaker_by_id(self, speaker_id: int) -> dict | None:
        """IDでスピーカーを取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, filepath FROM speakers WHERE id = ?",
                (speaker_id,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def set_user_speaker(self, user_id: int, speaker_id: int) -> bool:
        """ユーザーの話者を設定"""
        # スピーカーが存在するか確認
        if not self.get_speaker_by_id(speaker_id):
            return False

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO user_speakers (user_id, speaker_id)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET speaker_id = ?
            """, (user_id, speaker_id, speaker_id))

        return True

    def get_user_speaker(self, user_id: int) -> dict | None:
        """ユーザーの話者を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.name, s.filepath
                FROM user_speakers us
                JOIN speakers s ON us.speaker_id = s.id
                WHERE us.user_id = ?
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def remove_user_speaker(self, user_id: int) -> bool:
        """ユーザーの話者設定を削除"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM user_speakers WHERE user_id = ?", (user_id,))
            return cursor.rowcount > 0

    def add_speaker(self, name: str, filepath: str) -> int | None:
        """スピーカーを追加し、IDを返す"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO speakers (name, filepath) VALUES (?, ?)",
                    (name, filepath)
                )
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                return None  # 重複

    def get_speaker_by_name(self, name: str) -> dict | None:
        """名前でスピーカーを取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, name, filepath FROM speakers WHERE name = ?",
                (name,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    def delete_speaker(self, speaker_id: int) -> bool:
        """スピーカーを削除"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # 関連するuser_speakersも削除
            cursor.execute("DELETE FROM user_speakers WHERE speaker_id = ?", (speaker_id,))
            cursor.execute("DELETE FROM speakers WHERE id = ?", (speaker_id,))
            return cursor.rowcount > 0
