import logging
import json
from collections import namedtuple
from datetime import datetime, timedelta, time

from telegram.ext import CommandHandler, Updater
from telegram import ParseMode

from dbmanager import DBManager as dbm
from utils import match_re, timeperiods

# load config
with open("config.json") as f:
    config = json.load(f)

#logging
log_config = config["log"]

LOGFILE = log_config.get("filename")
LOGLEVEL = logging.DEBUG

logging.basicConfig(format=log_config.get("logformat"), level=LOGLEVEL, filename=LOGFILE)
logger = logging.getLogger(__name__)

#handlers
#filehandler = logging.FileHandler(LOGFILE)
#filehandler.setLevel(logging.INFO)

#logger.addHandler(filehandler)


#todo db
DBFILE = config["db"]["file"]

# named tuple for unpacked update
Update = namedtuple('Update', 'username, text, date')


def up_data(update):
    """Convenience function to unpack data from `telegram.Update`

    Returns
    `Update`
    """
    message = update.message

    username = message.from_user.username
    date = message.date
    text = message.text

    return Update._make([username, text, date])


def start(bot, update):
    available_commands = "\n".join(["`/add`", "`/tasks`", "`/del`", "`/edit`"])

    message = "`Welcome to TODOBOT`\n\n"
    message += "Start by adding tasks to your todo list\n\n"
    message += "Simply type: */add* _This is example task_\n"
    message += "This command will add the task to your _today_ todo list\n\n"
    message += "To add a task to another day, type:\n"
    message += "e.g. /add *tomorrow* _example task no. 2_\n"
    message += "You can replace *tomorrow* by other time such as:\n"
    message += "_in 2 days, in 6 weeks_, etc...\n\n"
    message += "See your tasks by using the /tasks command.\n"
    message += "Type /tasks for to see all tasks or /tasks *time* (e.g. today)\n\n"
    message += "To mark a task done, type:\n"
    message += "e.g. /done *number* (e.g. _2_)\n"
    message += "Get the number of task by using /tasks command \n\n"
    message += "At the end of each day your unfinised tasks will get moved to next day's list.\n\n"
    message += f"_Available commands:_\n{available_commands}"

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)
    logger.debug(f"Replying user @{update.message.from_user.username}")


def add_task(bot, update):
    upd = up_data(update)
    
    # parse input
    message = upd.text
    message = message.split()[1:]

    parsed = parse_date(message, update)

    if not parsed:
        update.message.reply_text("Specified timeperiod not found!")
        return

    day = datetime.strftime(parsed[0], "%Y-%m-%d %H:%M:%S") #debug
    message = parsed[1]
    
    update.message.reply_text(f"{day}\n{message}") #debug
    day = datetime.strftime(parsed[0], "%Y-%m-%d")
    
    # add to db
    with dbm(DBFILE) as db:
        db.add(day, message)

    logger.info(f"adding task:{message} for user @{upd.username}")
    update.message.reply_text("Updating tasklist ...")


def parse_date(datestring: list, update):
    """Calculates datetime.timedelta from natural input.
       If no input is found, defaults to today. 

       Returns:
       List[datetime.datetime, str(message)]
    """

    today = datetime.today()
    accepted_keywords = {'today': today,
                         'tomorrow': today + timedelta(days=1), 
                         'tmr': today + timedelta(days=1)}
    
    message = ""
    response = []
    wordsused = 0

    if datestring[0] in accepted_keywords.keys():
        message += f"Detected time `{datestring[0]}`" #debug
        update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN) #debug
        response.append(accepted_keywords[datestring[0]])
        wordsused += 1

    elif datestring[0] == "in":
        # Expected pattern is: int(n) str(timeperiod)
        # e.g. 2 days | 5 w | 3 months | 10 mins

        #make sure first arg is a number
        if not datestring[1].isdigit():
            update.message.reply_text("argument is not a digit")
            return None

        test = " ".join(datestring[1:3])
        match = match_re(test)

        # regext test
        if not match:
            return None
        
        num, period = datestring[1:3]
        period = period.lower()
        num = int(num)

        if period[:2] == 'mo': # handle minute & month collision
            delta = timeperiods[period[:2]](num)
        else:
            delta = timeperiods[period[0]](num)
        print(today + delta) #debug
        response.append(today + delta)
        wordsused += 3

    else:
        response.append(today)
    
    response.append(" ".join(datestring[wordsused:]))
    return response


def get_task(bot, update):
    #TODO: all functionalities
    upd = up_data(update)

    message = upd.text.split()[1:]
    with dbm(DBFILE) as db:
        if not message:
            data = db.get()
        else:
            day, _ = parse_date(message, update)
            day = datetime.strftime(day, "%Y-%m-%d")
            data = db.get(day)
    
    message = ""
    if len(data.keys()) == 1:
        message += f"*{day}*\n"
        for num, task in data['tasks'].items():
            message += f"{num}. - {task}\n"

    else:
        data = data.items()
        items = [(day, day_data) for day, day_data in data]
        items.sort(key=lambda x: x[0]) # sort by date ascending

        days = []
        for day, data in items:
            message_piece = f"*{day}*\n"
            for num, task in data['tasks'].items():
                message_piece += f"{num}) - {task}\n"
            days.append(message_piece)

        message += "\n".join(days)

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

#    if not message:
#        message += "TODO List is empty!"
#    update.message.reply_text(message)
#    logger.info(f"Getting all tasks for @{upd.username}")


def delete_task(bot, update):
    upd = up_data(update)
    day = datetime.strftime(upd.date, "%Y-%m-%d")

    task = upd.text.split()[1]
    
    with dbm(DBFILE) as db:
        db.delete(day, task)

    update.message.reply_text(f"Deleting all tasks for day {day}")
    logger.info(f"Deleting task {task} from day {day}")

def edit_task(bot, update):
    upd = up_data(update)
    day = datetime.strftime(upd.date, "%Y-%m-%d")
    
    args = upd.text.split()[1:]
    task = args[0]
    text = " ".join(args[1:])

    with dbm(DBFILE) as db:
        db.edit(day, task, text)

    update.message.reply_text(f"Updating task {task} on {day}")
    logger.info(f"Updating task {task} in day {day}")




def daily_maintenance(bot, job):
    """Moves all tasks from today to day after that at the end of the day"""

    dtoday = datetime.today()
    today = datetime.strftime(dtoday, "%Y-%m-%d")
    tomorrow = datetime.strftime(dtoday + timedelta(days=1),"%Y-%m-%d") 

    with dbm(DBFILE) as db:
        today_data = db.get(today)['tasks']
        print(today_data) #debug
        db.add(tomorrow, today_data)
        db.delete(today)
        print(db.get()) #debug
    
    message = f"Moved {today} data to {tomorrow} at {dtoday.time().strftime('%H:%M:%S')}" 
    logger.info(message)
    bot.send_message(chat_id=config['auth']['myid'], text=message)




if __name__ == "__main__":
    auth = config.get("auth")

    updater = Updater(token=auth.get("token"))
    dispatcher = updater.dispatcher
    jobq = updater.job_queue

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('add', add_task))
    dispatcher.add_handler(CommandHandler('tasks', get_task))
    dispatcher.add_handler(CommandHandler('del', delete_task))
    dispatcher.add_handler(CommandHandler('edit', edit_task))


    #jobs
    jobq.run_daily(daily_maintenance, time=time(9,29))
    #jobq.run_repeating(daily_maintenance, first=0, interval=60)

    updater.start_polling()
