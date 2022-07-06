import logging

from odoo import models, fields, exceptions, api, _

from .checkbox import CheckBoxApi

_logger = logging.getLogger(__name__)


# status: CREATED OPENING OPENED CLOSING CLOSED

class CheckboxShift(models.Model):
    _name = 'kw.checkbox.shift'
    _inherit = ['kw.checkbox.mixin']
    _description = 'Checkbox shifts'
    _order = 'closed_at_datetime desc, opened_at_datetime desc'
    _sql_constraints = [
        ('cb_id_uniq', 'unique (cb_id)', _('CheckBox ID must be unique'))]

    name = fields.Char(
        string='Serial', readonly=True, )
    active = fields.Boolean(
        default=True, )
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', change_default=True,
        default=lambda self: self.env.user.company_id.id, )
    cb_id = fields.Char(
        string='CheckBox ID', )
    status = fields.Char(
        readonly=True, )
    cashier_cb_id = fields.Char(
        string='Cashier CheckBox ID', readonly=True, )
    cashier_id = fields.Many2one(
        comodel_name='kw.checkbox.cashier', )
    cash_register_cb_id = fields.Char(
        string='Cash register CheckBox ID', readonly=True, )
    cash_register_id = fields.Many2one(
        comodel_name='kw.checkbox.cash.register', )
    opened_at_datetime = fields.Datetime(
        string='Opened at', )
    closed_at_datetime = fields.Datetime(
        string='Closed at', )

    def create_report_z(self, values, cash_reg):
        taxes_list = [tax['code'] for tax in values['taxes']]
        get_taxes = self.env['kw.checkbox.tax'].sudo().search(
            [('code', 'in', taxes_list)]
        )
        report = self.env['kw.checkbox.z.reports'].sudo().create({
            'name': values['id'],
            'cash_register_id': cash_reg.id,
            'serial': values['serial'],
            'is_z_report': values['is_z_report'],
            'taxes': get_taxes,
            'sell_receipts_count': values['sell_receipts_count'],
            'return_receipts_count': values['return_receipts_count'],
            'transfers_count': values['transfers_count'],
            'transfers_sum': values['transfers_sum'] * 0.01,
            'balance': values['balance'] * 0.01,
            'initial': values['initial'] * 0.01,
            'created_at': values['created_at'],
            'updated_at': values['updated_at'],
        })
        get_payment_list = []
        for payment in values['payments']:
            get_payment_list.append(
                self.env['kw.checkbox.z.reports.payments'].create({
                    'rec_id': payment['id'],
                    'code': payment['code'],
                    'type': payment['type'],
                    'label': payment['label'],
                    'sell_sum': payment['sell_sum'] * 0.01,
                    'return_sum': payment['return_sum'] * 0.01,
                    'service_in': payment['service_in'],
                    'service_out': payment['service_out'],
                }).id
            )
        report.write({
            'payments': get_payment_list
        })

    def close_opened(self):
        self.ensure_one()
        checkbox = self.cashier_id.get_checkbox()
        checkbox.license_key = self.cash_register_id.license_key
        response = checkbox.shift_close()
        self.create_report_z(response['z_report'], self.cash_register_id)
        self.update_info_by_token(self.cashier_id.access_token)

    @api.constrains('status', 'cashier_id', 'cash_register_id')
    def constrains_opened(self):
        for obj in self:
            if obj.status not in ['CREATED', 'OPENING', 'OPENED', ]:
                continue
            res = self.search([
                ('id', '!=', obj.id), ('cashier_id', '=', obj.cashier_id.id),
                ('cash_register_id', '=', obj.cash_register_id.id),
                ('status', 'in', ['CREATED', 'OPENING', 'OPENED', ]), ])
            if res:
                raise exceptions.ValidationError(
                    _('You should opened shift before open new one.'))

    @api.model
    def create(self, vals_list):
        if not vals_list.get('cb_id'):
            cashier_id = self.env['kw.checkbox.cashier'].browse(
                vals_list.get('cashier_id'))
            cash_register_id = self.env['kw.checkbox.cash.register'].browse(
                vals_list.get('cash_register_id'))
            if cashier_id and cash_register_id:
                checkbox = cashier_id.get_checkbox()
                checkbox.license_key = cash_register_id.license_key
                res = checkbox.shift_open()
                if 'message' in res:
                    raise exceptions.ValidationError(res.get('message'))
                if res:
                    vals_list.update({
                        'name': res['serial'], 'cb_id': res['id'],
                        'status': res['status'], })
        return super(CheckboxShift, self).create(vals_list)

    def update_info_by_token(self, token, ):
        self.ensure_one()

        checkbox = CheckBoxApi(
            test_mode=self.company_id.kw_checkbox_mode != 'prod',
            access_token=token, )
        res = checkbox.shift_info(self.cb_id)
        data = {
            'opened_at_datetime': res['opened_at'], 'status': res['status'],
            'closed_at_datetime': res['closed_at'], 'name': res['serial'], }
        if res.get('cashier'):
            data['cashier_cb_id'] = res['cashier']['id']
            cashier = self.env['kw.checkbox.cashier'].search([
                ('cb_id', '=', res['cashier']['id'])], limit=1)
            if cashier:
                data['cashier_id'] = cashier.id
        if res.get('cash_register'):
            data['cash_register_cb_id'] = res['cash_register']['id']
            cash_register = self.env['kw.checkbox.cash.register'].search([
                ('cb_id', '=', res['cash_register']['id'])], limit=1)
            if cash_register:
                data['cash_register_id'] = cash_register.id
        self.write(data)

    def update_info(self):
        self.ensure_one()
        cashier_token = None
        if self.cashier_id:
            cashier_token = self.cashier_id.get_checkbox().access_token
        elif self.cash_register_id:
            cashier_token = self.env[
                'kw.checkbox.cashier'].get_cashier_token(
                    self.cash_register_id.organization_id)
        if not cashier_token:
            raise exceptions.ValidationError(
                _('There is no acceptable username'))
        self.update_info_by_token(cashier_token)

    @api.model
    def get_or_create(self, res):
        data = {'closed_at_datetime': res['closed_at'], 'name': res['serial'],
                'opened_at_datetime': res['opened_at'], 'cb_id': res['id'],
                'status': res['status'], }
        if res.get('cashier'):
            data['cashier_cb_id'] = res['cashier']['id']
            cashier = self.env['kw.checkbox.cashier'].search([
                ('cb_id', '=', res['cashier']['id'])], limit=1)
            if cashier:
                data['cashier_id'] = cashier.id
        if res.get('cash_register'):
            data['cash_register_cb_id'] = res['cash_register']['id']
            cash_register = self.env['kw.checkbox.cash.register'].search([
                ('cb_id', '=', res['cash_register']['id'])], limit=1)
            if cash_register:
                data['cash_register_id'] = cash_register.id

        obj = self.get_by_cb_id(res['id'])
        if obj:
            obj.write(data)
        else:
            _logger.info(data)
            obj = self.create(data)
        return obj
