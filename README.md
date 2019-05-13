# CMDAR &ndash; (Classical Music) Digital Audio Recorder #

## Project ##

### Introduction ###

This is an audio version of the DVR.  The idea is to provide the following capabilities:

* Record regular (e.g. daily or weekly) programs on the "internet radio" (anything with an
  audio stream)
* Schedule ad hoc recording of an online stream

### Status ###

This is work in process.  It's currently working for me, but I want to at least ensure
that it works for (selected?) others as well.

### Planned future capabilities ###

* Radio tuners actively recording into circular buffers, which can then be played
  (including seeking within) or converted into saved recordings
* Integration with online station calendar/program guides
    * Discover and automatically record shows of interest

(see **TODO.md** for more details)

## Requirements ##

The current package is depenent on the following:

* **Python 3.7**
* **virtualenv** (or `python3-venv` package on Ubuntu)
    * This is not a strict requirement, but the `dar_server.sh` shell script wrapper
      expects it (though you can also run the server using `python` directly, see **Start
      the server** below)
* **VLC 3.0**
    * Note: his is invoked through the `cvlc` command line interface

These should be installed in your environment before proceeding with the set up
instructions below.

## Setting Things Up ##

*This is just a quick-and-dirty initial guide, I will write some better documentation
later.  Note that this has only been run on Ubuntu (18.04) to date--there are no
guarantees that it will work on other platforms exactly the same way.*

1. **Clone this project and create virtual environment**

            $ git clone git@github.com:crashka/cmdar.git cmdar
            $ cd cmdar
            $ virtualenv -p python3.7 venv

    (Or "`python3.7 -m venv venv`" can be used if the `venv` module is available)

2. **Install package dependencies in virtual environment**

            $ . venv/bin/activate
            (venv) $ pip install -r requirements.txt
            (venv) $ deactivate

3. **Edit the configuration file**

            $ emacs config/config.yml

    Create your own profile within the configuration, using `caladan` (seeded in the file)
    as an example.  Your profile should include the regularly scheduled programs you want
    to be persistent, as well as the streamer/scheduler parameters appropriate to your
    environment.  See **Configuration**, below, for more information on the content/format
    for the config file.

4. **Start the server**

            $ scripts/dar_server.sh --profile=<your_profile> --debug=2 --public

    You can also run using `python` directly, but you must be within the virtual
    environment (if you're using one):

            (venv) $ cd cmdar
            (venv) $ python server.sh --profile=<your_profile> --debug=2 --public

5. **Add crontab entry for server**

            $ crontab -e

    Note that new server instantiations started by cron will exit immediately if a server
    process is already running (listening port will be busy)--this is by design.  Thus,
    the crontab configuration I am currently using in my "production" environment looks
    like this:

            29,59 * * * * /local/prod/cmdar/scripts/dar_server.sh --profile=caladan --debug=2 --public >> /local/prod/cmdar/log/dar_server.log 2>&1

    You will expect to see stderr messages in the log file that look like this (a little
    ugly for now, but they do indicate that the server has not failed and is presumably
    healthy--you should ensure that log entries documenting execution of scheduled
    programs are interspersed):

            Sun May 12 16:29:01 PDT 2019 COMMAND: dar_server.sh --profile=caladan --debug=2 --public
             * Serving Flask app "server" (lazy loading)
             * Environment: production
               WARNING: Do not use the development server in a production environment.
               Use a production WSGI server instead.
             * Debug mode: off
            2019-05-12 16:29:02,560 ERROR [server.py:196]: Exiting due to OSError: [Errno 98] Address already in use)

## Server Command Line ##

        $ scripts/dar_server.sh --help
        Sun May 12 23:29:21 PDT 2019 COMMAND: dar_server.sh --help
        Usage: server.py [OPTIONS]
        
          Digital Audio Recorder server program (based on Flask)
        
        Options:
          --streamer TEXT  Name of streamer in config file (defaults to 'vlc')
          --delay INTEGER  Delay (in secs) before starting scheduler (defaults to 2)
          --debug INTEGER  Debug level (0-3)
          --profile TEXT   Profile in config.yml
          --public         Allow external access (outside of localhost)
          --help           Show this message and exit.

