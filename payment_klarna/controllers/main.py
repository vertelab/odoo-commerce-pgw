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

import uuid
import pprint

import logging
_logger = logging.getLogger(__name__)


class KlarnaController(http.Controller):
    
    
    @http.route('/klarna/terms', type='http', auth='public')
    def terms_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\nterms_test\n%s' % pprint.pformat(post))
        return ''
    
    @http.route('/klarna/cancellation_terms', type='http', auth='public')
    def cancellation_terms_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\ncancellation_terms_test\n%s' % pprint.pformat(post))
        return ''
    
    @http.route('/klarna/checkout', type='http', auth='public')
    def checkout_test(self, **post):
        """
        Foo.
        """
        # ~ _logger.warn('\n\ncheckout_test\n%s' % pprint.pformat(post))
        # ~ order_id = str(uuid.uuid4())
        # ~ klarna_values = {
            # ~ 'order_id': order_id,
            # ~ 'purchase_country': 'SE',
            # ~ 'purchase_currency': 'SEK',
            # ~ 'locale': 'sv-SE',
            # ~ 'order_amount': 10000,
            # ~ 'order_tax_amount': 2000,
            # ~ 'order_lines': [
                # ~ {
                    # ~ 'name': 'Foobar Enhancer 3000',
                    # ~ 'quantity': 1,
                    # ~ 'unit_price': 10000,
                    # ~ 'tax_rate': 2500,
                    # ~ 'total_amount': 10000,
                    # ~ 'total_tax_amount': 2000,
                # ~ }
            # ~ ],
            # ~ 'merchant_urls': {
                # ~ 'terms': 'https://robin.vertel.se/klarna/terms',
                # ~ 'cancellation_terms': 'https://robin.vertel.se/klarna/cancellation_terms',
                # ~ 'checkout': 'https://robin.vertel.se/klarna/checkout',
                # ~ 'confirmation': 'https://robin.vertel.se/klarna/confirmation/%s' % order_id,
                # ~ 'push': 'https://robin.vertel.se/klarna/push',
                # ~ 'validation': 'https://robin.vertel.se/klarna/validation',
                # ~ 'shipping_option_update': 'https://robin.vertel.se/klarna/shipping_option_update',
                # ~ 'address_update': 'https://robin.vertel.se/klarna/address_update',
                # ~ 'notification': 'https://robin.vertel.se/klarna/notification',
                # ~ 'country_change': 'https://robin.vertel.se/klarna/country_change',
            # ~ },
        # ~ }
        # ~ acquirer = request.env['payment.acquirer'].search([('provider', '=', 'klarna')])
        # ~ return acquirer.klarna_initiate_checkout(klarna_values)
        return ''
    
    @http.route('/klarna/confirmation/<string:order_id>', type='http', auth='public')
    def confirmation_test(self, order_id, **post):
        """
        Foo.
        """
        # ~ _logger.warn('\n\nconfirmation_test\n%s' % pprint.pformat(post))
        # ~ acquirer = request.env['payment.acquirer'].search([('provider', '=', 'klarna')])
        # ~ return acquirer.klarna_get_order(order_id)
        return ''
    
    @http.route('/klarna/push', type='http', auth='public')
    def push_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\npush_test\n%s' % pprint.pformat(post))
        return ''
    
    @http.route('/klarna/validation', type='http', auth='public')
    def validation_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\nvalidation_test\n%s' % pprint.pformat(post))
        return ''

    @http.route('/klarna/shipping_option_update', type='http', auth='public')
    def shipping_option_update_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\nshipping_option_update_test\n%s' % pprint.pformat(post))
        return ''
    
    @http.route('/klarna/address_update', type='http', auth='public')
    def address_update_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\naddress_update_test\n%s' % pprint.pformat(post))
        return ''
       
    
    @http.route('/klarna/notification', type='http', auth='public')
    def notification_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\nnotification_test\n%s' % pprint.pformat(post))
        return ''
       
    
    @http.route('/klarna/country_change', type='http', auth='public')
    def country_change_test(self, **post):
        """
        Foo.
        """
        _logger.warn('\n\ncountry_change_test\n%s' % pprint.pformat(post))
        return ''
       
  
