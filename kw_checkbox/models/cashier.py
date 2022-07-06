import logging

from odoo import models, fields, api, _

from .checkbox import CheckBoxApi

_logger = logging.getLogger(__name__)


class CheckboxCashier(models.Model):
    _name = 'kw.checkbox.cashier'
    _inherit = ['kw.checkbox.mixin']
    _description = 'Checkbox Cashier'
    _sql_constraints = [
        ('cb_id_uniq', 'unique (cb_id)', _('CheckBox ID must be unique'))]

    name = fields.Char(
        readonly=True, )
    active = fields.Boolean(
        default=True, )
    username = fields.Char(
        required=True, )
    password = fields.Char(
        required=True, )
    access_token = fields.Char(
        readonly=True, )
    cb_id = fields.Char(
        string='CheckBox ID', readonly=True, )
    key_id = fields.Char(
        readonly=True, )
    signature_type = fields.Char(
        readonly=True, )
    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', change_default=True,
        default=lambda self: self.env.user.company_id.id, )
    user_ids = fields.Many2many(
        comodel_name='res.users', string='Users',
        relation='kw_checkbox_cashier_res_users_rel',
        column1='cashier_id', column2='user_id', )
    organization_cb_id = fields.Char(
        string='Organization CheckBox ID', readonly=True, )
    organization_id = fields.Many2one(
        comodel_name='kw.checkbox.organization', readonly=True, )
    is_log_enabled = fields.Boolean(
        default=False, )

    @api.model
    def get_cashier_token(self, organization=None):
        domain = []
        if organization:
            domain.append(['organization_id', '=', organization.id])
        for cashier in self.search(domain):
            checkbox = cashier.get_checkbox()
            if checkbox:
                return checkbox.access_token
        return False

    def get_checkbox(self):
        self.ensure_one()
        checkbox = CheckBoxApi(
            access_token=self.access_token,
            test_mode=self.company_id.kw_checkbox_mode != 'prod')
        try:
            checkbox.cashier_me()
        except Exception as e:
            _logger.debug(e)
            checkbox = CheckBoxApi(
                username=self.username, password=self.password,
                test_mode=self.company_id.kw_checkbox_mode != 'prod')
            self.write({'access_token': checkbox.cashier_signin()})
            return checkbox
        else:
            return checkbox

    def update_info(self):
        self.ensure_one()
        checkbox = self.get_checkbox()
        res = checkbox.cashier_me()
        self.write({
            'key_id': res['key_id'], 'signature_type': res['signature_type'],
            'cb_id': res['id'], 'name': res['full_name'],
            'organization_cb_id': res['organization']['id'], })
        if not self.organization_id:
            org = self.env['kw.checkbox.organization'].search([
                ('cb_id', '=', res['organization']['id'])], limit=1)
            if not org:
                org = self.env['kw.checkbox.organization'].create({
                    'cb_id': res['organization']['id'], })
            self.organization_id = org.id
        self.organization_id.write({
            'name': res['organization']['title'],
            'edrpou': res['organization']['edrpou'],
            'tax_number': res['organization']['tax_number'], })

    def action_shifts(self):
        self.ensure_one()
        action = self.env.ref(
            'kw_checkbox.kw_checkbox_kw_checkbox_shift_action_window'
            '').read()[0]
        action['domain'] = [('cashier_id', '=', self.id)]
        return action

    def update_shifts(self):
        self.ensure_one()
        checkbox = self.get_checkbox()
        res = checkbox.shifts_get({
            'status': ['CREATED', 'OPENING', 'OPENED', 'CLOSING',
                       'CLOSED'],
            'desc': True, 'limit': 25, 'offset': 0, })
        for r in res['results']:
            r['cashier'] = {'id': self.cb_id}
            self.env['kw.checkbox.shift'].get_or_create(r)
