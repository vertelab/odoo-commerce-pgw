# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import models, fields, api, _
from openerp.exceptions import ValidationError, Warning, RedirectWarning

import requests
from requests.auth import HTTPBasicAuth
import json
import sys, traceback

import logging
_logger = logging.getLogger(__name__)

def test_klarna_get(url_append, url_data):
    url = klarna_url + url_append % url_data
    print url
    response = requests.get(
        url,
        json={},
        auth=HTTPBasicAuth(klarna_uid, klarna_passwd))
    print response
    print response.json()
    return response

klarna_values = {
    'purchase_country': 'SE',
    'purchase_currency': 'SEK',
    'locale': 'sv-SE',
    'order_amount': 10000,
    'order_tax_amount': 2000,
    'order_lines': [
        {
            'name': 'Foobar Enhancer 3000',
            'quantity': 1,
            'unit_price': 10000,
            'tax_rate': 2500,
            'total_amount': 10000,
            'total_tax_amount': 2000,
        }
    ],
    'merchant_urls': {
        'terms': 'https://robin.vertel.se/klarna/terms',
        'cancellation_terms': 'https://robin.vertel.se/klarna/cancellation_terms',
        'checkout': 'https://robin.vertel.se/klarna/checkout',
        'confirmation': 'https://robin.vertel.se/klarna/confirmation',
        'push': 'https://robin.vertel.se/klarna/push',
        'validation': 'https://robin.vertel.se/klarna/validation',
        'shipping_option_update': 'https://robin.vertel.se/klarna/shipping_option_update',
        'address_update': 'https://robin.vertel.se/klarna/address_update',
        'notification': 'https://robin.vertel.se/klarna/notification',
        'country_change': 'https://robin.vertel.se/klarna/country_change',
    },
}
# CHECKOUT
# skicka in klarna_values via POST till /checkout/v3/orders
# rendera response.json()['html_snippet'] för kunden
# hantera callbacks på relevanta merchant_urls
# kund fyller i formuläret och skickas till confirmation

# CONFIRMATION
# hämta ordern via GET på /checkout/v3/orders/{order_id}
# rendera response.json()['html_snippet'] för kunden


