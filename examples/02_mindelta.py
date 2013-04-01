#!/usr/bin/env python

import cherrypy
from spamprotector import IPProtector
cherrypy.tools.protect_high_frequency = IPProtector(mindt_seconds=0.5, interval_reqs=None)
cherrypy.tools.protect_strictly = IPProtector(mindt_seconds=2.0, interval_reqs=None)


class MyView(object):
    @cherrypy.expose
    @cherrypy.tools.protect_high_frequency()
    def index(self):
        return "Don't hammer me too much plz. Also, <a href={}>other is sensitive</a>.".format(cherrypy.url("other"))

    @cherrypy.expose
    @cherrypy.tools.protect_strictly()
    def other(self):
        return "You man not access me often! Same goes for <a href={}>that dude</a>.".format(cherrypy.url("dude"))

    @cherrypy.expose
    @cherrypy.tools.protect_strictly()
    def dude(self):
        return "Hi there."

cherrypy.quickstart(MyView())
