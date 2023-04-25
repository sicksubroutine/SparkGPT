import sqlite3

class DatabaseManager:

  def __init__(self, db_name):
    self.conn = sqlite3.connect(db_name)
    self.setup_database()

  def setup_database(self):
    schema = '''
      CREATE TABLE IF NOT EXISTS users (
          username TEXT PRIMARY KEY,
          ip_address TEXT,
          uuid TEXT,
          user_agent TEXT,
          identity_hash TEXT,
          sats INTEGER,
          recently_paid BOOLEAN
      );

      CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT,
          prompt TEXT,
          FOREIGN KEY (username) REFERENCES users (username)
      );

      CREATE TABLE IF NOT EXISTS conversation_history (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id INTEGER,
          role TEXT,
          content TEXT,
          FOREIGN KEY (conversation_id) REFERENCES conversations (id)
      );

      CREATE TABLE IF NOT EXISTS messages (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          conversation_id INTEGER,
          role TEXT,
          content TEXT,
          FOREIGN KEY (conversation_id) REFERENCES conversations (id)
      );
      '''
    self.conn.executescript(schema)
    self.conn.commit()

  def insert_user(self, username, ip_address, uuid, user_agent, identity_hash):
    self.conn.execute(
      '''
          INSERT INTO users (username, ip_address, uuid, user_agent, identity_hash, sats, recently_paid)
          VALUES (?, ?, ?, ?, ?, ?, ?)
      ''', (username, ip_address, uuid, user_agent, identity_hash, 0, False))
    self.conn.commit()

  def get_user(self, username):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username, ))
    return cursor.fetchone()
    
  def get_all_users(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM users")
    return cursor.fetchall()

  def update_user(self, username, field, value):
    self.conn.execute(f"UPDATE users SET {field}=? WHERE username=?",
                      (value, username))
    self.conn.commit()

  def delete_user(self, username):
    self.conn.execute("DELETE FROM users WHERE username=?", (username, ))
    self.conn.commit()

  def insert_conversation(self, username, prompt):
    cursor = self.conn.cursor()
    cursor.execute(
      "INSERT INTO conversations (username, prompt) VALUES (?, ?)",
      (username, prompt))
    self.conn.commit()
    return cursor.lastrowid

  def update_conversation_summaries(self, conversation_id, long_summary, short_summary):
    self.conn.execute('''
        UPDATE conversations
        SET summary = ?, short_summary = ?
        WHERE id = ?
    ''', (long_summary, short_summary, conversation_id))
    self.conn.commit()

  def get_conversation(self, conversation_id):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE id=?",
                   (conversation_id, ))
    return cursor.fetchone()

  def get_conversations_for_user(self, username):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE username=?",
                   (username, ))
    return cursor.fetchall()

  def insert_conversation_history(self, conversation_id, role, content):
    cursor = self.conn.cursor()
    cursor.execute(
      "INSERT INTO conversation_history (conversation_id, role, content) VALUES (?, ?, ?)",
      (conversation_id, role, content))
    self.conn.commit()
    return cursor.lastrowid

  def get_conversation_history(self, conversation_id):
    cursor = self.conn.cursor()
    cursor.execute(
      "SELECT * FROM conversation_history WHERE conversation_id=?",
      (conversation_id, ))
    return cursor.fetchall()

  def insert_message(self, conversation_id, role, content):
    cursor = self.conn.cursor()
    cursor.execute(
      "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
      (conversation_id, role, content))
    self.conn.commit()
    return cursor.lastrowid

  def get_messages(self, conversation_id):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE conversation_id=?",
                   (conversation_id, ))
    return cursor.fetchall()