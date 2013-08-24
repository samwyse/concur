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

from argparse import ArgumentParser
from cmd import Cmd as _Cmd
from datetime import datetime
from functools import wraps as _wraps
from pprint import pprint as _pprint
import json as _json
import re

from ValidateElements import *

try:
    from concur import ConcurClient, ConcurAPIError
except ImportError:
    from sys import path
    from os.path import join, normpath
    # Try looking in the parent of this script's directory.
    path.insert(0, normpath(join(path[0], '..')))
    from concur import ConcurClient, ConcurAPIError
import concur._xml2json as x2j

def mk_parser(*args):
    parser = ArgumentParser(
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

def _syntax(parser, dont_split=False, f=None):
    '''Decorator that accepts an ArgumentParser, then mutates a
function that is accepts a string to instead accept a Namespace.'''
    if f is None:
        from copy import copy
        from functools import partial
        return partial(_syntax, copy(parser), dont_split)
    parser.prog = f.func_name[3:]
    parser.description = f.func_doc or 'No description available'
    f.func_doc = parser.format_help()
    @_wraps(f)
    def wrapper(self, line):
        args = [line] if dont_split else line.split()
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

no_args = mk_parser()
filename = mk_parser('filename', {'nargs':'?'})
value = mk_parser('value', {'nargs':'?'})
define = mk_parser('name', {'nargs':'?'}, 'definition', {'nargs':'*'})
undefine = mk_parser('names', {'nargs':'+'})
key_value = lambda x: x.split('=', 1)  # turn 'foo=bar' into ('foo', 'bar')
http_request = mk_parser('path', {'nargs':'+'},
                         ('-o', '--options'), {'nargs':'*', 'type': key_value, 'default': ()})
options = mk_parser('options', {'nargs':'*', 'type': key_value, 'default': ()})



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
            import traceback
            traceback.print_exc()
            

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
\tget_Forms
\tget_Forms FormCode=RPTINFO
\tget_Fields FormId=n5oqVNsQ$soy2ftQuy$sU9oHBDNCFPyPQr9
\tcreate_report Name=MMMM+Expenses Purpose=All+expenses+for+MMM,+YYYY Comment=Includes+Client+Meetings. UserDefinedDate=YYYY-MM-DD+HH:MM:SS.0
\tget expense expensereport v2.0 Reports -o status=ACTIVE ReportCurrency=USD
\tget expense expensereport v2.0 report <ReportID>'''

    @_syntax(value, dont_split=True)
    def do_note(self, namespace):
        '''Comment.'''
        pass

    @_syntax(value, dont_split=True)
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

    @_syntax(filename, dont_split=True)
    def do_save(self, namespace):
        '''Save the current configuration as a list of commands.'''
        config_file = _get(namespace.filename, self.config_file)
        with open(config_file, 'w') as config:
            for item in self.aliases.items():
                print >>config, 'alias %s %s' % item
        #print >>config, 'oload %s' % self.oauth_file  # TODO

    @_syntax(filename, dont_split=True)
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

    @_syntax(value, dont_split=True)
    def do_client_id(self, namespace):
        '''Displays or sets the value.'''
        if namespace.value:
            self.client.client_id = namespace.value
        elif self.client.client_id:
            print 'client_id =', self.client.client_id
        else:
            print 'The client id is not set.'

    @_syntax(value, dont_split=True)
    def do_client_secret(self, namespace):
        '''Displays or sets the value.'''
        if namespace.value:
            self.client.client_secret = namespace.value
        elif self.client.client_secret:
            print 'client_secret =', self.client.client_secret
        else:
            print 'The client secret is not set.'

    @_syntax(value, dont_split=True)
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

    @_syntax(filename, dont_split=True)
    def do_osave(self, namespace):
        '''Saves OAuth information into a JSON file.'''
        oauth_file = _get(namespace.filename, self.oauth_file)
        with open(oauth_file, 'w') as fp:
            _json.dump(self.client.__dict__, fp)

    @_syntax(filename, dont_split=True)
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

    # Commands specific to Concur.

    @_syntax(options)
    def do_create_report(self, namespace):
        '''Creates a new expense report'''
        _pprint(self.client.post(
            'expense/expensereport/v1.1/Report',
            Report=validate_report_elements(namespace.options),
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',
            ))

    @_syntax(options)
    def do_quickexpense(self, namespace):
        '''Creates a new quick expense'''
        _pprint(self.client.post(
            'expense/expensereport/v1.0/quickexpense/',
            Report=validate_quickexpense_elements(namespace.options),
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2010/09',
            ))

    # See also: https://developer.concur.com/api-documentation/draft-documentation/attendee-resource-draft/attendee-resource-get-draft

    @_syntax(options)
    def do_get_attendees_by_id(self, namespace):
        '''Get attendees_by_id'''  # TODO
        options = validate_attendees_by_id(namespace.options)
        _pprint(self.client.get(
            'expense/v2.0/attendees/{attendees id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/draft-documentation/e-receipt-service-developer-preview/e-receipt-or-e-invoice-res

    @_syntax(options)
    def do_get_e_receiptandinvoice_by_id(self, namespace):
        '''Get e-receiptandinvoice_by_id'''  # TODO
        options = validate_e_receiptandinvoice_by_id(namespace.options)
        _pprint(self.client.get(
            'e-receiptandinvoice/v1.0/{e-receiptandinvoice id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/company-card-transaction-0

    @_syntax(options)
    def do_get_CardCharges(self, namespace):
        '''Get CardCharges'''  # TODO
        options = validate_CardCharges(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/CardCharges' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-delegator-resour-0

    @_syntax(options)
    def do_get_Delegators(self, namespace):
        '''Get Delegators'''  # TODO
        options = validate_Delegators(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/Delegators' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-attendee-r-0

    @_syntax(options)
    def do_get_Attendees(self, namespace):
        '''Get Attendees'''  # TODO
        options = validate_Attendees(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/report/{report id}/entry/{entry id}/Attendees' % options,
            ))

    @_syntax(options)
    def do_get_Attendees_by_id(self, namespace):
        '''Get Attendees_by_id'''  # TODO
        options = validate_Attendees_by_id(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/report/{report id}/entry/{entry id}/Attendees/{Attendees id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-attendee-r-1

    @_syntax(options)
    def do_post_Attendees(self, namespace):
        '''Post Attendees'''  # TODO
        options = validate_Attendees(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/report/{report id}/entry/{entry id}/Attendees' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_Attendees_1(self, namespace):
        '''Post Attendees_1'''  # TODO
        options = validate_Attendees_1(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/report/{report id}/entry/{entry id}/Attendees' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-itemizatio-0

    @_syntax(options)
    def do_post_Itemization(self, namespace):
        '''Post Itemization'''  # TODO
        options = validate_Itemization(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/report/{report id}/entry/{entry id}/Itemization' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-entry-resource/exp

    @_syntax(options)
    def do_get_entry_by_id(self, namespace):
        '''Get entry_by_id'''  # TODO
        options = validate_entry_by_id(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/report/{report id}/entry/{entry id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/expense-report-web-service-new-format/expense-report-header-re-0

    @_syntax(options)
    def do_post_report(self, namespace):
        '''Post report'''  # TODO
        options = validate_report(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/api/expense/expensereport/v1.1/report' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_batch(self, namespace):
        '''Post batch'''  # TODO
        options = validate_batch(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/api/expense/expensereport/v1.1/report/batch' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/travel-profile-web-service-new-format/form-payment-resource/form

    @_syntax(options)
    def do_get_fop(self, namespace):
        '''Get fop'''  # TODO
        options = validate_fop(namespace.options)
        _pprint(self.client.get(
            'travelprofile/v1.0/fop' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/new-portal-format/travel-profile-web-service-new-format/loyalty-program-resource/l

    @_syntax(options)
    def do_post_loyalty(self, namespace):
        '''Post loyalty'''  # TODO
        options = validate_loyalty(namespace.options)
        _pprint(self.client.post(
            'travelprofile/v1.0/loyalty' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_loyalty_1(self, namespace):
        '''Post loyalty_1'''  # TODO
        options = validate_loyalty_1(namespace.options)
        _pprint(self.client.post(
            'travelprofile/v1.0/loyalty' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/oauth-20-0

    @_syntax(options)
    def do_get_User(self, namespace):
        '''Get User'''  # TODO
        options = validate_User(namespace.options)
        _pprint(self.client.get(
            'user/v1.0/User' % options,
            ))

    @_syntax(options)
    def do_get_User_1(self, namespace):
        '''Get User_1'''  # TODO
        options = validate_User_1(namespace.options)
        _pprint(self.client.get(
            'user/v1.0/User' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/attendee/attendee-resource/attendee-resource-get

    @_syntax(options)
    def do_get_attendees_by_id_1(self, namespace):
        '''Get attendees_by_id_1'''  # TODO
        options = validate_attendees_by_id_1(namespace.options)
        _pprint(self.client.get(
            'expense/v2.0/attendees/{attendees id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/attendee-list/attendee-type-resource/attendee-type-resource-get

    @_syntax(options)
    def do_get_type(self, namespace):
        '''Get type'''  # TODO
        options = validate_type(namespace.options)
        _pprint(self.client.get(
            'expense/attendee/v1.0/type' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-entry-attendee-resource/v20-expense-entry-atte

    @_syntax(options)
    def do_get_attendees(self, namespace):
        '''Get attendees'''  # TODO
        options = validate_attendees(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/report/{report id}/entry/{entry id}/attendees' % options,
            ))

    @_syntax(options)
    def do_get_Attendees_1(self, namespace):
        '''Get Attendees_1'''  # TODO
        options = validate_Attendees_1(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/report/{report id}/entry/{entry id}/Attendees' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-entry-resource/expense-entry-resource-post

    @_syntax(options)
    def do_post_entry(self, namespace):
        '''Post entry'''  # TODO
        options = validate_entry(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/report/{report id}/entry' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-form-field-resource/expense-form-field-resourc

    @_syntax(options)
    def do_get_Fields(self, namespace):
        '''Retrieves the details of the configured form fields for the specified form'''
        options = validate_Fields(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/report/Form/%(FormId)s/Fields' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-form-resource/expense-form-resource-get

    @_syntax(options)
    def do_get_Forms(self, namespace):
        '''Retrieves the list of configured form types or the configured forms for the specified form type'''
        options = validate_Forms(namespace.options)
        options.setdefault('FormCode', '')
        _pprint(self.client.get(
            'expense/expensereport/v1.1/report/Forms/%(FormCode)s' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-group-configuration-resource/expense-group-con

    @_syntax(options)
    def do_get_expensereport_by_id(self, namespace):
        '''Get expensereport_by_id'''  # TODO
        options = validate_expensereport_by_id(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/{expensereport id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-report-resource/expense-report-resource-get

    @_syntax(options)
    def do_get_Reports(self, namespace):
        '''Get Reports'''  # TODO
        options = validate_Reports(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_1(self, namespace):
        '''Get Reports_1'''  # TODO
        options = validate_Reports_1(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_2(self, namespace):
        '''Get Reports_2'''  # TODO
        options = validate_Reports_2(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_3(self, namespace):
        '''Get Reports_3'''  # TODO
        options = validate_Reports_3(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_4(self, namespace):
        '''Get Reports_4'''  # TODO
        options = validate_Reports_4(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_5(self, namespace):
        '''Get Reports_5'''  # TODO
        options = validate_Reports_5(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_6(self, namespace):
        '''Get Reports_6'''  # TODO
        options = validate_Reports_6(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_7(self, namespace):
        '''Get Reports_7'''  # TODO
        options = validate_Reports_7(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_Reports_8(self, namespace):
        '''Get Reports_8'''  # TODO
        options = validate_Reports_8(namespace.options)
        _pprint(self.client.get(
            'expense/expenserepo/v2.0/Reports' % options,
            ))

    @_syntax(options)
    def do_get_report_by_id(self, namespace):
        '''Get report_by_id'''  # TODO
        options = validate_report_by_id(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v2.0/report/{report id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/expense-report-resource/expense-report-resource-post

    @_syntax(options)
    def do_post_Exceptions(self, namespace):
        '''Post Exceptions'''  # TODO
        options = validate_Exceptions(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/report/{report id}/Exceptions' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_submit(self, namespace):
        '''Post submit'''  # TODO
        options = validate_submit(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/report/{report id}/submit' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_workflowaction(self, namespace):
        '''Post workflowaction'''  # TODO
        options = validate_workflowaction(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.1/report/{report id}/workflowaction' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/integration-status-resource/integration-status-resourc

    @_syntax(options)
    def do_post_report_by_id(self, namespace):
        '''Post report_by_id'''  # TODO
        options = validate_report_by_id(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v2.0/integrationstatus/report/{report id}' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/expense-report/location-resource/location-resource-get

    @_syntax(options)
    def do_get_expensereport_by_id_1(self, namespace):
        '''Get expensereport_by_id_1'''  # TODO
        options = validate_expensereport_by_id_1(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.1/{expensereport id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/extract/extract-definition-resource/extract-definition-resource-get

    @_syntax(options)
    def do_get_v10(self, namespace):
        '''Get v1.0'''  # TODO
        options = validate_v10(namespace.options)
        _pprint(self.client.get(
            'expense/extract/v1.0' % options,
            ))

    @_syntax(options)
    def do_get_extract_by_id(self, namespace):
        '''Get extract_by_id'''  # TODO
        options = validate_extract_by_id(namespace.options)
        _pprint(self.client.get(
            'expense/extract/v1.0/{extract id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/extract/extract-file-resource/extract-file-resource-get

    @_syntax(options)
    def do_get_file(self, namespace):
        '''Get file'''  # TODO
        options = validate_file(namespace.options)
        _pprint(self.client.get(
            'expense/extract/v1.0/{extract id}/job/{job id}/file' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/extract/extract-job-resource/extract-job-resource-get

    @_syntax(options)
    def do_get_job(self, namespace):
        '''Get job'''  # TODO
        options = validate_job(namespace.options)
        _pprint(self.client.get(
            'expense/extract/v1.0/{extract id}/job' % options,
            ))

    @_syntax(options)
    def do_get_job_by_id(self, namespace):
        '''Get job_by_id'''  # TODO
        options = validate_job_by_id(namespace.options)
        _pprint(self.client.get(
            'expense/extract/v1.0/{extract id}/job/{job id}' % options,
            ))

    @_syntax(options)
    def do_get_status(self, namespace):
        '''Get status'''  # TODO
        options = validate_status(namespace.options)
        _pprint(self.client.get(
            'expense/extract/v1.0/{extract id}/job/{job id}/status' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/extract/extract-job-resource/extract-job-resource-post

    @_syntax(options)
    def do_post_job(self, namespace):
        '''Post job'''  # TODO
        options = validate_job(namespace.options)
        _pprint(self.client.post(
            'expense/extract/v1.0/{extract id}/job' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/imaging/image-resource/image-resource-post

    @_syntax(options)
    def do_post_receipt(self, namespace):
        '''Post receipt'''  # TODO
        options = validate_receipt(namespace.options)
        _pprint(self.client.post(
            'image/v1.0/receipt' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_expenseentry_by_id(self, namespace):
        '''Post expenseentry_by_id'''  # TODO
        options = validate_expenseentry_by_id(namespace.options)
        _pprint(self.client.post(
            'image/v1.0/expenseentry/{expenseentry id}' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_invoice_by_id(self, namespace):
        '''Post invoice_by_id'''  # TODO
        options = validate_invoice_by_id(namespace.options)
        _pprint(self.client.post(
            'image/v1.1/invoice/{invoice id}' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_report_by_id_1(self, namespace):
        '''Post report_by_id_1'''  # TODO
        options = validate_report_by_id_1(namespace.options)
        _pprint(self.client.post(
            'image/v1.0/report/{report id}' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/imaging/image-url-resource/image-url-resource-get

    @_syntax(options)
    def do_get_receipt_by_id(self, namespace):
        '''Get receipt_by_id'''  # TODO
        options = validate_receipt_by_id(namespace.options)
        _pprint(self.client.get(
            'image/v1.0/receipt/{receipt id}' % options,
            ))

    @_syntax(options)
    def do_get_report_by_id_1(self, namespace):
        '''Get report_by_id_1'''  # TODO
        options = validate_report_by_id_1(namespace.options)
        _pprint(self.client.get(
            'image/v1.0/report/{report id}' % options,
            ))

    @_syntax(options)
    def do_get_expenseentry_by_id(self, namespace):
        '''Get expenseentry_by_id'''  # TODO
        options = validate_expenseentry_by_id(namespace.options)
        _pprint(self.client.get(
            'image/v1.0/expenseentry/{expenseentry id}' % options,
            ))

    @_syntax(options)
    def do_get_invoice_by_id(self, namespace):
        '''Get invoice_by_id'''  # TODO
        options = validate_invoice_by_id(namespace.options)
        _pprint(self.client.get(
            'image/v1.0/invoice/{invoice id}' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/quick-expense/quick-expense-resource/quick-expense-resource-get

    @_syntax(options)
    def do_get_quickexpense(self, namespace):
        '''Get quickexpense'''  # TODO
        options = validate_quickexpense(namespace.options)
        _pprint(self.client.get(
            'expense/expensereport/v1.0/quickexpense' % options,
            ))

    # See also: https://developer.concur.com/api-documentation/web-services/quick-expense/quick-expense-resource/quick-expense-resource-post

    @_syntax(options)
    def do_post_quickexpense(self, namespace):
        '''Post quickexpense'''  # TODO
        options = validate_quickexpense(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.0/quickexpense' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))

    @_syntax(options)
    def do_post_quickexpense_1(self, namespace):
        '''Post quickexpense_1'''  # TODO
        options = validate_quickexpense_1(namespace.options)
        _pprint(self.client.post(
            'expense/expensereport/v1.0/quickexpense' % options,
            RootTag=options,  # TODO
            _xmlns='http://www.concursolutions.com/api/expense/expensereport/2011/03',  # TODO
            ))


def main(argv=None):
    if argv is None:
        import sys
        argv = sys.argv[1:]
    ConcurCmd().cmdloop()

if __name__ == '__main__':
    main()
