# To Do List #

## Server ##

* Mutual exclusion (dar.py)
* Flask server (mutual exclusion through listening port)

## Scheduler ##

* BUG: "cannot schedule new futures after shutdown" error if creating 'immediate' job, but
  also specifying 'norun'

## Streamer ##

* Compensate for buffering of pre-start-time stream, end at scheduled end
* Compensate for late start (grace period), end at scheduled time
* BUG: "unimplemented query (264) in control" error for KUSC_MP3 stream

## Logging/Error Handling ##

* Rectify debug and verbosity levels across scheduler and streamer modules

## Testing ##

* Fix the command line for selecting config profiles (i.e. revisit --testing flag)
