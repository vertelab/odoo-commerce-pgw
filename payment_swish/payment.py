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
# import requests

####################

import logging
_logger = logging.getLogger(__name__)


class AcquirerSwish(models.Model):
    _inherit = 'payment.acquirer'

    current_folder = os.path.dirname(os.path.abspath(__file__))
    cert_file_path = os.path.join(current_folder, "cert.pem")
    key_file_path = os.path.join(current_folder, "key.pem")
    cert = (cert_file_path, key_file_path) 
    verify_file_path = os.path.join(current_folder, "swish.pem")

    # the swish lib requiers a file path to the file...
    # when reading in the file make it to text first then put in to the field? 
    provider = fields.Selection(selection_add=[('swish', 'Swish')])
    
    # swish_merchant_number = fields.Char('Merchant Account #', required_if_provider='swish')
    # swish_cert = fields.Char('Swish Cert', required_if_provider='swish')
    # swish_key = fields.Char('Swish Key', required_if_provider='swish')
    # swish_verify = fields.Char('Swish Root Verification', required_if_provider='swish')
    
    # swish_number = '123456789'
    # swish_cert = cert_file_path
    # swish_key = key_file_path
    # swish_verify = verify_file_path

    
    # >>>>>>  This function is never called, which is very important...  <<<<<
    @api.multi
    def swish_form_generate_values(self, values):
        """Method that generates the values used to render the form button template."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        swish_tx_values = dict(values)
        _logger.warn(' \n\n\n ---->>>  swish_form_generate_values ---->>>   %s \n\n\n ' % swish_tx_values)
        # What data to use i dont know...?
        
        # swish_tx_values.update({
        #     'swish_merchant_number': '12345678',
        #     'currency': values['currency'] and values['currency'].name or '',
        #     'invoicenumber': values['reference'],
        #     'swish_payee_refernce': swish_tx_values['partner_phone'],
        #     'payeeReference': swish_tx_values['reference'],
        #     'swishKey': self.swish_key, #Which data should be used???
        #     'swish_payee_phone': '12345678', # Replace this 
        #     'orderReference': swish_tx_values['reference'], #Should be some other reference?'
        #     'notify_url': urls.url_join(base_url, '/payment/swish/initPayment'),
        #     #'feedback_url' : '/payment/swish/initPayment'
        #     # 'custom': json.dumps({
        #         # 'feedback_url': '/payment/swish/initPayment' 
        #     # })
        # })

        # Here is one important thing that is happening is to send a reference, to swish...
        self.create_swish_payment(values)
        return swish_tx_values

    # Redundant to use decorator ? 
    # @api.multi
    def swish_get_form_action_url(self):
        """Returns the url of the button form."""
        return '/payment/swish/initPayment'
 
    
    @api.multi
    def swish_compute_fees(self, amount, currency_id, country_id):
        """TODO: Compute fees."""
        self.ensure_one()
        return 0.0

    # Implementation taken from Wire Transfer for the create and write functions.
    # This type of implementaion may be redundant. 
    # Or we can use this hook for passing other data...
    # /usr/share/core-odoo/addons/payment_transfer/models/payment.py
    @api.model
    def create(self, values):
        """ Hook in create to create a default post_msg. This is done in create
        to have access to the name and other creation values. If no post_msg
        or a void post_msg is given at creation, generate a default one. """

        
        if values.get('provider') == 'swish' and not values.get('post_msg'):
            values['post_msg'] = self._format_transfer_data()
        
        _logger.warn(' \n\n\n ---->>>  create---->>>  %s \n\n\n ' % values)
        return super(AcquirerSwish, self).create(values)

    
    @api.multi
    def write(self, values):
        """ Hook in write to create a default post_msg. See create(). """
        _logger.warn(' \n\n\n ---->>>  write ---->>>  %s \n\n\n ' % values)

        if all(not acquirer.post_msg and acquirer.provider != 'swish' for acquirer in self) and values.get('provider') == 'swish':
            values['post_msg'] = self._format_transfer_data()
        return super(AcquirerSwish, self).write(values)

    @api.model
    def create_swish_payment(self, tx_val):
        _logger.warn(' \n ---->>> \n ---->>> \n ---->>>  create_swish_payment ref ---->>>  %s \n ---->>> \n ---->>> \n ' % tx_val )


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
            payee_payment_reference = tx_val['reference'], 
            callback_url = callback_url,
            payer_alias = payer_alias,
            amount = tx_val['amount'],
            currency = "SEK", #str(tx['currency_id'].name),
            message = 'Order '
        )
        


class TxPayex(models.Model):
    _inherit = 'payment.transaction'
    # Maybe add fields like: 
    # * swish_id
    # * swish_payment_reference
    # * 


    @api.model
    def _swish_form_get_tx_from_data(self, data):
        _logger.warn(' \n\n\n ---->>>  _swish_form_get_tx_from_data---->>>  %s \n\n\n ' % data)
        # Match the transaction here with the swish response. 
        # In this solution we dont send a tx id to swish, which may be not enough?   
        
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

    @api.model
    def _swish_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        status = data['status']
        if not status:
            invalid_parameters.append(('status', 'None', "A value"))
            return invalid_parameters
        if(status == 'ERROR'):
            invalid_parameters.append(('errorCode', 'data[errorCode]', data[errorCode]))
            invalid_parameters.append(('errorMessage', 'data[errorMessage]', data[errorMessage]))
        return invalid_parameters

        _logger.warn("\n\n\n <<<<<<<<<  _swish_form_get_invalid_parameters \n linked payment transaction   <<<<<<<<<< %s \n" % tx.read() )
        

    
    @api.model
    def _swish_form_validate(self, data):
        _logger.warn("\n\n\n <<<<<<<<<  _swish_form_validate \n   <<<<<<<<<< %s \n" % tx.read() )

        # status = data['status']
        # date = data[]
        # former_tx_state = self.state
        # res = {
# 
# 
        # }
        # return True



        # status = data.get('payment_status')
        # former_tx_state = self.state
        # res = {
        #     'acquirer_reference': data.get('txn_id'),
        #     'paypal_txn_type': data.get('payment_type'),
        # }
        # if status in ['Completed', 'Processed']:
        #     try:
        #         # dateutil and pytz don't recognize abbreviations PDT/PST
        #         tzinfos = {
        #             'PST': -8 * 3600,
        #             'PDT': -7 * 3600,
        #         }
        #         date = dateutil.parser.parse(data.get('payment_date'), tzinfos=tzinfos).astimezone(pytz.utc)
        #     except:
        #         date = fields.Datetime.now()
        #     res.update(date=date)
        #     self._set_transaction_done()
        #     if self.state == 'done' and self.state != former_tx_state:
        #         _logger.info('Validated Paypal payment for tx %s: set as done' % (self.reference))
        #         return self.write(res)
        #     return True
        # elif status in ['Pending', 'Expired']:
        #     res.update(state_message=data.get('pending_reason', ''))
        #     self._set_transaction_pending()
        #     if self.state == 'pending' and self.state != former_tx_state:
        #         _logger.info('Received notification for Paypal payment %s: set as pending' % (self.reference))
        #         return self.write(res)
        #     return True
        # else:
        #     error = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (self.reference, status)
        #     res.update(state_message=error)
        #     self._set_transaction_cancel()
        #     if self.state == 'cancel' and self.state != former_tx_state:
        #         _logger.info(error)
        #         return self.write(res)
        #     return True