class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'
    
    provider = fields.Selection(selection_add=[('klarna', 'Klarna')])
    
    klarna_api_version = fields.Char(string='API Version', required_if_provider='klarna', default='v1')
    klarna_eid = fields.Char(string='Merchant ID', required_if_provider='klarna')
    klarna_uid = fields.Char(string='Username', required_if_provider='klarna')
    klarna_password = fields.Char(string='Password', required_if_provider='klarna')
    klarna_region = fields.Selection(string='Region', selection=[('eu', 'Europe'), ('us', 'US')], default='eu')
    
    def _get_feature_support(self):
        """Get advanced feature support by provider.

        Each provider should add its technical in the corresponding
        key for the following features:
            * fees: support payment fees computations
            * authorize: support authorizing payment (separates
                         authorization and capture)
            * tokenize: support saving payment data in a payment.tokenize
                        object
        """
        res = super(PaymentAcquirer, self)._get_feature_support()
        # ~ res['fees'].append('paypal')
        return res

    @api.multi
    def _get_klarna_urls(self):
        """ Klarna URLS """
        region_url = '-na' if self.klarna_region == 'us' else ''
        if self.environment == 'prod':
            return {
                'klarna_form_url': 'https://api%s.example.com' % region_url,
                'klarna_rest_url': 'https://api%s.klarna.com' % region_url,
            }
        else:
            return {
                'klarna_form_url': 'https://api%s.example.com' % region_url,
                'klarna_rest_url': 'https://api%s.playground.klarna.com' % region_url,
            }

    # ~ @api.multi
    # ~ def klarna_compute_fees(self, amount, currency_id, country_id):
        # ~ """ Compute paypal fees.

            # ~ :param float amount: the amount to pay
            # ~ :param integer country_id: an ID of a res.country, or None. This is
                                       # ~ the customer's country, to be compared to
                                       # ~ the acquirer company country.
            # ~ :return float fees: computed fees
        # ~ """
        # ~ if not self.fees_active:
            # ~ return 0.0
        # ~ country = self.env['res.country'].browse(country_id)
        # ~ if country and self.company_id.country_id.id == country.id:
            # ~ percentage = self.fees_dom_var
            # ~ fixed = self.fees_dom_fixed
        # ~ else:
            # ~ percentage = self.fees_int_var
            # ~ fixed = self.fees_int_fixed
        # ~ fees = (percentage / 100.0 * amount + fixed) / (1 - percentage / 100.0)
        # ~ return fees

    @api.multi
    def klarna_form_generate_values(self, values):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

        paypal_tx_values = dict(values)
        paypal_tx_values.update({
            'cmd': '_xclick',
            'business': self.paypal_email_account,
            'item_name': '%s: %s' % (self.company_id.name, values['reference']),
            'item_number': values['reference'],
            'amount': values['amount'],
            'currency_code': values['currency'] and values['currency'].name or '',
            'address1': values.get('partner_address'),
            'city': values.get('partner_city'),
            'country': values.get('partner_country') and values.get('partner_country').code or '',
            'state': values.get('partner_state') and (values.get('partner_state').code or values.get('partner_state').name) or '',
            'email': values.get('partner_email'),
            'zip_code': values.get('partner_zip'),
            'first_name': values.get('partner_first_name'),
            'last_name': values.get('partner_last_name'),
            'paypal_return': '%s' % urlparse.urljoin(base_url, PaypalController._return_url),
            'notify_url': '%s' % urlparse.urljoin(base_url, PaypalController._notify_url),
            'cancel_return': '%s' % urlparse.urljoin(base_url, PaypalController._cancel_url),
            'handling': '%.2f' % paypal_tx_values.pop('fees', 0.0) if self.fees_active else False,
            'custom': json.dumps({'return_url': '%s' % paypal_tx_values.pop('return_url')}) if paypal_tx_values.get('return_url') else False,
        })
        return paypal_tx_values

    @api.multi
    def klarna_initiate_checkout(self, data):
        self.ensure_one()
        res = {}
        text = 'Oopsie poopsie!'
        try:
            response = requests.post(
                self.klarna_get_rest_url() + '/checkout/v3/orders',
                json=data,
                auth=HTTPBasicAuth(self.klarna_uid, self.klarna_password))
            text = response.text
            res = response.json()
        except:
            e = sys.exc_info()
            tb = ''.join(traceback.format_exception(e[0], e[1], e[2]))
            _logger.warn("Connection to Klarna Failed!\n%s" % tb)
        return '<html><head><title>Klarna Test Checkout</title></head><body>%s</body></html>' % res.get('html_snippet', text)

    @api.multi
    def klarna_get_order(self, order_id):
        self.ensure_one()
        res = {}
        url = self.klarna_get_rest_url() + '/checkout/v3/orders/%s' % order_id
        text = 'Oopsie poopsie!'
        try:
            response = requests.get(
                url,
                json={},
                auth=HTTPBasicAuth(self.klarna_uid, self.klarna_password))
            text = response.text
            res = response.json()
        except:
            e = sys.exc_info()
            tb = ''.join(traceback.format_exception(e[0], e[1], e[2]))
            _logger.warn("Connection to Klarna Failed!\n%s" % tb)
        return '<html><head><title>Klarna Test Checkout</title></head><body>%s<br/>%s</body></html>' % (res.get('html_snippet', text), url)
    
    
    @api.multi
    def klarna_get_form_action_url(self):
        return self._get_klarna_urls()['klarna_form_url']

    @api.multi
    def klarna_get_rest_url(self):
        return self._get_klarna_urls()['klarna_rest_url']
    

    @api.model
    def _amount_odoo2klarna(self, amount, currency):
        return amount * 10**currency.decimal_places

    @api.model
    def _amount_klarna2odoo(self, amount, currency):
        return amount / 10**currency.decimal_places
    
    @api.multi
    def klarna_post(self, url, data):
        self.ensure_one()
        response = False
        status_code == False
        try:
            response = requests.post(
                self.klarna_get_rest_url() + url,
                json=data,
                auth=HTTPBasicAuth(self.klarna_uid, self.klarna_password))
            status_code = response.status_code
        except:
            e = sys.exc_info()
            tb = ''.join(traceback.format_exception(e[0], e[1], e[2]))
            _logger.warn("Connection to Klarna Failed!\n%s" % tb)
        if status_code == 405:
            raise Warning("Wrong method (POST) used in Klarna API call.")
    
    @api.multi
    def klarna_get(self, url):
        self.ensure_one()
        response = False
        status_code == False
        text = False
        json = False
        try:
            response = requests.post(
                self.klarna_get_rest_url() + url,
                json={},
                auth=HTTPBasicAuth(self.klarna_uid, self.klarna_password))
            status_code = response.status_code
            # No JSON = something went very wrong. Throw exception, log traceback, and display error message to user.
            response.json()
        except:
            e = sys.exc_info()
            tb = ''.join(traceback.format_exception(e[0], e[1], e[2]))
            _logger.warn("Connection to Klarna Failed!\n%s" % tb)
            if not response:
                raise Warning("Connection to Klarna Failed! Is the Payment Acquirer set up correctly?")
            elif response.status_code == 405:
                raise Warning("Wrong method (GET) used in Klarna API call.\n\n%s" % response.text)
            elif response.status_code == 404:
                raise Warning("Wrong path used in Klarna API call: %\n\n%s" % (self.klarna_get_rest_url() + url, response.text))
            else:
                raise Warning("Failure in Klarna API call.\n\ncode: %s\n%s" % (response.status_code, response.text))
        return response
        
        
    @api.multi
    def klarna_cancel_order(self, order_id):
        """
        Cancel an authorized order.
        POST /ordermanagement/v1/orders/{order_id}/cancel
        """
        self.ensure_one()
        response = self.klarna_post('/ordermanagement/v1/orders/%s/cancel' % order_id, {})
        if response.status_code == 204:
            # Order cancelled
            return True
        # Something went wrong
        return False

    @api.model
    def klarna_format_error(self, data):
        res = 'error_code: %s\ncorrelation_id: %s\nerror_messages:\n' % (data['error_code'], data['correlation_id'])
        for msg in data['error_messages']:
            res += '\t%s\n' % msg
        return res
    
    @api.one
    def klarna_capture(self, order_id, amount, currency):
        """
        Capture part of the order amount (get paid).
        POST /ordermanagement/v1/orders/{order_id}/captures
        """
        self.ensure_one()
        data = {
            'captured_amount': self._amount_odoo2klarna(amount, currency),      # REQUIRED
            # ~ 'description': 'Foobar Gazonk',
            # ~ 'order_lines': [
                # ~ {
                    # ~ 'reference': '75001',
                    # ~ 'type': 'physical',
                    # ~ 'quantity': 1,
                    # ~ 'quantity_unit': 'pcs.',
                    # ~ 'name': 'string',
                    # ~ 'total_amount': 0,
                    # ~ 'unit_price': 0,
                    # ~ 'total_discount_amount': 0,
                    # ~ 'tax_rate': 0,
                    # ~ 'total_tax_amount': 0,
                    # ~ 'merchant_data': 'Some metadata',
                    # ~ 'product_url': 'https://yourstore.example/product/headphones',
                    # ~ 'image_url': 'https://yourstore.example/product/headphones.png',
                    # ~ 'product_identifiers': {
                        # ~ 'category_path': 'Electronics Store > Computers & Tablets > Desktops',
                        # ~ 'global_trade_item_number': '735858293167',
                        # ~ 'manufacturer_part_number': 'BOXNUC5CPYH',
                        # ~ 'brand': 'Intel'
                    # ~ }
                # ~ }
            # ~ ],
            # ~ 'shipping_info': [
                # ~ {
                    # ~ 'shipping_company': 'DHL US',
                    # ~ 'shipping_method': 'Home',
                    # ~ 'tracking_number': '63456415674545679874',
                    # ~ 'tracking_uri': 'http://shipping.example/findmypackage?63456415674545679874',
                    # ~ 'return_shipping_company': 'DHL US',
                    # ~ 'return_tracking_number': '93456415674545679888',
                    # ~ 'return_tracking_uri': 'http://shipping.example/findmypackage?93456415674545679888'
                # ~ }
            # ~ ],
            # ~ 'shipping_delay': 0, #Delay before the order will be shipped. Use for improving the customer experience regarding payments. This field is currently not returned when reading the order. Minimum: 0. Please note: to be able to submit values larger than 0, this has to be enabled in your merchant account. Please contact Klarna for further information.
        }
        response = self.klarna_post('/ordermanagement/v1/orders/%s/captures' % order_id, data)
        
        if response.status_code == 201:
            return True
        elif response.status_code == 403:
            # Capture not allowed
            raise Warning("Couldn't capture order %s: Capture not allowed.\n\n%s" % self.klarna_format_error(response.json()))
        elif response.status_code == 404:
            # Capture not allowed
            raise Warning("Couldn't capture order %s: Order not found.\n\n%s" % self.klarna_format_error(response.json()))
        else:
            raise Warning("Couldn't capture order %s: Unknown status code ()\n\n%s" % (response.status_code, self.klarna_format_error(response.json())))
    
    # ~ # Error feedback
    # ~ {
      # ~ "error_code" : "ERROR_CODE",
      # ~ "error_messages" : ["Array of error messages"],
      # ~ "correlation_id" : "Unique id for this request used for troubleshooting."
    # ~ }

