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
import os

import dateutil.parser
import pytz
from werkzeug import urls


from odoo import api, fields, models, _
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.tools.float_utils import float_compare

import swish

### For testing ####

from random import randint
import time
import requests

####################

import logging
_logger = logging.getLogger(__name__)


class AcquirerSwish(models.Model):
    _inherit = 'payment.acquirer'

    # TODO: Add fields for merchant_number, swish.key, and, cert.pem (they are hardcoded right now)
    # I dont know where we should such fields yet...
    # Can we even store files in fields?

    current_folder = os.path.dirname(os.path.abspath(__file__))
    cert_file_path = os.path.join(current_folder, "cert.pem")
    key_file_path = os.path.join(current_folder, "key.pem")
    cert = (cert_file_path, key_file_path) 
    verify_file_path = os.path.join(current_folder, "swish.pem")

    provider = fields.Selection(selection_add=[('swish', 'Swish')])
    
    @api.multi
    def swish_form_generate_values(self, values):
        """Method that generates the values used to render the form button template."""

        # Important to note, the transaction reference is gotten from these values
        swish_tx_values = dict(values)
        
        # self.create_swish_payment(values)
        _logger.warn("~ %s " % "swish_from_generate_values")
        self.create_fake_swish_call(values)
        return swish_tx_values

    # Redundant to use decorator ? 
    # @api.multi
    def swish_get_form_action_url(self):
        """Returns the url of the button form."""
        # Should use this custom swish later ?
        # return '/payment/swish/initPayment'
        return '/payment/process'
    
    @api.multi
    def swish_compute_fees(self, amount, currency_id, country_id):
        """TODO: Compute fees."""
        self.ensure_one()
        return 0.0


    def _format_transfer_data(self):
        post_msg = _('''<div>
<h3>Please use the following transfer details</h3>
<h4>%(bank_title)s</h4>
%(bank_accounts)s
<h4>Communication</h4>
<p>Please use the order name as communication reference.</p>
</div>''')  % {
        'bank_title': "RANDOM SWISH TITLE",
        'bank_accounts': "BANK ACCOUNT WOWOWOWOWWOW!!! ",
        }


    # Implementation taken from Wire Transfer for the create and write functions.
    # This type of implementaion may be redundant. 
    # Or we can use this hook for passing other data...
    # /usr/share/core-odoo/addons/payment_transfer/models/payment.py
    @api.model
    def create(self, values):
        """ Hook in create to create a default post_msg. This is done in create
        to have access to the name and other creation values. If no post_msg
        or a void post_msg is given at creation, generate a default one. """
        _logger.warn("~ CREATE AQUirer!!! ")

        if values.get('provider') == 'swish' and not values.get('post_msg'):
            _logger.warn("~ CREATE post msg get!!! ")
            values['post_msg'] = self._format_transfer_data()
        return super(AcquirerSwish, self).create(values)


    @api.multi
    def write(self, values):
        """ Hook in write to create a default post_msg. See create(). """
        if all(not acquirer.post_msg and acquirer.provider != 'swish' for acquirer in self) and values.get('provider') == 'swish':
            values['post_msg'] = self._format_transfer_data()
        return super(AcquirerSwish, self).write(values)


    @api.model
    def create_swish_payment(self, tx_val):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')    
        callback_url = base_url.replace('http', 'https') + '/payment/swish'
        currency = tx_val['currency'].name
        payer_alias = str(tx_val['partner_phone']).replace(' ','').replace('-','').replace('+','')

        current_folder = os.path.dirname(os.path.abspath(__file__))
        cert_file_path = os.path.join(current_folder, "cert.pem")
        key_file_path = os.path.join(current_folder, "key.pem")
        cert = (cert_file_path, key_file_path)
        verify = os.path.join(current_folder, "swish.pem")
        
        swish_client = swish.SwishClient(
            environment=swish.Environment.Test,
            merchant_swish_number='1231181189',
            cert=cert,
            verify=verify
        )

        swish_payment = swish_client.create_payment(
            payee_payment_reference = tx_val['reference'], # This reference is used in the transaction!
            callback_url = callback_url,
            payer_alias = payer_alias,
            amount = tx_val['amount'],
            currency = "SEK", #str(tx['currency_id'].name),
            message = 'Order '
        )

    @api.model
    def create_fake_swish_call(self, tx_val):
        callback_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url') + '/payment/swish'
        _logger.warn("~ callback_url %s" %  callback_url)
        payer_alias = str(tx_val['partner_phone']).replace(' ','').replace('-','').replace('+','')

        
        # Typical return data from swish
        # Date format: 'YYYY-MM-DDThh:mm:ssTZD'
        swish_data =  {
            'id': 'RANDOM_SWISH_ID',
            'payeePaymentReference': tx_val['reference'],
            'paymentReference': '8A5AA8BF2C074665A0A85B6B0E329AA5',
            'callbackUrl': 'https://swish.azzar.pl/payment/swish',
            'payerAlias': payer_alias,
            'payeeAlias': '1231181189',
            'currency': 'SEK',
            'message': 'Order ',
            'errorMessage': None,
            'status': 'PAID',
            'amount': str(tx_val['amount']),
            'dateCreated': '2020-09-04T14:00:45.748+0000',
            'datePaid': '2020-09-04T14:00:49.748+0000',
            'errorCode': None
        }

        transaction_registered = self.env['payment.transaction'].sudo().form_feedback(data=swish_data, acquirer_name='swish')

        if(transaction_registered):
            _logger.warning("~ Transaction is registered!!")


