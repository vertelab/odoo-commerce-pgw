import json

from odoo import models, fields, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    transaction_ids = fields.Many2many('payment.transaction', compute='_compute_transactions',
                                       string='SO Transactions', copy=False, readonly=True)
    authorized_transaction_ids = fields.Many2many('payment.transaction', compute='_compute_transactions',
                                                  string='SO Authorized Transactions', copy=False, readonly=True)

    @api.depends('origin')
    def _compute_transactions(self):
        for rec in self:
            if rec.origin and rec.origin.startswith('S'):
                sale_id = self.env['sale.order'].search([('name', '=', rec.origin)], limit=1)
                if sale_id:
                    rec.transaction_ids = sale_id.transaction_ids.ids
                    rec.authorized_transaction_ids = sale_id.authorized_transaction_ids.ids
                else:
                    rec.transaction_ids = False
                    rec.authorized_transaction_ids = False
            else:
                rec.transaction_ids = False
                rec.authorized_transaction_ids = False

    def button_validate(self):
        res = super(StockPicking, self).button_validate()
        done_transactions = self.transaction_ids.filtered(lambda trans: trans.state == 'done')
        for _trans in done_transactions:
            payment_data = _trans._payson_payment_verification()

            payment_data = {
                "status": "shipped",
                "id": _trans.payson_transaction_id,
                "merchant": payment_data.get('merchant'),
                "customer": payment_data.get('customer'),
                "order": payment_data.get('order')
            }

            _trans.acquirer_id._payson_request(
                data=json.dumps(payment_data),
                endpoint=f"/checkouts/{_trans.payson_transaction_id}",
                method='PUT'
            )

        return res
