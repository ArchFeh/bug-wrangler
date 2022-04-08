import socket
import sqlite3
import time
import datetime
import bugzilla
import schedule

conn = sqlite3.connect('test.db')
c = conn.cursor()
#static_bugs = []
ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server = "irc.libera.chat"  # Server
channel = "#name"
botnick = ""  # Your bots nick.
password = ""

adminname = ""  # Your IRC nickname.
exitcode = "bye " + botnick  # Text that we will use
ircsock.connect((server, 6667))  # Here we connect to the server using the port 6667
ircsock.send(
    bytes("USER " + botnick + " " + botnick + " " + botnick + " " + botnick + "\n", "UTF-8"))  # user information
ircsock.send(bytes("NICK " + botnick + "\n", "UTF-8"))  # assign the nick to the bot
ircsock.send(bytes("NICKSERV IDENTIFY " + adminname + " " + password + "\n", "UTF-8"))
msg_help = ["bugler is a irc bot for gentoo riscv team to conveniently handle bugs which "
            "posted in bugzilla. ",
            "changelog: when bugs are closed by b.g.o, notify."
            "fix fatal wrong in update bugs",
            "add private message support, you can do what you want without spam your channel",
            "To use this bot, command: .b cmd.",
            "commands: block, check, drop, fuzzy, help, kw, pick, query, rcheck, resolve, status",
            "block: block one bug, and it won't shown in query default",
            "check:check one bug's information. Example: .b check Id/Bug number",
            "drop:drop one bug",
            "fuzzy: search bug by keywords",
            "help:show this help",
            "kw:show keyword bugs.",
            "pick:show your willing to solve this bug. Example: .b pick Id/Bug number.",
            "query:query all the active bugs which are related with riscv. To show all bugs, use query all",
            "rcheck: search bug by owner. Example: .b rcheck irc-name.",
            "resolve: change the status of bug to resolved. example: .b resolve Id/Bug number"
            ]


def joinchan(chan):  # join channel(s).

    ircsock.send(bytes("JOIN " + chan + "\n", "UTF-8"))

    ircmsg = ""
    while ircmsg.find("End of /NAMES list.") == -1:
        ircmsg = ircsock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        print(ircmsg)


def ping():  # respond to server Pings.
    ircsock.send(bytes("PONG :pingis\n", "UTF-8"))


def sendmsg(msg, target=channel):  # sends messages to the target.
    # With this we are sending a ‘PRIVMSG’ to the channel. The ":” lets the server separate the target and the message.
    ircsock.send(bytes("PRIVMSG " + target + " :" + msg + "\n", "UTF-8"))


def insert_sql(number, summary, owner='', time='', status=''):
    c.execute("INSERT INTO BUG (NUMBER,SUMMARY,OWNER,TIME,STATUS) \
       VALUES (?,?,?,?,? )", (number, summary, owner, time, status))
    conn.commit()
    print("Successfully inserted")


def get_bugs():
    URL = "https://bugs.gentoo.org/xmlrpc.cgi"
    bzapi = bugzilla.Bugzilla(URL)
    query = bzapi.url_to_query("") #search filed
    query["include_fields"] = ["id", "summary"]
    bugs = bzapi.query(query)
    return bugs


def diff(listA, listB):
    retD = list(set(listB).difference(set(listA)))
    return retD


def make_static_list(list):
    listatic = []
    for x in range(len(list)):
        listatic.append(list[x].id)
    return listatic


def make_new_list(list):
    listnew = []
    for x in range(len(list)):
        listnew.append(list[x].id)
    return listnew


def job():
    global static_bugs
    new_bugs = get_bugs()
    print("static_bugs vs new_bugs: ", len(static_bugs) == len(new_bugs))
    static_list = make_static_list(static_bugs)
    new_list = make_new_list(new_bugs)
    ret = diff(static_list, new_list)
    ret_closed = diff(new_list, static_list)
    print("ret= ", ret)
    print("ret_closed= ", ret_closed)
    print("len of listnew: ", len(new_list), "len of listatic: ", len(static_list))
    if ret:
        print("New add: ", ret)
        i = 0
        for x in ret:
            print(x)
            index = new_list.index(x)
            print(index)
            print(len(new_bugs))
            print("New bug:", new_bugs[index].id, new_bugs[index].summary)
            insert_sql(new_bugs[index].id, new_bugs[index].summary)
            conn.commit()
            sendmsg("New Bug:" + str(new_bugs[index].id) + ' ' + new_bugs[index].summary)
            if i % 5 == 0:
                time.sleep(4)
    else:
        print("Nothing new")

    if ret_closed:
        print("Closed: ", ret)
        i = 0
        for x in ret_closed:
            print(x)
            index = static_list.index(x)
            print(index)
            print(len(static_bugs))
            print("Closed bug:", static_bugs[index].id, static_bugs[index].summary)
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
            data = ('b.g.o', datetime.datetime.now(), "closed", static_bugs[index].id)
            c.execute(sql_update_query, data)
            conn.commit()
            sendmsg("Bug closed by b.g.o:" + str(static_bugs[index].id) + ' ' + static_bugs[index].summary)
            if i % 5 == 0:
                time.sleep(4)
    else:
        print("Nothing closed")

    static_bugs = new_bugs
    print(static_bugs == new_bugs)


