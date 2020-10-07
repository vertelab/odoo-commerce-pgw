# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
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
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.tools.float_utils import float_compare

from odoo.http import request

import logging
_logger = logging.getLogger(__name__)

import pprint
import requests

class AcquirerSwedbankPay(models.Model):
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('swedbankpay', 'Swedbank Pay')])
    swedbankpay_merchant_id = fields.Char('Swedbank Merchant ID', required_if_provider='swedbankpay')
    swedbankpay_account_nr = fields.Char('Merchant Account #', required_if_provider='swedbankpay')
    swedbankpay_view = fields.Selection(string='SwedbankPay View', selection=[
        ('DIRECTDEBIT', 'DIRECTDEBIT'), #(Direct bank) – SALE
        ('IDEAL', 'IDEAL'), #(Direct bank) – SALE
        ('CPA', 'CPA'), #(Norwegian and Swedish overcharged SMS) – SALE
        ('CREDITCARD', 'CREDITCARD'), #(Credit Card) – AUTHORIZATION/SALE
        ('PX', 'PX'), #(PayEx account, WyWallet) – AUTHORIZATION/SALE
        ('MICROACCOUNT', 'MICROACCOUNT'), #(PayEx account, WyWallet) – AUTHORIZATION/SALE
        ('PAYPAL', 'PAYPAL'), #(PayPal transactions) – AUTHORIZATION/SALE
        ('INVOICE', 'INVOICE'), #(Ledger Service) – AUTHORIZATION/SALE
        ('EVC', 'EVC'), #(Value code) – AUTHORIZATION/SALE
        ('LOAN', 'LOAN'), #– AUTHORIZATION/SALE
        ('GC', 'GC'), #(Gift card / generic card) – AUTHORIZATION/SALE
        ('CA', 'CA'), #(Credit account) – AUTHORIZATION/SALE
        ('FINANCING', 'FINANCING'), #– AUTHORIZATION/SALE
        ('CREDITACCOUNT', 'CREDITACCOUNT'), #– AUTHORIZATION/SALE
        ('PREMIUMSMS', 'PREMIUMSMS'), #– SALE
        ('SWISH', 'SWISH'), #– SALE
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


    @api.multi ## CODE TAKEN FROM CORE-ODOO // PAYPAL
    def swedbankpay_form_generate_values(self, values):
        base_url = self.get_base_url()

        swedbankpay_tx_values = dict(values)
        swedbankpay_tx_values.update({
            'cmd': '_xclick',
            'business': self.paypal_email_account,
            'item_name': '%s: %s' % (self.company_id.name, values['reference']),
            'item_number': values['reference'],
            'amount': values['amount'],
            'currency_code': values['currency'] and values['currency'].name or '',
            'address1': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').code or '',
            'state': values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            # ~ 'paypal_return': urls.url_join(base_url, PaypalController._return_url),
            # ~ 'notify_url': urls.url_join(base_url, PaypalController._notify_url),
            # ~ 'cancel_return': urls.url_join(base_url, PaypalController._cancel_url),
            'handling': '%.2f' % paypal_tx_values.pop('fees', 0.0) if self.fees_active else False,
            # ~ 'custom': json.dumps({'return_url': '%s' % paypal_tx_values.pop('return_url')}) if paypal_tx_values.get('return_url') else False,
        })
        return swedbankpay_tx_values

    swedbankpay_key = fields.Char('Swedbank Key', required_if_provider='swedbankpay')
    swedbankpay_key = "example_swedbank_paykey_artur_example"

    
    @api.multi
    def xxxswedbankpay_form_generate_values(self, partner_values, tx_values):
        """Method that generates the values used to render the form button template."""
        self.ensure_one()
        return partner_values, tx_values

    # 
    @api.multi
    def swedbankpay_form_generate_values(self, values):
        _logger.warn("~ %s " % "swedbankpay_form_generate_values")
        base_url = request.httprequest.url_root
        
        currency_name = self.env['res.currency'].search([
            ("id","=",str(values['currency_id']))
        ]).name

        sale_order_id = str(values['reference']).split("-")[0]
        sale_order_amount_tax = self.env['sale.order'].search([
            ('name','=',sale_order_id)
        ]).amount_tax

        swedbankpay_tx_values = dict(values)

        swedbankpay_tx_values.update({
            'swd_currency_name': str(currency_name), 
            'swd_amount' : int(values['amount'] * 100),
            'swd_vatAmount': int(sale_order_amount_tax * 100), 
            'swd_refernce' : values['reference']

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
    @api.multi
    def swedbankpay_get_form_action_url(self):
        """Returns the url of the button form."""
        return '/payment/swedbankpay/initPayment'
    
    """TODO: Compute fees?"""    
    @api.multi
    def swedbankpay_compute_fees(self, amount, currency_id, country_id):
        self.ensure_one()
        if not self.fees_active:
            return 0.0
        return 0.0

class TxSwedbankPay(models.Model):
    _inherit = 'payment.transaction'
    swedbankpay_transaction_uri = fields.Char('Swedbank pay transaction URI')
    
    @api.model
    def _swedbankpay_form_get_tx_from_data(self, data):
        ref = data.get('orderRef') or self._context.get('orderRef')
        if ref:
            return self.env['payment.transaction'].search([('acquirer_reference', '=', ref)])
    
    @api.model
    def _swedbankpay_form_get_invalid_parameters(self, tx, data):
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
    
    @api.model
    def _swedbankpay_form_validate(self, tx, data):
        if data.get('transactionStatus') not in ['0', '3']:
            return False
        return tx.write({'state': 'done', 'date_validate': fields.Datetime.now()})

    # ? 
    @api.model
    def swedbankpay_create(self, values):
        #acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        return values
