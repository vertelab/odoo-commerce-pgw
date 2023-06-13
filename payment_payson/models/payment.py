# -*- coding: utf-8 -*-
import json
import logging

import requests
from werkzeug import urls

import base64
import json
import requests
from odoo.http import request

from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_payson.controllers.main import PaysonController

_logger = logging.getLogger(__name__)


class AcquirerPayson(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('payson', 'Payson')], ondelete={'payson': 'set default'})

    payson_agent_id = fields.Char(string='Payer Agent ID', required_if_provider='payson')
    payson_email = fields.Char(string='Seller E-mail', required_if_provider='payson')
    payson_key = fields.Char(string='Payson Key', help='The payson key.', required_if_provider='payson')

    @api.model
    def _get_payson_urls(self, environment):
        if environment == 'enabled':
            return {
                'payson_form_url': 'https://api.payson.se/2.0',
            }
        else:
            return {
                'payson_form_url': 'https://test-api.payson.se/2.0',
            }

    def _payson_request(self, data=None, method='POST', endpoint=None):
        url = f"{self._get_payson_urls(environment=self.state)['payson_form_url']}{endpoint}"
        payson_agent_key = f"{self.payson_agent_id}:{self.payson_key}".encode()
        credential_str = base64.b64encode(payson_agent_key).decode('ascii')
        headers = {
            'Authorization': 'Basic %s' % credential_str,
            'Content-Type': 'application/json'
        }
        resp = requests.request(method, url, data=data, headers=headers)
        return resp.json()

    def payson_form_generate_values(self, tx_values):
        payson_tx_values = dict(tx_values)
        return payson_tx_values

    def _partner_split_name(self, partner_name):
        return [' '.join(partner_name.split()[-1:]), ' '.join(partner_name.split()[:-1])]

    def payson_get_form_action_url(self):
        self.ensure_one()
        last_tx_id = request.session.get('__website_sale_last_tx_id')
        order = request.website.sale_get_order()

        first_name = self._partner_split_name(order.partner_id.name)[0]
        last_name = self._partner_split_name(order.partner_id.name)[-1]

        #Currency can be SEK or EUR#
        currency_name = order.currency_id.name
        if currency_name != "EUR" and currency_name != "SEK":
           raise ValidationError(f"Only SEK or EUR are valid currency when using payson not {currency_name}")

        payment_data = {
            "merchant": {
                "checkoutUri": urls.url_join(self.get_base_url(), PaysonController._checkout_url),
                "confirmationUri": urls.url_join(self.get_base_url(), PaysonController._confirmation_url),
                "notificationUri": urls.url_join(self.get_base_url(), PaysonController._notification_url),
                "termsUri": urls.url_join(self.get_base_url(), PaysonController._term_url),
                "reference": order.name
            },
            "customer": {
                "email": order.partner_id.email,
                "firstName": first_name,
                "lastName": last_name,
                'city': order.partner_id.city,
                'countryCode': order.partner_id.country_id.code,
                'phone': order.partner_id.phone or order.partner_id.mobile,
                'postalCode': order.partner_id.zip,
                'street': order.partner_id.street,
                'type': 'person'
            },
            "order": {
                "currency": currency_name,
                "items": [
                    {
                        "name": line_item.product_id.name,
                        "reference": line_item.product_id.default_code or '',
                        "quantity": line_item.product_uom_qty,
                        "unitPrice": line_item.price_unit,
                        "taxRate": "",
                        "type": "physical" if line_item.product_id.type != "service" else "service",
                    } for line_item in order.order_line
                ]
            }
        }

        payment_request = self._payson_request(
            data=json.dumps(payment_data), endpoint='/checkouts', method='POST')

        if payment_request.get("status") == "created":
            self.env['payment.transaction'].browse(last_tx_id).write({
                'payson_transaction_id': payment_request.get("id"),
                'payson_transaction_status': payment_request.get("status"),
                'payson_transaction_snippet': payment_request.get("snippet"),
                'payson_expiration_time': payment_request.get("expirationDate")
            })
            redirect_url = urls.url_join(self.get_base_url(), PaysonController._checkout_url)
            return redirect_url


