import socket
import sqlite3
import time
import datetime
import bugzilla
import schedule
import re
import xmlrpc

conn = sqlite3.connect('test.db')
c = conn.cursor()
ircsock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server = "irc.libera.chat"  # Server
channel = ""
botnick = ""  # Your bots nick.
password = ''

adminname = ""  # Your IRC nickname.
exitcode = "bye " + botnick  # Text that we will use

stat_unchangeable = ['closed', 'resolved', 'blocked', 'doing']
stat_changeable = ['open', ]


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


def insert_sql(number, summary, component, site, owner='', time='', status='open'):
    c.execute("INSERT INTO BUG (NUMBER,SUMMARY,COMPONENT,OWNER,TIME,STATUS,SITE) \
       VALUES (?,?,?,?,?,?,? )", (number, summary, component, owner, time, status, site))
    conn.commit()
    print("Successfully inserted")


def get_bugs():
    URL = "https://bugs.gentoo.org/xmlrpc.cgi"
    bzapi = bugzilla.Bugzilla(URL)
    query = bzapi.url_to_query(
        "https://bugs.gentoo.org/buglist.cgi?email2=riscv%40gentoo.org&emailassigned_to2=1&emailcc2=1&emailreporter2=1&emailtype2=substring&known_name=riscv&list_id=6094577&query_based_on=riscv&query_format=advanced&resolution=---")
    query["include_fields"] = ["id", "summary", "component"]
    bugs = bzapi.query(query)
    return bugs


def diff(listA, listB):
    retD = list(set(listB).difference(set(listA)))
    return retD


def make_new_list(list):
    list_new = []
    for x in range(len(list)):
        list_new.append(list[x].id)
    return list_new


def make_sql_list():
    list_sql = []
    cursor = c.execute("SELECT number from BUG")
    i = 0
    for row in cursor:
        list_sql.append(row[0])
    return list_sql


def update_sql():
    bugs_in_sql = make_sql_list()
    new_bugs = get_bugs()
    new_list = make_new_list(new_bugs)
    ret = diff(bugs_in_sql, new_list)
    ret_closed = diff(new_list, bugs_in_sql)
    if ret:
        print("New add: ", ret)
        i = 0
        for x in ret:
            index = new_list.index(x)
            print("New bug:", new_bugs[index].id, new_bugs[index].summary, new_bugs[index].component)
            insert_sql(new_bugs[index].id, new_bugs[index].summary, new_bugs[index].component,
                       "https://bugs.gentoo.org/" + str(new_bugs[index].id))
            conn.commit()
            sendmsg("New bug calling: " + str(new_bugs[index].id) + '; ' + new_bugs[index].summary + '; ' + new_bugs[
                index].component + " https://bugs.gentoo.org/" + str(new_bugs[index].id))
            if i % 5 == 0:
                time.sleep(4)
    else:
        print("Nothing new")

    if ret_closed:
        i = 0
        for x in ret_closed:
            sqlite_select_query = """SELECT number,summary,component,owner,status from BUG where number=?"""
            cursor = c.execute(sqlite_select_query, (int(x),))
            records = cursor.fetchall()
            for row in records:
                number = row[0]
                summary = row[1]
                component = row[2]
                owner = row[3]
                status_in = row[4]
            if status_in != 'closed':
                print("Closed bug: " + str(number) + " " + summary)
                if owner == '':
                    sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                    data = ('b.g.o', datetime.datetime.now(), "closed", number)
                    c.execute(sql_update_query, data)
                    sendmsg(
                        "Bug closed in b.g.o. All peace! Owner: b.g.o. " + str(
                            number) + ' ' + summary + ' ' + component + " https://bugs.gentoo.org/" + str(number))
                else:
                    sql_update_query = """Update BUG set TIME=?,STATUS=? where number = ?"""
                    data = (datetime.datetime.now(), "closed", number)
                    c.execute(sql_update_query, data)
                    sendmsg("Ura! Bug closed in b.g.o. Thanks " + owner + "! Cheers! " + str(number) + ' ' +
                            summary + ' ' + component + " https://bugs.gentoo.org/" + str(number))
                conn.commit()
                if i % 5 == 0:
                    time.sleep(4)


