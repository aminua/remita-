# -*- coding: utf-8 -*-
from hashlib import sha512
import logging
import urlparse

from odoo import models, fields
from odoo.exceptions import ValidationError
from odoo.tools import float_round

_logger = logging.getLogger(__name__)


class AcquirerRemita(models.Model):
    _inherit = 'payment.acquirer'

    def _get_remita_urls(self, environment):
        """remita URLs"""
        if environment == 'prod':
            return {
                'remita_get_rrr': "/get_rrr/remita",
            }
        else:
            return {
               'remita_get_rrr': "/get_rrr/remita",
            }

    provider = fields.Selection(selection_add=[('remita', "Remita")])
    merchant_id = fields.Char('Merchant Id')
    service_type_id = fields.Char('service Type Id')
    api_key = fields.Char('API KEY')

    def _remita_generate_digital_sign(self, acquirer, inout, values):
        """ Generate the shasign for incoming or outgoing communications.

        :param browse acquirer: the payment.acquirer browse record. It should
                                have a shakey in shaky out
        :param string inout: 'in' (odoo contacting remita) or 'out' (remita
                             contacting odoo).
        :param dict values: transaction values

        :return string: shasign
        """
        assert inout in ('in', 'out')
        assert acquirer.provider == 'remita'

        if inout == 'in':
            keys = "merchant_id service_type_id order_id total_amount response_url api_key"
        else:
            keys = "product_id pay_item_id webpay_mac_key"

        def get_value(key):
            if values.get(key):
                return values[key]
            return ''

        if acquirer.provider == 'remita':
           items = sorted((k.upper(), v) for k, v in values.items())
           sign = ''.join(str(v) for k, v in items)
           shasign = sha512(sign).hexdigest()
        return shasign

    def remita_form_generate_values(self, values=None):
        if not values:
            values = {}
        base_url = self.env['ir.config_parameter'].get_param('web.base.url')
        acquirer = self
        if not isinstance(values, dict):
            values = dict(values)
        remita_values = {
            'txn_ref':  values['reference'],
            'merchant_id': acquirer.merchant_id,
            'service_type_id': acquirer.service_type_id,
            'total_amount': '%d' % int(float_round(values['amount'], 2)),
            'response_url': '%s' % urlparse.urljoin(base_url, '/get_rrr/remita'),
            'api_key': acquirer.api_key,
        }
        if values.get('return_url'):
            shasign = self._remita_generate_digital_sign(acquirer, 'in', remita_values)
            remita_values['SHASIGN'] = shasign
        values.update(remita_values)
        return values

    def remita_get_form_action_url(self):
        acquirer = self
        return self._get_remita_urls(acquirer.environment)['remita_get_rrr']
   

class TxRemita(models.Model):
    _inherit = 'payment.transaction'

    # Remita status
    _buckaroo_valid_tx_status = [00, 01]    
    _buckaroo_pending_tx_status = [021, 020, 025, 040]    
    _buckaroo_cancel_tx_status = [012, 61]    
    _buckaroo_error_tx_status = [022, 02, 022, 023 , 031, 032, 19, 20, 26, 27]    
    _buckaroo_reject_tx_status = [030, 999]

    remita_txnid = fields.Char('Remita Retrieval Reference')

    # --------------------------------------------------
    # FORM RELATED METHODS
    # --------------------------------------------------
    
    def _remita_form_get_tx_from_data(self, data):
        reference = data.get('orderID')
        if not reference:
            error_msg = 'Remita: received data with missing reference (%s)' % reference
            _logger.error(error_msg)
            raise ValidationError(error_msg)

        # find tx -> @TDENOTE use txn_id ?
        tx_ids = self.env['payment.transaction'].search([('reference', '=', reference)])
        if not tx_ids or len(tx_ids) > 1:
            error_msg = 'Remita: received data for reference %s' % reference
            if not tx_ids:
                error_msg += '; no order found'
            else:
                error_msg += '; multiple order found'
            _logger.error(error_msg)
            raise ValidationError(error_msg)
        return self.browse(tx_ids[0])

    def _remita_form_validate(self, tx, data):
        status = data.get('responseStatus')
        data = {
            'remita_txnid': data.get('RRR'),
        }
        if status in ['SUCCESS', 'Completed', 'Processed']:
            _logger.info('Validated Remita payment for tx %s: set as done' % tx.reference)
            data.update(state='done', date_validate=data.get('udpate_time', fields.datetime.now()),
                        state_message=data.get('statusMessage', ''))
            return tx.write(data)
        elif status in ['Pending', 'Expired']:
            _logger.info('Received notification for Remita payment %s: set as pending' % tx.reference)
            data.update(state='pending', state_message=data.get('statusMessage', ''))
            return tx.write(data)
        else:
            error = 'Received unrecognized status for Remita payment %s: %s, set as error' % (tx.reference, status)
            _logger.info(error)
            data.update(state='error', state_message=error)
            return tx.write(data)

    def open_requery(self):
        url = "/notification"
        return {
            'type': 'ir.actions.act_url',
            'url': url,
            'target': 'new'
        }
