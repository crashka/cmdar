#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Streamer/media player
"""

import sys
import re
import logging
import subprocess
import datetime as dt

from core import cfg, log
from utils import LOV, str2time_dt

##############
# base class #
##############

class Streamer(object):
    """Obtain streamer subclass by config file name (direct references to subclass not allowed)

    Note: this method sets "name" and "info" (config parameters) subclass attributes
    """
    @classmethod
    def get(cls, name, cfg_profile = None):
        """
        :param name: name of streamer defined in config.yml
        """
        streamers = cfg.config('streamers', cfg_profile)
        if name not in streamers:
            raise RuntimeError("Streamer \"%s\" not known" % (name))
        info = streamers[name]
        subcls = getattr(sys.modules[cls.__module__], info['subclass'])
        subcls.name = name
        subcls.info = info
        return subcls

    @classmethod
    def save_stream(cls, url, media_type, filebase, duration, verbose = 2, dryrun = False):
        """
        :param url: stream URL (str)
        :param media_type: stream content-type (str)
        :param filebase: file or path name [minus file type] (str)
        :param duration: seconds (int) or [HH:]MM:SS (str)
        :param force: whether to overwrite existing file (bool)
        :param verbose: level (0-3) or False|True (same as 0|1)
        :param dryrun: build command, but do not execute (bool)
        :return: pathname of saved stream (or command args, if dryrun=True)
        """
        raise NotImplementedError("abstract method")

################
# subclass(es) #
################

VLC_CMD         = 'cvlc'
VLC_DFLT_FLAGS  = ['--no-sout-all',
                   '--sout-keep',
                   '--no-sout-file-overwrite',
                   '--play-and-exit']
VLC_FORCE_FLAGS = ['--no-sout-all',
                   '--sout-keep',
                   '--play-and-exit']

class VlcStreamer(Streamer):
    """
    """
    @classmethod
    def save_stream(cls, url, media_type, filebase, duration, add_ts = False, force = False,
                    verbose = False, dryrun = False):
        """
        :param url: stream URL (str)
        :param media_type: stream content-type (str)
        :param filebase: file or path name [minus file type] (str)
        :param duration: seconds (int) or [HH:]MM:SS (str)
        :param add_ts: whether to add timestamp to filebase (bool)
        :param force: whether to overwrite existing file (bool)
        :param verbose: level (0-3) or False|True (same as 0|1)
        :param dryrun: build command, but do not execute (bool)
        :return: pathname of saved stream (or command line, if dryrun=True)
        """
        if not hasattr(cls, 'name') or not hasattr(cls, 'info'):
            raise RuntimeError("%s must be obtained through Streamer.get()" % (cls.__name__))
        if media_type not in cls.info['media_types']:
            raise RuntimeError("media type \"%s\" not defined for streamer \"%s\"" % (media_type, cls.name))
        media_info = cls.info['media_types'][media_type]

        muxer = media_info['muxer']
        if add_ts:
            filebase += dt.datetime.now().strftime('%m%d%H%M')

        fileout = filebase + '.' + media_info['file_type']
        if isinstance(verbose, bool):
            verbose = int(verbose)
        sout_tc  = 'transcode{vcodec=none,scodec=none}'
        sout_ac  = 'file{mux=%s,dst=%s}' % (muxer, fileout)
        if isinstance(duration, str):
            delta = str2timedelta(duration)
            assert delta.days == 0
            duration = delta.seconds

        args = [VLC_CMD]
        if verbose > 0:
            args.append('-' + 'v' * verbose)
        args.append(url)
        args.append('--sout=#%s:%s' % (sout_tc, sout_ac))
        args.append('--run-time=%d' % (duration))
        args.extend(VLC_FORCE_FLAGS if force else VLC_DFLT_FLAGS)
        if dryrun:
            return ' '.join(args)

        log.info("Saving stream, cmd = '%s'" % (' '.join(args)))
        cp = subprocess.run(args, check=True, text=True, capture_output=True)
        # VLC does not have non-zero returncode on error, have to grep through stderr
        ignore = set(cls.info.get('ignore_errors', []))
        errors = []
        for line in cp.stderr.splitlines():
            m = re.fullmatch(r'(\[[0-9a-f]+\]) ([\w ]+) error: (.+)', line)
            if m:
                error_msg = m.group(3)
                if error_msg in ignore:
                    log.info("Ignoring error: \"%s\"" % (error_msg))
                else:
                    errors.append(error_msg)
        if errors:
            log.info("Errors: %s" % (errors))
            log.debug("Full stderr:\n" + cp.stderr.rstrip())
            raise RuntimeError(errors[0])
        return fileout

#####################
# command line tool #
#####################

import click
from core import dbg_hand

@click.command()
@click.option('--media_type', required=True, help="Stream content-type (e.g. audio/aacp)")
@click.option('--filebase',   required=True, help="File or path name (minus file type)")
@click.option('--duration',   required=True, help="Seconds or [HH:]MM:SS")
@click.option('--add_ts',     is_flag=True, help="Add timestamp to filename")
@click.option('--force',      is_flag=True, help="Overwrite file, if it already exists")
@click.option('--dryrun',     is_flag=True, help="Do not run, print out command instead")
@click.option('--debug',      default=0, help="Debug level (0-3)")
@click.argument('url',        required=True)
def main(media_type, filebase, duration, add_ts, force, dryrun, debug, url):
    """Command line for saving audio stream to a file
    """
    if debug > 0:
        log.setLevel(logging.DEBUG)
        log.addHandler(dbg_hand)

    if re.fullmatch(r'\d+', duration):
        duration = int(duration)

    streamer = Streamer.get('vlc')
    strout = streamer.save_stream(url, media_type, filebase, duration, add_ts=add_ts,
                                  force=force, verbose=debug, dryrun=dryrun)
    if dryrun:
        print("Command line: %s" % (strout))
    else:
        print("File created: %s" % (strout))

if __name__ == '__main__':
    main()
