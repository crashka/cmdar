#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""DAR Server (based on Flask)
"""

import logging

from flask import Flask, jsonify
import click

from core import BASE_DIR, cfg, log, dbg_hand
from dar import Dar

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
GET    /dar/shutdown[?<params>]         - shutdown DAR (kill running jobs) [**]

GET    /stations/<name>/record?<params> - schedule manual recording

GET    /programs/create?<params>        - create new program
GET    /programs/reload[?<params>]      - reload from config file [**]
GET    /programs/<id>/update?<params>   - update program info
GET    /programs/<id>/activate          - activate program
GET    /programs/<id>/inactivate        - inactivate program
GET    /programs/<id>/delete            - delete program

GET    /todos/<id>/suspend              - suspend todo item
GET    /todos/<id>/requeue              - requeue todo item
GET    /todos/<id>/cancel               - cancel todo item
GET    /todos/<id>/delete               - delete todo item (same as ``cancel``???)

[**] indicates implemented below
"""

@app.route('/dar')
def dar_info():
    return jsonify(dar.get_info())

@app.route('/dar/state')
def dar_state():
    return jsonify(state=dar.state)

@app.route('/dar/start')
def dar_start():
    return jsonify(result=dar.start_scheduler())

@app.route('/dar/pause')
def dar_pause():
    return jsonify(result=dar.pause_scheduler())

@app.route('/dar/resume')
def dar_resume():
    return jsonify(result=dar.resume_scheduler())

@app.route('/dar/shutdown')
def dar_shutdown():
    return jsonify(result=dar.stop_scheduler())

@app.route('/programs/reload')
def programs_reload():
    result = dar.reload_programs()
    return jsonify({i: list(j) for i, j in result.items()})

@app.route('/todos')
def todos_list():
    todos = []
    for job in dar.get_jobs():
        status = "Queued" if job.next_run_time else "Suspended"
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
@click.option('--debug',    default=0, help="Debug level (0-3)")
@click.option('--profile',  default=None, type=str, help="Profile in config.yml")
@click.option('--public',   is_flag=True, help="Allow external access (outside of localhost)")
def main(streamer, debug, profile, public):
    """Digital Audio Recorder server program (based on Flask)
    """
    if debug > 0:
        log.setLevel(logging.DEBUG if debug > 1 else logging.INFO)
        log.addHandler(dbg_hand)
    host = '0.0.0.0' if public else None

    global dar
    dar = Dar(streamer, debug, profile)
    dar.start_scheduler()

    app.run(host=host)

if __name__ == '__main__':
    main()
