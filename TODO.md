# To Do List #

## Server ##

* ~~Flask server (with mutual exclusion through listening port)~~
* Mutual exclusion for command line scheduler (dar.py)

## DAR ##

* Change reload_programs() to record_programs()
    * Note: we don't really re-read the config file (nor should we)
* Rectify Program and Todo Item
    * Don't pause manual todo items when reloading programs
* Implement manual recording (refactor reload_programs)
    * Only support WEEKLY ScheduleType for programs

## Scheduler ##

* Create usable ID for scheduled jobs (hash of name?)
* Capture streamer exceptions in listener and add (somehow!) to parent Dar
* BUG: "cannot schedule new futures after shutdown" error if creating 'immediate' job, but
  also specifying 'norun'

## Streamer ##

* Compensate for buffering of pre-start-time stream, end at scheduled end (pass start_time
  into do_record() and save_stream())
* ~~Ignore expected and/or harmless errors that don't affect processing (list in config.yml)~~
* Check integrity of output file after stream is closed (check and balance for ignoring
  errors in stdeff
* Compensate for late start (grace period), end at scheduled time
* BUG: "unimplemented query (264) in control" error for KUSC_MP3 stream

## Logging/Error Handling ##

* Rectify debug and verbosity levels across scheduler and streamer modules

## Testing ##

* ~~Fix the command line for selecting config profiles (i.e. revisit --testing flag)~~
    * ~~'profile' should be an arg to Dar.\_\_init\_\_(), do\_record(), and Streamer.get()~~

## Roadmap (Big Ticket Items) ##

* Active tuner(s) recording into circular buffer(s) (a la TiVo)
    * UPnP streamer serving content from circular buffer(s)
    * Ability to convert active buffer into a recording (set new end_time)
* Integration with playlist manager (cm3 project)
* Integration with SoCo package (e.g. play from tuner)
