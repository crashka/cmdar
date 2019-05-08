#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Digital Audio Recorder
"""

import os.path
import re
import logging
import datetime as dt

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.events import *

from __init__ import *
from core import BASE_DIR, cfg, log
from utils import LOV, str2timedelta, str2datetime, str2time, str2time_dt
from streamer import Streamer

################
# config stuff #
################

SCHEDULER = cfg.config('scheduler')

DB_DIR    = SCHEDULER['db_dir']
DB_FILE   = SCHEDULER['db_file']
if not DB_DIR:
    DB_PATH = DB_FILE
elif DB_DIR[0] in ('/.'):
    DB_PATH = os.path.join(DB_DIR, DB_FILE)
else:
    DB_PATH = os.path.join(BASE_DIR, DB_DIR, DB_FILE)
DB_URL    = 'sqlite:///' + DB_PATH

REC_DIR = SCHEDULER['rec_dir']
if not REC_DIR:
    REC_PATH = '.'
elif REC_DIR[0] in ('/.'):
    REC_PATH = REC_DIR
else:
    REC_PATH = os.path.join(BASE_DIR, REC_DIR)
# detect bad rec_dir on module load to avoid later embarrassment
if not os.path.isdir(REC_PATH):
    raise ConfigError("rec_dir \"%s\" is not a valid directory" % (REC_DIR))

ScheduleType  = LOV(['IMMEDIATE',
                     'ONCE',
                     'DAILY',
                     'WEEKLY',
                     'MONTHLY'], 'lower')

##################
# util functions #
##################

def schedule_trigger(sched):
    """Get trigger information from schedule structure

    :param sched: config file format (dict)
    :return: apscheduler trigger
    """
    if sched['type'] == ScheduleType.IMMEDIATE:
        if not sched.get('duration'):
            raise ConfigError("Must specify duration for %s schedule" % (sched['type']))
        return None
    elif sched['type'] == ScheduleType.ONCE:
        if not sched.get('date') or not sched.get('start_time'):
            raise ConfigError("Must specify date and start_time for %s schedule" % (sched['type']))
        run_dt = str2datetime("%s %s" % (sched['date'], sched['start_time']))
        return DateTrigger(run_date=run_dt)
    elif sched['type'] == ScheduleType.WEEKLY:
        if not sched.get('days') or not sched.get('start_time'):
            raise ConfigError("Must specify days and start_time for %s schedule" % (sched['type']))
        start = str2time(sched['start_time'])
        cron_info = {'day_of_week': sched['days'].lower(),
                     'hour'       : start.hour,
                     'minute'     : start.minute,
                     'second'     : start.second}
        return CronTrigger(**cron_info)
    else:
        raise NotImplementedError("Schedule type \"%s\" not supported" % (sched['type']))

def schedule_duration(sched):
    """Get duration information from schedule structure

    :param sched: config file format (dict)
    :return: number of seconds (int)
    """
    if sched.get('duration') and sched.get('end_time'):
        raise ConfigError("May not specify both duration and end_time")
    if sched.get('duration'):
        if isinstance(sched['duration'], int) or re.fullmatch(r'\d+', sched['duration']):
            delta = dt.timedelta(0, int(sched['duration']))
        else:
            delta = str2timedelta(sched['duration'])
    elif sched.get('end_time'):
        if not sched.get('start_time'):
            raise ConfigError("Must specify start_time if end_time specified")
        delta = str2time_dt(sched['end_time']) - str2time_dt(sched['start_time'])
    else:
        raise ConfigError("Must specify either duration or end_time")
    assert 'delta' in locals()
    # note that days will be negative if end_time is less then start_time (cross midnight
    # boundary), but seconds will still be right (no need to muck with day or negativity)
    assert delta.days in (0, -1)
    return delta.seconds


#######################
# scheduler functions #
#######################

APSCHED_EVENTS = ['EVENT_SCHEDULER_STARTED',
                  'EVENT_SCHEDULER_SHUTDOWN',
                  'EVENT_SCHEDULER_PAUSED',
                  'EVENT_SCHEDULER_RESUMED',
                  'EVENT_EXECUTOR_ADDED',
                  'EVENT_EXECUTOR_REMOVED',
                  'EVENT_JOBSTORE_ADDED',
                  'EVENT_JOBSTORE_REMOVED',
                  'EVENT_ALL_JOBS_REMOVED',
                  'EVENT_JOB_ADDED',
                  'EVENT_JOB_REMOVED',
                  'EVENT_JOB_MODIFIED',
                  'EVENT_JOB_EXECUTED',
                  'EVENT_JOB_ERROR',
                  'EVENT_JOB_MISSED',
                  'EVENT_JOB_SUBMITTED',
                  'EVENT_JOB_MAX_INSTANCES']

def apsched_eventname(event):
    """Return name of apscheduler event
    """
    return APSCHED_EVENTS[event.code.bit_length() - 1]

def apsched_listener(event):
    """Event handler for scheduler engine
    """
    if isinstance(event, JobExecutionEvent):
        info = {'event'    : apsched_eventname(event),
                'job_id'   : event.job_id,
                'jobstore' : event.jobstore,
                'run_time' : str(event.scheduled_run_time),
                'retval'   : event.retval,
                'exception': event.exception}
    elif isinstance(event, JobEvent):
        info = {'event'    : apsched_eventname(event),
                'job_id'   : event.job_id,
                'jobstore' : event.jobstore}
    else:
        info = {'event'    : apsched_eventname(event),
                'alias'    : event.alias}
    log.error(info) if info.get('exception') else log.info(info)

def apsched_init(debug = 0):
    """Initialize and return scheduler handle
    """
    if debug > 0:
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    apsched = BackgroundScheduler()
    apsched.add_jobstore(SQLAlchemyJobStore(url=DB_URL))
    apsched.add_listener(apsched_listener)
    return apsched

################
# DAR entities #
################

"""
Dar Entities:
  - Station
    - Create
    - Record
    - Delete
  - Program
    - Create
    - Record
    - Delete
  - Todo Item
    - Create
    - Suspend
    - Resume
    - Delete
  - Recording
    - Start
    - Stop
    - Delete
  - Tuner
    - Start
    - Change
    - Record
    - Stop
