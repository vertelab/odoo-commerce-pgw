# -*- coding: utf-8 -*-
from . import (
    VERSION, DEBUG_MODE_SILENT, IP_WHITELIST, IP_BLACKLIST,
    PayerIPNotOnWhitelistException,
    PayerIPBlacklistedException,
    PayerURLValidationError,
    PayerPostAPIError,
)
import base64
import hashlib
from xml import PayerXMLDocument
import urlparse


class PayerPostAPI(object):

    PAYER_POST_URL = "https://secure.payer.se/PostAPI_V1/InitPayFlow"
    API_VERSION = "Python_Payer_API_%s" % VERSION

    def __init__(self, agent_id, key_1, key_2, *args, **kwargs):

        self.agent_id = agent_id
        self.key_1 = key_1
        self.key_2 = key_2

        self.encoding = kwargs.get('encoding', "utf-8")
        self.currency = kwargs.get('currency', "SEK")

        self.debug_mode = kwargs.get('debug_mode', DEBUG_MODE_SILENT)
        self.test_mode = kwargs.get('test_mode', False)
        self.payment_methods = kwargs.get('payment_methods', None)

        self.xml_document = None

        self.set_order(kwargs.get('order', None))
        self.set_processing_control(kwargs.get('processing_control', None))

        self.ip_whitelist = kwargs.get('ip_whitelist', IP_WHITELIST)
        self.ip_blacklist = kwargs.get('ip_blacklist', IP_BLACKLIST)
        self.suppress_validation_checks = False

    def add_whitelist_ip(self, ip):
        self.ip_whitelist.append(ip)

    def add_blacklist_ip(self, ip):
        self.ip_blacklist.append(ip)

    def set_order(self, order):
        self.order = order

        self._generate_xml()

    def set_processing_control(self, processing_control):
        self.processing_control = processing_control

        self._generate_xml()

    def get_post_url(self):
        return self.PAYER_POST_URL

    def get_agent_id(self):
        if not self.agent_id:
            raise PayerPostAPIError(
                PayerPostAPIError.ERROR_MISSING_AGENT_ID)

        return self.agent_id

    def get_api_version(self):
        return self.API_VERSION

    def get_encoding(self):
        return self.encoding

    def get_checksum(self, data):
        if not self.key_1:
            raise PayerPostAPIError(PayerPostAPIError.ERROR_MISSING_KEY_1)

        if not self.key_2:
            raise PayerPostAPIError(PayerPostAPIError.ERROR_MISSING_KEY_2)

        return hashlib.md5(self.key_1 + data + self.key_2).hexdigest()

    def _generate_xml(self):

        if self.order and self.processing_control:

            kwargs = {
                'agent_id': self.get_agent_id(),
                'order': self.order,
                'processing_control': self.processing_control,
                'payment_methods': self.payment_methods,
                'debug_mode': self.debug_mode,
                'test_mode': self.test_mode,
            }
            kwargs = dict((k, v) for k, v in kwargs.items() if v)
            self.xml_document = PayerXMLDocument(**kwargs)

    def get_xml_data(self, *args, **kwargs):

        if not self.xml_document:
            self._generate_xml()

        if not self.order:
            raise PayerPostAPIError(PayerPostAPIError.ERROR_MISSING_ORDER)

        if not self.processing_control:
            raise PayerPostAPIError(
                PayerPostAPIError.ERROR_MISSING_PROCESSING_CONTROL)

        if not self.xml_document:
            raise PayerPostAPIError(PayerPostAPIError.ERROR_XML_ERROR)

        return self.xml_document.tostring(*args, **kwargs)

    def get_base64_data(self, xml_data=None, *args, **kwargs):
        if not xml_data:
            xml_data = self.get_xml_data(*args, **kwargs)

        return base64.b64encode(xml_data)

    def get_post_data(self):
        base64_data = self.get_base64_data()

        return {
            'payer_agentid': self.get_agent_id(),
            'payer_xml_writer': self.get_api_version(),
            'payer_data': base64_data,
            'payer_checksum': self.get_checksum(base64_data),
            'payer_charset': self.get_encoding(),
        }

    def validate_callback_ip(self, remote_addr):

        if self.suppress_validation_checks:
            return True

        if remote_addr in self.ip_blacklist:
            raise PayerIPBlacklistedException(
                "IP address %s is blacklisted." % str(remote_addr))

        if remote_addr not in self.ip_whitelist:
            raise PayerIPNotOnWhitelistException(
                "IP address %s is not on the whitelist." % str(remote_addr))

        return True

    def validate_callback_url(self, url):

        if self.suppress_validation_checks:
            return True

        try:
            url_parts = urlparse.urlparse(url)
            query = dict(urlparse.parse_qsl(url_parts.query,
                         keep_blank_values=True))
            supplied_checksum = query.pop('md5sum').lower()

            # The fancypants way of building the URL back up with
            # urlunparse/urlencode does not work as the incoming URL is not
            # urlencoded (i.e. contains raw @ in parameter values). Instead,
            # we might as well just split the URL at &md5sum which is
            # garuanteed to appear last in the parameters list.

            stripped_url = url[0:url.rfind('&')]

        except:
            raise PayerURLValidationError(
                'Could not extract MD5 checksum from URL %s.' % str(url))

        expected_checksum = self.get_checksum(stripped_url).lower()

        if supplied_checksum != expected_checksum:
            raise PayerURLValidationError(
                'MD5 checksums did not match. Expected %s, but got %s.' % (
                    expected_checksum, supplied_checksum,))

        return True
