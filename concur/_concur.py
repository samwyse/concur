import json
import urllib
import requests
import types
try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO
from xml.etree.cElementTree import ElementTree, register_namespace, fromstring
import re

from _xml2json import elem_to_internal, internal_to_elem, UsingPrefix


class ConcurAPIError(Exception):
    """Raised if the Concur API returns an error."""
    pass


class ConcurClient(object):
    """OAuth client for the Concur API"""
    api_url = "https://www.concursolutions.com/api"
    #app_auth_url = "Concur://app/authorize"
    web_auth_uri = "https://www.concursolutions.com/net2/oauth2/Login.aspx"
    token_url = "https://www.concursolutions.com/net2/oauth2/GetAccessToken.ashx"
    #tokeninfo_url = "https://api.Concur-app.com/oauth/v1/tokeninfo"
##    authentication_scheme = "Bearer"
    authentication_scheme = "OAuth"

    def __init__(self, client_id=None, client_secret=None,
                 access_token=None, use_app=False):

        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.auth_url = self.app_auth_url if use_app else self.web_auth_uri
        self.use_app = use_app

    def build_oauth_url(self, redirect_uri=None, scope="EXPRPT", state=None):
        params = {
            'client_id': self.client_id,
            'scope': scope
        }

        if redirect_uri:
            params['redirect_uri'] = redirect_uri

        if state:
            params['state'] = state

        # Use '%20' instead of '+'.
        encoded = urllib.urlencode(params).replace('+', '%20')
        return "%s?%s" % (self.auth_url, encoded)

    def get_oauth_token(self, code, **kwargs):

        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            #'grant_type': kwargs.get('grant_type', 'authorization_code')
        }

        if 'redirect_uri' in kwargs:
            params['redirect_uri'] = kwargs['redirect_uri']
##        response = requests.post(self.token_url, params=params)
        response = requests.get(self.token_url, params=params)
        content_type, parsed = self.validate_response(response)
        if content_type == 'xml':
##            if root.tag != 'Access_Token':
##                raise ConcurAPIError('unknown XML tag: %s' % root.tag)
            for item in 'Token', 'Expiration_date', 'Refresh_Token':
                print '\t%s:\t%s' % (item, root.find(item).text)
            return root.find('Token').text
        if content_type == 'json':
            try:
                return response['access_token']
            except:
                raise ConcurAPIError(response)

    def validate_response(self, response):

        content_type = response.headers['content-type']
        if 'xml' in content_type:
            root = fromstring(response.content)
            if root.tag.lower() == 'error':
                raise ConcurAPIError(root.find('Message').text)
            return 'xml', elem_to_internal(root,
                canonize=UsingPrefix(default_namespace=root),
                )
        if 'json' in content_type:
            return 'json', json.loads(response.content)
        raise ConcurAPIError('unknown content-type: %s' % content_type)

    def api(self, path, method='GET', **kwargs):

        params = kwargs['params'] if 'params' in kwargs else {}
        data = kwargs['data'] if 'data' in kwargs else {}
        headers = kwargs['headers'] if 'headers' in kwargs else {}

        if not self.access_token and 'access_token' not in params:
            raise ConcurAPIError("You must provide a valid access token.")

        url = "%s/%s" % (self.api_url, path)

        if 'access_token' in params:
            access_token = params['access_token']
            del(params['access_token'])
        else:
            access_token = self.access_token

        headers['Authorization'] = '%s %s' % (self.authentication_scheme, access_token)

        resp = requests.request(method, url,
                                params=params,
                                headers=headers,
                                data=data,
                                )
        if str(resp.status_code)[0] not in ('2', '3'):
            print 'method =', method
            print 'url =', url
            print 'params =', params
            print 'headers =', headers
            print 'data =', data
            print
            raise ConcurAPIError("Error returned via the API with status code (%s):" %
                                resp.status_code, resp.text)
        return resp

    def get(self, path, **params):
        content_type, parsed = self.validate_response(
            self.api(path, 'GET', params=params))
        return parsed

    def post(self, path, **data):
        params = data.pop('_params', {})
        if '_xmlns' in data:
            headers = { 'content-type': 'application/xml' }
            elem = ElementTree(
                internal_to_elem(
                    data,
                    canonize=UsingPrefix(
                        default_namespace=data.pop('_xmlns'),
                        ),
                    ),
                )
            data = StringIO()
            elem.write(data)
            data = data.getvalue()
        else:
            headers = {}
        content_type, parsed = self.validate_response(
            self.api(path, 'POST',
                     params=params,
                     headers=headers,
                     data=data,
                     ))
        return parsed

    def __getattr__(self, name):
        '''\
Turn method calls such as "Concur.foo_bar(...)" into
"Concur.api('/foo/bar', 'GET', params={...})", and then parse the
response.
'''
        base_path = name.replace('_', '/')

        # Define a function that does what we want.
        def closure(*path, **params):
            'Accesses the /%s API endpoints.'
            path = list(path)
            path.insert(0, base_path)
            return self.parse_response(
                self.api('/'.join(path), 'GET', params=params)
                )

        # Clone a new method with the correct name and doc string.
        retval = types.FunctionType(
            closure.func_code,
            closure.func_globals,
            name,
            closure.func_defaults,
            closure.func_closure)
        retval.func_doc =  closure.func_doc % base_path

        # Cache it to avoid additional calls to __getattr__.
        setattr(self, name, retval)
        return retval
