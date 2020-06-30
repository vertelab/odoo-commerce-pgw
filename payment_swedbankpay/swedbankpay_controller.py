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
import werkzeug
import requests
import json
 
import logging
_logger = logging.getLogger(__name__)
try:
    from payex.service import PayEx
except:
    _logger.warn('payment_swedbankpay requires pypayex: sudo pip install pypayex')

class PayexController(http.Controller):
    
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
        
    @http.route('/payment/swedbankpay/initPayment', type='http', auth='public', method='POST')
    def init_payment(self, **post):
        """
        Contact Swedbank Pay and redirect customer.
        """
        _logger.warn("Hello world!!! \n\n\n\n")
        tx = request.env['payment.transaction'].sudo().browse(request.session.get('sale_transaction_id', []))
        _logger.warn("Hello world!!! TX %s" % tx )
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
                    "vatAmount": int( (tx.sale_order_id.amount_tax / tx.sale_order_id.amount_untaxed) * 100),
                }
                ],
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

        # ~ SOURCE: https://developer.swedbankpay.com/home/technical-information#uri-usage
        # ~ Test ........ https://api.externalintegration.payex.com/
        # ~ Production .. https://api.payex.com/
        
        resp = requests.post('https://api.%spayex.com/psp/creditcard/payments' % ('externalintegration.' if tx.acquirer_id.environment == 'test' else ''), 
        headers = {'Authorization': 'Bearer %s' % tx.acquirer_id.swedbankpay_key , 'Content-Type': 'application/json' },
        data=data)

        if resp.status_code != 201:
            raise Warning('code %s :: message %s' % (resp.status_code, resp.text ))

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

        
