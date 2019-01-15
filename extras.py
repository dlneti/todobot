import json
import re
from datetime import timedelta

REGEX = "(^[0-9]+)\s?(s(ec)?(ond)?[s]?$|m(in)?[s]?(ute)?[s]?$|h[r]?[s]?(our)?[s]?$|d(ay)?[s]?$|w(eek)?[s]?$|month[s]?$|y[r]?(ear)?[s]?$)" 

DATEREGEX = "\d{4}-\d{2}-\d{2}|tmr|tomorrow"
DATEFORMAT = "%Y-%m-%d"


def match_re(inp):
    match = re.match(REGEX, inp)
    if not match:
        return None
    
    grps = match.groups()
    return grps


timeperiods = {
        "s": lambda x: timedelta(seconds=x),
        "m": lambda x: timedelta(seconds=x*60),
        "h": lambda x: timedelta(seconds=x*60*60),
        "d": lambda x: timedelta(days=x),
        "w": lambda x: timedelta(days=x*7),
        "mo": lambda x: timedelta(days=x*7*4),
        "y": lambda x: timedelta(days=x*7*4*12)
        }

tomorrow = ['tmr', 'tomorrow']

ADD_TASK = """
`Usage`
/add _example task_
This will add task to *TODAY* list

/add *time* _example task_
This will add task to list specified by *time*

*time* can be any natural input such as
_tomorrow, in 2 days, in 4 weeks, in 14 years_
or a specific date in YYYY-MM-DD format (preferred)

`Examples`
/add *in 2 days* _buy milk_
/add *tmr* _walk the dog_
"""
GET_TASK = """
`Usage`
/tasks without specified time shows all tasks

/tasks *time*
This will show tasks on day specified by *time*

*time* can be any natural input such as
_tomorrow, in 2 days, in 4 weeks, in 14 years_
or a specific date in YYYY-MM-DD format (preferred)

`Examples`
/tasks *today*
/tasks *tmr*
/tasks *in 5 days*
"""
DELETE_TASK = """
`Usage`
/del *time* _task number_
This will delete specified task from todo list

*time* can be any natural input such as
_tomorrow, in 2 days, in 4 weeks, in 14 years_
or a specific date in YYYY-MM-DD format (preferred)

_task number_ is number of a task (you can check the number with /tasks command)

/del without _task number_ will delete entire specified day

/del *all* to delete entire todo list

`Examples`
/del 1
/del tmr
/del 2019-10-10 3
"""
EDIT_TASK = """
`Usage`
/edit *time* _tasknum_ *new_task*
This will change _task_ on _day_ to *new_task*

*time* can be either _today_, _tomorrow_, _tmr_
or a specific date in format YYYY-MM-DD

_taksnum_ is the number of a task

Without *time* tasks on TODAY list will be edited

`Examples`
/edit _2_ do shopping
/edit *tomorrow* _3_ change underwear
/edit *2019-11-17* _1_ wish happy birthday
"""
DONE_TASK = """
`Usage`
/done *time* _tasknum_
This will mark task _tasknum_ on day *time* DONE
Using /done again on the same task will mark it UNDONE

*time* can be either _today_, _tomorrow_, _tmr_
or a specific date in format YYYY-MM-DD

_taksnum_ is the number of a task

/done without time will mark tasks on TODAY list

`Examples`
/done 2
/done tmr 1
/done 2019-02-02 2
"""

helpdata = {
        "add_task": ADD_TASK.strip(),
        "delete_task": DELETE_TASK.strip(),
        "get_task": GET_TASK.strip(),
        "edit_task": EDIT_TASK.strip(),
        "done_task": DONE_TASK.strip()
        }



STARTTEXT = """
`Welcome to TODOBOT`

Start by adding tasks to your todo list

Simply type: */add* _This is example task_
This command will add the task to your _today_ todo list

To add a task to another day, type:
e.g. /add *tomorrow* _example task no. 2_
You can replace *tomorrow* by other time such as:
_in 2 days, in 6 weeks_, etc...

See your tasks by using the /tasks command.
Type /tasks for to see all tasks or /tasks *time* (e.g. today)

To mark a task done, type:
e.g. /done *number* (e.g. _2_)
Get the number of task by using /tasks command

At the end of each day your unfinised tasks will get moved to next day's list.

_Available commands:_
{0}

Type *help* after each command for more detailed info
"""
