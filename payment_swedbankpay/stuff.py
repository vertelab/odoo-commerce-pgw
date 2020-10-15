
        ## Typical response
        # json = resp.json()
        # response_json = {'payment': 
        #     {'id': '/psp/creditcard/payments/800a96e4-0b7a-4593-6bb5-08d865e39b33',
        #     'number': 40104751724,
        #     'created': '2020-10-01T14:30:34.0133511Z',
        #     'updated': '2020-10-01T14:30:34.2816008Z',
        #     'instrument': 'CreditCard',
        #     'operation': 'Purchase',
        #     'intent': 'Authorization',
        #     'state': 'Ready',
        #     'currency': 'USD',
        #     'prices': {'id': '/psp/creditcard/payments/800a96e4-0b7a-4593-6bb5-08d865e39b33/prices'},
        #     'amount': 0,
        #     'description': 'Test Purchase',
        #     'initiatingSystemUserAgent': 'python-requests/2.20.0',
        #     'userAgent': 'USERAGENT=Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:81.0) Gecko/20100101 Firefox/81.0',
        #     'language': 'sv-SE', 'urls': {'id': '/psp/creditcard/payments/800a96e4-0b7a-4593-6bb5-08d865e39b33/urls'
        #     }, 
        #     'payeeInfo': {'id': '/psp/creditcard/payments/800a96e4-0b7a-4593-6bb5-08d865e39b33/payeeinfo'}, 
        #     'metadata': {'id': '/psp/creditcard/payments/800a96e4-0b7a-4593-6bb5-08d865e39b33/metadata'}}, 
        #     'operations': [
        #         {
        #             'method': 'PATCH',
        #             'href': 'https://api.externalintegration.payex.com/psp/creditcard/payments/800a96e4-0b7a-4593-6bb5-08d865e39b33',
        #             'rel': 'update-payment-abort', 'contentType': 'application/json'},
        #         {
        #             'method': 'GET',
        #             'href': 'https://ecom.externalintegration.payex.com/creditcardv2/payments/authorize/495252a6fa7d8d8e44f46e8d15e27240beea92c5996cec599ea06b5ed06c4ca0',
        #             'rel':'redirect-authorization',
        #             'contentType': 'text/html'
        #         }
        #         ]
        #     } 


        # Use the whole opereation dict for making a new request object for getting the reference.... 
        # (this is if we are going to need the reference in the controller...) 
      
        # SOURCE: https://developer.swedbankpay.com/home/technical-information#operations 
        # The operations should be performed as described in each response and not as described here in the documentation.
        # Always use the href and method as specified in the response by finding the appropriate 
        # operation based on its rel value.



        # Use payeeInfo and get the ??? 
        


 session <OpenERPSession {'db': 'amber', 'uid': 2, 'login': 'admin', 'session_token': 'e0adb8fc43722e9429d7701737f26dd31f8a3f10116ece8a1dcbeee8a4467038', 
 'context': {'lang': 'sv_SE', 'tz': 'Europe/Brussels', 'uid': 2},
  'geoip': {}, 'sale_order_id': 37, 'sale_last_order_id': 37, 'website_sale_current_pl': 1, '__payment_tx_ids__': [2, 3, 4, 37, 12, 13, 14, 22, 23, 24], '__website_sale_last_tx_id': 37}> 





    @http.route('/payment/swedbankpay/cancel', type='http', auth='none', csrf=False)
    def swedbankpay_cancel(self, **post):

        _logger.warning("~ cancel request %s" % request.httprequest)
        
        _logger.warning("~ cancel request args %s" % request.httprequest.args)
        # _logger.warning("~ cancel request form %s" % request.httprequest.form)
        # _logger.warning("~ cancel request values %s" % request.httprequest.values)
        
        # _logger.warning("~ cancel request args to_dict flat=True %s" % request.httprequest.values.to_dict(flat=True))
        # _logger.warning("~ cancel request args to_dict flat=False %s" % request.httprequest.values.to_dict(flat=False))
        
        
        # _logger.warning("~ cancel request json %s" % request.httprequest.json) # does not work 
        # _logger.warning("~ cancel request data %s" % request.httprequest.data) # empty
        # _logger.warning("~ cancel %s" % post) # empty 