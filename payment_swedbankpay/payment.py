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

import logging
_logger = logging.getLogger(__name__)

class AcquirerPayex(models.Model):
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

    swedbankpay_key = fields.Char('Swedbank Key', required_if_provider='swedbankpay')
    swedbankpay_key = "example_swedbank_paykey"

    
    @api.multi
    def xxxswedbankpay_form_generate_values(self, partner_values, tx_values):
        """Method that generates the values used to render the form button template."""
        self.ensure_one()
        return partner_values, tx_values

    @api.multi
    def swedbankpay_form_generate_values(self, values):
        """Method that generates the values used to render the form button template."""
        _logger.warn("Hello world!!! \n\n\n\n")
        # ~ base_url = 'rita.vertel.se'
        # ~ base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        base_url = request.httprequest.url_root
        _logger.warn("logger : base_url = %s \n\n\n\n\n\n\n\n" % base_url)
        
        swedbankpay_tx_values = dict(values)
        swedbankpay_tx_values.update({
            'Swd_merchant_id': self.swedbankpay_merchant_id,
            'Swd_account_nr': self.swedbankpay_account_nr,
            'Swd_view': self.swedbankpay_view,
            'Swd_currency': values['currency'] and values['currency'].name or '',
            'Swd_invoicenumber': values['reference'],
            'payeeId': tx.acquirer_id.swedbankpay_merchant_id,
            'payeeReference': tx.reference,
            'swedbankpayKey': tx.acquirer_id.swedbankpay_account_nr,
            'orderReference': tx.reference, #Should be some other reference? 
        })
        return swedbankpay_tx_values
    
    # ~ "payeeId": tx.acquirer_id.swedbankpay_merchant_id,
    # ~ "payeeReference": tx.reference,
        # ~ "payeeReference": tx.acquirer_id.swedbankpay_account_nr,
    # ~ "swedbankpayKey": tx.acquirer_id.swedbankpay_key,
        # ~ "payeeName": "xxxxx",
        # ~ "productCategory": "xxxxx",
    # ~ "orderReference": tx.reference,
    
    
    @api.multi
    def xxbuckaroo_form_generate_values(self, values):
        base_url = 'rita.vertel.se'
        buckaroo_tx_values = dict(values)
        buckaroo_tx_values.update({
            'Brq_websitekey': self.brq_websitekey,
            'Brq_amount': values['amount'],
            'Brq_currency': values['currency'] and values['currency'].name or '',
            'Brq_invoicenumber': values['reference'],
            'brq_test': False if self.environment == 'prod' else True,
            'Brq_return': urls.url_join(base_url, BuckarooController._return_url),
            'Brq_returncancel': urls.url_join(base_url, BuckarooController._cancel_url),
            'Brq_returnerror': urls.url_join(base_url, BuckarooController._exception_url),
            'Brq_returnreject': urls.url_join(base_url, BuckarooController._reject_url),
            'Brq_culture': (values.get('partner_lang') or 'en_US').replace('_', '-'),
            'add_returndata': buckaroo_tx_values.pop('return_url', '') or '',
        })
        buckaroo_tx_values['Brq_signature'] = self._buckaroo_generate_digital_sign('in', buckaroo_tx_values)
        return buckaroo_tx_values

    @api.multi
    def xxsips_form_generate_values(self, values):
        self.ensure_one()
        base_url = 'rita.vertel.se'
        currency = self.env['res.currency'].sudo().browse(values['currency_id'])
        currency_code = CURRENCY_CODES.get(currency.name, False)
        if not currency_code:
            raise ValidationError(_('Currency not supported by Wordline'))
        amount = round(values['amount'] * 100)
        if self.environment == 'prod':
            # For production environment, key version 2 is required
            merchant_id = getattr(self, 'sips_merchant_id')
            key_version = self.env['ir.config_parameter'].sudo().get_param('sips.key_version', '2')
        else:
            # Test key provided by Atos Wordline works only with version 1
            merchant_id = '002001000000001'
            key_version = '1'

        sips_tx_values = dict(values)
        sips_tx_values.update({
            'Data': u'amount=%s|' % amount +
                    u'currencyCode=%s|' % currency_code +
                    u'merchantId=%s|' % merchant_id +
                    u'normalReturnUrl=%s|' % urls.url_join(base_url, SipsController._return_url) +
                    u'automaticResponseUrl=%s|' % urls.url_join(base_url, SipsController._notify_url) +
                    u'transactionReference=%s|' % values['reference'] +
                    u'statementReference=%s|' % values['reference'] +
                    u'keyVersion=%s' % key_version,
            'InterfaceVersion': self.sips_version,
        })

        return_context = {}
        if sips_tx_values.get('return_url'):
            return_context[u'return_url'] = u'%s' % urls.url_quote(sips_tx_values.pop('return_url'))
        return_context[u'reference'] = u'%s' % sips_tx_values['reference']
        sips_tx_values['Data'] += u'|returnContext=%s' % (json.dumps(return_context))

        shasign = self._sips_generate_shasign(sips_tx_values)
        sips_tx_values['Seal'] = shasign
        return sips_tx_values    



    
    @api.multi
    def swedbankpay_get_form_action_url(self):
        """Returns the url of the button form."""
        return '/payment/swedbankpay/initPayment'
    
    @api.multi
    def swedbankpay_compute_fees(self, amount, currency_id, country_id):
        """TODO: Compute fees."""
        self.ensure_one()
        if not self.fees_active:
            return 0.0
        #~ currency = self.env['res.currency'].browse(currency_id)
        #~ if currency and currency.name == 'EUR':
            #~ fixed = self.fees_int_fixed
            #~ percentage = self.fees_int_var
        #~ elif currency and currency.name == 'SEK':
            #~ fixed = self.fees_dom_fixed
            #~ percentage = self.fees_dom_var
        #~ fees = (percentage / 100.0 * amount + fixed )
        #~ return fees
        return 0.0

class TxPayex(models.Model):
    _inherit = 'payment.transaction'
    
    @api.model
    def _payex_form_get_tx_from_data(self, data):
        ref = data.get('orderRef') or self._context.get('orderRef')
        if ref:
            return self.env['payment.transaction'].search([('acquirer_reference', '=', ref)])
    
    @api.model
    def _payex_form_get_invalid_parameters(self, tx, data):
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
    def _payex_form_validate(self, tx, data):
        if data.get('transactionStatus') not in ['0', '3']:
            return False
        return tx.write({'state': 'done', 'date_validate': fields.Datetime.now()})

    
    @api.model
    def payex_create(self, values):
        #acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        return values
