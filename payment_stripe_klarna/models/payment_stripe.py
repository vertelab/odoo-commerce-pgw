# coding: utf-8

from collections import namedtuple
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class PaymentAcquirerStripe(models.Model):
    _inherit = 'payment.acquirer'

    @api.model
    def _add_available_payment_method_types(self, stripe_session_data, tx_values):
        """
        Appends Klarna as a Payment as a usable Payment alternative for Stripe.

        https://stripe.com/docs/payments/klarna

        :param stripe_session_data: dictionary to add the payment method types to
        :param tx_values: values of the transaction to consider the payment method types for
        """
        super(PaymentAcquirerStripe, self)._add_available_payment_method_types(
            stripe_session_data, tx_values
        )
        PMT = namedtuple('PaymentMethodType', ['name', 'countries', 'currencies', 'recurrence'])

        # https://stripe.com/docs/payments/klarna
        all_payment_method_types = [
            PMT('klarna',
                ['at', 'be', 'de', 'dk', 'es', 'fi', 'fr', 'ie', 'it', 'nl',
                 'no', 'gb', 'se'], # 'us', # Removed see comment on currency
                ['eur', 'sek', 'nok', 'dkk', 'gdp'], # usd seem ok in doc but not in Odoo - Note: usd doesn't support 'Pay Now'
                 'recurring'),
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

        # stripe_session_data has indices in the dict key which makes following
        # rows a candidate for ugly code.
        # TODO: Refactor the snippet below - There is only one defined pmt in
        #       this method
        available_payment_method_types = map(lambda pmt: pmt.name, pmt_recurrence_filtered)
        for payment_method_type in available_payment_method_types:
            # Counting previous methods
            count_pmts = len(tuple(filter(lambda X: 'payment_method_types[' in X,
                                    stripe_session_data)))
            stripe_session_data[f'payment_method_types[{count_pmts}]'] = payment_method_type
