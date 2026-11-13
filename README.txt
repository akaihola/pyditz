===============================================
 PyDitz -- Ditz issue tracking tools in Python
===============================================

Ditz is a simple, light-weight distributed issue tracker designed to
work with distributed version control systems.  For more information,
see http://ditz.rubyforge.org/

PyDitz is a project which implements Ditz compatible functionality in
the Python language.  PyDitz was originally written by Antti Kaihola
<akaihol plus-sign ditz at-sign ambitone dot com>.

The pyditz.py script produces a report on work hours spent on selected
or all Ditz issues in a project.  It shows both totals as well as
daily and weekly hours. You can also exclude hours before and/or after
given timestamps. The name of the script is a bit off since I plan to
add more functionality.

This functionality would preferably be included in Ditz itself or a
plugin for it.  The Python implementation came about since the author
had an immediate need for work log reporting and Python is his first
language of choice.

A shortcoming in using Ditz for work log tracking is that the model it
uses doesn't work when multiple people might work on the same issue and
their work hours could overlap. The status is defined per issue, not
per issue/person.


Update 2026-11-13
=================

PyDitz hasn't been developed since February 2009, apart from the fixes
below.  The last Ditz release is 0.5 from August 2008, and the address
above stopped working when RubyForge closed.  The Ditz source is still
available as a gem at https://rubygems.org/gems/ditz.

pyditz.py is Python 2 code.  It still runs on Python 2.7 with PyYAML
3.13, and ``pyditz.py -u`` runs its doctests.  Running it on the Ditz
issues of the Sup mail client revealed bugs which are now fixed (see
ChangeLog.txt): unknown log messages stopped the report, every work
session crossing the 4am day boundary got four extra hours, and
minutes could be rounded up to 60.

If you're looking for an issue tracker which lives in the repository
like Ditz did, have a look at git-bug
(https://github.com/git-bug/git-bug), Backlog.md
(https://github.com/MrLesk/Backlog.md) or beads
(https://github.com/gastownhall/beads), which is designed for coding
agents.  For keeping a work log, Timewarrior
(https://github.com/GothenburgBitFactory/timewarrior) and Watson
(https://github.com/jazzband/Watson) track hours from the command line.
