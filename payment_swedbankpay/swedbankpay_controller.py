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
# from odoo.addons.sale.controllers.product_conffigurator import ProductConfiguratorController # remove me 
from odoo.addons.payment.controllers.portal import PaymentProcessing



import logging
_logger = logging.getLogger(__name__)

import pprint

# TODO: 
# Do some type of redirect, either use odoos or use an button for redirection (new snippet) that calls on controllers here.

# An other way is to "hjiack" the core-odoo controllers and "extend" them, 
# check the routes in the controller /usr/share/core-odoo/addons/website_sale/controllers/main.py  
# /shop/payment, /shop/payment/transaction, /shop/payment/validate, /shop/confirmation 
#
# Testdata
# https://developer.swedbankpay.com/resources/test-data


class SwedbankPayController(WebsiteSale):


    @http.route('/shop/payment/token', type='http', auth='public', website=True, sitemap=False)
    def payment_token_hjiack():
        _logger.warning("~~~hej")
        return request.redirect('/payment/swedbankpay/testing')

        

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
    @http.route('/payment/swedbankpay/verify/<transaction_id>', type='http', auth='public', method='POST', website=True, sitemap=False)
    def auth_payment(self, transaction_id ,**post):
        # Use this later, but i need more data got sale_order_ids and so on
        #tx = request.env['payment.transaction'].browse(transaction_id)

        _logger.warning("~ hej verify")
        _logger.warning(" ~ request.sess %s " % request.session)
        _logger.warning(" ~ request.sale_last %s " % request.session["sale_order_id"])


        tx = request.env['payment.transaction'].search([
            ('id','=', transaction_id)
        ])

        if not tx:
            return "no transaction found"
        #resp = requests.post(), 
        
        # Get payment values beacuse we need 
        #if not tx.sale_order_ids:
        #   return "should redirect user somewhere else, no sale_order_id on transaction"

        #values = self.get_payment_values(tx.id ,tx.sale_order_ids[0])
        values = self.get_payment_values(tx.id, request.session["sale_order_id"])

        headers = {
            'Authorization': 'Bearer %s' % values['bearer'], 
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        validation_url = ('https://api.%spayex.com' % ('externalintegration.' if tx.acquirer_id.state == 'test' else '')) + tx.swedbankpay_transaction_uri
        # validation_url = "https://api.externalintegration.payex.com" + tx.swedbankpay_transaction_uri

        resp = requests.get(validation_url, headers=headers)
        # _logger.info('swedbankpay validation_url {validation_url} headers {headers} resp.status {resp_status} resp.json {resp_json}'.format(
        #             validation_url=validation_url,headers=headers,
        #             resp_status=resp.status,resp_json=resp.json()))

        if not resp.status_code == 200 :
            return "Could not get status from transaction..."

        if resp.json()["payment"]["state"] == "Ready":
            
            # Check if transaction is payed....
            operation = self.get_operation(operation_to_get="paid-payment", operations=resp.json()['operations'])
                        
            paid_payment = requests.get(operation["href"], headers=headers)
            
            if paid_payment.status_code == 200:
                # Set transaction is done, this is inspired by the 
                _logger.warning("~ paid_payment == 200")
                tx.sudo()._set_transaction_done()
            
            _logger.warning("~ paid_payment %s" % paid_payment.__dict__)

            _logger.warning("~ request.sesion %s " % request.session)

            # TODO :This check does not work yet, needs to 
            self.remove_context(transaction_id=transaction_id) #, sale_order_id=tx.sale_order_ids[0])
            sale_order_id = request.session.get('sale_last_order_id')
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            
            # order.state = "sent"
            # order.action_draft() 
        
            # state = fields.Selection([
            #     ('draft', 'Quotation'),
            #     ('sent', 'Quotation Sent'),
            #     ('sale', 'Sales Order'),
            #     ('done', 'Locked'),
            #     ('cancel', 'Cancelled'),
            #     ]


            # self.remove_sale_order_from_session()
            # TODO: Return an xml template, that says thank you for the order.
            
            # order.write({'state':'sale'})
            order.action_confirm()

            try:
                order._send_order_confirmation_mail()
            except Exception:
                return request.render("payment_swedbankpay.verify_bad")
            request.website.sale_reset()

            # return request.render("payment_swedbankpay.verify_good",{order.})
            return request.render("website_sale.confirmation", {'order': order})

            # Process the transaction for real...
            # added_payment_transaction = PaymentProcessing.add_payment_transaction(tx)
            # if added_payment_transaction:
            #    return PaymentProcessing.payment_status_page(PaymentProcessing)
            # return "added_payment_transaction failed" 

        return request.render("payment_swedbankpay.verify_bad")

    

    # TODO: Change name
    @http.route(['/payment/swedbankpay/testing'], auth='public', website=True)
    def testing(self, **post):
        swedbankpay_acquirer = request.env['payment.acquirer'].search([("provider","=","swedbankpay")])
        sale_order_id =  request.session.get('sale_order_id', -1)

        payment_transaction_created = self.swedbankpay_payment_transaction(swedbankpay_acquirer.id, so_id=sale_order_id)
        if(payment_transaction_created["sucess"]):
            _logger.warning("swedbankpay ~ payment_transaction_created ")
        else:
            _logger.warning("swedbankpay ~ not payment_transaction_created %s" % payment_transaction_created)
        
        tx = request.env['payment.transaction'].browse(int(payment_transaction_created["transaction_id"]))

        swedbankpay_url = 'https://api.%spayex.com/psp/creditcard/payments' % ('externalintegration.' if tx.acquirer_id.state == 'test' else '')
        # swedbankpay_url = 'https://api.externalintegration.payex.com/psp/creditcard/payments'

        transaction_id = payment_transaction_created["transaction_id"]

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
            # Should return something like this response_validation["error_message"]
            # return "false"
            return request.render("payment_swedbankpay.verify_bad_transaction", {"message": '%s %s %s' % (response_validation["error_message"],response_validation["problems"],values)})

        else: 
            _logger.warning("~~~~~~~~~~~~~~~~~~~~")

            redirect_url = self.get_redirect_url(resp.json()['operations'])
            _logger.warning("~ ----> redirect_url %s " % redirect_url)
            
            tx = request.env['payment.transaction'].sudo().search([
                ('id','=', transaction_id)
            ])


            # Save the id to make an GET request in  /payment/swedbankpay/verify/<transaction_aquierers_id> route.
            tx.swedbankpay_transaction_uri = resp.json()['payment']['id']

            _logger.warning("~ TX-> %s" % tx.read())


            # svara med en redirect url...
            # return redirect_url
            _logger.warning("~~~~ %s" % redirect_url)
            return werkzeug.utils.redirect(redirect_url)
        
        return "message from payment/swedbankpay"

    
    #######  Helper functions...
    def get_payment_values(self, transaction_id, sale_order_id):
        tx = request.env['payment.transaction'].search([
            ('id','=', str(transaction_id))
        ])

        _logger.warning("~ get payment values %s " % tx.id)
        
        values = {}
        # TODO: Support multiple websites by using website configurations parameter instead 
        values['base_url'] = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        values['currency_name'] = request.env['res.currency'].search([
            ("id","=",str(tx.currency_id.id))
        ]).name
        
        # Use value that is unique, otherwise a returning customer cant be used... 
        # Used to use acquirer_reference, but it returned false... wierd...
        values['reference'] = tx.id

        sale_order_id = request.session.get('sale_order_id', -1)
        # _logger.warning('sandra %s' % request.session.get('sale_order_id', -1))
        
        sale_order = request.env['sale.order'].sudo().search([
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


        _logger.warning(values)
        
        values["complete_url"] = '%s/payment/swedbankpay/verify/%s' % (values['base_url'], values['reference'])  
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
                    "completeUrl": values['complete_url'],
                    "cancelUrl": '%s/shop/payment' % values['base_url'], # This url redirects back to the shop
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
            if str(operation['rel']) == "redirect-authorization":
                return operation['href']


    def get_operation(self, operation_to_get,  operations):
        for operation in operations:
            if str(operation['rel']) == operation_to_get:
                return operation
        return None



    def check_response(self, resp, tx):
        if resp.status_code == 401:
            return {"ok": False, "error_message" : 'Swedbankpay server is not aviable right now', "problems": {}}

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
    def swedbankpay_payment_transaction(self, acquirer_id, save_token=False, so_id=None, access_token=None, token=None, **kwargs):
        """ Json method that creates a payment.transaction, used to create a
        transaction when the user clicks on 'pay now' button. After having
        created the transaction, the event continues and the user is redirected
        to the acquirer website.

        :param int acquirer_id: id of a payment.acquirer record. If not set the
                                user is redirected to the checkout page
        """
        # Ensure a payment acquirer is selected
        if not acquirer_id:
            return {"sucess": False, "transaction_id": -1, 'message': 'not acquirer_id %s' % acquirer_id}

        try:
            acquirer_id = int(acquirer_id)
        except:
            return {"sucess": False, "transaction_id": -1, 'message': 'try int acquirer_id %s' % acquirer_id}

        # Retrieve the sale order
        domain = []
        if so_id:
            env = request.env['sale.order']
            domain = [('id', '=', so_id)]
            if access_token:
                env = env.sudo()
                domain.append(('access_token', '=', access_token))
            order = env.search(domain, limit=1)
        else:
            order = request.website.sale_get_order()

        if not order:
            order = request.website.sale_get_order()
            
        # Ensure there is something to proceed
        if not order or (order and not order.order_line):
            return {"sucess": False, "transaction_id": -1, 'message': 'not order  %{order} so_id {so_id} domain {domain} {get_order}'.format(order=order,so_id=so_id,domain=domain,get_order=request.website.sale_get_order())}

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

        return {"sucess": True, "transaction_id": str(transaction.id)}


    def payment_validate(self, transaction_id=None, sale_order_id=None, **post):
        """ Method that should be called by the server when receiving an update
        for a transaction. State at this point :

         - UDPATE ME
        """
        if sale_order_id is None:
            order = request.website.sale_get_order()
        else:
            order = request.env['sale.order'].sudo().browse(sale_order_id)
            assert order.id == request.session.get('sale_last_order_id')

        if transaction_id:
            tx = request.env['payment.transaction'].sudo().browse(transaction_id)
            assert tx in order.transaction_ids()
        elif order:
            tx = order.get_portal_last_transaction()
        else:
            tx = None

        if not order or (order.amount_total and not tx):
            return request.redirect('/shop')

        if order and not order.amount_total and not tx:
            return request.redirect(order.get_portal_url())

        # clean context and session, then redirect to the confirmation page
        request.website.sale_reset()
        if tx and tx.state == 'draft':
            return request.redirect('/shop')

        PaymentProcessing.remove_payment_transaction(tx)
        return request.redirect('/shop/confirmation')

    # This the check of the payment is done earlier in our code...
    # this function is only done for.... write something smart...
    def remove_context(self, transaction_id=None):
        tx = request.env['payment.transaction'].sudo().browse(transaction_id)
        request.website.sale_reset()
        remove_tx = PaymentProcessing.remove_payment_transaction(tx)

    def remove_sale_order_from_session(self): 
        request.session.pop("sale_order_id")
        request.session.pop("sale_last_order_id")
        request.session.pop("website_sale_current_pl")
        request.session.pop("__payment_tx_ids__")
        request.session.pop("__website_sale_last_tx_id")