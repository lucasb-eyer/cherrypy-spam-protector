#!/usr/bin/env python

import cherrypy
from spamprotector import IPProtector
cherrypy.tools.protect_low_frequency = IPProtector(interval_dt=15.0, interval_reqs=5, mindt_seconds=None)


class MyView(object):
    @cherrypy.expose
    @cherrypy.tools.protect_low_frequency()
    def index(self):
        return "You may hammer me in short bursts."

cherrypy.quickstart(MyView())
