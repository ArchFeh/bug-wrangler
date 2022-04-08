# bug-wrangler
bugler is a irc bot for gentoo riscv team to conveniently handle bugs which posted in bugzilla. 
# changelog: 

when bugs are closed by b.g.o, notify.fix fatal wrong in update bugs

add private message support, you can do what you want without spam your channel
# To use this bot, command: .b cmd.
commands: block, check, drop, fuzzy, help, kw, pick, query, rcheck, resolve, status

block: block one bug, and it won't shown in query default

check:check one bug's information. Example: .b check Id/Bug number

drop:drop one bug

fuzzy: search bug by keywords

help:show this help

kw:show keyword bugs.

pick:show your willing to solve this bug. Example: .b pick Id/Bug number.

query:query all the active bugs which are related with riscv. To show all bugs, use query all

rcheck: search bug by owner. Example: .b rcheck irc-name.

resolve: change the status of bug to resolved. example: .b resolve Id/Bug number
