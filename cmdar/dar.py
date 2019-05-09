#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Digital Audio Recorder
"""

import os.path
import re
import logging
import datetime as dt
#from random import choice

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

ScheduleType  = LOV(['IMMEDIATE',
                     'ONCE',
                     'DAILY',
                     'WEEKLY',
                     'MONTHLY'], 'lower')

#####################
# utility functions #
#####################

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


#########################
# apscheduler functions #
#########################

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

def apsched_init(db_path, debug = 0):
    """Initialize and return apscheduler handle
    """
    if debug > 3:
        logging.basicConfig()
        logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    sched = BackgroundScheduler()
    db_url = 'sqlite:///' + db_path
    sched.add_jobstore(SQLAlchemyJobStore(url=db_url))
    sched.add_listener(apsched_listener)
    return sched

######################
# streamer functions #
######################

def validate_streamer(streamer):
    """
    """
    engine = Streamer.get(streamer)
    if not issubclass(engine, Streamer) or type(engine) is Streamer:
        raise RuntimeError("Bad engine type \"%s\" for \"%s\"" % (engine.__name__, streamer))

def do_record(streamer, *args, **kwargs):
    """
    """
    # REVISIT: this is a little bit of a fudge, need to rethink the relatioship between
    # debug and verbosity levels across the streamer and scheduler modules!!!
    debug = kwargs.get('verbose', 0)
    if debug > 0:
        log.setLevel(logging.DEBUG)
        log.addHandler(dbg_hand)

    engine = Streamer.get(streamer)
    return engine.save_stream(*args, **kwargs)

################
# DAR entities #
################

"""
- Dar (recorder)
- Station
- Program
- Todo Item
- Recording
- Tuner
"""

class Dar(object):
    """
    """
    def __init__(self, debug = 0, testing = False):
        """
        """
        cfg_profile = 'testing' if testing else None
        self.stations    = cfg.config('stations', cfg_profile)
        self.programs    = cfg.config('programs', cfg_profile)
        self.scheduler   = cfg.config('scheduler', cfg_profile)
        self.todo_items  = {}
        self.recordings  = {}
        self.tuners      = {}

        self.db_dir      = self.scheduler['db_dir']
        self.db_file     = self.scheduler['db_file']
        self.rec_dir     = self.scheduler['rec_dir']

        if not self.db_dir:
            self.db_path = self.db_file
        elif self.db_dir[0] in ('/.'):
            self.db_path = os.path.join(self.db_dir, self.db_file)
        else:
            self.db_path = os.path.join(BASE_DIR, self.db_dir, self.db_file)
        self.sched = apsched_init(self.db_path, debug)

        if not self.rec_dir:
            self.rec_path = '.'
        elif self.rec_dir[0] in ('/.'):
            self.rec_path = self.rec_dir
        else:
            self.rec_path = os.path.join(BASE_DIR, self.rec_dir)
        # detect bad rec_dir on instantiation to avoid later embarrassment
        if not os.path.isdir(self.rec_path):
            raise ConfigError("rec_dir \"%s\" is not a valid directory" % (self.rec_dir))

class Station(object):
    """
    - Create
    - Record
    - Delete
    """
    def __init__(self):
        """
        """
        pass
    
    def create(self):
        """
        """
        pass

    def record(self, sched_info, save_as_program = None):
        """Manually start/schedule a recording

        :param sched_info: config file format (dict)
        :param save_as_program: program name (or don't save, if not specified)
        """
        pass

    def delete(self):
        """
        """
        pass

class Program(object):
    """
    - Create
    - Record
    - Delete
    """
    def __init__(self):
        """
        """
        pass
    
    def create(self):
        """
        """
        pass

    def record(self, repeating = True):
        """
        """
        pass

    def delete(self):
        """
        """
        pass

class TodoItem(object):
    """
    - Create
    - Suspend
    - Resume
    - Delete
    """
    def __init__(self):
        """
        """
    
    def create(self):
        """
        """
        pass

    def suspend(self):
        """
        """
        pass

    def resume(self):
        """
        """
        pass

    def delete(self):
        """
        """
        pass

class Recording(object):
    """
    - Start
    - Stop
    - Delete
    """
    def __init__(self):
        """
        """
        pass
    
    def start(self):
        """
        """
        pass

    def stop(self):
        """
        """
        pass

    def delete(self):
        """
        """
        pass

class Tuner(object):
    """
    - Start
    - Change
    - Record
    - Stop
    """
    def __init__(self):
        """
        """
        pass

    def start(self):
        """
        """
        pass

    def change(self):
        """
        """
        pass

    def record(self):
        """
        """
        pass

    def stop(self):
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
@click.option('--list',     'list_jobs', is_flag=True, help="List scheduled jobs")
@click.option('--reload',   is_flag=True, help="Reload programs/jobs from config file")
@click.option('--norun',    is_flag=True, help="Do not run the audio recorder (e.g. list or reload only)")
@click.option('--time',     'run_time', default=9999999, help="Time (in seconds) to run (forever, if not specified)")
@click.option('--streamer', default='vlc', help="Name of streamer in config file (defaults to 'vlc')")
@click.option('--nowait',   is_flag=True, help="Do not wait for jobs to complete when time expires")
@click.option('--debug',    default=0, help="Debug level (0-3)")
@click.option('--testing',  is_flag=True, help="Use 'testing' profile in config file")
#@click.argument('name',    default='all', required=True)
def main(list_jobs, reload, norun, run_time, streamer, nowait, debug, testing):
    """Digital Audio Recorder command line interface
    """
    if debug > 0:
        log.setLevel(logging.DEBUG if debug > 1 else logging.INFO)
        log.addHandler(dbg_hand)

    dar = Dar(debug, testing)
    # NOTE: creating 'sched' for convenience, and pretending that this could be a generic
    # scheduler handle (though the semantics below are unabashedly those of apscheduler)
    sched = dar.sched

    if reload:
        validate_streamer(streamer)
        if not sched.running:
            sched.start(paused=True)

        prev_jobs = set([job.id for job in sched.get_jobs()])
        load_jobs = set()

        for prog, info in dar.programs.items():
            station_name = info['station']
            sched_info   = info['schedule']
            station      = dar.stations[station_name]
            if isinstance(station['stream_url'], list):
                # LATER: perhaps choose at random (if assuming all URLs are reliable),
                # but for now we take the same (last) one on the list for consistency
                #url      = choice(station['stream_url'])
                url      = station['stream_url'][-1]
            else:
                url      = station['stream_url']
            media_type   = station['media_type']

            station_path = os.path.join(dar.rec_path, station_name)
            if not os.path.isdir(station_path):
                os.mkdir(station_path)
            filebase     = os.path.join(station_path, station_name.lower())
            duration     = schedule_duration(sched_info)
            trigger      = schedule_trigger(sched_info)

            name         = "%s [dur %s]" % (prog, str(dt.timedelta(0, duration)))
            args         = (streamer, url, media_type, filebase, duration)
            # TODO: get parameters for the streamer from the config file (hard-wiring
            # values to use for now)!!!
            kwargs       = {'add_ts': True, 'verbose': 1}
            sched.add_job(do_record, trigger, args=args, kwargs=kwargs, id=prog, name=name,
                            replace_existing=True, misfire_grace_time=300)
            load_jobs.add(prog)

        new_jobs = load_jobs.difference(prev_jobs)
        upd_jobs = load_jobs.intersection(prev_jobs)
        obs_jobs = prev_jobs.difference(load_jobs)

        print("Loading/reloading jobs from config file...")
        for job in [sched.get_job(id) for id in new_jobs]:
            print("  Added new job \"%s\":\n    %s" % (job.id, str(job)))
        for job in [sched.get_job(id) for id in upd_jobs]:
            print("  Updated existing job \"%s\":\n    %s" % (job.id, str(job)))
        for job in [sched.get_job(id) for id in obs_jobs]:
            job.pause()
            #job = sched.get_job(job.id)
            print("  Pausing obsolete job \"%s\":\n    %s" % (job.id, str(job)))

    if list_jobs:
        if not sched.running:
            sched.start(paused=True)

        print("Listing scheduled jobs...")
        for job in sched.get_jobs():
            status = "Scheduled" if job.next_run_time else "Paused"
            print("  %s job \"%s\":\n    %s" % (status, job.id, str(job)))

    if norun:
        if sched.running:
            sched.shutdown()
    else:
        print("Running scheduler for %s..." % (str(dt.timedelta(0, run_time))))
        if not sched.running:
            sched.start()
        else:
            sched.resume()  # no-op if actively running (not paused)
        sleep(run_time)
        sched.shutdown(wait=(not nowait))

if __name__ == '__main__':
    main()
