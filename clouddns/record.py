# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"


class Record(object):
    def __init__(self, domain,
                 data=None,
                 ttl=1800,
                 name=None,
                 priority=None,
                 type=None,
                 updated=None,
                 created=None,
                 id=None):
        self.domain = domain
        self.data = data
        self.name = name
        self.priority = priority
        self.id = id
        self.ttl = ttl
        self.type = type
        self.updated = updated and \
            self.domain.conn.convert_iso_datetime(updated) or \
            None
        self.created = created and \
            self.domain.conn.convert_iso_datetime(created) or \
            None

    def update(self, data=None,
               name=None,
               ttl=None,
               priority=None,
               type=None
               ):
        build_it = lambda k, v, d: ' %s="%s"' % (k, v and v or d)
        if data:
            self.data = data
        elif ttl:
            self.ttl = ttl
        elif name:
            self.name = name
        elif priority:
            self.priority = priority
        xml = '<record '
        xml += build_it('name', name, self.name)
        xml += build_it('ttl', ttl, self.ttl)
        xml += build_it('data', data, self.data)
        if self.type.upper() in ['MX', 'SRV']:
            xml += build_it('priority', priority, self.priority)

        xml += ' />'
        response = self.domain.conn.make_request('PUT',
                                                 ["domains",
                                                  self.domain.id,
                                                  "records",
                                                  self.id],
                                                 data=xml)
        output = self.domain.conn.wait_for_async_request(response)
        return output

    def __str__(self):
        return self.name


class RecordResults(object):
    """
    An iterable results set records for Record.

    This class implements dictionary- and list-like interfaces.
    """
    def __init__(self, domain, records=None):
        if records is None:
            records = []
        self._names = []
        self._records = []
        for obj in records:
                self._names.append(obj['name'])
                self._records.append(obj)
        self.domain = domain

    def __getitem__(self, key):
        return Record(self.domain, **(self._records[key]))

    def __getslice__(self, i, j):
        return [Record(self.domain, record_id=k) \
                    for k in self._records[i:j]]

    def __contains__(self, item):
        return item in self._records

    def __len__(self):
        return len(self._records)

    def __repr__(self):
        return 'RecordResults: %s records' % len(self._records)
    __str__ = __repr__

    def index(self, value, *args):
        """
        returns an integer for the first index of value
        """
        return self._names.index(value, *args)

    def count(self, value):
        """
        returns the number of occurrences of value
        """
        return self._names.count(value)
