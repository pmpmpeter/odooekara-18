from odoo import models, fields, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError


class CashManagement(models.Model):
    _name = "cash.management"
    _description = "Cash Requirement Report"
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Enable chatter for tracking

    name = fields.Char(string="Reference", copy=False, readonly=True)

    submit_by = fields.Many2one('hr.employee', string="Submitted By", tracking=True, copy=False)
    submitted_date = fields.Datetime(string="Submitted Date", readonly=True, tracking=True, copy=False)
    submitted_file = fields.Binary(string="Submitted CRR Report", attachment=True, copy=False)
    submitted_name = fields.Char(string="Submitted File Name", attachment=True, copy=False)
    tax_entity = fields.Selection([('entity1', 'Tax Entity1'),
                                   ('entity2', 'Tax Entity2'),
                                   ('both', 'Both')], string="Tax Entity", tracking=True, copy=False)
    tax_entity_1 = fields.Many2one('res.users', string="Tax Entity 1 User", copy=False)
    tax_entity_2 = fields.Many2one('res.users', string="Tax Entity 2 User", copy=False)
    tax_entity1 = fields.Many2one('res.company', string="Tax Entity 1 User", copy=False)
    tax_entity2 = fields.Many2one('res.company', string="Tax Entity 2 User", copy=False)
    tax_entity_1_amount = fields.Float(string="Tax Entity 1 Amount", copy=False, tracking=True, )
    tax_entity_2_amount = fields.Float(string="Tax Entity 2 Amount", copy=False, tracking=True, )

    approval_status = fields.Selection([
        ('draft', 'Draft'),
        ('to approve', 'To Approve'),
        ('approved', 'Approved'),
        ('submitted', 'Submitted'),
        ('consolidated', 'Consolidated'),
    ], string="Approval Status", default='draft', tracking=True, copy=False)

    approved_by = fields.Many2one('res.users', string="Approved By", readonly=True, copy=False)
    approved_date = fields.Datetime(string="Approved Date", readonly=True, copy=False)
    approved_file = fields.Binary(string="Approved CRR Report", copy=False)
    approved_name = fields.Char(string="Approved CRR Report", copy=False)
    revision_reason = fields.Text(string="Revision Reasons", readonly=True, default="")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    approval_state = fields.Char(string='Approval Status', compute='compute_approval_state', store=True, copy=False,
                                 tracking=True)
    approval_document = fields.Many2one('multi.approval', string='Approval Record', copy=False)
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", tracking=True, copy=False)
    start_date = fields.Date(string='Start Date')
    to_date = fields.Date(string='End Date')
    cash_payment_ids = fields.One2many('cash.management.line', 'cash_id', string="Cash Payments",
                                       domain=[('cash_type', '=', 'cash_payment')])
    cash_receipt_ids = fields.One2many('cash.management.line', 'cash_id', string="Cash Receipts",
                                       domain=[('cash_type', '=', 'cash_receipt')])
    budget_id = fields.Many2one('budget.analytic', string='Budget')
    x_review_result = fields.Char(string="Review Result")

    @api.model
    def default_get(self, fields):
        """Set default values for 'is_manager' when creating a record."""
        defaults = super().default_get(fields)
        entity1 = self.env['ir.config_parameter'].sudo().get_param('accounts_extended.tax_entity')
        entity2 = self.env['ir.config_parameter'].sudo().get_param('accounts_extended.tax_entity1')
        share1 = self.env['ir.config_parameter'].sudo().get_param('accounts_extended.share1')
        share2 = self.env['ir.config_parameter'].sudo().get_param('accounts_extended.share2')
        if entity1 and entity2:
            defaults['tax_entity1'] = self.env['res.company'].sudo().search([('id', '=', entity1)])
            defaults['tax_entity2'] = self.env['res.company'].sudo().search([('id', '=', entity2)])
            defaults['tax_entity_1_amount'] = share1
            defaults['tax_entity_2_amount'] = share2
        if entity1:
            defaults['tax_entity1'] = self.env['res.company'].sudo().search([('id', '=', entity1)])
            defaults['tax_entity_1_amount'] = share1
        if entity1:
            defaults['tax_entity2'] = self.env['res.company'].sudo().search([('id', '=', entity2)])
            defaults['tax_entity_2_amount'] = share2
        return defaults

    def action_crr_lines(self):
        self.ensure_one()
        # crr_ids = self.env['cash.management'].search([('budget_id','=',self.id)]).ids
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRR Line Items',
            'view_mode': 'list',
            'res_model': 'cash.management.line',
            'domain': [('id', 'in', self.cash_payment_ids.ids)],
            'context': {
                'group_by': ['budget_type']
            }
            # 'context': {'default_budget_id': self.id},
        }

    def unlink(self):
        for rec in self:
            if rec.approval_status != 'draft':
                raise UserError('You can able to delete Draft records only')
        return super(CashManagement, self).unlink()

    def action_submit_crr(self):
        for rec in self:
            rec.submitted_date = datetime.now()
            rec.submit_by = self.env.user.employee_id.id
            rec.approval_status = 'submitted'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('cash.management')
        return super().create(vals_list)

    @api.depends('approval_document.type_id.state', 'approval_document.line_ids.state')
    def compute_approval_state(self):
        for record in self:
            if record.approval_document:
                line_states = record.approval_document.line_ids.mapped('state')
                if all(state == 'Draft' for state in line_states):
                    record.approval_state = 'Waiting For Approval'
                elif 'Waiting for Approval' in line_states:
                    waiting_lines = record.approval_document.line_ids.filtered(
                        lambda l: l.state == 'Waiting for Approval')
                    if waiting_lines:
                        record.approval_state = f"Waiting for {', '.join(waiting_lines.mapped('name'))} Approval"
                elif all(state == 'Approved' for state in line_states):
                    record.approval_state = 'Approved'
                elif 'Refused' in line_states:
                    record.approval_state = 'Rejected'
                elif 'Cancel' in line_states:
                    record.approval_state = 'Cancelled'
            else:
                rec = self.env['multi.approval.type'].sudo().search(
                    [('model_id', '=', 'cash.management'), ('state', '=', 'confirm')], limit=1)
                if rec:
                    record.approval_state = 'To Submit for Approval'
                else:
                    record.approval_state = 'Not Applicable'


