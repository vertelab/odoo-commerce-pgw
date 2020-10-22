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
#/usr/share/core-odoo/addons/website_sale/controllers/main.py
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.sale.controllers.product_configurator import ProductConfiguratorController
from odoo.addons.payment.controllers.portal import PaymentProcessing



import logging
_logger = logging.getLogger(__name__)

import pprint

# TODO: 
# Do some type of redirect, either use odoos or use an button for redirection (new snippet) that calls on controllers here.

# An other way is to "hjiack" the core-odoo controllers and "extend" them, 
# check the routes in the controller /usr/share/core-odoo/addons/website_sale/controllers/main.py  
# /shop/payment, /shop/payment/transaction, /shop/payment/validate, /shop/confirmation 


class SwedbankPayController(WebsiteSale):

    @http.route('/shop/payment/swedbankpay/validate', type="json", auth='none')
    def swedbankpay_validate(self, **post):
        return "hello there"

    # is called if user directly decline the payment in the redirect link 
    @http.route('/payment/swedbankpay/cancel', type='http', auth='none', csrf=False)
    def swedbankpay_cancel(self, **post): 

        return "payment canceled!"

    @http.route('/payment/swedbankpay/callback', type='http', auth='none', csrf=False)
    def swedbankpay_callback(self, **post):
        _logger.warning("~ callback %s" % post)
        return "payment callbacked!"

    # Use the unique id that was sent in  values["complete_url"] 
    @http.route('/payment/swedbankpay/verify/<transaction_aquierers_id>', type='http', auth='public', method='POST')
    def auth_payment(self, **post):

        tx = request.env['payment.transaction'].search([
            ('acquirer_id','=', parameter)
        ])

        #Use tx.swedbankpay_transaction_uri = resp.json()['payment']['id'] for getting the payment status... 
        # As written in the swedbankpay docs: 
        """
        This means that when you reach this point, you need to make sure that the payment has gone
        through before you let the payer know that the payment was successful. You do this by doing a GET request. 
        This request has to include the payment Id generated from the initial POST request, 
        so that you can receive the state of the transaction.
        """

        return "test"        

    
    @http.route(['/shop/payment/transaction/swedbankpay',
        '/shop/payment/transaction/swedbankpay/<int:so_id>',
        '/shop/payment/transaction/swedbankpay/<int:so_id>/<string:access_token>'], type='json', auth="public", website=True)
    def init_transaction_to(self, acquirer_id, save_token=False, so_id=None, access_token=None, token=None, **kwargs):
        _logger.warning("~ swedbankpay lol")

        # Create the actual transaction...
        payment_transaction_created = self.payment_transaction(acquirer_id, save_token, so_id, access_token, token, **kwargs)
        if(payment_transaction_created):
            _logger.warning("~ payment_transaction_created ")

        swedbankpay_url = 'https://api.externalintegration.payex.com/psp/creditcard/payments'

        sale_order_id =  request.session.get('sale_order_id', -1)
        transaction_id = request.session['__website_sale_last_tx_id']
        # TODO: validate sale_order and transaction_id ?

        values = self.get_payment_values(transaction_id,sale_order_id)
        data = self.format_payment_request(values)

        headers = {
            'Authorization': 'Bearer %s' % values['bearer'], 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        resp = requests.post(swedbankpay_url, headers=headers, data=data)
        
        response_validation = self.check_response(resp, transaction_id)
        if not (response_validation["ok"]):
            _logger.warning("~~ ERORRS! ~~~")
            _logger.warning("~  ERROR MESSAGE: %s " % response_validation["error_message"])
            _logger.warning("~  PROBLEMS: %s " % response_validation["problems"])
            _logger.warning("~  PAYMENT VALUES: %s " % values)
            return response_validation["error_message"] # does this return work?!
        else: 
            _logger.warning("~~~~~~~~~~~~~~~~~~~~")

            redirect_url = self.get_redirect_url(resp.json()['operations'])
            _logger.warning("~ ----> redirect_url %s " % redirect_url)
            
            tx = request.env['payment.transaction'].search([
                ('id','=', transaction_id)
            ])

            # Save the id to make an GET request in  /payment/swedbankpay/verify/<transaction_aquierers_id> route.
            tx.swedbankpay_transaction_uri = resp.json()['payment']['id']

            return werkzeug.utils.redirect('/shop/payment/validate', 302)
            
    
    ### Helper functions...

    def get_payment_values(self, transaction_id, sale_order_id):
        tx = request.env['payment.transaction'].search([
            ('id','=', transaction_id)
        ])
        
        values = {}
        values['base_url'] = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        values['currency_name'] = request.env['res.currency'].search([
            ("id","=",str(tx.currency_id.id))
        ]).name
        
        # Use value that is unique, otherwise a returning customer cant be used... 
        values['reference'] = tx.acquirer_reference

        sale_order_id = request.session.get('sale_order_id', -1)
        
        sale_order = request.env['sale.order'].search([
            ('id','=',str(sale_order_id))
        ])
        values['amount_tax'] = sale_order.amount_tax
        values['amount'] = sale_order.amount_total
        
        swedbank_pay = request.env['payment.acquirer'].sudo().search([
            ('id','=',str(tx.acquirer_id.id))
        ])

        # TODO: 
        # Problem with these sometimes fields, they get updated if i restart/update the module.
        # There is an "noupdate" on the data fields. 
        values['merchant_id'] = swedbank_pay.swedbankpay_merchant_id
        values['bearer'] = swedbank_pay.swedbankpay_account_nr
        
        values["complete_url"] = '%s/payment/swedbankpay/verify/%s' % (values['base_url'], tx.acquirer_reference)  
        return values


    def format_payment_request(self, values):
        return json.dumps({
            "payment": {
                "operation": "Purchase",
                "intent": "Authorization",
                "currency": values['currency_name'],
                "prices": [{
                    "type": "CreditCard",
                    "amount":  int(values['amount'] * 100),
                    "vatAmount": int(values['amount_tax'] * 100), 
                }],
                ## TODO: Use better description!
                "description": "Test Purchase",
                "userAgent": 'USERAGENT=%s' % request.httprequest.user_agent.string,
                "language": "sv-SE",
                "urls": {
                    "completeUrl": values['complete_url'], #'%s/payment/swedbankpay/verify' % values['base_url'],
                    "cancelUrl": '%s/payment/swedbankpay/cancel' % values['base_url'], # Or redirect to back to the shop? 
                    "callbackUrl": '%s/payment/swedbankpay/callback' % values['base_url'],
                },
                "payeeInfo": {
                    "payeeId": values['merchant_id'],  # self.swedbankpay_merchant_id 
                    "payeeReference": values['reference'],
                }
            }
        })


    def get_redirect_url(self, operations):
        for operation in operations:
            _logger.warning(type(operation['rel']))
            if str(operation['rel']) == "redirect-authorization":
                return operation['href']


    def check_response(self, resp, tx):
        response_dict = json.loads(resp.text)
        response_json = resp.json()
        
        # Payment has attribute operations..
        if response_json.get('operations', False):
            return {"ok": True, "error_message" : '', "problems": {}}

        if resp.status_code != 200:
            problems = response_dict.get("problems", False)

            if not problems:
                return {"ok": False, "error_message" : 'Swedbankpay server is not aviable right now', "problems": {}}
            else:
                return {"ok": False, "error_message": 'Transaction failed', "problems": problems} 
        else:
            return {"ok": True, "error_message" : '', "problems": {}}


    # Copied from core controller /payment/core/
    def payment_transaction(self, acquirer_id, save_token=False, so_id=None, access_token=None, token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return False

        try:
            acquirer_id = int(acquirer_id)
        except:
            return False

        # Retrieve the sale order
        if so_id:
            env = request.env['sale.order']
            domain = [('id', '=', so_id)]
            if access_token:
                env = env.sudo()
                domain.append(('access_token', '=', access_token))
            order = env.search(domain, limit=1)
        else:
            order = request.website.sale_get_order()

        # Ensure there is something to proceed
        if not order or (order and not order.order_line):
            return False

        assert order.partner_id.id != request.website.partner_id.id

        # Create transaction
        vals = {'acquirer_id': acquirer_id,
                'return_url': '/shop/payment/validate'}

        if save_token:
            vals['type'] = 'form_save'
        if token:
            vals['payment_token_id'] = int(token)

        transaction = order._create_payment_transaction(vals)

        # store the new transaction into the transaction list and if there's an old one, we remove it
        # until the day the ecommerce supports multiple orders at the same time
        last_tx_id = request.session.get('__website_sale_last_tx_id')
        last_tx = request.env['payment.transaction'].browse(last_tx_id).sudo().exists()
        if last_tx:
            PaymentProcessing.remove_payment_transaction(last_tx)
        PaymentProcessing.add_payment_transaction(transaction)
        request.session['__website_sale_last_tx_id'] = transaction.id

        return True
