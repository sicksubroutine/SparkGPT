from flask import g
import os
from pysqlcipher3 import dbapi2 as sqlite
from pathlib import Path

env_file = Path(".env")

if env_file.exists():
  from dotenv import load_dotenv
  load_dotenv()
  print(" * Loading .env file")
else:
  print(" * Not loading .env file")

DATABASE = "prime_database.db"
PASSPHRASE = os.environ["DATABASE_PASSPHRASE"]

class DatabaseManager:

  def __init__(self, open_db):
    self.open_db = open_db
    self.setup_database()

  def setup_database(self):
    self.conn = self.open_db()
    schema = '''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            salt TEXT,
            ip_address TEXT,
            uuid TEXT,
            user_agent TEXT,
            identity_hash TEXT,
            sats INTEGER,
            recently_paid BOOLEAN,
            creation_date TEXT,
            last_login TEXT DEFAULT '',
            admin BOOLEAN DEFAULT FALSE
        );
        
        CREATE TABLE IF NOT EXISTS conversations (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          username TEXT,
          model TEXT,
          title TEXT,
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

  def insert_user(
    self,
    username:str,
    password:str,
    salt:str,
    ip_address:str,
    uuid:str,
    user_agent:str,
    identity_hash:str,
    sats:int,
    recently_paid:bool,
    creation_date:str
  ):
    self.conn.execute(
      '''
      INSERT INTO users(
        username, 
        password, 
        salt, 
        ip_address, 
        uuid, 
        user_agent, 
        identity_hash, 
        sats, 
        recently_paid,
        creation_date,
        last_login,
        admin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ''', (
        username, 
        password, 
        salt, 
        ip_address, 
        uuid, 
        user_agent, 
        identity_hash, 
        sats, 
        recently_paid,
        creation_date,
        'Never logged in',
        False
      ))
    self.conn.commit()

  def get_user(self, username:str):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username, ))
    return cursor.fetchone()
    
  """def get_all_users(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM users")
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]"""

  def update_user(self, username:str, field:str, value):
    self.conn.execute(f"UPDATE users SET {field}=? WHERE username=?",
                      (value, username))
    self.conn.commit()

  def delete_user(self, username:str):
    self.conn.execute("DELETE FROM users WHERE username=?", (username, ))
    self.conn.commit()

  def insert_conversation(
    self, 
    username:str, 
    model:str, 
    title:str, 
    prompt:str, 
    prompt_text:str
  ):
        cursor = self.conn.cursor()
        cursor.execute(
          """
          INSERT INTO conversations 
          (username, model, title, prompt) VALUES (?, ?, ?, ?)
          """, 
          (username, model, title, prompt)
        )
        conversation_id = cursor.lastrowid
        self.conn.commit()

        cursor.execute("""INSERT INTO conversation_history 
                      (conversation_id, role, content) 
                       VALUES (?, ?, ?)""",
                       (conversation_id, 'system', prompt_text))
        conversation_history_id = cursor.lastrowid
        self.conn.commit()

        cursor.execute("""INSERT INTO messages (conversation_id, role, content) 
                      VALUES (?, ?, ?)""",
                       (conversation_id, 'system', prompt_text))
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
    cursor.execute("SELECT * FROM messages WHERE conversation_id=? AND role=?", 
                   (conversation_id, 'system'))
    system_message = cursor.fetchone()
    self.conn.execute("DELETE FROM messages WHERE conversation_id=? AND id!=?", 
                      (conversation_id, system_message[0]))
    self.conn.commit()
    
    cursor.execute("""SELECT * FROM conversation_history 
                  WHERE conversation_id=? AND role=?""", (conversation_id, 'system'))
    system_message = cursor.fetchone()
    self.conn.execute("""DELETE FROM conversation_history WHERE conversation_id=? 
                      AND id!=?""", (conversation_id, system_message[0]))
    self.conn.commit()

  def delete_conversation(self, conversation_id):
    self.conn.execute("DELETE FROM conversations WHERE id=?", (conversation_id, ))
    self.conn.commit()

  def update_conversation_summaries(
    self, 
    conversation_id, 
    long_summary:str, 
    short_summary:str
  ):
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
    
  def get_conversations_for_user(self, username:str):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM conversations WHERE username=?",
                   (username, ))
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]


  def get_user_info(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT username, sats, admin, creation_date, last_login FROM users")
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    users = [dict(zip(columns, row)) for row in rows]
    for user in users:
      username = user['username']
      cursor.execute("SELECT COUNT(*) FROM conversations WHERE username=?",(username, ))
      user['conversation_count'] = cursor.fetchone()[0]
    return users
  
  def insert_conversation_history(
    self, 
    conversation_id, 
    role:str, 
    content:str
  ):
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

  def insert_message(self, conversation_id, role:str, content:str):
    cursor = self.conn.cursor()
    cursor.execute(
      "INSERT INTO messages (conversation_id, role, content) VALUES (?, ?, ?)",
      (conversation_id, role, content))
    self.conn.commit()
    return cursor.lastrowid
  
  def delete_oldest_message(self, conversation_id):
    cursor = self.conn.cursor()
    cursor.execute("""SELECT content FROM messages WHERE conversation_id=? AND
                   role!='system' ORDER BY id ASC LIMIT 1""",
                    (conversation_id, ))
    message = cursor.fetchone()
    if not message:
      return None
    message_content = message[0]
    cursor.execute("""DELETE FROM messages WHERE conversation_id=? AND
                   id IN (SELECT id FROM messages WHERE conversation_id=? AND
                   role!='system' ORDER BY id ASC LIMIT 1)""",
                    (conversation_id, conversation_id))
    self.conn.commit()
    return message_content
  
  def delete_message(self, conversation_id, message_id):
    cursor = self.conn.cursor()
    cursor.execute("DELETE FROM messages WHERE conversation_id=? AND id=?", 
                   (conversation_id, message_id))
    self.conn.commit()
    
  def delete_conversation_history(self, conversation_id, message_id):
    cursor = self.conn.cursor()
    cursor.execute("DELETE FROM conversation_history WHERE conversation_id=? AND id=?", 
                   (conversation_id, message_id))
    self.conn.commit()

  def get_messages(self, conversation_id) -> list:
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM conversation_history WHERE conversation_id=?",
                   (conversation_id, ))
    rows = cursor.fetchall()
    columns = [col[0] for col in cursor.description]
    return [dict(zip(columns, row)) for row in rows]

  def insert_payment(
    self, 
    username:str, 
    amount:int, 
    memo:str, 
    payment_request:str, 
    payment_hash:str, 
    invoice_status:str
    ):
    self.conn.execute(
        '''
        INSERT INTO payments 
        (username, amount, memo, payment_request, payment_hash, invoice_status)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (username, amount, memo, payment_request, payment_hash, invoice_status))
    self.conn.commit()

  def get_payment(self, payment_hash:str):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM payments WHERE payment_hash=?", (payment_hash,))
    return cursor.fetchone()

  def get_all_payments(self):
    cursor = self.conn.cursor()
    cursor.execute("SELECT * FROM payments")
    return cursor.fetchall()

  def update_payment(self, payment_hash:str, field:str, value):
    self.conn.execute(f"UPDATE payments SET {field}=? WHERE payment_hash=?",
                      (value, payment_hash))
    self.conn.commit()
      
  def get_invoice_status(self, payment_hash:str):
    cursor = self.conn.cursor()
    cursor.execute("SELECT invoice_status FROM payments WHERE payment_hash=?", 
                   (payment_hash,))
    result = cursor.fetchone()
    if result:
        return result[0]
    else:
        return None

  def delete_payment(self, payment_hash:str):
    self.conn.execute("DELETE FROM payments WHERE payment_hash=?", (payment_hash,))
    self.conn.commit()

  def delete_all_payments(self):
    self.conn.execute("DELETE FROM payments")
    self.conn.commit()
  
  def is_database_encrypted(self):
    try:
        cursor = self.conn.cursor()
        cursor.execute('PRAGMA cipher_version')
        result = cursor.fetchone()
        if result is not None:
            return True
        else:
            return False
    except Exception as e:
        print(f"Error checking if database is encrypted: {e}")
        return False


def open_db():
  if 'database' not in g:
    g.database = sqlite.connect(DATABASE) # type: ignore
    g.database.execute(f"PRAGMA key='{PASSPHRASE}'")
    g.database.execute("PRAGMA cipher_compatibility = 4")
    g.database.execute("PRAGMA kdf_iter = 64000")
    g.database.execute("PRAGMA cipher_page_size = 4096")
    g.database.execute("PRAGMA cipher_hmac_algorithm = HMAC_SHA512")
    g.database.execute("PRAGMA cipher_kdf_algorithm = PBKDF2_HMAC_SHA512")
    g.database.execute("PRAGMA cipher_use_hmac = ON")
    g.database.execute("PRAGMA cipher_plaintext_header_size = 0")
    g.database.execute("PRAGMA journal_mode = WAL")
    g.database.execute("PRAGMA synchronous = NORMAL")
    g.database.row_factory = sqlite.Row # type: ignore
  return g.database


def close_db(error):
  if 'database' in g:
    g.database.close()


def before_request():
  g.base = DatabaseManager(open_db)
