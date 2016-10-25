# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2016 Vertel AB (<http://vertel.se>).
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp import api, models, fields, _
import logging
_logger = logging.getLogger(__name__)

class PaymentAcquirer(models.Model):
    _inherit = 'payment.acquirer'
    
    invoice_type_id = fields.Many2one('sale_journal.invoice.type', 'Invoice Type', help="Generate invoice based on the selected option.")


class PaymentTransaction(models.Model):
    _inherit = 'payment.transaction'
    
    @api.model
    def create(self, values):
        #~ msg = '\ncreate'
        #~ for key in values:
            #~ msg += '\n%s: %s' % (key, values[key])
        #~ _logger.warn(msg)
        order = self.env['sale.order'].browse(values.get('sale_order_id'))
        acquirer_id = values.get('acquirer_id')
        if order and acquirer_id:
            acquirer = self.env['payment.acquirer'].search_read([('id', '=', acquirer_id)], ['invoice_type_id'])
            if acquirer:
                invoice_type_id = acquirer[0]['invoice_type_id'] and acquirer[0]['invoice_type_id'][0] or None
                _logger.warn(type(invoice_type_id))
                order.write({'invoice_type_id': invoice_type_id})
        return super(PaymentTransaction, self).create(values)
    
    @api.multi
    def write(self, values):
        #~ msg = '\nwrite'
        #~ for key in values:
            #~ msg += '\n%s: %s' % (key, values[key])
        #~ _logger.warn(msg)
        if 'acquirer_id' in values:
            acquirer = self.env['payment.acquirer'].search_read([('id', '=', acquirer_id)], ['invoice_type_id'])
            if acquirer:
                invoice_type_id = acquirer[0]['invoice_type_id']
                for record in self:
                    record.sale_order_id.write({'invoice_type_id': invoice_type_id})
        return super(PaymentTransaction, self).write(values)
