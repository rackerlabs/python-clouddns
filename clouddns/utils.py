""" See COPYING for license information. """

import re
from urllib    import quote
from urlparse  import urlparse
from errors    import InvalidUrl
from httplib   import HTTPConnection, HTTPSConnection


def parse_url(url):
    """
    Given a URL, returns a 4-tuple containing the hostname, port,
    a path relative to root (if any), and a boolean representing
    whether the connection should use SSL or not.
    """
    (scheme, netloc, path, params, query, frag) = urlparse(url)

    # We only support web services
    if not scheme in ('http', 'https'):
        raise InvalidUrl('Scheme must be one of http or https')

    is_ssl = scheme == 'https' and True or False

    # Verify hostnames are valid and parse a port spec (if any)
    match = re.match('([a-zA-Z0-9\-\.]+):?([0-9]{2,5})?', netloc)

    if match:
        (host, port) = match.groups()
        if not port:
            port = is_ssl and '443' or '80'
    else:
        raise InvalidUrl('Invalid host and/or port: %s' % netloc)

    return (host, int(port), path.strip('/'), is_ssl)


def unicode_quote(s):
    """
    Utility function to address handling of unicode characters
    when using the quote method of the stdlib module
    urlparse. Converts unicode, if supplied, to utf-8 and returns
    quoted utf-8 string.

    For more info see http://bugs.python.org/issue1712522 or
    http://mail.python.org/pipermail/python-dev/2006-July/067248.html
    """
    if isinstance(s, unicode):
        return quote(s.encode("utf-8"))
    else:
        return quote(str(s))

def is_subdict(subdict, parentdict):
    """
    Utility function that returns True id `subdict` is a subset
    of `parentdict`.
    All the key->value pairs found in `subdict` should be found
    and equal in `parentdict`
    """
    for key in subdict:
        if key not in parentdict:
            return False
        if subdict[key] != parentdict[key]:
            return False
    return True

class THTTPConnection(HTTPConnection):
    def __init__(self, host, port, timeout):
        HTTPConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        HTTPConnection.connect(self)
        self.sock.settimeout(self.timeout)


class THTTPSConnection(HTTPSConnection):
    def __init__(self, host, port, timeout):
        HTTPSConnection.__init__(self, host, port)
        self.timeout = timeout

    def connect(self):
        HTTPSConnection.connect(self)
        self.sock.settimeout(self.timeout)
