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
    payson_application_id = fields.Char(string='Application ID')
    payson_fees_payer = fields.Selection(
        selection=[('PRIMARYRECEIVER', 'Store'), ('SENDER', 'Customer')],
        string='Fees Payer', default='PRIMARYRECEIVER')
    payson_guarantee = fields.Selection(
        string='',
        selection=[('OPTIONAL', 'Optional'), ('REQUIRED', 'Required'), ('NO', 'No')],
        default='OPTIONAL')
    payson_show_receipt = fields.Boolean(string='Show receipt at checkout', default=True)
    
    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerPayson, self)._get_providers(cr, uid,
            context=context)
        providers.append(['payson', 'Payson'])
        return providers
    
    @api.multi
    def payson_form_generate_values(self, partner_values, tx_values):
        """Method that generates the values used to render the form button template."""
        self.ensure_one()
        
        _logger.warn(pprint.pformat(partner_values))
        _logger.warn(pprint.pformat(tx_values))
        return partner_values, tx_values
    
    @api.multi
    def payson_get_form_action_url(self):
        """Returns the url of the button form."""
        return '/payment/payson/initPayment'
    
    @api.multi
    def payson_compute_fees(self, amount, currency_id, country_id):
        """TODO: Compute fees."""
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
    
    payson_payment_type         = fields.Char(string='Payment type')
    payson_timestamp            = fields.Char(string='Timestamp')
    payson_purchase_id          = fields.Integer(string='Purchase ID')
    payson_status               = fields.Char(selection = 
        [('CREATED', 'Created'),
        ('PENDING', 'Pending'),
        ('PROCESSING', 'Processing'),
        ('COMPLETED', 'Completed'),
        ('CREDITED', 'Cedited'),
        ('ERROR', 'Error'),
        ('REVERSALERROR', 'Reversalerror'),
        ('ABORTED', 'Aborted')],
        string='Status', help="""
CREATED - The payment request was received and has been created in Payson's system. Funds will be transferred once approval is received.
PENDING - The sender has a pending transaction. A guarantee payment in progress has status pending. Please check guaranteeStatus for further details.
PROCESSING - The payment is in progress, check again later.
COMPLETED - The sender's transaction has completed.
CREDITED - The sender's transaction has been credited.
ERROR - The payment failed and all attempted transfers failed or all completed transfers were successfully reversed.
REVERSALERROR - One or more transfers failed when attempting to reverse a payment.
ABORTED - The payment was aborted before any money were transferred.
""")
    payson_type                 = fields.Selection([('TRANSFER', 'Transfer'), ('INVOICE', 'Invoice')], string='Payment type')
    payson_invoice_status       = fields.Char(string='Invoice Status')
    #payson_shipping_name        = fields.Char(string='Name')
    #payson_shipping_street      = fields.Char(string='Address')
    #payson_shipping_zip         = fields.Char(string='ZIP')
    #payson_shipping_city        = fields.Char(string='City')
    #payson_shipping_country     = fields.Char(string='Country')
    #payson_guarantee_status     = fields.Char(string='Guarantee status')
    #payson_guarantee_dlt        = fields.Char(string='Gauarantee Deadline')
    #payson_custom               = fields.Char(string='Custom field for our use. Probably not needed')
    #payson_tracking_id          = fields.Char(string='Tracking ID')
    
    #responseEnvelope.timestamp 	    DateTime 	    Timestamp that identifies when the response was sent.
    #purchaseId 	                    int 	        Payson purchaseId for this payment.
    #senderEmail 	                    string 	        The sender's email address.
    #status 	                        PaymentStatus 	The status of the payment.
    #type 	                            PaymentType 	Type of payment.
    #guaranteeStatus 	                GuaranteeStatus The status of an ongoing Payson Guarantee payment. This is only set if type is GUARANTEE.
    #guaranteeDeadlineTimestamp 	    DateTime 	    Timestamp that identifies when the next guarantee deadline is due, if one exists.
    #invoiceStatus 	                    InvoiceStatus 	The status of an ongoing Payson Invoice payment. This is only set if type is INVOICE.
    #custom 	                        string 	        A free-form field submitted with the Pay request.
    #trackingId 	                    string 	        Your own invoice or tracking id submitted with the Pay request.
    #receiverFee 	                    decimal 	    The fee charged the receiver of the payment
    
    #Shipping address
    #Invoice shipping                   address info.   Only set if the type is INVOICE and invoiceStatus is one of ORDERCREATED, SHIPPED, DONE or CREDITED. Please note that this address must be used as shipping address.
    
    #shippingAddress.name 	            string 	        The name of the shipment's receiver.
    #shippingAddress.streetAddress 	    string 	        The shipment receiver's street address.
    #shippingAddress.postalCode 	    string 	        The shipment receiver's postal code.
    #shippingAddress.city 	            string 	        The shipment receiver's city.
    #shippingAddress.country 	        string 	        The shipment receiver's country.
    
    @api.multi
    def payson_init_payment(self):
        self.ensure_one()
        
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
            'trackingId': self.reference, #Optional. string (128). Your own tracking id. This will be returned in requests to the PaymentDetails API endpoint.
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
        if (self.acquirer_id.payson_payment_method_card or self.acquirer_id.payson_payment_method_bank or self.acquirer_id.payson_payment_method_sms or self.acquirer_id.payson_payment_method_invoice):
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
            n += 1
        
        #Send request
        payson_response = self._payson_send_post('api.payson.se/1.0/Pay/', post)
        if not payson_response:
            return False
        
        #Check for success
        ack = get_parameter('responseEnvelope.ack', payson_response)
        
        if ack != "SUCCESS":
            _logger.warn("Contact with payson failed: responseEnvelope.ack = %s\nWhole response: %s" % (ack, payson_response))
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
        
        #Required 	token 	                Guid 	        The token obtained when creating the payment.
        
        token = data.get('token', False)
        if token:
            tx = self.env['payment.transaction'].search([('acquirer_reference', '=', token)])
            if len(tx) != 1:
                error_msg = 'Payson: callback referenced non-existing transaction: %s' % token
                _logger.warning(error_msg)
                raise ValidationError(error_msg)
            return tx
        else:
            error_msg = 'Payson: callback did not contain a token.'
            _logger.warning(error_msg)
            raise ValidationError(error_msg)
    
    @api.model
    def _payson_form_get_invalid_parameters(self, tx, data):
        _logger.debug('get invalid parameters')
        invalid_parameters = []
        
        if post.get('responseEnvelope.ack') != 'SUCCESS':
            invalid_parameters.append(('responseEnvelope.ack', 'SUCCESS', post.get('responseEnvelope.ack')))
        if post.get('currencyCode') != tx.currency_id.name:
            invalid_parameters.append('currencyCode', tx.currency_id.name, post.get('currencyId'))
        if float(post.get('receiverList(0).amount')) != tx.amount:
            invalid_parameters.append('receiverList(0).amount', tx.amount, post.get('receiverList(0).amount'))
        
        return invalid_parameters
        
        #PaymentDetails Response Parameters
        #Parameter 	                        Data type 	    Description
        
        #responseEnvelope.ack 	            AckCode 	    Acknowledge code indicating the overall success of the request.
        #responseEnvelope.timestamp 	    DateTime 	    Timestamp that identifies when the response was sent.
        #purchaseId 	                    int 	        Payson purchaseId for this payment.
        #senderEmail 	                    string 	        The sender's email address.
        #status 	                        PaymentStatus 	The status of the payment.
        #type 	                            PaymentType 	Type of payment.
        #guaranteeStatus 	                GuaranteeStatus The status of an ongoing Payson Guarantee payment. This is only set if type is GUARANTEE.
        #guaranteeDeadlineTimestamp 	    DateTime 	    Timestamp that identifies when the next guarantee deadline is due, if one exists.
        #invoiceStatus 	                    InvoiceStatus 	The status of an ongoing Payson Invoice payment. This is only set if type is INVOICE.
        #custom 	                        string 	        A free-form field submitted with the Pay request.
        #trackingId 	                    string 	        Your own invoice or tracking id submitted with the Pay request.
        #receiverList.receiver(n).email 	string 	        Email address of the receiver.
        #receiverList.receiver(n).amount 	string 	        The amount to transfer to this receiver.
        #receiverList.receiver(n).primary 	bool 	        Determines whether this is the primary receiver or not.
        #currencyCode 	                    CurrencyCode 	A three-character currency code.
        #receiverFee 	                    decimal 	    The fee charged the receiver of the payment
        
        #Shipping address
        #Invoice shipping                   address info.   Only set if the type is INVOICE and invoiceStatus is one of ORDERCREATED, SHIPPED, DONE or CREDITED. Please note that this address must be used as shipping address.
        #shippingAddress.name 	            string 	        The name of the shipment's receiver.
        #shippingAddress.streetAddress 	    string 	        The shipment receiver's street address.
        #shippingAddress.postalCode 	    string 	        The shipment receiver's postal code.
        #shippingAddress.city 	            string 	        The shipment receiver's city.
        #shippingAddress.country 	        string 	        The shipment receiver's country.
    
    @api.model
    def _payson_form_validate(self, tx, data):
        _logger.debug('validate form')
        tx_data = {}
        if post.get('type'):
            tx_data['payson_type'] = post.get('type')
        if post.get('status'):
            tx_data['payson_status'] = post.get('status')
            status = post.get('status')
            #TODO: Set status here
            if status in ['CREATED', 'PENDING', 'PROCESSING']:
                tx_data['state'] = 'draft'
            elif status in ['COMPLETED', 'CREDITED']:
                tx_data['state'] = 'done'
            elif status in ['ERROR', 'REVERSALERROR']:
                tx_data['state'] = 'error'
            elif status == 'ABORTED':
                tx_data['state'] = 'cancel'
        if post.get('invoiceStatus'):
            tx_data['payson_invoice_status'] = post.get('invoiceStatus')
        if post.get('receiverFee'):
            tx_data['fee'] = post.get('receiverFee')
        if post.get('purchaseId'):
            tx_data['payson_purchase_id'] = post.get('purchaseId')
        if post.get('responseEnvelope.timestamp'):
            tx_data['payson_timestamp'] = post.get('responseEnvelope.timestamp')
        
        return tx.write(tx_data)
    
    @api.model
    def payson_create(self, values):
        _logger.warn(self.env.context)
        acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        return values
    
    @api.multi
    def _payson_send_post(self, url, post):
        """
        Sends a post to the given url with the correct headers.
        """
        self.ensure_one()
        headers={
            #HTTP Headers
            #Headers are used to specify API credentials and HTTP content type. The following HTTP Headers must be submitted with each request to Payson:
            'PAYSON-SECURITY-USERID': self.acquirer_id.payson_agent_id, #Required. Your API User ID (AgentId).
            'PAYSON-SECURITY-PASSWORD': self.acquirer_id.payson_key, #Required. Your API Password (MD5-key).
            'Content-Type': 'application/x-www-form-urlencoded', #Required. Value must be: application/x-www-form-urlencoded
        }
        if self.acquirer_id.payson_application_id:
            headers['PAYSON-APPLICATION-ID'] = self.acquirer_id.payson_application_id, #Optional. Your Application ID. (Only applicable if you have received one) 
        try:
            if self.acquirer_id.environment == 'test':
                payson_response = urllib2.urlopen(urllib2.Request('https://test-%s' % url, data=werkzeug.url_encode(post), headers=headers)).read()
            else:
                payson_response = urllib2.urlopen(urllib2.Request('https://%s' % url, data=werkzeug.url_encode(post), headers=headers)).read()
        except:
            return False
        return payson_response
    
    #~ @api.multi
    #~ def payson_verify_ipn_callback(self, url):
        #~ """Contact Payson to verify the recieved callback."""
        #~ self.ensure_one()
        #~ if self.acquirer_id.environment == 'test':
            #~ payson_response = urllib2.urlopen('https://test-api.payson.se/1.0/Validate/?%s' % url).read()
        #~ else:
            #~ payson_response = urllib2.urlopen('https://api.payson.se/1.0/Validate/?%s' % url).read()
        #~ return payson_response == 'VERIFIED'
    
