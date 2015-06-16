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
_logger = logging.getLogger(__name__)

class PayerSEController(http.Controller):
    _success_url = "/payment/payerse/success"
    _auth_url = "/payment/payerse/authorize"
    _settle_url = "/payment/payerse/settle"
    _shop_url = "/payment/payerse/return"
    
    _ip_whitelist = ["79.136.103.5", "94.140.57.180", "94.140.57.181", "94.140.57.184"]
    
    def validate_ip(ip):
        if ip in self._ip_whitelist:
            return True
        _logger.warning('Payer.se: callback from unauthorized ip: %s' % ip)
        return False
        
    def validate_checksum(self, url, checksum, tx):
        if checksum:
            data = url[0:url.rfind('&')]
            expected = tx.acquirer_id._payerse_generate_checksum(data)
            if checksum == expected:
                return True
            _logger.warning('Payer.se: callback checksum (%s) did not match expected checksum (%s).' % (checksum, expected))
        else:
            _logger.warning('Payer.se: callback did not contain a checksum.')
        return False
    
    @http.route('/payment/payerse/settle', type='http', auth='none', method='GET')
    def settle_payment(self, **post):
        if self.validate_ip(request.httprequest.remote_addr):
            reference = post.get('order_id', False)
            if reference:
                order = request.env['sale.order'].search([('name', '=', reference)])
                if len(order) != 1:
                    _logger.warning('Payer.se callback referenced non-existing sales order: %s' % reference)
                    return ''
                tx = request.env['payment.acquirer'].search([('sale_order_id', '=', order[0].id)])
                if len(order) != 1:
                    _logger.warning('Payer.se callback referenced a sales order with no transaction: %s' % reference)
                    return ''
                if self.validate_checksum(request.httprequest.url, post.get('md5sum', False), tx[0]):
                    #Everything checked out. Do stuff
                    return ''
            else:
                _logger.warning('Payer.se callback did not contain an order reference.')
        return ''
    
    @http.route('/payment/payerse/test', type='http', auth='none', method='GET')
    def test(self, **post):
        foo = post.get('foo', False)
        return 'url: %s<br/>url_root: %s' % (request.httprequest.url, request.httprequest.url_root)