## Configuration ##

The top level of the `config.yml` file specifies the name of a "profile".  The `default`
profile is the base configuration that the other profiles inherit from.  The name of the
profile to be used is specified on the command line for the server (or if invoking
`dar.py` directly as a stand-alone tool).

The next level in the config file specifies each "section" within a profile.  These
sections indicate the parameters for the various components within the DAR.  Note that the
entire section is replaced if it is present within a named profile (i.e. one that inherits
from `default`).  Merging of parameters within a section between `default` and an
inherited profile may be supported at a later time, but for now, unchanged parameter
values must be repeated within the child profile.

The currently defined "section" names within a config "profile" are:

**stations**

: The list of radio stations (or other online audio streams) that the streamer should know
  about in order to record programs and/or manual recordings.

**programs**

: The list of radio programs that you may want subscribe to (i.e. automatically record).
  For now, only `weekly` schedule types are supported, but daily programs can be specified
  using "`Mon-Sun`" as a value for the `days` parameter.  Each program must specify
  `start_time`, and either `end-time` or `duration`.

**streamers**

: The only streamer currently supported is `vlc`, though you can override this section in
  your profile in order to ignore the incidental/inconsequential streamer (i.e. vlc)
  errors that may be present in your environment.  See `ignore_errors` in the `caladan`
  profile provided, as an example of what I have seen (and not yet rectified) in my
  current environment.

**scheduler**

: The only scheduler currently supported is `apscheduler` (PyPI package).  This section
  can be overridden in your profile to specify a destination directory for recordings
  (`rec_dir` parameter).

**server**

: This section is not currently used, so disregard for now (port and host values used by
  Flask are currently hardwired to defaults).

## REST API ##

### Overview ###

These are the only URLs currently implemented (see `cmdar/server.py` for a more complete
listing of the larger planned interface), all currently belonging to the browser-friendly,
pure-GET (and thus not truly RESTful to the pedant, haha) flavor of the API.

The **Todo Item** entity (`/todos`) represents the combination of actively scheduled
programs (the next instance thereof) and manually scheduled recordings (station plus
future date, start time, and end time/duration).

### Notes ###

* All calls return JSON
* For boolean URL parameters, sensible anglo-centric values are recognized (i.e. "`1`",
"`0`", "`true`", "`false`", "`yes`", "`no`", "`on`", "`off`").

### URLs ###

**`GET http://<host>:5000/dar`**

: Show DAR state/info

**`GET http://<host>:5000/dar/state`**

: Get DAR state

**`GET http://<host>:5000/dar/start`**

: Start DAR (new jobs will be spawned when schedule triggers fire)

**`GET http://<host>:5000/dar/pause`**

: Pause DAR (new jobs will not be spawned)

**`GET http://<host>:5000/dar/resume`**

: Resume DAR (spawning of new jobs will be re-enabled)

**`GET http://<host>:5000/dar/shutdown[?<params>]`**

: Shutdown DAR (running jobs will be killed by default)

    The following URL parameters are supported:

    * `wait_for_jobs=<bool>` &ndash; wait for running jobs to complete before shutting down
      scheduler [defaults to `true`]

**`GET http://<host>:5000/programs/reload[?<params>]`**

: Create repeating jobs for programs defined in `config.yml`.  Note that the action name
  in this URL is a misnomer, the configuration is not actually ***re***-loaded from the
  file (rather, the configuration at server instantiation-time is cached)

    The following URL parameters are supported:

    * `do_create=<bool>` &ndash; schedule jobs for programs not currently on the Todo list
      [defaults to `true`]
    * `do_update=<bool>` &ndash; update schedule information for programs already on the Todo
      list [defaults to `true`]
    * `do_pause=<bool>` &ndash; pause active programs (no new jobs) that are not (no longer?)
      represented in the configuration [defaults to `false`]

**`GET http://<host>:5000/todos[?<params>]`**

: List Todo Items (state/info)

## License ##

This project is licensed under the terms of the MIT License.