def help(target=channel):
    sendmsg("https://telegra.ph/Help-for-Bugler-04-26", target)


def pick(name, number, target=channel):
    if number.isdigit():
        if int(number) <= 5000:
            count = 0
            cursor = c.execute("SELECT id  from BUG")
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
                    sqlite_select_query = """SELECT site  from BUG where id=?"""
                    cursor = c.execute(sqlite_select_query, (int(number),))
                    records = cursor.fetchall()
                    for row in records:
                        site = row[0]
                    sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                    data = (name, datetime.datetime.now(), "doing", int(number))
                    sendmsg(name + " picked" + ' ' + number + "! Owner: " + check_status(number)[
                        0] + " --> " + name + " Status: " + check_status(number)[
                                1] + " --> doing " + site, target)
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
                sqlite_select_query = """SELECT site  from BUG where number=?"""
                cursor = c.execute(sqlite_select_query, (int(number),))
                records = cursor.fetchall()
                for row in records:
                    site = row[0]
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                data = (name, datetime.datetime.now(), "doing", int(number))
                sendmsg(name + " picked" + ' ' + number + "! Owner: " + check_status(number)[
                    0] + " --> " + name + " Status: " + check_status(number)[
                            1] + " --> doing " + site, target)
                c.execute(sql_update_query, data)
                conn.commit()


def close(name, number, target=channel):
    if number.isdigit():
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
                    sqlite_select_query = """SELECT site  from BUG where id=?"""
                    cursor = c.execute(sqlite_select_query, (int(number),))
                    records = cursor.fetchall()
                    for row in records:
                        site = row[0]
                    sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                    data = (name, datetime.datetime.now(), "closed", int(number))
                    sendmsg("Ura! " + name + " closed" + ' ' + number + "! Status: " + check_status(number)[
                        1] + " --> closed. Cheers! " + site, target)
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
                sqlite_select_query = """SELECT site  from BUG where number=?"""
                cursor = c.execute(sqlite_select_query, (int(number),))
                records = cursor.fetchall()
                for row in records:
                    site = row[0]
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                data = (name, datetime.datetime.now(), "closed", int(number))
                sendmsg("Ura! " + name + " closed" + ' ' + number + "! Status: " + check_status(number)[
                    1] + " --> closed. Cheers! " + site, target)
                c.execute(sql_update_query, data)
                conn.commit()


