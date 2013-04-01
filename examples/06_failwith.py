#!/usr/bin/env python

import cherrypy
from spamprotector import IPProtector
cherrypy.tools.protect = IPProtector()


def kind_failer(protector):
    info = "You failed because your previous request took place only {dt} seconds ago and your past {interval_reqs} requests took place within the past {interval_time} seconds."
    past_reqs = protector.get_past_requests(of=cherrypy.request.path_info, by=cherrypy.request.remote.ip)

    # Notice how past_reqs[-1] contains the _current_ request and -2 the past.
    info = info.format(dt=(past_reqs[-1] - past_reqs[-2]).total_seconds(),
                       interval_reqs=protector.interval_reqs,
                       interval_time=(past_reqs[-1] - past_reqs[0]).total_seconds())
    raise cherrypy.HTTPError(403, info)


class MyView(object):
    @cherrypy.expose
    @cherrypy.tools.protect(fail_with=kind_failer)
    def index(self):
        return "I tell my spammers all of my secrets."

cherrypy.quickstart(MyView())
