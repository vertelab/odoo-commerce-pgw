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
import base64
import hashlib
import logging
from openerp.addons.payment_payer_se.controllers.main import PayerSEController

_logger = logging.getLogger(__name__)

class AcquirerPayerSE(models.Model):
    _inherit = 'payment.acquirer'
    
    payerse_agent_id          = fields.Char(string='Payer.se Agent ID', required_if_provider='payerse')
    payerse_key_1              = fields.Char(string='Payer.se Key 1/Key A', help='The first preshared key.', required_if_provider='payerse')
    payerse_key_2              = fields.Char(string='Payer.se Key 2/Key B', help='The second preshared key.', required_if_provider='payerse')
    payerse_payment_method_card = fields.Boolean(string='Allow card payments.', help='Allow card payment.')
    payerse_payment_method_bank = fields.Boolean(string='Allow bank payments.', help='Allow bank payment.')
    payerse_payment_method_phone = fields.Boolean(string='Allow phone payments.', help='Allow phone payment.')
    payerse_payment_method_invoice = fields.Boolean(string='Allow invoice payments.', help='Allow card payment.')
    
    # Server 2 server
    #payerse_api_enabled                 = fields.boolean('Use Rest API')
    #payerse_api_username                = fields.char('Rest API Username')
    #payerse_api_password                = fields.char('Rest API Password')
    #payerse_api_access_token            = fields.char('Access Token')
    #payerse_api_access_token_validity   = fields.Datetime('Access Token Validity')
    

    def _get_providers(self, cr, uid, context=None):
        providers = super(AcquirerPayerSE, self)._get_providers(cr, uid, context=context)
        providers.append(['payerse', 'Payer.se'])
        return providers
    
    @api.v8
    def _payerse_generate_xml_data(self, partner_values, tx_values, order):
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
        etree.SubElement(buyer_details, "adress_line_1").text = partner_values['address']
        #etree.SubElement(buyer_details, "adress_line_2")    #Necessary?
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
        purchase_list = etree.SubElement(purchase, "purchase_list")
        
        #Generate product lines
        i = 1
        for line in order.order_line:
            freeform_purchase = etree.SubElement(purchase_list, "freeform_purchase")
            etree.SubElement(freeform_purchase, "line_number").text = unicode(i)
            etree.SubElement(freeform_purchase, "description").text = line.name
            etree.SubElement(freeform_purchase, "price_including_vat").text = unicode(100)
            etree.SubElement(freeform_purchase, "vat_percentage").text = unicode(25)
            etree.SubElement(freeform_purchase, "quantity").text = unicode(3) #line.product_uom_qty)
            i += 1
        
        #Generate callback data
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        processing_control = etree.SubElement(root, "processing_control")
        etree.SubElement(processing_control, "success_redirect_url").text = urlparse.urljoin(base_url, PayerSEController._success_url)
        etree.SubElement(processing_control, "authorize_notification_url").text = urlparse.urljoin(base_url, PayerSEController._auth_url)
        etree.SubElement(processing_control, "settle_notification_url").text = urlparse.urljoin(base_url, PayerSEController._settle_url)
        etree.SubElement(processing_control, "redirect_back_to_shop_url").text = urlparse.urljoin(base_url, tx_values.get('return_url', ''))
        
        #Generate other data
        
        database_overrides = etree.SubElement(root, "database_overrides")
        payment_methods = etree.SubElement(database_overrides, "accepted_payment_methods")
        if self.payerse_payment_method_bank:
            etree.SubElement(payment_methods, "payment_method").text = "bank"
        if self.payerse_payment_method_card:
            etree.SubElement(payment_methods, "payment_method").text = "card"
        if self.payerse_payment_method_invoice:
            etree.SubElement(payment_methods, "payment_method").text = "invoice"
        if self.payerse_payment_method_phone:
            etree.SubElement(payment_methods, "payment_method").text = "phone"
        
        if self.environment == "test":
            etree.SubElement(database_overrides, "test_mode").text = "true"
        else:
            etree.SubElement(database_overrides, "test_mode").text = "false"
        
        #TODO: how and when to use debug mode?
        etree.SubElement(database_overrides, "debug_mode").text = "verbose"
        
        #TODO: Add support for other languages
        etree.SubElement(database_overrides, "language").text = "sv"
        
        _logger.info(etree.tostring(root, pretty_print=True))
        
        return base64.b64encode(etree.tostring(root, pretty_print=False))
    
    def _payerse_generate_checksum(self, data):
        return hashlib.md5(self.payerse_key_1 + data + self.payerse_key_2).hexdigest()
    
    @api.multi
    def payerse_form_generate_values(self, partner_values, tx_values):
        """method that generates the values used to render the form button template."""
        self.ensure_one()
        _logger.info(partner_values)
        _logger.info(tx_values)
        
        reference = tx_values['reference']      #Orderns referens! WOHO!
        order = self.env['sale.order'].search([['name', '=', reference]])
        
        xml_data = self._payerse_generate_xml_data(partner_values, tx_values, order)
        
        payer_tx_values = dict(tx_values) #?????????
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
        """method that returns the url of the button form. It is used for example in
        ecommerce application, if you want to post some data to the acquirer."""
        return 'https://secure.payer.se/PostAPI_V1/InitPayFlow'
    
    @api.multi
    def payerse_compute_fees(self, amount, currency_id, country_id):
        """computed the fees of the acquirer, using generic fields
        defined on the acquirer model (see fields definition)."""
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
