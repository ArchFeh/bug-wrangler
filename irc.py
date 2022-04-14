import socket
import sqlite3
import time
import datetime
import bugzilla
import schedule
from urllib.error import HTTPError

conn = sqlite3.connect('test.db')
c = conn.cursor()
ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ircsock.settimeout(240)
server = "irc.libera.chat"  # Server
channel = ""
botnick = "bugler"  # Your bots nick.
password = ''

adminname = ""  # Your IRC nickname.
exitcode = "bye " + botnick  # Text that we will use

msg_help = ["Bugler is a irc bot for gentoo riscv team to conveniently handle bugs which "
            "posted in bugzilla. This is a easy-learned project, everyone can easily run or rewrite.",
            "changelog: exceptions handling to keep bot working"
            "when bugs are closed by b.g.o, notify."
            "fix fatal wrong in update bugs",
            "add private message support, you can do what you want without spam your channel",
            "To use this bot, command: .b cmd.",
            "commands: block, check, drop, fuzzy, help, kw, pick, query, rcheck, resolve, status",
            "block: block one bug, it won't be shown in query default mode and changed status",
            "check:check one bug's information. Example: .b check Id/Bug number",
            "close:close one bug"
            "drop:drop one bug, so others can take it",
            "fuzzy: search bug by keywords",
            "help:show this help",
            "kw:show keyword bugs.",
            "pick:show your willing to solve this bug. Example: .b pick Id/Bug number.",
            "query:query all the active bugs which are related with riscv. To show all bugs, use query all",
            "rcheck: search bug by owner. Example: .b rcheck irc-name.",
            "resolve: change the status of bug to resolved so the status can't be changed. example: .b resolve Id/Bug number"
            ]
stat_unchangeable = ['closed', 'resolved', 'blocked', 'doing']
stat_changeable = ['dropped', '', ]


def irc_connect():
    ircsock.connect((server, 6667))  # Here we connect to the server using the port 6667
    ircsock.send(
        bytes("USER " + botnick + " " + botnick + " " + botnick + " " + botnick + "\n", "UTF-8"))  # user information
    ircsock.send(bytes("NICK " + botnick + "\n", "UTF-8"))  # assign the nick to the bot
    ircsock.send(bytes("NICKSERV IDENTIFY " + adminname + " " + password + "\n", "UTF-8"))


def joinchan(chan):  # join channel(s).

    ircsock.send(bytes("JOIN " + chan + "\n", "UTF-8"))

    ircmsg = ""
    while ircmsg.find("End of /NAMES list.") == -1:
        ircmsg = ircsock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        print(ircmsg)


def ping(message):  # respond to server Pings.
    ircsock.send(bytes("PONG " + message + "\r\n", "UTF-8"))


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
    query = bzapi.url_to_query(
        "https://bugs.gentoo.org/buglist.cgi?email2=riscv%40gentoo.org&emailassigned_to2=1&emailcc2=1&emailreporter2=1&emailtype2=substring&known_name=riscv&list_id=6094577&query_based_on=riscv&query_format=advanced&resolution=---")
    query["include_fields"] = ["id", "summary"]
    bugs = bzapi.query(query)
    return bugs


def diff(listA, listB):
    retD = list(set(listB).difference(set(listA)))
    return retD


def make_static_list(list):
    list_static = []
    for x in range(len(list)):
        list_static.append(list[x].id)
    return list_static


def make_new_list(list):
    list_new = []
    for x in range(len(list)):
        list_new.append(list[x].id)
    return list_new


def make_sql_list():
    list_sql = []
    cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
    i = 0
    for row in cursor:
        list_sql.append(row[1])
    return list_sql


