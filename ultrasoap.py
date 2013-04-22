from contextlib import contextmanager
from functools import wraps

from suds import WebFault
from suds.client import Client
from suds.wsse import Security, UsernameToken

import ultratypes as types


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
