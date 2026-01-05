import sqlite3
import json
import time
import os

DB_FILE = "cache.db"

class DatabaseManager:
    def __init__(self, db_file=DB_FILE):
        self.db_file = db_file
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_file)

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        # 歌词缓存表
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lyrics_cache (
                song_id INTEGER PRIMARY KEY,
                data TEXT,
                updated_at REAL
            )
        ''')
        
        # 歌曲搜索/详情缓存表 (可选，暂存)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS song_info_cache (
                song_id INTEGER PRIMARY KEY,
                data TEXT,
                updated_at REAL
            )
        ''')
        
        conn.commit()
        conn.close()

    def get_lyrics(self, song_id):
        """获取缓存的歌词"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT data FROM lyrics_cache WHERE song_id = ?', (song_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            try:
                return json.loads(row[0])
            except:
                return None
        return None

    def save_lyrics(self, song_id, data):
        """保存歌词到缓存"""
        conn = self._get_connection()
        cursor = conn.cursor()
        now = time.time()
        json_str = json.dumps(data, ensure_ascii=False)
        
        cursor.execute('''
            INSERT OR REPLACE INTO lyrics_cache (song_id, data, updated_at)
            VALUES (?, ?, ?)
        ''', (song_id, json_str, now))
        
        conn.commit()
        conn.close()
        print(f"💾 [Cache] 歌词已缓存 ID: {song_id}")

# 全局实例
db = DatabaseManager()
