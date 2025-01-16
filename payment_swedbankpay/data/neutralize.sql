-- disable swedbankpay payment provider
UPDATE payment_provider
   SET swedbankpay_merchant_id = NULL,
       swedbankpay_key = NULL,
       swedbankpay_account_nr = NULL;
