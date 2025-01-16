# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source Management Solution, third party addon
#    Copyright (C) 2020++ Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


import json
import logging

import dateutil.parser
import pytz
from werkzeug import urls

from odoo.http import request
from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_provider import ValidationError
from odoo.exceptions import ValidationError
#from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.tools.float_utils import float_compare

from odoo.http import request

import logging

_logger = logging.getLogger(__name__)

import pprint
import requests


class ProviderSwedbankPay(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(selection_add=[('swedbankpay', 'Swedbank Pay')], ondelete={'swedbankpay': 'set default'})
    swedbankpay_merchant_id = fields.Char('Swedbank Merchant ID', required_if_provider='swedbankpay')
    swedbankpay_account_nr = fields.Char('Merchant Account #', required_if_provider='swedbankpay')
    swedbankpay_view = fields.Selection(string='SwedbankPay View', selection=[
        ('DIRECTDEBIT', 'DIRECTDEBIT'),  #(Direct bank) – SALE
        ('IDEAL', 'IDEAL'),  #(Direct bank) – SALE
        ('CPA', 'CPA'),  #(Norwegian and Swedish overcharged SMS) – SALE
        ('CREDITCARD', 'CREDITCARD'),  #(Credit Card) – AUTHORIZATION/SALE
        ('PX', 'PX'),  #(PayEx account, WyWallet) – AUTHORIZATION/SALE
        ('MICROACCOUNT', 'MICROACCOUNT'),  #(PayEx account, WyWallet) – AUTHORIZATION/SALE
        ('PAYPAL', 'PAYPAL'),  #(PayPal transactions) – AUTHORIZATION/SALE
        ('INVOICE', 'INVOICE'),  #(Ledger Service) – AUTHORIZATION/SALE
        ('EVC', 'EVC'),  #(Value code) – AUTHORIZATION/SALE
        ('LOAN', 'LOAN'),  #– AUTHORIZATION/SALE
        ('GC', 'GC'),  #(Gift card / generic card) – AUTHORIZATION/SALE
        ('CA', 'CA'),  #(Credit account) – AUTHORIZATION/SALE
        ('FINANCING', 'FINANCING'),  #– AUTHORIZATION/SALE
        ('CREDITACCOUNT', 'CREDITACCOUNT'),  #– AUTHORIZATION/SALE
        ('PREMIUMSMS', 'PREMIUMSMS'),  #– SALE
        ('SWISH', 'SWISH'),  #– SALE
    ], default='CREDITCARD', help="""Default payment method.
Valid view types – And valid purchaseOperation for those views:
* DIRECTDEBIT (Direct bank) – SALE
* IDEAL (Direct bank) – SALE
* CPA (Norwegian and Swedish overcharged SMS) – SALE
* CREDITCARD (Credit Card) – AUTHORIZATION/SALE
* PX or MICROACCOUNT (PayEx account, WyWallet) – AUTHORIZATION/SALE
* PAYPAL (PayPal transactions) – AUTHORIZATION/SALE
* INVOICE (Ledger Service) – AUTHORIZATION/SALE
* EVC (Value code) – AUTHORIZATION/SALE
* LOAN – AUTHORIZATION/SALE
* GC (Gift card / generic card) – AUTHORIZATION/SALE
* CA (Credit account) – AUTHORIZATION/SALE
* FINANCING – AUTHORIZATION/SALE
* CREDITACCOUNT – AUTHORIZATION/SALE
* PREMIUMSMS – SALE
* SWISH – SALE""", required_if_provider='swedbankpay')

    swedbankpay_key = fields.Char('Swedbank Key', required_if_provider='swedbankpay')
    swedbankpay_key = "example_swedbank_paykey_artur_example"

    def swedbankpay_form_generate_values_depricated(self, values):
        _logger.warn("~ %s " % "swedbankpay_form_generate_values")
        base_url = request.httprequest.url_root

        currency_name = self.env['res.currency'].search([
            ("id", "=", str(values['currency_id']))
        ]).name

        sale_order_id = str(values['reference']).split("-")[0]
        sale_order_amount_tax = self.env['sale.order'].search([
            ('name', '=', sale_order_id)
        ]).amount_tax

        swedbankpay_tx_values = dict(values)

        _logger.warning("~ SWEDBANKPAY FORM GENERATE VALUE %s " % swedbankpay_tx_values)

        swedbankpay_tx_values.update({
            'swd_currency_name': str(currency_name),
            'Swd_amount': int(values['amount'] * 100),
            'swd_vatAmount': int(sale_order_amount_tax * 100),
            'swd_refernce': values['reference'],
            'test': 'TEST_VAL'

            # 'Swd_merchant_id': self.swedbankpay_merchant_id,
            # 'Swd_account_nr': self.swedbankpay_account_nr,
            # 'Swd_view': self.swedbankpay_view,
            # 'Swd_currency': values['currency'] and values['currency'].name or '',
            # 'Swd_invoicenumber': values['reference'],
            # 'payeeId': tx.acquirer_id.swedbankpay_merchant_id,
            # 'payeeReference': tx.reference,
            # 'swedbankpayKey': tx.acquirer_id.swedbankpay_account_nr,
            # 'orderReference': tx.reference, #Should be some other reference?
        })

        return swedbankpay_tx_values

    # TODO: Dont know if this can be used
    def swedbankpay_get_form_action_url_depricated(self):
        """Returns the url of the button form."""
        return '/payment/swedbankpay/init'

    # TODO: Compute fees?
    def swedbankpay_compute_fees_depricated(self, amount, currency_id, country_id):
        self.ensure_one()
        if not self.fees_active:
            return 0.0
        return 0.0


class TxSwedbankPay(models.Model):
    _inherit = 'payment.transaction'

    swedbankpay_transaction_uri = fields.Char('Swedbank pay transaction URI')

    def _get_processing_values(self):
        """ Return the values used to process the transaction.

        The values are returned as a dict containing entries with the following keys:

        - `provider_id`: The provider handling the transaction, as a `payment.provider` id.
        - `provider_code`: The code of the provider.
        - `reference`: The reference of the transaction.
        - `amount`: The rounded amount of the transaction.
        - `currency_id`: The currency of the transaction, as a `res.currency` id.
        - `partner_id`: The partner making the transaction, as a `res.partner` id.
        - Additional provider-specific entries.

        Note: `self.ensure_one()`

        :return: The processing values.
        :rtype: dict
        """
        self.ensure_one()
        _logger.warning("_get_processing_values" * 100)

        processing_values = {
            'provider_id': self.provider_id.id,
            'provider_code': self.provider_code,
            'reference': self.reference,
            'amount': self.amount,
            'currency_id': self.currency_id.id,
            'partner_id': self.partner_id.id,
        }
        _logger.warning(f"{processing_values=}")

        # Complete generic processing values with provider-specific values.
        processing_values.update(self._get_specific_processing_values(processing_values))
        _logger.info(
            "generic and provider-specific processing values for transaction with reference "
            "%(ref)s:\n%(values)s",
            {'ref': self.reference, 'values': pprint.pformat(processing_values)},
        )

        # Render the html form for the redirect flow if available.
        if self.operation in ('online_redirect', 'validation'):
            redirect_form_view = self.provider_id._get_redirect_form_view(
                is_validation=self.operation == 'validation'
            )
            if redirect_form_view:  # Some provider don't need a redirect form.
                rendering_values = self._get_specific_rendering_values(processing_values)
                _logger.info(
                    "provider-specific rendering values for transaction with reference "
                    "%(ref)s:\n%(values)s",
                    {'ref': self.reference, 'values': pprint.pformat(rendering_values)},
                )
                redirect_form_html = self.env['ir.qweb']._render(redirect_form_view.id, rendering_values)
                processing_values.update(redirect_form_html=redirect_form_html)
        _logger.warning(f"2{processing_values=}")
        return processing_values

    def _get_specific_processing_values(self, processing_values):
        """ Return a dict of provider-specific values used to process the transaction.

        For a provider to add its own processing values, it must overwrite this method and return a
        dict of provider-specific values based on the generic values returned by this method.
        Provider-specific values take precedence over those of the dict of generic processing
        values.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """
        return dict()

    def _get_specific_rendering_values(self, processing_values):
        """ Return a dict of provider-specific values used to render the redirect form.

        For a provider to add its own rendering values, it must overwrite this method and return a
        dict of provider-specific values based on the processing values (provider-specific
        processing values included).

        :param dict processing_values: The processing values of the transaction.
        :return: The dict of provider-specific rendering values.
        :rtype: dict
        """
        return dict()

    def _get_mandate_values(self):
        """ Return a dict of module-specific values used to create a mandate.

        For a module to add its own mandate values, it must overwrite this method and return a dict
        of module-specific values.

        Note: `self.ensure_one()`

        :return: The dict of module-specific mandate values.
        :rtype: dict
        """
        self.ensure_one()
        return dict()

    def _send_payment_request(self):
        """ Request the provider handling the transaction to make the payment.

        This method is exclusively used to make payments by token, which correspond to both the
        `online_token` and the `offline` transaction's `operation` field.

        For a provider to support tokenization, it must override this method and make an API request
        to make a payment.

        Note: `self.ensure_one()`

        :return: None
        """
        self.ensure_one()
        self._ensure_provider_is_not_disabled()
        self._log_sent_message()

    @api.model
    def _swedbankpay_form_get_tx_from_data_depricated(self, data):
        ref = data.get('orderRef') or self._context.get('orderRef')
        if ref:
            return self.env['payment.transaction'].search(
                [('acquirer_reference', '=', ref)])

    def _swedbankpay_form_get_invalid_parameters_depricated(self, tx, data):
        invalid_parameters = []
        status = data.get('status')
        if not status:
            invalid_parameters.append(('status', 'None', "A value"))
            return invalid_parameters
        tx.state_message = status.get('description')
        if not status.get('errorCode'):
            invalid_parameters.append(('status[errorCode]', 'None', "A value"))
        elif status.get('errorCode') != 'OK':
            invalid_parameters.append(('status[errorCode]', status.get('errorCode'), "OK"))
        if not data.get('transactionStatus'):
            invalid_parameters.append(('transactionStatus', 'None', 'A value'))
        return invalid_parameters

    def _swedbankpay_form_validate_depricated(self, tx, data):
        if data.get('transactionStatus') not in ['0', '3']:
            return False
        return tx.write({'state': 'done', 'date_validate': fields.Datetime.now()})

    def swedbankpay_create_depricated(self, values):
        #acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        return values
