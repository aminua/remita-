import datetime
import json
from odoo import http, api
from odoo.http import request


class BankPaymentNotification(http.Controller):
    @http.route('/payment/remita/bank', type="json", methods=["POST"], auth="public", csrf=False)
    def bank_payment_feedback(self, **kwargs):
        response_dict = {
            'txn_state': "01",
            "message": "Not OK"
        }
        if not kwargs:
            kwargs = request.jsonrequest
        RRR = kwargs.get('rrr')
        data = request.env['payment.transaction']._get_transaction_status(dict(RRR=RRR), acquirer='remita')
        request.env['payment.transaction'].sudo().form_feedback(data, 'remita')
        payment_tx = request.env['payment.transaction'].sudo().search([('reference', '=', kwargs.get('orderRef'))])
        sale_order = payment_tx.sale_order_id  # TODO: validate sales order if it is not auto-validated
        if sale_order.state == 'draft':
            sale_order.action_confirm()
        invoice = request.env['account.invoice'].sudo().search([('origin', '=', str(kwargs.get('orderRef')))])
        if not invoice.exists():  # if invoice doesnt exist create a new one
            invoice = self.create_invoice(payment_tx, sale_order)
        sale_order.invoice_status = 'invoiced'
        if data.get('status') == "success":  # if payment status is success create and post payment immediately
            # validate the invoice
            invoice.sudo().action_invoice_open()
            # create and post payment immediately
            payment = request.sudo().create_payment(payment_tx, invoice)
            payment and payment.post()
            # create tnx record or verify this is automatically created
            response_dict['txn_state'] = '00'
            response_dict['message'] = 'Ok'
        # TODO: reset the sales order on the website to clear the cart.
        return request.make_response(data=json.dumps(response_dict), headers={
            'content-type': 'application/json; charset=UTF-8'
        }, cookies=None)

    # @http.route('/payment/remita/bank', type="http", methods=["POST"], auth="public", csrf=False)
    # def bank_payment_feedback(self, **kwargs):
    #     response_dict = {
    #         'txn_state': "01",
    #         "message": "Not OK"
    #     }
    #     RRR = kwargs.get('rrr')
    #     data = request.env['payment.transaction']._get_transaction_status(dict(RRR=RRR), acquirer='remita')
    #     request.env['payment.transaction'].sudo().form_feedback(data, 'remita')
    #     payment_tx = request.env['payment.transaction'].sudo().search([('reference', '=', kwargs.get('orderRef'))])
    #     sale_order = payment_tx.sale_order_id  # TODO: validate sales order if it is not auto-validated
    #     if sale_order.state == 'draft':
    #         sale_order.action_confirm()
    #     invoice = request.env['account.invoice'].sudo().search([('origin', '=', str(kwargs.get('orderRef')))])
    #     if not invoice.exists():  # if invoice doesnt exist create a new one
    #         invoice = self.create_invoice(payment_tx, sale_order)
    #     sale_order.invoice_status = 'invoiced'
    #     if data.get('status') == "success":  # if payment status is success create and post payment immediately
    #         # validate the invoice
    #         invoice.sudo().action_invoice_open()
    #         # create and post payment immediately
    #         payment = request.sudo().create_payment(payment_tx, invoice)
    #         payment and payment.post()
    #         # create tnx record or verify this is automatically created
    #         response_dict['txn_state'] = '00'
    #         response_dict['message'] = 'Ok'
    #     # TODO: reset the sales order on the website to clear the cart.
    #     return request.make_response(data=json.dumps(response_dict), headers={
    #         'content-type': 'application/json; charset=UTF-8'
    #     }, cookies=None)

    @api.multi
    def create_invoice(self, payment_tx, sale_order):
        invoice_id = request.env['account.invoice'].sudo().create({
            'journal_id': 1,
            'partner_id': payment_tx.sale_order_id.partner_id.id,  # get from sales order
            'company_id': payment_tx.sale_order_id.partner_id.company_id and payment_tx.sale_order_id.partner_id.company_id.id or 1,
            # Get the company of user
            'account_id': 1,  # There should be a default account
            'reference_type': '',
            'currency_id': payment_tx.currency_id.id,
            'origin': payment_tx.sale_order_id.name,  # sales order name
            'team_id': payment_tx.sale_order_id.team_id.id,  # get the team id from sales order
            'invoice_line_ids': [(0, 0, {
                'product_id': line.product_id.id,
                'name': line.name,
                'account_id': 2,
                'price_unit': line.price_unit,
                'quantity': line.product_uom_qty,
            }) for line in sale_order.order_line]
        })
        return invoice_id

    @api.multi
    def create_payment(self, payment_tx, invoice_id):
        payment_values = {
            'payment_transaction_id': payment_tx.id,
            'payment_reference': payment_tx.reference,
            'amount': payment_tx.amount,
            'payment_type': "inbound",
            'partner_type': 'customer',
            'partner_id': payment_tx.partner_id.id,
            'payment_method_id': 1,
            'payment_date': datetime.datetime.now().strftime('%y%m%d_%H%M%S'),
            'journal_id': 1,
            'currency_id': payment_tx.currency_id.id,
            'communication': invoice_id.number
        }
        payment_id = request.env['account.payment'].sudo().create(payment_values)
        return payment_id
