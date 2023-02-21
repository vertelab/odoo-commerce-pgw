# -*- coding: utf-8 -*-

import logging
import pprint
import requests
import werkzeug

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaysonController(http.Controller):

    @http.route('/payment/payson/verify', type='http', auth='public', method='POST')
    def auth_payment(self, **post):
    #     """
    #     Foo.
    #     """
    #     _logger.debug('Processing Payson callback with post data:\n%s' % pprint.pformat(post))  # debug
    #
    #     token = post.get('token')
    #     _logger.debug('token: |%s|' % token)
    #     if not token:
    #         return ''
    #     tx = request.env['payment.transaction'].sudo().search([('acquirer_reference', '=', token)])
    #     if len(tx) != 1:
    #         _logger.debug('no transaction found: %s' % tx)
    #         return ''
    #     tx = tx[0]
    #     # Verification requires access to post data in the original order. Odoo does not support this.
    #     # Instead we look up Payment Details for the token we are given, and use that data to update transactions
    #     lookup = tx.sudo()._payson_send_post('api.payson.se/1.0/PaymentDetails/', {'TOKEN': token})
    #     _logger.debug('lookup: %s' % lookup)
    #     if lookup:
    #         data = get_param_dict(lookup)
    #         res = request.env['payment.transaction'].sudo().form_feedback(data, 'payson')
    #         _logger.debug('value of res: %s' % res)
    #     else:
    #         _logger.debug('Payson lookup failed')
        return ''
    #
    # @http.route('/payment/payson/initPayment', type='http', auth='public', method='POST')
    # def init_payment(self, **post):
    #     """
    #     Contact Payson and redirect customer.
    #     """
    #
    #     # order = request.website.sale_get_order(context=context)
    #     _logger.warn('init_payment')
    #     tx_id = request.session.get('sale_transaction_id')
    #     _logger.warn('tx_id: %s' % tx_id)
    #     if not tx_id:
    #         return 'Error: Transaction not found'
    #     tx = request.env['payment.transaction'].sudo().browse(tx_id)
    #     if not tx:
    #         return 'Error: Transaction not found'
    #
    #     # TODO: Redirect to error page instead of ugly messages
    #     # ~ if not post.get('reference'):
    #     # ~ return 'Error: No reference'
    #     # ~ if not post.get('email'):
    #     # ~ return 'Error: No e-mail'
    #     # ~ if not post.get('name'):
    #     # ~ return 'Error: No name'
    #     # ~ tx = request.env['payment.transaction'].search(
    #     # ~ [('reference', '=', post.get('reference')),
    #     # ~ ('partner_name', '=', post.get('name')),
    #     # ~ ('partner_email', '=', post.get('email'))])
    #     # ~ if not tx:
    #     # ~ return 'Error: Transaction not found'
    #     _logger.warn('tx found')
    #     res = tx.sudo().payson_init_payment()
    #     _logger.warn('res: %s' % res)
    #     if not res:
    #         return 'Error: Could not contact Payson'
    #     return werkzeug.utils.redirect(res, 302)
