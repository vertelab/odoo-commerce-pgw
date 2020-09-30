######## For test_swish_class.py #################
from odoo import models, fields, api

import logging
_logger = logging.getLogger(__name__)

from string import ascii_letters, digits
from random import choice
from lxml import objectify


############# Swish imports ######################
import os
import unittest
from random import randint
import time
import swish

############# From payment.py ###################

import json
import dateutil.parser
import pytz
from werkzeug import urls
from random import randint
import time
from odoo.exceptions import ValidationError
import requests


##################################################

class SwishTest(models.Model):
    _name = 'swish.test'
    _inherit = 'payment.acquirer'

    _description = "Swish server action for testing // ARTUR"


    # Typical data that exists when triggering the payment
    _buyer_values = {
        'partner_name': 'Mitchell Admin',
        'partner_lang': 'sv_SE',
        'partner_email': 'hej@hjehejhejhjeh.se',
        'partner_address': '215 Vine St',
        'partner_city': 'Scranton',
        'partner_zip': '18503',
        'partner_phone': '+1 555-555-5555',
        # 'partner_country': res.country(233,),
        'partner_country_id': 233, 


        'billing_partner_name': 'Mitchell Admin',
        'billing_partner_commercial_company_name': 'YourCompany',
        'billing_partner_lang': 'sv_SE',
        'billing_partner_email': 'hej@hjehejhejhjeh.se',
        'billing_partner_address': '215 Vine St',
        'billing_partner_phone': '+1 555-555-5555',
        'billing_partner_city': 'Scranton',
        'billing_partner_zip': '18503',
        # 'billing_partner_country': res.country(233,),
        'billing_partner_country_id': 233,
        # 'billing_partner_country_name': 'Belgium',
    } 


    def hello(self): 
        _logger.warn("~hejsan svejsan")

    def swish_test(self):
        current_folder = os.path.dirname(os.path.abspath(__file__))
        cert_file_path = os.path.join(current_folder, "cert.pem")
        key_file_path = os.path.join(current_folder, "key.pem")
        cert = (cert_file_path, key_file_path)
        verify = os.path.join(current_folder, "swish.pem")
        
        client = swish.SwishClient(
            environment=swish.Environment.Test,
            merchant_swish_number='1231181189',
            cert=cert,
            verify=verify
        )

        payer_alias = '467%i' % randint(1000000, 9999999)
        payment = client.create_payment(
            payee_payment_reference='ServerActionTesting',
            callback_url='https://swish.azzar.pl/payment/swish',
            payer_alias=payer_alias,
            amount=100,
            currency='SEK',
            message= u'Kingston öö Flash Drive 8 GB'
        )

    # inspired by, maybe copy code from the file and adapt it to swish.
    # /usr/share/core-odoo/addons/payment_paypal/tests/test_paypal.py
    def test_swish_form_management(self):

        # Generate random test_ref
        #  
        test_ref = ''.join([choice(ascii_letters + digits) for i in range(32)])
        _logger.warn(" ~ test_ref %s" % test_ref)
        
        # Typical return data from swish
        # Date format: 'YYYY-MM-DDThh:mm:ssTZD'
        swish_data =  {
            'id': '1E22B9F21B92459CA16FD4B20F6272EF',
            'payeePaymentReference': test_ref,
            'paymentReference': '8A5AA8BF2C074665A0A85B6B0E329AA5',
            'callbackUrl': 'https://swish.azzar.pl/payment/swish',
            'payerAlias': '15555555555',
            'payeeAlias': '1231181189',
            'currency': 'SEK',
            'message': 'Order ',
            'errorMessage': None,
            'status': 'PAID',
            'amount': '2164.12',
            'dateCreated': '2020-09-04T14:00:45.748+0000',
            'datePaid': '2020-09-04T14:00:49.748+0000',
            'errorCode': None
        }     

        # Swish data with error codes.
        swish_data_error_data =  {
            'id': '1E22B9F21B92459CA16FD4B20F6272EF',
            'payeePaymentReference': test_ref,
            'paymentReference': '8A5AA8BF2C074665A0A85B6B0E329AA5',
            'callbackUrl': 'https://swish.azzar.pl/payment/swish',
            'payerAlias': '15555555555',
            'payeeAlias': '1231181189',
            'currency': 'SEK',
            'message': 'Order ',
            'errorMessage': 'A serius error message',
            'status': 'ERROR',
            'amount': '2164.12',
            'dateCreated': '2020-09-04T14:00:45.748+0000', 
            'datePaid': '2020-09-04T14:00:49.748+0000',
            'errorCode': 'An error code'
        }


        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.env['payment.acquirer'].search([('name','=','Swish Pay')]).id,
            'currency_id': self.env['res.currency'].search([('name','=','EUR')]).id,
            'reference': test_ref,
            'partner_name': self._buyer_values['partner_name'],
            'partner_country_id': self._buyer_values['partner_country_id']
        })

        # validate it
        self.env['payment.transaction'].form_feedback(swish_data_error_data, 'swish')

        txs = self.env['payment.transaction'].search([])
        for tx in txs:
            if tx.reference == test_ref:
                _logger.warn("~ transaction with reference found = %s" % test_ref)
                _logger.warn("~ transaction state = %s:" % tx.state)


    def test_swish_render(self):
        _logger.warn("~ %s" "TEST SWISH RENDER" )
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        # ----------------------------------------
        # Test: button direct rendering
        # This does not work, yet beacuse the controller needs be working.
        # ----------------------------------------

        test_ref = ''.join([choice(ascii_letters + digits) for i in range(32)])
        

        # render the button
        res = self.render(
            test_ref, 
            2164.12, 
            1, 
            partner_id=self.env['res.partner'].search([('id','=','3')]).id, 
            values=self._buyer_values
        )

        _logger.warn("~ res %s" %  res)

        form_values = {
            'cmd': '_xclick',
            'business': 'tde+paypal-facilitator@odoo.com',
            'item_name': 'YourCompany: %s' %test_ref,
            'item_number': test_ref,
            'first_name': 'Norbert',
            'last_name': 'Buyer',
            'amount': '0.01',
            'currency_code': 'EUR',
            'address1': 'Huge Street 2/543',
            'city': 'Sin City',
            'zip': '1000',
            'country': 'BE',
            'email': 'norbert.buyer@example.com',
            # TODO:Make test and use url fields like 'return', 'notify_url', 'cancel_return', 'custom'
            # See /usr/share/core-odoo/addons/payment_paypal/tests/test_paypal.py
        }

        # check form result
        tree = objectify.fromstring(res)

        # check response in form and so on...