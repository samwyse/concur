"""\
This implements a command line interpreter (CLI) for the concur API.

OAuth data is kept in a JSON file, for easy portability between different
programming languages.

Currently, the initialization of OAuth requires the user to copy a URL
into a web browser, then copy the URL of the resulting page back to this
script.
"""

copyright = """
Copyright (c) 2013 Sam Denton <samwyse@gmail.com>
All Rights Reserved.

Licensed under the Academic Free License (AFL 3.0)
http://opensource.org/licenses/afl-3.0
"""

from cmd import Cmd as _Cmd
from datetime import datetime
from functools import wraps as _wraps
from pprint import pprint as _pprint
import json as _json
import re

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

try:
    from concur import ConcurClient, ConcurAPIError
except ImportError:
    from sys import path
    from os.path import join, normpath
    # Try looking in the parent of this script's directory.
    path.insert(0, normpath(join(path[0], '..')))
    from concur import ConcurClient, ConcurAPIError
import concur._xml2json as x2j

class dict_re(dict):
    _repl = lambda self, matchobj: self.get(matchobj.group(), '')

    def compile(self, flags=0, pattern=None):
        '''Compile a regular expression consisting of the alternation
of all keys. The 'pattern' optional argument is intended for
"hand-optimized" patterns. This is a separate step to allow the
dictionary to be built incrementally. The return value allows idioms
such as, "x = dict_re(...).compile()"'''
        self.pattern = pattern if pattern else '|'.join(re.escape(key) for key in sorted(self.keys()))
        self._re  = re.compile(self.pattern, flags)
        self.flags = self._re.flags
        return self

    def sub(self, string, count=0):
        '''Return the string obtained by replacing occurrences of
        dictionary keys in string by the corresponding value.'''
        return self._re.sub(self._repl, string, count)

    def subn(self, string, count=0):
        '''Perform the same operation as sub(), but return a tuple
        (new_string, number_of_subs_made).'''
        return self._re.subn(self._repl, string, count)

def mk_parser(*args):
    import argparse
    parser = argparse.ArgumentParser(
        prog='',
        description='',
        add_help=False,
        )
    head_is_string = lambda lst: isinstance(lst[0], basestring)
    args = list(args)
    args.append(None)  # sentinel value
    while args:
        dest = args.pop(0)
        if dest is None:
            break
        flags = {} if head_is_string(args) else args.pop(0)
        if isinstance(dest, basestring):
            dest = (dest,)
        parser.add_argument(*dest, **flags)
    return parser

def _syntax(parser, presplit=True, f=None):
    '''Decorator that accepts an ArgumentParser, then mutates a
function that is accepts a string to instead accept a Namespace.'''
    if f is None:
        from copy import copy
        from functools import partial
        return partial(_syntax, copy(parser), presplit)
    parser.prog = f.func_name[3:]
    parser.description = f.func_doc or 'No description available'
    f.func_doc = parser.format_help()
    @_wraps(f)
    def wrapper(self, line):
        args = line.split() if presplit else [line]
        return f(self, parser.parse_args(args))
    return wrapper

    return decorator

def _get(filename, default):
    from os.path import expanduser
    return expanduser(filename if filename else default)

def _set(name, definition, dict, allow_creation=True):
    '''Helper function to set a value in a hash'''
    def show(item):
        '''Helper function to display a key-value pair'''
        if isinstance(item[1], basestring):
            print '%s: %s' % item

    if name is None:
        for item in sorted(dict.items()):
            show(item)
    elif len(definition) == 0:
        try:
            show((name, dict[name]))
        except KeyError:
            pass
    elif allow_creation or isinstance(dict.get(name), basestring):
        dict[name] = ' '.join(definition)
    else:
        print 'unknown key %r' % parsed[0]

def _unset(names, dict):
    '''Helper function to remove a value from a hash'''
    for name in names:
        try:
            del dict[name]
        except KeyError:
            pass