def help(target=channel):
    i = 0
    for x in msg_help:
        i = i + 1
        sendmsg(x, target)
        if i % 5 == 0:
            time.sleep(4)


def pick(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
            data = (name, datetime.datetime.now(), "doing", int(number))
            c.execute(sql_update_query, data)
            conn.commit()
            sendmsg(name + " picked" + ' ' + number + " status:doing", target)
        else:
            sendmsg(name + " picked wrong ID (out of list)", target)
    else:
        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
        data = (name, datetime.datetime.now(), "doing", int(number))
        c.execute(sql_update_query, data)
        conn.commit()
        sendmsg(name + " picked" + ' ' + number + " status:doing", target)


def block(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
            data = (name, datetime.datetime.now(), "blocked", int(number))
            c.execute(sql_update_query, data)
            conn.commit()
            sendmsg(name + " blocked" + ' ' + number + " status:blocked", target)
        else:
            sendmsg(name + " picked wrong ID (out of list)", target)
    else:
        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
        data = (name, datetime.datetime.now(), "blocked", int(number))
        c.execute(sql_update_query, data)
        conn.commit()
        sendmsg(name + " blocked" + ' ' + number + " status:blocked", target)


def check(number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where id=?"""
            cursor = c.execute(sqlite_select_query, (int(number),))
            records = cursor.fetchall()
            for row in records:
                sendmsg("ID: " +
                        str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                            2] + " Owner: " +
                        row[3] + " Time: " + row[4] + " Status: " +
                        row[5], target)
        else:
            sendmsg(" checked wrong ID (out of list)", target)

    else:
        sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where number=?"""
        cursor = c.execute(sqlite_select_query, (int(number),))
        records = cursor.fetchall()
        for row in records:
            sendmsg("ID: " +
                    str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                        2] + " Owner: " +
                    row[3] + " Time: " + row[4] + " Status: " +
                    row[5], target)


def drop(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
            data = (name, datetime.datetime.now(), "dropped", int(number))
            c.execute(sql_update_query, data)
            conn.commit()
            sendmsg(name + " dropped" + ' ' + number + " status:dropped", target)
        else:
            sendmsg(name + " picked wrong ID (out of list)", target)
    else:
        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
        data = (name, datetime.datetime.now(), "dropped", int(number))
        c.execute(sql_update_query, data)
        conn.commit()
        sendmsg(name + " dropped" + ' ' + number + " status:dropped", target)


def fuzzy(keyword, target=channel):
    sql_like_query = """SELECT * FROM BUG WHERE instr(summary,?)>0 GROUP BY number"""
    cursor = c.execute(sql_like_query, (keyword,))
    i = 0
    for row in cursor:
        i = i + 1
        sendmsg("ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Owner: " +
                row[3] + " Time: " + row[4] + " Status: " +
                row[5], target)
        if i % 5 == 0:
            time.sleep(4)


def kw(target=channel):
    sql_like_query = """SELECT * FROM BUG WHERE instr(summary,'keyword')>0 OR instr(summary,'support')>0 GROUP BY number"""
    cursor = c.execute(sql_like_query)
    i = 0
    for row in cursor:
        i = i + 1
        sendmsg("ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Owner: " +
                row[3] + " Time: " + row[4] + " Status: " +
                row[5], target)
        if i % 5 == 0:
            time.sleep(4)


def query(opt='', target=channel):
    if opt == "all":
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        i = 0
        for row in cursor:
            i = i + 1
            sendmsg("ID: " +
                    str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                        2] + " Owner: " +
                    row[3] + " Time: " + row[4] + " Status: " +
                    row[5], target)
            if i % 5 == 0:
                time.sleep(4)

    else:
        sql_like_query = """SELECT * FROM BUG WHERE instr(status,'blocked')<=0 GROUP BY id"""
        cursor = c.execute(sql_like_query)
        i = 0
        for row in cursor:
            i = i + 1
            sendmsg("ID: " +
                    str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                        2] + " Owner: " +
                    row[3] + " Time: " + row[4] + " Status: " +
                    row[5], target)
            if i % 5 == 0:
                time.sleep(4)


def rcheck(owner, target=channel):
    sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where owner=?"""
    cursor = c.execute(sqlite_select_query, (owner,))
    records = cursor.fetchall()
    for row in records:
        sendmsg("ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Owner: " +
                row[3] + " Time: " + row[4] + " Status: " +
                row[5], target)


def resolve(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
            data = (name, datetime.datetime.now(), "resolved", int(number))
            c.execute(sql_update_query, data)
            conn.commit()
            sendmsg(name + " resolved" + ' ' + number + " status:resolved", target)
        else:
            sendmsg(name + " picked wrong ID (out of list)", target)
    else:
        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
        data = (name, datetime.datetime.now(), "resolved", int(number))
        c.execute(sql_update_query, data)
        conn.commit()
        sendmsg(name + " resolved" + ' ' + number + " status:resolved", target)


def status(stat, target=channel):
    sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where status=?"""
    cursor = c.execute(sqlite_select_query, (stat,))
    records = cursor.fetchall()
    for row in records:
        sendmsg("ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Owner: " +
                row[3] + " Time: " + row[4] + " Status: " +
                row[5], target)



static_bugs = get_bugs()
for x in range(len(static_bugs)):
    insert_sql(static_bugs[x].id, static_bugs[x].summary)
    conn.commit()



def main():
    joinchan(channel)
    schedule.every(300).seconds.do(job)
    while 1:
        schedule.run_pending()
        ircmsg = ircsock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        print(ircmsg)

        if ircmsg.find("PRIVMSG") != -1 and ircmsg.find(channel) != -1:
            name = ircmsg.split('!', 1)[0][1:]
            message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]
            if len(name) < 17:
                if message.find('Hi ' + botnick) != -1:
                    sendmsg("Hello " + name + "!")
                elif message[:2].find('.b') != -1:

                    if len(message) <= 2:
                        sendmsg("Correct usage: .b help")
                    elif len(message) > 2:
                        if message.split(' ', 2)[2:] != []:
                            print("more than 2 arguements")
                            command = message.split(" ", 2)[1]
                            subcomand = message.split(" ", 2)[2]
                            print(command + " " + subcomand)
                            if command == "pick":
                                pick(name, subcomand)


                            elif command == "query" and subcomand == "all":
                                query(subcomand)

                            elif command == "resolve":
                                resolve(name, subcomand)

                            elif command == "drop":
                                drop(name, subcomand)

                            elif command == "block":
                                block(name, subcomand)

                            elif command == "check":
                                check(subcomand)

                            elif command == "rcheck":
                                rcheck(subcomand)

                            elif command == "status":
                                status(subcomand)

                            elif command == "fuzzy":
                                fuzzy(subcomand)


                        else:
                            command = message.split(' ', 1)[1]
                            print("one command ", command)
                            if command == "help":
                                help()

                            elif command == "query":
                                query()

                            elif command == "kw":
                                kw()

                elif name.lower() == adminname.lower() and message.rstrip() == exitcode:
                    sendmsg("Bye everyone I hope all bugs free)")
                    ircsock.send(bytes("QUIT \n", "UTF-8"))
                    conn.close()
                    return
                # else:
                #     message = "Could not parse. The message should be in the format of ‘.b [cmd]’ to work properly."
                #     sendmsg(message)
        elif ircmsg.find("PRIVMSG") != -1 and ircmsg.find(botnick) != -1:
            name = ircmsg.split('!', 1)[0][1:]
            message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]
            if len(name) < 17:
                if message.find('Hi ' + botnick) != -1:
                    sendmsg("Hello " + name + "!", name)
                elif message[:2].find('.b') != -1:

                    if len(message) <= 2:
                        sendmsg("Correct usage: .b help", name)
                    elif len(message) > 2:
                        if message.split(' ', 2)[2:] != []:
                            print("more than 2 arguements")
                            command = message.split(" ", 2)[1]
                            subcomand = message.split(" ", 2)[2]
                            print(command + " " + subcomand)
                            if command == "pick":
                                pick(name, subcomand, name)

                            elif command == "query" and subcomand == "all":
                                query(subcomand, name)

                            elif command == "resolve":
                                resolve(name, subcomand, name)

                            elif command == "drop":
                                drop(name, subcomand, name)

                            elif command == "block":
                                block(name, subcomand, name)

                            elif command == "check":
                                check(subcomand, name)
                            elif command == "rcheck":
                                rcheck(subcomand, name)

                            elif command == "status":
                                status(subcomand, name)

                            elif command == "fuzzy":
                                fuzzy(subcomand, name)

                        else:
                            command = message.split(' ', 1)[1]
                            print("one command ", command)
                            if command == "help":
                                help(name)

                            elif command == "query":
                                query(target=name)

                            elif command == "kw":
                                kw(name)

                elif name.lower() == adminname.lower() and message.rstrip() == exitcode:
                    sendmsg("Bye everyone I hope all bugs free)", name)
                    ircsock.send(bytes("QUIT \n", "UTF-8"))
                    conn.close()
                    return
                # else:
                #     message = "Could not parse. The message should be in the format of ‘.b [cmd]’ to work properly."
                #     sendmsg(message)
        else:
            if ircmsg.find("PING :") != -1:
                ping()


main()
conn.close()
