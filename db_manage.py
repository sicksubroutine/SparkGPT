from flask import g
import sqlite3
DATABASE = "prime_database.db"

class DatabaseManager:

  def __init__(self, open_db):
    self.open_db = open_db
    self.setup_database()

  def setup_database(self):
    self.conn = self.open_db()
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
          summary TEXT DEFAULT '',
          short_summary TEXT DEFAULT '',
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
        
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            amount INTEGER,
            memo TEXT,
            payment_request TEXT,
            payment_hash TEXT,
            invoice_status TEXT,
            FOREIGN KEY (username) REFERENCES users (username)
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

  def insert_conversation(self, username, prompt, chosen_prompt):
      
        cursor = self.conn.cursor()
        cursor.execute("INSERT INTO conversations (username, prompt) VALUES (?, ?)", (username, prompt))
        conversation_id = cursor.lastrowid
        self.conn.commit()

        cursor.execute("INSERT INTO conversation_history (conversation_id, role, content) VALUES (?, ?, ?)",
                       (conversation_id, 'system', chosen_prompt))
        conversation_history_id = cursor.lastrowid
        self.conn.commit()

        cursor.execute("INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
                       (conversation_id, 'system', chosen_prompt))
        message_id = cursor.lastrowid
        self.conn.commit()

        conversation_data = {
            "conversation_id": conversation_id,
            "conversation_history_id": conversation_history_id,
            "message_id": message_id
        }
        return conversation_data
  
  def reset_conversation(self, conversation_id):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE conversation_id=? AND role=?", (conversation_id, 'system'))
    system_message = cursor.fetchone()
    self.conn.execute("DELETE FROM messages WHERE conversation_id=? AND id!=?", (conversation_id, system_message[0]))
    self.conn.commit()
    # do the same for the conversation_history
    cursor.execute("SELECT * FROM conversation_history WHERE conversation_id=? AND role=?", (conversation_id, 'system'))
    system_message = cursor.fetchone()
    self.conn.execute("DELETE FROM conversation_history WHERE conversation_id=? AND id!=?", (conversation_id, system_message[0]))
    self.conn.commit()

  def delete_conversation(self, conversation_id):
    self.conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id, ))
    self.conn.commit()

  def update_conversation_summaries(self, conversation_id, long_summary, short_summary):
    self.conn.execute('''
        UPDATE conversations
        SET summary = ?, short_summary = ?
        WHERE id = ?
    ''', (long_summary, short_summary, conversation_id))
    self.conn.commit()

  def get_conversation_summaries(self, conversation_id):
    cursor = self.conn.cursor()
    cursor.execute("SELECT summary, short_summary FROM conversations WHERE id=?",
                   (conversation_id, ))
    return cursor.fetchone()
  
  
  def reset_conversation_summaries(self, conversation_id):
    self.conn.execute('''
        UPDATE conversations
        SET summary = '', short_summary = ''
        WHERE id = ?
    ''', (conversation_id, ))
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
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

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
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

  def insert_message(self, conversation_id, role, content):
    cursor = self.conn.cursor()
    cursor.execute(
      "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
      (conversation_id, role, content))
    self.conn.commit()
    return cursor.lastrowid
  
  def delete_message(self, conversation_id, message_id):
    cursor = self.conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id=? AND id=?", (conversation_id, message_id))
    self.conn.commit()

  def get_messages(self, conversation_id):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM messages WHERE conversation_id=?",
                   (conversation_id, ))
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

  def insert_payment(self, username, amount, memo, payment_request, payment_hash, invoice_status):
    self.conn.execute(
        '''
        INSERT INTO payments (username, amount, memo, payment_request, payment_hash, invoice_status)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, amount, memo, payment_request, payment_hash, invoice_status))
    self.conn.commit()

  def get_payment(self, payment_hash):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE payment_hash=?", (payment_hash,))
    return cursor.fetchone()

  def get_all_payments(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM payments")
    return cursor.fetchall()

  def update_payment(self, payment_hash, field, value):
    self.conn.execute(f"UPDATE payments SET {field}=? WHERE payment_hash=?",
                      (value, payment_hash))
    self.conn.commit()
      
  def get_invoice_status(self, payment_hash):
    cursor = self.conn.cursor()
    cursor.execute("SELECT invoice_status FROM payments WHERE payment_hash=?", (payment_hash,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

  def delete_payment(self, payment_hash):
    self.conn.execute("DELETE FROM payments WHERE payment_hash=?", (payment_hash,))
    self.conn.commit()

  def delete_all_payments(self):
    self.conn.execute("DELETE FROM payments")
    self.conn.commit()


def open_db():
  if 'database' not in g:
    g.database = sqlite3.connect(DATABASE)
    g.database.row_factory = sqlite3.Row
  return g.database


def close_db(error):
  if 'database' in g:
    g.database.close()


def before_request():
  g.d_base = DatabaseManager(open_db)
