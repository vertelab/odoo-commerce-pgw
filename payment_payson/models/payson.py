# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api, _, tools
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import SUPERUSER_ID
from lxml import etree
import urlparse
import urllib2
import base64
import hashlib
import logging
import pprint
import urllib
from openerp.addons.payment.models.payment_acquirer import ValidationError
import uuid
import werkzeug
import pprint

_logger = logging.getLogger(__name__)

def _partner_split_name(partner_name):
    return [' '.join(partner_name.split()[:-1]), ' '.join(partner_name.split()[-1:])]

def limit_string(text, length = 128):
    if len(text) > length:
        return text[:length]
    return text

def get_parameter(p, msg):
    n = msg.find('%s=' % p)
    if n < 0:
        return False
    msg = msg[n + 1 + len(p):]
    _logger.warn(msg)
    n = msg.find('&')
    if n > 0:
        msg = msg[:n]
    _logger.warn(msg)
    return msg
    
class AcquirerPayson(models.Model):
    _inherit = 'payment.acquirer'
    
    payson_agent_id = fields.Char(string='Payer Agent ID',
        required_if_provider='payson')
    payson_email = fields.Char(string='Seller E-mail',
        required_if_provider='payson')
    payson_key = fields.Char(string='Payson Key',
        help='The preshared key.', required_if_provider='payson')
    payson_payment_method_card = fields.Boolean(
        string='Activate card payments')
    payson_payment_method_bank = fields.Boolean(
        string='Activate bank payments')
    payson_payment_method_sms = fields.Boolean(
        string='Activate SMS payments')
    payson_payment_method_invoice = fields.Boolean(
        string='Activate invoice payments')
    payson_return_address = fields.Char(
        string='Success return address',
        help='Default return address when payment is successfull.',
        default='/shop/payment/validate',
        required_if_provider='payerse')
    payson_cancel_address = fields.Char(
        string='Cancellation return address',
        help='Default return address when payment is cancelled.',
        default='/shop/payment', required_if_provider='payerse')
    payson_debug_mode = fields.Selection(string='Debug mode',
        selection=[
            ('silent', 'Silent'),
            ('brief', 'Brief'),
            ('verbose', 'Verbose')
        ],
        required=True, default='verbose')
    payson_application_id = fields.Char(string='Application ID')
    payson_fees_payer = fields.Selection(
        selection=[('PRIMARYRECEIVER', 'Store'), ('SENDER', 'Customer')],
        string='Fees Payer', default='PRIMARYRECEIVER')
    payson_guarantee = fields.Selection(
        string='',
        selection=[('OPTIONAL', 'Optional'), ('REQUIRED', 'Required'), ('NO', 'No')],
        default='OPTIONAL')
    payson_show_receipt = fields.Boolean(string='Show receipt at checkout', default=True)
    
    def payson_validate_ip(self, ip):
        if ip in self._payerse_ip_whitelist:
            return True
        _logger.warning(
            'Payer: callback from unauthorized ip: %s' % ip)
        return False
    
    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerPayson, self)._get_providers(cr, uid,
            context=context)
        providers.append(['payson', 'Payson'])
        return providers
    
    def _payson_generate_checksum(self, data):
        """Generate and return an md5 cheksum."""
        #String text = SellerEmail + ":" + Cost + ":" + ExtraCost + ":" + OkURL + ":" + GuaranteeOffered + Key
        #String Generated_MD5_Hash_Value = MD5(text
        return hashlib.md5(
            data['SellerEmail'] + ":" + data['Cost'] + ":" +
            data['ExtraCost'] + ":" + data['OkURL'] + ":" +
            data['GuaranteeOffered'] + self.payson_key
        ).hexdigest()
    
    @api.multi
    def payson_form_generate_values(self, partner_values, tx_values):
        """Method that generates the values used to render the form button template."""
        self.ensure_one()
        
        _logger.debug(pprint.pformat(partner_values))
        _logger.debug(pprint.pformat(tx_values))
        return partner_values, tx_values
    
    @api.multi
    def payson_get_form_action_url(self):
        """Returns the url of the button form."""
        return '/payment/payson/initPayment'
    
    @api.multi
    def payson_compute_fees(self, amount, currency_id, country_id):
        """Computes the fee for a transaction.
        Broken. Fee is paid by customer and returned with callback."""
        self.ensure_one()
        if not self.fees_active:
            return 0.0
        country = self.env['res.country'].browse(country_id)
        if country and self.company_id.country_id.id == country.id:
            percentage = self.fees_dom_var
            fixed = self.fees_dom_fixed
        else:
            percentage = self.fees_int_var
            fixed = self.fees_int_fixed
        fees = (percentage / 100.0 * amount + fixed ) / (1 - percentage / 100.0)
        return fees


