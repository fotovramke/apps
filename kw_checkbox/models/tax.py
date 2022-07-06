import logging

from odoo import models, fields

_logger = logging.getLogger(__name__)


class CheckboxTax(models.Model):
    _name = 'kw.checkbox.tax'
    _description = 'Checkbox Tax'

    name = fields.Char(compute='_compute_name')
    index = fields.Char(
        readonly=True, )
    code = fields.Char(
        readonly=True, )
    label = fields.Char(
        readonly=True, )
    symbol = fields.Char(
        readonly=True, )
    rate = fields.Integer(
        readonly=True, )
    extra_rate = fields.Integer(
        readonly=True, )
    included = fields.Boolean(
        readonly=True, )
    active = fields.Boolean(
        default=True, readonly=True, )
    datetime_created_at = fields.Datetime(
        string='Create at', readonly=True, )
    datetime_updated_at = fields.Datetime(
        string='Update at', readonly=True, )
    cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register', readonly=True, )

    def _compute_name(self):
        for obj in self:
            obj.name = f"{obj.label} ({obj.code})"
