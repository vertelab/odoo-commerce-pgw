

class PayerProcessingControl(object):

    def __init__(self, success_redirect_url, authorize_notification_url,
                 settle_notification_url, redirect_back_to_shop_url,
                 *args, **kwargs):
        self.success_redirect_url = success_redirect_url
        self.authorize_notification_url = authorize_notification_url
        self.settle_notification_url = settle_notification_url
        self.redirect_back_to_shop_url = redirect_back_to_shop_url

    def get(self, key, default_value=None):
        return getattr(self, key, default_value)


class DictObject(object):

    def as_dict(self):
        return self.__dict__


class PayerBuyerDetails(DictObject):

    def __init__(self, *args, **kwargs):
        self.first_name = kwargs.get('first_name', None)
        self.last_name = kwargs.get('last_name', None)
        self.address_line_1 = kwargs.get('address_line_1', None)
        self.address_line_2 = kwargs.get('address_line_2', None)
        self.postal_code = kwargs.get('postal_code', None)
        self.city = kwargs.get('city', None)
        self.country_code = kwargs.get('country_code', None)
        self.phone_home = kwargs.get('phone_home', None)
        self.phone_work = kwargs.get('phone_work', None)
        self.phone_mobile = kwargs.get('phone_mobile', None)
        self.email = kwargs.get('email', None)
        self.organisation = kwargs.get('organisation', None)
        self.orgnr = kwargs.get('orgnr', None)
        self.customer_id = kwargs.get('customer_id', None)


class PayerOrderItem(DictObject):

    def __init__(self, description, price_including_vat, vat_percentage,
                 *args, **kwargs):

        self.description = unicode(description)
        self.price_including_vat = float(price_including_vat)
        self.vat_percentage = float(vat_percentage)
        self.quantity = int(kwargs.get('quantity', 1))


class PayerOrder(object):

    def __init__(self, order_id, *args, **kwargs):

        self.order_id = unicode(order_id)
        self.buyer_details = kwargs.get('buyer_details', PayerBuyerDetails())
        self.description = kwargs.get('description',
                                      'Order #%s' % self.order_id or '')
        self.order_items = kwargs.get('order_items', [])
        self.info_lines = kwargs.get('info_lines', [])

    def add_order_item(self, order_item):
        self.order_items.append(order_item)

    def add_info_line(self, info_line):
        self.info_lines.append(unicode(info_line))

    def set_buyer_details(self, buyer_details):
        self.buyer_details = buyer_details
