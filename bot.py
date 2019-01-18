import logging
import json
import sys
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
log_config = config.get("log")

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


PARSEMODE = ParseMode.MARKDOWN

# named tuple for unpacked update
Update = namedtuple('Update', 'username, user_id, text, date')


def help(func):
    @wraps(func)
    def wrapper(*a, **kw):
        update = a[1]
        text = update.message.text.split()
        if len(text) == 2 and text[1] in ['help', 'h']:
            helptext = helpdata.get(func.__name__)
            update.message.reply_text(helptext, parse_mode=PARSEMODE)
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
    user_id = message.from_user.id
    date = message.date
    text = message.text

    return Update._make([username, user_id, text, date])


def start(bot, update):
    available_commands = "\n".join(["`/add`", "`/tasks`", "`/del`", "`/edit`", "`/done`"])

    update.message.reply_text(STARTTEXT.format(available_commands), parse_mode=PARSEMODE)
    logger.debug(f"Replying user {update.message.from_user.name}")


@help
def add_task(bot, update):
    upd = up_data(update)
    
    # parse input
    message = upd.text
    message = message.split()[1:]

    parsed = parse_date(message, update)

    if not parsed:
        update.message.reply_text("Specified timeperiod not found!")
        return

    message = parsed[1]
    
    day = datetime.strftime(parsed[0], DATEFORMAT)
    
    # add to db
    with dbm(upd.user_id) as db:
        db.add(day, message)

    logger.info(f"adding task:{message} for user @{upd.username}")
    update.message.reply_text("Updating tasklist ...")


@help
def get_task(bot, update):
    upd = up_data(update)

    reply = ""
    message = upd.text.split()[1:]
    with dbm(upd.user_id) as db:
        if not message:
            data = db.get()
            day = datetime.strftime(upd.date, DATEFORMAT) # default get today
        else:
            day, _ = parse_date(message, update)
            day = datetime.strftime(day, DATEFORMAT)
            data = db.get(day)
            if not data:
                reply += f"*{day}* - "
    
    if not data:
        reply += "*Todo List* is empty!"
    elif len(data.keys()) == 1:
        reply += f"*{day}*\n"
        try:
            data = data['tasks']
        except KeyError:
            try:
                data = data[day]['tasks']
            except KeyError:
                day, data = list(data.items())[0]
                data = data['tasks']
                reply = f"*{day}*\n"
        
        for num, task in data.items():
            if task['done']:
                reply += f"`{num})` \u2705 "
            else:
                reply += f"`{num})` \u274c "
            reply += f"{task['text']}\n"

    else:
        data = data.items()
        items = [(day, day_data) for day, day_data in data]
        items.sort(key=lambda x: x[0]) # sort by date ascending

        days = []
        for day, data in items:
            reply_piece = f"*{day}*\n"
            for num, task in data['tasks'].items():
                if task['done']:
                    reply_piece += f"`{num})` \u2705 "
                else:
                    reply_piece += f"`{num})` \u274c "
                reply_piece += f"{task['text']}\n"
            days.append(reply_piece)

        reply += "\n".join(days)

    update.message.reply_text(reply, parse_mode=PARSEMODE)

@help
def delete_task(bot, update):
    upd = up_data(update)
    day = datetime.strftime(upd.date, DATEFORMAT)
    reply = ""

    message = upd.text.split()[1:]

    if not message:
        reply += "Tell me what to delete."
        logger.debug("/delete command empty")
        update.message.reply_text(reply)
        return

    with dbm(upd.user_id) as db:
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
                if message[0] in tomorrow:
                    message[0] = datetime.strftime(upd.date+timedelta(days=1), DATEFORMAT)
                try:
                    if message[0] == 'today':
                        db.delete(day)
                        reply += "Deleting *today*"
                    else:
                        db.delete(message[0])
                        reply += f"Deleting day *{message[0]}*"
                    logger.debug(f"Deleting day {message[0]}")
                except KeyError:
                    reply += f"{message[0]} not found!"

            if not reply:
                reply += f"\"{message[0]}\" not found!"

            
        else:
            if not date_match:
                reply += f"{message[0]} not found!"
            else:
                if message[0] in tomorrow:
                    message[0] = datetime.strftime(upd.date+timedelta(days=1), DATEFORMAT)
                if message[1].isdigit():
                    try:
                        db.delete(message[0], message[1])
                        reply += f"Deleting task {message[1]} from {message[0]}"
                        logger.debug(f"Deleting task {message[1]} from list {message[0]}")
                    except KeyError:
                        reply += f"Task {message[1]} not found in {message[0]}"

        update.message.reply_text(reply, parse_mode=PARSEMODE)

