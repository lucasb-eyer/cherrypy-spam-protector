#!/usr/bin/env python
# -*- coding: UTF-8 -*-

"""

Copyright (C) 2013 Lucas Beyer

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

"""
import cherrypy
from copy import deepcopy
from datetime import datetime
from collections import defaultdict, deque


# http://docs.cherrypy.org/dev/progguide/extending/customtools.html?highlight=tools
class IPProtector(cherrypy.Tool):
    """
    Sends a 403 response to IPs trying to spam your app, or parts of it.

    Example usage:
        from spamprotector import IPProtector
        # This one allows short spikes of request, if they then make a pause.
        cherrypy.tools.low_freq_protector = IPProtector(mindt_seconds=None, interval_dt=60.0, interval_reqs=10)
        # This one doesn't allow spikes of requests.
        cherrypy.tools.high_freq_protector = IPProtector(mindt_seconds=2.0, interval_reqs=None)

        class View(object):
            @cherrypy.expose
            @cherrypy.tools.low_freq_protector()
            def index(self):
                # ...
            @cherrypy.expose
            @cherrypy.tools.high_freq_protector(group_by='full')
            def some_request(self):
                # ...

            # Counts all requests from one IP which have the cookie 'something'
            # set to the same value as being the same. Note that this is
            # easily countered by using something like curl or wget on the
            # client-side, which ignores cookies. This is just an example, it's
            # useless in practice.
            @cherrypy.expose
            @cherrypy.tools.high_freq_protector(group_by=lambda: cherrypy.request.cookie['something'])
            def page1(self):
                # ...

            # Requests to this page and page1 above count together! This is
            # because their 'group_by' returns the same string. (Assuming the
            # client sends the same cookies.)
            @cherrypy.expose
            @cherrypy.tools.high_freq_protector(group_by=lambda: cherrypy.request.cookie['something'])
            def page2(self):
                # ...
    """
    def __init__(self, mindt_seconds=1.0, interval_dt=15.0, interval_reqs=5):
        """
        - mindt_seconds is the minimum amount of seconds that has to pass
          between two requests from the same IP. None to disable this check.
        - interval_dt and interval_reqs specify a certain interval of time (in
          seconds) during which at most interval_reqs may come from the same IP.
          Set interval_reqs to None in order to disable this check.
        """
        # Handle before_handler because that's the earliest point
        # cherrypy.request.params is set, according to documentation.
        self._point = "before_handler"
        self._name = None
        self._priority = 50

        # These are public by intent: changing them will actually work.
        self.mindt = mindt_seconds
        self.interval_dt = interval_dt
        self.interval_reqs = interval_reqs

        # +1 since we put the current request in there before checking anything.
        self._pastrequests = defaultdict(lambda: defaultdict(lambda: deque(maxlen=(interval_reqs or 1) + 1)))

    def callable(self, method=('GET', 'POST'), group_by='path_info', fail_with=None):
        """
        - method is the (or an iterable of) value(s) of cherrypy.request.method
          which should be handled. All other requests are not protected.
        - group_by specifies what requests are seen as the same and protected
          together:
            - 'path_info': requests with the same request.path_info.
            - 'path_query': requests with the same request.path_info AND
              request.query_string, i.e. the full URI.
            - 'full': like 'path_info' but adding request.params, i.e. the
              full URI and the full GET/POST parameters.
            - any callable: should return a string which is the same for
              requests which should be treated together.
        - fail_with defines what happens when a 'spammer' is detected:
            - any callable: calls fail_with(self) and returns whatever that returns.
            - any instance of (a subclass of) Exception: raises fail_with.
            - anything else: raises a HTTPError(403)
        """
        rq = cherrypy.request
        if rq.method != method and rq.method not in method:
            return

        if callable(group_by):
            rqline = group_by()
        elif group_by == 'path_info':
            rqline = rq.path_info
        elif group_by == 'path_query':
            rqline = rq.path_info + '?' + rq.query_string
        elif group_by == 'full':
            rqline = rq.path_info + '\n' + rq.params
        else:
            raise ValueError('Invalid group_by parameter to SpamIPProtector.callable(): ' + str(group_by))

        same_requests = self._pastrequests[rqline][cherrypy.request.remote.ip]
        now = datetime.now()
        same_requests.append(now)

        # Early opt-out in case this is the first request of this kind by this user.
        if len(same_requests) == 1:
            return

        # Get the time since the most recent request and since the
        # interval-oldest request.
        # If any of these checks have been disabled, -1.
        dt_prev_rq = (now - same_requests[-2]).total_seconds() if self.mindt is not None else -1.0
        dt_oldest_rq = (now - same_requests[0]).total_seconds() if self.interval_reqs is not None else -1.0

        # These are the actual checks for spam, to which we act using fail_with.
        if dt_prev_rq < self.mindt or (self.interval_reqs is not None and dt_oldest_rq < self.interval_dt and len(same_requests) == same_requests.maxlen):
            if callable(fail_with):
                return fail_with(self)
            elif isinstance(fail_with, Exception):
                raise fail_with
            else:
                raise cherrypy.HTTPError(403)
                # raise cherrypy.HTTPError(403, 'dt_prev_rq: ' + str(dt_prev_rq) + ' < self.mindt: ' + str(self.mindt) + ' or (dt_oldest_rq: ' + str(dt_oldest_rq) + ' < self.interval_dt: ' + str(self.interval_dt) + ' and len(same_requests): ' + str(len(same_requests)) + ' == same_requests.maxlen: ' + str(same_requests.maxlen) + ')')

    def get_past_requests(self, of=None, by=None):
        """
        - If both 'of' and 'by' are specified, this returns a deque of the oldest to
          newest 'interval_reqs' requests made of resource 'of' by ip 'by'.
        - If only one of 'of' or 'by' is specified, this returns a dict mapping
          either resources or IPs to such a deque.
        - If none is set, screw you.
        """
        if of:
            requests = self._pastrequests[of]
            if by:
                return deepcopy(requests[by])
            return deepcopy(requests)
        else:
            return {res: deepcopy(reqs) for res, v in self._pastrequests.iteritems() for ip, reqs in v if ip == by}
