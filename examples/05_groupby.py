#!/usr/bin/env python

import cherrypy
from spamprotector import IPProtector
cherrypy.tools.protect = IPProtector()


class MyView(object):
    @cherrypy.expose
    @cherrypy.tools.protect(group_by=lambda: 'most everything')
    def index(self):
        return "I'm not alone: users is fighting spam with me."

    @cherrypy.expose
    @cherrypy.tools.protect(group_by=lambda: 'most everything')
    def users(self):
        return "I'm helping index in his fight on spam."

cherrypy.quickstart(MyView())
