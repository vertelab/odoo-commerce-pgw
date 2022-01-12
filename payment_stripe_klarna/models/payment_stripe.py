# coding: utf-8

from collections import namedtuple
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

# The following currencies are integer only, see https://stripe.com/docs/currencies#zero-decimal
INT_CURRENCIES = [
    u'BIF', u'XAF', u'XPF', u'CLP', u'KMF', u'DJF', u'GNF', u'JPY', u'MGA', u'PYG', u'RWF', u'KRW',
    u'VUV', u'VND', u'XOF'
]
STRIPE_SIGNATURE_AGE_TOLERANCE = 600  # in seconds


class PaymentAcquirerStripe(models.Model):
    _inherit = 'payment.acquirer'

    @api.model
    def _add_available_payment_method_types(self, stripe_session_data, tx_values):
        """
        Add payment methods available for the given transaction

        :param stripe_session_data: dictionary to add the payment method types to
        :param tx_values: values of the transaction to consider the payment method types for
        """
        PMT = namedtuple('PaymentMethodType', ['name', 'countries', 'currencies', 'recurrence'])
        all_payment_method_types = [
            PMT('card', [], [], 'recurring'),
            PMT('ideal', ['nl'], ['eur'], 'punctual'),
            PMT('bancontact', ['be'], ['eur'], 'punctual'),
            PMT('eps', ['at'], ['eur'], 'punctual'),
            PMT('giropay', ['de'], ['eur'], 'punctual'),
            PMT('p24', ['pl'], ['eur', 'pln'], 'punctual'),
            PMT('klarna', ['at', 'be', 'de', 'dk', 'es', 'fi', 'fr', 'ie', 'it', 'nl', 'no', 'gb', 'us', 'se'], ['eur', 'sek', 'usd', 'nok', 'dkk', 'gdp'], 'recurring'),
        ]

        existing_icons = [(icon.name or '').lower() for icon in self.env['payment.icon'].search([])]
        linked_icons = [(icon.name or '').lower() for icon in self.payment_icon_ids]

        # We don't filter out pmt in the case the icon doesn't exist at all as it would be **implicit** exclusion
        icon_filtered = filter(lambda pmt: pmt.name == 'card' or
                                           pmt.name in linked_icons or
                                           pmt.name not in existing_icons, all_payment_method_types)
        country = (tx_values['billing_partner_country'].code or 'no_country').lower()
        pmt_country_filtered = filter(lambda pmt: not pmt.countries or country in pmt.countries, icon_filtered)
        currency = (tx_values.get('currency').name or 'no_currency').lower()
        pmt_currency_filtered = filter(lambda pmt: not pmt.currencies or currency in pmt.currencies, pmt_country_filtered)
        pmt_recurrence_filtered = filter(lambda pmt: tx_values.get('type') != 'form_save' or pmt.recurrence == 'recurring',
                                    pmt_currency_filtered)

        available_payment_method_types = map(lambda pmt: pmt.name, pmt_recurrence_filtered)
        for idx, payment_method_type in enumerate(available_payment_method_types):
            stripe_session_data[f'payment_method_types[{idx}]'] = payment_method_type
