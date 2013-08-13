concur
======

Python API Client for Concur (http://concur.com/).

concur
=====

This is a Python client library for the [Concur App](http://www.concur-app.com/).

Requirements
------------

* [Requests](http://docs.python-requests.org/en/latest/)

Installation
------------

Install via pip:

    pip install concur

Usage
-----

See `examples/oauth.py` for some basic examples.

You can request API endpoints like so:

    concur.api('/user/profile', 'GET', params={'access_token': access_token})

Or

    concur.get('/user/profile', params={'access_token': access_token})

Or just

    concur.user_profile(access_token=access_token)

For endpoints that require RESTful parameters in the URL, such as `/user/summary/daily/<YYYYMMDD>`

    concur.user_summary_daily('20130605', access_token=access_token)

All responses are decoded JSON objects.

Consult the [API documentation](https://developer.concur.com/api-documentation) for the methods supported.

Disclaimer
----------

This library uses data from Concur but is not endorsed or certified by Concur. Concur is a trademark of Concur Technologies, Inc.
