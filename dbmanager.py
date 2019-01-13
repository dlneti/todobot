import json
import logging

DBFILE = 'tododb.json'

logger = logging.getLogger(__name__)
filehandler = logging.FileHandler('db.log')
filehandler.setLevel(logging.DEBUG)

formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
filehandler.setFormatter(formatter)

logger.addHandler(filehandler)

class DBManager:
    """Simple json db manager

    Expected db format:

    {
      "YYYY-MM-DD": {
        "tasks": {
          "1": "task1",
          "2": "task2",
          "3": "task3"
        }
      },
        
       "abc": {}
       ...

    }

    """

    defaultday = lambda self, day: {day: {"tasks": {}}}

    def __init__(self, name):
        self.name = name
        self.write = False
        self.db = self._load_db(self.name)

    def __enter__(self):
        return self 

    def __exit__(self, *a):
        if self.write:
            with open(self.name, 'w') as f:
                json.dump(self.db, f, indent=2)

    def _load_db(self, db):
        """Load db from file, create it if doesn't exist"""
        try:
            with open(db) as f:
                return json.load(f)         
        except FileNotFoundError:
            with open(db, 'w') as f:
                json.dump({}, f)
            return {}


    def add(self, day, task):
        self.write = True
        new_dict = {}

        writeday = self.db.get(day)

        # if day doesnt exist we add default day so we can update it later
        if not writeday: 
            numid = 1
            self.db.update(self.defaultday(day))
        else: # else get id of last task on the day
            last = max(list(writeday['tasks'].keys()))
            numid = int(last) + 1

        if isinstance(task, str):
            new_dict.update({numid: task})

        if isinstance(task, dict):
            tasks = task.values()
            print(tasks) # debug

            for i in tasks:
                new_dict.update({numid: i})
                numid += 1

        self.db[day]['tasks'].update(new_dict)
        logger.debug(f"Task <{new_dict}> number <{numid}> added to day <{day}>")


    def get(self, day=0, task=0):
        if not day and not task:
            return self.db

        if not day:
            logger.debug("Specify date")
            return

        dayindb = self._presence(day)
        if not dayindb:
            logger.debug(f"Day {day} not found")
            return

        if not task:
            return self.db.get(day)
        
        task = str(task)
        taskintasks = self._presence(day, task)
        if taskintasks:
            return self.db[day]['tasks'][task]
        
        logger.debug(f"Task {task} not found")
        return 
    

    def delete(self, day=0, task=0, force=False):
        if not day and not task:
            if force: # delete whole db
                self.db = {}
                self.write = True
                return
            logger.debug("Specify task or date")
            return

        if not day:
            logger.debug(f"Specify date for task {task}")
            return

        dayindays = self._presence(day)
        if not dayindays:
            logger.debug(f"Day {day} not found")
            return

        if not task:
            del self.db[day]
            logger.debug(f"Deleting day {day}")
            self.write = True
            return

        task = str(task)
        taskintasks = self._presence(day, task)
        if not taskintasks:
            logger.debug(f"Task {task} not found")
            return

        del self.db[day]['tasks'][task] 
        logger.debug(f"Deleting task {task} from day {day}")
        self.write = True
        
        # rearrange
        tasks = self.db[day]['tasks']
        count = 1
        newtasks = {}
        for i in tasks.values():
            newtasks.update({count: i})
            count += 1
        self.db[day] = {'tasks': newtasks}

        return


    def edit(self, day, task, text):
        task = str(task)
        taskintasks = self._presence(day, task)

        if not taskintasks:
            logger.debug(f"Task {task} not found")
            return

        self.db[day]['tasks'][task] = text 
        logger.debug(f"Modifying task {task} -> {text}")
        self.write = True
        return

    def _presence(self, day=False, task=False) -> bool:
        if not task:
            return day in self.db.keys()
        return task in self.db[day]['tasks'].keys()
        





