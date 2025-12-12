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
import pprint

import requests
from werkzeug.urls import url_join
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from odoo.addons.payment_swedbankpay import const

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ProviderSwedbankPay(models.Model):
    _inherit = 'payment.provider'

    code = fields.Selection(
        selection_add=[('swedbankpay', 'Swedbank Pay')], ondelete={'swedbankpay': 'set default'}
    )
    swedbankpay_merchant_id = fields.Char(
        'Swedbank Merchant ID', required_if_provider='swedbankpay'
    )
    swedbankpay_account_nr = fields.Char(
        'Merchant Account #', required_if_provider='swedbankpay'
    )
    swedbankpay_view = fields.Selection(
        string='SwedbankPay View', selection=[
            ('DIRECTDEBIT', 'DIRECTDEBIT'),  # (Direct bank) – SALE
            ('IDEAL', 'IDEAL'),  # (Direct bank) – SALE
            ('CPA', 'CPA'),  # (Norwegian and Swedish overcharged SMS) – SALE
            ('CREDITCARD', 'CREDITCARD'),  # (Credit Card) – AUTHORIZATION/SALE
            ('PX', 'PX'),  # (PayEx account, WyWallet) – AUTHORIZATION/SALE
            ('MICROACCOUNT', 'MICROACCOUNT'),  # (PayEx account, WyWallet) – AUTHORIZATION/SALE
            ('PAYPAL', 'PAYPAL'),  # (PayPal transactions) – AUTHORIZATION/SALE
            ('INVOICE', 'INVOICE'),  # (Ledger Service) – AUTHORIZATION/SALE
            ('EVC', 'EVC'),  # (Value code) – AUTHORIZATION/SALE
            ('LOAN', 'LOAN'),  # – AUTHORIZATION/SALE
            ('GC', 'GC'),  # (Gift card / generic card) – AUTHORIZATION/SALE
            ('CA', 'CA'),  # (Credit account) – AUTHORIZATION/SALE
            ('FINANCING', 'FINANCING'),  # – AUTHORIZATION/SALE
            ('CREDITACCOUNT', 'CREDITACCOUNT'),  # – AUTHORIZATION/SALE
            ('PREMIUMSMS', 'PREMIUMSMS'),  # – SALE
            ('SWISH', 'SWISH'),  # – SALE
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

    swedbankpay_key = fields.Char('Swedbank Key', required=False)

    def _swedbankpay_get_api_url(self):
        """ Return the API URL according to the provider state.

        Note: self.ensure_one()

        :return: The API URL
        :rtype: str
        """
        self.ensure_one()

        if self.state == 'enabled':
            return 'https://api.payex.com'
        else:
            return 'https://api.externalintegration.payex.com'
            

    def _swedbankpay_make_request(self, endpoint, payload=None, method='POST'):
        """ Make a request to Swedbankpay API at the specified endpoint.
        Note: self.ensure_one()
        :param str endpoint: The endpoint to be reached by the request.
        :param dict payload: The payload of the request.
        :param str method: The HTTP method of the request.
        :return The JSON-formatted content of the response.
        :rtype: dict
        :raise ValidationError: If an HTTP error occurs.
        """
        self.ensure_one()
        url = url_join(self._swedbankpay_get_api_url(), endpoint)
        #headers = {'Authorization': f'Bearer {self.swedbankpay_key}', 'Content-Type': 'application/json;version=3.1'}
        #swedbankpay_account_nr
        headers = {'Authorization': f'Bearer {self.swedbankpay_account_nr}', 'Content-Type': 'application/json;version=3.1'}
        try:
            if method == 'GET':
                response = requests.get(url, params=payload, headers=headers, timeout=10)
            else:
                response = requests.post(url, data=payload, headers=headers, timeout=10)
            
            _logger.info("Response status: %s, content: %s", response.status_code, response.text)
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError:
                _logger.exception(
                    "Invalid API request at %s with data:\n%s\nResponse: %s", 
                    url, pprint.pformat(payload), response.text
                )
                _logger.warning(f"{headers=}")
                _logger.warning(f"{url=}")
                # Try to get error details from response
                error_message = "Unknown error"
                try:
                    error_data = response.json()
                    if 'detail' in error_data:
                        error_message = error_data['detail']
                    elif 'title' in error_data:
                        error_message = error_data['title']
                    elif 'message' in error_data:
                        error_message = error_data['message']
                    else:
                        error_message = str(error_data)
                except (ValueError, KeyError):
                    error_message = response.text or f"HTTP {response.status_code} error"
                
                raise ValidationError("Swedbankpay: " + _(
                    "The communication with the API failed. Error: %s", error_message
                ))
                
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            _logger.exception("Unable to reach endpoint at %s", url)
            raise ValidationError(
                "Swedbankpay: " + _("Could not establish the connection to the API.")
            )
        
        return response.json()

