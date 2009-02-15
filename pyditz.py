#!/usr/bin/env python
# -*- coding: utf-8 -*-

VERSION = '0.11'

__doc__ = """
SYNOPSIS

    pyditz.py [-h,--help] [-v,--verbose] [--version] [-u,--unittest]
              [-a,--after] [-b,--before] FILE/DIRECTORY...

DESCRIPTION

    This utility calculates total time spent in progress of given Ditz issues.

EXAMPLES

    $ pyditz.py -a 2008-07-01 .ditz/issue-*.yaml
    $ pyditz.py -b 2008-08-01 .ditz

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
from collections import defaultdict
import logging
import yaml
import re


CLOSE_STATUS = re.compile(r'closed (?:issue )?with disposition (\w+)')
CHANGE_STATUS = re.compile(r'changed status from (unstarted|in_progress|paused|closed) to (in_progress|paused)')
ASSIGN_STATUS = re.compile('assigned to release ')

class Matcher(object):
    def __init__(self, data):
        self.data = data
    def match(self, pattern):
        self.matchobj = pattern.match(self.data)
        return self.matchobj
    def group(self, index):
        return self.matchobj.group(index)

def format_h_m(delta):
    """
    Return a timedelta in a 1h20' style format.

    Last changed: 2008-12-27 11:52+0200

    >>> print format_h_m(timedelta(1, 154))
    24h03'
    >>> print format_h_m(timedelta(0, 3535))
    59'
    """
    hours = 24 * delta.days + delta.seconds // 3600
    minutes = round(delta.seconds % 3600 / 60.0)
    if hours:
        return "%dh%02d'" % (hours, minutes)
    else:
        return "%d'" % minutes

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
    >>> parse_status('assigned to release 0.1 from unassigned')
    (None, None)
    """
    status = Matcher(status)
    if status.match(CLOSE_STATUS):
        return None, status.group(1)
    elif status.match(CHANGE_STATUS):
        return status.group(1), status.group(2)
    elif status.match(ASSIGN_STATUS):
        return None, None
    else:
        raise ValueError('Invalid status change message %r' % status.data)

