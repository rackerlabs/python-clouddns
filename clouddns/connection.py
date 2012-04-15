__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
"""
connection operations

Connection instances are used to communicate with the remote service.

See COPYING for license information.
"""

import os
import socket
import consts
import time
import datetime
import json

from Queue import Queue, Empty, Full
from errors import ResponseError, UnknownDomain, NotDomainOwner, DomainAlreadyExists
from httplib import HTTPSConnection, HTTPConnection, HTTPException
from sys import version_info
from urllib import quote

from utils  import unicode_quote, parse_url, \
    THTTPConnection, THTTPSConnection
from domain import DomainResults, Domain
from authentication import Authentication

# Because HTTPResponse objects *have* to have read() called on them
# before they can be used again ...
# pylint: disable-msg=W0612


class Connection(object):
    """
    Manages the connection to the storage system and serves as a factory
    for Container instances.

    @undocumented: http_connect
    @undocumented: make_request
    @undocumented: _check_container_name
    """

    def __init__(self, username=None, api_key=None, timeout=10, **kwargs):
        """
        Accepts keyword arguments for Rackspace Cloud username and api key.
        Optionally, you can omit these keywords and supply an
        Authentication object using the auth keyword.

        @type username: str
        @param username: a Rackspace Cloud username
        @type api_key: str
        @param api_key: a Rackspace Cloud API key
        """
        self.connection_args = None
        self.connection = None
        self.token = None
        self.debuglevel = int(kwargs.get('debuglevel', 0))
        self.user_agent = kwargs.get('useragent', consts.user_agent)
        self.timeout = timeout

        self.auth = 'auth' in kwargs and kwargs['auth'] or None

        if not self.auth:
            authurl = kwargs.get('authurl', consts.us_authurl)
            if username and api_key and authurl:
                self.auth = Authentication(username, api_key, authurl=authurl,
                            useragent=self.user_agent)
            else:
                raise TypeError("Incorrect or invalid arguments supplied")

        self._authenticate()

    def _authenticate(self):
        """
        Authenticate and setup this instance with the values returned.
        """
        (url, self.token) = self.auth.authenticate()
        self.connection_args = parse_url(url)

        if version_info[0] <= 2 and version_info[1] < 6:
            self.conn_class = self.connection_args[3] and THTTPSConnection or \
                                                              THTTPConnection
        else:
            self.conn_class = self.connection_args[3] and HTTPSConnection or \
                                                              HTTPConnection
        self.http_connect()

    def convert_iso_datetime(self, dt):
        """
        Convert iso8601 to datetime
        """
        isoFormat = "%Y-%m-%dT%H:%M:%S.000+0000"
        if type(dt) is datetime.datetime:
            return dt
        if dt.endswith("Z"):
            dt = dt.split('Z')[0]
            isoFormat = "%Y-%m-%dT%H:%M:%S"
        return datetime.datetime.strptime(dt, isoFormat)

    def http_connect(self):
        """
        Setup the http connection instance.
        """
        (host, port, self.uri, is_ssl) = self.connection_args
        self.connection = self.conn_class(host, port=port, \
                                              timeout=self.timeout)
        self.connection.set_debuglevel(self.debuglevel)

    def make_request(self, method, path=[], data='', hdrs=None, parms=None):
        """
        Given a method (i.e. GET, PUT, POST, etc), a path, data, header and
        metadata dicts, and an optional dictionary of query parameters,
        performs an http request.
        """
        query_args = ""
        path = '/%s/%s' % \
                 (self.uri.rstrip('/'), '/'.join(
                   [unicode_quote(i) for i in path]))
        if isinstance(parms, dict) and parms:
            query_args = \
                ['%s=%s' % (quote(x),
                            quote(str(y))) for (x, y) in parms.items()]
        elif isinstance(parms, list) and parms:
            query_args = \
                ["%s" % x for x in parms]
        path = '%s?%s' % (path, '&'.join(query_args))

        headers = {'Content-Length': str(len(data)),
                   'User-Agent': self.user_agent,
                   'X-Auth-Token': self.token}
        isinstance(hdrs, dict) and headers.update(hdrs)

        def retry_request():
            '''Re-connect and re-try a failed request once'''
            self.http_connect()
            self.connection.request(method, path, data, headers)
            return self.connection.getresponse()

        try:
            if 'PYTHON_CLOUDDNS_DEBUG' in os.environ and \
                    os.environ['PYTHON_CLOUDDNS_DEBUG'].strip():
                import sys
                url = "https://%s%s\n" % \
                    (self.connection_args[0],
                     path)
                sys.stderr.write("METHOD: %s\n" % (str(method)))
                sys.stderr.write("URL: %s" % (url))
                sys.stderr.write("HEADERS: %s\n" % (str(headers)))
                sys.stderr.write("DATA: %s\n" % (str(data)))
                sys.stderr.write("curl -X '%s' -H 'X-Auth-Token: %s' %s %s" % \
                                     (method, self.token, url, str(data)))
            self.connection.request(method, path, data, headers)
            response = self.connection.getresponse()
        except (socket.error, IOError, HTTPException):
            response = retry_request()
        if response.status == 401:
            self._authenticate()
            headers['X-Auth-Token'] = self.token
            response = retry_request()
        return response

    def get_domains(self):
        return DomainResults(self, self.list_domains_info())

    def list_domains_info(self, filter_by_name=None):
        parms = {}
        if filter_by_name:
            parms = {'name': filter_by_name}
        response = self.make_request('GET', ['domains'], parms=parms)
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        read_output = response.read()
        return json.loads(read_output)['domains']

    def get_domain(self, id=None, **dico):
        filter_by_name = ""
        if id:
            dico['id'] = id
        if 'name' in dico:
            dico['name'] = dico['name'].lower()
            filter_by_name = dico['name']

        domains = self.list_domains_info(filter_by_name=filter_by_name)
        for domain in domains:
            for k in dico:
                if k in domain and domain[k] == dico[k]:
                    return Domain(self, **domain)
        raise UnknownDomain("Not found")

    # Take a reponse parse it if there is asyncResponse and wait for
    # it (TODO: should offer to not)
    def wait_for_async_request(self, response):
        if (response.status < 200) or (response.status > 299):
            _output = response.read().strip()
            try:
                output = json.loads(_output)
            except ValueError:
                output = None
            api_reasons = ""
            if output and 'validationErrors' in output:
                for msg in output['validationErrors']['messages']:
                    api_reasons += " (%s)" % msg
            raise ResponseError(response.status, response.reason+api_reasons)
        output = json.loads(response.read())
        jobId = output['jobId']
        while True:
            response = self.make_request('GET', ['status', jobId],
                                         parms=['showDetails=True']) 
            if (response.status < 200) or (response.status > 299):
                response.read()
                raise ResponseError(response.status, response.reason)
            _output = response.read().strip()
            output = json.loads(_output)
            if output['status'] == 'COMPLETED':
                try:
                    return output['response']
                except KeyError:
                    return output
            if output['status'] == 'ERROR':
                if (output['error']['code'] == 409 and 
                    output['error']['details'] == 'Domain already exists'):
                    raise DomainAlreadyExists
                if (output['error']['code'] == 409 and 
                    output['error']['details'].find('belongs to another owner')):
                    raise NotDomainOwner
                raise ResponseError(output['error']['code'],
                                    output['error']['details'])
            time.sleep(1)
            continue

    def _domain(self, name, ttl, emailAddress, comment=""):
        if not ttl >= 300:
            raise Exception("Ttl is a minimun of 300 seconds")
        s = '<domain name="%s" ttl="%s" emailAddress="%s" comment="%s"></domain>'
        return s % (name, ttl, emailAddress, comment)

    def create_domain(self, name, ttl, emailAddress, comment=""):
        domain = [name, ttl, emailAddress, comment]
        return self.create_domains([domain])[0]

    def create_domains(self, domains):
        xml = '<domains xmlns="http://docs.rackspacecloud.com/dns/api/v1.0">'
        ret = []
        for dom in domains:
            ret.append(self._domain(*dom))
        xml += "\n".join(ret)
        xml += "</domains>"
        response = self.make_request('POST', ['domains'], data=xml)
        output = self.wait_for_async_request(response)

        ret = []
        for domain in output['domains']:
            ret.append(Domain(connection=self, **domain))
        return ret

    def delete_domain(self, domain_id):
        return self.delete_domains([domain_id])

    def delete_domains(self, domains_id):
        ret = ["id=%s" % (i) for i in domains_id]
        response = self.make_request('DELETE',
                                     ['domains'],
                                     parms=ret,
                                      )
        return self.wait_for_async_request(response)

    def import_domain(self, bind_zone):
        """
        Allows for a bind zone file to be imported in one operation.  The
        bind_zone parameter can be a string or a file object.
        """

        if type(bind_zone) is file:
            bind_zone = bind_zone.read()

        xml = '<domains xmlns="http://docs.rackspacecloud.com/dns/api/v1.0">'
        xml += '<domain contentType="BIND_9">'
        xml += '<contents>%s</contents>' % bind_zone
        xml += '</domain></domains>'

        response = self.make_request('POST', ['domains', 'import'], data=xml)
        output = self.wait_for_async_request(response)

        ret = []
        for domain in output['domains']:
            ret.append(Domain(self, **domain))
        return ret


class ConnectionPool(Queue):
    """
    A thread-safe connection pool object.

    This component isn't required when using the clouddns library, but it may
    be useful when building threaded applications.
    """

    def __init__(self, username=None, api_key=None, **kwargs):
        auth = kwargs.get('auth', None)
        self.timeout = kwargs.get('timeout', 5)
        self.connargs = {'username': username,
                         'api_key': api_key,
                         'auth': auth}
        poolsize = kwargs.get('poolsize', 10)
        Queue.__init__(self, poolsize)

    def get(self):
        """
        Return a clouddns connection object.

        @rtype: L{Connection}
        @return: a clouddns connection object
        """
        try:
            (create, connobj) = Queue.get(self, block=0)
        except Empty:
            connobj = Connection(**self.connargs)
        return connobj

    def put(self, connobj):
        """
        Place a clouddns connection object back into the pool.

        @param connobj: a clouddns connection object
        @type connobj: L{Connection}
        """
        try:
            Queue.put(self, (time.time(), connobj), block=0)
        except Full:
            del connobj
# vim:set ai sw=4 ts=4 tw=0 expandtab:
