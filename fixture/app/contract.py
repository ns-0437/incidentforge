"""Public payload validation and canonicalization."""
import re


def identity(value):
    if not isinstance(value,str) or not re.fullmatch(r'[A-Za-z0-9_.:-]{1,160}',value):
        raise ValueError('invalid identity')
    return value


def integer(value):
    if type(value) is not int or not 0 < value <= 1_000_000_000:
        raise ValueError('positive bounded integer required')
    return value


def items(value):
    if not isinstance(value,list) or not 1<=len(value)<=32:
        raise ValueError('items required')
    totals={}
    for item in value:
        if set(item)!={'sku','qty'}:
            raise ValueError('item fields')
        sku=identity(item['sku'])
        totals[sku]=integer(totals.get(sku,0)+integer(item['qty']))
    return [{'sku':s,'qty':q} for s,q in sorted(totals.items())]


def money(body):
    currency=body['currency']
    if not isinstance(currency,str) or not re.fullmatch('[A-Z]{3}',currency):
        raise ValueError('currency must be three uppercase letters')
    return {'amount_cents':integer(body['amount_cents']), 'currency':currency}


def order_payload(body):
    if len(identity(body['client_request_id']))>64:
        raise ValueError('client request identity too long')
    return {'client_request_id':identity(body['client_request_id']),
            'customer_id':identity(body['customer_id']), 'items':items(body['items']), **money(body)}