class TxPayson(models.Model):
    _inherit = 'payment.transaction'
    
    payson_token               = fields.Char(string='Payson token')
    payson_payment_type        = fields.Char(string='Payment type')
    payson_testmode            = fields.Boolean(string='Testmode')
    payson_added_fee           = fields.Float(string='Added fee')
    payson_paymentid           = fields.Char(string='Payment ID')
    payson_uuid                = fields.Char(string='Internal ID for redirection')
    
    
    @api.multi
    def payson_init_payment(self):
        self.ensure_one()
        if self.state == 'done':
            return False
        headers={
            #HTTP Headers
            #Headers are used to specify API credentials and HTTP content type. The following HTTP Headers must be submitted with each request to Payson:
            'PAYSON-SECURITY-USERID': self.acquirer_id.payson_agent_id, #Required. Your API User ID (AgentId).
            'PAYSON-SECURITY-PASSWORD': self.acquirer_id.payson_key, #Required. Your API Password (MD5-key).
            'Content-Type': 'application/x-www-form-urlencoded', #Required. Value must be: application/x-www-form-urlencoded
        }
        if self.acquirer_id.payson_application_id:
            headers['PAYSON-APPLICATION-ID'] = self.acquirer_id.payson_application_id, #Optional. Your Application ID. (Only applicable if you have received one) 
        
        post={
            #Pay request parameters 
            'returnUrl': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + self.acquirer_id.payson_return_address,   #Required. string (2048). URL to which the customer's browser is redirected after the payment is completed. Note: This includes both successful and unsuccessful payments.
            'cancelUrl': self.env['ir.config_parameter'].sudo().get_param('web.base.url') + self.acquirer_id.payson_cancel_address,	#Required. string (2048). URL to which the customer is redirected if the payment is manually canceled by the user before it is completed.
            'ipnNotificationUrl': '%s/payment/payson/verify' % self.env['ir.config_parameter'].sudo().get_param('web.base.url'), #Recommended. string (2048). The URL for receiving an Instant Payment Notification about this payment. Note: This parameter has been made optional due to backward compatability. Read more about the use of it here »
            'memo': limit_string(self.reference), #Required. string (128). Description of items the customer is purchasing.
            'senderEmail': limit_string(self.partner_email), #Required. string (128). Email address of the person sending money. This is the Payson account where the settled amount is transferred from.
            'senderFirstName': limit_string(_partner_split_name(self.partner_name)[0]), #Required. string (128). First name of the buyer as entered during checkout.
            'senderLastName': limit_string(_partner_split_name(self.partner_name)[1]), #Required. string (128). Last name of the buyer as entered during checkout.
            
            'localeCode': 'SV', #Optional. LocaleCode (SV/EN/FI/DK/NO). Locale of pages displayed by Payson during payment. Default: SE
            'currencyCode': self.currency_id.name, #Optional. CurrencyCode (SEK/EUR). The currency used for the payment. Default: SEK
            'feesPayer': self.acquirer_id.payson_fees_payer, #Optional. FeesPayer (SENDER/PRIMARYRECEIVER). The payer of the Payson fees. Default: PRIMARYRECEIVER
            #~ 'invoiceFee': '', #Optional. decimal. An invoice fee that will be added as an order item. Must be in the range 0 to 40 Note: This amount should be included in amount specified for the primary receiver
            #~ 'custom': '', #Optional. string (256). A free-form field for your own use. This will be returned in requests to the PaymentDetails API endpoint.
            #~ 'trackingId': '', #Optional. string (128). Your own tracking id. This will be returned in requests to the PaymentDetails API endpoint.
            'guaranteeOffered': self.acquirer_id.payson_guarantee, #Optional. GuaranteeOffered (OPTIONAL/REQUIRED/NO). Whether Payson Guarantee is offered or not. Default: OPTIONAL
            'showReceiptPage': self.acquirer_id.payson_show_receipt, #Optional. bool. Whether to show the receipt page in Paysons checkout. Default: true
            
            #Receiver Details
            #The list of receivers. If you have more than one receiver you must specify exactly one as primary.
            'receiverList.receiver(0).email': limit_string(self.acquirer_id.payson_email), #Required. string (128). Email address of the receiver.
            'receiverList.receiver(0).amount': self.amount, #Required. decimal. The amount (including VAT) to transfer to this recipient. Note: If you have more than one receiver, the primary receiver's amount must still be the full amount of the payment.
            
            #Module does not support multiple receivers. Reference for possible future use:
            #'receiverList.receiver(0..N).primary': , #Optional. bool. Whether this receiver is the primary receiver. This only applies if there is more than one receiver.
            
        }
        
        #Optional. FundingConstraint (CREDITCARD/BANK/INVOICE/SMS). Specifies a list of allowed funding options for the payment. If this field is omitted, the payment can be funded by any funding type that is supported for the merchant (excluding invoice).
        n = 0
        if self.acquirer_id.payson_payment_method_card:
            post['fundingList.fundingConstraint(%i).constraint' % n] = 'CREDITCARD'
            n += 1
        if self.acquirer_id.payson_payment_method_bank:
            post['fundingList.fundingConstraint(%i).constraint' % n] = 'BANK'
            n += 1
        if self.acquirer_id.payson_payment_method_sms:
            post['fundingList.fundingConstraint(%i).constraint' % n] = 'SMS'
            n += 1
        if self.acquirer_id.payson_payment_method_invoice:
            post['fundingList.fundingConstraint(%i).constraint' % n] = 'INVOICE'
        
        #Order Item Details
        #Note: Order Items are required for Invoice, and optional for all other payments types.
        #For each orderItem, you must specify all or none of the parameters sku, quantity, unitPrice & taxPercentage.
        #~ 'orderItemList.orderItem(0..N).description': , #Required. string (128) 	Description of this item.
        #~ 'orderItemList.orderItem(0..N).sku': , #Optional. string (128).SKU of this item.
        #~ 'orderItemList.orderItem(0..N).quantity': , #Optional. decimal. Quantity of this item.
        #~ 'orderItemList.orderItem(0..N).unitPrice': , #Optional. decimal. The unit price of this item not including VAT.
        #~ 'orderItemList.orderItem(0..N).taxPercentage': , #Optional. decimal. Tax percentage for this item. Note: Must be a decimal value and not an actual percentage. E.g. for a 25% tax percentage use 0.25.
        
        n = 0
        for line in self.sale_order_id.order_line:
            post['orderItemList.orderItem(%s).description' % n] = limit_string(line.name)
            post['orderItemList.orderItem(%s).sku' % n] = limit_string(line.product_id and line.product_id.default_code or 'NONE404')
            post['orderItemList.orderItem(%s).quantity' % n] = line.product_uom_qty
            post['orderItemList.orderItem(%s).unitPrice' % n] = line.price_unit
            post['orderItemList.orderItem(%s).taxPercentage' % n] = self.sale_order_id._amount_line_tax(line) / line.price_subtotal
        
        #Send request
        try:
            if self.acquirer_id.environment == 'test':
                payson_response = urllib2.urlopen(urllib2.Request('https://test-api.payson.se/1.0/Pay/', data=werkzeug.url_encode(post), headers=headers)).read()
            else:
                payson_response = urllib2.urlopen(urllib2.Request('https://api.payson.se/1.0/Pay/', data=werkzeug.url_encode(post), headers=headers)).read()
        except:
            return False
        
        #Check for success
        ack = get_parameter('responseEnvelope.ack', payson_response)
        
        if ack != "SUCCESS":
            _logger.warn("Contact with payson failed: %s" % payson_response)
            return False
        
        #Extract token
        token = get_parameter('TOKEN', payson_response)
        if not token:
            #No token received in the response
            _logger.warn("Contact with payson failed. No token received: %s" % payson_response)
            return False
        
        self.acquirer_reference = token
        
        if self.acquirer_id.environment == 'test':
            return "https://test-www.payson.se/paySecure/?token=%s" % token
        return "https://www.payson.se/paySecure/?token=%s" % token
    
    @api.model
    def _payson_form_get_tx_from_data(self, data):
        _logger.debug('get tx from data')
        reference = data[0].get('order_id', False)
        if reference:
            # Search for sale order name instead of reference, to avoid bugs in payment module
            so = self.env['sale.order'].search([('name', '=', reference)])
            tx = self.env['payment.transaction'].search([('sale_order_id', '=', so.id)])
            if len(tx) != 1:
                error_msg = 'Payer: callback referenced non-existing transaction: %s' % reference
                _logger.warning(error_msg)
                raise ValidationError(error_msg)
            return tx
        else:
            error_msg = 'Payer: callback did not contain a tx reference.'
            _logger.warning(error_msg)
            raise ValidationError(error_msg)
    
    @api.model
    def _payson_form_get_invalid_parameters(self, tx, data):
        _logger.debug('get invalid parameters')
        invalid_parameters = []
        post = data[0]
        url = data[1]
        ip = data[2]
        
        checksum = post.get('md5sum', None)
        url = url[0:url.rfind('&')]                 # Remove checksum
        url=urllib2.unquote(url).decode('utf8')     # Convert to UTF-8
        expected = tx.acquirer_id._payerse_generate_checksum(url)
        testmode = post.get('payer_testmode', 'false') == 'true'
        if checksum:
            checksum = checksum.lower()
        else:
            invalid_parameters.append(('md5sum', 'None', 'a value'))
        if checksum and checksum != expected:
            invalid_parameters.append(('md5sum', checksum, expected))
        if not tx.acquirer_id.payerse_validate_ip(ip):
            invalid_parameters.append(('callback sender ip', ip, tx.acquirer_id._payerse_ip_whitelist))
        if testmode != tx.payerse_testmode:
            invalid_parameters.append(('test_mode', testmode, tx.payerse_testmode))
        return invalid_parameters
    
    @api.model
    def _payson_form_validate(self, tx, data):
        _logger.debug('validate form')
        post = data[0]  
        payer_callback_type = post.get('payer_callback_type', False)    #[authorize|settle|store] – callback type
        payer_added_fee = post.get('payer_added_fee', False)	        #[when payer adds the fee for a specific payment type] - fee
        payer_payment_id = post.get('payer_payment_id', False)	        #[xxx@yyyyy – reference: max 64 characters long] - id
        #md5sum = post.get('md5sum', False)
        
        tx_data = {
            'payerse_payment_type': post.get('payer_payment_type', '')
        }
        
        if payer_payment_id:
            tx_data['acquirer_reference'] = payer_payment_id
        if payer_added_fee:
            tx_data['payerse_added_fee'] = payer_added_fee
        
        if not payer_callback_type:
            error = 'Received unrecognized status for Payer payment %s: %s, set as error' % (tx.reference, payer_callback_type)
            _logger.warning(error)
            tx_data.update(state='error', state_message=error)
            tx.write(tx_data)
            return False
        elif payer_callback_type == 'settle':
            _logger.debug('Validated Payer payment for tx %s: set as done' % (tx.reference))
            tx_data.update(state='done', date_validate=fields.Datetime.now(), state_message='Payment verified by Payer')
        elif payer_callback_type == 'auth':
            _logger.debug('Received authorization for Payer payment %s: set as pending' % (tx.reference))
            tx_data.update(state='pending', state_message='Payment authorized by Payer')
        elif payer_callback_type == 'store':
            # Purpose unknown.Does not seem to be used. 
            _logger.debug('Received back to store callback from Payer payment %s' % (tx.reference))
            return True
        else:
            error = 'Received unrecognized status for Payer payment %s: %s, set as error' % (tx.reference, payer_callback_type)
            _logger.warning(error)
            tx_data.update(state='error', state_message=error)
            tx.write(tx_data)
            return False
        return tx.write(tx_data)
    
    @api.model
    def payson_create(self, values):
        _logger.warn(values)
        acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        values['partner_name'] = "foo barson"
        return values