def job():
    bugs_in_sql = make_sql_list()
    try:
        new_bugs = get_bugs()
    except HTTPError as err:
        print(err.code, err.reason)
    else:
        # print("static_bugs vs new_bugs: ", len(static_bugs) == len(new_bugs))
        # static_list = make_static_list(static_bugs)
        new_list = make_new_list(new_bugs)
        ret = diff(bugs_in_sql, new_list)
        ret_closed = diff(new_list, bugs_in_sql)
        # print("ret= ", ret)
        # print("ret_closed= ", ret_closed)
        # print("len of list_new: ", len(new_list), "len of list_static: ", len(static_list))
        if ret:
            print("New add: ", ret)
            i = 0
            for x in ret:
                # print(x)
                index = new_list.index(x)
            i = 0
            for x in ret:
                # print(x)
                index = new_list.index(x)
                # print(index)
                # print(len(new_bugs))
                print("New bug:", new_bugs[index].id, new_bugs[index].summary)
                insert_sql(new_bugs[index].id, new_bugs[index].summary)
                conn.commit()
                sendmsg("New Bug calling: " + str(new_bugs[index].id) + ' ' + new_bugs[index].summary)
                if i % 5 == 0:
                    time.sleep(4)
        else:
            print("Nothing new")

        if ret_closed:
            i = 0
            for x in ret_closed:
                # print(x)
                # index = bugs_in_sql.index(x)
                # print(index)
                # print(len(static_bugs))
                sqlite_select_query = """SELECT number,summary,owner,status from BUG where number=?"""
                cursor = c.execute(sqlite_select_query, (int(x),))
                records = cursor.fetchall()
                for row in records:
                    number = row[0]
                    summary = row[1]
                    owner = row[2]
                    status_in = row[3]
                if status_in != 'closed':
                    print("Closed bug: " + str(number) + " " + summary)
                    # owner = check_status(bugs_in_sql[index].id)[0]
                    if owner == '':
                        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                        data = ('b.g.o', datetime.datetime.now(), "closed", number)
                        c.execute(sql_update_query, data)
                        sendmsg(
                            "Bug closed in b.g.o. All peace! Owner: b.g.o. " + str(number) + ' ' + summary)
                    else:
                        sql_update_query = """Update BUG set TIME=?,STATUS=? where number = ?"""
                        data = (datetime.datetime.now(), "closed", number)
                        c.execute(sql_update_query, data)
                        sendmsg("Ura! Bug closed in b.g.o. Thanks " + owner + "! Cheers! " + str(number) + ' ' +
                                summary)
                    conn.commit()
                    if i % 5 == 0:
                        time.sleep(4)
        else:
            print("Nothing closed")


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
            if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
                if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                    1] == 'blocked':
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + ", no need to change, all peace!", target)
                else:
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + " has focused on it, Let's look forward to his results!", target)
            elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                    check_status(number)[1] in stat_changeable:
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                data = (name, datetime.datetime.now(), "doing", int(number))
                sendmsg(name + " picked" + ' ' + number + "! Owner: " + check_status(number)[
                    0] + " --> " + name + " Status: " + check_status(number)[1] + " --> doing", target)
                c.execute(sql_update_query, data)
                conn.commit()

        else:
            sendmsg(name + " picked wrong ID (out of list)", target)
    else:
        if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
            if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                1] == 'blocked':
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + ", no need to change, all peace!", target)
            else:
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + " has focused on it, Let's look forward to his results!", target)
        elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                check_status(number)[1] in stat_changeable:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
            data = (name, datetime.datetime.now(), "doing", int(number))
            sendmsg(name + " picked" + ' ' + number + "! Owner: " + check_status(number)[
                0] + " --> " + name + " Status: " + check_status(number)[1] + " --> doing", target)
            c.execute(sql_update_query, data)
            conn.commit()


def close(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
                if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                    1] == 'blocked':
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + ", no need to change, all peace!", target)
                else:
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + " has focused on it, Let's look forward to his results!", target)
            elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                    check_status(number)[1] in stat_changeable:
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                data = (name, datetime.datetime.now(), "closed", int(number))
                sendmsg("Ura! " + name + " closed" + ' ' + number + "! Status: " + check_status(number)[
                    1] + " --> closed. Cheers!", target)
                c.execute(sql_update_query, data)
                conn.commit()

        else:
            sendmsg(name + " picked wrong ID (out of list)", target)
    else:
        if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
            if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                1] == 'blocked':
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + ", no need to change, all peace!", target)
            else:
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + " has focused on it, Let's look forward to his results!", target)
        elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                check_status(number)[1] in stat_changeable:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
            data = (name, datetime.datetime.now(), "closed", int(number))
            sendmsg("Ura! " + name + " closed" + ' ' + number + "! Status: " + check_status(number)[
                1] + " --> closed. Cheers!", target)
            c.execute(sql_update_query, data)
            conn.commit()


def block(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
                if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                    1] == 'blocked':
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + ", no need to change, all peace!", target)
                else:
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + " has focused on it, Let's look forward to his results!", target)
            elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                    check_status(number)[1] in stat_changeable:
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                data = (name, datetime.datetime.now(), "blocked", int(number))
                sendmsg(name + " blocked" + ' ' + number + "! Status: " + check_status(number)[1] + " --> blocked",
                        target)
                c.execute(sql_update_query, data)
                conn.commit()

        else:
            sendmsg(name + " blocked wrong ID (out of list)", target)
    else:
        if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
            if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                1] == 'blocked':
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + ", no need to change, all peace!", target)
            else:
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + " has focused on it, Let's look forward to his results!", target)
        elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                check_status(number)[1] in stat_changeable:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
            data = (name, datetime.datetime.now(), "blocked", int(number))
            sendmsg(name + " blocked" + ' ' + number + "! Status: " + check_status(number)[1] + " --> blocked", target)
            c.execute(sql_update_query, data)
            conn.commit()


