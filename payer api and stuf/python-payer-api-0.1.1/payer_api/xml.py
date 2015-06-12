# -*- coding: utf-8 -*-
from . import (
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_BANK,
    PAYMENT_METHOD_PHONE,
    PAYMENT_METHOD_INVOICE,
    DEBUG_MODE_SILENT,
)
from lxml import etree as ET
import urllib
import urlparse
import StringIO


class PayerXMLDocument(object):

    ROOT_ELEMENT_NAME = "payread_post_api_0_2"
    ORDER_ID_URL_PARAMETER_NAME = 'order_id'

    def __init__(self, *args, **kwargs):

        self.root = None

        self.agent_id = kwargs.get('agent_id', None)

        self.debug_mode = kwargs.get('debug_mode', DEBUG_MODE_SILENT)
        self.test_mode = bool(kwargs.get('test_mode', False))

        self.message = kwargs.get('message', None)
        self.hide_details = kwargs.get('hide_details', False)

        self.language = kwargs.get('language', 'sv')
        self.currency = kwargs.get('currency', 'SEK')

        self.payment_methods = kwargs.get('payment_methods', [
            PAYMENT_METHOD_CARD,
            PAYMENT_METHOD_BANK,
            PAYMENT_METHOD_PHONE,
            PAYMENT_METHOD_INVOICE,
        ])

        self.order = kwargs.get('order', None)

        processing_control = kwargs.get('processing_control', kwargs)
        self.success_redirect_url = \
            processing_control.get('success_redirect_url', None)
        self.authorize_notification_url = \
            processing_control.get('authorize_notification_url', None)
        self.settle_notification_url = \
            processing_control.get('settle_notification_url', None)
        self.redirect_back_to_shop_url = \
            processing_control.get('redirect_back_to_shop_url', None)

        super(PayerXMLDocument, self).__init__()

    def _build_xml_tree(self):

        self.root = ET.Element(self.ROOT_ELEMENT_NAME, nsmap={
            'xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        }, attrib={
            "{http://www.w3.org/2001/XMLSchema-instance}"
            "noNamespaceSchemaLocation": 'payread_post_api_0_2.xsd',
        })

        # seller_details element
        seller_details = ET.SubElement(self.root, 'seller_details')
        ET.SubElement(seller_details, 'agent_id').text = self.agent_id

        buyer_details = ET.SubElement(self.root, 'buyer_details')
        for key, value in self.order.buyer_details.as_dict().iteritems():
            if value:
                ET.SubElement(buyer_details, key).text = \
                    unicode(value) if value else ''

        # purchase element
        purchase = ET.SubElement(self.root, 'purchase')
        ET.SubElement(purchase, 'currency').text = unicode(self.currency)
        ET.SubElement(purchase, 'description').text = \
            unicode(self.order.description)
        ET.SubElement(purchase, 'reference_id').text = \
            unicode(self.order.order_id)
        if self.message:
            ET.SubElement(purchase, 'message').text = unicode(self.message)
        ET.SubElement(purchase, 'hide_details').text = \
            "true" if self.hide_details else "false"

        purchase_list = ET.SubElement(purchase, 'purchase_list')

        for idx, item in enumerate(self.order.order_items):
            freeform_purchase = ET.SubElement(
                purchase_list, 'freeform_purchase')

            data = item.as_dict()

            ET.SubElement(freeform_purchase, 'line_number').text = \
                unicode(idx + 1)
            ET.SubElement(freeform_purchase, 'description').text = \
                unicode(data.get('description', 'Product'))
            ET.SubElement(freeform_purchase, 'price_including_vat').text = \
                unicode("%.2f" % float(data.get('price_including_vat', 0)))
            ET.SubElement(freeform_purchase, 'vat_percentage').text = \
                unicode("%.2f" % float(data.get('vat_percentage', 25)))
            ET.SubElement(freeform_purchase, 'quantity').text = \
                unicode(data.get('quantity', 1))

        for idx, value in enumerate(self.order.info_lines):
            info_line = ET.SubElement(purchase_list, 'info_line')

            ET.SubElement(info_line, 'line_number').text = unicode(3000 + idx)
            ET.SubElement(info_line, 'text').text = unicode(value[0:255])

        # processing_control element
        processing_control = ET.SubElement(self.root, 'processing_control')
        ET.SubElement(processing_control, 'success_redirect_url').text = \
            self.get_success_redirect_url()
        ET.SubElement(processing_control, 'authorize_notification_url').text = \
            self.get_authorize_notification_url(self.order.order_id)
        ET.SubElement(processing_control, 'settle_notification_url').text = \
            self.get_settle_notification_url(self.order.order_id)
        ET.SubElement(processing_control, 'redirect_back_to_shop_url').text = \
            self.get_redirect_back_to_shop_url()

        # database_overrides element
        database_overrides = ET.SubElement(self.root, 'database_overrides')
        ET.SubElement(database_overrides, 'debug_mode').text = self.debug_mode
        ET.SubElement(database_overrides, 'test_mode').text = \
            "true" if self.test_mode else "false"
        ET.SubElement(database_overrides, 'language').text = \
            self.language.lower()

        if len(self.payment_methods):
            payment_methods = ET.SubElement(
                database_overrides, 'accepted_payment_methods')
            for payment_method in self.payment_methods:
                ET.SubElement(payment_methods, 'payment_method').text = \
                    payment_method

    def tostring(self, encoding="utf-8", pretty_print=False,
                 rebuild_tree=False):
        if self.root is None or rebuild_tree:
            self._build_xml_tree()

        tree = ET.ElementTree(self.root)
        output = StringIO.StringIO()
        tree.write(output, pretty_print=pretty_print, xml_declaration=True,
                   encoding=encoding, method="xml")

        retval = output.getvalue()
        output.close()

        return retval

    def __str__(self):
        return self.tostring()

    @classmethod
    def _add_params_to_url(cls, url, params={}):
        url_parts = list(urlparse.urlparse(url))
        query = dict(urlparse.parse_qsl(url_parts[4]))
        query.update(params)

        url_parts[4] = urllib.urlencode(query)

        return urlparse.urlunparse(url_parts)

    def get_success_redirect_url(self):
        return self.success_redirect_url

    def get_authorize_notification_url(self, order_id=None):
        return self._add_params_to_url(self.authorize_notification_url,
                                       params={
                                           self.ORDER_ID_URL_PARAMETER_NAME:
                                           order_id or ''
                                       })

    def get_settle_notification_url(self, order_id=None):
        return self._add_params_to_url(self.settle_notification_url,
                                       params={
                                           self.ORDER_ID_URL_PARAMETER_NAME:
                                           order_id or ''
                                       })

    def get_redirect_back_to_shop_url(self):
        return self.redirect_back_to_shop_url
