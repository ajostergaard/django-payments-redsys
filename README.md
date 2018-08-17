# django-payments-redsys

A Redsys~~Sermepa~~ payment gateway backend for [django-payments](https://github.com/mirumee/django-payments).

## Parameters

* merchant_code (required): Merchant Code - Redsys parameter.
* terminal (required): Terminal - Redsys parameter.
* shared_secret (required): Terminal Key - Redsys parameter.
  * "obtained by accessing the Administration Module, Merchant Data Query option in the 'See Key' section"
* currency (default:'978'): ISO-4217 currency code.
  * For example: EUR: '978', GBP: '826', USD: '840' (source: https://en.wikipedia.org/wiki/ISO_4217#Active_codes).
* endpoint (default:'https://sis-t.redsys.es:25443/sis/realizarPago': desired endpoint.
  * Sandbox endpoint is default. Production endpoint is https://sis.redsys.es/sis/realizarPago
* order_number_prefix (default:'0000'): Payment PK is suffixed to this to create Redsys order number
* signature_version (default:'HMAC_SHA256_V1'): Only supported signature type.


## settings.py

```python
PAYMENT_VARIANTS = {
    'redsys': ('payments_redsys.RedsysProvider', {
        'merchant_code': '123456789',
        'terminal': '1',
        'shared_secret': 'qwertyasdf0123456789',
    })
}

CHECKOUT_PAYMENT_CHOICES = [('redsys', 'Redsys')]

if any('redsys' in provider for provider in CHECKOUT_PAYMENT_CHOICES):
    INSTALLED_APPS.append('payments_redsys')
```
