# -*- coding: utf-8 -*-
##############################################################################
#
# OpenERP, Open Source Management Solution, third party addon
# Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
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

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo import http
from odoo.http import request
import werkzeug
import requests
import json

from swish import client
from swish import environment
import swish as sw

import logging
_logger = logging.getLogger(__name__)

class SwishController(http.Controller):

    @http.route('/payment/swish', type='json', auth='public', method='POST', csrf=False)
    def swish_callback(self, **post): 
        data = json.loads(request.httprequest.data)
                    
        # Form feedback also calls the functions 
        # * _swish_form_get_tx_from_data 
        # * _swish_form_get_invalid_parameters
        # * _swish_form_validate
        res = request.env['payment.transaction'].sudo().form_feedback(data=data, acquirer_name='swish')
