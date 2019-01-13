import json
import re
from datetime import timedelta

REGEX = "(^[0-9]+)\s?(s(ec)?(ond)?[s]?$|m(in)?[s]?(ute)?[s]?$|h[r]?[s]?(our)?[s]?$|d(ay)?[s]?$|w(eek)?[s]?$|month[s]?$|y[r]?(ear)?[s]?$)" 


def match_re(inp):
    match = re.match(REGEX, inp)

    if not match:
        #print(f"{inp} not matched!")
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
