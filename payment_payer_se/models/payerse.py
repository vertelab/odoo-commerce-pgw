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
from openerp.addons.payment_payer_se.controllers.main import PayerSEController
from openerp.addons.payment.models.payment_acquirer import ValidationError

_logger = logging.getLogger(__name__)

class AcquirerPayerSE(models.Model):
    _inherit = 'payment.acquirer'
    
    payerse_agent_id = fields.Char(string='Payer Agent ID',
        required_if_provider='payerse')
    payerse_key_1 = fields.Char(string='Payer Key 1',
        help='The first preshared key. Sometimes called Key A.', required_if_provider='payerse')
    payerse_key_2 = fields.Char(string='Payer Key 2',
        help='The second preshared key. Sometimes called Key B.',
        required_if_provider='payerse')
    payerse_payment_method_card = fields.Boolean(
        string='Allow card payments')
    payerse_payment_method_bank = fields.Boolean(
        string='Allow bank payments')
    payerse_payment_method_wywallet = fields.Boolean(
        string='Allow Wywallet payments')
    #~ payerse_payment_method_sms = fields.Boolean(
        #~ string='Allow SMS payments.')
    payerse_payment_method_instalment = fields.Boolean(
        string='Allow instalment plan')
    payerse_payment_method_invoice = fields.Boolean(
        string='Allow invoice payments')
    payerse_return_address = fields.Char(
        string='Success return address',
        help='Default return address when payment is successfull.',
        default='/shop/payment/validate',
        required_if_provider='payerse')
    payerse_cancel_address = fields.Char(
        string='Cancellation return address',
        help='Default return address when payment is cancelled.',
        default='/shop/payment', required_if_provider='payerse')
    payerse_debug_mode = fields.Selection(string='Debug mode',
        selection=[
            ('silent', 'Silent'),
            ('brief', 'Brief'),
            ('verbose', 'Verbose')
        ],
        required=True, default='verbose')
    payerse_proxy = fields.Boolean(
        string='Server is behind a proxy',
        help='The IP whitelisting function requires this option to be checked, if the server is behind a proxy.',
        required=True, default=False)
    _payerse_ip_whitelist = [
        "79.136.103.5",
        "94.140.57.180",
        "94.140.57.181",
        "94.140.57.184",
    ]
    
    def payerse_get_ip(self, request):
        if self.payerse_proxy:
            return request.environ.get('HTTP_X_FORWARDED_FOR', '')
        return request.remote_addr
    
    def payerse_validate_ip(self, ip):
        if ip in self._payerse_ip_whitelist:
            return True
        _logger.warning(
            'Payer: callback from unauthorized ip: %s' % ip)
        return False
    
    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerPayerSE, self)._get_providers(cr, uid,
            context=context)
        providers.append(['payerse', 'Payer'])
        return providers
    
    @api.v8
    def _payerse_generate_xml_data(self, partner_values, tx_values):
        """Generates and returns XML-data for Payer."""
        root = etree.Element("payread_post_api_0_2", nsmap={
            "xsi": "http://www.w3.org/2001/XMLSchema-instance",
        }, attrib={
            "{http://www.w3.org/2001/XMLSchema-instance}"
            "noNamespaceSchemaLocation": "payread_post_api_0_2.xsd",
        })
        #Generate seller data
        seller_details = etree.SubElement(root, "seller_details")
        etree.SubElement(seller_details, "agent_id").text = self.payerse_agent_id
        
        #Generate buyer data
        buyer_details = etree.SubElement(root, "buyer_details")
        etree.SubElement(buyer_details, "first_name").text = partner_values['first_name']
        etree.SubElement(buyer_details, "last_name").text = partner_values['last_name']
        etree.SubElement(buyer_details, "address_line_1").text = partner_values['address']
        #etree.SubElement(buyer_details, "address_line_2")    #Necessary? Nope.
        etree.SubElement(buyer_details, "postal_code").text = partner_values['zip']
        etree.SubElement(buyer_details, "city").text = partner_values['city']
        etree.SubElement(buyer_details, "country_code").text = partner_values['country'].code
        etree.SubElement(buyer_details, "phone_home").text = partner_values['phone']
        #etree.SubElement(buyer_details, "phone_work").text = partner_values['phone']
        #etree.SubElement(buyer_details, "phone_mobile").text = partner_values['phone']
        etree.SubElement(buyer_details, "email").text = partner_values['email']
        #etree.SubElement(buyer_details, "organisation").text = partner_values['first_name']
        #etree.SubElement(buyer_details, "orgnr").text = partner_values['first_name']
        
        #Generate purchase data
        purchase = etree.SubElement(root, "purchase")
        etree.SubElement(purchase, "currency").text = tx_values['currency'].name
        etree.SubElement(purchase, "description").text = tx_values['reference']
        etree.SubElement(purchase, "reference_id").text = tx_values['reference']
        purchase_list = etree.SubElement(purchase, "purchase_list")
        
        #Generate product lines
        for line in tx_values['payer_order_lines']:
            freeform_purchase = etree.SubElement(purchase_list, "freeform_purchase")
            etree.SubElement(freeform_purchase, "line_number").text = unicode(line['line_number'])
            etree.SubElement(freeform_purchase, "description").text = unicode(line['description'])
            etree.SubElement(freeform_purchase, "price_including_vat").text = unicode(line['price_including_vat'])
            etree.SubElement(freeform_purchase, "vat_percentage").text = unicode(line['vat_percentage'])
            etree.SubElement(freeform_purchase, "quantity").text = unicode(int(line['quantity']))
        
        #Generate callback data
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        processing_control = etree.SubElement(root, "processing_control")
        etree.SubElement(processing_control, "success_redirect_url").text = urlparse.urljoin(base_url, tx_values.get('return_url', ''))
        etree.SubElement(processing_control, "authorize_notification_url").text = urlparse.urljoin(base_url, tx_values.get('callback_url', ''))
        etree.SubElement(processing_control, "settle_notification_url").text = urlparse.urljoin(base_url, tx_values.get('callback_url', ''))
        etree.SubElement(processing_control, "redirect_back_to_shop_url").text = urlparse.urljoin(base_url, tx_values.get('cancel_url', ''))
        
        #Generate other data
        
        database_overrides = etree.SubElement(root, "database_overrides")
        payment_methods = etree.SubElement(database_overrides, "accepted_payment_methods")
        # Can be set to sms, card, bank, phone, invoice & auto (lies!)
        # Can be bank, card, invoice, wywallet, enter (= instalment plan) (truth)
        # Quite possibly another method for electronic invoices.
        if self.payerse_payment_method_bank:
            etree.SubElement(payment_methods, "payment_method").text = "bank"
        if self.payerse_payment_method_card:
            etree.SubElement(payment_methods, "payment_method").text = "card"
        if self.payerse_payment_method_invoice:
            etree.SubElement(payment_methods, "payment_method").text = "invoice"
        if self.payerse_payment_method_wywallet:
            etree.SubElement(payment_methods, "payment_method").text = "wywallet"
        #~ if self.payerse_payment_method_sms:
            #~ etree.SubElement(payment_methods, "payment_method").text = "sms"
        if self.payerse_payment_method_instalment:
            etree.SubElement(payment_methods, "payment_method").text = "enter"
        
        if self.environment == "test":
            etree.SubElement(database_overrides, "test_mode").text = "true"
        else:
            etree.SubElement(database_overrides, "test_mode").text = "false"
        
        etree.SubElement(database_overrides, "debug_mode").text = self.payerse_debug_mode
        
        #TODO: Add support for other languages
        etree.SubElement(database_overrides, "language").text = "sv"
        
        _logger.info(etree.tostring(root, pretty_print=True))
        
        return base64.b64encode(etree.tostring(root, pretty_print=False))
    
    def _payerse_generate_checksum(self, data):
        """Generate and return an md5 cheksum."""
        return hashlib.md5(self.payerse_key_1 + data + self.payerse_key_2).hexdigest()
    
    @api.multi
    def payerse_form_generate_values(self, partner_values, tx_values):
        """Method that generates the values used to render the form button template."""
        self.ensure_one()
        
        _logger.info(pprint.pformat(partner_values))
        _logger.info(pprint.pformat(tx_values))
        
        payer_tx_values = dict(tx_values)
        if not payer_tx_values.get('return_url'):
            payer_tx_values['return_url'] = self.payerse_return_address
        if not payer_tx_values.get('cancel_url'):
            payer_tx_values['cancel_url'] = self.payerse_cancel_address
        if not payer_tx_values.get('callback_url'):
            payer_tx_values['callback_url'] = PayerSEController._callback_url

        #Calculate order lines that will be sent to Payer
        reference = payer_tx_values.get('reference')
        payer_order_lines = []
        total = 0
        if reference:
            order = self.env['sale.order'].search([['name', '=', reference]])
            i = 1
            for line in order.order_line:
                tax = order._amount_line_tax(line)
                line_dict = {}
                line_dict["line_number"] = i
                if line.product_uom_qty.is_integer():
                    line_dict["description"] = line.name
                    line_dict['quantity'] = line.product_uom_qty
                else:
                    line_dict["description"] = '%d X %s' % (line.product_uom_qty, line.name)
                    line_dict['quantity'] = 1.0
                line_dict['price_including_vat'] = (line.price_subtotal + tax) / line_dict['quantity']
                line_dict['vat_percentage'] = tax * 100 / line.price_subtotal
                total += line_dict['quantity'] * line_dict['price_including_vat']
                payer_order_lines.append(line_dict)
                i += 1
            payer_tx_values['payer_order_lines'] = payer_order_lines
        
        #Check that order lines add up to the given amount and adjust if necessary
        diff = payer_tx_values['amount'] - total
        if abs(diff) > 0.01:
            payer_tx_values['payer_order_lines'].append({
                'line_number': i,
                'description': 'Order total adjustment',
                'price_including_vat': diff,
                'vat_percentage': 0.0,
                'quantity': 1.0,
            })
        
        xml_data = self._payerse_generate_xml_data(partner_values, payer_tx_values)
        
        payer_tx_values.update({
            'payer_agentid': self.payerse_agent_id,
            'payer_xml_writer': "payer_php_0_2_v27",
            'payer_data': xml_data,
            'payer_charset': "UTF-8",
            'payer_checksum': self._payerse_generate_checksum(xml_data),
            'payer_testmode': self.environment,
        })
        
        return partner_values, payer_tx_values
    
    @api.multi
    def payerse_get_form_action_url(self):
        """Returns the url of the button form."""
        return 'https://secure.payer.se/PostAPI_V1/InitPayFlow'
    
    @api.multi
    def payerse_compute_fees(self, amount, currency_id, country_id):
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


