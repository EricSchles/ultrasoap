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
            code = e.fault.faultcode
            description = e.fault.faultstring
            cls = UDNS_ERRORS.get(code, UDNSException)
            raise cls(code, description)
    return wrapper

class DNSRecord(object):
    def __init__(self, zone_name, host_name, record_type):
        self._DName = host_name
        self._TTL = TTL
        if type(record_type) != int:
            self._Type = types[record_type]
        else:
            self._Type = record_type
        self._ZoneName = zone_name

        self.InfoValues = {}

    def as_instance(self):
        result = Client('http://testapi.ultradns.com/UltraDNS_WS/v01?wsdl').factory.create('ns5:ResourceRecord')
        result._DName = self._DName
        result._TTL = self._TTL
        result._Type = self._Type
        return result


    def parse_record_data(self, rr):
        raise NotImplementedError()

    def add_record(self):
        raise NotImplementedError()

    def delete_record(self):
        raise NotImplementedError()

    def __cmp__(self, other):
        return cmp(self._Type, other._Type)

    def interesting(self):
        return True

    def get_type(self):
        for record_type, record_intger_code in types.iteritems():
            if record_intger_code == self._Type:
                return record_type

    def as_dict(self):
        return {
            'HostName': self._DName,
            'TTL': self._TTL,
            'RecordType': self.get_type(),
            'ZoneName': self._ZoneName,
            'Interesting': self.interesting()
        }

class MXRecord(DNSRecord):
    def __init__(self, zone_name, host_name, priority_value, mail_server):
        super(DNSRecord, self).__init__(self, zone_name, host_name, 'MX')
        self.InfoValues._Info1Value = priority_value
        self.InfoValues._Info2Value = mail_server

    def parse_record_data(self, rr):
        self.InfoValues._Info1Value = rr.priority
        self.InfoValues._Info2Value = rr.mailserver.lower()

    def as_dict(self):
        base = super(DNSRecord, self).as_dict()
        base['PriorityValue'] = self.InfoValues._Info1Value
        base['MailServer'] = self.InfoValues._Info2Value
        return base

class ARecord(DNSRecord):
    def __init__(self, zone_name, host_name, ip_address_v4):
        super(DNSRecord, self).__init__(self, zone_name, host_name, 'A')
        self.InfoValues._Info1Value = ip_address_v4

    def parse_record_data(self, rr):
        self.InfoValues._Info1Value = rr.address.lower()

    def as_dict(self):
        base = super(DNSRecord, self).as_dict()
        base['IPAddress'] = self.InfoValues._Info1Value
        return base

class TXTRecord(DNSRecord):
    def __init__(self, zone_name, host_name, char_str):
        super(DNSRecord, self).__init__(self, zone_name, host_name, 'TXT')
        self.InfoValues._Info1Value = char_str

    def parse_record_data(self, rr):
        self.InfoValues._Info1Value = rr.char_str

    def as_dict(self):
        base = super(DNSRecord, self).as_dict()
        base['CharStr'] = self.InfoValues._Info1Value
        return base

class NSRecord(DNSRecord):
    def __init__(self, zone_name, host_name, name_server):
        super(DNSRecord, self).__init__(self, zone_name, host_name, 'NS')
        self.InfoValues._Info1Value = name_server

    def parse_record_data(self, rr):
        self.InfoValues._Info1Value = rr.name_server

    def as_dict(self):
        base = super(DNSRecord, self).as_dict()
        base['NameServer'] = self.InfoValues._Info1Value
        return base

class SOARecord(DNSRecord):
    def __init__(self, zone_name, host_name, contact_name, serial_number, refresh_duration, retry_duration, expire_limit, min_ttl):
        super(DNSRecord, self).__init__(self, zone_name, host_name, 'SOA')
        self.InfoValues._Info1Value = host_name
        self.InfoValues._Info2Value = contact_name
        self.InfoValues._Info3Value = serial_number
        self.InfoValues._Info4Value = refresh_duration
        self.InfoValues._Info5Value = retry_duration
        self.InfoValues._Info6Value = expire_limit
        self.InfoValues._Info7Value = min_ttl

    def parse_record_data(self, rr):
        self.InfoValues._Info1Value = rr.host_name
        self.InfoValues._Info2Value = rr.contact_name
        self.InfoValues._Info3Value = rr.serial_number
        self.InfoValues._Info4Value = rr.refresh_duration
        self.InfoValues._Info5Value = rr.retry_duration
        self.InfoValues._Info6Value = rr.expire_limit
        self.InfoValues._Info7Value = rr.min_ttl

    def as_dict(self):
        base = super(DNSRecord, self).as_dict()
        base['HostName'] = self.InfoValues._Info1Value
        base['ContactName'] = self.InfoValues._Info2Value
        base['SerialNumber'] = self.InfoValues._Info3Value
        base['RefreshDuration'] = self.InfoValues._Info4Value
        base['RetryDuration'] = self.InfoValues._Info5Value
        base['ExpireLimit'] = self.InfoValues._Info6Value
        base['MinTTL'] = self.InfoValues._Info7Value

        return base

    def interesting(self):
        return False

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
                                                     rrType=rr_type)

    @translate_exceptions
    def create_mx_record(self, zone_name, host_name, priority_value, mail_server, transaction_id=''):
        resource_record = MXRecord(self, zone_name, host_name, priority_value, mail_server)
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_a_record(self, zone_name, host_name, ip_address_v4, transaction_id=''):
        resource_record = ARecord(self, zone_name, host_name, ip_address_v4)
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_txt_record(self, zone_name, host_name, char_str, transaction_id=''):
        resource_record = TXTRecord(self, zone_name, host_name, char_str)
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_ns_record(self, zone_name, name_server, host_name, preference_value, transaction_id=''):
        resource_record = NSRecord(self, zone_name, host_name, name_server)
        resource_record.InfoValues._Info1Value = name_server
        return self.service.createResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)

    @translate_exceptions
    def create_soa_record(self, zone_name, host_name, contact_name, serial_number, refresh_duration, retry_duration, expire_limit, min_ttl, transaction_id=''):
        resource_record = SOARecord(self, zone_name, host_name, contact_name, serial_number, refresh_duration, retry_duration, expire_limit, min_ttl)
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
        resource_record = DNSRecord(zone_name, host_name, rr_type).as_instance()

        resource_record._Guid = gu_id
        resource_record._Type = rr_type
        resource_record._TTL = ttl

        str_prefix = 'resource_record.InfoValues[\"_'
        str_middle = '\"] = '

        # TODO: Clean up this for loop, so I don't use eval, or ** in the arguments
        for i in infovalues.keys():
            exec(str_prefix + i + str_middle + "\"" + infovalues[i] + "\"")

        result = False
        result = self.service.updateResourceRecord(resourceRecord=resource_record,
                                                 trasactionID=transaction_id)
        return result
