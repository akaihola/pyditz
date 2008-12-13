#!/usr/bin/env python
# -*- coding: utf-8 -*-

VERSION = '0.1'

__doc__ = """
SYNOPSIS

    pyditz.py [-h,--help] [-v,--verbose] [--version] [-u,--unittest]
              [-a,--after] [-b,--before] FILE/DIRECTORY...

DESCRIPTION

    This utility calculates total time spent in progress of given Ditz issues.

EXAMPLES

    $ pyditz.py -a 2008-07-01 ditz/issue-*.yaml
    $ pyditz.py -b 2008-08-01 ditz 

AUTHOR

    Antti Kaihola <akaihol+ditz@ambitone.com>

LICENSE

    This program is distributed under the terms of the GNU Affero General
    Public License.

VERSION

    %s
""" % VERSION


from glob import glob
from os.path import join, isdir, isfile
from optparse import OptionParser, TitledHelpFormatter, Option, OptionValueError
from copy import copy
from datetime import timedelta, datetime
import logging
import yaml


CLOSE_STATUS = 'closed issue with disposition '
CHANGE_STATUS = 'changed status from '
def parse_status(status):
    """
    >>> parse_status('changed status from unstarted to in_progress')
    ('unstarted', 'in_progress')
    >>> parse_status('changed status from in_progress to paused')
    ('in_progress', 'paused')
    >>> parse_status('changed status from paused to in_progress')
    ('paused', 'in_progress')
    >>> parse_status('closed issue with disposition fixed')
    (None, 'fixed')
    """
    if status.startswith(CLOSE_STATUS):
        return None, status[len(CLOSE_STATUS):]
    elif status.startswith(CHANGE_STATUS):
        parts = status[len(CHANGE_STATUS):].split()
        if parts[1] != 'to':
            raise ValueError('Invalid status change message %r' % status)
        return parts[0], parts[2]
    else:
        raise ValueError('Invalid status change message %r' % status)

class Issue(yaml.YAMLObject):
    """
    A YAML-serializable Ditz issue object
    """
    yaml_tag = u'!ditz.rubyforge.org,2008-03-06/issue'

    def total_time(self, earliest=None, latest=None):
        r"""
        >>> from StringIO import StringIO
        >>> i = yaml.load(StringIO('''--- !ditz.rubyforge.org,2008-03-06/issue 
        ... log_events: 
        ... - - 2008-06-16 10:39:28.385966 Z
        ...   - Antti Kaihola <akaihol+ditz@ambitone.com>
        ...   - created
        ...   - ""
        ... - - 2008-06-16 10:39:33.857418 Z
        ...   - Antti Kaihola <akaihol+ditz@ambitone.com>
        ...   - changed status from unstarted to in_progress
        ...   - ""
        ... - - 2008-06-16 11:39:41.877059 Z
        ...   - Antti Kaihola <akaihol+ditz@ambitone.com>
        ...   - changed status from in_progress to paused
        ...   - ""
        ... - - 2008-10-06 10:39:33.857418 Z
        ...   - Antti Kaihola <akaihol+ditz@ambitone.com>
        ...   - changed status from paused to in_progress
        ...   - ""
        ... - - 2008-10-06 12:39:41.877059 Z
        ...   - Antti Kaihola <akaihol+ditz@ambitone.com>
        ...   - changed status from in_progress to paused
        ...   - ""
        ... '''))

        >>> i.total_time()
        datetime.timedelta(0, 10816, 39282)

        >>> from datetime import datetime
        >>> i.total_time(earliest=datetime(2008,9,1))
        datetime.timedelta(0, 7208, 19641)
        >>> i.total_time(latest=datetime(2008,9,1))
        datetime.timedelta(0, 3608, 19641)
        """

        def filtered(timestamp):
            """Return True if timestamp is earlier or later than those
            specified in the arguments of the wrapping function."""
            if earliest is not None and timestamp < earliest:
                return True
            if latest is not None and timestamp > latest:
                return True
            return False

        cum_time = timedelta()
        dtstart = None
        for timestamp, _person, status, _comment in self.log_events:
            if status in ('created', 'commented'):
                continue
            _status_from, status_to = parse_status(status)
            if status_to == 'in_progress':
                if not filtered(timestamp):
                    dtstart = timestamp
            elif status_to in ('paused', 'fixed'):
                if dtstart is not None:
                    cum_time += timestamp - dtstart
                    dtstart = None
            else:
                raise ValueError('Unknown status %r' % status_to)
        return cum_time

    def __repr__(self):
        return self.id


