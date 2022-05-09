from errbot import BotPlugin, botcmd, re_botcmd
import sqlite3
import re
import datetime
import bugzilla
import xmlrpc

stat_unchangeable = ['closed', 'resolved', 'blocked', 'doing']
stat_changeable = ['open']


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
    conn = sqlite3.connect('plugins/test.db')
    c = conn.cursor()
    list_sql = []
    cursor = c.execute("SELECT number from BUG")
    for row in cursor:
        list_sql.append(row[0])
    conn.close()
    return list_sql


def check_status(number):
    conn = sqlite3.connect('plugins/test.db')
    c = conn.cursor()
    if int(number) <= 5000:
        sqlite_select_query = """SELECT owner,status  from BUG where id=?"""
        cursor = c.execute(sqlite_select_query, (int(number),))
        records = cursor.fetchall()
        if records:
            for row in records:
                owner = row[0]
                stat = row[1]
            return owner, stat

    else:
        sqlite_select_query = """SELECT owner,status  from BUG where number=?"""
        cursor = c.execute(sqlite_select_query, (int(number),))
        records = cursor.fetchall()
        if records:
            for row in records:
                owner = row[0]
                stat = row[1]
            return owner, stat

    conn.close()


def insert_sql(number, summary, component, site, owner='', time='', status='open'):
    conn = sqlite3.connect('plugins/test.db')
    c = conn.cursor()
    c.execute("INSERT INTO BUG (NUMBER,SUMMARY,COMPONENT,OWNER,TIME,STATUS,SITE) \
       VALUES (?,?,?,?,?,?,? )", (number, summary, component, owner, time, status, site))
    conn.commit()
    conn.close()


