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
_logger = logging.getLogger(__name__)

class PaysonController(http.Controller):
    _callback_url = "/payment/payson/verify"
    
    @http.route('/payment/payson/verify', type='http', auth='none', method='GET')
    def auth_payment(self, **post):
        """
        OkURL - The address that the response is sent to
        PaysonRef - The unique id of this transaction in Payson's system
        MD5 - MD5 hash to validate the call
        RefNr - The reference used in your system, if set
        Fee - The transaction fee
        """
        _logger.debug('Processing Payson callback with post data:\n%s' % pprint.pformat(post))  # debug
        data = [post, request.httprequest.url, request.httprequest.remote_addr]
        res = request.env['payment.transaction'].sudo().form_feedback(data, 'payson')
        _logger.debug('value of res: %s' % res)
        if res:
            return 'TRUE'
        else:
            return ''
            
    @http.route('/payment/payson/initPayment', type='http', auth='none', method='POST')
    def init_payment(self, **post):
        """
        Contact Payson and redirect customer.
        """
        reference = post.get('reference')
        if not reference:
            return 'Error: No reference'
        tx = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not tx:
            return 'Error: Transaction not found'
        res = tx.payson_init_payment()
        if not res:
            return 'Error: Could not contact Payson'
        return werkzeug.utils.redirect(res, 300)
    
    # TODO: Delete test function or get rekt.
    @http.route('/payment/payson/test', type='http', auth='none', method='GET')
    def test(self, **post):
        url = request.httprequest.url
        url=urllib2.unquote(url).decode('utf8')
        url = url.replace("/payment/payerse/test", "/payment/payerse/verify")
        acquirer = request.env['payment.acquirer'].browse(2)
        return acquirer._payerse_generate_checksum(url)

