# -*- coding: utf-8 -*-

import logging
import pprint
import json
import requests
import werkzeug

from odoo import http, _
from odoo.http import request

_logger = logging.getLogger(__name__)


class PaysonController(http.Controller):
    _checkout_url = '/payment/payson/checkout'
    _confirmation_url = '/payment/payson/confirmation'
    _notification_url = '/payment/payson/notification'
    _term_url = '/payment/stripe/terms'

    @http.route(_checkout_url, type='http', auth='public', website=True, csrf=False)
    def payson_checkout(self, **post):
        transaction_id = request.env['payment.transaction'].sudo().browse(
            request.session.get('__website_sale_last_tx_id'))

        if transaction_id:
            payson_resp = transaction_id._payson_payment_verification()
            if payson_resp.get("status") in ["denied", "canceled", "expired"]:
                return request.redirect('/shop/cart')

            values = {"transaction_id": transaction_id}
            return request.render("payment_payson.payson_checkout", values)
        else:
            return request.redirect('/shop')

    @http.route(_confirmation_url, type='http', auth='public', csrf=False)
    def payson_confirmation(self, **post):
        _logger.info('Payson Payson Confirmation: receiving payson term: %s', post)
        last_tx_id = request.env['payment.transaction'].sudo().browse(request.session.get('__website_sale_last_tx_id'))
        last_tx_id._payson_checkout_get_tx_data()
        return werkzeug.utils.redirect('/payment/process')

    @http.route(_notification_url, type='http', auth='public', csrf=False)
    def payson_notification(self, **post):
        _logger.info('Payson Payson Notification: receiving payson term: %s', post)
        transaction_id = request.env['payment.transaction'].sudo().sudo().search([
                ("payson_transaction_id", "=", post.get('checkout'))])
        transaction_id.sudo()._payson_checkout_get_tx_data()

    @http.route(_term_url, type='http', auth='public', csrf=False)
    def payson_term(self, **post):
        _logger.info('Payson Payson Term: receiving payson term: %s', post)
