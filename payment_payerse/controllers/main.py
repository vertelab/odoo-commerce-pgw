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

from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import http
from openerp.http import request
import openerp.tools
import pprint

import logging
_logger = logging.getLogger(__name__)

#~ import string
#~ import urllib2
#~ import werkzeug

class PayerSEController(http.Controller):
    _callback_url = "/payment/payerse/verify"
    
    @http.route('/payment/payerse/verify', type='http', auth='public', method='GET')
    def auth_payment(self, **post):
        _logger.debug('Processing Payer.se callback with post data:\n%s' % pprint.pformat(post))  # debug
        data = [post, request.httprequest.url, request.httprequest.remote_addr]
        res = request.env['payment.transaction'].sudo().form_feedback(data, 'payerse')
        _logger.debug('value of res: %s' % res)
        if res:
            return 'TRUE'
        else:
            return ''
    
    # TODO: Delete test function or get rekt.
    #~ @http.route('/payment/payerse/test', type='http', auth='public', method='GET')
    #~ def test(self, **post):
        #~ url = request.httprequest.url
        #~ url=urllib2.unquote(url).decode('utf8')
        #~ url = url.replace("/payment/payerse/test", "/payment/payerse/verify")
        #~ acquirer = request.env['payment.acquirer'].browse(2)
        #~ return acquirer._payerse_generate_checksum(url)

