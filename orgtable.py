#!/usr/bin/env python

"""
Periodically fetch Emacs org-mode data from git and serve aggregated results as html on port 5000
"""


import sched
import sys
import threading
import time

import git
import pandas
from flask import Flask
from PyOrgMode import PyOrgMode

DATA = None
SCHED = sched.scheduler(time.time, time.sleep)
TIMER = 600

APP = Flask(__name__)
@APP.route('/a', methods=['GET'])
def hello_world():
    """return html data"""
    return DATA

def get_data():
    """Fetch data - called by scheduler periodically """

    # Pull repo
    repo = git.Repo('../org-mode/')
    origin = repo.remotes.origin
    origin.pull()


    # Extract org-mode date
    arch = {}
    base = PyOrgMode.OrgDataStructure()
    base.load_from_file("../org-mode/todo.org")
    for top_level in base.root.content:
        arch[top_level.heading] = {}
        for pri in ['A', 'B', 'C', 'total']:
            arch[top_level.heading][pri] = {}
            arch[top_level.heading][pri]['TODO'] = 0
            arch[top_level.heading][pri]['DONE'] = 0
        for item in top_level.content:
            if item.priority:
                arch[top_level.heading][item.priority][item.todo] += 1
                arch[top_level.heading]['total'][item.todo] += 1
    data_frame = pandas.DataFrame.from_dict({(i, j): arch[i][j]
                                             for i in arch.keys()
                                             for j in arch[i].keys()},
                                            orient='index')

    html = ('''<html> <head> <link rel="stylesheet" type="text/css"
               href="static/styles/dataFrame.css"> </head><body>'''
            + data_frame.to_html() + '</body> </html>')
    return html

def schedule_data(scheduler):
    """
    Scheduler function for fetching data hourly
    Runs in a background thread to not interfere with flask
    """

    global DATA
    try:
        DATA = get_data()
        sys.stdout.write("Successfully fetched data\n")
    except Exception:
        sys.stderr.write("Error opening URL\n")

    SCHED.enter(TIMER, 1, schedule_data, (scheduler,))


def main():
    """Start Scheduler & flask app """

    SCHED.enter(0, 1, schedule_data, (SCHED,))
    background_thread = threading.Thread(target=SCHED.run, args=())
    background_thread.daemon = True
    try:
        background_thread.start()
    except (KeyboardInterrupt, SystemExit):
        sys.exit(1)
    APP.run(debug=True, threaded=True)

if __name__ == '__main__':
    main()
