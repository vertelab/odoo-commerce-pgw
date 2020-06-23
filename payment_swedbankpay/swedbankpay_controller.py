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

import logging
_logger = logging.getLogger(__name__)
try:
    from payex.service import PayEx
except:
    _logger.warn('payment_payex requires pypayex: sudo pip install pypayex')

class PayexController(http.Controller):
    
    @http.route('/payment/payex/verify', type='http', auth='public', method='GET')
    def auth_payment(self, **post):
        """
        Customer returns from Swedbank Pay. Look up status of order.
        """
        _logger.warn(post)
        ref = post.get('orderRef', '')
        if not ref:
            _logger.warn("Error in Swedbank Pay return. No reference found!")
            return "Error when contacting Swedbank Pay!"
        tx = request.env['payment.transaction'].sudo()._payex_form_get_tx_from_data(post)
        if not tx:
            _logger.warn("Error in Swedbank Pay return. No transaction found!")
            return "Error when contacting Swedbank Pay!"
        service = PayEx(
            merchant_number=tx.acquirer_id.payex_account_nr,
            encryption_key=tx.acquirer_id.payex_key,
            production=tx.acquirer_id.environment == 'prod')
        response = service.complete(orderRef=ref)
        _logger.warn("Swedbank Pay response: %s" % response)
        if response:
            if request.env['payment.transaction'].sudo().with_context({'orderRef': ref}).form_feedback(response, 'payex'):
                return werkzeug.utils.redirect('/shop/payment/validate', 302)
            return "Couldn't verify your payment!"
        _logger.warn("Error when contacting PayEx! Didn't get a response.\n%s" % response)
        return 'Error when contacting PayEx!'
        
    @http.route('/payment/payex/initPayment', type='http', auth='public', method='POST')
    def init_payment(self, **post):
        """
        Contact Swedbank Pay and redirect customer.
        """
        tx = request.env['payment.transaction'].sudo().browse(request.session.get('sale_transaction_id', []))
        if not tx:
            werkzeug.utils.redirect('/shop/payment', 302)
        service = PayEx(
            merchant_number=tx.acquirer_id.payex_account_nr,
            encryption_key=tx.acquirer_id.payex_key,
            production=tx.acquirer_id.environment == 'prod')
        response = service.initialize(
            purchaseOperation = 'SALE',
            price = int(tx.amount * 100),
            currency = tx.currency_id.name,
            vat =int( (tx.sale_order_id.amount_tax / tx.sale_order_id.amount_untaxed) * 100),
            orderID = tx.reference,
            productNumber = tx.reference,
            description = 'Web order',
            clientIPAddress = request.httprequest.remote_addr,
            clientIdentifier = 'USERAGENT=%s' % request.httprequest.user_agent.string,
            additionalValues = 'RESPONSIVE=1',
            returnUrl = '%s/payment/payex/verify' % request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
            view = tx.acquirer_id.payex_view,
            cancelUrl = '%s/shop/payment' % request.env['ir.config_parameter'].sudo().get_param('web.base.url'),
        )
        # code 	            String(128) 	Obsolete parameter, check errorCode.
        # errorCode 	    String 	        Indicates the result of the request. Returns OK if request is successful.
        # description 	    String(512) 	A literal description explaining the result. Returns OK if request is successful.
        # paramName 	    String 	        Returns the name of the parameter that contains invalid data.
        # thirdPartyError 	String 	        Returns the error code received from third party (not available for all payment methods).
        # orderRef 	        String(32) 	    This parameter is only returned if the parameter is successful, and returns a 32bit, hexadecimal value (Guid) identifying the orderRef.Example: 8e96e163291c45f7bc3ee998d3a8939c
        # sessionRef 	    String 	        Obsolete parameter.
        # redirectUrl 	    String 	        Dynamic URL to send the end user to, when using redirect model.
        if response:
            _logger.warn(response)
            status = response.get('status')
            if not status:
                _logger.warn("Error when contacting Swedbank Pay! Didn't get a status.\n%s" % response)
                return 'Error when contacting Swedbank Pay!'
            tx.state_message = status.get('description')
            if not status.get('errorCode'):
                _logger.warn("Error when contacting Swedbank Pay! Didn't get an error code.\n%s" % response)
                return 'Error when contacting PayEx!'
            if status.get('errorCode') != 'OK':
                _logger.warn("Error when contacting Swedbank Pay! Status not OK.\n%s" % response)
                return 'Error when contacting PayEx!'
            if not response.get('orderRef'):
                _logger.warn("Error when contacting Swedbank Pay! Didn't get an order reference.\n%s" % response)
                return 'Error when contacting PayEx!'
            if not response.get('redirectUrl'):
                _logger.warn("Error when contacting Swedbank Pay! Didn't get a redirect url.\n%s" % response)
                return 'Error when contacting Swedbank Pay!'
            tx.acquirer_reference = response.get('orderRef')
            return werkzeug.utils.redirect(response.get('redirectUrl'), 302)
        _logger.warn("Error when contacting Swedbank Pay! Didn't get a response.\n%s" % response)
        return 'Error when contacting Swebank Pay!'