"""
Bekräfta hela summan.
Capture the full amount.
POST /ordermanagement/v1/orders/{order_id}/captures

Bekräfta betalning på del av summan.
Capture part of the order amount.
POST /ordermanagement/v1/orders/{order_id}/captures

==========

Hämta orderinformation
Retrieve an order.
GET /ordermanagement/v1/orders/{order_id}

Hämta information om en betalning
Retrieve a capture.
GET /ordermanagement/v1/orders/{order_id}/captures/{capture_id}

Kommunicera med kunden, troligtvis en kopia på faktura.
Trigger a new send out of customer communication.
POST /ordermanagement/v1/orders/{order_id}/captures/{capture_id}/trigger-send-out

Återbetala hela eller del av order (ej mer än ordervärdet).
Refund an amount of a captured order
POST /ordermanagement/v1/orders/{order_id}/refunds

Signalera att kund och mottagare är nöjd. Inga fler betalningar kommer ske. Tror inte vi behöver denna?
Release the remaining authorization for an order
POST /ordermanagement/v1/orders/{order_id}/release-remaining-authorization
"""

class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    klarna_order_url = fields.Char('Order URL')

    @api.model
    def _klarna_form_get_tx_from_data(self, data):
        reference, txn_id = data.get('item_number'), data.get('txn_id')
        if not reference or not txn_id:
            error_msg = _('Paypal: received data with missing reference (%s) or txn_id (%s)') % (reference, txn_id)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        txs = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not txs or len(txs) > 1:
            error_msg = 'Paypal: received data for reference %s' % (reference)
            if not txs:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return txs[0]

    @api.multi
    def _klarna_form_get_invalid_parameters(self, data):
        invalid_parameters = []
        # ~ _logger.info('Received a notification from Paypal with IPN version %s', data.get('notify_version'))
        # ~ if data.get('test_ipn'):
            # ~ _logger.warning(
                # ~ 'Received a notification from Paypal using sandbox'
            # ~ ),

        # ~ # TODO: txn_id: shoudl be false at draft, set afterwards, and verified with txn details
        # ~ if self.acquirer_reference and data.get('txn_id') != self.acquirer_reference:
            # ~ invalid_parameters.append(('txn_id', data.get('txn_id'), self.acquirer_reference))
        # ~ # check what is buyed
        # ~ if float_compare(float(data.get('mc_gross', '0.0')), (self.amount + self.fees), 2) != 0:
            # ~ invalid_parameters.append(('mc_gross', data.get('mc_gross'), '%.2f' % self.amount))  # mc_gross is amount + fees
        # ~ if data.get('mc_currency') != self.currency_id.name:
            # ~ invalid_parameters.append(('mc_currency', data.get('mc_currency'), self.currency_id.name))
        # ~ if 'handling_amount' in data and float_compare(float(data.get('handling_amount')), self.fees, 2) != 0:
            # ~ invalid_parameters.append(('handling_amount', data.get('handling_amount'), self.fees))
        # ~ # check buyer
        # ~ if self.payment_token_id and data.get('payer_id') != self.payment_token_id.acquirer_ref:
            # ~ invalid_parameters.append(('payer_id', data.get('payer_id'), self.payment_token_id.acquirer_ref))
        # ~ # check seller
        # ~ if data.get('receiver_id') and self.acquirer_id.paypal_seller_account and data['receiver_id'] != self.acquirer_id.paypal_seller_account:
            # ~ invalid_parameters.append(('receiver_id', data.get('receiver_id'), self.acquirer_id.paypal_seller_account))
        # ~ if not data.get('receiver_id') or not self.acquirer_id.paypal_seller_account:
            # ~ # Check receiver_email only if receiver_id was not checked.
            # ~ # In Paypal, this is possible to configure as receiver_email a different email than the business email (the login email)
            # ~ # In Odoo, there is only one field for the Paypal email: the business email. This isn't possible to set a receiver_email
            # ~ # different than the business email. Therefore, if you want such a configuration in your Paypal, you are then obliged to fill
            # ~ # the Merchant ID in the Paypal payment acquirer in Odoo, so the check is performed on this variable instead of the receiver_email.
            # ~ # At least one of the two checks must be done, to avoid fraudsters.
            # ~ if data.get('receiver_email') != self.acquirer_id.paypal_email_account:
                # ~ invalid_parameters.append(('receiver_email', data.get('receiver_email'), self.acquirer_id.paypal_email_account))

        return invalid_parameters

    @api.multi
    def _klarna_form_validate(self, data):
        status = data.get('payment_status')
        res = {
            'acquirer_reference': data.get('txn_id'),
            'paypal_txn_type': data.get('payment_type'),
        }
        if status in ['Completed', 'Processed']:
            _logger.info('Validated Paypal payment for tx %s: set as done' % (self.reference))
            try:
                # dateutil and pytz don't recognize abbreviations PDT/PST
                tzinfos = {
                    'PST': -8 * 3600,
                    'PDT': -7 * 3600,
                }
                date_validate = dateutil.parser.parse(data.get('payment_date'), tzinfos=tzinfos).astimezone(pytz.utc)
            except:
                date_validate = fields.Datetime.now()
            res.update(state='done', date_validate=date_validate)
            return self.write(res)
        elif status in ['Pending', 'Expired']:
            _logger.info('Received notification for Paypal payment %s: set as pending' % (self.reference))
            res.update(state='pending', state_message=data.get('pending_reason', ''))
            return self.write(res)
        else:
            error = 'Received unrecognized status for Paypal payment %s: %s, set as error' % (self.reference, status)
            _logger.info(error)
            res.update(state='error', state_message=error)
            return self.write(res)
    
