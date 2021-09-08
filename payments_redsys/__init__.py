# Copyright (C) 2018 AJ Ostergaard
#
# This file is part of django-payments-redsys.
#
# django-payments-redsys is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# django-payments-redsys is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with django-payments-redsys.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import zeep
import hashlib
import datetime
import json
import re
import xmltodict

import base64
import hmac
import pyDes

from codecs import encode

from django.http import HttpResponse
from django.shortcuts import redirect

from payments.forms import PaymentForm
from payments.core import BasicProvider, get_base_url, urljoin
from payments import PaymentError

from django import forms

import logging
logger = logging.getLogger('payments_redsys')

def compute_signature(salt, payload, key):
    '''
    For Redsys:
        salt = order number (Ds_Order or Ds_Merchant_Order)
        payload = Ds_MerchantParameters
        key = shared secret (aka key) from the Redsys Administration Module
              (Merchant Data Query option in the "See Key" section)
    '''
    bkey = base64.b64decode(key)
    des3 = pyDes.triple_des(bkey, mode=pyDes.CBC, IV='\0' * 8, pad='\0', padmode=pyDes.PAD_NORMAL)
    pepper = des3.encrypt(str(salt))
    payload_hash = hmac.new(pepper, payload, hashlib.sha256).digest()
    return base64.b64encode(payload_hash)

def compare_signatures(sig1, sig2):
    alphanumeric_characters = re.compile('[^a-zA-Z0-9]')
    sig1safe = re.sub(alphanumeric_characters, '', sig1)
    sig2safe = re.sub(alphanumeric_characters, '', sig2)
    return sig1safe == sig2safe

class RedsysResponseForm(forms.Form):
    Ds_SignatureVersion = forms.CharField(max_length=256)
    Ds_Signature = forms.CharField(max_length=256)
    Ds_MerchantParameters = forms.CharField(max_length=2048)

# TODO: Will be great to reach the endpoint just using "real" or "pruebas", but will be a major update
REDSYS_ENVIRONMENTS = {
    "real": "https://sis.redsys.es",
    "pruebas": "https://sis-t.redsys.es:25443",
}

