import json
from odoo import http
from odoo.http import HttpRequest, request


class BankPaymentNotification(http.Controller):
    @http.route('/payment/remita/bank', type="http", methods=["POST"], auth="public", csrf=False)
    def bank_payment_feedback(self, **kwargs):

        response_dict = {
            'txn_state': "01",
            "message": "Not OK"
        }
        RRR = kwargs.get('rrr')
        data = request.env['payment.transaction']._get_transaction_status(dict(RRR=RRR), acquirer='remita')

        request.env['payment.transaction'].sudo().form_feedback(data, 'remita')
        if data.get('status') == "success":
            # create tnx record or verify this is automatically created
            response_dict['txn_state'] = '00'
            response_dict['message'] = 'Ok'
        return request.make_response(data=json.dumps(response_dict), headers={
            'content-type': 'application/json; charset=UTF-8'
        }, cookies=None)