def format_timedelta(delta):
    """
    >>> format_timedelta(timedelta(0, 99999))
    " 27h46'"
    >>> format_timedelta(timedelta(0, 60))
    "     1'"
    >>> format_timedelta(timedelta(0, 3600))
    "  1h00'"
    """
    minutes = 24 * 60 * delta.days + delta.seconds // 60
    hours = minutes // 60
    hstr = hours and '%3dh' % hours or '    '
    mstr = (hours and "%02d'" or "%2d'") % (minutes % 60)
    return hstr + mstr


def iterate_files(filepaths):
    """
    Yield a read-only file handle for
     * each file in ``filepaths``
     * each issue file inside each directory in ``filepaths``.
    """
    for direntry in filepaths:
        if isdir(direntry):
            files = glob(join(direntry, 'issue-*.yaml'))
            for filehandle in iterate_files(files):
                yield filehandle
        elif isfile(direntry):
            yield file(direntry)
        else:
            raise TypeError('%r is not a file nor a directory' % direntry)

def report_progress_times(filepaths, options):
    """
    Parse each issue file in filepaths (and each issue file inside directories
    in filepaths), calculate total time spent in progress and report totals for
    issues separately with a grand total at the end.
    """
    cum_time = timedelta()
    for filehandle in iterate_files(filepaths):
        issue = yaml.load(filehandle)
        filehandle.close()
        total_time = issue.total_time(earliest=options.after,
                                      latest=options.before)
        if total_time:
            print format_timedelta(total_time), issue.id[:5], issue.title
        cum_time += total_time
    print cum_time


########################################################################
## add timestamp support to OptionParser

def check_timestamp(_, opt, value):
    """
    >>> check_timestamp(None, 'after', '2008-05-06')
    datetime.datetime(2008, 5, 6, 0, 0)
    >>> check_timestamp(None, 'after', '2008-05-06 18')
    datetime.datetime(2008, 5, 6, 18, 0)
    >>> check_timestamp(None, 'after', '2008-05-06_18:45')
    datetime.datetime(2008, 5, 6, 18, 45)
    """
    format = ('%Y-%m-%d'+value[10:11]+'%H:%M')[:len(value)-2]
    try:
        return datetime.strptime(value, format)
    except ValueError:
        raise OptionValueError(
            "option %s: invalid timestamp value: %r" % (opt, value))

class MyOption(Option):
    "Option class for optparse, enhanced with a timestamp option type"
    TYPES = Option.TYPES + ("timestamp",)
    TYPE_CHECKER = copy(Option.TYPE_CHECKER)
    TYPE_CHECKER["timestamp"] = check_timestamp


########################################################################
## parse command line

def parse_cmdline():
    "Parse the command line"
    parser = OptionParser(formatter=TitledHelpFormatter(),
                          option_class=MyOption,
                          usage=globals()['__doc__'],
                          version=VERSION)
    parser.add_option('-u', '--unittest', action='store_true')
    parser.add_option('-v', '--verbose' , action='count')
    parser.add_option('-a', '--after' , action='store', type='timestamp')
    parser.add_option('-b', '--before' , action='store', type='timestamp')
    return parser.parse_args()

def set_loglevel(verbosity):
    """
    Set the Python logging level according to the verbosity setting from the
    command line.
    """
    loglevel = 40 - 10*(min(3, verbosity or 0))
    logging.basicConfig(level=loglevel, format='%(levelname)-8s %(message)s')

def main():
    "Main program"
    opts, args = parse_cmdline()
    set_loglevel(opts.verbose)
    if opts.unittest:
        from doctest import testmod
        testmod()
    else:
        report_progress_times(args, opts)

if __name__ == '__main__':
    main()
