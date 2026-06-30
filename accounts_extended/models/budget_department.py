from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class DepartmentBudget(models.Model):
    _name = "budget.department"
    _rec_name = 'name'
    _description = "Department Budget"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', copy=False)
    sequence = fields.Char(string='Sequence', copy=False)
    department_id = fields.Many2one('hr.department', string='Department', required=True)
    analytic_account_id = fields.Many2one('account.analytic.account', required=True, string="Analytic Account")
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company)
    # crossovered_budget_id = fields.Many2one('crossovered.budget', 'Budget', required=True)
    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    active = fields.Boolean('Active', default=True)
    state = fields.Selection(selection=[
        ('draft', 'Draft'),
        ('submit', 'Submitted'),
        ('cancel', 'Cancelled'),
    ], string='Status', copy=False, tracking=True, default='draft')
    # cash_payment_ids = fields.One2many('crr.budget.line', 'budget_department_id', string="CRR Lines")
    cash_type = fields.Selection([('cash_payment', 'Cash Payment'),
                                  ('cash_receipt', 'Cash Receipt')], string="Cash Type")

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (copy)", self.name)
        return super(DepartmentBudget, self).copy(default=default)

    def unlink(self):
        for rec in self:
            if rec.state == 'submit':
                raise UserError('You cannot delete submitted record.')
        super().unlink()

    def _check_budget_position_configuration(self):
        self.ensure_one()
        budget_positions = self.cash_payment_ids.budget_position_id.filtered(lambda b: not b.budget_type)
        if budget_positions:
            raise ValidationError(
                'Budget type for the following Budgetary Positions are not configured.\nBudgetary Positions:- %s' % ', '.join(
                    budget_positions.mapped("name")))

    def action_submit(self):
        for rec in self:
            rec._check_budget_position_configuration()
            # if rec.crossovered_budget_id.state == 'done':
            #     raise UserError('The Budget: %s is in done stage.' % rec.crossovered_budget_id.name)
            if not rec.cash_payment_ids:
                raise UserError('Please Add Monthly Breakups.')
            for line in rec.cash_payment_ids:
                # pass
                line.write({
                    'budget_name': line.budget_position_id.name,
                    'analytic_account_id': rec.analytic_account_id.id,
                    'department_id': rec.department_id.id,
                    # 'budget_id': rec.crossovered_budget_id.id,
                    # 'version': rec.crossovered_budget_id.version,
                })

            # rec.cash_payment_ids.write({'budget_id':rec.crossovered_budget_id.id})
            rec.state = 'submit'

    def action_cancel(self):
        for rec in self:
            rec.cash_payment_ids.write({'budget_id': False})
            rec.state = 'cancel'

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'
