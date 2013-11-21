from contextlib import contextmanager
from functools import wraps

from suds import WebFault
from suds.client import Client
from suds.wsse import Security, UsernameToken

from ultratypes import types

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
    def get_resource_records_of_zone(self, zone_name, rr_type=types['ALL']):
        return self.service.getResourceRecordsOfZone(zoneName=zone_name,
                                                     rrType=rr_type)['ResourceRecord']

    def create_base_record(self, zone_name, host_name, rr_type, ttl=TTL):
        if type(rr_type) != int:
            record_type = types[rr_type]
        else:
            record_type = rr_type
        return {
            '_DName': host_name,
            '_TTL': ttl,
            '_ZoneName': zone_name,
            '_Type': record_type,
            'InfoValues': {}
        }

    @translate_exceptions
    def create_mx_record(self, zone_name, host_name, priority_value, mail_server, transaction_id=''):
        resource_record = self.create_base_record(zone_name, host_name, 'MX')
        resource_record['InfoValues']['_Info1Value'] = mail_server
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_a_record(self, zone_name, host_name, ip_address_v4, transaction_id=''):
        resource_record = self.create_base_record(zone_name, host_name, 'A')
        resource_record['InfoValues']['_Info1Value'] = ip_address_v4
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_txt_record(self, zone_name, host_name, char_str, transaction_id=''):
        resource_record = self.create_base_record(zone_name, host_name, 'TXT')
        resource_record['InfoValues']['_Info1Value'] = char_str
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_ns_record(self, zone_name, name_server, host_name, preference_value, transaction_id=''):
        resource_record = self.create_base_record(zone_name, host_name, 'NS')
        resource_record['InfoValues']['_Info1Value'] = name_server
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_soa_record(self, zone_name, host_name, contact_name, serial_number, refresh_duration, retry_duration, expire_limit, min_ttl, transaction_id=''):
        resource_record = self.create_base_record(zone_name, host_name, 'SOA')
        resource_record['InfoValues']['_Info1Value'] = host_name
        resource_record['InfoValues']['_Info2Value'] = contact_name
        resource_record['InfoValues']['_Info3Value'] = serial_number
        resource_record['InfoValues']['_Info4Value'] = refresh_duration
        resource_record['InfoValues']['_Info5Value'] = retry_duration
        resource_record['InfoValues']['_Info6Value'] = expire_limit
        resource_record['InfoValues']['_Info7Value'] = min_ttl
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def delete_all_records(self, zone_name, rr_type=types['ALL'], transaction_id=''):
        existing_records = [rec for rec in self.get_resource_records_of_zone(zone_name, rr_type)]
        results = []
        for rec in existing_records:
            gu_id = rec._Guid
            results.append(self.service.deleteResourceRecord(guid=gu_id,
                                                             trasactionID=transaction_id))
        return all(results)

    @translate_exceptions
    def delete_record(self, gu_id, transaction_id=''):
        return self.service.deleteResourceRecord(guid=gu_id,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def update_record(self, zone_name, gu_id, rr_type, host_name, ttl, infovalues, transaction_id=''):
        resource_record = {
            '_DName': host_name,
            'InfoValues': {}
        }

        resource_record['_Guid'] = gu_id
        resource_record['_Type'] = rr_type
        resource_record['_TTL'] = ttl

        str_prefix = 'resource_record[\"InfoValues\"][\"_'
        str_middle = '\"] = '

        # TODO: Clean up this for loop, so I don't use eval, or ** in the arguments
        for i in infovalues.keys():
            exec(str_prefix + i + str_middle + "\"" + infovalues[i] + "\"")

        result = False
        result = self.service.updateResourceRecord(resourceRecord=resource_record,
                                                   trasactionID=transaction_id)
        return result
