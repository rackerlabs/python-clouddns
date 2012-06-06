=========================================
 Python interface to Rackspace Cloud DNS
=========================================

:Homepage:  https://github.com/chmouel/python-clouddns
:Credits:   Copyright 2011 Chmouel Boudjnah <chmouel@chmouel.com>
:Licence:   BSD


Usage
=====

A Rackspace Cloud username and API key are required and can be obtained
from http://manage.rackspacecloud.com.  

Domains and records can be found by specifying their name or id.  To
enable debugging output for the HTTP connection, include the keyword 
argument debuglevel=1.  Additional debugging output is available by
setting the 'PYTHON_CLOUDDNS_DEBUG' environment variable.

List all domains::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    for domain in dns.get_domains():
        print domain.name

Create a new domain::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    dns.create_domain(name='1234-example.com', ttl=300, 
                      emailAddress='me@you.com')

Import a domain from a BIND zone file or string::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    with open('/tmp/example.com.zone', 'r') as f:
        dns.import_domain(f)

Update a domain::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    domain = dns.get_domain(name='1234-example.com')
    domain.update(ttl=600)

Delete a domain::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    domain = dns.get_domain(name='1234-example.com')
    dns.delete_domain(domain.id)

List all records for a domain::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    domain = dns.get_domain(name='1234-example.com')
    for record in domain.get_records():
        print '(%s) %s -> %s' % (record.type, record.name, record.data)

Create new record::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    domain = dns.get_domain(name='1234-example.com')
    domain.create_record('www.1234-example.com', '127.0.0.1', 'A')

Update a record::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    domain = dns.get_domain(name='1234-example.com')
    record = domain.get_record(name='www.1234-example.com')
    record.update(data='10.1.1.1', ttl=600)

Delete a record::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey')

    domain = dns.get_domain(name='1234-example.com')
    record = domain.get_record(name='www.1234-example.com')
    domain.delete_record(record.id)

Alternative Geographic Endpoints
================================

The examples above use the default authentication endpoint in the US. For UK
accounts, you must override the authentication URL::

    #!/usr/bin/env python
    import clouddns
    dns = clouddns.connection.Connection('username','apikey',
                                         authurl=clouddb.consts.uk_authurl)
  
GUI
===

A web based GUI is available here: https://github.com/rackerhacker/rackspace-clouddns-gui

