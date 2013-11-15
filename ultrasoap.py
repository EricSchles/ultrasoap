from contextlib import contextmanager
from functools import wraps

from suds import WebFault
from suds.client import Client
from suds.wsse import Security, UsernameToken

import ultratypes as types

RECORD_TYPES = {
    'A': '1',
    'CNAME': '5',
    'MX': '15',
    'NS': '2',
    'TXT': '16',
}

TTL = '86400'

@contextmanager
def udns_transaction(client):
    '''
    Context manager for UltraDNS transactions. Returns the transaction ID that
    should be passed to UltraDNSClient methods.
    '''
    transaction_id = client.start_transaction()
    try:
        yield transaction_id
        client.commit_transaction(transaction_id)
    except:
        client.rollback_transaction(transaction_id)
        raise


UDNS_ERRORS = {}

def error_id(id_):
    '''Register the excption in UDNS_ERRORS'''
    def wrap_exception(cls):
        UDNS_ERRORS[id_] = cls
        return cls
    return wrap_exception


class UDNSException(Exception):
    pass


@error_id(1801)
class ZoneNotFound(UDNSException):
    pass


def translate_exceptions(f):
    '''Translate suds WebFaults to UDNSException (or an appropriate subclass)'''
    @wraps(f)
    def wrapper(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except WebFault, e:
            code = int(e.fault.detail.UltraWSException.errorCode)
            description = e.fault.detail.UltraWSException.errorDescription
            cls = UDNS_ERRORS.get(code, UDNSException)
            raise cls(code, description)
    return wrapper


class UltraDNSClient(object):
    def __init__(self, url, user, password, account_id, timeout=90):
        self.client = Client(url, timeout=timeout)
        self.account_id = account_id

        security = Security()
        token = UsernameToken(user, password)
        security.tokens.append(token)
        self.client.set_options(wsse=security)

    @property
    def factory(self):
        return self.client.factory

    @property
    def service(self):
        return self.client.service

    @translate_exceptions
    def start_transaction(self):
        return self.service.startTransaction()

    @translate_exceptions
    def commit_transaction(self, transaction):
        return self.service.commitTransaction(transactionID=transaction)

    @translate_exceptions
    def rollback_transaction(self, transaction):
        return self.service.rollbackTransaction(transactionID=transaction)

    @translate_exceptions
    def create_primary_zone(self, zone_name, transaction_id=''):
        return self.service.createPrimaryZone(transactionID=transaction_id,
                                              accountId=self.account_id,
                                              zoneName=zone_name,
                                              forceImport=True)

    @translate_exceptions
    def delete_zone(self, zone_name, transaction_id=''):
        return self.service.deleteZone(zoneName=zone_name,
                                       transactionID=transaction_id)

    @translate_exceptions
    def get_resource_records_of_zone(self, zone_name, rr_type=types.ALL):
        return self.service.getResourceRecordsOfZone(zoneName=zone_name,
                                                     rrType=rr_type)

    @translate_exceptions
    def create_record(self, zone_name, delegation_name, record_type):
        resource_record = self.factory.create('ns5:ResourceRecord')
        resource_record._DName = delegation_name
        resource_record._TTL = TTL
        resource_record._Type = RECORD_TYPES[record_type]
        resource_record._ZoneName = zone_name

        return resource_record

    @translate_exceptions
    def create_mx_record(self, zone_name, delegation_name, preference_value, mail_server,transaction_id=''):
        resource_record = self.create_record(zone_name, delegation_name, 'MX')
        resource_record.InfoValues._Info1Value = preference_value
        resource_record.InfoValues._Info2Value = mail_server
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_a_record(self, zone_name, delegation_name, ip_address_v4, transaction_id=''):
        resource_record = self.create_record(zone_name, delegation_name, 'A')
        resource_record.InfoValues._Info1Value = ip_address_v4
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_txt_record(self, zone_name, delegation_name, char_str, transaction_id=''):
        resource_record = self.create_record(zone_name, delegation_name, 'TXT')
        resource_record.InfoValues._Info1Value = char_str
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def remove_records(self, zone_name, transaction_id=''):
        existing_records = [rec for rec in self.get_resource_records_of_zone(zone_name)]

        results = []

        for rec in existing_records:
            gu_id = rec._Guid
            results.append(self.service.deleteResourceRecord(guid=gu_id,
                                                             trasactionID=transaction_id))
        return all(results)


    # @translate_exceptions
    # def create_ns_record(self, zone_name, zone_name_2, delegation_name, preference_value, transaction_id=''):
    #     resource_record = self.create_record(zone_name, delegation_name, 'NS')
    #     resource_record.InfoValues._Info1Value = zone_name_2
    #     return self.service.createResourceRecord(resourceRecord=resource_record,
    #                                              trasactionID=transaction_id)

