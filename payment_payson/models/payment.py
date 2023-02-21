# -*- coding: utf-8 -*-
import json
import logging

import dateutil.parser
import pytz
import requests
from werkzeug import urls

import hashlib
import base64
import json
import requests
from datetime import datetime
import calendar
from random import choices
import hmac
import string
from odoo.http import request
import pprint

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.tools.float_utils import float_compare


_logger = logging.getLogger(__name__)


def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]


class AcquirerPayson(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[
        ('payson', 'Payson')
    ], ondelete={'payson': 'set default'})

    payson_agent_id = fields.Char(string='Payer Agent ID',
                                  required_if_provider='payson')
    payson_email = fields.Char(string='Seller E-mail',
                               required_if_provider='payson')
    payson_key = fields.Char(string='Payson Key',
                             help='The preshared key.', required_if_provider='payson')
    payson_payment_method_card = fields.Boolean(
        string='Activate card payments',
        help='Unchecking all payment methods will use the default methods for your account.')
    payson_payment_method_bank = fields.Boolean(
        string='Activate bank payments',
        help='Unchecking all payment methods will use the default methods for your account.')
    payson_payment_method_sms = fields.Boolean(
        string='Activate SMS payments',
        help='Unchecking all payment methods will use the default methods for your account.')
    payson_payment_method_invoice = fields.Boolean(
        string='Activate invoice payments',
        help='Unchecking all payment methods will use the default methods for your account.')
    payson_return_address = fields.Char(
        string='Success return address',
        help='Default return address when payment is successful.',
        default='/shop/payment/validate',
        required_if_provider='payson')
    payson_cancel_address = fields.Char(
        string='Cancellation return address',
        help='Default return address when payment is cancelled.',
        default='/shop/payment', required_if_provider='payson')
    payson_application_id = fields.Char(string='Application ID')
    payson_fees_payer = fields.Selection(
        selection=[('PRIMARYRECEIVER', 'Store'), ('SENDER', 'Customer')],
        string='Fees Payer', default='PRIMARYRECEIVER')
    payson_guarantee = fields.Selection(
        string='',
        selection=[('OPTIONAL', 'Optional'), ('REQUIRED', 'Required'), ('NO', 'No')],
        default='OPTIONAL')
    payson_show_receipt = fields.Boolean(string='Show receipt at checkout', default=True)

    @api.model
    def _get_payson_urls(self, environment):
        if environment == 'enabled':
            return {
                'payson_form_url': 'https://api.payson.se/2.0/',
            }
        else:
            return {
                'payson_form_url': 'https://test-api.payson.se/2.0/',
            }

    def _payson_request(self, data=None, method='POST', endpoint=None):
        url = urls.url_join(self._get_payson_urls(environment=self.state)['payson_form_url'], endpoint)
        payson_agent_key = f"{self.payson_agent_id}:{self.payson_key}".encode()
        credential_str = base64.b64encode(payson_agent_key).decode('ascii')
        headers = {
            'Authorization': 'Basic %s' % credential_str,
            'Content-Type': 'application/json'
        }
        resp = requests.request(method, url, data=data, headers=headers)
        return resp

    def payson_get_form_action_url(self):
        self.ensure_one()
        last_tx_id = request.session.get('__website_sale_last_tx_id')

        payment_data = {
            'checkoutUri': "https://www.examplestore.com/checkout.php",
            "order": {
                "currency": "sek",
                "items": [
                    {
                        "name": "Test product",
                        "unitPrice": 399.00,
                        "quantity": 1.00,
                        "taxRate": 0.25
                     }
                  ]
               }
        }

        payment_request = self._payson_request(
            data=json.dumps(payment_data), endpoint='/checkout', method='POST')
        print(payment_request)


class TxPayson(models.Model):
    _inherit = 'payment.transaction'

    payson_payment_type = fields.Char(string='Payment type')
    payson_timestamp = fields.Char(string='Timestamp')
    payson_purchase_id = fields.Integer(string='Purchase ID')
    payson_status = fields.Char(selection=
                                [('CREATED', 'Created'),
                                 ('PENDING', 'Pending'),
                                 ('PROCESSING', 'Processing'),
                                 ('COMPLETED', 'Completed'),
                                 ('CREDITED', 'Cedited'),
                                 ('ERROR', 'Error'),
                                 ('REVERSALERROR', 'Reversalerror'),
                                 ('ABORTED', 'Aborted')],
                                string='Status', help="""
                                CREATED - The payment request was received and has been created in Payson's system. 
                                Funds will be transferred once approval is received.
                                PENDING - The sender has a pending transaction. A guarantee payment in progress has 
                                status pending. Please check guaranteeStatus for further details.
                                PROCESSING - The payment is in progress, check again later.
                                COMPLETED - The sender's transaction has completed.
                                CREDITED - The sender's transaction has been credited.
                                ERROR - The payment failed and all attempted transfers failed or all completed 
                                transfers were successfully reversed.
                                REVERSALERROR - One or more transfers failed when attempting to reverse a payment.
                                ABORTED - The payment was aborted before any money were transferred.""")

    payson_type = fields.Selection([('TRANSFER', 'Transfer'), ('INVOICE', 'Invoice')], string='Payment type')
    payson_invoice_status = fields.Char(string='Invoice Status')

