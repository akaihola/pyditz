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
