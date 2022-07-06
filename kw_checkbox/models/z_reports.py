
import logging

from odoo import models, fields, exceptions, _

from .checkbox import CheckBoxApi

_logger = logging.getLogger(__name__)


class ZReports(models.Model):
    _name = 'kw.checkbox.z.reports'
    _description = 'ZReports'

    name = fields.Char(string='Report ID', required=True)
    cash_register_id = fields.Many2one('kw.checkbox.cash.register')
    serial = fields.Integer()
    is_z_report = fields.Boolean()
    payments = fields.Many2many('kw.checkbox.z.reports.payments')
    taxes = fields.Many2many('kw.checkbox.tax')
    sell_receipts_count = fields.Integer()
    return_receipts_count = fields.Integer()
    transfers_count = fields.Integer()
    transfers_sum = fields.Float()
    balance = fields.Float()
    initial = fields.Float()
    created_at = fields.Datetime()
    updated_at = fields.Datetime()

    html_text = fields.Html(string='Html', compute='_compute_print_report')

    def _compute_print_report(self):
        self.ensure_one()
        cashier_token = self.env[
            'kw.checkbox.cashier'].get_cashier_token(
                self.cash_register_id.organization_id)
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        checkbox = CheckBoxApi(
            access_token=cashier_token,
            license_key=self.cash_register_id.license_key,
            test_mode=self.cash_register_id
            .company_id.kw_checkbox_mode != 'prod'
        )
        res = checkbox.get_print_report(report_id=self.name)
        self.html_text = '<pre class="tab">' + res.replace('\n',
                                                           '<br>') + "</pre>"


class ZReportsPayment(models.Model):
    _name = 'kw.checkbox.z.reports.payments'
    _description = 'Checkbox payment report'
    z_report_id = fields.Many2one(
        comodel_name='kw.checkbox.z.reports'
    )
    rec_id = fields.Char()
    code = fields.Char()
    type = fields.Char()
    label = fields.Char()
    sell_sum = fields.Integer()
    return_sum = fields.Integer()
    service_in = fields.Integer()
    service_out = fields.Integer()
