# Part of Odoo. See LICENSE file for full copyright and licensing details.

# The currencies supported by Swedbankpay, in ISO 4217 format.
SUPPORTED_CURRENCIES = [
    'SEK',
    'EUR',
]

# Mapping of transaction states to Swedbankpay payment statuses.
PAYMENT_STATUS_MAPPING = {
    'pending': ['pending auth', 'ready'],
    'done': ['successful', 'paid'],
    'cancel': ['cancelled', 'aborted'],
    'error': ['failed'],
}

# The codes of the payment methods to activate when Swedbankpay is activated.
DEFAULT_PAYMENT_METHODS_CODES = [
    # Primary payment methods.
    'card',
    'swish',
    # Brand payment methods.
    'visa',
    'mastercard',
    'amex',
    'discover',
]