class TxPayex(models.Model):
    _inherit = 'payment.transaction'

    swish_transaction_id = fields.Char('Swish transaction id')
    swish_transaction_payment_reference = fields.Char('Swish payment reference')

    # Maybe add fields like: 
    # * swish_id
    # * swish_payment_reference
   
    # These functions are triggered by making a payment on the website "Betala nu"-knappen
    # Fucntions will be executed in this order: 
    #   1. _<acquirer-name>_form_get_tx_from_data
    #   2. _<acquirer-name>_form_get_invalid_parameters
    #   3. _<acquirer-name>__form_validate
    # For more information /usr/share/core-odoo/addons/payment/models/payment_acquirer.py 
    # in the function PaymentTransaction.form_feedback


    # Here we find the transaction that is connected to the sale order (sale cart)
    # This is done by looking after the reference that odoo generates for the sale order 
    # (the reference value is passed through _form_generate_values function)
    @api.model
    def _swish_form_get_tx_from_data(self, data):
        _logger.warn('~ _swish_form_get_tx_from_data  REFERENCE: %s  ' % data['payeePaymentReference'])        
        reference = data['payeePaymentReference']
        if not reference:
            error_msg = 'Swish: received data with missing reference (%s)' % reference
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Swish: received data for reference %s' % reference
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    # If there is any invalid_parameters the next function will not be executed.
    @api.model
    def _swish_form_get_invalid_parameters(self, data):
        _logger.warn(" ~ _swish_form_get_invalid_parameters %s " % "None!")

        invalid_parameters = []
        if not data['status']:
            invalid_parameters.append(('status', 'None', "A value"))
            return invalid_parameters
        if(data['status'] == 'ERROR'):
            invalid_parameters.append(('errorCode', data['errorCode'], 'None' ))
            invalid_parameters.append(('errorMessage', data['errorMessage'], 'None'))
        if(data['status'] == 'DECLINED'):
            invalid_parameters.append(('Declined', 'The payer declined to make the payment', ''))
        if(data['status'] == 'CANCELLED'):
            invalid_parameters.append((
                'Cancelled', 
                'The payment request was cancelled either by the merchant or by the payer via the merchant site.', 
                ''
            ))
        return invalid_parameters

            
    @api.model
    def _swish_form_validate(self, data):
        _logger.warn("~ _swish_form_validate  %s" % data )

        status = data['status']
        former_tx_state = self.state
        res = {
            'acquirer_reference': data['payeePaymentReference'],
            'swish_transaction_id': data['id'], 
            'swish_transaction_payment_reference': data['paymentReference']
        }

        if status in ['PAID']:
            try:
                date = dateutil.parser.parse(data['datePaid']).astimezone(pytz.utc)
                _logger.warn("~ %s" % date)
            except:
                date = fields.Datetime.now()

            res.update(date=date)
            self._set_transaction_done()
            if self.state == 'done' and self.state != former_tx_state:
                _logger.info('~ Validated swish payment for tx %s: set as done' % (self.reference))
                return self.write(res)
        
            _logger.warn("~ %s" % "End of swish validate returns true")  
            return True