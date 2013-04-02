# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import json

import consts
from errors import InvalidDomainName, ResponseError
from math import ceil
from record import RecordResults, Record
from utils import is_subdict


class Domain(object):
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
                 comment=None,
                 updated=None,
                 created=None,
                 nameservers=[],
                 recordsList=[],
                 ):
        self.conn = connection
        self.name = name
        self.id = id
        self.accountId = accountId
        self.ttl = ttl
        self.emailAddress = emailAddress
        self.comment = comment
        self.updated = updated and \
            self.conn.convert_iso_datetime(updated) or \
            None
        self.created = created and \
            self.conn.convert_iso_datetime(created) or \
            None
        self.nameservers = nameservers
        self.records = recordsList
        self._total_records = -1
    
    @property
    def total_records(self):
        if self._total_records == -1:
            self.list_records_info(offset=0, limit=1)
        return self._total_records

    def get_record(self, id=None, **dico):
        if id:
            dico['id'] = id
        if 'name' in dico:
            dico['name'] = dico['name'].lower()
        records = self.list_records_info()
        for record in records:
            if is_subdict(dico, record):
                return Record(self, **record)
        #TODO:
        raise Exception("Not found")

    def get_records(self, type=None, name=None, data=None, offset=0, limit=None):
        return RecordResults(self, self.list_records_info(type,
                                                          name,
                                                          data,
                                                          offset,
                                                          limit))

    def list_records_info(self, type=None, 
                                name=None, 
                                data=None, 
                                offset=0, 
                                limit=None):
        if offset != 0:
            if limit is None:
                raise ValueError('limit must be specified when setting offset')
            elif offset % limit > 0:
                raise ValueError(
                        'offset (%d) must be a multiple of limit (%d)' % 
                        (offset, limit))
        if limit is None:
            limit = int(ceil(self.total_records / 100.0) * 100)
        if (name is not None or data is not None) and type is None:
            raise ValueError('filtering by name or data requires type to be set')
        records = []
        step = min(limit, 100)
        for _offset in xrange(offset, offset + limit, step):
            resp = self._list_records_raw(type, name, data, _offset, step)
            records_info = json.loads(resp)
            if 'totalEntries' in records_info:
                self._total_records = records_info['totalEntries']
            records.extend(records_info['records'])
        return records[:limit]

    def _list_records_raw(self, type, name, data, offset, limit):
        """
        Returns a chunk list of records
        """
        parms = {'offset': offset, 'limit': limit, 'type': type, 
                 'name': name, 'data': data}
        parms = dict(filter(lambda x: x[1] is not None, parms.items()))
        response = self.conn.make_request('GET', ["domains", self.id,
                                                  "records"], parms=parms)
        if (response.status < 200) or (response.status > 299):
            response.read()
            raise ResponseError(response.status, response.reason)
        return response.read()

    def __getitem__(self, key):
        return self.get_record(key)

    def __str__(self):
        return self.name

    def update(self,
               ttl=None,
               emailAddress=None,
               comment=None):
        dom = {}
        if ttl:
            self.ttl = ttl
            dom['ttl'] = self.ttl
        if emailAddress:
            self.emailAddress = emailAddress
            dom['emailAddress'] = self.emailAddress
        if comment: 
            self.comment = comment
            dom['comment'] = self.comment
        js = json.dumps(dom)

        response = self.conn.make_request('PUT', ["domains", self.id],
                                          data=js, hdrs={'Content-Type': 'application/json'})
        output = self.conn.wait_for_async_request(response)
        return output

    def _record(self, name, data, type, ttl=None, priority=None, comment=""):
        rec = {'name': name,
               'data': data,
               'type': type,
               'comment': comment}
        if type.upper() in ('MX', 'SRV'):
            rec['priority'] = priority
        if ttl: rec['ttl'] = ttl
        return rec 

    def create_record(self, name, data, type, ttl=None, priority=None, comment=""):
        rec = [name, data, type, ttl, priority, comment]
        return self.create_records((rec,))[0]

    def create_records(self, records):
        ret = []
        for rec in records:
            ret.append(self._record(*rec))
        js = json.dumps({"records": ret})
        response = self.conn.make_request('POST',
                                          ['domains', self.id, 'records'],
                                          data=js,
                                          hdrs={'Content-Type': 'application/json'})
        output = self.conn.wait_for_async_request(response)

        ret = []
        for record in output['records']:
            ret.append(Record(domain=self, **record))
        return ret

    def delete_record(self, record_id):
        return self.delete_records([record_id])

    def delete_records(self, records_id):
        ret = ["id=%s" % (i) for i in records_id]
        response = self.conn.make_request('DELETE',
                                          ['domains',
                                           self.id,
                                           'records'],
                                          parms=ret,
                                           )
        return response


class DomainResults(object):
    """
    An iterable results set object for Domains.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, conn, domains=None):
        self._domains = domains if domains is not None else []
        self._names = [k['name'] for k in self._domains]
        self.conn = conn
    
    def __getitem__(self, key):
        kwargs = {}
        if 'comment' in self._domains[key]:
            kwargs['comment'] = self._domains[key]['comment']
        else:
            kwargs['comment'] = None
        
        return Domain(self.conn,
                      self._domains[key]['name'],
                      self._domains[key]['id'],
                      self._domains[key]['accountId'],
                      **kwargs)
                         

    def __getslice__(self, i, j):
        return [Domain(self.conn, k['name'], k['id'], \
                              k['accountId']) for k in self._domains[i:j]]

    def __contains__(self, item):
        return item in self._names

    def __repr__(self):
        return 'DomainResults: %s domains' % len(self)
    __str__ = __repr__

    def __len__(self):
        return len(self._domains)
