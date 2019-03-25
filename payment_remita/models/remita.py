# -*- coding: utf-8 -*-
from hashlib import sha512
import logging
import urlparse

from odoo.addons.payment.models.payment_acquirer import ValidationError
from odoo.addons.payment_remita.controllers.main import RemitaController
from odoo import models, fields
from odoo.tools import float_round


_logger = logging.getLogger(__name__)


class AcquirerRemita(models.Model):
    _inherit = 'payment.acquirer'

    def _get_remita_urls(self, environment):
        """remita URLs"""
        if environment == 'prod':
            return {
                'remita_form_url': 'http://www.remitademo.net/remita/ecomm/init.reg',
                'remita_rest_url': 'https://login.remita.net/remita/ecomm',
            }
        else:
            return {
               'remita_form_url': 'http://www.remitademo.net/remita/ecomm/init.reg',
               'remita_rest_url': 'http://www.remitademo.net/remita/ecomm',
            }

    def _get_providers(self):
        providers = super(AcquirerRemita, self)._get_providers()
        providers.append(['remita', 'Remita'])
        return providers

    merchantId = fields.Char('Merchant Id', required_if_provider='remita'),
    serviceTypeId = fields.Char('service Type Id', required_if_provider='remita'),
    apikey = fields.Char('API KEY', required_if_provider='remita'),

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
            keys = "aaaaaamerchantId aaaaaserviceTypeId aaaaorderId aaamountt aaresponseurl api_key"
        else:
            keys = "aaaproduct_id aapay_item_id webpay_mac_key"

        def get_value(key):
            if values.get(key):
                return values[key]
            return ''

        if acquirer.provider == 'remita':
           items = sorted((k.upper(), v) for k, v in values.items())
           sign = ''.join(str(v) for k, v in items)
           shasign = sha512(sign).hexdigest()
        return shasign

    def remita_form_generate_values(self, partner_values, tx_values):
        base_url = self.pool['ir.config_parameter'].get_param('web.base.url')
        acquirer = self
        remita_tx_values = dict(tx_values)
        temp_remita_tx_values = {
            'aaaatxn_ref':  tx_values['reference'],
            'aaaaaamerchantId': acquirer.merchantId,
            'aaaaaserviceTypeId': acquirer.serviceTypeId,
            'aaamountt': '%d' % int(float_round(tx_values['amount'], 2)),
            'aaresponseurl': '%s' % urlparse.urljoin(base_url, RemitaController._cp_path),
            'api_key': acquirer.apikey,
        }
        if remita_tx_values.get('return_url'):
           shasign = self._remita_generate_digital_sign(acquirer, 'in', temp_remita_tx_values)
        temp_remita_tx_values['SHASIGN'] = shasign
        remita_tx_values.update(temp_remita_tx_values)
        return partner_values, remita_tx_values

    def remita_get_form_action_url(self, cr, uid, id, context=None):
        acquirer = self
        return self._get_remita_urls(acquirer.environment)['remita_form_url']
   

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
