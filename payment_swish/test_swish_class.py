##################################################
from odoo import models, fields, api

############# Swish imports ######################
import os
import unittest
from random import randint
import time

import swish

#################################################

import logging
_logger = logging.getLogger(__name__)


############# From payment.py ###################



import json

import dateutil.parser
import pytz
from werkzeug import urls

# These seem unnecesary...
from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paypal.controllers.main import PaypalController
from odoo.tools.float_utils import float_compare

from random import randint
import time


#################################################

class SwishTest(models.Model):
    _name = 'swishsa.test'
    _inherit = 'payment.acquirer'

    _description = "Swish server action for testing // ARTUR"


    def search_for(self):

        # tx = self.env['payment.transaction'].search([]) # Tar upp alla... 
        # for t in tx:
        #     _logger.warn("\n\n\n <<<<<<<<<<<<<<<<<<< %s \n" % t.read() )

        
        # Detta funkar lol....
        a_reference = 'SO036-25'
        tr = self.env['payment.transaction'].search([
            ('reference', '=', a_reference)
        ])
        
        _logger.warn("\n\n\n <<<<<<<<<    TR   <<<<<<<<<< %s \n" % tr.read() )

    def swish_test(self):
        _logger.warn("\n\n\n <<<<<<<<<<<<<<<<<<< %s \n" % 'SWISH TEST!!!')

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
    def test_20_paypal_form_management(self):


        swish_data =  {'id': '1E22B9F21B92459CA16FD4B20F6272EF',
                    'payeePaymentReference': 'SO036-34',
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

        
        
        # self.env['payment.transaction'].form_feedback(swish_data, 'swish')
    """ 
        # create tx
        tx = self.env['payment.transaction'].create({
            'amount': 1.95,
            'acquirer_id': self.paypal.id,
            'currency_id': self.currency_euro.id,
            'reference': 'test_ref_2',
            'partner_name': 'Norbert Buyer',
            'partner_country_id': self.country_france.id})

        # validate it
        tx.form_feedback(swish_data, 'paypal')

        
        # check
        self.assertEqual(tx.state, 'pending', 'paypal: wrong state after receiving a valid pending notification')
        self.assertEqual(tx.state_message, 'multi_currency', 'paypal: wrong state message after receiving a valid pending notification')
        self.assertEqual(tx.acquirer_reference, '08D73520KX778924N', 'paypal: wrong txn_id after receiving a valid pending notification')

        # update tx
        tx.write({
            'state': 'draft',
            'acquirer_reference': False})

        # update notification from paypal
        paypal_post_data['payment_status'] = 'Completed'
        # validate it
        tx.form_feedback(paypal_post_data, 'paypal')
"""

        