class RedsysProvider(BasicProvider):
    def __init__(self, *args, **kwargs):
        self.merchant_code = kwargs.pop('merchant_code')
        self.terminal = kwargs.pop('terminal')
        self.shared_secret = kwargs.pop('shared_secret')
        self.currency = kwargs.pop('currency', '978')
        self.direct_payment = str(kwargs.pop('direct_payment', False)).upper()

        # Get provided endpoint base domain or REDSYS.pruebas env
        self.endpoint = urljoin(
            kwargs.pop('endpoint', REDSYS_ENVIRONMENTS.get('pruebas')),
            "",
        )
        assert self.endpoint in REDSYS_ENVIRONMENTS.values(), \
            "Provided Redsys endpoint '{}' is not valid".format(self.endpoint)

        self.order_number_prefix = kwargs.pop('order_number_prefix','0000')
        self.signature_version = kwargs.pop('signature_version','HMAC_SHA256_V1')
        #TODO self.button_image = '/static/images/payment_button.jpg'
        super(RedsysProvider, self).__init__(*args, **kwargs)

    @property
    def endpoint_form(self):
        return "{}/sis/realizarPago".format(self.endpoint)

    @property
    def endpoint_wsdl(self):
        return "{}/sis/services/SerClsWSEntrada/wsdl/SerClsWSEntrada.wsdl".format(self.endpoint)

    def post(self, *args, **kwargs):
        client = zeep.Client(*args) 
        return client.service.trataPeticion(kwargs.get('data', {}))

    def get_hidden_fields(self, payment):
        #site = Site.objects.get_current()
        order_number = '%s%d' % (self.order_number_prefix,payment.pk)
        amount = str(int(payment.total * 100)) # price is in cents
        # switch to payment.get_total_price() at some point
        # returns a TaxedMoney from 'prices'
        # need the gross element of TaxedMoney
        # also switch to amount.quantize(CENTS, rounding=ROUND_HALF_UP)
        merchant_data = {
            "DS_MERCHANT_AMOUNT": amount,
            "DS_MERCHANT_ORDER": order_number,
            "DS_MERCHANT_MERCHANTCODE": self.merchant_code,
            "DS_MERCHANT_DIRECTPAYMENT": self.direct_payment,
            "DS_MERCHANT_CURRENCY": self.currency,
            "DS_MERCHANT_TRANSACTIONTYPE": '0',
            "DS_MERCHANT_TERMINAL": self.terminal,
            "DS_MERCHANT_MERCHANTURL": self.get_return_url(payment),
            "DS_MERCHANT_URLOK": urljoin(get_base_url(), payment.get_success_url()),
            "DS_MERCHANT_URLKO": urljoin(get_base_url(), payment.get_failure_url()),
            "Ds_Merchant_ConsumerLanguage": '002',
        }
        json_data = json.dumps(merchant_data)
        b64_params = base64.b64encode(json_data.encode())
        signature = compute_signature(str(order_number), b64_params, self.shared_secret)
        data = {
            'Ds_SignatureVersion': self.signature_version,
            'Ds_MerchantParameters': b64_params.decode(),
            'Ds_Signature': signature.decode(),
        }
        return data

    def refund(self, payment, amount=None):
        """
        It requests a refund to Redsys using their Webservices layer

        More information about the process and the error codes at
        https://canales.redsys.es/canales/ayuda/documentacion/Manual%20integracion%20para%20conexion%20por%20Web%20Service.pdf
        """
        refund_amount = amount or payment.captured_amount
        # cents = str(int(
        #     refund_amount.quantize(CENTS, rounding=ROUND_HALF_UP)) * 100
        # )
        cents = str(int(refund_amount * 100))
        order_number = '%s%d' % (self.order_number_prefix, payment.pk)
        merchant_data = {
            "DS_MERCHANT_AMOUNT": cents,
            "DS_MERCHANT_ORDER": order_number,
            "DS_MERCHANT_MERCHANTCODE": self.merchant_code,
            "DS_MERCHANT_DIRECTPAYMENT": self.direct_payment,
            "DS_MERCHANT_CURRENCY": self.currency,
            "DS_MERCHANT_TRANSACTIONTYPE": '3',
            "DS_MERCHANT_TERMINAL": self.terminal,
            "DS_MERCHANT_MERCHANTURL": self.get_return_url(payment),
        }

        # Prepare the signature
        signature_data = xmltodict.unparse(
            {"DATOSENTRADA": merchant_data},
            full_document=False,
        )
        b64_params = base64.b64encode(signature_data.encode())
        signature = compute_signature(
            str(order_number),
            signature_data.encode(), 
            self.shared_secret
        )

        # Prepare the resultant XML
        data = {
            "REQUEST": {
                "DATOSENTRADA": merchant_data,
                'DS_SIGNATUREVERSION': self.signature_version,
                'DS_SIGNATURE': signature.decode(),
            },
        }
        data_xml = xmltodict.unparse(data)
        response = self.post(
            self.endpoint_wsdl,
            data=data_xml,
        )

        # Validate the response
        response_code = None
        try:
            response_dict = xmltodict.parse(response)
            response_code = response_dict.get('RETORNOXML', {}).get('CODIGO', False)

            parsed_code = int(response_code)
            if 0 <= parsed_code < 100 \
                or parsed_code == 400 \
                or parsed_code == 900:
                return refund_amount
        except:
            # Wait to raise 
            pass

        raise PaymentError("Redsys error '{}'".format(response_code or "non matched response"))

    def get_form(self, payment, data=None):
        return PaymentForm(self.get_hidden_fields(payment),
                           self.endpoint_form, self._method)

    def process_data(self, payment, request):
        form = RedsysResponseForm(request.POST)
        if form.is_valid():
            logger.debug('processing payment gateway response for payment %d' % payment.pk)
            order_number = '%s%d' % (self.order_number_prefix, payment.pk)
            signature = compute_signature(order_number,
                                          form.cleaned_data['Ds_MerchantParameters'].encode(),
                                          self.shared_secret)

            if not compare_signatures(signature.decode(), form.cleaned_data['Ds_Signature']):
                logger.debug('signature mismatch - possible attack')
                return HttpResponse()

            binary_merchant_parameters = base64.b64decode(form.cleaned_data['Ds_MerchantParameters'])
            merchant_parameters = json.loads(binary_merchant_parameters.decode())
            transaction_type = merchant_parameters['Ds_TransactionType']
            response_code = int(merchant_parameters['Ds_Response'])

            if response_code < 100:
                # Authorised transaction for payments and preauthorisations
                if transaction_type == '0':
                    payment.captured_amount = int(merchant_parameters['Ds_Amount']) / 100
                    payment.transaction_id = merchant_parameters['Ds_AuthorisationCode']
                    payment.extra_data = merchant_parameters
                    payment.change_status('confirmed')
                    logger.debug('payment %d confirmed' % payment.pk)
                elif transaction_type == '1':
                    payment.extra_data = merchant_parameters
                    payment.change_status('preauth')
                    logger.debug('payment %d preauthorised' % payment.pk)
                else:
                    logger.debug('authorised payment response but unrecognised transaction type %s' % transaction_type)

            if response_code == 900:
                # Authorised transaction for refunds and confirmations
                if transaction_type == '3':
                    payment.extra_data = merchant_parameters
                    payment.change_status('refunded')
                    logger.debug('payment %d automatic refund' % payment.pk)
                else:
                    logger.debug('authorised refund response but unrecognised transaction type %s' % transaction_type)

            if response_code > 100 and response_code != 900:
                # any of a long list of errors/rejections
                payment.extra_data = merchant_parameters
                payment.change_status('rejected', message='Ds_Response was %d' % response_code)
                # perhaps import and raise PaymentError from django-payments
                logger.debug('rejected: %s' % binary_merchant_parameters.decode())

        return HttpResponse()
