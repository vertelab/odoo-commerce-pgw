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
from openerp.exceptions import except_orm, Warning, RedirectWarning
import logging

_logger = logging.getLogger(__name__)

class sale_order(models.Model):
    _inherit = 'sale.order'
    
    @api.multi
    def action_button_confirm(self):
        super(sale_order, self).action_button_confirm()
        _logger.warn('action_button_confirm\nstate: %s\ntx_id: %s\ntx_id.state: %s\naqcuirer_id.validation: %s\nactive_id: %s' % (self.state, self.payment_tx_id.id, self.payment_tx_id.state, self.payment_tx_id.acquirer_id.validation, self._context.get('active_id')))
        if self.state in ['manual'] and self.payment_tx_id and\
        self.payment_tx_id.state in ['done'] and\
        self.payment_tx_id.acquirer_id.validation == 'automatic' and\
        not self._context.get('active_id'):
            _logger.warn('inside if statement')
            new_context = dict(self._context)
            new_context['active_id'] = self.id
            new_context['open_invoices'] = True
            wizard = self.env["sale.advance.payment.inv"].with_context(new_context).create({})
            new_context['active_ids'] = [self.id]
            res = wizard.with_context(new_context).create_invoices()
            _logger.warn('res: %s' % res)
            inv = self.env['account.invoice'].browse(res['res_id'])
            inv.signal_workflow('invoice_open')
            journal = self.env['account.journal'].browse(17)
            
            values = {
                'journal_id': journal.id,
                'account_id': journal.default_credit_account_id.id,
                'partner_id': self.env['res.partner']._find_accounting_partner(inv.partner_id).id,
                'amount': inv.type in ('out_refund', 'in_refund') and -inv.residual or inv.residual,
                'reference': inv.name,
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
            }
            values_upd = self.env['account.voucher'].recompute_voucher_lines(values['partner_id'], values['journal_id'], values['amount'], inv.currency_id.id, values['type'], inv.date_invoice)['value']
            if values_upd.get('line_cr_ids'):
                values_upd['line_cr_ids'] = [(0, 0, values_upd['line_cr_ids'][0])]
            del values_upd['line_dr_ids']
            new_context = {
                'close_after_process': True,
                'invoice_type': inv.type,
                'invoice_id': inv.id,
                'type': inv.type in ('out_invoice','out_refund') and 'receipt' or 'payment',
            }
            values.update(values_upd)
            _logger.warn(values)
            voucher = self.env['account.voucher'].create(values)
            
            voucher.signal_workflow('proforma_voucher')
        return True
