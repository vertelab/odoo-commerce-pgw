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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import http
from openerp.http import request
from openerp import SUPERUSER_ID
import openerp.tools
import string
import werkzeug
import logging
import pprint
import urllib2
from io import TextIOBase

_logger = logging.getLogger(__name__)

def get_param_dict(text):
    res = {}
    text = text.replace('+', ' ')
    while len(text) > 1:
        n = text.find('=')
        key = urllib2.unquote(text[:n]).decode('utf8')
        text = text[n + 1:]
        n = text.find('&')
        res[key] = urllib2.unquote(text[:n]).decode('utf8')
        text = text[n + 1:]
    return res

class PaysonController(http.Controller):
    
    @http.route('/payment/payson/verify', type='http', auth='public', method='POST')
    def auth_payment(self, **post):
        """
        Foo.
        """
        _logger.debug('Processing Payson callback with post data:\n%s' % pprint.pformat(post))  # debug
        
        token = post.get('token')
        _logger.debug('token: |%s|' % token)
        if not token:
            return ''
        tx = request.env['payment.transaction'].sudo().search([('acquirer_reference', '=', token)])
        if len(tx) != 1:
            _logger.debug('no transaction found: %s' % tx)
            return ''
        tx = tx[0]
        #Verification requires access to post data in the original order. Odoo does not support this.
        #Instead we look up Payment Details for the token we are given, and use that data to update transactions
        lookup = tx.sudo()._payson_send_post('api.payson.se/1.0/PaymentDetails/', {'TOKEN': token})
        _logger.debug('lookup: %s' % lookup)
        if lookup:
            data = get_param_dict(lookup)
            res = request.env['payment.transaction'].sudo().form_feedback(data, 'payson')
            _logger.debug('value of res: %s' % res)
        else:
            _logger.debug('Payson lookup failed')
        return ''
        
    @http.route('/payment/payson/initPayment', type='http', auth='public', method='POST')
    def init_payment(self, **post):
        """
        Contact Payson and redirect customer.
        """
        
        #order = request.website.sale_get_order(context=context)
        _logger.warn('init_payment')
        tx_id = request.session.get('sale_transaction_id')
        _logger.warn('tx_id: %s' % tx_id)
        if not tx_id:
            return 'Error: Transaction not found'
        tx = request.env['payment.transaction'].sudo().browse(tx_id)
        if not tx:
            return 'Error: Transaction not found'
        
        
        #TODO: Redirect to error page instead of ugly messages
        #~ if not post.get('reference'):
            #~ return 'Error: No reference'
        #~ if not post.get('email'):
            #~ return 'Error: No e-mail'
        #~ if not post.get('name'):
            #~ return 'Error: No name'
        #~ tx = request.env['payment.transaction'].search(
            #~ [('reference', '=', post.get('reference')),
            #~ ('partner_name', '=', post.get('name')),
            #~ ('partner_email', '=', post.get('email'))])
        #~ if not tx:
            #~ return 'Error: Transaction not found'
        _logger.warn('tx found')
        res = tx.sudo().payson_init_payment()
        _logger.warn('res: %s' % res)
        if not res:
            return 'Error: Could not contact Payson'
        return werkzeug.utils.redirect(res, 302)
        

