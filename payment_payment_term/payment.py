# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2017 Vertel AB (<http://vertel.se>).
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

from openerp import models, fields, api, _, tools
from openerp.exceptions import except_orm, Warning, RedirectWarning

import logging
_logger = logging.getLogger(__name__)

class Acquirer(models.Model):
    _inherit = 'payment.acquirer'

    payment_term_ids = fields.Many2many(comodel_name='account.payment.term', string='Payment Terms')

    @api.model
    def get_payment_terms(self, acquirers, user):
        alist = []
        for acquirer in acquirers:
            if not acquirer.payment_term_ids or (user.partner_id.commercial_partner_id.property_payment_term in acquirer.payment_term_ids):
                alist.append(acquirer)
        return alist
