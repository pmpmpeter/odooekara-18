from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from collections import defaultdict


class RevisionHistory(models.Model):
    _name = 'revision.history'
    _description = 'Revision History'

    name = fields.Char(string="Sequence", required=True, copy=False, default='/')
    budget_post_id = fields.Many2one('account.report.budget', string="Budgetary Position")
    budget_code = fields.Char(string="Budget Code")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    initial_allocate = fields.Float(string="Initial Allocation")
    additional_amount = fields.Float(string="Additional Amount")
    budget_id = fields.Many2one('budget.analytic', string='Budget')
    revision_date = fields.Datetime(string='Revision Date')

    @api.model
    def create(self, vals):
        if 'name' not in vals or not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('revision.history') or 'New'
        return super(RevisionHistory, self).create(vals)


class ResCompanyTaxEntity(models.Model):
    _name = "res.company.tax.entity"
    _description = "Tax Entity Master"

    budget_id = fields.Many2one("budget.analytic",string="Company",ondelete="cascade")
    entity_id = fields.Many2one("res.company",string="Entity",required=True)
    share = fields.Float(string="Share (%)",required=True)
    sequence = fields.Integer(string="Sequence",default=1)
    loan_account_id = fields.Many2one("account.account",string="Loan Account")

    
