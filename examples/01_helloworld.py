#!/usr/bin/env python

import cherrypy
from spamprotector import IPProtector
cherrypy.tools.protect = IPProtector()


class HelloWorld(object):
    @cherrypy.expose
    @cherrypy.tools.protect()
    def index(self):
        return "<h1>Hello, World!</h1>"

cherrypy.quickstart(HelloWorld())
