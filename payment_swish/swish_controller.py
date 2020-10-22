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
from odoo.addons.website_sale.controllers.main import WebsiteSale 

import werkzeug
import requests
import json

from swish import client
from swish import environment
import swish as sw

from odoo import fields, http, tools, _
from odoo.http import request
from odoo.addons.base.models.ir_qweb_fields import nl2br
from odoo.addons.http_routing.models.ir_http import slug
from odoo.addons.payment.controllers.portal import PaymentProcessing
from odoo.addons.website.controllers.main import QueryURL
from odoo.exceptions import ValidationError
from odoo.addons.website.controllers.main import Website
from odoo.addons.sale.controllers.product_configurator import ProductConfiguratorController
from odoo.addons.website_form.controllers.main import WebsiteForm
from odoo.osv import expression

import logging
_logger = logging.getLogger(__name__)

class SwishController(WebsiteSale):
    # Should we use website=False in the decorator?
    @http.route('/payment/swish', type='json', auth='none', method='POST', csrf=False)
    def swish_callback(self, **post): 
        data = json.loads(request.httprequest.data)
        _logger.warn("~ %s /payment/swish (swish_callback) " % request.session)
                    
        # Form feedback also calls the functions 
        # * _swish_form_get_tx_from_data 
        # * _swish_form_get_invalid_parameters
        # * _swish_form_validate
        transaction_registered = request.env['payment.transaction'].sudo().form_feedback(data=data, acquirer_name='swish')

        if(transaction_registered):
            _logger.warn("~ Transaction was sucessfully registered")
            return werkzeug.utils.redirect('/payment/swish/test_route', 302)

    # Taken directly from core..
    # @http.route('/shop/payment', auth='public', website=True, sitemap=False)
    # def my_shop(self, **post):
    #     order = request.website.sale_get_order()
        
    #     redirection = self.checkout_redirection(order)
        
    #     render_values = self._get_shop_payment_values(order, **post)
    #     render_values['only_services'] = order and order.only_services or False

    #     if render_values['errors']:
    #         render_values.pop('acquirers', '')
    #         render_values.pop('tokens', '')

    #     return request.render("website_sale.payment", render_values)

    # Routes that does not work
    # @http.route('/payment/swish/return', auth='public')
    # @http.route('/payment/swish/test_route', auth='public', website=True)
