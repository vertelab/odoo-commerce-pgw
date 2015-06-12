VERSION = '0.1.1'

DEBUG_MODE_BRIEF = "brief"
DEBUG_MODE_SILENT = "silent"
DEBUG_MODE_VERBOSE = "verbose"

PAYMENT_METHOD_CARD = "card"
PAYMENT_METHOD_BANK = "bank"
PAYMENT_METHOD_PHONE = "phone"
PAYMENT_METHOD_INVOICE = "invoice"

IP_WHITELIST = [
    "192.168.100.1",
    "192.168.100.20",
    "79.136.103.5",
    "94.140.57.180",
    "94.140.57.181",
    "94.140.57.184",
]

IP_BLACKLIST = []


class PayerIPNotOnWhitelistException(Exception):
    pass


class PayerIPBlacklistedException(Exception):
    pass


class PayerURLValidationError(Exception):
    pass


class PayerPostAPIError(Exception):

    ERROR_MISSING_AGENT_ID = 100
    ERROR_MISSING_KEY_1 = 101
    ERROR_MISSING_KEY_2 = 102
    ERROR_MISSING_ORDER = 200
    ERROR_MISSING_PROCESSING_CONTROL = 300
    ERROR_XML_ERROR = 400

    ERROR_MESSAGES = {
        ERROR_MISSING_AGENT_ID: "Agent ID not set.",
        ERROR_MISSING_KEY_1: "Key 1 not set.",
        ERROR_MISSING_KEY_2: "Key 2 not set.",
        ERROR_MISSING_ORDER: "Order not set.",
        ERROR_MISSING_PROCESSING_CONTROL: "Processing control not set.",
        ERROR_XML_ERROR: "There was an error while generating XML data.",
    }

    def __init__(self, code):
            self.code = code

    def __str__(self):
        return repr("Error %s: %s" % (
            self.code,
            self.ERROR_MESSAGES.get(self.code, "Unknown Error")))
