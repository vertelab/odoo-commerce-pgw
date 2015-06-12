import unittest
import hashlib
import base64
from payer_api import (
    PayerIPNotOnWhitelistException,
    PayerIPBlacklistedException,
    PayerURLValidationError,
    PayerPostAPIError,
)
from payer_api.postapi import PayerPostAPI
from payer_api.order import (
    PayerProcessingControl,
    PayerOrder,
    PayerBuyerDetails,
    PayerOrderItem,
)


class TestCase(unittest.TestCase):
    # Implement assertIsNotNone for Python runtimes < 2.7 or < 3.1
    if not hasattr(unittest.TestCase, 'assertIsNotNone'):
        def assertIsNotNone(self, value, *args):
            self.assertNotEqual(value, None, *args)


class TestPayerPostAPI(TestCase):

    def setUp(self):
        self.api = PayerPostAPI(
            agent_id="AGENT_ID",
            key_1="6866ef97a972ba3a2c6ff8bb2812981054770162",
            key_2="1388ac756f07b0dda2961436ba8596c7b7995e94",
        )

        self.api.set_processing_control(self.getProcessingControl())
        self.api.set_order(self.getOrder())

    def getOrder(self):
        return PayerOrder(
            order_id="123456",
            buyer_details=PayerBuyerDetails(
                first_name="John",
                last_name="Doe",
                address_line_1="1234 Main Street",
                postal_code="12345",
                city="Anywhere",
                phone_mobile="012345678",
                email="john.doe@host.com",
            ),
            order_items=[
                PayerOrderItem(
                    description='A product',
                    price_including_vat=123.50,
                    vat_percentage=25,
                    quantity=4,
                ),
                PayerOrderItem(
                    description='Another product',
                    price_including_vat=123.0,
                    vat_percentage=12.5,
                    quantity=2,
                ),
            ],
            info_lines=[
                "Shipping with 5 work days",
                "Additional line of order info",
            ]
        )

    def getProcessingControl(self):
        return PayerProcessingControl(
            success_redirect_url="http://localhost/webshop/thankyou/",
            authorize_notification_url="http://localhost/webshop/auth/",
            settle_notification_url="http://localhost/webshop/settle/",
            redirect_back_to_shop_url="http://localhost/webshop/",
        )

    def test_checksums(self):
        xml_data = self.api.get_xml_data()

        checksum = self.api.get_checksum(self.api.get_base64_data())
        expected_checksum = hashlib.md5(
            "6866ef97a972ba3a2c6ff8bb2812981054770162" +
            base64.b64encode(xml_data) +
            "1388ac756f07b0dda2961436ba8596c7b7995e94").hexdigest()

        self.assertEqual(checksum, expected_checksum)

    def test_callback_validation(self):
        xml = self.api.xml_document

        auth_url = xml.get_authorize_notification_url(
            order_id=self.api.order.order_id)
        settle_url = xml.get_settle_notification_url(
            order_id=self.api.order.order_id)

        ad = {
            'payer_callback_type': 'auth',
            'payer_testmode': 'false',
            'payer_payment_type': 'card',
            'payer_merchant_reference_id': self.api.order.order_id,
        }

        sd = ad
        sd.update({
            'payer_callback_type': 'settle',
            'payer_added_fee': 0,
            'payer_payment_id': 'yYkYOKFf_Z@hbJj3nS41Q2xE9dVm',
            'payread_payment_id': 'yYkYOKFf_Z@hbJj3nS41Q2xE9dVm',
        })

        # We avoid using urllib.erlencode() here as incoming URL's are known to
        # be erroneously encoded, e.g. enecoded @ characters in query string

        def add_query_params(url, params):
            qsl = ["%s=%s" % (k, v,) for k, v in params.iteritems()]
            return "&".join([url] + qsl)

        auth_url = add_query_params(auth_url, ad)
        settle_url = add_query_params(settle_url, sd)

        def get_md5_sum(url):
            return hashlib.md5(
                "6866ef97a972ba3a2c6ff8bb2812981054770162" +
                url +
                "1388ac756f07b0dda2961436ba8596c7b7995e94").hexdigest()

        auth_url_test = "%s&md5sum=%s" % (
            auth_url, get_md5_sum(auth_url))
        auth_url_api = "%s&md5sum=%s" % (
            auth_url, self.api.get_checksum(auth_url))
        settle_url_test = "%s&md5sum=%s" % (
            settle_url, get_md5_sum(settle_url))
        settle_url_api = "%s&md5sum=%s" % (
            settle_url, self.api.get_checksum(settle_url))

        self.assertTrue(self.api.validate_callback_url(auth_url_test))
        self.assertTrue(self.api.validate_callback_url(auth_url_api))

        self.assertTrue(self.api.validate_callback_url(settle_url_test))
        self.assertTrue(self.api.validate_callback_url(settle_url_api))

        self.assertEqual(auth_url_test, auth_url_api)
        self.assertEqual(settle_url_test, settle_url_api)

        self.assertRaises(PayerURLValidationError,
                          self.api.validate_callback_url,
                          (self.api, auth_url))
        self.assertRaises(PayerURLValidationError,
                          self.api.validate_callback_url,
                          (self.api, settle_url))
        self.assertRaises(PayerURLValidationError,
                          self.api.validate_callback_url,
                          (self.api, auth_url +
                           "&md5sum=79acb36d5a10837c377e6f3f1cf9fc9c"))
        self.assertRaises(PayerURLValidationError,
                          self.api.validate_callback_url,
                          (self.api, settle_url +
                           "&md5sum=79acb36d5a10837c377e6f3f1cf9fc9c"))

        # IP white/blacklists
        for ip in self.api.ip_whitelist:
            self.assertTrue(self.api.validate_callback_ip(ip))

        new_ip = "123.123.123.123"

        self.assertRaises(PayerIPNotOnWhitelistException,
                          self.api.validate_callback_ip,
                          new_ip)

        self.api.add_whitelist_ip(new_ip)
        self.assertTrue(self.api.validate_callback_ip(new_ip))

        self.api.add_blacklist_ip(new_ip)
        self.api.add_blacklist_ip("234.234.234.234")

        for ip in self.api.ip_blacklist:
            self.assertRaises(PayerIPBlacklistedException,
                              self.api.validate_callback_ip,
                              ip)

    def test_config_errors(self):
        api = PayerPostAPI(agent_id=None, key_1=None, key_2=None)

        # Checksums (keys 1 & 2)
        self.assertRaises(PayerPostAPIError,
                          api.get_checksum, "data")

        api.key_1 = "key1"
        self.assertRaises(PayerPostAPIError,
                          api.get_checksum, "data")

        api.key_2 = "key2"

        raised = False
        try:
            api.get_checksum("data")
        except:
            raised = True

        self.assertFalse(raised, 'Exception raised')
        self.assertIsNotNone(api.get_checksum("data"))

        # Order, Processing control, agent ID
        self.assertRaises(PayerPostAPIError,
                          api.get_post_data)

        api.agent_id = "AGENT_ID"

        api.set_order(self.getOrder())
        api.set_processing_control(self.getProcessingControl())

        raised = False
        try:
            api.get_post_data()
        except:
            raised = True
        self.assertFalse(raised, 'Exception raised')

        api.agent_id = None
        self.assertRaises(PayerPostAPIError,
                          api._generate_xml)


if __name__ == '__main__':
    unittest.main()
