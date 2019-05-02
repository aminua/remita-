# -*- encoding: utf-8 -*-
from odoo import api, models, fields


class ResCurrency(models.Model):

    _inherit = 'res.currency'

    subunit_ids = fields.One2many('res.currency.subunit', 'currency_id', string='Subunit')
    currency_word = fields.Char('Currency in word')


class ResCurrencySubunit(models.Model):
    """Manage subunits of major currencies and solve the problem of currency amount in words"""

    _name = 'res.currency.subunit'
    _rec_name = 'name'
    _auto = True
    _description = 'Currency Subunit'
    _table = 'res_currency_subunit'
    _order = 'name ASC'
    _sql_constrains = [
        ('unique_currency_id', 'UNIQUE(currency_id)', 'Related currency must be unique')
    ]

    name = fields.Char(string="Subunit name")
    symbol = fields.Char(string="Symbol")
    position = fields.Selection([
        ('before', 'Before Amount'),
        ('after', 'After Amount'),
    ], string="Currency position")
    decimal_places = fields.Integer(string='Decimal places')
    currency_id = fields.Many2one(comodel_name='res.currency', string="Parent currency")
