# To Do List #

## Server ##

* Mutual exclusion (or at least race protection) for command line scheduler (dar.py)

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
* Check integrity of output file after stream is closed (check and balance for ignoring
  errors in stdeff
* Compensate for late start (grace period), end at scheduled time
* BUG: "unimplemented query (264) in control" error for KUSC_MP3 stream

## Logging/Error Handling ##

* Rectify debug and verbosity levels across scheduler and streamer modules

## Testing ##

* Yes

## Roadmap (Bigger Ticket Items) ##

* Use Mutagen to write recordings metadata to output files
* Active tuner(s) recording into circular buffer(s) (a la TiVo)
    * UPnP streamer serving content from circular buffer(s)
    * Ability to convert active buffer into a recording (set new end_time)
* Integration with playlist manager (cm3 project)
* Integration with SoCo package (e.g. play from tuner)
