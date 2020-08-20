# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by MaxVueTech
# See LICENSE file for full copyright and licensing details.
{
    'name': 'Paytm Payment Acquirer',
    'category': 'Payment Gateway',
    'summary': 'Payment Acquirer: Paytm Implementation',
    'version': '1.0',
    'author': 'MaxVueTech',
    'website':'http://maxvuetech.com',
    'description': """Paytm Payment Acquirer""",
    'depends': ['payment'],
    'data': [
        'views/paytm.xml',
        'views/payment_acquirer.xml',
        'data/paytm.xml',
    ],
    'images': [
        'static/description/paytm_payment_gateway_banner.png',
    ],
}
