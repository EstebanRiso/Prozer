
import sqlite3
import json

DB_NAME = "mydata.db"

def init_db():
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    
    cur.execute('''
        CREATE TABLE IF NOT EXISTS scrape_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS process_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS combined_data (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT
        )
    ''')
    
    con.commit()
    con.close()

def save_scrape_data(json_data):

    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    data_text = json.dumps(json_data)
    cur.execute("INSERT INTO scrape_data (data) VALUES (?)", (data_text,))
    con.commit()
    con.close()

def save_process_data(json_data):

    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    data_text = json.dumps(json_data)
    cur.execute("INSERT INTO process_data (data) VALUES (?)", (data_text,))
    con.commit()
    con.close()

def save_combined_data(json_data):

    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    data_text = json.dumps(json_data)
    cur.execute("INSERT INTO combined_data (data) VALUES (?)", (data_text,))
    con.commit()
    con.close()

def get_scrape_data():

    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("SELECT id, data FROM scrape_data")
    rows = cur.fetchall()
    con.close()

    results = []
    for row_id, data_text in rows:
        data_obj = json.loads(data_text)
        results.append({"id": row_id, "data": data_obj})
    return results

def get_process_data():

    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("SELECT id, data FROM process_data")
    rows = cur.fetchall()
    con.close()

    results = []
    for row_id, data_text in rows:
        data_obj = json.loads(data_text)
        results.append({"id": row_id, "data": data_obj})
    return results

def get_combined_data():
  
    con = sqlite3.connect(DB_NAME)
    cur = con.cursor()
    cur.execute("SELECT id, data FROM combined_data")
    rows = cur.fetchall()
    con.close()

    results = []
    for row_id, data_text in rows:
        data_obj = json.loads(data_text)
        results.append({"id": row_id, "data": data_obj})
    return results