def drop(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
                if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                    1] == 'blocked':
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + ", no need to change, all peace!", target)
                else:
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + " has focused on it, Let's look forward to his results!", target)
            elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                    check_status(number)[1] in stat_changeable:
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                data = ('', datetime.datetime.now(), "dropped", int(number))
                sendmsg(name + " dropped" + ' ' + number + "! Status: " + check_status(number)[
                    1] + " --> dropped. People can pick this bug again!", target)
                c.execute(sql_update_query, data)
                conn.commit()

        else:
            sendmsg(name + " dropped wrong ID (out of list)", target)
    else:
        if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
            if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                1] == 'blocked':
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + ", no need to change, all peace!", target)
            else:
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + " has focused on it, Let's look forward to his results!", target)
        elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                check_status(number)[1] in stat_changeable:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
            data = ('', datetime.datetime.now(), "dropped", int(number))
            sendmsg(name + " dropped" + ' ' + number + "! Status: " + check_status(number)[
                1] + " --> dropped. People can pick this bug again!", target)
            c.execute(sql_update_query, data)
            conn.commit()


def resolve(name, number, target=channel):
    if int(number) <= 5000:
        count = 0
        cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
        for row in cursor:
            count = count + 1
        if int(number) <= count:
            if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
                if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                    1] == 'blocked':
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + ", no need to change, all peace!", target)
                else:
                    sendmsg(
                        "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                            0] + " has focused on it, Let's look forward to his results!", target)
            elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                    check_status(number)[1] in stat_changeable:
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                data = (name, datetime.datetime.now(), "resolved", int(number))
                sendmsg("Ura! " + name + " resolved" + ' ' + number + "! Status: " + check_status(number)[
                    1] + " --> resolved. Cheers!", target)
                c.execute(sql_update_query, data)
                conn.commit()

        else:
            sendmsg(name + " picked wrong ID (out of list)", target)
    else:
        if check_status(number)[1] in stat_unchangeable and check_status(number)[0] != name:
            if check_status(number)[1] == 'closed' or check_status(number)[1] == 'resolved' or check_status(number)[
                1] == 'blocked':
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + ", no need to change, all peace!", target)
            else:
                sendmsg(
                    "Bug: " + number + " Status: " + check_status(number)[1] + "! Owner: " + check_status(number)[
                        0] + " has focused on it, Let's look forward to his results!", target)
        elif (check_status(number)[0] == name and check_status(number)[1] in stat_unchangeable) or \
                check_status(number)[1] in stat_changeable:
            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
            data = (name, datetime.datetime.now(), "resolved", int(number))
            sendmsg("Ura! " + name + " resolved" + ' ' + number + "! Status: " + check_status(number)[
                1] + " --> resolved. Cheers!", target)
            c.execute(sql_update_query, data)
            conn.commit()


def check_status(number):
    if int(number) <= 5000:
        sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where id=?"""
        cursor = c.execute(sqlite_select_query, (int(number),))
        records = cursor.fetchall()
        for row in records:
            owner = row[3]
            stat = row[5]
        return owner, stat

    else:
        sqlite_select_query = """SELECT id,number,summary,owner,time,status  from BUG where number=?"""
        cursor = c.execute(sqlite_select_query, (int(number),))
        records = cursor.fetchall()
        for row in records:
            owner = row[3]
            stat = row[5]
        return owner, stat


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
        sendmsg("Owner: " +
                row[3] + " ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Time: " + row[4] + " Status: " +
                row[5], target)


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


# static_bugs = get_bugs_old()


# for x in range(len(static_bugs)):
#    insert_sql(static_bugs[x].id, static_bugs[x].summary)
#    conn.commit()


def main():
    irc_connect()
    joinchan(channel)
    schedule.every(300).seconds.do(job)
    while 1:
        try:
            ircmsg = ircsock.recv(2048).decode("UTF-8")
            ircmsg = ircmsg.strip('\n\r')
            print(ircmsg)
            schedule.run_pending()

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
                            if message.split(' ', 2)[2:] != [] and message.split(' ', 3)[3:] == []:
                                print("more than 2 arguements")
                                command = message.split(" ", 2)[1]
                                subcomand = message.split(" ", 2)[2]
                                print(command + " " + subcomand)
                                if command == "pick":
                                    pick(name, subcomand)

                                elif command == "close":
                                    close(name, subcomand)

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
                            if message.split(' ', 2)[2:] != [] and message.split(' ', 3)[3:] == []:
                                print("more than 2 arguements")
                                command = message.split(" ", 2)[1]
                                subcomand = message.split(" ", 2)[2]
                                print(command + " " + subcomand)
                                if command == "pick":
                                    pick(name, subcomand, name)

                                elif command == "close":
                                    close(name, subcomand, name)

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

            else:
                if ircmsg.find("PING :") != -1:
                    message = ircmsg.split(':')[1]
                    ping(message)
                    print(message)
        except socket.timeout:
            ircsock.close()
            irc_connect()
            joinchan(channel)


main()
conn.close()
