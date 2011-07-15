__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
"""
connection operations

Connection instances are used to communicate with the remote service.

See COPYING for license information.
"""

import  os
import  socket
import  consts
import  time
from Queue  import Queue, Empty, Full
from errors import ResponseError
from httplib   import HTTPSConnection, HTTPConnection, HTTPException
from sys    import version_info
from urllib import quote

from utils  import unicode_quote, parse_url, \
 THTTPConnection, THTTPSConnection
from domain import DomainResults, Domain
from authentication import Authentication
from    fjson     import json_loads
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
        path = '/%s/%s' % \
                 (self.uri.rstrip('/'), '/'.join(
                   [unicode_quote(i) for i in path]))
        if isinstance(parms, dict) and parms:
            query_args = \
                ['%s=%s' % (quote(x),
                            quote(str(y))) for (x, y) in parms.items()]
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
                sys.stderr.write("URL: %s\n" % (path))
                sys.stderr.write("ARGS: %s\n" % (str(data)))
                sys.stderr.write("METHOD: %s\n" % (str(method)))
                sys.stderr.write("HEADERS: %s\n" % (str(headers)))
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

    def list_domains_info(self):
        response = self.make_request('GET', ['domains'])
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        return json_loads(response.read())['domains']

    def get_domain(self, id=None, **dico):
        if id:
            dico['id'] = id
        domains = self.list_domains_info()
        for domain in domains:
            for k in dico:
                if k in domain and domain[k] == dico[k]:
                    return Domain(self, **domain)
        #TODO:
        raise Exception("Not found")

    # Take a reponse parse it if there is asyncResponse and wait for
    # it (TODO: should offer to not)
    def wait_for_async_request(self, response):
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        output = json_loads(response.read())

        while True:
            if 'asyncResponse' in output:
                jobId = output['asyncResponse']['jobId']
                response = self.make_request('GET', ['status', jobId])
                if (response.status < 200) or (response.status > 299):
                    response.read()
                    raise ResponseError(response.status, response.reason)
                _output = response.read().strip()
                if not _output:
                    return True
                output = json_loads(_output)
                time.sleep(1)
                continue
            elif 'DnsFault' in output:
                raise ResponseError(output['DnsFault']['code'],
                                    output['DnsFault']['message'])
            else:
                return output

    def create_domain(self, name, ttl, emailAddress):
        if not ttl >= 300:
            raise Exception("Ttl is a minimun of 300 seconds")
        xml = """<domains xmlns="http://docs.rackspacecloud.com/dns/api/v1.0">
    <domain name="%(name)s" ttl="%(ttl)s" emailAddress="%(emailAddress)s">
    </domain>
</domains>
""" % locals()
        response = self.make_request('POST', ['domains'], data=xml)
        output = self.wait_for_async_request(response)

        if 'domains' in output:
            domain = output["domains"]["domain"]
            return Domain(connection=self, **domain[0])
        else:
            raise Exception("This should not happen")

    #TODO: deleteSubdomain
    def delete_domain(self, domain_id):
        response = self.make_request('DELETE', ['domains', domain_id])
        return self.wait_for_async_request(response)


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
