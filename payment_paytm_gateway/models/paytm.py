# -*- coding: utf-8 -*-
# Part of Odoo Module Developed by MaxVueTech
# See LICENSE file for full copyright and licensing details.

""" This file manages all the operations and the functionality of the gateway
integration """

import logging

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_paytm_gateway.models.checksum import \
    generate_checksum, verify_checksum
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

globvar = 0


class AcquirerPaytm(models.Model):

    """ Class to handle all the functions required in integration """
    _inherit = 'payment.acquirer'

    provider = fields.Selection(selection_add=[('paytm_payment', 'Paytm')])
    paytm_mid = fields.Char('Paytm Merchant Identifier',
                            required_if_provider='paytm_payment')
    paytm_key = fields.Char('Paytm Merchant Key',
                            required_if_provider='paytm_payment')
    paytm_website = fields.Char('Paytm Website',
                                required_if_provider='paytm_payment')
    paytm_channel = fields.Char('Paytm Channel',
                                required_if_provider='paytm_payment')
    paytm_industry = fields.Char('Paytm Industry',
                                 required_if_provider='paytm_payment')

    @api.model
    def _get_paytm_urls(self, environment):
        """ paytm URLS """
        if environment == 'prod':
            return {
                'paytm_form_url':
                'https://pguat.paytm.com/oltp-web/processTransaction?orderid=',
            }
        else:
            return {
                'paytm_form_url':
                'https://pguat.paytm.com/oltp-web/processTransaction?orderid=',
            }

    @api.multi
    def paytm_payment_form_generate_values(self, values):
        """ Gathers the data required to make payment """
        global globvar
        globvar = values['reference']
        paytm_values = dict(values)
        params = {
            'MID': self.paytm_mid,
            'ORDER_ID': values['reference'],
            'CUST_ID': values['reference'],
            'TXN_AMOUNT': values['amount'],
            'CHANNEL_ID': self.paytm_channel,
            'INDUSTRY_TYPE_ID': self.paytm_industry,
            'WEBSITE': self.paytm_website,
            'MOBILE_NO': values['billing_partner_phone'] or '',
            'EMAIL': values['billing_partner_email'] or '',
            'CITY': values['billing_partner_city'] or '',
            'STATE': values['billing_partner_state'].name or '',
            'PINCODE': values['billing_partner_zip'] or ''
        }
        checksum = generate_checksum(params, self.paytm_key)
        paytm_values.update(params)
        paytm_values['CHECKSUMHASH'] = checksum
        return paytm_values

    @api.multi
    def paytm_payment_get_form_action_url(self):
        """ Get the form url of Paytm"""
        url = self._get_paytm_urls(self.environment)['paytm_form_url']
        url = url + globvar
        return url


class TxPaytmPayment(models.Model):

    """ Handles the functions for validation after transaction is processed """
    _inherit = 'payment.transaction'

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------
    @api.model
    def _paytm_payment_form_get_tx_from_data(self, data):
        """ Verify the validity of data coming from paytm """
        reference = data.get('ORDERID')
        if not reference:
            error_msg = _(
                'paytm: received data with missing reference (%s)'
            ) % (reference)
            _logger.info(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.env['payment.transaction'
                          ].search([('reference', '=', reference)])
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Paytm: received data for reference %s' % (
                reference)
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.info(error_msg)
            raise ValidationError(error_msg)
        return tx_ids[0]

    @api.multi
    def _paytm_payment_form_validate(self, data):
        """ Verify the validity of data  coming from paytm """
        res = {}
        status = data.get('STATUS')
        if status == 'TXN_SUCCESS':
            checksum = data['CHECKSUMHASH']
            acquirer = self.env['payment.acquirer'
                                ].search([('provider', '=', 'paytm_payment')])
            check_data = verify_checksum(data, acquirer.paytm_key, checksum)
            if check_data:
                _logger.info(
                    'Validated Paytm payment for tx %s: set as '
                    'done' % (self.reference))
                res.update(state='done', date_validate=data.get(
                    'payment_date', fields.datetime.now()))
                return self.write(res)
            else:
                error = 'Received unrecognized data for paytm payment %s, '\
                    'set as error' % self.reference
                _logger.info(error)
                res.update(state='cancel', state_message=error)
                return self.write(res)
        else:
            _logger.info(data.get('RESPMSG'))
            res.update(state='cancel', state_message=data.get('RESPMSG'))
            return self.write(res)
