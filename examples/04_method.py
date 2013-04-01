#!/usr/bin/env python

import cherrypy
from spamprotector import IPProtector
cherrypy.tools.protect = IPProtector()


class MyView(object):
    @cherrypy.expose
    @cherrypy.tools.protect(method='POST')
    def index(self):
        return "I'm only protected from POST spams."

    @cherrypy.expose
    @cherrypy.tools.protect(method=('POST', 'PUT'))
    def other(self):
        return "But I'm protected from both POST and PUT spams."

cherrypy.quickstart(MyView())