def block(name, number, target=channel):
    if number.isdigit():
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
                    sqlite_select_query = """SELECT site  from BUG where id=?"""
                    cursor = c.execute(sqlite_select_query, (int(number),))
                    records = cursor.fetchall()
                    for row in records:
                        site = row[0]
                    sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                    data = (name, datetime.datetime.now(), "blocked", int(number))
                    sendmsg(name + " blocked" + ' ' + number + "! Status: " + check_status(number)[
                        1] + " --> blocked " + site,
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
                sqlite_select_query = """SELECT site  from BUG where number=?"""
                cursor = c.execute(sqlite_select_query, (int(number),))
                records = cursor.fetchall()
                for row in records:
                    site = row[0]
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                data = (name, datetime.datetime.now(), "blocked", int(number))
                sendmsg(name + " blocked" + ' ' + number + "! Status: " + check_status(number)[
                    1] + " --> blocked " + site, target)
                c.execute(sql_update_query, data)
                conn.commit()


def drop(name, number, target=channel):
    if number.isdigit():
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
                    sqlite_select_query = """SELECT site  from BUG where id=?"""
                    cursor = c.execute(sqlite_select_query, (int(number),))
                    records = cursor.fetchall()
                    for row in records:
                        site = row[0]
                    sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                    data = ('', datetime.datetime.now(), "open", int(number))
                    sendmsg(name + " dropped" + ' ' + number + "! Status: " + check_status(number)[
                        1] + " --> open. People can pick this bug again! " + site,
                            target)
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
                sqlite_select_query = """SELECT site  from BUG where number=?"""
                cursor = c.execute(sqlite_select_query, (int(number),))
                records = cursor.fetchall()
                for row in records:
                    site = row[0]
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                data = ('', datetime.datetime.now(), "open", int(number))
                sendmsg(name + " dropped" + ' ' + number + "! Status: " + check_status(number)[
                    1] + " --> open. People can pick this bug again! " + site, target)
                c.execute(sql_update_query, data)
                conn.commit()


def resolve(name, number, target=channel):
    if number.isdigit():
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
                    sqlite_select_query = """SELECT site  from BUG where id=?"""
                    cursor = c.execute(sqlite_select_query, (int(number),))
                    records = cursor.fetchall()
                    for row in records:
                        site = row[0]
                    sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                    data = (name, datetime.datetime.now(), "resolved", int(number))
                    sendmsg("Ura! " + name + " resolved" + ' ' + number + "! Status: " + check_status(number)[
                        1] + " --> resolved. Cheers! " + site, target)
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
                sqlite_select_query = """SELECT site  from BUG where number=?"""
                cursor = c.execute(sqlite_select_query, (int(number),))
                records = cursor.fetchall()
                for row in records:
                    site = row[0]
                sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                data = (name, datetime.datetime.now(), "resolved", int(number))
                sendmsg("Ura! " + name + " resolved" + ' ' + number + "! Status: " + check_status(number)[
                    1] + " --> resolved. Cheers! " + site, target)
                c.execute(sql_update_query, data)
                conn.commit()


def check_status(number):
    if int(number) <= 5000:
        sqlite_select_query = """SELECT owner,status  from BUG where id=?"""
        cursor = c.execute(sqlite_select_query, (int(number),))
        records = cursor.fetchall()
        if records != []:
            for row in records:
                owner = row[0]
                stat = row[1]
            return owner, stat

    else:
        sqlite_select_query = """SELECT owner,status  from BUG where number=?"""
        cursor = c.execute(sqlite_select_query, (int(number),))
        records = cursor.fetchall()
        if records != []:
            for row in records:
                owner = row[0]
                stat = row[1]
            return owner, stat


def check(number, target=channel):
    if number.isdigit():
        if int(number) <= 5000:
            count = 0
            cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
            for row in cursor:
                count = count + 1
            if int(number) <= count:
                sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where id=?"""
                cursor = c.execute(sqlite_select_query, (int(number),))
                records = cursor.fetchall()
                for row in records:
                    sendmsg("ID: " +
                            str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                                2] + " Component: " + row[3] + " Owner: " +
                            row[4] + " Time: " + row[5] + " Status: " +
                            row[6] + " " + row[7], target)
            else:
                sendmsg(" checked wrong ID (out of list)", target)

        else:
            sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where number=?"""
            cursor = c.execute(sqlite_select_query, (int(number),))
            records = cursor.fetchall()
            for row in records:
                sendmsg("ID: " +
                        str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                            2] + " Component: " + row[3] + " Owner: " +
                        row[4] + " Time: " + row[5] + " Status: " +
                        row[6] + " " + row[7], target)


def fuzzy(keyword, target=channel):
    sql_like_query = """SELECT * FROM BUG WHERE instr(summary,?)>0 GROUP BY number"""
    cursor = c.execute(sql_like_query, (keyword,))
    i = 0
    for row in cursor:
        i = i + 1
        sendmsg("ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Component: " + row[3] + " Owner: " +
                row[4] + " Time: " + row[5] + " Status: " +
                row[6] + " " + row[7], target)
        if i % 5 == 0:
            time.sleep(4)
    sendmsg("Found: " + str(i), target)



def kw(target=channel):
    sql_like_query = """SELECT * FROM BUG WHERE instr(component,'Keywording')>0 and instr(status,'blocked')<=0 AND instr(status,'resolved')<=0 AND
                instr(status,'closed')<=0 GROUP BY number"""
    cursor = c.execute(sql_like_query)
    i = 0
    for row in cursor:
        i = i + 1
        sendmsg("ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Component: " + row[3] + " Owner: " +
                row[4] + " Time: " + row[5] + " Status: " +
                row[6] + " " + row[7], target)
        if i % 5 == 0:
            time.sleep(4)
    sendmsg("Active component: Keywords: " + str(i), target)


