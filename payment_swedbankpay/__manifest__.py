# -*- coding: utf-8 -*-
##############################################################################
#
# Odoo, Open Source Management Solution, third party addon
# Copyright (C) 2020++ Vertel AB (<http://vertel.se>).
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
# ~ 'external_dependencies': {'python': ['swedbankpay']},
##############################################################################
{
        'name': 'SwedbankPay Payment Acquirer',
        'version': '12.0.0.1',
        'summary': 'Payment Acquirer: Swedbank Pay Implementation',
        'category': 'Hidden',
        'description': """SwedbankPay Payment Acquirer.""",
        'author': 'Vertel AB',
        'license': 'AGPL-3',
        'website': 'http://www.vertel.se',
        'depends': ['payment'],
        'data': ['swedbankpay.xml',
                'payment_acquirer.xml',
                'swedbankpay_data.xml',
                'res_cnfig_view.xml',
        ],
        'installable': True,
}

# vim:expandtab:smartindent:tabstop=4s:softtabstop=4:shiftwidth=4: