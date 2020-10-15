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

from swish import client
from swish import environment
import swish as sw

import logging
_logger = logging.getLogger(__name__)

class SwishController(http.Controller):
    # Should we use website=False in the decorator?
    @http.route('/payment/swish', type='json', auth='none', method='POST', csrf=False)
    def swish_callback(self, **post): 
        data = json.loads(request.httprequest.data)
        # _logger.warn("~ ~ ~~~~~ ~~~ %s " % data)
        _logger.warn("~ %s /payment/swish (swish_callback) " % request.session)
                    
        # Form feedback also calls the functions 
        # * _swish_form_get_tx_from_data 
        # * _swish_form_get_invalid_parameters
        # * _swish_form_validate
        transaction_registered = request.env['payment.transaction'].sudo().form_feedback(data=data, acquirer_name='swish')

        if(transaction_registered):
            _logger.warn("~ Transaction was sucessfully registered")
            return werkzeug.utils.redirect('/payment/swish/test_route', 302)
            
    # We can hijack this route from core-odoo, do the same stuff that are done there, then redirect???
    @http.route('/shop/payment', type='json', auth="public", website=True, sitemap=False)
    def paymnet(self, **post):
        _logger.warn("~ ~ ~ shop payment ~~~")
        # return request.
            
            
    @http.route('/payment/swish/return', auth='public')
    def swish_return(self, **post):
        _logger.warning("~ /payment/swish/return: RETURN URL ACTIVATED")
        return 'RETURN HELLO'
        
    @http.route('/payment/swish/tx_url', auth='public')
    def swish_tx_url(self, **post): 
        _logger.warning("~ /payment/swish/tx_url TX TX URL")
        
        
    @http.route('/payment/swish/test_route', auth='public', website=True)
    def test_route(self, **post):
        _logger.warning("~ hello there? ")
        return "<h3>hej</h3>"
        
    
    # Default tx_url ?
    # @http.route('/payment/process', type='json', auth='none', method='POST', website=True)
    
    # This crashes somestuff... if multiple aquirers is used. 
    # @http.route('/shop/payment/transaction', type='json', auth='public', method='POST')
    # def send_swish_payment(self, **post):
    #     _logger.warn("~ %s /shop/payment/transaction (send_swish_payment) " % request.session)
    #     _logger.warn("~ %s" % request.session.session_token)
    #     return werkzeug.utils.redirect('http://www.google.com', 302)



    
