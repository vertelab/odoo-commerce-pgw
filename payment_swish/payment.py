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
    swish_merchant_number = fields.Char('Merchant Account #', required_if_provider='swish')
    swish_cert = fields.Char('Swish Cert', required_if_provider='swish')
    swish_key = fields.Char('Swish Key', required_if_provider='swish')
    swish_verify = fields.Char('Swish Root Verification', required_if_provider='swish')
    
    swish_number = '123456789'
    swish_cert = cert_file_path
    swish_key = key_file_path
    swish_verify = verify_file_path
    

    swish_key = fields.Char('Swish Key', required_if_provider='swish')
    swish_key = "example_swish_paykey"

    @api.multi
    def swish_form_generate_values(self, values):
        """Method that generates the values used to render the form button template."""
        
        swish_tx_values = dict(values)

        # What data to use i dont know...?
        swish_tx_values.update({
            'swish_merchant_number': self.swish_merchant_number,
            'currency': values['currency'] and values['currency'].name or '',
            'invoicenumber': values['reference'],
            'swish_payee_refernce': swish_tx_values['partner_phone'],
            'payeeReference': swish_tx_values['reference'],
            'swishKey': self.swish_key, #Which data should be used???
            'swish_payee_phone': '12345678', # Replace this 
            'orderReference': swish_tx_values['reference'], #Should be some other reference? 
        })
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
    # /usr/share/core-odoo/addons/payment_transfer/models/payment.py
    @api.model
    def create(self, values):
        """ Hook in create to create a default post_msg. This is done in create
        to have access to the name and other creation values. If no post_msg
        or a void post_msg is given at creation, generate a default one. """
        if values.get('provider') == 'swish' and not values.get('post_msg'):
            values['post_msg'] = self._format_transfer_data()
        return super(AcquirerSwish, self).create(values)

    
    @api.multi
    def write(self, values):
        """ Hook in write to create a default post_msg. See create(). """
        if all(not acquirer.post_msg and acquirer.provider != 'swish' for acquirer in self) and values.get('provider') == 'swish':
            values['post_msg'] = self._format_transfer_data()
        return super(AcquirerSwish, self).write(values)


class TxPayex(models.Model):
    _inherit = 'payment.transaction'
    
    @api.model
    def _swish_form_get_tx_from_data(self, data):
        ref = self._context.get('orderRef')
        #if ref: 
        # matches right now all the paymenttransactions ?
        return self.env['payment.transaction'].search([('acquirer_reference', '=', ref)])


    @api.model
    def _swish_form_get_invalid_parameters(self, tx, data):
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
    def _swish_form_validate(self, tx, data):
        if data.get('transactionStatus') not in ['0', '3']:
            return False
        return tx.write({'state': 'done', 'date_validate': fields.Datetime.now()})

    
    @api.model
    def swish_create(self, values):
        #acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        return values