class TxPayerSE(models.Model):
    _inherit = 'payment.transaction'
    
    payerse_payment_type        = fields.Char(string='Payment type')
    payerse_testmode            = fields.Boolean(string='Testmode')
    payerse_added_fee           = fields.Float(string='Added fee')
    payerse_paymentid           = fields.Char(string='Payment ID')
    
    @api.model
    def _payerse_form_get_tx_from_data(self, data):
        _logger.info('get txfrom data')
        reference = data[0].get('payer_merchant_reference_id', False)
        if reference:
            tx = self.env['payment.transaction'].search([('reference', '=', reference)])
            if len(tx) != 1:
                error_msg = 'Payer: callback referenced non-existing transaction: %s' % reference
                _logger.warning(error_msg)
                raise ValidationError(error_msg)
            return tx[0]
        else:
            error_msg = 'Payer: callback did not contain a tx reference.'
            _logger.warning(error_msg)
            raise ValidationError(error_msg)
    
    @api.model
    def _payerse_form_get_invalid_parameters(self, tx, data):
        _logger.info('get invalid parameters')
        invalid_parameters = []
        post = data[0]
        url = data[1]
        request = data[2]
        
        checksum = post.get('md5sum', None)
        url = url[0:url.rfind('&')]                 # Remove checksum
        url=urllib2.unquote(url).decode('utf8')     # Decode to UTF-8 from URI
        
        #~ msg = "\npost:\n"
        #~ for key in post:
            #~ msg += "\t%s:\t\t%s\n" % (key, post[key])
        #~ msg += "\nurl:\t%s\ndata:\t%s\nip:\t%s" % (url, callback_data, ip)
        #~ _logger.info(msg)
        
        expected = tx.acquirer_id._payerse_generate_checksum(url)
        testmode = post.get('payer_testmode', 'false') == 'true'
        ip = tx.acquirer_id.payerse_get_ip(request)
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
    def _payerse_form_validate(self, tx, data):
        _logger.info('validate form')
        post = data[0]
        #order_id = post.get('order_id', False)                        #Original parameter added by merchants shop.
        #payer_testmode = post.get('payer_testmode', False)	        #[true|false] – indicates test or live mode    
        payer_callback_type = post.get('payer_callback_type', False)    #[authorize|settle|store] – callback type
        payer_added_fee = post.get('payer_added_fee', False)	        #[when payer adds the fee for a specific payment type] - fee
        payer_payment_id = post.get('payer_payment_id', False)	        #[xxx@yyyyy – reference: max 64 characters long] - id
        #md5sum = post.get('md5sum', False)
                
        tx_data = {
            'payerse_payment_type': post.get('payer_payment_type', False),  #[invoice|card|sms|wywallet|bank|enter] – payment type
        }
        
        if payer_payment_id:
            tx_data['acquirer_reference'] = payer_payment_id
        if payer_added_fee:
            tx_data['payerse_added_fee'] = payer_added_fee
        
        if not payer_callback_type:
            return False
        elif payer_callback_type == 'settle':
            _logger.info('Validated Payer payment for tx %s: set as done' % (tx.reference))
            tx_data.update(state='done', date_validate=fields.Datetime.now())
        elif payer_callback_type == 'auth':
            _logger.info('Received authorization for Payer payment %s: set as pending' % (tx.reference))
            tx_data.update(state='pending', state_message='Payment authorized by Payer')
        elif payer_callback_type == 'store':
            _logger.info('Received back to store callback from Payer payment %s' % (tx.reference))
            return True
        else:
            error = 'Received unrecognized status for Payer payment %s: %s, set as error' % (tx.reference, payer_callback_type)
            _logger.info(error)
            tx_data.update(state='error', state_message=error)
        return tx.write(tx_data)
    
    @api.model
    def payerse_create(self, values):
        #~ msg = "\n"
        #~ for key in values:
            #~ msg += "%s:\t\t%s\n" % (key, values[key])
        #~ _logger.info(msg)
        acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        values['payerse_testmode'] = True if acquirer.environment == 'test' else False
        
        return values
