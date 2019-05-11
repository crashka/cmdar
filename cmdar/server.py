#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""DAR Server (based on Flask)
"""

import sys
import logging
import threading

from flask import Flask, request, jsonify
import click

from core import BASE_DIR, cfg, log, dbg_hand
from dar import Dar, TodoState

#############
# Flask App #
#############

app = Flask(__name__)

################
# Flask Routes #
################

"""
-----------------
RESTful interface
-----------------
GET    /dar                             - show DAR state/info [**]
PATCH  /dar                             - change DAR state

GET    /stations                        - list stations (state/info)
GET    /stations/<id>                   - get station state/info
PATCH  /stations/<id>                   - schedule manual recording

GET    /programs[?<params>]             - list programs (state/info)
POST   /programs                        - create new program
GET    /programs/<id>                   - get program state/info
PUT    /programs/<id>                   - update program info
PATCH  /programs/<id>                   - change program state
DELETE /programs/<id>                   - delete program

[Note: Todo Items represent active programs + manual recordings]
GET    /todos[?<params>]                - list todo items (state/info) [**]
GET    /todos/<id>                      - get todo item state/info
PATCH  /todos/<id>                      - change todo item state
DELETE /todos/<id>                      - cancel todo item

----------------------------
Browser (pure-GET) shortcuts
----------------------------
GET    /dar/state                       - get DAR state [**]
GET    /dar/start                       - start DAR (new jobs enabled) [**]
GET    /dar/pause                       - pause DAR (no new jobs) [**]
GET    /dar/resume                      - resume DAR (new jobs re-enabled) [**]
GET    /dar/shutdown[?<params>]         - shutdown DAR (kill running jobs by default) [**]

GET    /stations/<name>/record?<params> - schedule manual recording

GET    /programs/create?<params>        - create new program
GET    /programs/reload[?<params>]      - reload programs from config file [**]
GET    /programs/<id>/update?<params>   - update program info
GET    /programs/<id>/activate          - activate program
GET    /programs/<id>/inactivate        - inactivate program
GET    /programs/<id>/delete            - delete program

GET    /todos/<id>/suspend              - suspend todo item
GET    /todos/<id>/requeue              - requeue todo item
GET    /todos/<id>/cancel               - cancel todo item
GET    /todos/<id>/delete               - delete todo item (same as ``cancel``???)

[**] implemented below
"""

#-----#
# dar #
#-----#

@app.route('/dar')
def dar_info():
    """Show DAR state/info
    """
    return jsonify(dar.get_info())

@app.route('/dar/state')
def dar_state():
    """Get DAR state
    """
    return jsonify(state=dar.state)

@app.route('/dar/start')
def dar_start():
    """Start DAR (new jobs enabled)
    """
    return jsonify(result=dar.start_scheduler())

@app.route('/dar/pause')
def dar_pause():
    """Pause DAR (no new jobs)
    """
    return jsonify(result=dar.pause_scheduler())

@app.route('/dar/resume')
def dar_resume():
    """Resume DAR (new jobs re-enabled)
    """
    return jsonify(result=dar.resume_scheduler())

@app.route('/dar/shutdown')
def dar_shutdown():
    """Shutdown DAR (kill running jobs by default)

    Supported params (defaults):
      - wait_for_jobs (True)
    """
    try:
        result = dar.stop_scheduler(**request.args)
    except TypeError as e:
        log.info("Caught TypeError: %s" % (str(e)))
        return "Error: " + str(e), 400
    return jsonify(result=result)

#----------#
# programs #
#----------#

@app.route('/programs/reload')
def programs_reload():
    """Reload programs from config file

    Supported params (defaults):
      - do_create (True)
      - do_update (True)
      - do_pause (False)
    """
    try:
        result = dar.reload_programs(**request.args)
    except TypeError as e:
        log.info("Caught TypeError: %s" % (str(e)))
        return "Error: " + str(e), 400
    return jsonify({i: list(j) for i, j in result.items()})

#--------#
# /todos #
#--------#

@app.route('/todos')
def todos_list():
    """List todo items (state/info)
    """
    todos = []
    for job in dar.get_jobs():
        status = TodoState.QUEUED if job.next_run_time else TodoState.SUSPENDED
        todos.append({'id': job.id, 'status': status, 'info': str(job)})
    return jsonify(todos)

#############
# DAR setup #
#############

dar = None

#######################
# Server Command Line #
#######################

@click.command()
@click.option('--streamer', default='vlc', help="Name of streamer in config file (defaults to 'vlc')")
@click.option('--delay',    default=2, help="Delay (in secs) before starting scheduler (defaults to 2)")
@click.option('--debug',    default=0, help="Debug level (0-3)")
@click.option('--profile',  default=None, type=str, help="Profile in config.yml")
@click.option('--public',   is_flag=True, help="Allow external access (outside of localhost)")
def main(streamer, delay, debug, profile, public):
    """Digital Audio Recorder server program (based on Flask)
    """
    if debug > 0:
        log.setLevel(logging.DEBUG if debug > 1 else logging.INFO)
        log.addHandler(dbg_hand)
    host = '0.0.0.0' if public else None

    global dar
    dar = Dar(streamer, debug, profile)
    # defer starting scheduler in case Flask doesn't come up due to port conflict
    # (or whatever)--reduce chance of race between servers for running jobs
    start_timer = threading.Timer(delay, dar.start_scheduler)
    start_timer.start()

    try:
        app.run(host=host)
    except OSError as e:
        # trap known startup failure "[Errno 98] Address already in use"
        if e.errno == 98:
            start_timer.cancel()
            log.error("Exiting due to OSError: %s)" % (e))
            sys.exit(1)
        raise e

if __name__ == '__main__':
    main()
