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

import logging
_logger = logging.getLogger(__name__)

from openerp import models, fields, api, _, tools
import hashlib

class AcquirerSumup(models.Model):
    _inherit = 'payment.acquirer'
    
    def _sumup_appid(self):
        self.sumup_appid = hashlib.sha224(self.env['ir.config_parameter'].get_param('database.uuid')).hexdigest()
    sumup_appid = fields.Char('Application identifier', compute='_sumup_appid',required_if_provider='sumup',help="Register this application identifier with SumUp https://me.sumup.com/developers")
    sumup_key = fields.Char('Key', required_if_provider='sumup',help="Record this key from https://me.sumup.com/developers when you have added the application identifier")
    sumup_view = fields.Selection(string='SumUp View', selection=[
        ('DIRECTDEBIT', 'DIRECTDEBIT'), #(Direct bank) – SALE
        ('IDEAL', 'IDEAL'), #(Direct bank) – SALE
        ('CPA', 'CPA'), #(Norwegian and Swedish overcharged SMS) – SALE
        ('CREDITCARD', 'CREDITCARD'), #(Credit Card) – AUTHORIZATION/SALE
        ('PX', 'PX'), #(SumUp account, WyWallet) – AUTHORIZATION/SALE
        ('MICROACCOUNT', 'MICROACCOUNT'), #(SumUp account, WyWallet) – AUTHORIZATION/SALE
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
* PX or MICROACCOUNT (SumUp account, WyWallet) – AUTHORIZATION/SALE
* PAYPAL (PayPal transactions) – AUTHORIZATION/SALE
* INVOICE (Ledger Service) – AUTHORIZATION/SALE
* EVC (Value code) – AUTHORIZATION/SALE
* LOAN – AUTHORIZATION/SALE
* GC (Gift card / generic card) – AUTHORIZATION/SALE
* CA (Credit account) – AUTHORIZATION/SALE
* FINANCING – AUTHORIZATION/SALE
* CREDITACCOUNT – AUTHORIZATION/SALE
* PREMIUMSMS – SALE
* SWISH – SALE""", required_if_provider='sumup')
    
    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerSumup, self)._get_providers(cr, uid,
            context=context)
        providers.append(['sumup', 'SumUp'])
        return providers
    
    def sumup_form_generate_values(self, partner_values, tx_values):
        """Method that generates the values used to render the form button template."""
        self.ensure_one()
        return partner_values, tx_values
    
    def sumup_get_form_action_url(self):
        """Returns the url of the button form."""
        return '/payment/sumup/initPayment'
    
    def sumup_compute_fees(self, amount, currency_id, country_id):
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

class TxSumup(models.Model):
    _inherit = 'payment.transaction'
    
    @api.model
    def _sumup_form_get_tx_from_data(self, data):
        ref = data.get('orderRef') or self._context.get('orderRef')
        if ref:
            return self.env['payment.transaction'].search([('acquirer_reference', '=', ref)])
    
    @api.model
    def _sumup_form_get_invalid_parameters(self, tx, data):
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
    def _sumup_form_validate(self, tx, data):
        if data.get('transactionStatus') not in ['0', '3']:
            return False
        return tx.write({'state': 'done', 'date_validate': fields.Datetime.now()})

    
    @api.model
    def sumup_create(self, values):
        #acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        return values
