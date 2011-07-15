# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"

import consts
from errors import InvalidDomainName, ResponseError
from fjson import json_loads
from record import RecordResults, Record


class Domain(object):
    """
    Container object and Object instance factory.

    If your account has the feature enabled, containers can be publically
    shared over a global content delivery network.

    @ivar name: the container's name (generally treated as read-only)
    @type name: str
    @ivar object_count: the number of objects in this container (cached)
    @type object_count: number
    """
    def __set_name(self, name):
        # slashes make for invalid names
        if isinstance(name, (str, unicode)) and \
                ('/' in name or len(name) > consts.domain_name_limit):
            raise InvalidDomainName(name)
        self._name = name

    name = property(fget=lambda self: self._name, fset=__set_name,
        doc="the name of the domain (read-only)")

    def __init__(self, connection=None,
                 name=None,
                 id=None,
                 accountId=None,
                 ttl=None,
                 emailAddress=None,
                 ):
        """
        Domains will rarely if ever need to be instantiated directly by the
        user.

        Instead, use the L{create_domain<Connection.create_domain>},
        L{get_domain<Connection.get_domain>},
        L{list_domains<Connection.list_domains>} and
        other methods on a valid Connection object.
        """
        self.conn = connection
        self.name = name
        self.id = id
        self.accountId = accountId
        self.ttl = ttl
        self.emailAddress = emailAddress

    def get_record(self, id=None, **dico):
        if id:
            dico['id'] = id
        records = self.list_records_info()
        for record in records:
            for k in dico:
                if k in record and record[k] == dico[k]:
                    return Record(self, **record)
        #TODO:
        raise Exception("Not found")

    def get_records(self):
        return RecordResults(self, self.list_records_info())

    def list_records_info(self):
        resp = self._list_records_raw()
        return json_loads(resp)['records']['record']

    def _list_records_raw(self):
        """
        Returns a chunk list of records
        """
        response = self.conn.make_request('GET', ["domains", self.id,
                                                  "records"])
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        return response.read()

    def __getitem__(self, key):
        return self.get_record(key)

    def __str__(self):
        return self.name

    def update(self, name=None,
               ttl=None,
               emailAddress=None):
        xml = '<domain xmlns="http://docs.rackspacecloud.com/dns/api/v1.0" '

        if name:
            xml += ' name="%s"' % (name)
            self.name = name
        if ttl:
            xml += ' ttl="%s"' % (ttl)
            self.ttl = ttl
        if emailAddress:
            xml += ' emailAddress="%s"' % (emailAddress)
            self.emailAddress = emailAddress
        xml += ' />'

        response = self.conn.make_request('PUT', ["domains", self.id],
                                          data=xml)
        output = self.conn.wait_for_async_request(response)
        return output

    def create_record(self, name, data, type):
        xml = """<recordsList xmlns="http://docs.rackspacecloud.com/dns/api/v1.0">
<record type="%(type)s" data="%(data)s" name="%(name)s"/>
</recordsList>
        """ % locals()
        response = self.conn.make_request('POST',
                                          ['domains', self.id, 'records'],
                                          data=xml)
        output = self.conn.wait_for_async_request(response)
        if 'records' in output:
            record = output["records"]
            return Record(domain=self, **record[0])
        else:
            raise Exception("This should not happen")

    def delete_record(self, record_id):
        response = self.conn.make_request('DELETE',
                                          ['domains',
                                           self.id,
                                           'records',
                                           record_id])
        return response


class DomainResults(object):
    """
    An iterable results set object for Domains.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, conn, domains=list()):
        self._domains = domains
        self._names = [k['name'] for k in domains]
        self.conn = conn

    def __getitem__(self, key):
        return Domain(self.conn,
                         self._domains[key]['name'],
                         self._domains[key]['id'],
                         self._domains[key]['accountId'])

    def __getslice__(self, i, j):
        return [Domain(self.conn, k['name'], k['id'], \
                              k['accountId']) for k in self._domains[i:j]]

    def __contains__(self, item):
        return item in self._names

    def __repr__(self):
        return 'DomainResults: %s domains' % len(self._domains)
    __str__ = __repr__

    def __len__(self):
        return len(self._domains)
