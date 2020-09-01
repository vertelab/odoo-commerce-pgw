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
 
import logging
_logger = logging.getLogger(__name__)


class xxBuckarooController(http.Controller):
    _return_url = '/payment/buckaroo/return'
    _cancel_url = '/payment/buckaroo/cancel'
    _exception_url = '/payment/buckaroo/error'
    _reject_url = '/payment/buckaroo/reject'

    @http.route([
        '/payment/buckaroo/return',
        '/payment/buckaroo/cancel',
        '/payment/buckaroo/error',
        '/payment/buckaroo/reject',
    ], type='http', auth='none', csrf=False)
    def xxbuckaroo_return(self, **post):
        """ Buckaroo."""
        _logger.info('Buckaroo: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'buckaroo')
        post = {key.upper(): value for key, value in post.items()}
        return_url = post.get('ADD_RETURNDATA') or '/'
        return werkzeug.utils.redirect('/payment/process')



class SwedbankPayController(http.Controller):
    _notify_url = '/payment/swedbankpay/ipn/' # ??
    _return_url = '/payment/swedbankpay/return/'
    _cancel_url = '/payment/swedbankpay/cancel/'
    _exception_url = '/payment/swedbankpay/error/'
    _reject_url = '/payment/swedbankpay/reject/'

    @http.route([
        '/payment/swedbankpay/return',
        '/payment/swedbankpay/cancel',
        '/payment/swedbankpay/error',
        '/payment/swedbankpay/reject',
    ], type='http', auth='none', csrf=False)
    def swedbankpay_return(self, **post):
        """Swedbank Pay."""
        _logger.info('Swedbank Pay: entering form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'swedbankpay')
        post = {key.upper(): value for key, value in post.items()}
        return_url = post.get('ADD_RETURNDATA') or '/'
        return werkzeug.utils.redirect('/payment/process')
    
    @http.route('/payment/swedbankpay/verify', type='http', auth='public', method='POST')
    def auth_payment(self, **post):
        """
        Customer returns from Swedbank Pay. Look up status of order.
        """
        _logger.warn(post)
        ref = post.get('orderReference', '')
        if not ref:
            _logger.warn("Error in Swedbank Pay return. No reference found!")
            return "5. Error when contacting Swedbank Pay!"
        tx = request.env['payment.transaction'].sudo()._swedbankpay_form_get_tx_from_data(post)
        if not tx:
            _logger.warn("Error in Swedbank Pay return. No transaction found!")
            return "6. Error when contacting Swedbank Pay!"
        service = PayEx(
            merchant_number=tx.acquirer_id.swedbankpay_account_nr,
            encryption_key=tx.acquirer_id.swedbankpay_key,
            production=tx.acquirer_id.environment == 'prod')
        response = service.complete(orderRef=ref)
        _logger.warn("Swedbank Pay response: %s" % response)
        if response:
            if request.env['payment.transaction'].sudo().with_context({'orderRef': ref}).form_feedback(response, 'swedbankpay'):
                return werkzeug.utils.redirect('/shop/payment/validate', 302)
            return "Couldn't verify your payment!"
        _logger.warn("Error when contacting Swedbank Pay! Didn't get a response.\n%s" % response)
        return '7. Error when contacting Swedbank Pay!'
        
    @http.route('/shop/payment/transaction', type='json', auth='public', method='POST') ## Alternative link. Plan B.
    # ~ @http.route('/payment/swedbankpay/initPayment', type='http', auth='public', method='POST')
    def init_payment(self, **post):
        """
        Contact Swedbank Pay and redirect customer.
        """
        _logger.warn("1. Hello world!!! \n\n\n\n")
        tx = request.env['payment.transaction'].sudo().browse(request.session.get('sale_transaction_id', []))
        _logger.warn("2. Hello world!!! TX = %s \n\n\n" % tx )
        if not tx:
            werkzeug.utils.redirect('/shop/payment', 302)
        # ~ request.post
        # ~ SWEDBANK PAY CODE DOCUMENTATION
        # ~ https://developer.swedbankpay.com/payments/card/redirect

        data = json.dumps({
            "payment": {
                "operation": "Purchase",
                "intent": "Authorization",
                "currency": tx.currency_id.name,
                "prices": [{
                    "type": "CreditCard",
                    "amount": int(tx.amount * 100),
                    "vatAmount": int(sum(tx.sale_order_ids.mapped('amount_tax')) * 100 ),
                }],
                "description": "Test Purchase",
                "userAgent": 'USERAGENT=%s' % request.httprequest.user_agent.string,
                "language": "sv-SE",
                "urls": {
                    "completeUrl": '%s/payment/swedbankpay/verify' % request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                    "cancelUrl": '%s/shop/payment' % request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                    # ~ "logoUrl":  '%s/logo500.png' % request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                },
                "payeeInfo": {
                    "payeeId": tx.acquirer_id.swedbankpay_merchant_id,
                    "payeeReference": tx.reference,
                    # ~ "payeeReference": tx.acquirer_id.swedbankpay_account_nr,
                    "swedbankpayKey": tx.acquirer_id.swedbankpay_key,
                    # ~ "payeeName": "xxxxx",
                    # ~ "productCategory": "xxxxx",
                    "orderReference": tx.reference,
                    # ~ "subsite": request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
                }
            }
        })

        _logger.warn("66. data = json-dump = %s \n\n\n" % data )

        data = {"payment": {"operation": "Purchase", "intent": "Authorization", "currency": 'SEK', "prices": 
        [{"type": "CreditCard", "amount": '10000', "vatAmount": '2500'}], "description": "Test Purchase", "userAgent": 
        "USERAGENT=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:79.0) Gecko/20100101 Firefox/79.0", "language": "sv-SE", "urls": 
            {"completeUrl": "http://localhost:8069/payment/swedbankpay/verify", "cancelUrl": "http://localhost:8069/shop/payment"},
             "payeeInfo": {"payeeId": "424bf7dc-2c0c-4d64-b625-dd5e17551b48", "payeeReference": "SO001", "swedbankpayKey": 
            "86eb07f6e313598322ed5651861940679befcaba772f9b13916e74ff4fa67b67", 
             "orderReference": "SO002"}}}

        _logger.warn("66. data = json-dump = %s \n\n\n" % data )
        # ~ SOURCE: https://developer.swedbankpay.com/home/technical-information#uri-usage
        # ~ Test ........ https://api.externalintegration.payex.com/
        # ~ Production .. https://api.payex.com/
        # ~ 2020-08-25 .. DO NOT REMOVE!

        # ~ _logger.warn("6. tx.acquirer_id.environment \n\n\n" % tx.acquirer_id.environment )
        # ~ _logger.warn("7. tx.acquirer_id.swedbankpay_key \n\n\n" % tx.acquirer_id.swedbankpay_key )
        
        # ~ resp = requests.post('https://api.%spayex.com/psp/creditcard/payments' % ('externalintegration.' if tx.acquirer_id.environment == 'test' else ''), 
        # ~ headers = {'Authorization': 'Bearer %s' % tx.acquirer_id.swedbankpay_key , 'Content-Type': 'application/json' },
        # ~ data=data)
        resp = requests.post('https://api.externalintegration.payex.com/psp/creditcard/payments', 
        headers = {'Authorization': 'Bearer 86eb07f6e313598322ed5651861940679befcaba772f9b13916e74ff4fa67b67', 'Content-Type': 'application/json' },
        data=data)
        _logger.warn("8. resp = %s \n\n\n" % resp )
        _logger.warn("8. http.request %s '%s' \n\n\n" % (resp.status_code, resp.text ) )

# ~ int(sum(tx.sale_order_ids.mapped('amount_tax')) * 100 )

        # ~ if resp.status_code != 201:
            # ~ raise Warning('code %s :: message %s' % (resp.status_code, resp.text ))

        _logger.warn("9. http.request \n\n\n" )

        if resp:

            responseDict = json.loads(resp.text)
            _logger.warn('SWEDBANKPAY: %s' % responseDict)

            if not resp.status_code:
                _logger.warn("Error when contacting Swedbank Pay! Didn't get a status. %s %s" % (resp.status_code, resp.text ))
                return '1. Error when contacting Swedbank Pay!'
            tx.state_message = '%s' % responseDict.get('payment')
            if resp.status_code != 201:
                _logger.warn("Error when contacting Swedbank Pay! We did get an error code. %s %s" % (resp.status_code, resp.text))
                return '2. Error when contacting SwedbankPay!'

            if not responseDict.get('payment', {}).get('number'):
                _logger.warn("Error when contacting Swedbank Pay! Didn't get an order reference. %s" % responseDict.get('payment'))
                return '3. Error when contacting Swedbank Pay!'
            tx.acquirer_reference = responseDict.get('payment', {}).get('number')

            if not responseDict.get('operations', [{},{}])[1].get('href'):
                _logger.warn("Error when contacting Swedbank Pay! Didn't get a redirect url.%s" % responseDict)
                return '4. Error when contacting Swedbank Pay!'
            return werkzeug.utils.redirect(responseDict.get('operations', [{},{}])[1].get('href'), 302)

    # ~ @http.route('/shop/payment/transaction', type='json', auth='public', method='POST')
    # ~ def init_payment2(self, **post):
        # ~ _logger.warn("\n\n\n\n\n\n Hej \n\n\n\n\n\n")





