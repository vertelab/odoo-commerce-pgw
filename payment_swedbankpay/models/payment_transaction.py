import logging
import pprint
import json

import requests
from werkzeug.urls import url_join
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.http import request
from werkzeug import urls
from odoo.addons.payment_swedbankpay import const
from odoo.addons.payment import utils as payment_utils
from odoo import api, fields, models
from odoo.addons.payment_swedbankpay.controllers.main import SwedbankpayController
from odoo.exceptions import UserError, ValidationError


_logger = logging.getLogger(__name__)


class TxSwedbankPay(models.Model):
    _inherit = 'payment.transaction'

    swedbankpay_transaction_uri = fields.Char('Swedbank pay transaction URI')

    def _get_specific_rendering_values(self, processing_values):
        """ Return a dict of provider-specific values used to process the transaction.

        For a provider to add its own processing values, it must overwrite this method and return a
        dict of provider-specific values based on the generic values returned by this method.
        Provider-specific values take precedence over those of the dict of generic processing
        values.

        :param dict processing_values: The generic processing values of the transaction.
        :return: The dict of provider-specific processing values.
        :rtype: dict
        """

        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != 'swedbankpay':
            return res

        # Initiate the payment and retrieve the payment link data.
        payment_order = self._swedbankpay_create_order()

        print("payment_order", payment_order)

        payment_link_data = list(filter(
            lambda operation: operation.get('rel') == 'redirect-checkout', payment_order.get('operations')
        ))[0]

        self.provider_reference = payment_order.get('paymentOrder', {}).get('id', '').split('/')[-1]

        rendering_values = {
            'api_url': payment_link_data.get('href'),
        }
        return rendering_values

    def _swedbankpay_create_order(self, customer_id=None):
        """ Create and return an Order object to initiate the payment.

        :param str customer_id: The ID of the Customer object to assign to the Order for
                                non-subsequent payments.
        :return: The created Order.
        :rtype: dict
        """
        payload = self._swedbankpay_prepare_order_payload(customer_id=customer_id)
        _logger.info(
            "Sending '/psp/paymentorders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(payload)
        )
        order_data = self.provider_id._swedbankpay_make_request('/psp/paymentorders', payload=payload)
        _logger.info(
            "Response of '/psp/paymentorders' request for transaction with reference %s:\n%s",
            self.reference, pprint.pformat(order_data)
        )
        return order_data

    def _swedbankpay_prepare_order_payload(self, customer_id=None):
        base_url = self.provider_id.get_base_url()

        cancel_url = urls.url_join(base_url, SwedbankpayController._cancel_url)
        complete_url = urls.url_join(base_url, SwedbankpayController._complete_url)
        url_params = {
            'tx_ref': self.reference,
            'return_access_tkn': payment_utils.generate_access_token(self.reference),
        }

        payload = json.dumps({
            "paymentorder": {
                "operation": "Purchase",
                "currency": self.currency_id.name,
                "amount": int(self.amount * 100),
                "vatAmount": 0,
                "description": f"Odoo Payment ({self.reference})",
                "userAgent": "Mozilla/5.0...",
                "language": "sv-SE",
                "urls": {
                    "hostUrls": [base_url],
                    "completeUrl": f'{complete_url}?{urls.url_encode(url_params)}',
                    "cancelUrl": f'{cancel_url}?{urls.url_encode(url_params)}',
                    "callbackUrl": urls.url_join(base_url, SwedbankpayController._webhook_url),
                    # "logoUrl": urls.url_join(base_url, f"web/image/res.company/{self.company_id.id}/logo") # 50px by 400px
                },
                "payeeInfo": {
                    "payeeId": self.provider_id.swedbankpay_merchant_id,
                    "payeeReference": self.reference.replace('-', ''),
                    "payeeName": self.partner_name,
                    "orderReference": self.reference
                }
            }
        })

        return payload

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        """ Override of payment to find the transaction based on swedbankpay data.

        :param str provider_code: The code of the provider that handled the transaction
        :param dict notification_data: The notification data sent by the provider
        :return: The transaction if found
        :rtype: recordset of `payment.transaction`
        :raise: ValidationError if the data match no transaction
        """
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != 'swedbankpay' or len(tx) == 1:
            return tx

        reference = notification_data.get('tx_ref') or notification_data.get('orderReference')
        if not reference:
            raise ValidationError("Swedbankpay: " + _("Received data with missing reference."))

        tx = self.search([('reference', '=', reference), ('provider_code', '=', 'swedbankpay')])
        if not tx:
            raise ValidationError(
                "Swedbankpay: " + _("No transaction found matching reference %s.", reference)
            )
        return tx

    def _swedbankpay_post_purchase_capture(self):
        _logger.info(
            "Sending '/psp/paymentorders/{id}/captures' request for transaction with reference %s",
            self.reference
        )
        payload = json.dumps({
            "transaction": {
                "description": f"Authorized payment capture for {self.reference}",
                "amount": int(self.amount * 100),
                "vatAmount": 0,
                "payeeReference": f"{self.reference.replace('-', '')}{self.reference.replace('-', '')}",
                "receiptReference": self.reference,
                "orderItems": [{
                    "name": line.product_id.name,
                    "type": 'PRODUCT' if line.product_id.detailed_type in ['product', 'consu'] else 'SERVICE',
                    "class": line.product_id.categ_id.name.replace(' ', ''),
                    "quantity": line.product_uom_qty,
                    "quantityUnit": "pcs",
                    "unitPrice": int(line.price_total * 100),
                    "vatPercent": 0,
                    "amount": int(line.price_total * 100),
                    "vatAmount": 0,
                    "reference": line.product_id.default_code.replace(' ', '') if line.product_id.default_code else line.product_id.name.replace(' ', '')

                } for line in self.sale_order_ids[0].order_line]
            }
        })
        capture_data = self.provider_id._swedbankpay_make_request(
            f'/psp/paymentorders/{self.provider_reference}/captures', payload=payload
        )
        print("capture_data", capture_data)
        return capture_data

    def _process_notification_data(self, notification_data):
        """ Override of payment to process the transaction based on Swedbankpay data.

        Note: self.ensure_one()

        :param dict notification_data: The notification data sent by the provider
        :return: None
        :raise: ValidationError if inconsistent data were received
        """
        super()._process_notification_data(notification_data)
        if self.provider_code != 'swedbankpay':
            return

        order_status_request = self.provider_id._swedbankpay_make_request(
            f'/psp/paymentorders/{self.provider_reference}', method='GET'
        )

        order_status = order_status_request.get('paymentOrder')

        print("_process_notification_data order_status", pprint.pformat(order_status))

        self.payment_method_id = self.env['payment.method'].search(
            [('code', '=', 'swedbankpay')], limit=1
        ) or self.payment_method_id

        # Update the payment state.
        payment_status = order_status['status'].lower()
        if payment_status in const.PAYMENT_STATUS_MAPPING['pending']:
            self._set_pending()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['done']:
            self._set_done()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['cancel']:
            self._set_canceled()
        elif payment_status in const.PAYMENT_STATUS_MAPPING['error']:
            self._set_error(_(
                "An error occurred during the processing of your payment (status %s). Please try "
                "again.", payment_status
            ))
        else:
            _logger.warning(
                "Received data with invalid payment status (%s) for transaction with reference %s.",
                payment_status, self.reference
            )
            self._set_error("Swedbankpay: " + _("Unknown payment status: %s", payment_status))
