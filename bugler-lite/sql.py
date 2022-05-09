import datetime
import sqlite3
import bugzilla
import sys

conn = sqlite3.connect('test.db')
print("数据库打开成功")
c = conn.cursor()


def chang_sql():
    addColumn = "ALTER TABLE BUG ADD COLUMN site text"
    c.execute(addColumn)
    conn.commit()
    conn.close()


def create_sql():
    c.execute('''CREATE TABLE BUG
        (ID integer PRIMARY KEY      autoincrement,
        NUMBER  INT     NOT NULL,
        SUMMARY           TEXT    NOT NULL,
        COMPONENT      TEXT     NOT NULL,
        OWNER            TEXT,
        TIME           timestamp,
        STATUS         TEXT,
        SITE        TEXT  NOT NULL);''')
    print("数据表创建成功")


def insert_sql(number, summary, component, owner='', time='', status='open'):
    c.execute("INSERT INTO BUG (NUMBER,SUMMARY,OWNER,TIME,STATUS,COMPONENT) \
       VALUES (?,?,?,?,?,? )", (number, summary, owner, time, status, component))
    conn.commit()
    print("数据插入成功")


def select_sql_all():
    cursor = c.execute("SELECT number from BUG")
    for row in cursor:
        #     print("ID = ", row[0])
        x = row[0]
        sql_update_query = """Update BUG set SITE=? where number = ?"""
        data = ("https://bugs.gentoo.org/xmlrpc.cgi/" + str(x), int(x))
        c.execute(sql_update_query, data)
        conn.commit()
    #     print("SUMMARY = ", row[2])
    #     print("OWNER = ", row[3])
    #     print("TIME = ", row[4])
    #     print("STATUS = ", row[5], "\n")

    cursor.close()


def select_sql(id):
    sqlite_select_query = """SELECT id,number,summary,owner,time,status,component,site from BUG where id=?"""
    cursor = c.execute(sqlite_select_query, (id,))
    records = cursor.fetchall()
    for row in records:
        print("ID = ", row[0])
        print("NUMBER = ", row[1])
        print("SUMMARY = ", row[2])
        print("OWNER = ", row[3])
        print("TIME = ", row[4])
        print("STATUS = ", row[5])
        print("COMPONENT = ", row[6])
        print("SITE = ", row[7])

        cursor.close()


def like_sql():
    sql_like_query = """SELECT * FROM BUG WHERE instr(component,'Keywording')>0 and instr(status,'blocked')<=0 AND instr(status,'resolved')<=0 AND
        instr(status,'closed')<=0 GROUP BY number"""
    cursor = c.execute(sql_like_query)
    for row in cursor:
        print("ID = ", row[0])
        print("NUMBER = ", row[1])
        print("SUMMARY = ", row[2])
        print("OWNER = ", row[3])
        print("TIME = ", row[4])
        print("STATUS = ", row[5])
        print("COMPONENT = ", row[6], "\n")
    cursor.close()


def check_status(number):
    sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where number=?"""
    cursor = c.execute(sqlite_select_query, (int(number),))
    records = cursor.fetchall()
    print(records)
    for row in records:
        owner = row[3]
        status = row[5]
    return owner, status


create_sql()
# sqlite_select_query = """SELECT site  from BUG where id=?"""
# cursor = c.execute(sqlite_select_query, (int(2),))
# records = cursor.fetchall()
# for row in records:
#     site = row[0]
#     print(type(site))

# for x in range(len(bugs)):
#    insert_sql(bugs[x].id, bugs[x].summary, bugs[x].component)
#
# #update_sql(1,"yu",datetime.datetime.now(),"solved")
# chang_sql()
# like_sql()
# select_sql_all()
# select_sql()
