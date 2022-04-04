import datetime
import sqlite3
import bugzilla
import sys

URL = "https://bugs.gentoo.org/xmlrpc.cgi"
bzapi = bugzilla.Bugzilla(URL)
query = bzapi.url_to_query(
    "https://bugs.gentoo.org/buglist.cgi?email2=riscv%40gentoo.org&emailassigned_to2=1&emailcc2=1&emailreporter2=1&emailtype2=substring&known_name=riscv&list_id=6087782&query_based_on=riscv&query_format=advanced&resolution=---")
query["include_fields"] = ["id", "summary"]
bugs = bzapi.query(query)

conn = sqlite3.connect('test.db')
print("数据库打开成功")
c = conn.cursor()


def create_sql():
    c.execute('''CREATE TABLE BUG
        (ID INT PRIMARY KEY     NOT NULL,
        NUMBER  INT     NOT NULL,
        SUMMARY           TEXT    NOT NULL,
        OWNER            TEXT,
        TIME           timestamp,
        STATUS         TEXT);''')
    print("数据表创建成功")


def insert_sql(id, number, summary, owner='', time='', status=''):
    c.execute("INSERT INTO BUG (ID,NUMBER,SUMMARY,OWNER,TIME,STATUS) \
       VALUES (?,?,?,?,?,? )", (id, number, summary, owner, time, status))
    conn.commit()
    print("数据插入成功")


def select_sql_all():
    cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
    for row in cursor:
        print("ID = ", row[0])
        print("NUMBER = ", row[1])
        print("SUMMARY = ", row[2])
        print("OWNER = ", row[3])
        print("TIME = ", row[4])
        print("STATUS = ", row[5], "\n")
    print("数据操作成功")
    cursor.close()

def select_sql(id):
    sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where id=?"""
    cursor = c.execute(sqlite_select_query,(id,))
    records=cursor.fetchall()
    for row in records:
        print("ID = ", row[0])
        print("NUMBER = ", row[1])
        print("SUMMARY = ", row[2])
        print("OWNER = ", row[3])
        print("TIME = ", row[4])
        print("STATUS = ", row[5], "\n")
    cursor.close()

def update_sql(id,owner='', time=datetime.datetime.now(), status=''):
    sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
    data=(owner,time, status,id)
    c.execute(sql_update_query,data)

def like_sql():
    sql_like_query = """SELECT * FROM BUG WHERE instr(summary,'keyword')>0 OR instr(summary,'support')>0 GROUP BY number"""
    cursor =  c.execute(sql_like_query)
    for row in cursor:
        print("ID = ", row[0])
        print("NUMBER = ", row[1])
        print("SUMMARY = ", row[2])
        print("OWNER = ", row[3])
        print("TIME = ", row[4])
        print("STATUS = ", row[5], "\n")
    cursor.close()

# create_sql()
# for x in range(len(bugs)):
#     insert_sql(x,bugs[x].id,bugs[x].summary)

#update_sql(1,"yu",datetime.datetime.now(),"solved")
#select_sql(0)
like_sql()
conn.commit()

conn.close()

if sys.argv[1] == 'query':
    query_bug()
if sys.argv[1] == 'pick':
    pick_bug(sys.argv[2])
