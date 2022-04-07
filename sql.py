import sqlite3

conn = sqlite3.connect('test.db')
print("Successfully opened database")
c = conn.cursor()

def create_sql():
    c.execute('''CREATE TABLE BUG
        (ID integer PRIMARY KEY      autoincrement,
        NUMBER  INT     NOT NULL,
        SUMMARY           TEXT    NOT NULL,
        OWNER            TEXT,
        TIME           timestamp,
        STATUS         TEXT);''')
    print("Successfully created table")

create_sql()