class Bugler(BotPlugin):
    @botcmd
    def b(self, msg, args):
        return "I'm alive!"

    @re_botcmd(pattern=r"bug\s\d{6}", prefixed=False, flags=re.IGNORECASE)
    def search_bugs(self, msg, match):
        bug_list = re.findall('bug\s\d{6}', msg.body)
        if bug_list:
            URL = "https://bugs.gentoo.org/xmlrpc.cgi"
            bzapi = bugzilla.Bugzilla(URL)
            for i in bug_list:
                try:
                    bzapi.getbug(i.split(None)[1])
                except xmlrpc.client.Fault as err:
                    yield err
                else:
                    bug = bzapi.getbug(i.split(None)[1])
                    yield (str(
                        bug.id) + " " + bug.summary + " " + bug.component + " " + bug.status + " " + bug.resolution + " " + "https://bugs.gentoo.org/" + str(
                        bug.id))

    # @botcmd()
    # def b_update(self, msg, args):
    #     bugs_in_sql = make_sql_list()
    #     new_bugs = get_bugs()
    #     new_list = make_new_list(new_bugs)
    #     ret = diff(bugs_in_sql, new_list)
    #     ret_closed = diff(new_list, bugs_in_sql)
    #     if ret:
    #         for x in ret:
    #             index = new_list.index(x)
    #             insert_sql(new_bugs[index].id, new_bugs[index].summary, new_bugs[index].component)
    #             yield (
    #                     "New Bug calling: " + str(new_bugs[index].id) + ' ' + new_bugs[index].summary + ' ' + new_bugs[
    #                 index].component)
    #
    #     if ret_closed:
    #         conn = sqlite3.connect('plugins/test.db')
    #         c = conn.cursor()
    #         for x in ret_closed:
    #             sqlite_select_query = """SELECT summary,component,owner,status from BUG where number=?"""
    #             cursor = c.execute(sqlite_select_query, (x,))
    #             records = cursor.fetchall()
    #             for row in records:
    #                 summary = row[0]
    #                 component = row[1]
    #                 owner = row[2]
    #                 status_in = row[3]
    #             if status_in != 'closed':
    #                 if owner == '':
    #                     sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
    #                     data = ('b.g.o', datetime.datetime.now(), "closed", x)
    #                     c.execute(sql_update_query, data)
    #                     yield (
    #                             "Bug closed in b.g.o. All peace! Owner: b.g.o. " + str(
    #                         x) + ' ' + summary + " Component: " + component)
    #                 else:
    #                     sql_update_query = """Update BUG set TIME=?,STATUS=? where number = ?"""
    #                     data = (datetime.datetime.now(), "closed", x)
    #                     c.execute(sql_update_query, data)
    #                     yield ("Ura! Bug closed in b.g.o. Thanks " + owner + "! Cheers! " + str(x) + ' ' +
    #                            summary + " Component: " + component)
    #         conn.commit()
    #         conn.close()

    def activate(self):
        super().activate()
        self.start_poller(300, self.update_sql)  # callbacks every minute

    def update_sql(self):
        bugs_in_sql = make_sql_list()
        new_bugs = get_bugs()
        new_list = make_new_list(new_bugs)
        ret = diff(bugs_in_sql, new_list)
        ret_closed = diff(new_list, bugs_in_sql)
        if ret:
            for x in ret:
                index = new_list.index(x)
                insert_sql(new_bugs[index].id, new_bugs[index].summary, new_bugs[index].component,
                           "https://bugs.gentoo.org/" + str(new_bugs[index].id))
                self.send(self.build_identifier("#PLCT-gentoo"),
                          "New Bug calling: " + str(new_bugs[index].id) + ' ' + new_bugs[index].summary + ' ' +
                          new_bugs[index].component + " https://bugs.gentoo.org/" + str(new_bugs[index].id))

        if ret_closed:
            conn = sqlite3.connect('plugins/test.db')
            c = conn.cursor()
            for x in ret_closed:
                sqlite_select_query = """SELECT summary,component,owner,status from BUG where number=?"""
                cursor = c.execute(sqlite_select_query, (x,))
                records = cursor.fetchall()
                for row in records:
                    summary = row[0]
                    component = row[1]
                    owner = row[2]
                    status_in = row[3]
                if status_in != 'closed':
                    if owner == '':
                        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                        data = ('b.g.o', datetime.datetime.now(), "closed", x)
                        c.execute(sql_update_query, data)
                        self.send(self.build_identifier("#PLCT-gentoo"),
                                  "Bug closed in b.g.o. All peace! Owner: b.g.o. " + str(
                                      x) + ' ' + summary + " Component: " + component + " https://bugs.gentoo.org/" + str(
                                      x))
                    else:
                        sql_update_query = """Update BUG set TIME=?,STATUS=? where number = ?"""
                        data = (datetime.datetime.now(), "closed", x)
                        c.execute(sql_update_query, data)
                        self.send(self.build_identifier("#PLCT-gentoo"),
                                  "Ura! Bug closed in b.g.o. Thanks " + owner + "! Cheers! " + str(x) + ' ' +
                                  summary + " Component: " + component + " https://bugs.gentoo.org/" + str(x))
            conn.commit()
            conn.close()

    @re_botcmd(pattern=r"b\scheck\s\d{1,}", prefixed=False, flags=re.IGNORECASE)
    def b_check(self, msg, match):
        cmd = re.findall("b\scheck\s\d{1,}", msg.body)
        if cmd:
            if cmd[0].split(None)[2].isdigit():
                conn = sqlite3.connect('plugins/test.db')
                c = conn.cursor()
                if int(cmd[0].split(None)[2]) <= 5000:
                    count = 0
                    cursor = c.execute("SELECT id,number,summary,component,owner,time,status  from BUG")
                    for row in cursor:
                        count = count + 1
                    if int(cmd[0].split(None)[2]) <= count:
                        sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where id=?"""
                        cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                        records = cursor.fetchall()
                        for row in records:
                            return ("ID: " +
                                    str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                                        2] + " Component: " + row[3] + " Owner: " +
                                    row[4] + " Time: " + row[5] + " Status: " +
                                    row[6] + " " + row[7])
                    else:
                        return "checked wrong ID (out of list)"

                else:
                    sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where number=?"""
                    cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                    records = cursor.fetchall()
                    for row in records:
                        return ("ID: " +
                                str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                                    2] + " Component: " + row[3] + " Owner: " +
                                row[4] + " Time: " + row[5] + " Status: " +
                                row[6] + " " + row[7])
                conn.close()

    @re_botcmd(pattern=r"b\sfuzzy\s.*", prefixed=False, flags=re.IGNORECASE)
    def b_fuzzy(self, msg, match):
        cmd = re.findall("b\sfuzzy\s.*", msg.body)
        if cmd:
            conn = sqlite3.connect('plugins/test.db')
            c = conn.cursor()
            sql_like_query = """SELECT * FROM BUG WHERE instr(summary,?)>0 GROUP BY number"""
            cursor = c.execute(sql_like_query, (cmd[0].split(None)[2],))
            i = 0
            for row in cursor:
                i = i + 1
                yield ("ID: " +
                       str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                           2] + " Component: " + row[3] + " Owner: " +
                       row[4] + " Time: " + row[5] + " Status: " +
                       row[6] + " " + row[7])
            c.close()
            yield ("Found: " + str(i))

    @re_botcmd(pattern=r"b\shelp", prefixed=False, flags=re.IGNORECASE)
    def b_help(self, msg, match):
        return "https://telegra.ph/Help-for-Bugler-04-26"

    @re_botcmd(pattern=r"b\spick\s\d{1,}", prefixed=False, flags=re.IGNORECASE)
    def b_pick(self, msg, match):
        cmd = re.findall("b\spick\s\d{1,}", msg.body)
        user_name = msg.nick
        if user_name == 'ervbot':
            user_name = msg.body.split()[0]
        if cmd:
            if cmd[0].split(None)[2].isdigit():
                conn = sqlite3.connect('plugins/test.db')
                c = conn.cursor()
                if int(cmd[0].split(None)[2]) <= 5000:
                    count = 0
                    cursor = c.execute("SELECT id  from BUG")
                    for row in cursor:
                        count = count + 1
                    if int(cmd[0].split(None)[2]) <= count:
                        owner = check_status(cmd[0].split(None)[2])[0]
                        stat = check_status(cmd[0].split(None)[2])[1]
                        if stat in stat_unchangeable and owner != user_name:
                            if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + ", no need to change, all peace!")
                            else:
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + " has focused on it, Let's look forward to his results!")
                        elif (owner == user_name and stat in stat_unchangeable) or \
                                stat in stat_changeable:
                            sqlite_select_query = """SELECT site  from BUG where id=?"""
                            cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                            records = cursor.fetchall()
                            for row in records:
                                site = row[0]
                            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                            data = (user_name, datetime.datetime.now(), "doing", int(cmd[0].split(None)[2]))
                            c.execute(sql_update_query, data)
                            conn.commit()
                            return (user_name + " picked" + ' ' + cmd[0].split(None)[
                                2] + "! Owner: " + owner + " --> " + user_name + " Status: " + stat + " --> doing " + site)
                    else:
                        return user_name + " picked wrong ID (out of list)"
                else:
                    owner = check_status(cmd[0].split(None)[2])[0]
                    stat = check_status(cmd[0].split(None)[2])[1]
                    if stat in stat_unchangeable and owner != user_name:
                        if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + ", no need to change, all peace!")
                        else:
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + " has focused on it, Let's look forward to his results!")
                    elif (owner == user_name and stat in stat_unchangeable) or stat in stat_changeable:
                        sqlite_select_query = """SELECT site  from BUG where number=?"""
                        cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                        records = cursor.fetchall()
                        for row in records:
                            site = row[0]
                        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                        data = (user_name, datetime.datetime.now(), "doing", int(cmd[0].split(None)[2]))
                        c.execute(sql_update_query, data)
                        conn.commit()
                        return (user_name + " picked" + ' ' + cmd[0].split(None)[
                            2] + "! Owner: " + owner + " --> " + user_name + " Status: " + stat + " --> doing " + site)
                conn.close()

    @re_botcmd(pattern=r"b\sclose\s\d{1,}", prefixed=False, flags=re.IGNORECASE)
    def b_close(self, msg, match):
        cmd = re.findall("b\sclose\s\d{1,}", msg.body)
        user_name = msg.nick
        if user_name == 'ervbot':
            user_name = msg.body.split()[0]
        if cmd:
            if cmd[0].split(None)[2].isdigit():
                conn = sqlite3.connect('plugins/test.db')
                c = conn.cursor()
                if int(cmd[0].split(None)[2]) <= 5000:
                    count = 0
                    cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
                    for row in cursor:
                        count = count + 1
                    if int(cmd[0].split(None)[2]) <= count:
                        owner = check_status(cmd[0].split(None)[2])[0]
                        stat = check_status(cmd[0].split(None)[2])[1]
                        if stat in stat_unchangeable and owner != user_name:
                            if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + ", no need to change, all peace!")
                            else:
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + " has focused on it, Let's look forward to his results!")
                        elif (owner == user_name and stat in stat_unchangeable) or \
                                stat in stat_changeable:
                            sqlite_select_query = """SELECT site  from BUG where id=?"""
                            cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                            records = cursor.fetchall()
                            for row in records:
                                site = row[0]
                            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                            data = (user_name, datetime.datetime.now(), "closed", int(cmd[0].split(None)[2]))
                            c.execute(sql_update_query, data)
                            conn.commit()
                            return ("Ura! " + user_name + " closed" + ' ' + cmd[0].split(None)[
                                2] + "! Status: " + stat + " --> closed. Cheers! " + site)
                    else:
                        return user_name + " picked wrong ID (out of list)"
                else:
                    owner = check_status(cmd[0].split(None)[2])[0]
                    stat = check_status(cmd[0].split(None)[2])[1]
                    if stat in stat_unchangeable and owner != user_name:
                        if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + ", no need to change, all peace!")
                        else:
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + " has focused on it, Let's look forward to his results!")
                    elif (owner == user_name and stat in stat_unchangeable) or \
                            stat in stat_changeable:
                        sqlite_select_query = """SELECT site  from BUG where number=?"""
                        cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                        records = cursor.fetchall()
                        for row in records:
                            site = row[0]
                        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                        data = (user_name, datetime.datetime.now(), "closed", int(cmd[0].split(None)[2]))
                        c.execute(sql_update_query, data)
                        conn.commit()
                        return "Ura! " + user_name + " closed" + ' ' + cmd[0].split(None)[
                            2] + "! Status: " + stat + " --> closed. Cheers! " + site

                conn.close()

    @re_botcmd(pattern=r"b\sblock\s\d{1,}", prefixed=False, flags=re.IGNORECASE)
    def b_block(self, msg, match):
        cmd = re.findall("b\sblock\s\d{1,}", msg.body)
        user_name = msg.nick
        if user_name == 'ervbot':
            user_name = msg.body.split()[0]
        if cmd:
            if cmd[0].split(None)[2].isdigit():
                conn = sqlite3.connect('plugins/test.db')
                c = conn.cursor()
                if int(cmd[0].split(None)[2]) <= 5000:
                    count = 0
                    cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
                    for row in cursor:
                        count = count + 1
                    if int(cmd[0].split(None)[2]) <= count:
                        owner = check_status(cmd[0].split(None)[2])[0]
                        stat = check_status(cmd[0].split(None)[2])[1]
                        if stat in stat_unchangeable and owner != user_name:
                            if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + ", no need to change, all peace!")
                            else:
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + " has focused on it, Let's look forward to his results!")
                        elif (owner == user_name and stat in stat_unchangeable) or \
                                stat in stat_changeable:
                            sqlite_select_query = """SELECT site  from BUG where id=?"""
                            cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                            records = cursor.fetchall()
                            for row in records:
                                site = row[0]
                            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                            data = (user_name, datetime.datetime.now(), "blocked", int(cmd[0].split(None)[2]))
                            c.execute(sql_update_query, data)
                            conn.commit()
                            return user_name + " blocked" + ' ' + cmd[0].split(None)[
                                2] + "! Status: " + stat + " --> blocked " + site
                    else:
                        return user_name + " blocked wrong ID (out of list)"
                else:
                    owner = check_status(cmd[0].split(None)[2])[0]
                    stat = check_status(cmd[0].split(None)[2])[1]
                    if stat in stat_unchangeable and owner != user_name:
                        if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + ", no need to change, all peace!")
                        else:
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + " has focused on it, Let's look forward to his results!")
                    elif (owner == user_name and stat in stat_unchangeable) or \
                            stat in stat_changeable:
                        sqlite_select_query = """SELECT site  from BUG where number=?"""
                        cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                        records = cursor.fetchall()
                        for row in records:
                            site = row[0]
                        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                        data = (user_name, datetime.datetime.now(), "blocked", int(cmd[0].split(None)[2]))
                        c.execute(sql_update_query, data)
                        conn.commit()
                        return user_name + " blocked" + ' ' + cmd[0].split(None)[
                            2] + "! Status: " + stat + " --> blocked " + site
                conn.close()

    @re_botcmd(pattern=r"b\sdrop\s\d{1,}", prefixed=False, flags=re.IGNORECASE)
    def b_drop(self, msg, match):
        cmd = re.findall("b\sdrop\s\d{1,}", msg.body)
        user_name = msg.nick
        if user_name == 'ervbot':
            user_name = msg.body.split()[0]
        if cmd:
            if cmd[0].split(None)[2].isdigit():
                conn = sqlite3.connect('plugins/test.db')
                c = conn.cursor()
                if int(cmd[0].split(None)[2]) <= 5000:
                    count = 0
                    cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
                    for row in cursor:
                        count = count + 1
                    if int(cmd[0].split(None)[2]) <= count:
                        owner = check_status(cmd[0].split(None)[2])[0]
                        stat = check_status(cmd[0].split(None)[2])[1]
                        if stat in stat_unchangeable and owner != user_name:
                            if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + ", no need to change, all peace!")
                            else:
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + " has focused on it, Let's look forward to his results!")
                        elif (owner == user_name and stat in stat_unchangeable) or \
                                stat in stat_changeable:
                            sqlite_select_query = """SELECT site  from BUG where id=?"""
                            cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                            records = cursor.fetchall()
                            for row in records:
                                site = row[0]
                            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                            data = ('', datetime.datetime.now(), "open", int(cmd[0].split(None)[2]))
                            c.execute(sql_update_query, data)
                            conn.commit()
                            return (user_name + " dropped" + ' ' + cmd[0].split(None)[
                                2] + "! Status: " + stat + " --> open. People can pick this bug again! " + site)
                    else:
                        return user_name + " dropped wrong ID (out of list)"
                else:
                    owner = check_status(cmd[0].split(None)[2])[0]
                    stat = check_status(cmd[0].split(None)[2])[1]
                    if stat in stat_unchangeable and owner != user_name:
                        if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + ", no need to change, all peace!")
                        else:
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + " has focused on it, Let's look forward to his results!")
                    elif (owner == user_name and stat in stat_unchangeable) or \
                            stat in stat_changeable:
                        sqlite_select_query = """SELECT site  from BUG where number=?"""
                        cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                        records = cursor.fetchall()
                        for row in records:
                            site = row[0]
                        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                        data = ('', datetime.datetime.now(), "open", int(cmd[0].split(None)[2]))
                        c.execute(sql_update_query, data)
                        conn.commit()
                        return (user_name + " dropped" + ' ' + cmd[0].split(None)[
                            2] + "! Status: " + stat + " --> open. People can pick this bug again! " + site)

                conn.close()

    @re_botcmd(pattern=r"b\sresolve\s\d{1,}", prefixed=False, flags=re.IGNORECASE)
    def b_resolve(self, msg, match):
        cmd = re.findall("b\sresolve\s\d{1,}", msg.body)
        user_name = msg.nick
        if user_name == 'ervbot':
            user_name = msg.body.split()[0]
        if cmd:
            if cmd[0].split(None)[2].isdigit():
                conn = sqlite3.connect('plugins/test.db')
                c = conn.cursor()
                if int(cmd[0].split(None)[2]) <= 5000:
                    count = 0
                    cursor = c.execute("SELECT id,number,summary,owner,time,status  from BUG")
                    for row in cursor:
                        count = count + 1
                    if int(cmd[0].split(None)[2]) <= count:
                        owner = check_status(cmd[0].split(None)[2])[0]
                        stat = check_status(cmd[0].split(None)[2])[1]
                        if stat in stat_unchangeable and owner != user_name:
                            if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + ", no need to change, all peace!")
                            else:
                                return (
                                        "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                        owner + " has focused on it, Let's look forward to his results!")
                        elif (owner == user_name and stat in stat_unchangeable) or \
                                stat in stat_changeable:
                            sqlite_select_query = """SELECT site  from BUG where id=?"""
                            cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                            records = cursor.fetchall()
                            for row in records:
                                site = row[0]
                            sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where id = ?"""
                            data = (user_name, datetime.datetime.now(), "resolved", int(cmd[0].split(None)[2]))
                            c.execute(sql_update_query, data)
                            conn.commit()
                            return ("Ura! " + user_name + " resolved" + ' ' + cmd[0].split(None)[
                                2] + "! Status: " + stat + " --> resolved. Cheers! " + site)
                    else:
                        return user_name + " picked wrong ID (out of list)"
                else:
                    owner = check_status(cmd[0].split(None)[2])[0]
                    stat = check_status(cmd[0].split(None)[2])[1]
                    if stat in stat_unchangeable and owner != user_name:
                        if stat == 'closed' or stat == 'resolved' or stat == 'blocked':
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + ", no need to change, all peace!")
                        else:
                            return (
                                    "Bug: " + cmd[0].split(None)[2] + " Status: " + stat + "! Owner: " +
                                    owner + " has focused on it, Let's look forward to his results!")
                    elif (owner == user_name and stat in stat_unchangeable) or \
                            stat in stat_changeable:
                        sqlite_select_query = """SELECT site  from BUG where number=?"""
                        cursor = c.execute(sqlite_select_query, (int(cmd[0].split(None)[2]),))
                        records = cursor.fetchall()
                        for row in records:
                            site = row[0]
                        sql_update_query = """Update BUG set OWNER=?,TIME=?,STATUS=? where number = ?"""
                        data = (user_name, datetime.datetime.now(), "resolved", int(cmd[0].split(None)[2]))
                        c.execute(sql_update_query, data)
                        conn.commit()
                        return ("Ura! " + user_name + " resolved" + ' ' + cmd[0].split(None)[
                            2] + "! Status: " + stat + " --> resolved. Cheers! " + site)

                conn.close()

    @re_botcmd(pattern=r"b\skw", prefixed=False, flags=re.IGNORECASE)
    def b_kw(self, msg, args):
        conn = sqlite3.connect('plugins/test.db')
        c = conn.cursor()
        sql_like_query = """SELECT * FROM BUG WHERE instr(component,'Keywording')>0 and instr(status,'blocked')<=0 AND instr(status,'resolved')<=0 AND
                    instr(status,'closed')<=0 GROUP BY number"""
        cursor = c.execute(sql_like_query)
        i = 0
        for row in cursor:
            i = i + 1
            yield ("ID: " +
                   str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                       2] + " Component: " + row[3] + " Owner: " +
                   row[4] + " Time: " + row[5] + " Status: " +
                   row[6] + " " + row[7])
        conn.close()
        yield ("Active component: Keywords: " + str(i))

    # @re_botcmd(pattern=r"b\squery\sall", prefixed=False, flags=re.IGNORECASE)
    # def b_query(self, msg, match):
    #     cmd = re.findall("b\squery\sall", msg.body)
    #     if cmd:
    #         conn = sqlite3.connect('plugins/test.db')
    #         c = conn.cursor()
    #         i = 0
    #         cursor = c.execute("SELECT id,number,summary,component,owner,time,status,site  from BUG")
    #         for row in cursor:
    #             i = i + 1
    #             yield ("ID: " +
    #                    str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
    #                        2] + " Component: " + row[3] + " Owner: " +
    #                    row[4] + " Time: " + row[5] + " Status: " +
    #                    row[6] + " " + row[7])
    #         conn.close()
    #         yield "All bugs: " + str(i)

    @re_botcmd(pattern=r"b\squery", prefixed=False, flags=re.IGNORECASE)
    def b_query(self, msg, match):
        cmd = re.findall("b\squery", msg.body)
        if cmd:
            conn = sqlite3.connect('plugins/test.db')
            c = conn.cursor()
            i = 0
            sql_like_query = """SELECT * FROM BUG WHERE instr(status,'blocked')<=0 AND instr(status,'resolved')<=0 AND instr(status,'closed')<=0 GROUP BY id """
            cursor = c.execute(sql_like_query)
            for row in cursor:
                i = i + 1
                yield ("ID: " +
                       str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                           2] + " Component: " + row[3] + " Owner: " +
                       row[4] + " Time: " + row[5] + " Status: " +
                       row[6] + " " + row[7])
            conn.close()
            yield "All active bugs: " + str(i)

    @re_botcmd(pattern=r"b\sowner\s.*", prefixed=False, flags=re.IGNORECASE)
    def b_owner(self, msg, match):
        cmd = re.findall("b\sowner\s.*", msg.body)
        if cmd:
            conn = sqlite3.connect('plugins/test.db')
            c = conn.cursor()
            sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where owner=?"""
            cursor = c.execute(sqlite_select_query, (cmd[0].split(None)[2],))
            records = cursor.fetchall()
            i = 0
            for row in records:
                i = i + 1
                yield ("Owner: " +
                       row[4] + " ID: " +
                       str(row[0]) + " Bug number: " + str(row[1]) + " Title: " + row[
                           2] + " Component: " + row[3] + " Time: " + row[5] + " Status: " +
                       row[6] + " " + row[7])
            conn.close()
            yield cmd[0].split(None)[2] + " has " + str(i) + " bugs."

    @re_botcmd(pattern=r"b\sstatus\s.*", prefixed=False, flags=re.IGNORECASE)
    def b_status(self, msg, match):
        cmd = re.findall("b\sstatus\s.*", msg.body)
        if cmd:
            if cmd[0].split(None)[2] in stat_unchangeable or cmd[0].split(None)[2] in stat_changeable:
                conn = sqlite3.connect('plugins/test.db')
                c = conn.cursor()
                sqlite_select_query = """SELECT id,number,summary,component,owner,time,status,site  from BUG where status=?"""
                cursor = c.execute(sqlite_select_query, (cmd[0].split(None)[2],))
                records = cursor.fetchall()
                i = 0
                for row in records:
                    i = i + 1
                    yield ("ID: " +
                           str(row[0]) + " bug " + str(row[1]) + " Title: " + row[
                               2] + " Component: " + row[3] + " Owner: " +
                           row[4] + " Time: " + row[5] + " Status: " +
                           row[6] + " " + row[7])
                conn.close()
                yield str(i) + " bugs " + cmd[0].split(None)[2]
