import sqlite3
from pathlib import Path
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
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS speakers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL UNIQUE,
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

    def refresh_speakers(self, audiofiles_dir: str):
        """audiofilesディレクトリからスピーカー一覧を更新（新規ファイルのみ追加）"""
        audio_extensions = {".mp3", ".wav"}
        audiofiles_path = Path(audiofiles_dir)

        # 音声ファイル一覧を取得
        audio_files = []
        if audiofiles_path.exists():
            for f in audiofiles_path.iterdir():
                if f.is_file() and f.suffix.lower() in audio_extensions:
                    audio_files.append((f.name, str(f.absolute())))

        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 既存のファイル名を取得
            cursor.execute("SELECT filename FROM speakers")
            existing_filenames = {row[0] for row in cursor.fetchall()}

            # 新規ファイルのみ挿入
            new_files = [
                (filename, filepath)
                for filename, filepath in audio_files
                if filename not in existing_filenames
            ]

            if new_files:
                cursor.executemany(
                    "INSERT INTO speakers (filename, filepath) VALUES (?, ?)",
                    new_files
                )

            # ディレクトリに存在しないファイルを削除
            current_filenames = {filename for filename, _ in audio_files}
            removed_filenames = existing_filenames - current_filenames
            if removed_filenames:
                cursor.executemany(
                    "DELETE FROM speakers WHERE filename = ?",
                    [(fn,) for fn in removed_filenames]
                )

        total = len(audio_files)
        added = len(new_files)
        removed = len(removed_filenames) if 'removed_filenames' in dir() else 0
        print(f"Speakers refreshed: {total} files (added: {added}, removed: {removed})")
        return total

    def get_speakers(self) -> list[dict]:
        """スピーカー一覧を取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, filename, filepath FROM speakers ORDER BY filename")
            return [dict(row) for row in cursor.fetchall()]

    def get_speaker_by_id(self, speaker_id: int) -> dict | None:
        """IDでスピーカーを取得"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, filename, filepath FROM speakers WHERE id = ?",
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
                SELECT s.id, s.filename, s.filepath
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