@help
def edit_task(bot, update):
    upd = up_data(update)
    day = datetime.strftime(upd.date, DATEFORMAT)
    reply = ""
    
    message = upd.text.split()[1:]
    if not message:
        reply += "Tell me what task to edit"

    elif len(message) < 2:
        reply += "I didn't get that :(\nType: /edit _help_"
    else:
        with dbm(upd.user_id) as db:

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
                        if time in tomorrow:
                            time = upd.date + timedelta(days=1)
                            time = str(time.date())
                    else:
                        update.message.reply_text(f"*\"{time}\"* not found!", parse_mode=PARSEMODE)
                        return
                    

                    text = " ".join(message[2:])
                    try:
                        db.edit(time, message[1], text)
                        reply += f"Editing task {message[1]} on {time}"
                    except KeyError:
                        reply += f"Task _{message[1]}_ on *{time}* not found!"

    update.message.reply_text(reply, parse_mode=PARSEMODE)



@help
def done_task(bot, update):
    upd = up_data(update)
    time = datetime.strftime(upd.date, DATEFORMAT)
    reply = ""

    message = upd.text.split()[1:]

    if not message:
        reply += "Which task?"
    else:
        with dbm(upd.user_id) as db:
            if message[0].isdigit():
                number = message[0]
                try:
                    done = db.done(time, number)
                    reply += f"Marking task {number} "
                    if done:
                        reply += "*DONE*"
                    else:
                        reply += "*UNDONE*"

                    logger.debug(f"Marking task {number} DONE|UNDONE on {time}")
                except KeyError:
                    reply += f"Task {number} not found!"
            else:
                time = message[0]
                number = message[1]
                
                if not number.isdigit():
                    update.message.reply_text(f"*{number}* is not a digit!")
                    return

                date_match = re.match(DATEREGEX, time)
                if date_match:
                    if time in tomorrow:
                        time = datetime.strftime(upd.date + timedelta(days=1), DATEFORMAT)
                        time = str(time)
                    try:
                        done = db.done(time, number)
                        reply += f"Marking task {number} on {time} "
                        if done:
                            reply += "*DONE*"
                        else:
                            reply += "*UNDONE*"

                        logger.debug(f"Marking task {number} DONE|UNDONE on {time}")
                    except KeyError:
                        reply += f"Task {number} on {time} not found!"
                else:
                    reply += "*\"{time}\"* not found!"


    update.message.reply_text(reply, parse_mode=PARSEMODE)
    pass

        

def daily_maintenance(bot, job):
    """Moves all tasks from today to day after that at the end of the day"""

    dtoday = datetime.today() 
    #dtoday = datetime.today() - timedelta(days=1)
    today = datetime.strftime(dtoday, DATEFORMAT)
    tomorrow = datetime.strftime(dtoday + timedelta(days=1), DATEFORMAT) 

    with dbm(upd.user_id) as db:
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
    
    response = []
    wordsused = 0

    if datestring[0] in accepted_keywords.keys():
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
        response.append(today + delta)
        wordsused += 3

    else:
        response.append(today)
    
    response.append(" ".join(datestring[wordsused:]))
    return response


if __name__ == "__main__":
    auth = config.get("auth")
    con = config.get("con")
    args = sys.argv[1:]

    updater = Updater(token=auth.get("token"))
    dispatcher = updater.dispatcher
    jobq = updater.job_queue

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('add', add_task))
    dispatcher.add_handler(CommandHandler('tasks', get_task))
    dispatcher.add_handler(CommandHandler('del', delete_task))
    dispatcher.add_handler(CommandHandler('edit', edit_task))
    dispatcher.add_handler(CommandHandler('done', done_task))


    #jobs
    #jobq.run_daily(daily_maintenance, time=time(0,1))
    #jobq.run_repeating(daily_maintenance, first=0, interval=600)

    if args:
        updater.start_webhook(listen="0.0.0.0",
                              port=con.get('port'),
                              url_path=con.get('path'),
                              key=con.get('key'),
                              cert=con.get('cert'),
                              webhook_url=con.get('url'))
    else:
        updater.start_polling()
