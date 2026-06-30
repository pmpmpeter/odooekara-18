from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class CashPool(models.Model):
    _name = "cash.pool"
    _description = "Cash Pool"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', copy=False)
    fund_line_ids = fields.One2many('cash.pool.fund.line', 'pool_id', string="Fund Lines")
    sequence = fields.Char(string='Sequence', copy=False)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, copy=False)
    amount = fields.Float(string='Amount')
    active = fields.Boolean('Active', default=True)
    current_balance = fields.Float(string='Current Balance', copy=False)
    available_balance = fields.Float(string='Available Balance', copy=False)
    is_available_balance = fields.Float(string='Is Available Balance')
    manager_id = fields.Many2one('res.partner',string='Manager',copy=False)
    manager = fields.Many2one('res.users',string='Manager',copy=False)
    state = fields.Selection([
            ('draft', 'Draft'),
            ('waiting_for_approval', 'Waiting for Approval'),
            ('approved', 'Approved')
        ], string='Status', default='draft', required=True)
    invalid_cash_pool = fields.Boolean(string='Invalid Cash Pool',default=False)
    x_review_result = fields.Char(string="Review Result")

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (copy)", self.name)
        return super(CashPool, self).copy(default=default)

    def action_reset_to_draft(self):
        for record in self:
            for fund_line in record.fund_line_ids:
                if fund_line.state != 'approved':
                    fund_line.state = 'draft'
            record.state = 'draft'
            record.is_available_balance = False

    def action_submit_for_approval(self):
        for record in self:
            if record.fund_line_ids:
                for fund_line in record.fund_line_ids:
                    if fund_line.amount <= 0:
                        raise ValidationError("The fund amount must be greater than 0.")

            if record.manager_id and not record.manager_id.email:
                raise ValidationError("The selected manager must have an email address.")

            for fund_line in record.fund_line_ids:
                if fund_line.state != 'approved':
                    fund_line.state = 'waiting_for_approval'
            record.state = 'waiting_for_approval'

    def action_approved(self):
        for record in self:
            approved_fund_lines = record.fund_line_ids.filtered(lambda l: l.state == 'waiting_for_approval')
            current_balance = record.current_balance
            total_amount = 0.0
            avail_total_amount = 0.0
            for fund_line in approved_fund_lines:
                fund_line.opening_balance = current_balance
                fund_line.closing_balance = current_balance + fund_line.amount
                current_balance = fund_line.closing_balance
                total_amount += fund_line.amount

            record.current_balance += total_amount
            approved_fund_lines.write({'state': 'approved'})
            template = self.env.ref('accounts_extended.cash_pool_manager_email_template')
            if template:
                template.sudo().send_mail(record.id, force_send=True)
            if hasattr(self, 'x_has_request_approval'):
                self.x_has_request_approval = False
            if not record.is_available_balance:
                record.available_balance = record.current_balance
                fund = self.env['fund.management'].sudo().search([])
                lines = fund.cash_pool_line
                if lines:
                    for line in lines:
                        if line.cash_pool.id == record.id:
                            avail_total_amount += abs(
                                line.april_cash_pool + line.may_cash_pool + line.june_cash_pool + line.july_cash_pool + line.august_cash_pool + line.september_cash_pool +
                                line.october_cash_pool + line.november_cash_pool + line.december_cash_pool + line.january_cash_pool + line.febuary_cash_pool + line.march_cash_pool)
                    record.available_balance = record.current_balance - avail_total_amount
                    if record.available_balance == 0:
                        record.invalid_cash_pool = True
                    else:
                        record.invalid_cash_pool = False
                record.is_available_balance = True
            record.state = 'approved'

    # @api.model_create_multi
    # def create(self, vals_list):
    #     for vals in vals_list:
    #             vals['sequence'] = self.env['ir.sequence'].next_by_code('cash.pool')
    #     return super().create(vals_list)