fix_dates = dict_re((
    ('YYYY', '%Y'),
    ('YY', '%y'),
    ('MMMM', '%B'),
    ('MMM', '%b'),
    ('MM', '%m'),
    ('DDDD', '%A'),
    ('DDD', '%a'),
    ('DD', '%d'),
    ('HH:MM', '%H:%M'),
    ('HH:MM:SS', '%H:%M:%S'),
    )).compile(pattern='YY(?:YY)?|M{2,4}|D{2,4}|HH\:MM(?:\:SS)?')
no_args = mk_parser()
filename = mk_parser('filename', {'nargs':'?'})
value = mk_parser('value', {'nargs':'?'})
define = mk_parser('name', {'nargs':'?'}, 'definition', {'nargs':'*'})
undefine = mk_parser('names', {'nargs':'+'})
key_value = lambda x: x.split('=', 1)  # turn 'foo=bar' into ('foo', 'bar')
http_request = mk_parser('path', {'nargs':'+'},
                         ('-o', '--options'), {'nargs':'*', 'type': key_value})


class ConcurCmd(_Cmd):

    config_file = '~/.concur_cli.rc'
    oauth_file = '~/concur_oauth.json'

    def __init__(self, config_file=None):
        '''Initializes the interpreter.'''
        self.client = ConcurClient()
        self.aliases = {}
        self.open_files = []
        self.do_load(self.config_file)
        return _Cmd.__init__(self)

    def onecmd(self, line):
        try:
            return _Cmd.onecmd(self, line)
        except ConcurAPIError as error:
            print "%s: %s" % (type(error).__name__, error[0])
            print error[1]
        except Exception as error:
            print "%s: %s" % (type(error).__name__, error)

    def default(self, line):
        '''Handle aliases.'''
        parts = line.split(None, 1)
        if len(parts) > 0 and parts[0] in self.aliases:
            newline = self.aliases[parts[0]]
            if len(parts) > 1:
                newline += ' ' + parts[1]
            return self.onecmd(newline)
        return _Cmd.default(self, line)

    # Simple commands

    @_syntax(no_args)
    def do_quit(self, namespace):
        '''Exits the interpreter.'''
        return True

    @_syntax(no_args)
    def do_copyright(self, namespace):
        '''Displays copyright and licensing information.'''
        print copyright

    @_syntax(no_args)
    def do_examples(self, namespace):
        '''Displays example commands.'''
        print '''\
These are some commands to try.
\tget expense expensereport v2.0 Reports -o status=ACTIVE
\tget expense expensereport v2.0 Reports -o ReportCurrency=USD
\tget expense expensereport v2.0 report 9A529938A4E44F6C8652 -o'''

    @_syntax(value, presplit=False)
    def do_note(self, namespace):
        '''Comment.'''
        pass

    @_syntax(value, presplit=False)
    def do_echo(self, namespace):
        '''Displays information to the user.'''
        print namespace.value

    # Commands related to aliases.

    @_syntax(define)
    def do_alias(self, namespace):
        '''Manage aliases.'''
        _set(namespace.name, namespace.definition, self.aliases)

    @_syntax(undefine)
    def do_unalias(self, namespace):
        '''Delete aliases.'''
        _unset(namespace.names, self.aliases)

    @_syntax(filename, presplit=False)
    def do_save(self, namespace):
        '''Save the current configuration as a list of commands.'''
        config_file = _get(namespace.filename, self.config_file)
        with open(config_file, 'w') as config:
            for item in self.aliases.items():
                print >>config, 'alias %s %s' % item
        #print >>config, 'oload %s' % self.oauth_file  # TODO

    @_syntax(filename, presplit=False)
    def do_load(self, namespace):
        '''Run commands from a file.'''
        from os.path import exists, expanduser, join
        config_file = _get(namespace.filename, self.config_file)
        if config_file in self.open_files:
            print 'already processing %s' % config_file
            return
        if exists(config_file):
            self.open_files.append(config_file)
            with open(config_file, 'r') as config:
                for line in config:
                    self.onecmd(line)
            self.open_files.pop()

    # Commands related to OAuth.

    @_syntax(value, presplit=False)
    def do_client_id(self, namespace):
        '''Displays or sets the value.'''
        if namespace.value:
            self.client.client_id = namespace.value
        elif self.client.client_id:
            print 'client_id =', self.client.client_id
        else:
            print 'The client id is not set.'

    @_syntax(value, presplit=False)
    def do_client_secret(self, namespace):
        '''Displays or sets the value.'''
        if namespace.value:
            self.client.client_secret = namespace.value
        elif self.client.client_secret:
            print 'client_secret =', self.client.client_secret
        else:
            print 'The client secret is not set.'

    @_syntax(value, presplit=False)
    def do_access_token(self, namespace):
        '''Displays or sets the value.'''
        from urlparse import urlparse, parse_qs
        client = self.client
        if namespace.value:
            parts = urlparse(namespace.value)
            code = parse_qs(parts.query)['code'][0]
            client.access_token = client.get_oauth_token(code)
        elif client.access_token:
            print 'access_token =', client.access_token
        else:
            print 'The access token is not set.'
            print 'Enter the URL below in a web browser and follow the instructions.'
            print ' ', client.build_oauth_url()
            print 'Once the web browser redirects, copy the complete URL and'
            print 'use it to re-run this command.'

    @_syntax(filename, presplit=False)
    def do_osave(self, namespace):
        '''Saves OAuth information into a JSON file.'''
        oauth_file = _get(namespace.filename, self.oauth_file)
        with open(oauth_file, 'w') as fp:
            _json.dump(self.client.__dict__, fp)

    @_syntax(filename, presplit=False)
    def do_oload(self, namespace):
        '''Loads OAuth information from a JSON file.'''
        from os.path import exists, expanduser, join
        oauth_file = _get(namespace.filename, self.oauth_file)
        if exists(oauth_file):
            with open(oauth_file, 'r') as fp:
                self.client.__dict__.update(_json.load(fp))

    # Commands related to the REST API.

    @_syntax(http_request)
    def do_get(self, namespace):
        '''Issues an HTTP GET request'''
        _pprint(self.client.get('/'.join(namespace.path), **dict(namespace.options)))

    @_syntax(http_request)
    def do_post(self, namespace):
        '''Issues an HTTP POST request'''
        _pprint(self.client.post('/'.join(namespace.path))) #, **namespace.options))

    @_syntax(no_args)
    def do_create_report(self, namespace):
        '''Creates a new expense report'''
        data = {
            'Name': 'MMMM Expenses',  # ReportName
            'Purpose': 'All expenses for MMM, YYYY',
            'Comment': 'Includes Client Meetings.',  # LastComment (in summary)
            'UserDefinedDate': 'YYYY-MM-DD HH:MM:SS.0',  # ReportDate
            }
        now = datetime.now()
        new_report = {'Report': dict((k, now.strftime(fix_dates.sub(v))) for k, v in data.items())}
        canonization = x2j.UsingPrefix(default_namespace='http://www.concursolutions.com/api/expense/expensereport/2011/03')
        elem = x2j.internal_to_elem(new_report, canonize=canonization)
        from xml.etree.ElementTree import ElementTree
        if not isinstance(elem, ElementTree):
            elem = ElementTree(elem)
        buffer = StringIO()
        elem.write(buffer)
        _pprint(self.client.post_raw('expense/expensereport/v1.1/Report',
                                     content_type='application/xml',
                                     data=buffer.getvalue()))


def main(argv=None):
    if argv is None:
        import sys
        argv = sys.argv[1:]
    ConcurCmd().cmdloop()

if __name__ == '__main__':
    main()
