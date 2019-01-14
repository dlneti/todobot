import logging
import json
from collections import namedtuple
from datetime import datetime, timedelta, time
from functools import wraps

from telegram.ext import CommandHandler, Updater
from telegram import ParseMode

from dbmanager import DBManager as dbm
from extras import *

# load config
with open("config.json") as f:
    config = json.load(f)

#logging
log_config = config["log"]

LOGFILE = log_config.get("debug")
BOTLOG = log_config.get("filename")
LOGFORMAT = log_config.get("logformat")
LOGLEVEL = logging.DEBUG

logging.basicConfig(format=LOGFORMAT, level=LOGLEVEL, filename=LOGFILE)
logger = logging.getLogger(__name__)

#handlers
filehandler = logging.FileHandler(BOTLOG)
filehandler.setLevel(LOGLEVEL)

formatter = logging.Formatter(LOGFORMAT)
filehandler.setFormatter(formatter)

logger.addHandler(filehandler)


#todo db
DBFILE = config["db"]["file"]

# named tuple for unpacked update
Update = namedtuple('Update', 'username, text, date')


def help(func):

    @wraps(func)
    def wrapper(*a, **kw):
        update = a[1]
        text = update.message.text.split()
        if len(text) == 2 and text[1] in ['help', 'h']:
            helptext = helpdata.get(func.__name__)
            update.message.reply_text(helptext, parse_mode=ParseMode.MARKDOWN)
        else:
            return func(*a, **kw)
    return wrapper


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

    update.message.reply_text(STARTTEXT.format(available_commands), parse_mode=ParseMode.MARKDOWN)
    logger.debug(f"Replying user @{update.message.from_user.username}")


@help
def add_task(bot, update):
    upd = up_data(update)
    print('add_task is running')
    
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


@help
def get_task(bot, update):
    upd = up_data(update)

    message = upd.text.split()[1:]
    with dbm(DBFILE) as db:
        if not message:
            data = db.get()
            day = datetime.strftime(upd.date, "%Y-%m-%d") # default get today
        else:
            day, _ = parse_date(message, update)
            day = datetime.strftime(day, "%Y-%m-%d")
            data = db.get(day)
    
    message = ""
    if not data:
        message += "*TODO List* is empty!"
    elif len(data.keys()) == 1:
        message += f"*{day}*\n"
        try:
            data = data['tasks']
        except KeyError:
            data = data[day]['tasks']
        
        for num, task in data.items():
            message += f"`{num})` {task}\n"

    else:
        data = data.items()
        items = [(day, day_data) for day, day_data in data]
        items.sort(key=lambda x: x[0]) # sort by date ascending

        days = []
        for day, data in items:
            message_piece = f"*{day}*\n"
            for num, task in data['tasks'].items():
                message_piece += f"`{num})` {task}\n"
            days.append(message_piece)

        message += "\n".join(days)

    update.message.reply_text(message, parse_mode=ParseMode.MARKDOWN)

@help
def delete_task(bot, update):
    upd = up_data(update)
    day = datetime.strftime(upd.date, "%Y-%m-%d")
    reply = ""

    message = upd.text.split()[1:]

    if not message:
        reply += "Tell me what to delete."
        logger.debug("/delete command empty")
        update.message.reply_text(reply)
        return

    with dbm(DBFILE) as db:
        date_match = re.match(DATEREGEX, message[0])
        if len(message) == 1:
            if message[0] == 'all':
                db.delete(force=True)
                reply += "Deleting database"
                logger.debug("Deleting whole db")

            # Without specifying date default delete task from today
            if message[0].isdigit():
                try:
                    db.delete(day, message[0])
                    reply += f"Deleting task {message[0]} from *today*"
                except KeyError:
                    reply += f"Task {message[0]} in list {day} not found!"
                
            if date_match:
                try:
                    db.delete(message[0])
                    reply += f"Deleting day {message[0]}"
                    logger.debug(f"Deleting day {message[0]}")
                except KeyError:
                    reply += f"List {message[0]} not found!"

            if not reply:
                reply += f"\"{message[0]}\" not found!"

            
        else:
            if not date_match:
                reply += f"{message[0]} not found!"
            else:
                if message[1].isdigit():
                    try:
                        db.delete(message[0], message[1])
                        reply += f"Deleting task {message[1]} from list {message[0]}"
                        logger.debug(f"Deleting task {message[1]} from list {message[0]}")
                    except KeyError:
                        reply += f"Task {message[1]} not found in list {message[0]}"

        update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)

@help
def edit_task(bot, update):
    upd = up_data(update)
    day = datetime.strftime(upd.date, "%Y-%m-%d")
    reply = ""
    
    message = upd.text.split()[1:]
    if not message:
        reply += "Tell me what task to edit"

    elif len(message) < 2:
        reply += "I didn't get that :(\nType: /edit _help_"
    else:
        with dbm(DBFILE) as db:

            if message[0].isdigit():
                text = " ".join(message[1:])
                try:
                    db.edit(day, message[0], text)
                    reply += f"Editing task {message[0]} on {day}"
                    logger.debug(f"Deleting task {message[1]} from list {day}")
                except KeyError:
                    reply += f"Task {message[0]} not found!"
            else:
                if not message[1].isdigit():
                    reply += f"Second argument should be _task number_\nType: /edit _help_"
                else:
                    time = message[0]
                    date_match = re.match(DATEREGEX, time)
                    if date_match:
                        pass
                    elif time in ['tomorrow', 'tmr']:
                        time = upd.date + timedelta(days=1)
                        time = str(time.date())
                    else:
                        update.message.reply_text(f"\"{time}\" not found!")
                        return
                    

                    text = " ".join(message[2:])
                    try:
                        db.edit(time, message[1], text)
                        reply += f"Editing task {message[1]} on {time}"
                    except KeyError:
                        reply += f"Task {message[1]} not found!"

    update.message.reply_text(reply, parse_mode=ParseMode.MARKDOWN)


        

def daily_maintenance(bot, job):
    """Moves all tasks from today to day after that at the end of the day"""

    dtoday = datetime.today() - timedelta(days=1)
    today = datetime.strftime(dtoday, "%Y-%m-%d")
    tomorrow = datetime.strftime(dtoday + timedelta(days=1),"%Y-%m-%d") 

    with dbm(DBFILE) as db:
        today_data = db.get(today)['tasks']
        db.add(tomorrow, today_data)
        db.delete(today)
    
    message = f"Moved {today} data to {tomorrow} at {dtoday.time().strftime('%H:%M:%S')}" 
    logger.info(message)
    bot.send_message(chat_id=config['auth']['myid'], text=message)


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
    #jobq.run_daily(daily_maintenance, time=time(0,1))
    #jobq.run_repeating(daily_maintenance, first=0, interval=60)

    updater.start_polling()
