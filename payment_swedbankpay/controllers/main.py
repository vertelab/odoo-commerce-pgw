# Part of Odoo. See LICENSE file for full copyright and licensing details.

import hmac
import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.addons.payment import utils as payment_utils
from odoo.http import request


_logger = logging.getLogger(__name__)


class SwedbankpayController(http.Controller):
    _webhook_url = '/payment/swedbankpay/webhook'
    _cancel_url = '/payment/swedbankpay/cancel'
    _complete_url = '/payment/swedbankpay/complete'

    @http.route(
        _cancel_url, type='http', auth='public', methods=['GET'], csrf=False, save_session=False
    )
    def swedbankpay_return_from_canceled_checkout(self, tx_ref, return_access_tkn):
        """ Process the transaction after the customer has canceled the payment.

        :param str tx_ref: The reference of the transaction having been canceled.
        :param str return_access_tkn: The access token to verify the authenticity of the request.
                                      swedbankpay forbids any parameter with the name "token" inside.
        """
        _logger.info(
            "Handling redirection from swedbankpay for cancellation of transaction with reference %s",
            tx_ref,
        )

        tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
            'swedbankpay', {'tx_ref': tx_ref}
        )
        if not payment_utils.check_access_token(return_access_tkn, tx_ref):
            raise Forbidden()
        tx_sudo._handle_notification_data('swedbankpay', {})

        return request.redirect('/payment/status')

    @http.route(_complete_url, type='http', methods=['GET'], auth='public', csrf=False)
    def swedbankpay_complete_url(self, tx_ref, return_access_tkn):
        """ Process the notification data sent by swedbankpay to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """

        _logger.info(
            "Handling redirection from swedbankpay for completion of transaction with reference %s",
            tx_ref,
        )

        if not payment_utils.check_access_token(return_access_tkn, tx_ref):
            raise Forbidden()

        return request.redirect('/payment/status')

    @http.route(_webhook_url, type='http', methods=['POST'], auth='public', csrf=False)
    def swedbankpay_webhook(self):
        """ Process the notification data sent by swedbankpay to the webhook.

        :return: An empty string to acknowledge the notification.
        :rtype: str
        """
        data = request.get_json_data()
        _logger.info("Notification received from swedbankpay with data:\n%s", pprint.pformat(data))

        try:
            # Check the origin and integrity of the notification
            tx_sudo = request.env['payment.transaction'].sudo()._get_tx_from_notification_data(
                'swedbankpay', data
            )

            # Handle the notification data
            tx_sudo._handle_notification_data('swedbankpay', data)
        except ValidationError:  # Acknowledge the notification to avoid getting spammed
            _logger.warning(
                "unable to handle the notification data; skipping to acknowledge", exc_info=True
            )
        return ''
