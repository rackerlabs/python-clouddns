# -*- encoding: utf-8 -*-
__author__ = "Chmouel Boudjnah <chmouel@chmouel.com>"
import clouddns
import os
import sys

REGION = "US"

US_RCLOUD_USER = os.environ.get("US_RCLOUD_USER")
US_RCLOUD_KEY = os.environ.get("US_RCLOUD_KEY")

UK_RCLOUD_USER = os.environ.get("UK_RCLOUD_USER")
UK_RCLOUD_KEY = os.environ.get("UK_RCLOUD_KEY")

CNX = None
if 'US' == REGION:
  DOMAIN = "%s-test-us.com" % (US_RCLOUD_USER)
elif 'UK' == REGION:
  DOMAIN = "%s-test-uk.com" % (US_RCLOUD_USER)

FORCE_DBG = True


def dbg(msg, force_dbg=FORCE_DBG):
    if ('PYTHON_CLOUDDNS_DEBUG' in os.environ and \
            os.environ['PYTHON_CLOUDDNS_DEBUG'].strip()) or \
            force_dbg:
        print "****** %s ******" % msg

if not US_RCLOUD_KEY or not US_RCLOUD_USER:
    print "API Keys env not defined"
    sys.exit(1)


def auth():
    global CNX
    if not CNX:
        if REGION == "US":
            dbg("Authing to US cloud")
            CNX = clouddns.connection.Connection(US_RCLOUD_USER, US_RCLOUD_KEY)
        elif REGION == "UK":
            dbg("DBG: Authing to UK cloud")
            CNX = clouddns.connection.Connection(
                UK_RCLOUD_USER,
                UK_RCLOUD_KEY,
                authurl=clouddns.consts.uk_authurl)
    return CNX


def test():
    cnx = auth()

    # Domain list
    all_domains = cnx.get_domains()
    if all_domains:
        # __getitem__
        domain = all_domains[0]

        # __getslice__
        domain = all_domains[0:1][0]
        # __contains__
        assert(str(domain) in all_domains)
        # __len__
        len(all_domains)

        for x in all_domains:
            prefix = "%s-test" % US_RCLOUD_USER
            if str(x).startswith(prefix):
                dbg("Deleting domain: %s" % x.name)
                cnx.delete_domain(x.id)

    # Create Domain
    dbg("Creating domain: %s" % (DOMAIN))
    domain_created = cnx.create_domain(name=DOMAIN,
                                       ttl=300,
                                       emailAddress="foo@foo.com")

    # Get domain by id.
    dbg("GETting domain by ID: %s" % (domain_created.id))
    sDomain = cnx.get_domain(domain_created.id)
    assert(sDomain.id == domain_created.id)

    # Get domain by name.
    dbg("GETting domain by Name: %s" % (DOMAIN))
    sDomain = cnx.get_domain(name=DOMAIN)
    assert(sDomain.id == domain_created.id)

    domain = domain_created

    ttl = 500
    # Update Domain
    domain.update(ttl=ttl)
    sDomain = cnx.get_domain(name=DOMAIN)

    record = "test1.%s" % (DOMAIN)
    # Create A Record
    dbg("Creating A Record: %s" % (record))
    newRecord = \
        domain.create_record(name=record, data="127.0.0.1", type="A")

    # Get Record by ID
    dbg("Get Record By ID: %s" % (newRecord.id))
    record = domain.get_record(newRecord.id)
    assert(record.id == newRecord.id)

    # Get Record by name
    dbg("Get Record By Name: %s" % (record))
    record = domain.get_record(name=record.name)
    assert(record.id == newRecord.id)

    # Modify A Record data
    newRecord.update(data="127.0.0.2", ttl=1300)
    record = domain.get_record(name=record.name)
    assert(record.data == newRecord.data)

    # Get list of records for the domain
    for rec  in domain.list_records_info():
        print rec

    # Delete A Record
    domain.delete_record(newRecord.id)

    # Create MX Record
    priority = 1
    dbg("Creating MX Record: %s" % (DOMAIN))
    newRecord = domain.create_record(name=DOMAIN, data='aspmx.l.google.com', priority=priority, type='MX')
    dbg("Check new record priority: %s" % (newRecord.id))
    record = domain.get_record(newRecord.id)
    assert(priority == record.priority)

    priority = 10
    # Update priority
    newRecord.update(priority=priority)
    record = domain.get_record(id=newRecord.id)
    assert(priority == record.priority)

    # Delete MX Record
    dbg('Tests Complete. Cleaning up')
    domain.delete_record(record.id)
    cnx.delete_domain(domain.id)

test()
