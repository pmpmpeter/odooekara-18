from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from collections import defaultdict


class BudgetAnalytic(models.Model):
    _inherit = 'budget.analytic'

    name = fields.Char('Budget Name', required=True, tracking=1)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, tracking=True)
    date_from = fields.Date('Start Date', tracking=True)
    date_to = fields.Date('End Date', tracking=True)
    revision_date = fields.Datetime(string='Last Revised Date')
    fy_crr_budget_total = fields.Float("Total CRR", tracking=1, readonly=True)
    fy_cur_budget_total = fields.Float("Total Utilization", tracking=1, readonly=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('revision', 'To Revision'),
        ('confirm', 'Confirmed'),
        ('to approve', 'To Approve'),
        ('validate', 'Validated'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ], 'Status', default='draft', index=True, required=True, readonly=True, copy=False, tracking=True)
    approval_state = fields.Char(string='Approval Status', compute='compute_approval_state', store=True, copy=False,
                                 tracking=True)
    approval_document = fields.Many2one('multi.approval', string='Approval Record', copy=False)
    revision_reason = fields.Text(string="Revision Reasons", readonly=True, default="", copy=False)
    revision_history_ids = fields.One2many('revision.history', 'budget_post_id', string='Revision History')
    crr_line_count = fields.Float('CRR', compute='_compute_crr_line_count')
    share_line_count = fields.Float('CRR', compute='_compute_crr_line_count')
    is_budget_consolidate = fields.Float('Is Budget Consolidated', copy=False)
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", tracking=True, copy=False)
    partner_id = fields.Many2one('res.partner', string='Requested Company')
    cash_payment_ids = fields.One2many('crr.budget.line', 'budget_id', string="CRR Lines")
    crr_consolidate = fields.One2many('crr.budget.line.consolidate', 'budget_id',
                                      string="Cash Outflow/Cash Inflow - Consolidate")
    cash_receipt_ids = fields.One2many('crr.budget.line', 'budget_id', string="Cash Receipts",
                                       domain=[('cash_type', '=', 'cash_receipt')])
    show_budget_sum = fields.Boolean('Show budget Sum', default=False, copy=False)
    tax_entity1 = fields.Many2one('res.company', string="Tax Entity 1 User", copy=False)
    tax_entity2 = fields.Many2one('res.company', string="Tax Entity 2 User", copy=False)
    tax_entity_1_percentage = fields.Float(string="Tax Entity 1 %", copy=False, tracking=True)
    tax_entity_2_percentage = fields.Float(string="Tax Entity 2 %", copy=False, tracking=True)
    crr_share_ids = fields.One2many('crr.share.line', 'budget_id', string='CRR Share')
    freez_april_month = fields.Boolean("Freeze April",default=False)
    freez_may_month = fields.Boolean("Freeze May",default=False)
    freez_june_month = fields.Boolean("Freeze June",default=False)
    freez_july_month = fields.Boolean("Freeze July",default=False)
    freez_august_month = fields.Boolean("Freeze August",default=False)
    freez_september_month = fields.Boolean("Freeze September",default=False)
    freez_october_month = fields.Boolean("Freeze October",default=False)
    freez_november_month = fields.Boolean("Freeze November",default=False)
    freez_december_month = fields.Boolean("Freeze December",default=False)
    freez_january_month = fields.Boolean("Freeze January",default=False)
    freez_february_month = fields.Boolean("Freeze February",default=False)
    freez_march_month = fields.Boolean("Freeze March",default=False)
    cash_balance_apr = fields.Float(string='Cash Balance as on 1st April', copy=False)

    rf_freez_april_month = fields.Boolean("Freeze April",default=False)
    rf_freez_may_month = fields.Boolean("Freeze May",default=False)
    rf_freez_june_month = fields.Boolean("Freeze June",default=False)
    rf_freez_july_month = fields.Boolean("Freeze July",default=False)
    rf_freez_august_month = fields.Boolean("Freeze August",default=False)
    rf_freez_september_month = fields.Boolean("Freeze September",default=False)
    rf_freez_october_month = fields.Boolean("Freeze October",default=False)
    rf_freez_november_month = fields.Boolean("Freeze November",default=False)
    rf_freez_december_month = fields.Boolean("Freeze December",default=False)
    rf_freez_january_month = fields.Boolean("Freeze January",default=False)
    rf_freez_february_month = fields.Boolean("Freeze February",default=False)
    rf_freez_march_month = fields.Boolean("Freeze March",default=False)

    x_has_request_approval = fields.Boolean(string="Request Approval",default=False)
    x_review_result = fields.Char(string="Review Result")

    version = fields.Integer("Version", default=1, readonly=True, store=True, copy=False)
    share_rev_effective_from = fields.Selection(selection=[
        ('april', 'April'),
        ('may', 'May'),
        ('june', 'June'),
        ('july', 'July'),
        ('august', 'August'),
        ('september', 'September'),
        ('october', 'October'),
        ('november', 'November'),
        ('december', 'December'),
        ('january', 'January'),
        ('february', 'February'),
        ('march', 'March')
    ], string="Share Revision Effective from", copy=False)
    is_update_required = fields.Boolean(string="Update required",default=False)
    is_share_revised = fields.Boolean(string='Share Revised',default=False)
    doc_attachment = fields.One2many('doc.attach','budget_id', string='Attachments')
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Budget name already exists!"),
    ]
    tax_entity_ids = fields.One2many(
        "res.company.tax.entity",
        "budget_id",
        string="Tax Entities",
    )

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        self.ensure_one()
        default = dict(default or {})
        if 'name' not in default:
            default['name'] = _("%s (copy)", self.name)
        return super(BudgetAnalytic, self).copy(default=default)

    def _compute_crr_line_count(self):
        for rec in self:
            rec.crr_line_count = len(
                self.env['cash.management'].search([('budget_id', '=', self.id)]).cash_payment_ids.ids) or 0
            rec.share_line_count = len(rec.crr_share_ids)
            entity_ids = self.env.company.tax_entity_ids.ids
            if entity_ids:
                rec.tax_entity_ids = [(6, 0, entity_ids)]

    def freeze_april_month(self):
        self.freez_april_month = True

    def freeze_may_month(self):
        self.freez_may_month = True

    def freeze_june_month(self):
        self.freez_june_month = True

    def freeze_july_month(self):
        self.freez_july_month = True

    def freeze_august_month(self):
        self.freez_august_month = True

    def freeze_september_month(self):
        self.freez_september_month = True

    def freeze_october_month(self):
        self.freez_october_month = True

    def freeze_november_month(self):
        self.freez_november_month = True

    def freeze_december_month(self):
        self.freez_december_month = True

    def freeze_january_month(self):
        self.freez_january_month = True

    def freeze_february_month(self):
        self.freez_february_month = True

    def freeze_march_month(self):
        self.freez_march_month = True

    def action_rf_freez_april_month(self):
        self.rf_freez_april_month = True if not self.rf_freez_april_month else False

    def action_rf_freez_may_month(self):
        self.rf_freez_may_month = True if not self.rf_freez_may_month else False

    def action_rf_freez_june_month(self):
        self.rf_freez_june_month = True if not self.rf_freez_june_month else False

    def action_rf_freez_july_month(self):
        self.rf_freez_july_month = True if not self.rf_freez_july_month else False

    def action_rf_freez_august_month(self):
        self.rf_freez_august_month = True if not self.rf_freez_august_month else False

    def action_rf_freez_september_month(self):
        self.rf_freez_september_month = True if not self.rf_freez_september_month else False

    def action_rf_freez_october_month(self):
        self.rf_freez_october_month = True if not self.rf_freez_october_month else False

    def action_rf_freez_november_month(self):
        self.rf_freez_november_month = True if not self.rf_freez_november_month else False

    def action_rf_freez_december_month(self):
        self.rf_freez_december_month = True if not self.rf_freez_december_month else False

    def action_rf_freez_january_month(self):
        self.rf_freez_january_month = True if not self.rf_freez_january_month else False

    def action_rf_freez_february_month(self):
        self.rf_freez_february_month = True if not self.rf_freez_february_month else False

    def action_rf_freez_march_month(self):
        self.rf_freez_march_month = True if not self.rf_freez_march_month else False

    def get_cash_balance(self):
        query = """
                    select sum(aml.debit-aml.credit) as balance
                    from account_move_line aml
                    join account_account aa on (aa.id = aml.account_id)
                    where aa.account_type='asset_cash' and aml.date<%s
                    AND aml.company_id = %s;
                """
        query_params = (self.date_from, self.company_id.id)
        self.env.cr.execute(query, query_params)
        lines = self.env.cr.dictfetchall()
        if (lines[0].get('balance') != None):
            opening_balance_1 = lines[0].get('balance')
            self.cash_balance_apr = opening_balance_1

    def action_draft(self):
        if self.env.user.has_group('multi_level_approval.group_approval_manager'):
            model_name = 'budget.analytic'
            res_id = self.id
            origin_ref = f"{model_name},{res_id}"
            existing_approvals = self.env['multi.approval'].search(
                [("origin_ref", "=", origin_ref), ("state", "=", 'Submitted')])
            existing_approvals.write({'state': 'Cancel'})
            vals = {
                'approval_state': 'To Submit for Approval',
                'x_has_request_approval': False,
            }
            if self.version == 1:
                vals['state'] = 'draft'
            else:
                vals['state'] = 'revision'
            self.sudo().write(vals)
        else:
            raise ValidationError('You can not reset the record to draft. Please contact the Administrator.')

    def update_cash_balance_apr(self):
        # if self.user_type == "odoo" and self.cash_balance_apr:
        if self.user_type == "odoo":
            surplus_line = self.crr_consolidate.search(
                [('budget_name', '=', 'Surplus/ Deficit(IN-OUT)'), ('budget_id', '=', self.id)])
            cash = self.cash_balance_apr
            actual_april_crr_budget_plan = 0
            actual_may_crr_budget_plan = 0
            actual_june_crr_budget_plan = 0
            if not self.crr_consolidate.search(
                    [('budget_name', '=', 'Actual Surplus/ Deficit'), ('budget_id', '=', self.id)]):
                if cash > abs(surplus_line.april_crr_budget_plan):
                    actual_april_crr_budget_plan = cash - abs(surplus_line.april_crr_budget_plan)
                    if actual_april_crr_budget_plan > abs(surplus_line.may_crr_budget_plan):
                        actual_may_crr_budget_plan = actual_april_crr_budget_plan - abs(
                            surplus_line.may_crr_budget_plan)
                        if actual_may_crr_budget_plan > surplus_line.june_crr_budget_plan:
                            actual_june_crr_budget_plan = actual_may_crr_budget_plan - abs(
                                surplus_line.june_crr_budget_plan)
                    self.crr_consolidate.create({'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                                                 'april_crr_budget_plan': actual_april_crr_budget_plan,
                                                 'may_crr_budget_plan': actual_may_crr_budget_plan,
                                                 'june_crr_budget_plan': actual_june_crr_budget_plan,
                                                 'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                                                 'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                                                 'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                                                 'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                                                 'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                                                 'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                                                 'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                                                 'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                                                 'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                                                 'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                                                     actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                                                 'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                                                 'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                                                 'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                                                 'is_actual_surples': True,
                                                 'sequence': 10})
                else:
                    self.crr_consolidate.create(
                        {'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                         'april_crr_budget_plan': cash - abs(surplus_line.april_crr_budget_plan),
                         'may_crr_budget_plan': surplus_line.may_crr_budget_plan,
                         'june_crr_budget_plan': surplus_line.june_crr_budget_plan,
                         'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                         'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                         'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                         'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                         'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                         'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                         'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                         'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                         'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                         'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                             actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                         'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                         'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                         'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                         'is_actual_surples': True,
                         'sequence': 10})
            else:
                existing = self.crr_consolidate.search(
                    [('budget_name', '=', 'Actual Surplus/ Deficit'), ('budget_id', '=', self.id)])
                if cash > abs(surplus_line.april_crr_budget_plan):
                    actual_april_crr_budget_plan = cash - abs(surplus_line.april_crr_budget_plan)
                    if actual_april_crr_budget_plan > abs(surplus_line.may_crr_budget_plan):
                        actual_may_crr_budget_plan = actual_april_crr_budget_plan - abs(
                            surplus_line.may_crr_budget_plan)
                        if actual_may_crr_budget_plan > surplus_line.june_crr_budget_plan:
                            actual_june_crr_budget_plan = actual_may_crr_budget_plan - abs(
                                surplus_line.june_crr_budget_plan)
                    existing.write(
                        {'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                         'april_crr_budget_plan': actual_april_crr_budget_plan,
                         'may_crr_budget_plan': actual_may_crr_budget_plan,
                         'june_crr_budget_plan': actual_june_crr_budget_plan,
                         'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                         'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                         'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                         'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                         'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                         'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                         'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                         'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                         'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                         'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                             actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                         'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                         'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                         'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                         'is_actual_surples': True,
                         'sequence': 10})
                else:
                    existing.write(
                        {'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                         'april_crr_budget_plan': cash - abs(surplus_line.april_crr_budget_plan),
                         'may_crr_budget_plan': surplus_line.may_crr_budget_plan,
                         'june_crr_budget_plan': surplus_line.june_crr_budget_plan,
                         'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                         'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                         'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                         'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                         'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                         'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                         'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                         'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                         'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                         'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                             actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                         'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                         'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                         'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                         'is_actual_surples': True,
                         'sequence': 10})

       
        if self.user_type == "non_odoo":
            surplus_line = self.cash_payment_ids.search(
                [('budget_name', '=', 'Surplus/ Deficit(IN-OUT)'), ('budget_id', '=', self.id)])
            cash = self.cash_balance_apr
            actual_april_crr_budget_plan = 0
            actual_may_crr_budget_plan = 0
            actual_june_crr_budget_plan = 0
            if not self.cash_payment_ids.search(
                    [('budget_name', '=', 'Actual Surplus/ Deficit'), ('budget_id', '=', self.id)]):
                if cash > abs(surplus_line.april_crr_budget_plan):
                    actual_april_crr_budget_plan = cash - abs(surplus_line.april_crr_budget_plan)
                    if actual_april_crr_budget_plan > abs(surplus_line.may_crr_budget_plan):
                        actual_may_crr_budget_plan = actual_april_crr_budget_plan - abs(
                            surplus_line.may_crr_budget_plan)
                        if actual_may_crr_budget_plan > surplus_line.june_crr_budget_plan:
                            actual_june_crr_budget_plan = actual_may_crr_budget_plan - abs(
                                surplus_line.june_crr_budget_plan)
                        else:
                            actual_june_crr_budget_plan = surplus_line.june_crr_budget_plan
                    else:
                        actual_may_crr_budget_plan = surplus_line.may_crr_budget_plan
                        actual_june_crr_budget_plan = surplus_line.june_crr_budget_plan
                    self.cash_payment_ids.create({'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                                                  'april_crr_budget_plan': actual_april_crr_budget_plan,
                                                  'may_crr_budget_plan': actual_may_crr_budget_plan,
                                                  'june_crr_budget_plan': actual_june_crr_budget_plan,
                                                  'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                                                  'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                                                  'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                                                  'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                                                  'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                                                  'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                                                  'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                                                  'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                                                  'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                                                  'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                                                      actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                                                  'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                                                  'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                                                  'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                                                  'is_actual_surples': True,
                                                  'sequence': 10})
                else:
                    self.cash_payment_ids.create(
                        {'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                         'april_crr_budget_plan': cash - abs(surplus_line.april_crr_budget_plan),
                         'may_crr_budget_plan': surplus_line.may_crr_budget_plan,
                         'june_crr_budget_plan': surplus_line.june_crr_budget_plan,
                         'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                         'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                         'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                         'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                         'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                         'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                         'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                         'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                         'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                         'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                             actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                         'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                         'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                         'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                         'is_actual_surples': True,
                         'sequence': 10})


            else:
                existing = self.cash_payment_ids.search(
                    [('budget_name', '=', 'Actual Surplus/ Deficit'), ('budget_id', '=', self.id)])
                if cash > abs(surplus_line.april_crr_budget_plan):
                    actual_april_crr_budget_plan = abs(surplus_line.april_crr_budget_plan) - cash
                    if actual_april_crr_budget_plan > abs(surplus_line.may_crr_budget_plan):
                        actual_may_crr_budget_plan = actual_april_crr_budget_plan - abs(
                            surplus_line.may_crr_budget_plan)
                        if actual_may_crr_budget_plan > surplus_line.june_crr_budget_plan:
                            actual_june_crr_budget_plan = actual_may_crr_budget_plan - abs(
                                surplus_line.june_crr_budget_plan)
                        else:
                            actual_june_crr_budget_plan = surplus_line.june_crr_budget_plan
                    else:
                        actual_may_crr_budget_plan = surplus_line.may_crr_budget_plan
                        actual_june_crr_budget_plan = surplus_line.june_crr_budget_plan
                    existing.write(
                        {'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                         'april_crr_budget_plan': actual_april_crr_budget_plan,
                         'may_crr_budget_plan': actual_may_crr_budget_plan,
                         'june_crr_budget_plan': actual_june_crr_budget_plan,
                         'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                         'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                         'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                         'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                         'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                         'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                         'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                         'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                         'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                         'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                             actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                         'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                         'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                         'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                         'is_actual_surples': True,
                         'sequence': 10})

                else:
                    existing.write(
                        {'budget_name': 'Actual Surplus/ Deficit', 'budget_id': self.id,
                         'april_crr_budget_plan': cash - abs(surplus_line.april_crr_budget_plan),
                         'may_crr_budget_plan': surplus_line.may_crr_budget_plan,
                         'june_crr_budget_plan': surplus_line.june_crr_budget_plan,
                         'july_crr_budget_plan': surplus_line.july_crr_budget_plan,
                         'august_crr_budget_plan': surplus_line.august_crr_budget_plan,
                         'september_crr_budget_plan': surplus_line.september_crr_budget_plan,
                         'october_crr_budget_plan': surplus_line.october_crr_budget_plan,
                         'november_crr_budget_plan': surplus_line.november_crr_budget_plan,
                         'december_crr_budget_plan': surplus_line.december_crr_budget_plan,
                         'january_crr_budget_plan': surplus_line.january_crr_budget_plan,
                         'febuary_crr_budget_plan': surplus_line.febuary_crr_budget_plan,
                         'march_crr_budget_plan': surplus_line.march_crr_budget_plan,
                         'quarter_1_crr_budget_plan': abs(actual_april_crr_budget_plan) + abs(
                             actual_may_crr_budget_plan) + abs(actual_june_crr_budget_plan),
                         'quarter_2_crr_budget_plan': surplus_line.quarter_2_crr_budget_plan,
                         'quarter_3_crr_budget_plan': surplus_line.quarter_3_crr_budget_plan,
                         'quarter_4_crr_budget_plan': surplus_line.quarter_4_crr_budget_plan,
                         'is_actual_surples': True,
                         'sequence': 10})

    def update_share_amount(self):
        if self.crr_share_ids:
            for rec in self.crr_share_ids:
                actual_surplus = self.crr_consolidate.search(
                    [('budget_name', '=', 'Actual Surplus/ Deficit'), ('budget_id', '=', self.id)])
                if actual_surplus:
                    for entity in self.company_id.tax_entity_ids:
                        share = entity.share
                        rec.write({
                            'crr_share_april': share / 100 * (actual_surplus.april_crr_budget_plan),
                            'crr_share_may': share / 100 * (actual_surplus.may_crr_budget_plan),
                            'crr_share_june': share / 100 * (actual_surplus.june_crr_budget_plan),
                        })

                else:
                    surplus = self.crr_consolidate.search(
                        [('budget_name', '=', 'Surplus/ Deficit'), ('budget_id', '=', self.id)])
                    if actual_surplus:
                        if rec.entity == self.tax_entity1:
                            share = self.tax_entity_1_percentage
                            rec.write({
                                'crr_share_april': share / 100 * (surplus.april_crr_budget_plan),
                                'crr_share_may': share / 100 * (surplus.may_crr_budget_plan),
                                'crr_share_june': share / 100 * (surplus.june_crr_budget_plan),
                            })
                        elif rec.entity == self.tax_entity2:
                            share = self.tax_entity_2_percentage
                            rec.write({
                                'crr_share_april': share / 100 * (surplus.april_crr_budget_plan),
                                'crr_share_may': share / 100 * (surplus.may_crr_budget_plan),
                                'crr_share_june': share / 100 * (surplus.june_crr_budget_plan),
                            })

    @api.onchange('freez_april_month', 'freez_may_month', 'freez_june_month', 'freez_july_month', 'freez_august_month',
                  'freez_september_month', 'freez_october_month', 'freez_november_month', 'freez_december_month',
                  'freez_january_month', 'freez_february_month', 'freez_march_month')
    def _onchange_freeze_month(self):
        for field in self._fields:
            if field.startswith('freez_') and getattr(self, field):
                self._freeze_all_fields(field)

    def _freeze_all_fields(self, active_field):
        for field in self._fields:
            if field.startswith('freez_') and field != active_field:
                setattr(self, field, False)

    @api.model
    def default_get(self, fields):
        """Set default values for 'is_manager' when creating a record."""
        defaults = super().default_get(fields)
        entity1 = self.env.company.tax_entity1.id
        entity2 = self.env.company.tax_entity2.id
        share1 = self.env.company.share1
        share2 = self.env.company.share2
        entity_ids = self.env.company.tax_entity_ids.ids
        if entity_ids:
            defaults['tax_entity_ids'] = [(6, 0, entity_ids)]

        if entity1 and entity2:
            defaults['tax_entity1'] = entity1
            defaults['tax_entity2'] = entity2
            defaults['tax_entity_1_percentage'] = share1
            defaults['tax_entity_2_percentage'] = share2
        elif entity1:
            defaults['tax_entity1'] = entity1
            defaults['tax_entity_1_percentage'] = share1
        elif entity2:
            defaults['tax_entity2'] = entity2
            defaults['tax_entity_2_percentage'] = share2
        if defaults.get('user_type') == 'non_odoo':
            budget_position = self.env['account.report.budget'].sudo().search([('budget_category', '=', 'consolidate')],
                                                                            order='sequence asc')
            new_lines = []
            for line in budget_position:
                new_lines.append((0, 0, {
                    'budget_position_id': line.id,
                    'budget_type': line.budget_type,
                }))
                defaults['cash_payment_ids'] = new_lines
        return defaults

    def unlink(self):
        for rec in self:
            # if rec.is_budget_consolidate:
            if rec.state != 'draft':
                raise UserError('You can only delete records when they are in the Draft stage.')
        return super(BudgetAnalytic, self).unlink()

    def action_open_forecast_lines(self):
        self.ensure_one()
        crr_ids = self.env['crr.budget.line'].sudo().search(
            ['|', ('revision_budget_id', 'in', self.ids), ('budget_id', 'in', self.ids)])
        action = self.env['ir.actions.actions']._for_xml_id(
            'accounts_extended.action_open_rolling_forecast_odoo') if self.user_type == 'odoo' else self.env[
            'ir.actions.actions']._for_xml_id('accounts_extended.action_open_rolling_forecast_non_odoo')
        # action['domain'] = [('id', 'in', crr_ids.ids)]
        return action

    def action_open_budget_vs_actual(self):
        self.ensure_one()
        # crr_ids = self.env['crr.budget.line'].sudo().search(
        #     [('budget_id', 'in', self.ids)])
        action = self.env['ir.actions.actions']._for_xml_id(
            'accounts_extended.action_open_budget_vs_actual_odoo') if self.user_type == 'odoo' else self.env[
            'ir.actions.actions']._for_xml_id('accounts_extended.action_open_budget_vs_actual_non_odoo')
        # action['domain'] = [('budget_id', 'in', self.ids)]
        # action['context'] = {'group_by': False}
        return action

    def action_open_crr_lines(self):
        self.ensure_one()
        crr_ids = self.env['crr.budget.line'].sudo().search([('id', 'in', self.cash_payment_ids.ids)])
        view_id = self.env.ref(
            'accounts_extended.crr_budget_line_extend1').id if self.user_type == 'odoo' else self.env.ref(
            'accounts_extended.crr_budget_line_extend2').id
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRR Line Items',
            'view_mode': 'tree',
            'view_id': view_id,
            'res_model': 'crr.budget.line',
            'domain': [('id', 'in', crr_ids.ids)],
        }

    def action_open_share_lines(self):
        self.ensure_one()
        share_ids = self.crr_share_ids
        # view_id = self.env.ref(
        #     'accounts_extended.crr_budget_line_extend1').id
        action = {
            'type': 'ir.actions.act_window',
            'name': 'Share Amount',
            'view_mode': 'tree',
            # 'view_id': view_id,
            'res_model': 'crr.share.line',
            'context': {'group_by': ['version_name']},
            'domain': ['|', ('revision_budget_id', 'in', self.ids), ('budget_id', 'in', self.ids)],
            # 'domain': [('id', 'in', share_ids.ids)],
        }
        # action['context']['group_by'] = ['version_name']
        return action

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
                    [('model_id', '=', 'budget.analytic'), ('state', '=', 'confirm')], limit=1)
                if rec:
                    record.approval_state = 'To Submit for Approval'
                else:
                    record.approval_state = 'Not Applicable'

    def action_share_revise(self):
        for rec in self:
            rec.is_share_revised = True
            for rec in self:
                prev_version = rec.version
                version = rec.version + 1
                rec.cash_payment_ids.sudo().write({
                    'version': version,
                })
                crr_ids = self.env['crr.budget.line'].sudo().search(
                    ['|', ('budget_id', 'in', self.ids), ('revision_budget_id', 'in', self.ids)])
                sequence = len(crr_ids) + 1
                for line in rec.cash_payment_ids:
                    line.copy({
                        'sequence': sequence,
                        'budget_id': False,
                        'revision_budget_id': rec.id,
                        'version': prev_version,
                    })
                    sequence += 1
                rec.crr_share_ids.sudo().write({
                    'version': version,
                })
                crr_share_ids = self.env['crr.share.line'].sudo().search(
                    ['|', ('budget_id', 'in', self.ids), ('revision_budget_id', 'in', self.ids)])
                share_sequence = len(crr_share_ids) + 1
                for line in rec.crr_share_ids:
                    line.copy({
                        'budget_id': False,
                        'revision_budget_id': rec.id,
                        'version': prev_version,
                    })
                    share_sequence += 1
                # print('new_lines',new_lines)
                # new_lines = new_lines.filtered(lambda l:l.version == version)
                rec.sudo().write({
                    'version': version,
                    'revision_date': fields.Datetime.now(),
                })


    def _action_revise(self):
        for rec in self:
            prev_version = rec.version
            version = rec.version + 1
            rec.cash_payment_ids.sudo().write({
                'version': version,
            })
            crr_ids = self.env['crr.budget.line'].sudo().search(
                ['|', ('budget_id', 'in', self.ids), ('revision_budget_id', 'in', self.ids)])
            sequence = len(crr_ids) + 1
            for line in rec.cash_payment_ids:
                line.copy({
                    'sequence': sequence,
                    'budget_id': False,
                    'revision_budget_id': rec.id,
                    'version': prev_version,
                })
                sequence += 1
            rec.crr_share_ids.sudo().write({
                'version': version,
            })
            crr_share_ids = self.env['crr.share.line'].sudo().search(
                ['|', ('budget_id', 'in', self.ids), ('revision_budget_id', 'in', self.ids)])
            share_sequence = len(crr_share_ids) + 1
            for line in rec.crr_share_ids:
                line.copy({
                    'budget_id': False,
                    'revision_budget_id': rec.id,
                    'version': prev_version,
                })
                share_sequence += 1
            # print('new_lines',new_lines)
            # new_lines = new_lines.filtered(lambda l:l.version == version)
            rec.sudo().write({
                'version': version,
                'revision_date': fields.Datetime.now(),
            })

    def action_revise(self):
        return {
            'name': 'Budget Revision',
            'type': 'ir.actions.act_window',
            'res_model': 'budget.revision.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

    def action_budget_confirm(self):
        for line in self.budget_line_ids:
            if not line.analytic_account_id and line.user_type == 'odoo':
                raise UserError('Kinldy add a Analytic Account for a Budget Line')

        return super().action_budget_confirm()

    def action_budget_done(self):
        for rec in self.budget_line_ids:
            if not rec.is_budget_code:
                rec.is_budget_code = True
                rec.budget_code = self.env['ir.sequence'].next_by_code('budget.code')
        return super().action_budget_done()


    def consolidate_crr(self):
        self._check_budget_position_configuration()
        if self.user_type == "non_odoo":
            new_lines = []
            existing_lines = self.budget_line_ids.ids
            for line in self.cash_payment_ids:
                if not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line:
                    if existing_lines:
                        budget = self.budget_line_ids.filtered(
                            lambda rec: rec.general_budget_id in [line.budget_position_id])
                        self.write({
                            'budget_line_ids': [(1, budget.id, {
                                'general_budget_id': line.budget_position_id.id,
                                'capex_opex': line.budget_type,
                                'date_from': self.date_from,
                                'date_to': self.date_to,
                                'committed_amount': line.crr_budget_total,
                            })]
                        })
                    else:

                        new_lines.append((0, 0, {
                            'general_budget_id': line.budget_position_id.id,
                            'capex_opex': line.budget_type,
                            'date_from': self.date_from,
                            'date_to': self.date_to,
                            'committed_amount': line.crr_budget_total,
                        }))
            if new_lines:
                self.budget_line_ids = new_lines
            surplus = self.cash_payment_ids.filtered(lambda rec: rec.is_budget_surples_sum_line)
            surplus._compute_to_get_quarter_values()

        elif self.user_type == "odoo":
            new_lines = []
            existing_lines = self.budget_line_ids.ids
            for line in self.cash_payment_ids:
                if not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line:
                    if existing_lines:
                        budget = self.budget_line_ids.filtered(
                            lambda rec: rec.crr_budget_line_id in [line])
                        if budget:
                            self.write({
                                'budget_line_ids': [(1, budget.id, {
                                    'general_budget_id': line.budget_position_id.id,
                                    'capex_opex': line.budget_type,
                                    'date_from': self.date_from,
                                    'date_to': self.date_to,
                                    'committed_amount': line.crr_budget_total,
                                    'analytic_account_id': line.analytic_account_id.id,
                                    'department_id': line.department_id.id,

                                })]
                            })
                        else:
                            new_lines.append((0, 0, {
                                'general_budget_id': line.budget_position_id.id,
                                'capex_opex': line.budget_type,
                                'date_from': self.date_from,
                                'date_to': self.date_to,
                                'committed_amount': line.crr_budget_total,
                                'analytic_account_id': line.analytic_account_id.id,
                                'department_id': line.department_id.id,
                                'crr_budget_line_id': line.id
                            }))
                    else:
                        new_lines.append((0, 0, {
                            'general_budget_id': line.budget_position_id.id,
                            'capex_opex': line.budget_type,
                            'date_from': self.date_from,
                            'date_to': self.date_to,
                            'committed_amount': line.crr_budget_total,
                            'analytic_account_id': line.analytic_account_id.id,
                            'department_id': line.department_id.id,
                            'crr_budget_line_id': line.id
                        }))
            if new_lines:
                self.budget_line_ids = new_lines
            surplus = self.crr_consolidate.filtered(lambda rec: rec.is_budget_surples_sum_line)
            surplus._compute_to_get_quarter_values()
        self.is_budget_consolidate = True

    def _get_share_vals(self, entity, surplus_line):
        # share = self.tax_entity_1_percentage if entity == self.tax_entity1 else self.tax_entity_2_percentage
        share = entity.share
        share_factor = share / 100
        month_vals = {
            'crr_share_april': share_factor * (surplus_line.april_crr_budget_plan),
            'crr_share_may': share_factor * (surplus_line.may_crr_budget_plan),
            'crr_share_june': share_factor * (surplus_line.june_crr_budget_plan),
            'crr_share_july': share_factor * (surplus_line.july_crr_budget_plan),
            'crr_share_august': share_factor * (surplus_line.august_crr_budget_plan),
            'crr_share_september': share_factor * (surplus_line.september_crr_budget_plan),
            'crr_share_october': share_factor * (surplus_line.october_crr_budget_plan),
            'crr_share_november': share_factor * (surplus_line.november_crr_budget_plan),
            'crr_share_december': share_factor * (surplus_line.december_crr_budget_plan),
            'crr_share_january': share_factor * (surplus_line.january_crr_budget_plan),
            'crr_share_february': share_factor * (surplus_line.febuary_crr_budget_plan),
            'crr_share_march': share_factor * (surplus_line.march_crr_budget_plan)
        }

        if self.share_rev_effective_from:
            months = ['april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december',
                      'january', 'february', 'march']
            slice_index = months.index(self.share_rev_effective_from)
            months_to_update = months[slice_index:]
            filtered_dict = {}
            for key, value in month_vals.items():
                month_name = key.replace('crr_share_', '')
                if month_name in months_to_update:
                    filtered_dict[key] = value
            month_vals = filtered_dict
            month_vals.update({'share_rev_effective_from': self.share_rev_effective_from,
                               'revision_date': fields.Date.today(),
                                'crr_consolidate_id':surplus_line.id,
                               })

        share_vals = {
            'entity': entity.entity_id.id,
            'version': self.version,
            'tax_entity_percentage': share,
            'company_id': self.company_id.id,
            'budget_id': self.id,
            'ref_company': self.sudo().company_id.name if self.sudo().user_type == 'odoo' else self.sudo().partner_id.name,
        }
        share_vals.update(month_vals)
        return share_vals

    def split_share_amount(self):
        self.update_cash_balance_apr()
        if not self.company_id.tax_entity_ids:
            raise ValidationError('Kindly Fill any one Tax Entity Details.')
        # if self.tax_entity_1_percentage and not self.tax_entity1:
        #     raise ValidationError('Kindly Add Tax Entity 1 User')
        # if self.tax_entity_2_percentage and not self.tax_entity2:
        #     raise ValidationError('Kindly Add Tax Entity 2 User')
        if self.version > 1 and not self.share_rev_effective_from:
            raise ValidationError('Please specify the month from which the Share Revision should be effective.')
        total = self.tax_entity_1_percentage + self.tax_entity_2_percentage
        if total < 100 or total > 100:
            raise ValidationError('Share must be 100%.')
        self.consolidate_crr()
        if self.user_type == "non_odoo":
            actual_surplus = self.cash_payment_ids.filtered(lambda rec: rec.is_actual_surples)
            surplus = self.cash_payment_ids.filtered(
                lambda rec: rec.is_budget_surples_sum_line) if not actual_surplus else actual_surplus
            # surplus._compute_to_get_quarter_values()
        else:
            actual_surplus = self.crr_consolidate.filtered(lambda rec: rec.is_actual_surples)
            surplus = self.crr_consolidate.filtered(
                lambda rec: rec.is_budget_surples_sum_line) if not actual_surplus else actual_surplus
            # surplus = self.crr_consolidate.filtered(lambda rec: rec.is_budget_surples_sum_line)
        surplus._compute_to_get_quarter_values()
        self.crr_share_ids.unlink()
        share_line = self.crr_share_ids
        if not share_line:
            for entity in self.company_id.tax_entity_ids:
                share_vals = self._get_share_vals(entity, surplus)
                self.env['crr.share.line'].sudo().create(share_vals)
        else:
            for entity in self.company_id.tax_entity_ids:
                for line in share_line:
                    if entity.id in share_line.entity.ids:
                        if entity.id == line.entity:
                            share_vals = self._get_share_vals(line.entity, surplus)
                            line.sudo().write(share_vals)
                    else:
                        share_vals = self._get_share_vals(entity, surplus)
                        self.env['crr.share.line'].sudo().create(share_vals)

        self.is_share_revised = False

    def action_consolidate_crr_lines(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consolidate CRR',
            'view_mode': 'tree',
            'res_model': 'crr.budget.line.consolidate',
            'domain': [('id', 'in', self.crr_consolidate.ids)],
        }

    def _check_budget_position_configuration(self):
        self.ensure_one()
        budget_positions = self.cash_payment_ids.budget_position_id.filtered(lambda b: not b.budget_type)
        if budget_positions:
            raise ValidationError(
                'Budget type for the following Budgetary Positions are not configured.\nBudgetary Positions:- %s' % ', '.join(
                    budget_positions.mapped("name")))

    def action_consolidate_crr_lines_total(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Consolidate CRR Total',
            'view_mode': 'tree',
            'res_model': 'crr.budget.line',
            'domain': ['&', ('budget_id', '=', self.id), '|', '|',
                       ('is_budget_in_sum_line', '=', True),
                       ('is_budget_total', '=', True),
                       ('is_budget_out_sum_line', '=', True)
                       ],
            'context': {'group_by': ['analytic_account_id']},
        }

    def update_main_budget_cashflow_surplus(self):
        for record in self:
            for line in self.cash_payment_ids.filtered(lambda c: c.is_budget_surples_sum_line):
                record.write({'fy_crr_budget_total': line.crr_budget_total})
                record.write({'fy_cur_budget_total': line.cur_budget_total})

    def update_cash_outflow_inflow_calculation(self):
        self._check_budget_position_configuration()
        self._get_cash_outflow_inflow()
        self.cash_payment_ids._compute_to_get_quarter_values()
        self.consolidate_crr()
        self.update_main_budget_cashflow_surplus()
        # self.cash_payment_ids._compute_total_budget_value(self.id)

    def get_cash_outflow_inflow_calculation(self):
        self._check_budget_position_configuration()
        if self.user_type == 'non_odoo':
            crr_line_ids = self.cash_payment_ids.sudo().search([('budget_id', '=', self.id)]).ids
            seq = 1
            for outflow_type_id in self.cash_payment_ids.search(
                    [('budget_type', 'in', ('opex', 'capex')), ('budget_id', '=', self.id),
                     ('id', 'in', crr_line_ids)]):
                outflow_type_id.sequence = seq
                outflow_type_id.budget_name = outflow_type_id.budget_position_id.name
                seq += 1
            self.env['crr.budget.line'].create(
                {'budget_name': 'Total Cash Outflow', 'budget_id': self.id, 'is_budget_out_sum_line': True,
                 'sequence': seq})
            seq += 1
            for inflow_type_id in self.cash_payment_ids.search(
                    [('budget_type', 'in', ('ocif', 'noocif')), ('budget_id', '=', self.id),
                     ('id', 'in', crr_line_ids)]):
                inflow_type_id.budget_name = inflow_type_id.budget_position_id.name
                inflow_type_id.sequence = seq
                seq += 1
            self.env['crr.budget.line'].create(
                {'budget_name': 'Total Cash Inflow', 'budget_id': self.id, 'is_budget_in_sum_line': True,
                 'sequence': seq})
            seq += 1
            self.env['crr.budget.line'].create(
                {'budget_name': 'Surplus/ Deficit(IN-OUT)', 'budget_id': self.id, 'is_budget_surples_sum_line': True,
                 'sequence': seq})
        elif self.user_type == 'odoo':
            self._get_cash_outflow_inflow()
            seq = 1
            for rec in self.env['account.report.budget'].search(
                    [('budget_category', '=', 'consolidate'), ('budget_type', 'in', ('opex', 'capex'))],
                    order='sequence asc'):
                self.env['crr.budget.line.consolidate'].create({
                    'company_id': self.env.user.company_id.id,
                    'budget_id': self.id,
                    'budget_position_id': rec.id,
                    'budget_type': rec.budget_type,
                    'april_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'april_crr_budget_plan')),
                    'may_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'may_crr_budget_plan')),
                    'june_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'june_crr_budget_plan')),
                    'july_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'july_crr_budget_plan')),
                    'august_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'august_crr_budget_plan')),
                    'september_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'september_crr_budget_plan')),
                    'october_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'october_crr_budget_plan')),
                    'november_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'november_crr_budget_plan')),
                    'december_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'december_crr_budget_plan')),
                    'january_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'january_crr_budget_plan')),
                    'febuary_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'febuary_crr_budget_plan')),
                    'march_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'march_crr_budget_plan')),
                    'cash_type': 'cash_payment',
                    'budget_name': rec.name,
                    'sequence': seq,
                })
                seq += 1
            self.env['crr.budget.line.consolidate'].create(
                {'budget_name': 'Total Cash Outflow', 'budget_id': self.id, 'is_budget_out_sum_line': True,
                 'sequence': seq})
            seq += 1
            for rec in self.env['account.report.budget'].search(
                    [('budget_category', '=', 'consolidate'), ('budget_type', 'in', ('ocif', 'noocif'))],
                    order='sequence asc'):
                self.env['crr.budget.line.consolidate'].create({
                    'company_id': self.env.user.company_id.id,
                    'budget_id': self.id,
                    'budget_position_id': rec.id,
                    'budget_type': rec.budget_type,
                    'april_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'april_crr_budget_plan')),
                    'may_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'may_crr_budget_plan')),
                    'june_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'june_crr_budget_plan')),
                    'july_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'july_crr_budget_plan')),
                    'august_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'august_crr_budget_plan')),
                    'september_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'september_crr_budget_plan')),
                    'october_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'october_crr_budget_plan')),
                    'november_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'november_crr_budget_plan')),
                    'december_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'december_crr_budget_plan')),
                    'january_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'january_crr_budget_plan')),
                    'febuary_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'febuary_crr_budget_plan')),
                    'march_crr_budget_plan': sum(self.cash_payment_ids.search(
                        [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
                        'march_crr_budget_plan')),
                    'cash_type': 'cash_payment',
                    'budget_name': rec.name,
                    'sequence': seq,
                })
                seq += 1
            self.env['crr.budget.line.consolidate'].create(
                {'budget_name': 'Total Cash Inflow', 'budget_id': self.id, 'is_budget_in_sum_line': True,
                 'sequence': seq, })
            seq += 1
            self.env['crr.budget.line.consolidate'].create(
                {'budget_name': 'Surplus/ Deficit(IN-OUT)', 'budget_id': self.id, 'is_budget_surples_sum_line': True,
                 'sequence': seq})
            self.cash_payment_ids._compute_total_budget_value(self.id)
        self.show_budget_sum = True
        self.consolidate_crr()
        self.update_cash_outflow_inflow_calculation()
        return True

    def _get_cash_outflow_inflow(self):
        if self.user_type == 'odoo':
            for item in self.cash_payment_ids:
                if not item.budget_name:
                    item.budget_name = item.budget_position_id.name
            acc_ids = self.cash_payment_ids.mapped('analytic_account_id')
            print('acc_ids', acc_ids.mapped('name'))
            #     seq = 1
            monthly_breakup_lines = self.env['crr.budget.line']
            for acc_id in acc_ids:
                print('acc_id', acc_id.name)
                crr_line_ids = self.cash_payment_ids.filtered(
                    lambda c: c.analytic_account_id == acc_id and c.version == self.version)
                opex_total_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Operational Expenditure(OPEX) Total' and c.is_budget_total)
                if not opex_total_line:
                    opex_total_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Operational Expenditure(OPEX) Total', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id,
                         'version': self.version,
                         'is_budget_total': True})

                opex_line_items = opex_total_line

                capex_total_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Capital Expenditure(CAPEX) Total' and c.is_budget_total)
                if not capex_total_line:
                    capex_total_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Capital Expenditure(CAPEX) Total', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id, 'version': self.version,
                         'is_budget_total': True})
                capex_line_items = capex_total_line
                noocif_total_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Non-Operating Cash-In-Flow (NOCIF) Total' and c.is_budget_total)
                if not noocif_total_line:
                    noocif_total_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Non-Operating Cash-In-Flow (NOCIF) Total', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id, 'version': self.version,
                         'is_budget_total': True})
                noocif_line_items = noocif_total_line
                ocif_total_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Operating Cash-In-Flow (OCIF) Total' and c.is_budget_total)
                if not ocif_total_line:
                    ocif_total_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Operating Cash-In-Flow (OCIF) Total', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id, 'version': self.version,
                         'is_budget_total': True})
                ocif_line_items = ocif_total_line
                # ----------------------------------------------------------------- #

                total_cash_outflow_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Total Cash Outflow' and c.is_budget_out_sum_line)
                if not total_cash_outflow_line:
                    total_cash_outflow_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Total Cash Outflow', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id, 'version': self.version,
                         'is_budget_out_sum_line': True})
                total_cash_inflow_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Total Cash Inflow' and c.is_budget_in_sum_line)
                if not total_cash_inflow_line:
                    total_cash_inflow_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Total Cash Inflow', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id, 'version': self.version,
                         'is_budget_in_sum_line': True})

                    ##################################################################
                total_surplus_deficit_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Surplus/ Deficit(IN-OUT)' and c.is_budget_surples_sum_line)
                if not total_surplus_deficit_line:
                    total_surplus_deficit_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Surplus/ Deficit(IN-OUT)', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id, 'version': self.version,
                         'is_budget_surples_sum_line': True})
                budget_lines = crr_line_ids.filtered(
                    lambda
                        line: not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line)
                for line in budget_lines.sorted(reverse=True):
                    if line.budget_type == 'opex':
                        opex_line_items = line + opex_line_items
                        # opex_line_items += line
                    if line.budget_type == 'capex':
                        # capex_line_items += line
                        capex_line_items = line + capex_line_items
                    if line.budget_type == 'noocif':
                        noocif_line_items = line + noocif_line_items
                        # noocif_line_items += line
                    if line.budget_type == 'ocif':
                        # ocif_line_items += line
                        ocif_line_items = line + ocif_line_items

                opex_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'opex')
                opex_total_line.write({
                    'april_crr_budget_plan': sum(opex_budget_lines.mapped('april_crr_budget_plan')),
                    'may_crr_budget_plan': sum(opex_budget_lines.mapped('may_crr_budget_plan')),
                    'june_crr_budget_plan': sum(opex_budget_lines.mapped('june_crr_budget_plan')),
                    'july_crr_budget_plan': sum(opex_budget_lines.mapped('july_crr_budget_plan')),
                    'august_crr_budget_plan': sum(opex_budget_lines.mapped('august_crr_budget_plan')),
                    'september_crr_budget_plan': sum(opex_budget_lines.mapped('september_crr_budget_plan')),
                    'october_crr_budget_plan': sum(opex_budget_lines.mapped('october_crr_budget_plan')),
                    'november_crr_budget_plan': sum(opex_budget_lines.mapped('november_crr_budget_plan')),
                    'december_crr_budget_plan': sum(opex_budget_lines.mapped('december_crr_budget_plan')),
                    'january_crr_budget_plan': sum(opex_budget_lines.mapped('january_crr_budget_plan')),
                    'febuary_crr_budget_plan': sum(opex_budget_lines.mapped('febuary_crr_budget_plan')),
                    'march_crr_budget_plan': sum(opex_budget_lines.mapped('march_crr_budget_plan')),
                })

                capex_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'capex')
                capex_total_line.write({
                    'april_crr_budget_plan': sum(capex_budget_lines.mapped('april_crr_budget_plan')),
                    'may_crr_budget_plan': sum(capex_budget_lines.mapped('may_crr_budget_plan')),
                    'june_crr_budget_plan': sum(capex_budget_lines.mapped('june_crr_budget_plan')),
                    'july_crr_budget_plan': sum(capex_budget_lines.mapped('july_crr_budget_plan')),
                    'august_crr_budget_plan': sum(capex_budget_lines.mapped('august_crr_budget_plan')),
                    'september_crr_budget_plan': sum(capex_budget_lines.mapped('september_crr_budget_plan')),
                    'october_crr_budget_plan': sum(capex_budget_lines.mapped('october_crr_budget_plan')),
                    'november_crr_budget_plan': sum(capex_budget_lines.mapped('november_crr_budget_plan')),
                    'december_crr_budget_plan': sum(capex_budget_lines.mapped('december_crr_budget_plan')),
                    'january_crr_budget_plan': sum(capex_budget_lines.mapped('january_crr_budget_plan')),
                    'febuary_crr_budget_plan': sum(capex_budget_lines.mapped('febuary_crr_budget_plan')),
                    'march_crr_budget_plan': sum(capex_budget_lines.mapped('march_crr_budget_plan')),
                })

                noocif_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'noocif')
                noocif_total_line.write({
                    'april_crr_budget_plan': sum(noocif_budget_lines.mapped('april_crr_budget_plan')),
                    'may_crr_budget_plan': sum(noocif_budget_lines.mapped('may_crr_budget_plan')),
                    'june_crr_budget_plan': sum(noocif_budget_lines.mapped('june_crr_budget_plan')),
                    'july_crr_budget_plan': sum(noocif_budget_lines.mapped('july_crr_budget_plan')),
                    'august_crr_budget_plan': sum(noocif_budget_lines.mapped('august_crr_budget_plan')),
                    'september_crr_budget_plan': sum(noocif_budget_lines.mapped('september_crr_budget_plan')),
                    'october_crr_budget_plan': sum(noocif_budget_lines.mapped('october_crr_budget_plan')),
                    'november_crr_budget_plan': sum(noocif_budget_lines.mapped('november_crr_budget_plan')),
                    'december_crr_budget_plan': sum(noocif_budget_lines.mapped('december_crr_budget_plan')),
                    'january_crr_budget_plan': sum(noocif_budget_lines.mapped('january_crr_budget_plan')),
                    'febuary_crr_budget_plan': sum(noocif_budget_lines.mapped('febuary_crr_budget_plan')),
                    'march_crr_budget_plan': sum(noocif_budget_lines.mapped('march_crr_budget_plan')),
                })

                ocif_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'ocif')
                ocif_total_line.write({
                    'april_crr_budget_plan': sum(ocif_budget_lines.mapped('april_crr_budget_plan')),
                    'may_crr_budget_plan': sum(ocif_budget_lines.mapped('may_crr_budget_plan')),
                    'june_crr_budget_plan': sum(ocif_budget_lines.mapped('june_crr_budget_plan')),
                    'july_crr_budget_plan': sum(ocif_budget_lines.mapped('july_crr_budget_plan')),
                    'august_crr_budget_plan': sum(ocif_budget_lines.mapped('august_crr_budget_plan')),
                    'september_crr_budget_plan': sum(ocif_budget_lines.mapped('september_crr_budget_plan')),
                    'october_crr_budget_plan': sum(ocif_budget_lines.mapped('october_crr_budget_plan')),
                    'november_crr_budget_plan': sum(ocif_budget_lines.mapped('november_crr_budget_plan')),
                    'december_crr_budget_plan': sum(ocif_budget_lines.mapped('december_crr_budget_plan')),
                    'january_crr_budget_plan': sum(ocif_budget_lines.mapped('january_crr_budget_plan')),
                    'febuary_crr_budget_plan': sum(ocif_budget_lines.mapped('febuary_crr_budget_plan')),
                    'march_crr_budget_plan': sum(ocif_budget_lines.mapped('march_crr_budget_plan')),
                })

               

                monthly_breakup_lines += opex_line_items + capex_line_items + total_cash_outflow_line + noocif_line_items + ocif_line_items + total_cash_inflow_line + total_surplus_deficit_line
                print(4444444444444444, total_cash_inflow_line.april_crr_budget_plan)

            seq = 1
            for breakup_line in monthly_breakup_lines:
                breakup_line.sequence = seq
                breakup_line.is_consolidated = True
                seq += 1

    
