#!/usr/bin/env python
import logging

#from django.conf import settings

from ultrasoap import UltraDNSClient, types, UDNSException, ZoneNotFound
import exceptions


def _strip_dot(domain_name):
    return domain_name.rstrip('.')


def _ensure_dot(domain_name):
    return _strip_dot(domain_name) + '.'


def _get_zone_records(record_api, domain_name, rr_type=types.ALL):
    domain_name = _ensure_dot(domain_name)
    client = get_neustar()
    try:
        rrs = client.get_resource_records_of_zone(domain_name, rr_type)
    except ZoneNotFound, e:
        raise exceptions.ZoneNotFound(orig_execption=e)
    except UDNSException, e:
        raise exceptions.DomainServiceError(orig_execption=e)
    return rrs
    #return [DNSRecord.rr_to_record(record_api, domain_name, rr) for rr in rrs]


# Public API:

_nameservers_cache = None

def get_nameservers():
    global _nameservers_cache
    if _nameservers_cache is None:
        _nameservers_cache = settings.NEUSTAR_NAMESERVERS
    return _nameservers_cache


def get_neustar(timeout=90):
    from credentials import url, user, password, account_id
    client = UltraDNSClient(url=url, user=user, password=password,
                            account_id=account_id, timeout=timeout)
    return client


def create_zone(domain_name):
    domain_name = _ensure_dot(domain_name)
    client = get_neustar()
    return client.create_primary_zone(domain_name)


def delete_zone(domain_name):
    domain_name = _ensure_dot(domain_name)
    client = get_neustar()
    return client.delete_zone(domain_name)


def get_entries(domain_name):
    domain_name = _ensure_dot(domain_name)
    records = _get_zone_records(None, domain_name)
    records.sort()
    return [r.record_dict for r in records if r.interesting()]


def change_record(domain_name, record_name, record_type, values):
    pass


def main():
    logging.basicConfig(level=logging.INFO)
    logging.getLogger('suds.client').setLevel(logging.DEBUG)

    #print get_neustar().service.getZoneInfo(zoneName='wwwiketechonlinecom.com.')
    #delete_zone('wwwiketechonlinecom.com')
    #create_zone('wwwiketechonlinecom.com')
    print get_entries('wwwiketechonlinecom.com')


if __name__ == '__main__':
    main()