class TimeDistribution(object):
    """
    Calculate distribution of time intervals into days and ISO weeks.

    Class last changed: 2008-12-17 11:48+0200
    """
    def __init__(self, splithour=4):
        self.splithour = splithour
        self.days = defaultdict(timedelta)
        self.weeks = defaultdict(timedelta)
        self.total = timedelta()

    def _add_to_day(self, day, duration):
        """
        >>> from datetime import date
        >>> t = TimeDistribution()
        >>> t._add_to_day(date(2008, 12, 17), timedelta(0, 7200))
        >>> t.total
        datetime.timedelta(0, 7200)
        >>> dict(t.weeks)
        {(2008, 51): datetime.timedelta(0, 7200)}
        >>> dict(t.days)
        {datetime.date(2008, 12, 17): datetime.timedelta(0, 7200)}
        """
        self.days[day] += duration
        self.weeks[day.isocalendar()[:2]] += duration
        self.total += duration

    def add(self, dtstart, dtend):
        """
        >>> t = TimeDistribution(splithour=4)
        >>> t.add(datetime(2008, 11, 15, 13, 45),  # 13:45-15:15
        ...       datetime(2008, 11, 15, 15, 15))
        >>> t.add(datetime(2008, 12, 15, 3, 45),   # Mon 3:45 - next Tue 5:15
        ...       datetime(2008, 12, 23, 5, 15))
        >>> from pprint import pprint
        >>> pprint(dict(t.days))
        {datetime.date(2008, 11, 15): datetime.timedelta(0, 5400),
         datetime.date(2008, 12, 14): datetime.timedelta(0, 900),
         datetime.date(2008, 12, 15): datetime.timedelta(1),
         datetime.date(2008, 12, 16): datetime.timedelta(1),
         datetime.date(2008, 12, 17): datetime.timedelta(1),
         datetime.date(2008, 12, 18): datetime.timedelta(1),
         datetime.date(2008, 12, 19): datetime.timedelta(1),
         datetime.date(2008, 12, 20): datetime.timedelta(1),
         datetime.date(2008, 12, 21): datetime.timedelta(1),
         datetime.date(2008, 12, 22): datetime.timedelta(1),
         datetime.date(2008, 12, 23): datetime.timedelta(0, 18900)}
        >>> pprint(dict(t.weeks))
        {(2008, 46): datetime.timedelta(0, 5400),
         (2008, 50): datetime.timedelta(0, 900),
         (2008, 51): datetime.timedelta(7),
         (2008, 52): datetime.timedelta(1, 18900)}
        >>> t.total
        datetime.timedelta(8, 25200)
        """
        dstart = (dtstart-timedelta(0, self.splithour*3600)).date()
        dend = (dtend-timedelta(0, self.splithour*3600)).date()
        dstart00h = datetime(*dstart.timetuple()[:3])
        dateline = dstart00h + timedelta(1, self.splithour*3600)
        if dtend > dateline:
            self._add_to_day(dstart, dateline - dtstart)
            for d in range(1, (dend - dstart).days):
                self._add_to_day(dstart + timedelta(d), timedelta(1))
            self._add_to_day(dend, dtend - datetime(*dend.timetuple()[:3]))
        else:
            self._add_to_day(dstart, dtend - dtstart)

    def _str_weeks(self):
        """
        >>> t = TimeDistribution()
        >>> t._str_weeks()
        ''
        >>> t.weeks[2008, 51] = timedelta(2, 189)
        >>> t._str_weeks()
        "2008-51/48h03'"
        """
        return ' '.join('%04d-%02d/%s' % (key[0], key[1],
                                          format_h_m(self.weeks[key]))
                        for key in sorted(self.weeks.keys()))

    def _str_days(self):
        """
        >>> from datetime import date
        >>> t = TimeDistribution()
        >>> t._str_days()
        ''
        >>> t.days[date(2008, 12, 13)] = timedelta(0, 189)
        >>> t._str_days()
        "2008-12-13/3'"
        """
        return ' '.join(
            '%04d-%02d-%02d/%s' % (key.year, key.month, key.day,
                                   format_h_m(self.days[key]))
            for key in sorted(self.days.keys()))

    def __add__(self, other):
        """
        >>> t = TimeDistribution(splithour=4)
        >>> t.add(datetime(2008, 11, 15, 13, 45),  # 13:45-15:15
        ...       datetime(2008, 11, 15, 15, 15))
        >>> from pprint import pprint
        >>> pprint((t.total, dict(t.weeks), dict(t.days)))
        (datetime.timedelta(0, 5400),
         {(2008, 46): datetime.timedelta(0, 5400)},
         {datetime.date(2008, 11, 15): datetime.timedelta(0, 5400)})
        """
        result = self.__class__()
        for attname in 'days', 'weeks':
            mydict = getattr(self, attname)
            otherdict = getattr(other, attname)
            mykeys = set(mydict.keys())
            otherkeys = set(otherdict.keys())
            for key in mykeys.union(otherkeys):
                getattr(result, attname)[key] += mydict[key] + otherdict[key]
        result.total = self.total + other.total
        return result

    def __nonzero__(self):
        """
        >>> bool(TimeDistribution(splithour=4))
        False
        >>> t = TimeDistribution(splithour=4)
        >>> t.total = timedelta(0, 60)
        >>> bool(t)
        True
        """
        return self.total > timedelta()

    def __repr__(self):
        """
        >>> from datetime import date
        >>> t = TimeDistribution(splithour=4)
        >>> t.weeks[2008, 46] = timedelta(0, 5400)
        >>> t.days[date(2008, 11, 15)] = timedelta(0, 5400)
        >>> t.total = timedelta(0, 5400)
        >>> t
        <TimeDistribution 1h30' 2008-46/1h30' 2008-11-15/1h30'>
        """
        return '<TimeDistribution %s %s %s>' % (
            format_h_m(self.total), self._str_weeks(), self._str_days())

    def report_txt(self):
        r"""
        >>> t = TimeDistribution()
        >>> t.add(datetime(2008, 12, 29, 1),
        ...       datetime(2009,  1,  5, 5))
        >>> print '\n'.join(t.report_txt())
        2008 52   3h00' 2008-12-28   3h00'
        2009 01 168h00' 2008-12-29  24h00'
                        2008-12-30  24h00'
                        2008-12-31  24h00'
                        2009-01-01  24h00'
                        2009-01-02  24h00'
                        2009-01-03  24h00'
                        2009-01-04  24h00'
             02   5h00' 2009-01-05   5h00'
        total   176h00'
        """
        last_year = last_week = None
        for day in sorted(self.days.keys()):
            year, week = day.isocalendar()[:2]
            print_year = '    '
            print_week = (2+1+7)*' '
            if year != last_year:
                print_year = '%04d' % year
                last_year = year
                last_week = None
            if week != last_week:
                print_week = '%02d %7s' % (week,
                                           format_h_m(self.weeks[year, week]))
                last_week = week
            yield '%s %s %04d-%02d-%02d %7s' % (
                print_year, print_week, day.year, day.month, day.day,
                format_h_m(self.days[day]))
        yield 'total %9s' % format_h_m(self.total)

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
        <TimeDistribution 3h00' 2008-25/1h00' 2008-41/2h00' 2008-06-16/1h00' 2008-10-06/2h00'>

        >>> from datetime import datetime
        >>> i.total_time(earliest=datetime(2008,9,1))
        <TimeDistribution 2h00' 2008-41/2h00' 2008-10-06/2h00'>
        >>> i.total_time(latest=datetime(2008,9,1))
        <TimeDistribution 1h00' 2008-25/1h00' 2008-06-16/1h00'>
        """

        def filtered(timestamp):
            """Return True if timestamp is earlier or later than those
            specified in the arguments of the wrapping function."""
            if earliest is not None and timestamp < earliest:
                return True
            if latest is not None and timestamp > latest:
                return True
            return False

        cum_time = TimeDistribution()
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
                    cum_time.add(dtstart, timestamp)
                    dtstart = None
            elif status_to is not None:
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
    cum_time = TimeDistribution()
    for filehandle in iterate_files(filepaths):
        issue = yaml.load(filehandle)
        filehandle.close()
        issue_time = issue.total_time(earliest=options.after,
                                      latest=options.before)
        if issue_time:
            print format_timedelta(issue_time.total), issue.id[:5], issue.title
        cum_time += issue_time
    print '\n'.join(cum_time.report_txt())


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
