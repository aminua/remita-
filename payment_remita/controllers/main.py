try:
    import simplejson as json
except ImportError:
    import json
import logging
import hashlib
import requests
from odoo.http import request

import odoo.http as http


_logger = logging.getLogger(__name__)


class RemitaPayment(http.Controller):

    @http.route('/get_rrr/remita', type="http", auth='public')
    def pay_rrr(self, **post):
        if request.httprequest.method == 'POST':
            if post:
                payload = {
                    "serviceTypeId": post.get('serviceTypeId'),
                    "amount": post.get("totalAmount"),
                    "orderId": post.get("orderId"),
                    "payerName": "Olalekan Babawale",
                    "payerEmail": "babawaleolalekan@gmail.com",
                    "payerPhone": "2347032650989",
                    "description": "Payment for Donation"
                }

                url = ' https://remitademo.net/remita/exapp/api/v1/send/api/echannelsvc/merchant/api/paymentinit'
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': "remitaConsumerKey=" + post.get('merchantId') + ",remitaConsumerToken=" + post.get('apiHash')
                }
                response = requests.post(url, payload=json.dumps(payload), headers=headers)
                if response.json().get('statuscode') and response.json().get('statuscode') == '025':
                    pass # update the values to send to the template
                request.render('') # render the form for rrr payment


    @http.route(['/payment/remita/return/'], type='http', auth="none", methods=['GET', 'POST'])
    def get_rrr(self, **post):
        url = 'http://www.remitademo.net/remita/ecomm'
        merchantId = '2547916'
        rrr = post.get('RRR')
        api_key = '1946'
        hash_object = hashlib.sha512(rrr + api_key + merchantId)
        hex_dig = hash_object.hexdigest()
        user_agent = "json/status.reg"
        full_url = url + '/' + merchantId + '/' + rrr + '/' + hex_dig + '/' + user_agent
        response = requests.get(full_url)
        result = response.json()
        code = result['status']
        description = result['message']
        paymentreference = result['RRR']
        orderId = result['orderId']
        if code == '01' or code == '00':
            _logger.info('remita: validated data')
            return request.render("payment_remita.payment_status_temp", dict(description=description,
                                                                             paymentreference=paymentreference,
                                                                             orderId=orderId))
        else:
            _logger.warning('Remita received %s' % description)
            return request.render("payment_remita.payment_status_temp", dict(description=description,
                                                                             paymentreference=paymentreference))