def query(opt='', target=channel):
    if opt == "all":
        cursor = c.execute("SELECT id,number,summary,component,owner,time,status,site  from BUG")
        i = 0
        for row in cursor:
            i = i + 1
            sendmsg("ID: " +
                    str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                        2] + " Component: " + row[3] + " Owner: " +
                    row[4] + " Time: " + row[5] + " Status: " +
                    row[6] + " " + row[7], target)
            if i % 5 == 0:
                time.sleep(4)
        sendmsg("All bugs: " + str(i), target)
    else:
        sql_like_query = """SELECT * FROM BUG WHERE instr(status,'blocked')<=0 AND instr(status,'resolved')<=0 AND instr(status,'closed')<=0 GROUP BY id """
        cursor = c.execute(sql_like_query)
        i = 0
        for row in cursor:
            i = i + 1
            sendmsg("ID: " +
                    str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                        2] + " Component: " + row[3] + " Owner: " +
                    row[4] + " Time: " + row[5] + " Status: " +
                    row[6] + " " + row[7], target)
            if i % 5 == 0:
                time.sleep(4)
        sendmsg("Active bugs: " + str(i), target)


def owner(owner, target=channel):
    sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where owner=?"""
    cursor = c.execute(sqlite_select_query, (owner,))
    records = cursor.fetchall()
    i = 0
    for row in records:
        i = i + 1
        sendmsg("Owner: " +
                row[4] + " ID: " +
                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                    2] + " Component: " + row[3] + " Time: " + row[5] + " Status: " +
                row[6] + " " + row[7], target)
        if i % 5 == 0:
            time.sleep(4)
    sendmsg(owner+" has " + str(i)+" bugs.", target)



def status(stat, target=channel):
    if stat in stat_unchangeable or stat in stat_changeable:
        sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where status=?"""
        cursor = c.execute(sqlite_select_query, (stat,))
        records = cursor.fetchall()
        i = 0
        for row in records:
            i = i + 1
            sendmsg("ID: " +
                    str(row[0]) + " bug " + str(row[1]) + " Title: " + row[
                        2] + " Component: " + row[3] + " Owner: " +
                    row[4] + " Time: " + row[5] + " Status: " +
                    row[6] + " " + row[7], target)
            if i % 5 == 0:
                time.sleep(4)
        sendmsg(str(i)+" bugs "+stat, target)


def willikins(mess):
    bug_list = re.findall('bug\s\d{6}', mess)
    if bug_list:
        URL = "https://bugs.gentoo.org/xmlrpc.cgi"
        bzapi = bugzilla.Bugzilla(URL)
        for i in bug_list:
            try:
                bzapi.getbug(i.split(None)[1])
            except xmlrpc.client.Fault as err:
                print(err)
                sendmsg(str(err))
            else:
                bug = bzapi.getbug(i.split(None)[1])
                sendmsg("https://bugs.gentoo.org/" + str(i.split(None)[
                                                             1]) + " " + bug.summary + "; " + bug.component + "; " + bug.status + "; " + bug.resolution)


# static_bugs = get_bugs_old()


# for x in range(len(static_bugs)):
#    insert_sql(static_bugs[x].id, static_bugs[x].summary)
#    conn.commit()


