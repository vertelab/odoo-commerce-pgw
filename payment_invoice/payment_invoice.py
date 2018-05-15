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

from openerp import models, fields, api, _, tools, http
from openerp.exceptions import except_orm, Warning, RedirectWarning, ValidationError
from openerp.http import request
from openerp.tools.float_utils import float_compare
import pprint
import werkzeug
import logging

_logger = logging.getLogger(__name__)

class InvoicePaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'
    
    invoice_mark_done = fields.Boolean(string='Mark Transactions as Done', help="Mark transactions as done when confirmed in the webshop. This will confirm the sale order.")
    
    @api.model
    def _get_providers(self):
        providers = super(InvoicePaymentAcquirer, self)._get_providers()
        providers.append(['invoice', _('Invoice')])
        return providers
    
    @api.multi
    def invoice_get_form_action_url(self):
        return '/payment/invoice/feedback'
    
    @api.model
    def _format_invoice_data(self):
        banks = self.env.user.company_id.bank_ids.filtered('footer')
        # filter only bank accounts marked as visible
        #~ banks = self.env['res.partner.bank'].search([('id', 'in', bank_ids), ('footer', '=', True)])
        bank_title = _('Bank Accounts') if len(banks) > 1 else _('Bank Account')
        bank_accounts = ''.join(['<ul>'] + ['<li>%s</li>' % bank.name for bank in banks] + ['</ul>'])
        post_msg = '''<div>
<h3>Please use the following invoice details</h3>
<h4>%(bank_title)s</h4>
%(bank_accounts)s
<h4>Communication</h4>
<p>Please use the order name as communication reference.</p>
</div>''' % {
            'bank_title': bank_title,
            'bank_accounts': bank_accounts,
        }
        return post_msg
    
    @api.model
    @api.returns('self', lambda value: value.id)
    def create(self, values):
        """ Hook in create to create a default post_msg. This is done in create
        to have access to the name and other creation values. If no post_msg
        or a void post_msg is given at creation, generate a default one. """
        if values.get('provider') == 'invoice' and not values.get('post_msg'):
            values['post_msg'] = self._format_invoice_data()
        return super(InvoicePaymentAcquirer, self).create(values)


class InvoicePaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    @api.model
    def _invoice_form_get_tx_from_data(self, data):
        reference, amount, currency_name = data.get('reference'), data.get('amount'), data.get('currency_name')
        tx = self.search([('reference', '=', reference)])

        if not tx or len(tx) > 1:
            error_msg = 'received data for reference %s' % (pprint.pformat(reference))
            if not tx:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return tx
    
    @api.model
    def _invoice_form_get_invalid_parameters(self, tx, data):
        invalid_parameters = []

        if float_compare(float(data.get('amount', '0.0')), tx.amount, 2) != 0:
            invalid_parameters.append(('amount', data.get('amount'), '%.2f' % tx.amount))
        if data.get('currency') != tx.currency_id.name:
            invalid_parameters.append(('currency', data.get('currency'), tx.currency_id.name))

        return invalid_parameters

    @api.model
    def _invoice_form_validate(self, tx, data):
        if tx.acquirer_id.invoice_mark_done:
            _logger.info('Validated invoice payment for tx %s: set as done' % (tx.reference))
            return tx.write({'state': 'done'})
        else:
            _logger.info('Validated invoice payment for tx %s: set as pending' % (tx.reference))
            return tx.write({'state': 'pending'})

class InvoiceController(http.Controller):
    _accept_url = '/payment/invoice/feedback'

    @http.route(['/payment/invoice/feedback'], type='http', auth='none')
    def invoice_form_feedback(self, **post):
        _logger.warn('Here We asarer')
        _logger.info('Beginning form_feedback with post data %s', pprint.pformat(post))  # debug
        request.env['payment.transaction'].sudo().form_feedback(post, 'invoice')
        return werkzeug.utils.redirect(post.pop('return_url', '/'))
