"""
exception classes

See COPYING for license information.
"""


class Error(StandardError):
    """
    Base class for all errors and exceptions
    """
    pass


class ResponseError(Error):
    """
    Raised when the remote service returns an error.
    """
    def __init__(self, status, reason):
        self.status = status
        self.reason = reason
        Error.__init__(self)

    def __str__(self):
        return '%d: %s' % (self.status, self.reason)

    def __repr__(self):
        return '%d: %s' % (self.status, self.reason)


class InvalidDomainName(Error):
    """
    Raised for invalid storage domain names.
    """
    pass


class AuthenticationFailed(Error):
    """
    Raised on a failure to authenticate.
    """
    pass


class AuthenticationError(Error):
    """
    Raised when an unspecified authentication error has occurred.
    """
    pass


class InvalidUrl(Error):
    """
    Not a valid url for use with this software.
    """
    pass

class UnknownDomain(Error):
    """
    Raised when a domain name does not belong to this account.
    """
    pass
