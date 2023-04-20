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

import json
import logging
import pprint
import requests
import time
import werkzeug

from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from odoo import http
from odoo.http import request
#/usr/share/core-odoo/addons/website_sale/controllers/main.py
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.payment.controllers.portal import PaymentProcessing

_logger = logging.getLogger(__name__)


class SwedbankPayController(WebsiteSale):

    @http.route('/shop/payment/swedbankpay/validate', type="json", auth='none')
    def swedbankpay_validate(self, **post):
        _logger.warning("\n"*2 + "~"*25 + 'Validate' + '~'*25)
        _logger.warning(post)
        return "hello there"

    # is called if user directly decline the payment in the redirect link 
    @http.route('/payment/swedbankpay/cancel/<transaction_id>', type='http', auth='none', csrf=False)
    def swedbankpay_cancel(self, transaction_id, **post):
        _logger.info("\n"*2 + "~"*25 + 'Cancel' + '~'*25)
        _logger.info(f'Cancel of transaction id: {transaction_id}')
        tx = request.env['payment.transaction'].sudo().search([('id', '=', transaction_id)])
        tx.state = 'cancel'
        return werkzeug.utils.redirect(f'{request.httprequest.host_url}shop')

    @http.route('/payment/swedbankpay/callback/<transaction_id>', type='json', auth='none', csrf=False, method='POST')
    def swedbankpay_callback(self, transaction_id, **post):
        _logger.debug('~'*25 + 'Calback' + '~'*25)
        data = json.loads(request.httprequest.data)
        _logger.warning(f'Callback header:\n{request.httprequest.headers}')
        _logger.warning(f'Callback data: {data}')

        uri = data.get('transaction', {}).get('id')
        tx = request.env['payment.transaction'].sudo().search([('id', '=', transaction_id)])
        if not tx:
            _logger.warning(f'Callback could not find associated transaction: {transaction_id}')
            return

        if not tx.provider == 'swedbankpay':
            _logger.warning('Swedbankpay controller received callback not associated to swedbankpay: {tx.provider}')
            return 

        # Verify that the URI we "trust" from SwedbankPay atleast is 
        # for the same transaction.
        if not uri.startswith(tx.swedbankpay_transaction_uri):
            _logger.warning('URI mismatch:\n{uri}\ntx.swedbankpay_transaction_uri')
            return
        bearer = tx.acquirer_id.swedbankpay_account_nr
        headers = {
            'Authorization': f'Bearer {bearer}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        test = 'externalintegration.' if tx.acquirer_id.state == 'test' else ''
        validation_url = f'https://api.{test}payex.com' + uri

        for i in range(10):
            resp = requests.get(validation_url, headers=headers)
            if resp.status_code == 200:
                _logger.info('Got response code 200 in callback')
                break
            time.sleep(10*i)
        else:
            # Should do something here?
            _logger.warning('Callback could not get status from transaction')
            return 'Could not get status from transaction...'
        resp_data = json.loads(resp.text)
        auth = resp_data.get('authorization', {})
        auth_status = auth.get('authenticationStatus')
        state = auth.get('transaction', {}).get('state')
        
        
        #https://verifone.cloud/docs/online-payments/3dsecure
        #auth_status possible values
        #Y: Authentication is successful
        #N: Authentication fails
        #A: Authentication attempted (see the next sections for details)
        #U: Unable to authenticate (e.g., Issuer’s ACS is down)
        
        #https://developer.swedbankpay.com/payment-instruments/card/features/core/callback
        #auth_status possible values
        #Indicates the state of the transaction, usually initialized, completed or failed. If a partial authorization has been done and further transactions are possible, the state will be awaitingActivity
        
        # Successfull transaction
        if state == 'Completed' and auth_status == 'Y':
            self.complete_transaction(tx, mail=False)
        # Failed transaction
        elif auth_status == 'N':
            failure_reason = auth.get('failedReason')
            _logger.warning(f"Payment failed state={state} auth_status={auth_status} failure_reason={failure_reason}")
        # What to do here?
        else:
            failure_reason = auth.get('failedReason')
            _logger.warning(f"Callback response not supported. state={state} auth_status={auth_status} failure_reason={failure_reason}")
            pass
        _logger.debug('~'*25 + 'Callback complete' + '~'*25)
        
        return "Callback received succesfully"

    # Use the unique id that was sent in  values["complete_url"] 
    @http.route('/payment/swedbankpay/verify/<transaction_id>', type='http', auth='public', method='POST', website=True, sitemap=False)
    def auth_swedbankpay(self, transaction_id ,**post):
        _logger.warning("\n"*2 + "~"*25 + "auth_swedbankpay" + "~"*25)
        _logger.warning(f'Transaction id: {transaction_id}')
        _logger.warning(f'Post: {post}')
        _logger.warning(f"request.session: {request.session}")

        tx = request.env['payment.transaction'].sudo().search(
            [('id','=', transaction_id)])

        if not tx:
            _logger.warning('Could not find transaction in Auth')
            return "No transaction found"
        values = self.get_payment_values(tx)

        headers = {
            'Authorization': f'Bearer {values["bearer"]}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        test = 'externalintegration.' if tx.acquirer_id.state == 'test' else ''
        validation_url = f'https://api.{test}payex.com' + tx.swedbankpay_transaction_uri
        _logger.info(f'Validation URL: {validation_url}')

        # Do 3 retries if failing to get correct response.
        for i in range(3):
            resp = requests.get(validation_url, headers=headers)
            if resp.status_code == 200:
                _logger.info('Transaction status received')
                break
            time.sleep(10)
        else:
            _logger.warning('Auth could not get status on transaction')
            return ("Could not get status from transaction...Please wait a few "
                    "seconds and refresh this page, should the error still be "
                    "pressent please contact the merchant to manually verify "
                    "the transaction")

        if resp.json()["payment"]["state"] == "Ready":
            _logger.info('Transaction in state Ready checking payment status')
            # Check if transaction is payed....
            operation = self.get_operation(
                operation_to_get="paid-payment",
                operations=resp.json()['operations'])

            # Do 3 retries if failing to get correct response.
            for i in range(3):
                paid_payment = requests.get(operation["href"], headers=headers)
                if paid_payment.status_code == 200:
                    _logger.info(f'Transaction {transaction_id} OK')
                    break
                time.sleep(10)
            else:
                _logger.warning(f'Failed to verify transaction {transaction_id}')
                return ('Failed to verify transaction, transaction in an '
                        'unknown state please contact Merchant to verify '
                        'status manually')

            # Transaction is OK, always return OK status to customer.
            try:
                _logger.info(f'Cleaning up transaction {transaction_id}')
                request.website.sale_reset()
                PaymentProcessing.remove_payment_transaction(tx)
                self.complete_transaction(tx, mail=True)

            finally:
                return request.render("website_sale.confirmation", {'order': tx.sale_order_ids})

        elif resp.json()['payment']['state'] == "Failed":
            _logger.warning('Failed to complete payment')
            tx.state = 'cancel'
            return request.render("payment_swedbankpay.verify_bad_2", {})
        elif resp.json()['payment']['state'] == 'Aborted':
            _logger.warning('Merchant aborted sale before completion')
            tx.state = 'cancel'
            return request.render("payment_swedbankpay.aborted", {})
        elif resp.json()['payment']['state'] == 'Pending':
            _logger.warning('Transaction in Pending state, please investigate manually')
            tx.state = 'error'
            return request.render('payment_swedbankpay.pending', {})
        else:
            _logger.warning('Failed to complete payment in state: '
                            f'{resp.json()["payment"]["state"]}, '
                            'this should not happen!')
            tx.state = 'error'
            return request.render("payment_swedbankpay.unexpected")

    @http.route(['/payment/swedbankpay/init'], auth='public', website=True, csrf=False, type='http')
    def init_swedbankpay(self, **post):
        tx_id = request.session.get('__website_sale_last_tx_id')
        if not tx_id:
            _logger.warning('Could not find last transaction')
            return "No payment transaction found."
        tx = request.env['payment.transaction'].sudo().browse(tx_id)

        _logger.info('~' * 25 + 'Init Pay - Swedbankpay' + '~'*25)

        test = 'externalintegration.' if tx.acquirer_id.state == 'test' else ''
        swedbankpay_url = f'https://api.{test}payex.com/psp/creditcard/payments'
        _logger.info(f'Transaction URL: {swedbankpay_url}')

        values = self.get_payment_values(tx)
        data = self.format_payment_request(values)
        _logger.info(f'Payment data: {data}')

        headers = {
            'Authorization': f'Bearer {values["bearer"]}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }

        resp = requests.post(swedbankpay_url, headers=headers, data=data)
        _logger.info(f'Swedbank transaction init response: {resp.text}')
        response_validation = self.check_response(resp)
        if not (response_validation["ok"]):
            _logger.warning("~~ ERORR! ~~~")
            _logger.warning(f'~  ERROR MESSAGE: {response_validation["error_message"]} ')
            _logger.warning(f'~  PROBLEMS: {response_validation["problems"]}')
            _logger.warning(f'~  PAYMENT VALUES: {values}')
            # Change error message here?
            return request.render(
                "payment_swedbankpay.verify_bad",
                {"message": '%s' % (response_validation["error_message"])})
        else:
            _logger.info("~"*25 + 'Transaction Init OK' + '~'*25)

            redirect_url = self.get_redirect_url(resp.json()['operations'])
            _logger.info("~ ----> redirect_url %s " % redirect_url)
            # Save the id to make an GET request in
            # /payment/swedbankpay/verify/<transaction_aquierers_id> route.
            tx.swedbankpay_transaction_uri = resp.json()['payment']['id']

            _logger.info("~ TX-> %s" % tx.read())

            # return redirect_url
            _logger.info("~~~~ %s" % redirect_url)
            return werkzeug.utils.redirect(redirect_url)

    #######  Helper functions...

    def complete_transaction(self, tx, mail=False):
        tx.sudo()._set_transaction_done()
        for order in tx.sale_order_ids:
            order.action_confirm()
            if mail:
                try:
                    order._send_order_confirmation_mail()
                except Exception:
                    _logger.error('Failed to send confirmation mail')

    def get_payment_values(self, tx):
        # TODO: Support multiple websites by using website configurations parameter instead 
        values = {}
        url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        values['currency_name'] = tx.currency_id.name

        # Use value that is unique, otherwise a returning customer cant be used... 
        # Used to use acquirer_reference, but it returned false... wierd...
        values['reference'] = tx.id
        values['amount_tax'] = sum(tx.mapped('sale_order_ids.amount_tax'))
        values['amount'] = sum(tx.mapped('sale_order_ids.amount_total'))
        values['description'] = ', '.join(tx.mapped('sale_order_ids.name'))[:40]

        # TODO: Problem with these sometimes fields, they get updated if i restart/update the module.
        # There is an "noupdate" on the data fields.
        values['merchant_id'] = tx.acquirer_id.swedbankpay_merchant_id
        values['bearer'] = tx.acquirer_id.swedbankpay_account_nr

        ref = values['reference']
        values["complete_url"] = f'{url}/payment/swedbankpay/verify/{ref}'
        values['callback_url'] = f'{url}/payment/swedbankpay/callback/{ref}'
        values['cancel_url'] = f'{url}/payment/swedbankpay/cancel/{ref}'

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
                "description": values['description'],
                "userAgent": 'USERAGENT=%s' % request.httprequest.user_agent.string,
                "language": "sv-SE",
                "urls": {
                    "completeUrl": values['complete_url'],
                    "cancelUrl": values["cancel_url"],
                    "callbackUrl": values['callback_url'],
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

    def check_response(self, resp):
        if resp.status_code == 401:
            return {"ok": False, "error_message" : 'Swedbankpay server is not available right now', "problems": {}}

        response_dict = json.loads(resp.text)
        response_json = resp.json()

        # Payment has attribute operations..
        if response_json.get('operations'):
            return {"ok": True, "error_message" : '', "problems": {}}

        if resp.status_code != 200:
            problems = response_dict.get("problems")

            if not problems:
                return {"ok": False, "error_message" : 'Swedbankpay server is not available right now', "problems": {}}
            else:
                return {"ok": False, "error_message": 'Transaction failed', "problems": problems} 
        else:
            return {"ok": True, "error_message" : '', "problems": {}}


# These two can be removed?
    # This the check of the payment is done earlier in our code...
    # this function is only done for.... write something smart...
    def remove_context(self, tx):
        tx = request.env['payment.transaction'].sudo().browse(transaction_id)
        request.website.sale_reset()
        remove_tx = PaymentProcessing.remove_payment_transaction(tx)

    def remove_sale_order_from_session(self): 
        request.session.pop("sale_order_id")
        request.session.pop("sale_last_order_id")
        request.session.pop("website_sale_current_pl")
        request.session.pop("__payment_tx_ids__")
        request.session.pop("__website_sale_last_tx_id")
