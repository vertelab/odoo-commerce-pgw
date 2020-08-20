# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by MaxVueTech
# See LICENSE file for full copyright and licensing details.

""" File to manage the functions used while redirection"""

import logging
import pprint
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaytmController(http.Controller):

    """ Handles the redirection back from payment gateway to merchant site """
    _return_url = '/payment/paytm/return/'

    def _get_return_url(self, **post):
        """ Extract the return URL from the data coming from paytm. """
        post = dict(post)
        return_url = '/shop/payment/validate'
        return return_url

    def paytm_validate_data(self, **post):
        """ Validate the data coming from paytm. """
        res = False
        reference = post['ORDERID']
        if reference:
            _logger.info('paytm: validated data')
            res = request.env['payment.transaction'
                              ].sudo().form_feedback(post, 'paytm_payment')
            return res

    @http.route('/payment/paytm/return', type='http', auth='none',
                methods=['GET', 'POST'], csrf=False)
    def paytm_return(self, **post):
        """ Gets the Post data from paytm after making payment """
        _logger.info('Beginning paytm form_feedback with post data %s',
                     pprint.pformat(post))  # debug
        return_url = self._get_return_url(**post)
        self.paytm_validate_data(**post)
        return werkzeug.utils.redirect(return_url)