class CashManagementLine(models.Model):
    _name = 'cash.management.line'
    _description = 'Cash Management Line'

    @api.depends('apr', 'may', 'june', 'july', 'aug', 'sep', 'october', 'nov', 'dec', 'jan', 'feb', 'march')
    def _compute_to_get_quarter_values(self):
        for rec in self:
            rec.quarter_1, rec.quarter_2, rec.quarter_3, rec.quarter_4 = 0.0, 0.0, 0.0, 0.0
            rec.quarter_1 = rec.apr + rec.may + rec.june
            rec.quarter_2 = rec.july + rec.aug + rec.sep
            rec.quarter_3 = rec.october + rec.nov + rec.dec
            rec.quarter_4 = rec.jan + rec.feb + rec.march

    @api.depends('quarter_1', 'quarter_2', 'quarter_3', 'quarter_4')
    def _compute_to_get_total(self):
        for rec in self:
            rec.budget_total = rec.quarter_1 + rec.quarter_2 + rec.quarter_3 + rec.quarter_4

    company_id = fields.Many2one('res.company', string="Company")
    cash_id = fields.Many2one('cash.management', string="Cash Management Reference", ondelete='cascade')
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", related='cash_id.user_type',
                                 store=True)
    budget_position_id = fields.Many2one('account.budget.post', string="Budget \n Position")
    budget_type = fields.Selection([('capex', 'Capex'),
                                    ('opex', 'Opex'),
                                    ('ocif', 'OCIF'),
                                    ('noocif', 'NOOCIF')], string="Budget Type")
    apr = fields.Float(string="Apr")
    may = fields.Float(string="May")
    june = fields.Float(string="Jun")
    july = fields.Float(string="Jul")
    aug = fields.Float(string="Aug")
    sep = fields.Float(string="Sep")
    october = fields.Float(string="Oct")
    nov = fields.Float(string="Nov")
    dec = fields.Float(string="Dec")
    jan = fields.Float(string="Jan")
    feb = fields.Float(string="Feb")
    march = fields.Float(string="Mar")
    cash_type = fields.Selection([('cash_payment', 'Cash Payment'),
                                  ('cash_receipt', 'Cash Receipt')], string="Cash Type", required=True)
    quarter_1 = fields.Float('Q1', compute='_compute_to_get_quarter_values')
    quarter_2 = fields.Float('Q2', compute='_compute_to_get_quarter_values')
    quarter_3 = fields.Float('Q3', compute='_compute_to_get_quarter_values')
    quarter_4 = fields.Float('Q4', compute='_compute_to_get_quarter_values')
    budget_total = fields.Float('Total', compute='_compute_to_get_total')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    department_id = fields.Many2one('hr.department', string='Department')
