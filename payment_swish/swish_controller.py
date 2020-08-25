# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo import http
from odoo.http import request
import werkzeug
import requests
import json
 
import logging
_logger = logging.getLogger(__name__)

class swishController(http.Controller):
    _notify_url = '/payment/swish/ipn/' # ??
    _return_url = '/payment/swish/dpn/'
    _cancel_url = '/payment/swish/cancel/'
    
    @http.route('/payment/swish/verify', type='http', auth='public', method='POST')
    def auth_payment(self, **post):
        """
        Customer returns from Swedbank Pay. Look up status of order.
        """
        return "auth_payment"
        
     
    @http.route('/shop/payment/transaction', type='json', auth='public', method='POST')
    def init_payment2(self, **post):
        tx = request.env['payment.transaction'].sudo()._swish_form_get_tx_from_data(post)
        _logger.warn("1. tx type         = %s \n\n\n" % tx.read())
        
        #swish_form_generate_values needs some values as parameter...
        # Other wise have a function that just get the swish keys and so on.. 
        
        #vals = request.env['payment.acquirer'].sudo().swish_form_generate_values({})
        _logger.warn("2. values         = %s \n\n\n" % tx.read())


    # # Get swish client
    # swish_client = swish.SwishClient(
    #     environment = swish.Environment.Test,
    #     merchant_swish_number = # tx.acquirer_id.swish_account,
    #     cert = ( tx.acquirer_id.swish_cert, tx.acquirer_id.swish_cert),
    #     verify = tx.acquirer_id.swish_verify
    # )
    
    # payer_alias = '467%i' % randint(1000000, 9999999) # Random phone number
    # payment = client.create_payment(
    #     payee_payment_reference=tx.reference,
    #     callback_url='https://example.com/api/swishcb/paymentrequests',
    #     payer_alias=tx.partner_phone, # Is it this ? 
    #     amount=tx.amount,
    #     currency=tx.currency_id.name,
    #     message= u'A Really nice message'
    # )




    # @http.route('/payment/swish/initPayment', type='http', auth='public', method='POST')
    # ORM API searches to use sale_transactoin_id ? 
    #     tx = request.env['payment.transaction'].sudo().browse(request.session.get('sale_transaction_id', []))
    #     rsg = request.session.get('sale_transaction_id', []) # ?? 
