# CMDAR &ndash; (Classical Music) Digital Audio Recorder #

## Introduction ##

This is an audio version of the DVR.  The idea is to provide the following capabilities:

* Record regular (e.g. daily or weekly) programs on the "internet radio" (anything with an
  audio stream)
* Schedule ad hoc recording of an online stream

Future new capabilities:

* Radio tuners actively recording into circular buffers, which can then be played
  (including seeking within) or converted into saved recordings
* Integration with online station calendar/program guides
    * Discover and automatically record shows of interest

## Requirements ##

The current package is depenent on the following:

* Python 3.7
* virtualenv (or python3-venv package on Ubuntu)
* VLC 3.0

## Setting Things Up ##

*This is just a quick-and-dirty initial guide, I will write some better documentation
later.  Note that this has only been run on Ubuntu (18.04) to date--there are no
guarantees that it will work on other platforms exactly the same way.*

1. **Clone this project and create virtual environment**

            $ git clone git@github.com:crashka/cmdar.git cmdar
            $ cd cmdar
            $ virtualenv -p python3.7 venv

    (Or `python3.7 -m venv venv` if the `venv` module is available)

2. **Install package dependenceis in virtual environment**

            $ . venv/bin/activate
            (venv) $ pip install -r requirements.txt
            (venv) $ deactivate

3. **Edit the configuration file**

            $ emacs config/config.yml

    Create your own profile, using `caladan` (seeded in the file) as an example.  Your
    profile should include the programs you want to be persistent, as well as the
    streamer/scheduler parameters appropriate to your environment.  See **Configuration**
    below for more information on the content/format for the config file.

4. **Start the server**

            $ scripts/dar_server.sh --profile=<your_profile> --debug=2 --public

    You can also run using `python` directly, but you must be within the virtual
    environment:

            (venv) $ cd cmdar
            (venv) $ python server.sh --profile=<your_profile> --debug=2 --public

5. **Add crontab entry for server**

            $ crontab -e

    Note that new server instantiations will exit immediately if a server process is already running (listening port will be busy)--this is by design.  Thus, the crontab configuration I am currently using in my "production" environment looks like this:

            29,59 * * * * /local/prod/cmdar/scripts/dar_server.sh --profile=caladan --debug=2 --public >> /local/prod/cmdar/log/dar_server.log 2>&1

    You will expect to see stderr messages in the log file that look like this:

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
profile is the base configuration that the other profiles inherit from.  The profile to be
used is specified on the command line for the server (or if invoking `dar.py` directly as
a stand-alone tool).

The next level in the configuration file specifies each "section" within a profile.  These
sections indicate the parameters for the various components within the recorder.  Note
that the entire section is replaced if present within a named profile (i.e. one that
inherits from `default`).  Merging of parameters between `default` and an inherited
profile within a section may be supported at a later time, but for now, unchanged
parameter values must be repeated within the child profile.

The "section" names within a configuration "profile" are currently defined as:

**stations**

: The list of radio stations (or other online audio streams) that the streamer should know
  about in order to record programs and/or manual recordings.

**programs**

: The list of radio programs that you may want subscribe to (i.e. automatically record).
  For now, only `weekly` schedule types are supported, but daily programs can be specified
  using `Mon-Sun` as a value for the `days` parameter.  Each program must specify
  `start_time` and either `end-time` or `duration`.

**streamers**

: The only streamer currently supported is `vlc`, though you can override the section in
  your profile to ignore streamer errors that may be specific to your environment (see the
  `ignore_errors` parameter for the `caladan` profile that has been provided as an
  example).

**scheduler**

: The only scheduler currently supported is the `apscheduler` package.  This section can be overridden in your profile to specify a destination directory for recordings (`rec_dir`).

**server**

: This section is not currently used, so disregard for now (port and host values used by
  Flask are currently hardwired to defaults).

## REST API ##

These are the only URIs currently implemented (see `cmdar/server.py` for a more complete
listing of the more complete planned interface).  These all belong to the browser-friendly
pure-GET flavor of the API.

The **Todo Item** entity (`/todos`) represents the combination of actively scheduled
programs (the next instance thereof) and manually scheduled recordings (station plus
future date, start time, and end time/duration).

Note: for boolean URI parameters, sensible, anglo-centric values are recognized
(i.e. `1`, `0`, `true`, `false`, `yes`, `no`, `on`, `off`).

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

: Shutdown DAR (running jobs will be killed by default).  The following URI parameters are
  supported:

    * `wait_for_jobs=<bool>` - wait for running jobs to complete before shutting down
      scheduler [defaults to true]

**`GET http://<host>:5000/programs/reload[?<params>]`**

: Create repeating jobs for programs defined in config.yml.  Note that the method
  referenced in the URI is a misnomer, the configuration is actually not RE-loaded from
  the file (the configuration from server instantiation is cached).  The following URI
  parameters are supported:

    * `do_create=<bool>` - schedule jobs for programs not currently on the Todo list
      [defaults to true]
    * `do_update=<bool>` - update schedule information for programs already on the Todo
      list [defaults to true]
    * `do_pause=<bool>` - pause active programs (no new jobs) that are not (no longer?)
      represented in the configuration [defaults to false]

**`GET http://<host>:5000/todos[?<params>]`**

: List Todo Items (state/info)

## License ##

This project is licensed under the terms of the MIT License.