class CashPoolFundLine(models.Model):
    _name = "cash.pool.fund.line"
    _description = "Cash Pool Fund Line"

    pool_id = fields.Many2one('cash.pool', string="Cash Pool", ondelete="cascade")
    added_by_id = fields.Many2one('res.users', string="Added By", default=lambda self:self.env.user)
    amount = fields.Float(string="Amount")
    date = fields.Date(string="Date")
    approved_by_id = fields.Many2one('res.users', string="Approved By")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_for_approval', 'Waiting Approval'),
        ('approved', 'Approved')
    ], string="Status", default="draft")
    opening_balance = fields.Float(string="Opening Balance")
    closing_balance = fields.Float(string="Closing Balance")



class CashPoolLines(models.Model):
    _name = 'cash.pool.lines'
    _description = "Cash Pool Lines"

    fund_management_id = fields.Many2one('fund.management', string="Fund ID")
    available_balance = fields.Float(string='Available Cash Pool Balance', related='cash_pool.available_balance')
    rev_fund_management_id = fields.Many2one('fund.management', string="Rev Fund ID")
    sequence = fields.Char(string='Sequence', copy=False)
    cash_pool = fields.Many2one('cash.pool', string='Cash Pool')
    april_cash_pool = fields.Float(string="Apr")
    may_cash_pool = fields.Float(string="May")
    june_cash_pool = fields.Float(string="Jun")
    july_cash_pool = fields.Float(string="Jul")
    august_cash_pool = fields.Float(string="Aug")
    september_cash_pool = fields.Float(string="Sep")
    october_cash_pool = fields.Float(string="Oct")
    november_cash_pool = fields.Float(string="Nov")
    december_cash_pool = fields.Float(string="Dec")
    january_cash_pool = fields.Float(string="Jan")
    febuary_cash_pool = fields.Float(string="Feb")
    march_cash_pool = fields.Float(string="Mar")
    quarter_1_cash_pool = fields.Float('Q1')
    quarter_2_cash_pool = fields.Float('Q2')
    quarter_3_cash_pool = fields.Float('Q3')
    quarter_4_cash_pool = fields.Float('Q4')
    version = fields.Integer("Version", default=1, readonly=True, store=True, copy=False)
    version_name = fields.Char("Version", compute='_compute_version_name', store=True, copy=False)
    revision_date = fields.Datetime(string="Allocated Date")

    @api.depends('version')
    def _compute_version_name(self):
        for record in self:
            record.version_name = 'Version ' + str(record.version)

    # @api.depends("april_cash_pool","may_cash_pool","june_cash_pool")
    @api.onchange("april_cash_pool", "may_cash_pool", "june_cash_pool")
    def _compute_q1(self):
        self.quarter_1_cash_pool = self.april_cash_pool + self.may_cash_pool + self.june_cash_pool

    @api.onchange("july_cash_pool", "august_cash_pool", "september_cash_pool")
    def _compute_q2(self):
        self.quarter_2_cash_pool = self.july_cash_pool + self.august_cash_pool + self.september_cash_pool

    @api.onchange("october_cash_pool", "november_cash_pool", "december_cash_pool")
    def _compute_q3(self):
        self.quarter_3_cash_pool = self.october_cash_pool + self.november_cash_pool + self.december_cash_pool

    @api.onchange("january_cash_pool", "febuary_cash_pool", "march_cash_pool")
    def _compute_q4(self):
        self.quarter_4_cash_pool = self.january_cash_pool + self.febuary_cash_pool + self.march_cash_pool

    # @api.onchange('april_cash_pool', 'may_cash_pool', 'june_cash_pool', 'july_cash_pool', 'august_cash_pool','september_cash_pool',
    #               'october_cash_pool', 'november_cash_pool', 'december_cash_pool','january_cash_pool', 'febuary_cash_pool', 'march_cash_pool')
    # def _onchange_quarter_cal(self):
    #     print('gggggggggggggggggggggggg')
    #     for rec in self:
    #         rec.quarter_1_cash_pool = rec.april_cash_pool + rec.may_cash_pool + rec.june_cash_pool
    #         rec.quarter_2_cash_pool = rec.july_cash_pool + rec.august_cash_pool + rec.september_cash_pool
    #         rec.quarter_3_cash_pool = rec.october_cash_pool + rec.november_cash_pool + rec.december_cash_pool
    #         rec.quarter_4_cash_pool = rec.january_cash_pool + rec.febuary_cash_pool + rec.febuary_cash_pool
