cherrypy-spam-protector
=======================

A cherrypy tool that protects you from spam.
It does so by sending a 403 HTTP response to those IPs trying to spam your app, or parts of it.

Getting started
===============

Just drop this file into your project and import it. Don't worry, it's MIT licensed.

Usage
=====

The simplest way to use the protector is to decorate your page handler with an instance of it.
A simple hello-world example would look like this:

```python
import cherrypy
from spamprotector import IPProtector
cherrypy.tools.protect = IPProtector()

class HelloWorld(object):
    @cherrypy.expose
    @cherrypy.tools.protect()
    def index(self):
        return "<h1>Hello, World!</h1>"

cherrypy.quickstart(HelloWorld())
```

Don't forget the parentheses at the end of the decorator.

How it works
------------

The tool keeps track of the exact times of the past X requests by IP *and* by resource.
If the same IP makes too many requests of the same resource in too little time, the tool
automatically retaliates by sending a 403 HTTP response.

Almost all of the aspects in this mechanism are configurable, as we'll cover in the following.

What is considered spam and what isn't?
---------------------------------------

There is no correct, generic answer to this question.
"More requests from the same source as a human would realistically request" doesn't cut it,
since you probably don't want to deny access to search engine robots either.

If your application respects the REST convention, especially the [difference
between GET and PUSH](http://stackoverflow.com/a/3477374/766432),
you'll probably *not* protect calls to GET.

The other important aspect defining spam is time.
Any request that follows the preceding request for the same resource in too small a time interval is considered spam.
In addition to that, too many requests being made in a certain interval can be considered spam too.

Choosing time intervals
-----------------------

This tool lets you configure both of the above time measures of detecting spam.
This configuration happens at the tool's creation time.

### Setting a minimum time delta
This setting protects you from a burst of requests to the same resource.

```python
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
```

(Ignore the `interval_reqs=None` parameter for now, we'll cover it later.)

The first protector, which protects the index page, will respond with a 403 error only if
the same IP requests the index more than two times in a second.
The second protector, which protects both `other` and `dude`, will ring the alarm bell as
soon as the same IP requests one of these pages more than once in two seconds.

Setting the `mindt_seconds` option to `None` completely disables this kind of protection.
The default value for this setting is `1.0` seconds.

It is important to understand that it is OK to access both `other` and `dude` within less
than two seconds; they are protected independently, because they are two distinct requests.

### Allowing for short bursts
If you do want to allow short bursts of action, but want the average over a certain interval of time
to not surpass a threshold, you can build the protector using the 'interval' settings as follows:

```python
from spamprotector import IPProtector
cherrypy.tools.protect_low_frequency = IPProtector(interval_dt=15.0, interval_reqs=5, mindt_seconds=None)
```

This ensures that whatever request is protected by this protector is never requested more than
five times in 15 seconds. Whether these five times occur within the frame of half a second or
the full 15 seconds doesn't matter.

Notice that we had to disable the `mindt_seconds` setting as it would have stopped the bursts
regardless hadn't we disabled it.

Setting the `interval_reqs` parameter to `None` completely disables this kind of protection.
The default values for these settings are `interval_dt=15.0` and `interval_reqs=5`.

Protecting only a certain kind of requests
------------------------------------------

You can choose what kind of requests (`POST`, `GET`, `PUT`, ...) to protect on a per-resource
basis. This works as follows:

```python
from spamprotector import IPProtector
cherrypy.tools.protect = IPProtector()

class MyView(object):
    @cherrypy.expose
    @cherrypy.tools.protect(method='POST')
    def index(self):
        # ...

    @cherrypy.expose
    @cherrypy.tools.protect(method=('POST', 'PUT'))
    def users(self):
        # GET, POST, PUT, DELETE users
```

In this example, the `index` is only protected from a spam of `POST` requests,
all others (especially `GET` requests) are unaffected by the tool.
The `users` is protected from both `POST` and `PUT` requests, but unprotected
from any other requests.

By default, `method` is `('GET', 'POST')` and thus protects only from `GET` and
`POST` spam. There is no wildcard-like value which protects everything.

Protecting multiple resources
-----------------------------

The `group_by` parameter specifies maps a request to a resource.
Protection works on resources and thus, if two requests are mapped to the same resource, these
requests are counted together. The following example should clarify this:

```python
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
```

In this example, access to both `index` and `users` are counted together, because the callable
`group_by` returns the same value for them. Thus, if the same IP requests `index` first and
`users` 100ms later, it will receive a 403 response for `users`.

`group_by` can be any callable that returns a hashable, usually a string. Since some mappings
are very common, `group_by` can also be any of the following strings:

- `path_info` maps a request to its corresponding [cherrypy.request.path_info](http://docs.cherrypy.org/stable/refman/_cprequest.html#cherrypy._cprequest.Request.path_info)
- `path_query` maps a request to a combination of the `path_info` above and the request's [cherrypy.request.query_string](http://docs.cherrypy.org/stable/refman/_cprequest.html#cherrypy._cprequest.Request.query_string).
  This almost corresponds to the full URI of the request.
- `full` maps a request to a combination of the `path_info` and all `GET`/`POST` parameters.
  This is very specialized and only protects from a spammer spamming almost identical requests.

The default value is `path_info`.
This implies that you can safely protect two different page handlers using the same protector
without them getting in eachother's way.

I got spammed. What now??
-------------------------

By default, this tool sends a 403 answer as soon as it detects spam
(It does so through a `raise HTTPError(403)`.), but this too is customizable.

The `fail_with` parameter is a callable which will be called as soon as spam is detected.
It has to take one parameter, which is the instance of the detector. It could then use
that instance's `get_past_requests` method to further investigate, or raise an exception,
or do whatever else you see fit. The return value of that callable is in turn returned.

Since raising exceptions is such a common task but cannot be done within a lambda, `fail_with`
may also be an instance of (a subclass of) `Exception`, in which case it is raised.

By default, `fail_with` is `None`, which entails raising a `HTTPError(403)`.

### Inspecting the past requests

The `get_past_requests(of, by)` method allows further inspection of the current state of requests.
Note that it only returns a snapshot (deep copy) of the state of requests when called.

What is returned depends on the parameters given:

- If both `of` and `by` are specified, it returns a deque of the past `interval_reqs` requests
  made of resource `of` by IP `by`, ordered from oldest to newest.
- If only one of `of` or `by` is specified, it returns a dict mapping either resources
  (as returned by `group_by`, strings by default) or IPs to such a deque, respectively.
- If none is specified, well, screw you. (It returns something falsy, None for now.)

### fail\_with example

```python
from spamprotector import IPProtector
cherrypy.tools.protect = IPProtector()


def kind_failer(protector):
    info = "You failed because your previous request took place only {dt} seconds ago and your past {interval_reqs} requests took place within the past {interval_time} seconds."
    past_reqs = protector.get_past_requests(of=cherrypy.request.path_info, by=cherrypy.request.remote.ip)
    info = info.format(dt=(past_reqs[-1] - past_reqs[-2]).total_seconds(),
                       interval_reqs=protector.interval_reqs,
                       interval_time=(past_reqs[-1] - past_reqs[0]).total_seconds())
    raise cherrypy.HTTPError(403, info)


class MyView(object):
    @cherrypy.expose
    @cherrypy.tools.protect(fail_with=kind_failer)
    def index(self):
        return "I tell my spammers all of my secrets."
```

Notice how `past_reqs[-1]` contains the _current_ request and `past_reqs[-2]` the past.

License: MIT
============

Copyright (C) 2013 Lucas Beyer

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