"""

def validate_streamer(streamer):
    """
    """
    engine = Streamer.get(streamer)
    if not issubclass(engine, Streamer) or type(engine) is Streamer:
        raise RuntimeError("Bad engine type \"%s\" for \"%s\"" % (engine.__name__, streamer))

def do_record(streamer, *args, **kwargs):
    """
    """
    engine = Streamer.get(streamer)
    return engine.save_stream(*args, **kwargs)

class Dar(object):
    """
    """
    def __init__(self):
        """
        """
        self.stations   = cfg.config('stations')
        self.programs   = cfg.config('programs')
        self.testprogs  = cfg.config('testprogs')
        self.todo_items = {}
        self.recordings = {}
        self.tuners     = {}

class Station(object):
    """
    """
    def __init__(self):
        """
        """
        pass
    
    def record_manual(station, sched_info, save_as_program = None):
        """
        :param station: Station or name
        :param sched_info: config file format (dict)
        :param save_as_program: program name (or don't save, if not specified)
        """
        pass

class Program(object):
    """
    """
    def __init__(self):
        """
        """
        pass
    
    def record_program(program, repeating = True):
        """
        """
        pass

class TodoItem(object):
    """
    """
    def __init__(self):
        """
        """
    
    def suspend_todo_item():
        """
        """
        pass

    def resume_todo_item():
        """
        """
        pass

    def delete_todo_item():
        """
        """
        pass

class Recording(object):
    """
    """
    def __init__(self):
        """
        """
        pass
    
class Tuner(object):
    """
    """
    def __init__(self):
        """
        """
        pass

#####################
# command line tool #
#####################

from time import sleep
import click
from core import dbg_hand

@click.command()
@click.option('--list',     'cmd', flag_value='list', default=True, help="List scheduled jobs")
@click.option('--reload',   'cmd', flag_value='reload', help="Reload jobs from config file")
@click.option('--run',      'cmd', flag_value='run', help="Run the audio recorder")
@click.option('--time',     default=9999999, help="Time (in seconds) to run (forever, if not specified)")
@click.option('--streamer', default='vlc', help="Name of streamer in config file (defaults to 'vlc')")
@click.option('--nowait',   is_flag=True, help="Do not wait for jobs to complete when terminating")
@click.option('--debug',    default=0, help="Debug level (0-3)")
#@click.argument('name',    default='all', required=True)
def main(cmd, time, streamer, nowait, debug):
    """Digital Audio Recorder command line interface
    """
    if debug > 0:
        log.setLevel(logging.DEBUG)
        log.addHandler(dbg_hand)

    recorder = Dar()
    programs = recorder.testprogs

    apsched = apsched_init(debug)

    if cmd == 'reload':
        validate_streamer(streamer)
        for prog, info in programs.items():
            station_name = info['station']
            sched_info   = info['schedule']
            station      = recorder.stations[station_name]
            url          = station['stream_url']
            media_type   = station['media_type']

            station_path = os.path.join(REC_PATH, station_name)
            if not os.path.isdir(station_path):
                os.mkdir(station_path)
            filebase     = os.path.join(station_path, station_name.lower())
            duration     = schedule_duration(sched_info)
            trigger      = schedule_trigger(sched_info)

            args         = (streamer, url, media_type, filebase, duration)
            kwargs       = {'add_ts': True}
            apsched.add_job(do_record, trigger, args=args, kwargs=kwargs, id=prog, name=prog,
                            replace_existing=True, misfire_grace_time=300)

        apsched.start(paused=True)
        for job in apsched.get_jobs():
            if job.id in programs:
                print("Added job \"%s\":\n  %s" % (job.id, str(job)))
            else:
                job.pause()
                print("Pausing job \"%s\":\n  %s" % (job.id, str(job)))
    elif cmd == 'list':
        apsched.start(paused=True)
        for job in apsched.get_jobs():
            print("Scheduled job \"%s\":\n  %s" % (job.id, str(job)))
    elif cmd == 'run':
        apsched.start()
        sleep(time)
        apsched.shutdown(wait=(not nowait))

if __name__ == '__main__':
    main()
