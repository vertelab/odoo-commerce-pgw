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

class PayerSEController(http.Controller):
    #_success_url = "/payment/payerse/success"
    _verify_url = "/payment/payerse/verify"
    #~ _settle_url = "/payment/payerse/settle"
    
    
        
    #~ def validate_checksum(self, url, checksum, tx):
        #~ if checksum:
            #~ data = url[0:url.rfind('&')]
            #~ expected = tx.acquirer_id._payerse_generate_checksum(data)
            #~ if checksum == expected:
                #~ return True
            #~ _logger.warning('Payer.se: callback checksum (%s) did not match expected checksum (%s).' % (checksum, expected))
        #~ else:
            #~ _logger.warning('Payer.se: callback did not contain a checksum.')
        #~ return False
    
    #~ @http.route('/payment/payerse/settle', type='http', auth='none', method='GET')
    #~ def settle_payment(self, **post):
        #~ _logger.info('Beginning Payer.se settle callback with post data %s' % pprint.pformat(post))  # debug
        #~ data = [post, request.httprequest.url, request.httprequest.remote_addr]
        #~ res = request.env['payment.transaction'].sudo().form_feedback(data, 'payerse')
        #~ if res:
            #~ return 'TRUE'
        #~ return 'FALSE' # Will this cancel payment? Yes!
    
    @http.route('/payment/payerse/verify', type='http', auth='none', method='GET')
    def auth_payment(self, **post):
        _logger.info('Processing Payer.se callback with post data:\n%s' % pprint.pformat(post))  # debug
        data = [post, request.httprequest.url, request.httprequest.remote_addr]
        res = request.env['payment.transaction'].sudo().form_feedback(data, 'payerse')
        _logger.info('value of res: %s' % res)
        if res:
            return 'TRUE'
        else:
            return 'FALSE' # Will this cancel payment? Yes!
        
        
        #~ if self.validate_ip(request.httprequest.remote_addr):
            #~ reference = post.get('order_id', False)
            #~ if reference:
                #~ order = request.env['sale.order'].search([('name', '=', reference)])
                #~ if len(order) != 1:
                    #~ _logger.warning('Payer.se callback referenced non-existing sales order: %s' % reference)
                    #~ return ''
                #~ tx = request.env['payment.acquirer'].search([('sale_order_id', '=', order[0].id)])
                #~ if len(order) != 1:
                    #~ _logger.warning('Payer.se callback referenced a sales order with no transaction: %s' % reference)
                    #~ return ''
                #~ if self.validate_checksum(request.httprequest.url, post.get('md5sum', False), tx[0]):
                    #~ #Everything checked out. Do stuff.
                    #~ return 'TRUE'
            #~ else:
                #~ _logger.warning('Payer.se callback did not contain an order reference.')
        #~ return ''
    
    
    @http.route('/payment/payerse/test', type='http', auth='none', method='GET')
    def test(self, **post):
        url = request.httprequest.url
        url=urllib2.unquote(url).decode('utf8') 
        return '\nUTF-8: %s' % url