class BudgetLines(models.Model):
    _inherit = 'budget.line'

    def _compute_achieved_amount(self):
        groups = defaultdict(lambda: defaultdict(set))
        for line in self:
            model, fname, accounts = self._get_accounts_from_line(line)
            groups[(model, fname)][(line.date_from, line.date_to)].update(accounts)

        queries = []
        queries_params = []
        for (model, fname), by_date in groups.items():
            for (date_from, date_to), account_ids in by_date.items():
                query, params = self._get_query_account_analytic_line(model, fname, date_from, date_to, account_ids)
                queries.append(query)
                queries_params += params

        self.env.cr.execute(" UNION ALL ".join(queries), queries_params)

        agg_general = defaultdict(lambda: defaultdict(float))  # {(model, date_from, date_to): {(analytic, general): amount}}
        agg_analytic = defaultdict(lambda: defaultdict(float))  # {(model, date_from, date_to): {analytic: amount}}
        for model, fname, date_from, date_to, account_id, general_account_id, amount in self.env.cr.fetchall():
            agg_general[(model, fname, date_from, date_to)][(account_id, general_account_id)] += amount
            agg_analytic[(model, fname, date_from, date_to)][account_id] += amount

        for line in self:
            model, fname, accounts = self._get_accounts_from_line(line)
            general_accounts = line.general_budget_id.account_ids
            if general_accounts:
                line.achieved_amount = sum(
                    agg_general.get((model, fname, line.date_from, line.date_to), {}).get((account, general_account), 0)
                    for account in accounts
                    for general_account in general_accounts.ids
                )
            else:
                line.achieved_amount = 0

    def unlink(self):
        for rec in self:
            if rec.budget_analytic_id.is_budget_consolidate:
                raise UserError('You cannot able to delete Consolidated records')
        return super(BudgetLines, self).unlink()

    def _compute_balance_amount(self):
        for rec in self:
            rec.balance_amount = rec.committed_amount - (abs(rec.achieved_amount) + rec.reserved_amount)

    @api.depends('additional_amount')
    def _compute_is_edited(self):
        for rec in self:
            rec.under_revision = False
            if rec.budget_analytic_id.state == 'revision':
                if rec.additional_amount > 0:
                    rec.under_revision = True

    name = fields.Char(compute="_compute_line_name", store=True)
    budget_code = fields.Char('Budget Code')
    is_budget_code = fields.Boolean('Is Budget Code',default=False)
    reserved_amount = fields.Float('Reserved Amount')
    balance_amount = fields.Float('Balance Amount', compute='_compute_balance_amount')
    capex_opex = fields.Selection([
        ('capex', 'Capex'),
        ('opex', 'Opex'),
        ('ocif', 'OCIF'),
        ('noocif', 'NOOCIF')
    ], 'Capex/Opex/OCIF/NOOCIF', default='capex', index=True, required=True, copy=False, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department')
    additional_amount = fields.Float('Additional Amount')
    under_revision = fields.Boolean(string='Under Revision', default=False, copy=False)
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", tracking=True, copy=False)
    crr_budget_line_id = fields.Many2one('crr.budget.line', string="CRR Lines")

    def write(self, vals):
        if vals.get('committed_amount'):
            message = _("Planned Amount has been Updated: from " + str(self.committed_amount) + ' to ' + str(
                vals.get('committed_amount')))
            if self.budget_analytic_id:
                self.budget_analytic_id.message_post(body=message)  # Logs message in parent Budget record
        if self.budget_analytic_id.state == 'revision':
            if vals.get('additional_amount') or vals.get('general_budget_id') or vals.get(
                    'analytic_account_id') or vals.get('department_id') or vals.get('capex_opex') or vals.get(
                'date_from') or vals.get('date_to'):
                vals['under_revision'] = True
        return super(BudgetLines, self).write(vals)

    @api.depends("budget_analytic_id", "budget_code")
    def _compute_line_name(self):
        for record in self:
            computed_name = record.budget_analytic_id.name
            if record.general_budget_id:
                computed_name += ' - ' + record.general_budget_id.name
            if record.analytic_account_id:
                computed_name += ' - ' + record.analytic_account_id.name
            if record.budget_code:
                computed_name += ' - ' + record.budget_code
            record.name = computed_name

