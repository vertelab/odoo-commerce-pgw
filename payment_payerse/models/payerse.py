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
from openerp.addons.payment_payerse.controllers.main import PayerSEController
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
    #~ payerse_auth_only = fields.Boolean(
        #~ string='Authorize only', default=False)
    payerse_payment_method_auto = fields.Boolean(
        string='Automatic Payment Options')
    payerse_payment_method_card = fields.Boolean(
        string='Activate card payments')
    payerse_payment_method_bank = fields.Boolean(
        string='Activate bank payments')
    payerse_payment_method_wywallet = fields.Boolean(
        string='Activate Wywallet payments')
    payerse_payment_method_einvoice = fields.Boolean(
        string='Activate e-invoice payments.')
    payerse_payment_method_instalment = fields.Boolean(
        string='Activate instalment plan')
    payerse_payment_method_invoice = fields.Boolean(
        string='Activate invoice payments')
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
    _payerse_ip_whitelist = [
        "79.136.103.5",
        "94.140.57.180",
        "94.140.57.181",
        "94.140.57.184",
        #DANGER: Only enable when testing locally.
        #"127.0.0.1"
    ]
    
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
        etree.SubElement(buyer_details, "first_name").text = partner_values['first_name'] or ''
        etree.SubElement(buyer_details, "last_name").text = partner_values['last_name'] or ''
        etree.SubElement(buyer_details, "address_line_1").text = partner_values['address'] or ''
        #etree.SubElement(buyer_details, "address_line_2")    #Necessary? Nope.
        etree.SubElement(buyer_details, "postal_code").text = partner_values['zip'] or ''
        etree.SubElement(buyer_details, "city").text = partner_values['city'] or ''
        etree.SubElement(buyer_details, "country_code").text = partner_values['country'] and partner_values['country'].code or ''
        etree.SubElement(buyer_details, "phone_home").text = partner_values['phone'] or ''
        #etree.SubElement(buyer_details, "phone_work").text = partner_values['phone']
        #etree.SubElement(buyer_details, "phone_mobile").text = partner_values['phone']
        etree.SubElement(buyer_details, "email").text = partner_values['email'] or ''
        #etree.SubElement(buyer_details, "organisation").text = partner_values['first_name']
        #etree.SubElement(buyer_details, "orgnr").text = partner_values['first_name']
        #~ if self.payerse_auth_only:
            #~ # All options are stored in the same element as comma separated key value pairs
            #~ etree.SubElement(buyer_details, "options").text = 'auth_only=true'
        
        #Generate purchase data
        purchase = etree.SubElement(root, "purchase")
        etree.SubElement(purchase, "currency").text = tx_values['currency'].name
        etree.SubElement(purchase, "description").text = tx_values['reference']
        #etree.SubElement(purchase, "reference_id").text = tx_values['reference']
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
        etree.SubElement(processing_control, "authorize_notification_url").text = urlparse.urljoin(base_url, '%s?order_id=%s' % (PayerSEController._callback_url, tx_values['reference']))
        etree.SubElement(processing_control, "settle_notification_url").text = urlparse.urljoin(base_url, '%s?order_id=%s' % (PayerSEController._callback_url, tx_values['reference']))
        etree.SubElement(processing_control, "redirect_back_to_shop_url").text = urlparse.urljoin(base_url, tx_values.get('cancel_url', ''))
        
        #Generate other data
        
        database_overrides = etree.SubElement(root, "database_overrides")
        payment_methods = etree.SubElement(database_overrides, "accepted_payment_methods")
        # Can be bank, card, invoice, einvoice, wywallet, enter (= instalment plan), and auto (= card ???)
        if self.payerse_payment_method_auto:
            etree.SubElement(payment_methods, "payment_method").text = "auto"
        else:
            if self.payerse_payment_method_bank:
                etree.SubElement(payment_methods, "payment_method").text = "bank"
            if self.payerse_payment_method_card:
                etree.SubElement(payment_methods, "payment_method").text = "card"
            if self.payerse_payment_method_invoice:
                etree.SubElement(payment_methods, "payment_method").text = "invoice"
            if self.payerse_payment_method_einvoice:
                # Untested because it's not supported by the test account
                etree.SubElement(payment_methods, "payment_method").text = "einvoice"
            if self.payerse_payment_method_wywallet:
                etree.SubElement(payment_methods, "payment_method").text = "wywallet"
            if self.payerse_payment_method_instalment:
                etree.SubElement(payment_methods, "payment_method").text = "enter"
        
        if self.environment == "test":
            etree.SubElement(database_overrides, "test_mode").text = "true"
        else:
            etree.SubElement(database_overrides, "test_mode").text = "false"
        
        etree.SubElement(database_overrides, "debug_mode").text = self.payerse_debug_mode
        lang = partner_values.get('lang', 'en')[:2]
        if lang == 'nb':    # Workaround for norwegian translation.
            lang = 'no'
        etree.SubElement(database_overrides, "language").text = lang
        
        res = etree.tostring(root, pretty_print=False)
        _logger.debug(res)
        return base64.b64encode(res)
    
    def _payerse_generate_checksum(self, data):
        """Generate and return an md5 cheksum."""
        return hashlib.md5(self.payerse_key_1 + data + self.payerse_key_2).hexdigest()
    
    def payerse_form_generate_values(self, partner_values, tx_values):
        """Method that generates the values used to render the form button template."""
        self.ensure_one()
        
        _logger.debug(pprint.pformat(partner_values))
        _logger.debug(pprint.pformat(tx_values))
        
        payer_tx_values = dict(tx_values)
        if not payer_tx_values.get('return_url'):
            payer_tx_values['return_url'] = self.payerse_return_address
        if not payer_tx_values.get('cancel_url'):
            payer_tx_values['cancel_url'] = self.payerse_cancel_address

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
                line_dict['price_including_vat'] = ((line.price_subtotal + tax) / line_dict['quantity']) if line_dict['quantity'] else 0
                line_dict['vat_percentage'] = (tax * 100 / line.price_subtotal) if line.price_subtotal else 0.0
                total += line_dict['quantity'] * line_dict['price_including_vat']
                payer_order_lines.append(line_dict)
                i += 1
            payer_tx_values['payer_order_lines'] = payer_order_lines
        
        #Check that order lines add up to the given total and adjust if necessary
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
    
    def payerse_get_form_action_url(self):
        """Returns the url of the button form."""
        return 'https://secure.payer.se/PostAPI_V1/InitPayFlow'
    
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
        fees = ((percentage / 100.0 * amount + fixed ) / (1 - percentage / 100.0)) if percentage != 100.0 else 0
        return fees


class TxPayerSE(models.Model):
    _inherit = 'payment.transaction'
    
    payerse_payment_type        = fields.Char(string='Payment type')
    payerse_testmode            = fields.Boolean(string='Testmode')
    payerse_added_fee           = fields.Float(string='Added fee')
    payerse_paymentid           = fields.Char(string='Payment ID')
    
    @api.model
    def _payerse_form_get_tx_from_data(self, data):
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
    def _payerse_form_get_invalid_parameters(self, tx, data):
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
    def _payerse_form_validate(self, tx, data):
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
    def payerse_create(self, values):
        acquirer = self.env['payment.acquirer'].browse(values['acquirer_id'])
        values['payerse_testmode'] = True if acquirer.environment == 'test' else False
        
        return values