class TxPayson(models.Model):
    _inherit = 'payment.transaction'

    payson_expiration_time = fields.Datetime(string='Expiration Time', readonly=True)
    payson_transaction_id = fields.Char(string='Transaction ID', readonly=True)
    payson_purchase_id = fields.Char(string='Purchase ID', readonly=True)
    payson_transaction_snippet = fields.Text(string='Transaction Snippet', readonly=True)

    payson_transaction_status = fields.Selection([
        ('created', 'Created'),
        ('readyToPay', 'Ready To Pay'),
        ('readyToShip', 'Ready To Ship'),
        ('shipped', 'Shipped'),
        ('paidToAccount', 'Paid To Account'),
        ('expired', 'Expired'),
        ('canceled', 'Canceled'),
        ('denied', 'Denied')],
        string='Payson Status', help="""
                                Created - Set by Payson after the checkout has been created 
                                Ready To Pay - Set by Payson after all necessary customer information has been added.
                                Ready To Ship - Set by Payson after the customer has completed a payment or when an invoice can be sent.
                                Shipped - Set by the merchant to signal that the order has been shipped..
                                Paid To Account - Set by Payson when money has been paid out to the merchant´s account.
                                Expired - Set by Payson when expirationTime is reached for a checkout with status created (default 3 hours),
                                    or when the status readyToShip has been set for more than 59 days.
                                Canceled - Set by either the merchant or the customer.
                                    The customer is able to cancel the order before its status is set to readyToShip.
                                    The merchant is able to cancel the order before its status is set to shipped.
                                Denied - Payson will set the status to denied if the purchase is denied for any reason.""")
    total_fee_excluding_tax = fields.Float(string="Total Fee Excluding Tax", readonly=True)
    total_fee_including_tax = fields.Float(string="Total Fee Including Tax", readonly=True)
    total_price_excluding_tax = fields.Float(string="Total Price Excluding Tax", readonly=True)
    total_price_including_tax = fields.Float(string="Total Price Including Tax", readonly=True)
    total_tax_amount = fields.Float(string="Total Tax Amount", readonly=True)

    def _payson_payment_verification(self):
        """ Given a data dict coming from payson, verify it and find the related transaction record. """
        if self.payson_transaction_id:
            payment_data = self.acquirer_id.sudo()._payson_request(data=None, method='GET',
                                                                   endpoint=f"/Checkouts/{self.payson_transaction_id}")
            return payment_data
        else:
            error_msg = _('Payson: no order found for transaction id')
            raise ValidationError(error_msg)

    def _payson_checkout_get_tx_data(self):
        self.ensure_one()
        if self.state == 'pending':
            pass

        if self.state in ['cancel', 'error']:
            _logger.warning(
                'Payson: trying to validate a cancelled payment and order tx (ref %s)', self.payson_transaction_id)
            return True

        # if self.state != 'draft':
        #     _logger.warning('Payson: trying to validate an already validated tx (ref %s)', self.payson_transaction_id)
        #     return True

        payson_data = self._payson_payment_verification()

        payson_vals = {
            "payson_transaction_status": payson_data.get("status"),
            "payson_purchase_id": payson_data.get("purchaseId"),
            "total_fee_excluding_tax": payson_data.get("order")["totalFeeExcludingTax"],
            "total_fee_including_tax": payson_data.get("order")["totalFeeIncludingTax"],
            "total_price_excluding_tax": payson_data.get("order")["totalPriceExcludingTax"],
            "total_price_including_tax": payson_data.get("order")["totalPriceIncludingTax"],
            "total_tax_amount": payson_data.get("order")["totalTaxAmount"],
        }

        if payson_data.get("status") not in ["denied", "canceled", "expired"]:
            self.write(payson_vals)

            if payson_data.get("status") == "readyToShip":
                self._set_transaction_done()
            if payson_data.get("status") == "readyToPay":
                self._set_transaction_pending()

            if self.payment_token_id:
                self.payment_token_id.verified = True
            return True
        else:
            self.write({
                'state_message': "Customer Cancelled Order",
                "payson_transaction_status": payson_data.get("status"),
            })
            self._set_transaction_cancel()
            return False

    def _set_transaction_cancel(self):
        '''Move the transaction's payment to the cancel state(e.g. Paypal).'''
        allowed_states = ('draft', 'authorized')
        target_state = 'cancel'
        (tx_to_process, tx_already_processed, tx_wrong_state) = self._filter_transaction_state(
            allowed_states, target_state)
        if not tx_to_process:
            tx_to_process = self
        for tx in tx_already_processed:
            _logger.info('Trying to write the same state twice on tx (ref: %s, state: %s' % (tx.reference, tx.state))
        for tx in tx_wrong_state:
            _logger.warning('Processed tx with abnormal state (ref: %s, target state: %s, previous state %s, '
                            'expected previous states: %s)' % (tx.reference, target_state, tx.state, allowed_states))

        # Cancel the existing payments.
        tx_to_process.mapped('payment_id').action_cancel()
        tx_to_process.write({'state': target_state, 'date': fields.Datetime.now()})
        self.sale_order_ids.action_cancel()
        tx_to_process._log_payment_transaction_received()