def main():
    irc_connect()
    joinchan(channel)
    schedule.every(300).seconds.do(update_sql)
    while 1:
        ircmsg = ircsock.recv(2048).decode("UTF-8")
        ircmsg = ircmsg.strip('\n\r')
        print(ircmsg)
        schedule.run_pending()

        if ircmsg.find("PRIVMSG") != -1 and ircmsg.find(channel) != -1:
            name = ircmsg.split('!', 1)[0][1:]
            if name != 'ervbot':
                message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]
                willikins(message)
                if len(name) < 17:
                    if message.find('Hi ' + botnick) != -1:
                        sendmsg("Hello " + name + "!")
                    elif message[:2].find('.b') != -1:

                        if len(message) <= 2:
                            sendmsg("Correct usage: .b help")
                        elif len(message) > 2:
                            if message.split(' ', 2)[2:] != [] and message.split(' ', 3)[3:] == []:
                                print("more than 2 arguments")
                                command = message.split(" ", 2)[1]
                                subcommand = message.split(" ", 2)[2]
                                print(command + " " + subcommand)
                                if command == "pick":
                                    pick(name, subcommand)

                                elif command == "close":
                                    close(name, subcommand)

                                elif command == "query" and subcommand == "all":
                                    query(subcommand)

                                elif command == "resolve":
                                    resolve(name, subcommand)

                                elif command == "drop":
                                    drop(name, subcommand)

                                elif command == "block":
                                    block(name, subcommand)

                                elif command == "check":
                                    check(subcommand)

                                elif command == "owner":
                                    owner(subcommand)

                                elif command == "status":
                                    status(subcommand)

                                elif command == "fuzzy":
                                    fuzzy(subcommand)


                            else:
                                command = message.split(' ', 1)[1]
                                print("one command ", command)
                                if command == "help":
                                    help()

                                elif command == "query":
                                    query()

                                elif command == "kw":
                                    kw()

                                elif command == "update":
                                    update_sql()

                    elif name.lower() == adminname.lower() and message.rstrip() == exitcode:
                        sendmsg("Bye everyone I hope all bugs free)")
                        ircsock.send(bytes("QUIT \n", "UTF-8"))
                        conn.close()
                        return

            elif name == 'ervbot':
                name_irc = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1].split(' ', 3)[0].lstrip('[').rstrip(']')
                message = ircmsg.split('PRIVMSG', 1)[1].split(':', 1)[1]
                willikins(message)
                if len(name_irc) < 17:
                    if message.find('Hi ' + botnick) != -1:
                        sendmsg("Hello " + name_irc + "!")
                    elif message.split(" ")[1] == '.b':
                        if len(message.split(' ')) <= 2 or len(message.split(' ')) > 4:
                            sendmsg("Correct usage: .b help")
                        elif len(message.split(' ')) == 4:
                            print("more than 2 arguments")
                            command = message.split(" ", 3)[2]
                            subcommand = message.split(" ", 3)[3]
                            print(command + " " + subcommand)
                            if command == "pick":
                                pick(name_irc, subcommand)

                            elif command == "close":
                                close(name_irc, subcommand)

                            elif command == "query" and subcommand == "all":
                                query(subcommand)

                            elif command == "resolve":
                                resolve(name_irc, subcommand)

                            elif command == "drop":
                                drop(name_irc, subcommand)

                            elif command == "block":
                                block(name_irc, subcommand)

                            elif command == "check":
                                check(subcommand)

                            elif command == "owner":
                                owner(subcommand)

                            elif command == "status":
                                status(subcommand)

                            elif command == "fuzzy":
                                fuzzy(subcommand)

                        elif len(message.split(' ')) == 3:
                            command = message.split(" ", 2)[2]
                            print("one command ", command)
                            if command == "help":
                                help()

                            elif command == "query":
                                query()

                            elif command == "kw":
                                kw()
                            elif command == "update":
                                update_sql()


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
                            subcommand = message.split(" ", 2)[2]
                            print(command + " " + subcommand)
                            if command == "pick":
                                pick(name, subcommand, name)

                            elif command == "close":
                                close(name, subcommand, name)

                            elif command == "query" and subcommand == "all":
                                query(subcommand, name)

                            elif command == "resolve":
                                resolve(name, subcommand, name)

                            elif command == "drop":
                                drop(name, subcommand, name)

                            elif command == "block":
                                block(name, subcommand, name)

                            elif command == "check":
                                check(subcommand, name)
                            elif command == "owner":
                                owner(subcommand, name)

                            elif command == "status":
                                status(subcommand, name)

                            elif command == "fuzzy":
                                fuzzy(subcommand, name)

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


main()
conn.close()
