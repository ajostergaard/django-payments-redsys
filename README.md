# django-payments-redsys

A Redsys payment gateway backend for [django-payments](https://github.com/mirumee/django-payments).

> Redsys was previously known as Sermepa.

## Install

    pip install django-payments-redsys

## Configuration

Configure django payments with this provider by adding the following to `settings.py`:

```python
PAYMENT_VARIANTS = {
    'redsys': ('payments_redsys.RedsysProvider', {
        'merchant_code': '123456789',
        'terminal': '1',
        'shared_secret': 'qwertyasdf0123456789',
    })
}
```

Here's a list with all available options:

- `merchant_code` (required): Merchant Code - Redsys parameter.
- `terminal` (required): Terminal - Redsys parameter.
- `shared_secret` (required): Terminal Key - Redsys parameter.
  - "obtained by accessing the Administration Module, Merchant Data Query option in the 'See Key' section"
- `currency` (default:`'978'`): ISO-4217 currency code.
  - For example: EUR: '978', GBP: '826', USD: '840' (source: https://en.wikipedia.org/wiki/ISO_4217#Active_codes).
  - May also use some textual currency codes like e.g. `'EUR'`, `'GBP'`... - see source code for full list
- `environment`: (default: `"test"`, other valid option is `"real"`).
  - `test` will use https://sis-t.redsys.es:25443
  - `real` (Production) will use https://sis.redsys.es
- `order_number_prefix` (optional, default: `'0000'`): Payment PK is suffixed to this to create Redsys order number
- `signature_version` (default: `'HMAC_SHA256_V1'`): Only supported signature type.
- `direct_payment` (default: `False`): True or False
  - redsys (spanish) related doc: https://pagosonline.redsys.es/oneclick.html
- `process_on_redirect` (default: `False`): whether the payment will also be processed upon redirect (see explanation below)

### `process_on_redirect` and testing environments

Once a payment has been made, Redsys provides the payment data twice: once via a POST to a webhook endpoint (while still within the Redsys website), and later upon redirect as GET querystring arguments. The latter is particularly convenient during local development, as Redsys won't be able to call a "localhost" webhook. When setting `process_on_redirect` to `True`, his Redsys provider will process the payment upon redirect, before finally redirecting to your `success_url`/`failure_url` - this way you can test the whole payment flow end to end without needing to set up some sort of reverse proxy.

Our recommendation is to do something like this in your `settings.py`:

```python
import os
ENVIRONMENT = os.getenv("ENVIRONMENT", "dev")
PAYMENT_VARIANTS = {
    "redsys": (
        "payments_redsys.RedsysProvider",
        {
            # ...
            "process_on_redirect": ENVIRONMENT == "dev",
        },
    )
}
```

> `process_on_redirect` can also be convenient in other situations (e.g. private intranets) where your application is not accessible via the public internet.

Besides this, as already mentioned above, Redsys has a test environment and provides some test credit card numbers you may use.
Check out [Tarjetas y entornos de prueba](https://pagosonline.redsys.es/desarrolladores-inicio/integrate-con-nosotros/tarjetas-y-entornos-de-prueba/) (spanish) for details.

### About order numbers

Redsys requires your payments to include an order number (alphanumeric, 4 to 12 chars) that must be unique per merchant.

With this `RedsysProvider` you can either include an `order_number` in your Payment model (field or property), or a default one will be generated based on the setting `order_number_prefix` and the payment instance's primary key.

## Sample project

This repo contains the seed of sample project that you can look at for inspiration and reference. It is a minimalistic django project, it has enough to be used in automated tests. You can also run it with `just sample-app`.

## Contributing to this codebase

You may use the `Justfile` tool to run most commands in the development workflow (run the sample app, tests, etc.). Call `just` on a terminal to see all available options.

We use `poetry` and `pyproject.toml`. Get set up and check that things work with:

```sh
poetry install
just test
```

## Credits

- Copyright (C) 2018 AJ Ostergaard
- Additional contributions by Carles Barrobés

This code is published as free software. See `pyproject.toml` for details about the license.
