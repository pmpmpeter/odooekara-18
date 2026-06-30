from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from collections import defaultdict


class CrossoveredBudget(models.Model):
    _inherit = 'crossovered.budget'

    name = fields.Char('Budget Name', required=True, tracking=1)
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user, tracking=True)
    date_from = fields.Date('Start Date', tracking=True)
    date_to = fields.Date('End Date', tracking=True)
    crossovered_budget_line = fields.One2many('crossovered.budget.lines', 'crossovered_budget_id', 'Budget Lines',
                                              copy=False)
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
    revision_history_ids = fields.One2many('revision.history', 'budget_id', string='Revision History')
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
        return super(CrossoveredBudget, self).copy(default=default)

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
            model_name = 'crossovered.budget'
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

            # if self.crr_share_ids:
            #     for rec in self.crr_share_ids:
            #         actual_surplus = self.crr_consolidate.search(
            #             [('budget_name', '=', 'Actual Surplus/ Deficit'), ('budget_id', '=', self.id)])
            #         if rec.entity == self.tax_entity1:
            #             share = self.tax_entity_1_percentage
            #             rec.write({
            #                 'crr_share_april': share / 100 * (actual_surplus.april_crr_budget_plan),
            #                 'crr_share_may': share / 100 * (actual_surplus.may_crr_budget_plan),
            #                 'crr_share_june': share / 100 * (actual_surplus.june_crr_budget_plan),
            #             })
            #         elif rec.entity == self.tax_entity2:
            #             share = self.tax_entity_2_percentage
            #             rec.write({
            #                 'crr_share_april': share / 100 * (actual_surplus.april_crr_budget_plan),
            #                 'crr_share_may': share / 100 * (actual_surplus.may_crr_budget_plan),
            #                 'crr_share_june': share / 100 * (actual_surplus.june_crr_budget_plan),
            #             })

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

                    # if rec.entity == self.tax_entity1:
                    #     share = self.tax_entity_1_percentage
                    #     rec.write({
                    #         'crr_share_april': share / 100 * (actual_surplus.april_crr_budget_plan),
                    #         'crr_share_may': share / 100 * (actual_surplus.may_crr_budget_plan),
                    #         'crr_share_june': share / 100 * (actual_surplus.june_crr_budget_plan),
                    #     })
                    # elif rec.entity == self.tax_entity2:
                    #     share = self.tax_entity_2_percentage
                    #     rec.write({
                    #         'crr_share_april': share / 100 * (actual_surplus.april_crr_budget_plan),
                    #         'crr_share_may': share / 100 * (actual_surplus.may_crr_budget_plan),
                    #         'crr_share_june': share / 100 * (actual_surplus.june_crr_budget_plan),
                    #     })
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
            budget_position = self.env['account.budget.post'].sudo().search([('budget_category', '=', 'consolidate')],
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
        return super(CrossoveredBudget, self).unlink()

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
                    [('model_id', '=', 'crossovered.budget'), ('state', '=', 'confirm')], limit=1)
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
        for line in self.crossovered_budget_line:
            if not line.analytic_account_id and line.user_type == 'odoo':
                raise UserError('Kinldy add a Analytic Account for a Budget Line')

        return super().action_budget_confirm()

    def action_budget_done(self):
        for rec in self.crossovered_budget_line:
            if not rec.is_budget_code:
                rec.is_budget_code = True
                rec.budget_code = self.env['ir.sequence'].next_by_code('budget.code')
        return super().action_budget_done()

    # def consolidate_crr(self):
    #     if not self.tax_entity1 and not self.tax_entity2:
    #         raise ValidationError('Kindly Fill any one Tax Entity  Details')
    #     total = self.tax_entity_1_percentage + self.tax_entity_2_percentage
    #     if total < 100 or total > 100:
    #         raise ValidationError('Share must be 100%')
    #     if self.user_type == "non_odoo":
    #         new_lines = []
    #         existing_lines = self.crossovered_budget_line.ids
    #         for line in self.cash_payment_ids:
    #             if not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line:
    #                 if existing_lines:
    #                     budget = self.crossovered_budget_line.filtered(
    #                         lambda rec: rec.general_budget_id in [line.budget_position_id])
    #                     self.write({
    #                         'crossovered_budget_line': [(1, budget.id, {
    #                             'general_budget_id': line.budget_position_id.id,
    #                             'capex_opex': line.budget_type,
    #                             'date_from': self.date_from,
    #                             'date_to': self.date_to,
    #                             'planned_amount': line.crr_budget_total,
    #                         })]
    #                     })
    #                 else:
    #
    #                     new_lines.append((0, 0, {
    #                         'general_budget_id': line.budget_position_id.id,
    #                         'capex_opex': line.budget_type,
    #                         'date_from': self.date_from,
    #                         'date_to': self.date_to,
    #                         'planned_amount': line.crr_budget_total,
    #                     }))
    #         if new_lines:
    #             self.crossovered_budget_line = new_lines
    #         surplus = self.cash_payment_ids.filtered(lambda rec: rec.is_budget_surples_sum_line)
    #         surplus._compute_to_get_quarter_values()
    #         share_line = []
    #         ent = 1
    #         for entity in [self.tax_entity1, self.tax_entity2]:
    #             if entity:
    #                 share = self.tax_entity_1_percentage if ent == 1 else self.tax_entity_2_percentage
    #                 if not self.crr_share_ids:
    #                     share_line.append((0, 0, {
    #                         'entity': entity.id,
    #                         'company_id': self.company_id.id,
    #                         'crr_share_april': share / 100 * (surplus.april_crr_budget_plan),
    #                         'crr_share_may': share / 100 * (surplus.may_crr_budget_plan),
    #                         'crr_share_june': share / 100 * (surplus.june_crr_budget_plan),
    #                         'crr_share_july': share / 100 * (surplus.july_crr_budget_plan),
    #                         'crr_share_august': share / 100 * (surplus.august_crr_budget_plan),
    #                         'crr_share_september': share / 100 * (surplus.september_crr_budget_plan),
    #                         'crr_share_october': share / 100 * (surplus.october_crr_budget_plan),
    #                         'crr_share_november': share / 100 * (surplus.november_crr_budget_plan),
    #                         'crr_share_december': share / 100 * (surplus.december_crr_budget_plan),
    #                         'crr_share_january': share / 100 * (surplus.january_crr_budget_plan),
    #                         'crr_share_february': share / 100 * (surplus.febuary_crr_budget_plan),
    #                         'crr_share_march': share / 100 * (surplus.march_crr_budget_plan),
    #                     }))
    #                 else:
    #                     entity = self.crr_share_ids.filtered(lambda rec: rec.entity in entity)
    #                     self.write({
    #                         'crr_share_ids': [(1, entity.id, {
    #                             # 'entity':self.entity.id,
    #                             'company_id': self.company_id.id,
    #                             'crr_share_april': share / 100 * (surplus.april_crr_budget_plan),
    #                             'crr_share_may': share / 100 * (surplus.may_crr_budget_plan),
    #                             'crr_share_june': share / 100 * (surplus.june_crr_budget_plan),
    #                             'crr_share_july': share / 100 * (surplus.july_crr_budget_plan),
    #                             'crr_share_august': share / 100 * (surplus.august_crr_budget_plan),
    #                             'crr_share_september': share / 100 * (surplus.september_crr_budget_plan),
    #                             'crr_share_october': share / 100 * (surplus.october_crr_budget_plan),
    #                             'crr_share_november': share / 100 * (surplus.november_crr_budget_plan),
    #                             'crr_share_december': share / 100 * (surplus.december_crr_budget_plan),
    #                             'crr_share_january': share / 100 * (surplus.january_crr_budget_plan),
    #                             'crr_share_february': share / 100 * (surplus.febuary_crr_budget_plan),
    #                             'crr_share_march': share / 100 * (surplus.march_crr_budget_plan),
    #                         })]
    #                     })
    #             ent += 1
    #         self.crr_share_ids = share_line
    #
    #     elif self.user_type == "odoo":
    #         new_lines = []
    #         existing_lines = self.crossovered_budget_line.ids
    #         for line in self.cash_payment_ids:
    #             if not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line:
    #                 if existing_lines:
    #                     budget = self.crossovered_budget_line.filtered(
    #                         lambda rec: rec.crr_budget_line_id in [line])
    #                     self.write({
    #                         'crossovered_budget_line': [(1, budget.id, {
    #                             'general_budget_id': line.budget_position_id.id,
    #                             'capex_opex': line.budget_type,
    #                             'date_from': self.date_from,
    #                             'date_to': self.date_to,
    #                             'planned_amount': line.crr_budget_total,
    #                             'analytic_account_id': line.analytic_account_id.id,
    #
    #                         })]
    #                     })
    #                 else:
    #
    #                     new_lines.append((0, 0, {
    #                         'general_budget_id': line.budget_position_id.id,
    #                         'capex_opex': line.budget_type,
    #                         'date_from': self.date_from,
    #                         'date_to': self.date_to,
    #                         'planned_amount': line.crr_budget_total,
    #                         'analytic_account_id': line.analytic_account_id.id,
    #                         'crr_budget_line_id': line.id
    #                     }))
    #         if new_lines:
    #             self.crossovered_budget_line = new_lines
    #         surplus = self.crr_consolidate.filtered(lambda rec: rec.is_budget_surples_sum_line)
    #         surplus._compute_to_get_quarter_values()
    #         share_line = []
    #         ent = 1
    #         for entity in [self.tax_entity1, self.tax_entity2]:
    #             if entity:
    #                 share = self.tax_entity_1_percentage if ent == 1 else self.tax_entity_2_percentage
    #                 if not self.crr_share_ids:
    #                     share_line.append((0, 0, {
    #                         'entity': entity.id,
    #                         'company_id': self.company_id.id,
    #                         'crr_share_april': share / 100 * (surplus.april_crr_budget_plan),
    #                         'crr_share_may': share / 100 * (surplus.may_crr_budget_plan),
    #                         'crr_share_june': share / 100 * (surplus.june_crr_budget_plan),
    #                         'crr_share_july': share / 100 * (surplus.july_crr_budget_plan),
    #                         'crr_share_august': share / 100 * (surplus.august_crr_budget_plan),
    #                         'crr_share_september': share / 100 * (surplus.september_crr_budget_plan),
    #                         'crr_share_october': share / 100 * (surplus.october_crr_budget_plan),
    #                         'crr_share_november': share / 100 * (surplus.november_crr_budget_plan),
    #                         'crr_share_december': share / 100 * (surplus.december_crr_budget_plan),
    #                         'crr_share_january': share / 100 * (surplus.january_crr_budget_plan),
    #                         'crr_share_february': share / 100 * (surplus.febuary_crr_budget_plan),
    #                         'crr_share_march': share / 100 * (surplus.march_crr_budget_plan),
    #                     }))
    #                 else:
    #                     entity = self.crr_share_ids.filtered(lambda rec: rec.entity in entity)
    #                     self.write({
    #                         'crr_share_ids': [(1, entity.id, {
    #                             # 'entity':entity.id,
    #                             'company_id': self.company_id.id,
    #                             'crr_share_april': share / 100 * (surplus.april_crr_budget_plan),
    #                             'crr_share_may': share / 100 * (surplus.may_crr_budget_plan),
    #                             'crr_share_june': share / 100 * (surplus.june_crr_budget_plan),
    #                             'crr_share_july': share / 100 * (surplus.july_crr_budget_plan),
    #                             'crr_share_august': share / 100 * (surplus.august_crr_budget_plan),
    #                             'crr_share_september': share / 100 * (surplus.september_crr_budget_plan),
    #                             'crr_share_october': share / 100 * (surplus.october_crr_budget_plan),
    #                             'crr_share_november': share / 100 * (surplus.november_crr_budget_plan),
    #                             'crr_share_december': share / 100 * (surplus.december_crr_budget_plan),
    #                             'crr_share_january': share / 100 * (surplus.january_crr_budget_plan),
    #                             'crr_share_february': share / 100 * (surplus.febuary_crr_budget_plan),
    #                             'crr_share_march': share / 100 * (surplus.march_crr_budget_plan),
    #                         })]
    #                     })
    #             ent += 1
    #         self.crr_share_ids = share_line
    #     self.is_budget_consolidate = True

    def consolidate_crr(self):
        self._check_budget_position_configuration()
        if self.user_type == "non_odoo":
            new_lines = []
            existing_lines = self.crossovered_budget_line.ids
            for line in self.cash_payment_ids:
                if not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line:
                    if existing_lines:
                        budget = self.crossovered_budget_line.filtered(
                            lambda rec: rec.general_budget_id in [line.budget_position_id])
                        self.write({
                            'crossovered_budget_line': [(1, budget.id, {
                                'general_budget_id': line.budget_position_id.id,
                                'capex_opex': line.budget_type,
                                'date_from': self.date_from,
                                'date_to': self.date_to,
                                'planned_amount': line.crr_budget_total,
                            })]
                        })
                    else:

                        new_lines.append((0, 0, {
                            'general_budget_id': line.budget_position_id.id,
                            'capex_opex': line.budget_type,
                            'date_from': self.date_from,
                            'date_to': self.date_to,
                            'planned_amount': line.crr_budget_total,
                        }))
            if new_lines:
                self.crossovered_budget_line = new_lines
            surplus = self.cash_payment_ids.filtered(lambda rec: rec.is_budget_surples_sum_line)
            surplus._compute_to_get_quarter_values()

        elif self.user_type == "odoo":
            new_lines = []
            existing_lines = self.crossovered_budget_line.ids
            for line in self.cash_payment_ids:
                if not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line:
                    if existing_lines:
                        budget = self.crossovered_budget_line.filtered(
                            lambda rec: rec.crr_budget_line_id in [line])
                        if budget:
                            self.write({
                                'crossovered_budget_line': [(1, budget.id, {
                                    'general_budget_id': line.budget_position_id.id,
                                    'capex_opex': line.budget_type,
                                    'date_from': self.date_from,
                                    'date_to': self.date_to,
                                    'planned_amount': line.crr_budget_total,
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
                                'planned_amount': line.crr_budget_total,
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
                            'planned_amount': line.crr_budget_total,
                            'analytic_account_id': line.analytic_account_id.id,
                            'department_id': line.department_id.id,
                            'crr_budget_line_id': line.id
                        }))
            if new_lines:
                self.crossovered_budget_line = new_lines
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
            for rec in self.env['account.budget.post'].search(
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
            for rec in self.env['account.budget.post'].search(
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
                # [('analytic_account_id', '=', acc_id), ('budget_id', '=', self.id)]).ids
                # opex_domain = [('budget_name','=', 'Operational Expenditure(OPEX)'), ('budget_id','=',  self.id),
                #             ('is_buget_categ','=', True)]
                opex_total_line = crr_line_ids.filtered(
                    lambda c: c.budget_name == 'Operational Expenditure(OPEX) Total' and c.is_budget_total)
                if not opex_total_line:
                    opex_total_line = self.env['crr.budget.line'].create(
                        {'budget_name': 'Operational Expenditure(OPEX) Total', 'analytic_account_id': acc_id.id,
                         'budget_id': self.id,
                         'version': self.version,
                         'is_budget_total': True})

                # opex_line_items = self.env['crr.budget.line']
                opex_line_items = opex_total_line
                # for line in crr_line_ids.filtered(
                #         lambda line: not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line):
                #     if line.budget_type == 'opex':
                #         opex_line_items += line

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

                # out_flow_budget_lines = budget_lines.filtered(lambda b: b.budget_type in ['capex','opex'])
                # print('acccccccccccccccccccccc',acc_id.name)
                # print('out_flow_budget_lines',sum(out_flow_budget_lines.mapped('april_crr_budget_plan')))
                # total_cash_outflow_line.write({
                #     'april_crr_budget_plan': sum(out_flow_budget_lines.mapped('april_crr_budget_plan')),
                #     'may_crr_budget_plan': sum(out_flow_budget_lines.mapped('may_crr_budget_plan')),
                #     'june_crr_budget_plan': sum(out_flow_budget_lines.mapped('june_crr_budget_plan')),
                #     'july_crr_budget_plan': sum(out_flow_budget_lines.mapped('july_crr_budget_plan')),
                #     'august_crr_budget_plan': sum(out_flow_budget_lines.mapped('august_crr_budget_plan')),
                #     'september_crr_budget_plan': sum(out_flow_budget_lines.mapped('september_crr_budget_plan')),
                #     'october_crr_budget_plan': sum(out_flow_budget_lines.mapped('october_crr_budget_plan')),
                #     'november_crr_budget_plan': sum(out_flow_budget_lines.mapped('november_crr_budget_plan')),
                #     'december_crr_budget_plan': sum(out_flow_budget_lines.mapped('december_crr_budget_plan')),
                #     'january_crr_budget_plan': sum(out_flow_budget_lines.mapped('january_crr_budget_plan')),
                #     'febuary_crr_budget_plan': sum(out_flow_budget_lines.mapped('febuary_crr_budget_plan')),
                #     'march_crr_budget_plan': sum(out_flow_budget_lines.mapped('march_crr_budget_plan')),
                # })
                #
                # in_flow_budget_lines = budget_lines.filtered(lambda b: b.budget_type in ['ocif','noocif'])
                # print('in_flow_budget_lines',sum(in_flow_budget_lines.mapped('april_crr_budget_plan')))
                # total_cash_inflow_line.sudo().write({
                #     'april_crr_budget_plan': sum(in_flow_budget_lines.mapped('april_crr_budget_plan')),
                #     'may_crr_budget_plan': sum(in_flow_budget_lines.mapped('may_crr_budget_plan')),
                #     'june_crr_budget_plan': sum(in_flow_budget_lines.mapped('june_crr_budget_plan')),
                #     'july_crr_budget_plan': sum(in_flow_budget_lines.mapped('july_crr_budget_plan')),
                #     'august_crr_budget_plan': sum(in_flow_budget_lines.mapped('august_crr_budget_plan')),
                #     'september_crr_budget_plan': sum(in_flow_budget_lines.mapped('september_crr_budget_plan')),
                #     'october_crr_budget_plan': sum(in_flow_budget_lines.mapped('october_crr_budget_plan')),
                #     'november_crr_budget_plan': sum(in_flow_budget_lines.mapped('november_crr_budget_plan')),
                #     'december_crr_budget_plan': sum(in_flow_budget_lines.mapped('december_crr_budget_plan')),
                #     'january_crr_budget_plan': sum(in_flow_budget_lines.mapped('january_crr_budget_plan')),
                #     'febuary_crr_budget_plan': sum(in_flow_budget_lines.mapped('febuary_crr_budget_plan')),
                #     'march_crr_budget_plan': sum(in_flow_budget_lines.mapped('march_crr_budget_plan')),
                # })
                # print('in_flow_budget_lines2222222222222222',sum(in_flow_budget_lines.mapped('april_crr_budget_plan')))

                monthly_breakup_lines += opex_line_items + capex_line_items + total_cash_outflow_line + noocif_line_items + ocif_line_items + total_cash_inflow_line + total_surplus_deficit_line
                # print('in_flow_budget_lines3333333333333333',sum(in_flow_budget_lines.mapped('april_crr_budget_plan')))
                print(4444444444444444, total_cash_inflow_line.april_crr_budget_plan)

            seq = 1
            for breakup_line in monthly_breakup_lines:
                breakup_line.sequence = seq
                breakup_line.is_consolidated = True
                seq += 1

    # def get_cash_outflow_inflow_calculation(self):
    #     if self.user_type == 'non_odoo':
    #         crr_line_ids = self.cash_payment_ids.sudo().search([('budget_id', '=', self.id)]).ids
    #         seq = 1
    #         for outflow_type_id in self.cash_payment_ids.search(
    #                 [('budget_type', 'in', ('opex', 'capex')), ('budget_id', '=', self.id),
    #                  ('id', 'in', crr_line_ids)]):
    #             outflow_type_id.sequence = seq
    #             outflow_type_id.budget_name = outflow_type_id.budget_position_id.name
    #             seq += 1
    #         self.env['crr.budget.line'].create(
    #             {'budget_name': 'Total Cash Outflow', 'budget_id': self.id, 'is_budget_out_sum_line': True,
    #              'sequence': seq})
    #         seq += 1
    #         for inflow_type_id in self.cash_payment_ids.search(
    #                 [('budget_type', 'in', ('ocif', 'noocif')), ('budget_id', '=', self.id),
    #                  ('id', 'in', crr_line_ids)]):
    #             inflow_type_id.budget_name = inflow_type_id.budget_position_id.name
    #             inflow_type_id.sequence = seq
    #             seq += 1
    #         self.env['crr.budget.line'].create(
    #             {'budget_name': 'Total Cash Inflow', 'budget_id': self.id, 'is_budget_in_sum_line': True,
    #              'sequence': seq})
    #         seq += 1
    #         self.env['crr.budget.line'].create(
    #             {'budget_name': 'Surplus/ Deficit(IN-OUT)', 'budget_id': self.id, 'is_budget_surples_sum_line': True,
    #              'sequence': seq})
    #     elif self.user_type == 'odoo':
    #         # for item in self.cash_payment_ids:
    #         #     if not item.budget_name:
    #         #         item.budget_name = item.budget_position_id.name
    #         # acc_ids = self.cash_payment_ids.mapped('analytic_account_id')
    #         # print('acc_ids', acc_ids.mapped('name'))
    #         # #     seq = 1
    #         # monthly_breakup_lines = self.env['crr.budget.line']
    #         # for acc_id in acc_ids:
    #         #     print('acc_id', acc_id.name)
    #         #     crr_line_ids = self.cash_payment_ids.filtered(
    #         #         lambda c: c.analytic_account_id == acc_id)
    #         #     # [('analytic_account_id', '=', acc_id), ('budget_id', '=', self.id)]).ids
    #         #     # opex_domain = [('budget_name','=', 'Operational Expenditure(OPEX)'), ('budget_id','=',  self.id),
    #         #     #             ('is_buget_categ','=', True)]
    #         #     opex_total_line = crr_line_ids.filtered(
    #         #         lambda c: c.budget_name == 'Operational Expenditure(OPEX) Total' and c.is_budget_total)
    #         #     if not opex_total_line:
    #         #         opex_total_line = self.env['crr.budget.line'].create(
    #         #             {'budget_name': 'Operational Expenditure(OPEX) Total', 'analytic_account_id': acc_id.id,
    #         #              'budget_id': self.id,
    #         #              'is_budget_total': True})
    #         #
    #         #     # opex_line_items = self.env['crr.budget.line']
    #         #     opex_line_items = opex_total_line
    #         #     # for line in crr_line_ids.filtered(
    #         #     #         lambda line: not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line):
    #         #     #     if line.budget_type == 'opex':
    #         #     #         opex_line_items += line
    #         #
    #         #     capex_total_line = crr_line_ids.filtered(
    #         #         lambda c: c.budget_name == 'Capital Expenditure(CAPEX) Total' and c.is_budget_total)
    #         #     if not capex_total_line:
    #         #         capex_total_line = self.env['crr.budget.line'].create(
    #         #             {'budget_name': 'Capital Expenditure(CAPEX) Total', 'analytic_account_id': acc_id.id,
    #         #              'budget_id': self.id,
    #         #              'is_budget_total': True})
    #         #     capex_line_items = capex_total_line
    #         #     noocif_total_line = crr_line_ids.filtered(
    #         #         lambda c: c.budget_name == 'Non-Operating Cash-In-Flow (NOCIF) Total' and c.is_budget_total)
    #         #     if not noocif_total_line:
    #         #         noocif_total_line = self.env['crr.budget.line'].create(
    #         #             {'budget_name': 'Non-Operating Cash-In-Flow (NOCIF) Total', 'analytic_account_id': acc_id.id,
    #         #              'budget_id': self.id,
    #         #              'is_budget_total': True})
    #         #     noocif_line_items = noocif_total_line
    #         #     ocif_total_line = crr_line_ids.filtered(
    #         #         lambda c: c.budget_name == 'Operating Cash-In-Flow (OCIF) Total' and c.is_budget_total)
    #         #     if not ocif_total_line:
    #         #         ocif_total_line = self.env['crr.budget.line'].create(
    #         #             {'budget_name': 'Operating Cash-In-Flow (OCIF) Total', 'analytic_account_id': acc_id.id,
    #         #              'budget_id': self.id,
    #         #              'is_budget_total': True})
    #         #     ocif_line_items = ocif_total_line
    #         #     # ----------------------------------------------------------------- #
    #         #
    #         #     total_cash_outflow_line = crr_line_ids.filtered(
    #         #         lambda c: c.budget_name == 'Total Cash Outflow' and c.is_budget_out_sum_line)
    #         #     if not total_cash_outflow_line:
    #         #         total_cash_outflow_line = self.env['crr.budget.line'].create(
    #         #             {'budget_name': 'Total Cash Outflow', 'analytic_account_id': acc_id.id,
    #         #              'budget_id': self.id,
    #         #              'is_budget_out_sum_line': True})
    #         #     total_cash_inflow_line = crr_line_ids.filtered(
    #         #         lambda c: c.budget_name == 'Total Cash Inflow' and c.is_budget_in_sum_line)
    #         #     if not total_cash_inflow_line:
    #         #         total_cash_inflow_line = self.env['crr.budget.line'].create(
    #         #             {'budget_name': 'Total Cash Inflow', 'analytic_account_id': acc_id.id,
    #         #              'budget_id': self.id,
    #         #              'is_budget_in_sum_line': True})
    #         #
    #         #         ##################################################################
    #         #     total_surplus_deficit_line = crr_line_ids.filtered(
    #         #         lambda c: c.budget_name == 'Surplus/ Deficit(IN-OUT)' and c.is_budget_surples_sum_line)
    #         #     if not total_surplus_deficit_line:
    #         #         total_surplus_deficit_line = self.env['crr.budget.line'].create(
    #         #             {'budget_name': 'Surplus/ Deficit(IN-OUT)', 'analytic_account_id': acc_id.id,
    #         #              'budget_id': self.id,
    #         #              'is_budget_surples_sum_line': True})
    #         #     budget_lines = crr_line_ids.filtered(
    #         #         lambda
    #         #             line: not line.is_budget_total and not line.is_buget_categ and not line.is_actual_surples and not line.is_budget_out_sum_line and not line.is_budget_in_sum_line and not line.is_budget_surples_sum_line)
    #         #     for line in budget_lines.sorted(reverse=True):
    #         #         if line.budget_type == 'opex':
    #         #             opex_line_items = line + opex_line_items
    #         #             # opex_line_items += line
    #         #         if line.budget_type == 'capex':
    #         #             # capex_line_items += line
    #         #             capex_line_items = line + capex_line_items
    #         #         if line.budget_type == 'noocif':
    #         #             noocif_line_items = line + noocif_line_items
    #         #             # noocif_line_items += line
    #         #         if line.budget_type == 'ocif':
    #         #             # ocif_line_items += line
    #         #             ocif_line_items = line + ocif_line_items
    #         #
    #         #
    #         #     opex_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'opex')
    #         #     opex_total_line.write({
    #         #         'april_crr_budget_plan': sum(opex_budget_lines.mapped('april_crr_budget_plan')),
    #         #         'may_crr_budget_plan': sum(opex_budget_lines.mapped('may_crr_budget_plan')),
    #         #         'june_crr_budget_plan': sum(opex_budget_lines.mapped('june_crr_budget_plan')),
    #         #         'july_crr_budget_plan': sum(opex_budget_lines.mapped('july_crr_budget_plan')),
    #         #         'august_crr_budget_plan': sum(opex_budget_lines.mapped('august_crr_budget_plan')),
    #         #         'september_crr_budget_plan': sum(opex_budget_lines.mapped('september_crr_budget_plan')),
    #         #         'october_crr_budget_plan': sum(opex_budget_lines.mapped('october_crr_budget_plan')),
    #         #         'november_crr_budget_plan': sum(opex_budget_lines.mapped('november_crr_budget_plan')),
    #         #         'december_crr_budget_plan': sum(opex_budget_lines.mapped('december_crr_budget_plan')),
    #         #         'january_crr_budget_plan': sum(opex_budget_lines.mapped('january_crr_budget_plan')),
    #         #         'febuary_crr_budget_plan': sum(opex_budget_lines.mapped('febuary_crr_budget_plan')),
    #         #         'march_crr_budget_plan': sum(opex_budget_lines.mapped('march_crr_budget_plan')),
    #         #     })
    #         #
    #         #     capex_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'capex')
    #         #     capex_total_line.write({
    #         #         'april_crr_budget_plan': sum(capex_budget_lines.mapped('april_crr_budget_plan')),
    #         #         'may_crr_budget_plan': sum(capex_budget_lines.mapped('may_crr_budget_plan')),
    #         #         'june_crr_budget_plan': sum(capex_budget_lines.mapped('june_crr_budget_plan')),
    #         #         'july_crr_budget_plan': sum(capex_budget_lines.mapped('july_crr_budget_plan')),
    #         #         'august_crr_budget_plan': sum(capex_budget_lines.mapped('august_crr_budget_plan')),
    #         #         'september_crr_budget_plan': sum(capex_budget_lines.mapped('september_crr_budget_plan')),
    #         #         'october_crr_budget_plan': sum(capex_budget_lines.mapped('october_crr_budget_plan')),
    #         #         'november_crr_budget_plan': sum(capex_budget_lines.mapped('november_crr_budget_plan')),
    #         #         'december_crr_budget_plan': sum(capex_budget_lines.mapped('december_crr_budget_plan')),
    #         #         'january_crr_budget_plan': sum(capex_budget_lines.mapped('january_crr_budget_plan')),
    #         #         'febuary_crr_budget_plan': sum(capex_budget_lines.mapped('febuary_crr_budget_plan')),
    #         #         'march_crr_budget_plan': sum(capex_budget_lines.mapped('march_crr_budget_plan')),
    #         #     })
    #         #
    #         #     noocif_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'noocif')
    #         #     noocif_total_line.write({
    #         #         'april_crr_budget_plan': sum(noocif_budget_lines.mapped('april_crr_budget_plan')),
    #         #         'may_crr_budget_plan': sum(noocif_budget_lines.mapped('may_crr_budget_plan')),
    #         #         'june_crr_budget_plan': sum(noocif_budget_lines.mapped('june_crr_budget_plan')),
    #         #         'july_crr_budget_plan': sum(noocif_budget_lines.mapped('july_crr_budget_plan')),
    #         #         'august_crr_budget_plan': sum(noocif_budget_lines.mapped('august_crr_budget_plan')),
    #         #         'september_crr_budget_plan': sum(noocif_budget_lines.mapped('september_crr_budget_plan')),
    #         #         'october_crr_budget_plan': sum(noocif_budget_lines.mapped('october_crr_budget_plan')),
    #         #         'november_crr_budget_plan': sum(noocif_budget_lines.mapped('november_crr_budget_plan')),
    #         #         'december_crr_budget_plan': sum(noocif_budget_lines.mapped('december_crr_budget_plan')),
    #         #         'january_crr_budget_plan': sum(noocif_budget_lines.mapped('january_crr_budget_plan')),
    #         #         'febuary_crr_budget_plan': sum(noocif_budget_lines.mapped('febuary_crr_budget_plan')),
    #         #         'march_crr_budget_plan': sum(noocif_budget_lines.mapped('march_crr_budget_plan')),
    #         #     })
    #         #
    #         #     ocif_budget_lines = budget_lines.filtered(lambda b: b.budget_type == 'ocif')
    #         #     ocif_total_line.write({
    #         #         'april_crr_budget_plan': sum(ocif_budget_lines.mapped('april_crr_budget_plan')),
    #         #         'may_crr_budget_plan': sum(ocif_budget_lines.mapped('may_crr_budget_plan')),
    #         #         'june_crr_budget_plan': sum(ocif_budget_lines.mapped('june_crr_budget_plan')),
    #         #         'july_crr_budget_plan': sum(ocif_budget_lines.mapped('july_crr_budget_plan')),
    #         #         'august_crr_budget_plan': sum(ocif_budget_lines.mapped('august_crr_budget_plan')),
    #         #         'september_crr_budget_plan': sum(ocif_budget_lines.mapped('september_crr_budget_plan')),
    #         #         'october_crr_budget_plan': sum(ocif_budget_lines.mapped('october_crr_budget_plan')),
    #         #         'november_crr_budget_plan': sum(ocif_budget_lines.mapped('november_crr_budget_plan')),
    #         #         'december_crr_budget_plan': sum(ocif_budget_lines.mapped('december_crr_budget_plan')),
    #         #         'january_crr_budget_plan': sum(ocif_budget_lines.mapped('january_crr_budget_plan')),
    #         #         'febuary_crr_budget_plan': sum(ocif_budget_lines.mapped('febuary_crr_budget_plan')),
    #         #         'march_crr_budget_plan': sum(ocif_budget_lines.mapped('march_crr_budget_plan')),
    #         #     })
    #         #
    #         #     # out_flow_budget_lines = budget_lines.filtered(lambda b: b.budget_type in ['capex','opex'])
    #         #     # print('acccccccccccccccccccccc',acc_id.name)
    #         #     # print('out_flow_budget_lines',sum(out_flow_budget_lines.mapped('april_crr_budget_plan')))
    #         #     # total_cash_outflow_line.write({
    #         #     #     'april_crr_budget_plan': sum(out_flow_budget_lines.mapped('april_crr_budget_plan')),
    #         #     #     'may_crr_budget_plan': sum(out_flow_budget_lines.mapped('may_crr_budget_plan')),
    #         #     #     'june_crr_budget_plan': sum(out_flow_budget_lines.mapped('june_crr_budget_plan')),
    #         #     #     'july_crr_budget_plan': sum(out_flow_budget_lines.mapped('july_crr_budget_plan')),
    #         #     #     'august_crr_budget_plan': sum(out_flow_budget_lines.mapped('august_crr_budget_plan')),
    #         #     #     'september_crr_budget_plan': sum(out_flow_budget_lines.mapped('september_crr_budget_plan')),
    #         #     #     'october_crr_budget_plan': sum(out_flow_budget_lines.mapped('october_crr_budget_plan')),
    #         #     #     'november_crr_budget_plan': sum(out_flow_budget_lines.mapped('november_crr_budget_plan')),
    #         #     #     'december_crr_budget_plan': sum(out_flow_budget_lines.mapped('december_crr_budget_plan')),
    #         #     #     'january_crr_budget_plan': sum(out_flow_budget_lines.mapped('january_crr_budget_plan')),
    #         #     #     'febuary_crr_budget_plan': sum(out_flow_budget_lines.mapped('febuary_crr_budget_plan')),
    #         #     #     'march_crr_budget_plan': sum(out_flow_budget_lines.mapped('march_crr_budget_plan')),
    #         #     # })
    #         #     #
    #         #     # in_flow_budget_lines = budget_lines.filtered(lambda b: b.budget_type in ['ocif','noocif'])
    #         #     # print('in_flow_budget_lines',sum(in_flow_budget_lines.mapped('april_crr_budget_plan')))
    #         #     # total_cash_inflow_line.sudo().write({
    #         #     #     'april_crr_budget_plan': sum(in_flow_budget_lines.mapped('april_crr_budget_plan')),
    #         #     #     'may_crr_budget_plan': sum(in_flow_budget_lines.mapped('may_crr_budget_plan')),
    #         #     #     'june_crr_budget_plan': sum(in_flow_budget_lines.mapped('june_crr_budget_plan')),
    #         #     #     'july_crr_budget_plan': sum(in_flow_budget_lines.mapped('july_crr_budget_plan')),
    #         #     #     'august_crr_budget_plan': sum(in_flow_budget_lines.mapped('august_crr_budget_plan')),
    #         #     #     'september_crr_budget_plan': sum(in_flow_budget_lines.mapped('september_crr_budget_plan')),
    #         #     #     'october_crr_budget_plan': sum(in_flow_budget_lines.mapped('october_crr_budget_plan')),
    #         #     #     'november_crr_budget_plan': sum(in_flow_budget_lines.mapped('november_crr_budget_plan')),
    #         #     #     'december_crr_budget_plan': sum(in_flow_budget_lines.mapped('december_crr_budget_plan')),
    #         #     #     'january_crr_budget_plan': sum(in_flow_budget_lines.mapped('january_crr_budget_plan')),
    #         #     #     'febuary_crr_budget_plan': sum(in_flow_budget_lines.mapped('febuary_crr_budget_plan')),
    #         #     #     'march_crr_budget_plan': sum(in_flow_budget_lines.mapped('march_crr_budget_plan')),
    #         #     # })
    #         #     # print('in_flow_budget_lines2222222222222222',sum(in_flow_budget_lines.mapped('april_crr_budget_plan')))
    #         #
    #         #
    #         #     monthly_breakup_lines += opex_line_items + capex_line_items + total_cash_outflow_line + noocif_line_items + ocif_line_items + total_cash_inflow_line + total_surplus_deficit_line
    #         #     # print('in_flow_budget_lines3333333333333333',sum(in_flow_budget_lines.mapped('april_crr_budget_plan')))
    #         #     print(4444444444444444,total_cash_inflow_line.april_crr_budget_plan)
    #         #
    #         # seq = 1
    #         # for breakup_line in monthly_breakup_lines:
    #         #     breakup_line.sequence = seq
    #         #     breakup_line.is_consolidated = True
    #         #     seq += 1
    #         self.show_budget_sum = True
    #         self.consolidate_crr()
    #         return True
    #     #         # seq += 1
    #     #         for outflow_type_id in self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', 'opex'), ('budget_id', '=', self.id),
    #     #                  ('id', 'in', crr_line_ids)]):
    #     #             outflow_type_id.sequence = seq
    #     #             outflow_type_id.budget_name = outflow_type_id.budget_position_id.name
    #     #             seq += 1
    #     #         self.env['crr.budget.line'].create(
    #     #             {'budget_name': 'Operational Expenditure(OPEX) Total', 'budget_id': self.id,
    #     #              'sequence': seq, 'analytic_account_id': acc_id, 'is_budget_total': True, 'budget_type': 'opex'})
    #     #         seq += 1
    #     #         # self.env['crr.budget.line'].create(
    #     #         #     {'budget_name': 'Capital Expenditure(CAPEX)', 'budget_id': self.id,
    #     #         #      'sequence': seq,'is_buget_categ':True})
    #     #         # seq += 1
    #     #
    #     #         for outflow_type_id in self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', 'capex'), ('budget_id', '=', self.id),
    #     #                  ('id', 'in', crr_line_ids)]):
    #     #             outflow_type_id.sequence = seq
    #     #             outflow_type_id.budget_name = outflow_type_id.budget_position_id.name
    #     #             seq += 1
    #     #         self.env['crr.budget.line'].create(
    #     #             {'budget_name': 'Capital Expenditure(CAPEX) Total', 'budget_id': self.id,
    #     #              'sequence': seq, 'analytic_account_id': acc_id, 'is_budget_total': True, 'budget_type': 'capex'})
    #     #         seq += 1
    #     #         self.env['crr.budget.line'].create(
    #     #             {'budget_name': 'Total Cash Outflow', 'budget_id': self.id, 'is_budget_out_sum_line': True,
    #     #              'sequence': seq, 'analytic_account_id': acc_id})
    #     #         seq += 1
    #     #         # self.env['crr.budget.line'].create(
    #     #         #     {'budget_name': 'Non-Operating Cash-In-Flow (NOCIF)', 'budget_id': self.id,
    #     #         #      'sequence': seq,'is_buget_categ':True})
    #     #         # seq += 1
    #     #         for inflow_type_id in self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', 'noocif'), ('budget_id', '=', self.id),
    #     #                  ('id', 'in', crr_line_ids)]):
    #     #             inflow_type_id.budget_name = inflow_type_id.budget_position_id.name
    #     #             inflow_type_id.sequence = seq
    #     #             seq += 1
    #     #         self.env['crr.budget.line'].create(
    #     #             {'budget_name': 'Non-Operating Cash-In-Flow (NOCIF) Total', 'budget_id': self.id,
    #     #              'sequence': seq, 'analytic_account_id': acc_id, 'is_budget_total': True, 'budget_type': 'noocif'})
    #     #         seq += 1
    #     #         # self.env['crr.budget.line'].create(
    #     #         #     {'budget_name': 'Operating Cash-In-Flow (OCIF)', 'budget_id': self.id,
    #     #         #      'sequence': seq,'is_buget_categ':True})
    #     #         # seq += 1
    #     #         for inflow_type_id1 in self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', 'ocif'), ('budget_id', '=', self.id),
    #     #                  ('id', 'in', crr_line_ids)]):
    #     #             inflow_type_id1.budget_name = inflow_type_id1.budget_position_id.name
    #     #             inflow_type_id1.sequence = seq
    #     #             seq += 1
    #     #         self.env['crr.budget.line'].create(
    #     #             {'budget_name': 'Operating Cash-In-Flow (OCIF) Total', 'budget_id': self.id,
    #     #              'sequence': seq, 'analytic_account_id': acc_id, 'is_budget_total': True, 'budget_type': 'ocif'})
    #     #         seq += 1
    #     #         self.env['crr.budget.line'].create(
    #     #             {'budget_name': 'Total Cash Inflow', 'budget_id': self.id, 'is_budget_in_sum_line': True,
    #     #              'sequence': seq, 'analytic_account_id': acc_id})
    #     #         seq += 1
    #     #         self.env['crr.budget.line'].create({'budget_name': 'Surplus/ Deficit(IN-OUT)', 'budget_id': self.id,
    #     #                                             'is_budget_surples_sum_line': True, 'sequence': seq,
    #     #                                             'analytic_account_id': acc_id})
    #     #         seq += 1
    #     #     seq = 1
    #     #     for rec in self.env['account.budget.post'].search(
    #     #             [('budget_category', '=', 'consolidate'), ('budget_type', 'in', ('opex', 'capex'))],
    #     #             order='sequence asc'):
    #     #         self.env['crr.budget.line.consolidate'].create({
    #     #             'company_id': self.env.user.company_id.id,
    #     #             'budget_id': self.id,
    #     #             'budget_position_id': rec.id,
    #     #             'budget_type': rec.budget_type,
    #     #             'april_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'april_crr_budget_plan')),
    #     #             'may_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'may_crr_budget_plan')),
    #     #             'june_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'june_crr_budget_plan')),
    #     #             'july_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'july_crr_budget_plan')),
    #     #             'august_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'august_crr_budget_plan')),
    #     #             'september_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'september_crr_budget_plan')),
    #     #             'october_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'october_crr_budget_plan')),
    #     #             'november_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'november_crr_budget_plan')),
    #     #             'december_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'december_crr_budget_plan')),
    #     #             'january_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'january_crr_budget_plan')),
    #     #             'febuary_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'febuary_crr_budget_plan')),
    #     #             'march_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'march_crr_budget_plan')),
    #     #             'cash_type': 'cash_payment',
    #     #             'budget_name': rec.name,
    #     #             'sequence': seq,
    #     #         })
    #     #         seq += 1
    #     #     self.env['crr.budget.line.consolidate'].create(
    #     #         {'budget_name': 'Total Cash Outflow', 'budget_id': self.id, 'is_budget_out_sum_line': True,
    #     #          'sequence': seq})
    #     #     seq += 1
    #     #     for rec in self.env['account.budget.post'].search(
    #     #             [('budget_category', '=', 'consolidate'), ('budget_type', 'in', ('ocif', 'noocif'))],
    #     #             order='sequence asc'):
    #     #         self.env['crr.budget.line.consolidate'].create({
    #     #             'company_id': self.env.user.company_id.id,
    #     #             'budget_id': self.id,
    #     #             'budget_position_id': rec.id,
    #     #             'budget_type': rec.budget_type,
    #     #             'april_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'april_crr_budget_plan')),
    #     #             'may_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'may_crr_budget_plan')),
    #     #             'june_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'june_crr_budget_plan')),
    #     #             'july_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'july_crr_budget_plan')),
    #     #             'august_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'august_crr_budget_plan')),
    #     #             'september_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'september_crr_budget_plan')),
    #     #             'october_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'october_crr_budget_plan')),
    #     #             'november_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'november_crr_budget_plan')),
    #     #             'december_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'december_crr_budget_plan')),
    #     #             'january_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'january_crr_budget_plan')),
    #     #             'febuary_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'febuary_crr_budget_plan')),
    #     #             'march_crr_budget_plan': sum(self.cash_payment_ids.search(
    #     #                 [('budget_type', '=', rec.budget_type), ('budget_id', '=', self.id)]).mapped(
    #     #                 'march_crr_budget_plan')),
    #     #             'cash_type': 'cash_payment',
    #     #             'budget_name': rec.name,
    #     #             'sequence': seq,
    #     #         })
    #     #         seq += 1
    #     #     self.env['crr.budget.line.consolidate'].create(
    #     #         {'budget_name': 'Total Cash Inflow', 'budget_id': self.id, 'is_budget_in_sum_line': True,
    #     #          'sequence': seq, })
    #     #     seq += 1
    #     #     self.env['crr.budget.line.consolidate'].create(
    #     #         {'budget_name': 'Surplus/ Deficit(IN-OUT)', 'budget_id': self.id, 'is_budget_surples_sum_line': True,
    #     #          'sequence': seq})
    #     #     self.cash_payment_ids._compute_total_budget_value(self.id)
    #     # self.show_budget_sum = True
    #     # self.consolidate_crr()
    #     return True


class Crossoverbudgetlines(models.Model):
    _inherit = 'crossovered.budget.lines'

    def _compute_practical_amount(self):
        groups = defaultdict(lambda: defaultdict(set))  # {(model, fname): {(date_from, date_to): account_ids}}
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
                line.practical_amount = sum(
                    agg_general.get((model, fname, line.date_from, line.date_to), {}).get((account, general_account), 0)
                    for account in accounts
                    for general_account in general_accounts.ids
                )
            else:
                # line.practical_amount = sum(
                #     agg_analytic.get((model, fname, line.date_from, line.date_to), {}).get(account, 0)
                #     for account in accounts
                # )
                line.practical_amount = 0

    def unlink(self):
        for rec in self:
            if rec.crossovered_budget_id.is_budget_consolidate:
                raise UserError('You cannot able to delete Consolidated records')
        return super(Crossoverbudgetlines, self).unlink()

    def _compute_balance_amount(self):
        for rec in self:
            rec.balance_amount = rec.planned_amount - (abs(rec.practical_amount) + rec.reserved_amount)

    @api.depends('additional_amount')
    def _compute_is_edited(self):
        for rec in self:
            rec.under_revision = False
            if rec.crossovered_budget_id.state == 'revision':
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
        if vals.get('planned_amount'):
            message = _("Planned Amount has been Updated: from " + str(self.planned_amount) + ' to ' + str(
                vals.get('planned_amount')))
            if self.crossovered_budget_id:
                self.crossovered_budget_id.message_post(body=message)  # Logs message in parent Budget record
        if self.crossovered_budget_id.state == 'revision':
            if vals.get('additional_amount') or vals.get('general_budget_id') or vals.get(
                    'analytic_account_id') or vals.get('department_id') or vals.get('capex_opex') or vals.get(
                'date_from') or vals.get('date_to'):
                vals['under_revision'] = True
        return super(Crossoverbudgetlines, self).write(vals)

    @api.depends("crossovered_budget_id", "general_budget_id", "analytic_account_id", "budget_code")
    def _compute_line_name(self):
        # just in case someone opens the budget line in form view
        for record in self:
            computed_name = record.crossovered_budget_id.name
            if record.general_budget_id:
                computed_name += ' - ' + record.general_budget_id.name
            if record.analytic_account_id:
                computed_name += ' - ' + record.analytic_account_id.name
            if record.budget_code:
                computed_name += ' - ' + record.budget_code
            record.name = computed_name


class RevisionHistory(models.Model):
    _name = 'revision.history'
    _description = 'Revision History'

    name = fields.Char(string="Sequence", required=True, copy=False, default='/')
    budget_post_id = fields.Many2one('account.budget.post', string="Budgetary Position")
    budget_code = fields.Char(string="Budget Code")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    initial_allocate = fields.Float(string="Initial Allocation")
    additional_amount = fields.Float(string="Additional Amount")
    budget_id = fields.Many2one('crossovered.budget', string='Budget')
    revision_date = fields.Datetime(string='Revision Date')

    @api.model
    def create(self, vals):
        if 'name' not in vals or not vals.get('name'):
            vals['name'] = self.env['ir.sequence'].next_by_code('revision.history') or 'New'
        return super(RevisionHistory, self).create(vals)


class BudgetaryPosition(models.Model):
    _name = 'account.budget.post'
    _inherit = ['account.budget.post', 'mail.thread', 'mail.activity.mixin']

    name = fields.Char('Name', required=True, tracking=True)
    sequence = fields.Integer(string='Sequence', tracking=True)
    budget_type = fields.Selection([
        ('capex', 'Capex'),
        ('opex', 'Opex'),
        ('ocif', 'OCIF'),
        ('noocif', 'NOOCIF')
    ], 'Budget Type', index=True, tracking=True)

    budget_category = fields.Selection([('regular', 'Regular'),
                                        ('consolidate', 'Consolidate')], 'Category', tracking=True)
    state = fields.Selection([("locked", "Locked"),
                              ("unlocked", "Unlocked")], string='Status', default='unlocked', tracking=True)
    is_locked = fields.Integer(string='Is Lock')
    company_id = fields.Many2one('res.company', 'Company', required=True, copy=False,
                                 default=lambda self: self.env.company)

    def action_lock(self):
        for rec in self:
            rec.state = 'locked'

    def action_unlock(self):
        for rec in self:
            rec.state = 'unlocked'


class CrrBudgetLine(models.Model):
    _name = 'crr.budget.line'
    _description = 'Crr Budget Line'
    _order = 'sequence'

    def _compute_total_budget_value(self, budget_id):
        budget = self.env['crossovered.budget'].sudo().search([('id', '=', budget_id)])
        if budget.user_type == 'odoo':
            crr_lines = self.filtered(lambda rec: rec.budget_id in budget and not rec.is_budget_total)
            total1 = self.filtered(lambda rec: rec.budget_id in budget and rec.is_budget_total)
            for rec in total1:
                crr_filtered_lines = crr_lines.filtered(
                    lambda lines: lines.analytic_account_id == rec.analytic_account_id and lines.budget_type
                                  == rec.budget_type)
                rec.april_crr_budget_plan = sum(crr_filtered_lines.mapped('april_crr_budget_plan'))
                rec.may_crr_budget_plan = sum(crr_filtered_lines.mapped('may_crr_budget_plan'))
                rec.june_crr_budget_plan = sum(crr_filtered_lines.mapped('june_crr_budget_plan'))
                rec.july_crr_budget_plan = sum(crr_filtered_lines.mapped('july_crr_budget_plan'))
                rec.august_crr_budget_plan = sum(crr_filtered_lines.mapped('august_crr_budget_plan'))
                rec.september_crr_budget_plan = sum(crr_filtered_lines.mapped('september_crr_budget_plan'))
                rec.october_crr_budget_plan = sum(crr_filtered_lines.mapped('october_crr_budget_plan'))
                rec.november_crr_budget_plan = sum(crr_filtered_lines.mapped('november_crr_budget_plan'))
                rec.december_crr_budget_plan = sum(crr_filtered_lines.mapped('december_crr_budget_plan'))
                rec.january_crr_budget_plan = sum(crr_filtered_lines.mapped('january_crr_budget_plan'))
                rec.febuary_crr_budget_plan = sum(crr_filtered_lines.mapped('febuary_crr_budget_plan'))
                rec.march_crr_budget_plan = sum(crr_filtered_lines.mapped('march_crr_budget_plan'))

                print(rec.april_crr_budget_plan, 'utrere')

    @api.depends(
        'quarter_1_crr_budget_plan', 'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan',
        'quarter_4_crr_budget_plan',
        'april_crr_budget_plan', 'may_crr_budget_plan', 'june_crr_budget_plan', 'july_crr_budget_plan',
        'august_crr_budget_plan',
        'september_crr_budget_plan', 'october_crr_budget_plan', 'november_crr_budget_plan', 'december_crr_budget_plan',
        'january_crr_budget_plan', 'febuary_crr_budget_plan', 'march_crr_budget_plan'
    )
    def _compute_to_get_quarter_values(self):
        def compute_quarters(record):
            record.quarter_1_crr_budget_plan = record.april_crr_budget_plan + record.may_crr_budget_plan + record.june_crr_budget_plan
            record.quarter_1_cur_budget = record.april_cur_budget + record.may_cur_budget + record.june_cur_budget
            record.quarter_1_var_budget = record.quarter_1_crr_budget_plan - record.quarter_1_cur_budget
            record.quarter_2_crr_budget_plan = record.july_crr_budget_plan + record.august_crr_budget_plan + record.september_crr_budget_plan
            record.quarter_2_cur_budget = record.july_cur_budget + record.august_cur_budget + record.september_cur_budget
            record.quarter_2_var_budget = record.quarter_2_crr_budget_plan - record.quarter_2_cur_budget
            record.quarter_3_crr_budget_plan = record.october_crr_budget_plan + record.november_crr_budget_plan + record.december_crr_budget_plan
            record.quarter_3_cur_budget = record.october_cur_budget + record.november_cur_budget + record.december_cur_budget
            record.quarter_3_var_budget = record.quarter_3_crr_budget_plan - record.quarter_3_cur_budget
            record.quarter_4_crr_budget_plan = record.january_crr_budget_plan + record.febuary_crr_budget_plan + record.march_crr_budget_plan
            record.quarter_4_cur_budget = record.january_cur_budget + record.february_cur_budget + record.march_cur_budget
            record.quarter_4_var_budget = record.quarter_4_crr_budget_plan - record.quarter_4_cur_budget

        def sum_budget_fields(search_dom, fields):
            return {field: sum(self.env['crr.budget.line'].search(search_dom).mapped(field)) for field in fields}

        fields = [
            'april_crr_budget_plan', 'may_crr_budget_plan', 'june_crr_budget_plan', 'july_crr_budget_plan',
            'august_crr_budget_plan',
            'september_crr_budget_plan', 'october_crr_budget_plan', 'november_crr_budget_plan',
            'december_crr_budget_plan',
            'january_crr_budget_plan', 'febuary_crr_budget_plan', 'march_crr_budget_plan', 'quarter_1_crr_budget_plan',
            'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan', 'quarter_4_crr_budget_plan'
        ]

        for rec in self:
            compute_quarters(rec)  # Compute initial quarter values
            if rec.is_budget_out_sum_line or rec.is_budget_in_sum_line or rec.is_budget_surples_sum_line:
                if rec.is_budget_out_sum_line:
                    # search_dom = [('cash_type', '=', 'cash_payment'), ('budget_id', '=', rec.budget_id.id)]
                    search_dom = [('budget_type', 'in', ['capex', 'opex']), ('budget_id', '=', rec.budget_id.id)]
                elif rec.is_budget_in_sum_line:
                    search_dom = [('budget_type', 'in', ['ocif', 'noocif']), ('budget_id', '=', rec.budget_id.id)]
                    # search_dom = [('cash_type', '=', 'cash_receipt'), ('budget_id', '=', rec.budget_id.id)]
                elif rec.is_budget_surples_sum_line:
                    search_dom_in = [('is_budget_in_sum_line', '=', True), ('budget_id', '=', rec.budget_id.id),
                                     ('analytic_account_id', '=', rec.analytic_account_id.id)]
                    search_dom_out = [('is_budget_out_sum_line', '=', True), ('budget_id', '=', rec.budget_id.id),
                                      ('analytic_account_id', '=', rec.analytic_account_id.id)]

                    # Calculate surplus by subtracting outflows from inflows
                    surplus = sum_budget_fields(search_dom_in, fields)
                    outflows = sum_budget_fields(search_dom_out, fields)
                    for field in fields:
                        setattr(rec, field, surplus[field] - outflows[field])
                    continue

                if rec.analytic_account_id:
                    search_dom.append(('analytic_account_id', '=', rec.analytic_account_id.id))

                # Sum the values for the specified fields
                budget_sums = sum_budget_fields(search_dom, fields)
                for field, value in budget_sums.items():
                    setattr(rec, field, value)

    @api.depends('quarter_1_crr_budget_plan', 'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan',
                 'quarter_4_crr_budget_plan')
    def _compute_to_get_total(self):
        for rec in self:
            rec.crr_budget_total = rec.quarter_1_crr_budget_plan + rec.quarter_2_crr_budget_plan + rec.quarter_3_crr_budget_plan + rec.quarter_4_crr_budget_plan
            rec.cur_budget_total = rec.quarter_1_cur_budget + rec.quarter_2_cur_budget + rec.quarter_3_cur_budget + rec.quarter_4_cur_budget
            rec.var_budget_total = rec.quarter_1_var_budget + rec.quarter_2_var_budget + rec.quarter_3_var_budget + rec.quarter_4_var_budget


    @api.depends('april_crr_budget_plan',
                 'may_crr_budget_plan',
                 'june_crr_budget_plan',
                 'july_crr_budget_plan',
                 'august_crr_budget_plan',
                 'september_crr_budget_plan',
                 'october_crr_budget_plan',
                 'november_crr_budget_plan',
                 'december_crr_budget_plan',
                 'january_crr_budget_plan',
                 'febuary_crr_budget_plan',
                 'march_crr_budget_plan',)
    def _compute_cur(self):
        for rec in self:
            budget_lines = rec.sudo().search([])
            opex_total_line = budget_lines.search([('budget_name','=','Operational Expenditure(OPEX) Total'),('is_budget_total','=',True),('budget_id','=',self.budget_id.id)])
            capex_total_line = budget_lines.search([('budget_name', '=', 'Capital Expenditure(CAPEX) Total'),('is_budget_total','=',True),('budget_id','=',self.budget_id.id)])
            noocif_total_line = budget_lines.search([('budget_name', '=', 'Non-Operating Cash-In-Flow (NOCIF) Total'),('is_budget_total','=',True),('budget_id','=',self.budget_id.id)])
            ocif_total_line = budget_lines.search([('budget_name', '=', 'Operating Cash-In-Flow (OCIF) Total'),('is_budget_total','=',True),('budget_id','=',self.budget_id.id)])
            cash_inflow = budget_lines.search([('budget_name', '=', 'Total Cash Inflow'),('is_budget_in_sum_line','=',True),('budget_id','=',self.budget_id.id)])
            cash_outflow = budget_lines.search([('budget_name', '=', 'Total Cash Outflow'), ('is_budget_out_sum_line', '=', True),('budget_id','=',self.budget_id.id)])
            surples_sum_line = budget_lines.search([('budget_name', '=', 'Surplus/ Deficit(IN-OUT)'), ('is_budget_surples_sum_line', '=', True),('budget_id','=',self.budget_id.id)])
            opex_budget_lines = budget_lines.filtered(lambda b: b.budget_id.id == self.budget_id.id  and b.budget_type == 'opex' and not b.is_budget_total and not b.is_buget_categ and not b.is_actual_surples and not b.is_budget_out_sum_line and not b.is_budget_in_sum_line and not b.is_budget_surples_sum_line)
            opex_total_line.write({
                'april_cur_budget': sum(opex_budget_lines.mapped('april_cur_budget')),
                'may_cur_budget': sum(opex_budget_lines.mapped('may_cur_budget')),
                'june_cur_budget': sum(opex_budget_lines.mapped('june_cur_budget')),
                'july_cur_budget': sum(opex_budget_lines.mapped('july_cur_budget')),
                'august_cur_budget': sum(opex_budget_lines.mapped('august_cur_budget')),
                'september_cur_budget': sum(opex_budget_lines.mapped('september_cur_budget')),
                'october_cur_budget': sum(opex_budget_lines.mapped('october_cur_budget')),
                'november_cur_budget': sum(opex_budget_lines.mapped('november_cur_budget')),
                'december_cur_budget': sum(opex_budget_lines.mapped('december_cur_budget')),
                'january_cur_budget': sum(opex_budget_lines.mapped('january_cur_budget')),
                'february_cur_budget': sum(opex_budget_lines.mapped('february_cur_budget')),
                'march_cur_budget': sum(opex_budget_lines.mapped('march_cur_budget')),
            })
            capex_budget_lines = budget_lines.filtered(lambda b: b.budget_id.id == self.budget_id.id and b.budget_type == 'capex'and not b.is_budget_total and not b.is_buget_categ and not b.is_actual_surples and not b.is_budget_out_sum_line and not b.is_budget_in_sum_line and not b.is_budget_surples_sum_line)
            capex_total_line.write({
                'april_cur_budget': sum(capex_budget_lines.mapped('april_cur_budget')),
                'may_cur_budget': sum(capex_budget_lines.mapped('may_cur_budget')),
                'june_cur_budget': sum(capex_budget_lines.mapped('june_cur_budget')),
                'july_cur_budget': sum(capex_budget_lines.mapped('july_cur_budget')),
                'august_cur_budget': sum(capex_budget_lines.mapped('august_cur_budget')),
                'september_cur_budget': sum(capex_budget_lines.mapped('september_cur_budget')),
                'october_cur_budget': sum(capex_budget_lines.mapped('october_cur_budget')),
                'november_cur_budget': sum(capex_budget_lines.mapped('november_cur_budget')),
                'december_cur_budget': sum(capex_budget_lines.mapped('december_cur_budget')),
                'january_cur_budget': sum(capex_budget_lines.mapped('january_crr_budget_plan')),
                'february_cur_budget': sum(capex_budget_lines.mapped('february_cur_budget')),
                'march_cur_budget': sum(capex_budget_lines.mapped('march_cur_budget')),
            })
            cash_outflow.write({
                'april_cur_budget' : sum(opex_total_line.mapped('april_cur_budget')) + sum(capex_total_line.mapped('april_cur_budget')),
                'may_cur_budget':sum(opex_total_line.mapped('may_cur_budget')) + sum(capex_total_line.mapped('may_cur_budget')),
                'june_cur_budget': sum(opex_total_line.mapped('june_cur_budget')) + sum(capex_total_line.mapped('june_cur_budget')),
                'july_cur_budget': sum(opex_total_line.mapped('july_cur_budget')) + sum(capex_total_line.mapped('july_cur_budget')),
                'august_cur_budget': sum(opex_total_line.mapped('august_cur_budget')) + sum(capex_total_line.mapped('august_cur_budget')),
                'september_cur_budget':sum(opex_total_line.mapped('september_cur_budget')) + sum(capex_total_line.mapped('september_cur_budget')),
                'october_cur_budget': sum(opex_total_line.mapped('october_cur_budget')) + sum(capex_total_line.mapped('october_cur_budget')),
                'november_cur_budget': sum(opex_total_line.mapped('november_cur_budget')) + sum(capex_total_line.mapped('november_cur_budget')),
                'december_cur_budget': sum(opex_total_line.mapped('december_cur_budget')) + sum(capex_total_line.mapped('december_cur_budget')),
                'january_cur_budget': sum(opex_total_line.mapped('january_cur_budget')) + sum(capex_total_line.mapped('january_cur_budget')),
                'february_cur_budget':sum(opex_total_line.mapped('february_cur_budget')) + sum(capex_total_line.mapped('february_cur_budget')),
                'march_cur_budget': sum(opex_total_line.mapped('march_cur_budget')) + sum(capex_total_line.mapped('march_cur_budget')),
            })
            noocif_budget_lines = budget_lines.filtered(lambda b: b.budget_id.id == self.budget_id.id and b.budget_type == 'noocif'and not b.is_budget_total and not b.is_buget_categ and not b.is_actual_surples and not b.is_budget_out_sum_line and not b.is_budget_in_sum_line and not b.is_budget_surples_sum_line)
            noocif_total_line.write({
                'april_cur_budget': sum(noocif_budget_lines.mapped('april_cur_budget')),
                'may_cur_budget': sum(noocif_budget_lines.mapped('may_cur_budget')),
                'june_cur_budget': sum(noocif_budget_lines.mapped('june_cur_budget')),
                'july_cur_budget': sum(noocif_budget_lines.mapped('july_cur_budget')),
                'august_cur_budget': sum(noocif_budget_lines.mapped('august_cur_budget')),
                'september_cur_budget': sum(noocif_budget_lines.mapped('september_cur_budget')),
                'october_cur_budget': sum(noocif_budget_lines.mapped('october_cur_budget')),
                'november_cur_budget': sum(noocif_budget_lines.mapped('november_cur_budget')),
                'december_cur_budget': sum(noocif_budget_lines.mapped('december_cur_budget')),
                'january_cur_budget': sum(noocif_budget_lines.mapped('january_cur_budget')),
                'february_cur_budget': sum(noocif_budget_lines.mapped('february_cur_budget')),
                'march_cur_budget': sum(noocif_budget_lines.mapped('march_cur_budget')),
            })

            ocif_budget_lines = budget_lines.filtered(lambda b: b.budget_id.id == self.budget_id.id and b.budget_type == 'ocif'and not b.is_budget_total and not b.is_buget_categ and not b.is_actual_surples and not b.is_budget_out_sum_line and not b.is_budget_in_sum_line and not b.is_budget_surples_sum_line)
            ocif_total_line.write({
                'april_cur_budget': sum(ocif_budget_lines.mapped('april_cur_budget')),
                'may_cur_budget': sum(ocif_budget_lines.mapped('may_cur_budget')),
                'june_cur_budget': sum(ocif_budget_lines.mapped('june_cur_budget')),
                'july_cur_budget': sum(ocif_budget_lines.mapped('july_cur_budget')),
                'august_cur_budget': sum(ocif_budget_lines.mapped('august_cur_budget')),
                'september_cur_budget': sum(ocif_budget_lines.mapped('september_cur_budget')),
                'october_cur_budget': sum(ocif_budget_lines.mapped('october_cur_budget')),
                'november_cur_budget': sum(ocif_budget_lines.mapped('november_cur_budget')),
                'december_cur_budget': sum(ocif_budget_lines.mapped('december_cur_budget')),
                'january_cur_budget': sum(ocif_budget_lines.mapped('january_cur_budget')),
                'february_cur_budget': sum(ocif_budget_lines.mapped('february_cur_budget')),
                'march_cur_budget': sum(ocif_budget_lines.mapped('march_cur_budget')),
            })
            cash_inflow.write({
                'april_cur_budget': sum(ocif_total_line.mapped('april_cur_budget')) + sum(
                    noocif_total_line.mapped('april_cur_budget')),
                'may_cur_budget': sum(ocif_total_line.mapped('may_cur_budget')) + sum(
                    noocif_total_line.mapped('may_cur_budget')),
                'june_cur_budget': sum(ocif_total_line.mapped('june_cur_budget')) + sum(
                    noocif_total_line.mapped('june_cur_budget')),
                'july_cur_budget': sum(ocif_total_line.mapped('july_cur_budget')) + sum(
                    noocif_total_line.mapped('july_cur_budget')),
                'august_cur_budget': sum(ocif_total_line.mapped('august_cur_budget')) + sum(
                    noocif_total_line.mapped('august_cur_budget')),
                'september_cur_budget': sum(ocif_total_line.mapped('september_cur_budget')) + sum(
                    noocif_total_line.mapped('september_cur_budget')),
                'october_cur_budget': sum(ocif_total_line.mapped('october_cur_budget')) + sum(
                    noocif_total_line.mapped('october_cur_budget')),
                'november_cur_budget': sum(ocif_total_line.mapped('november_cur_budget')) + sum(
                    noocif_total_line.mapped('november_cur_budget')),
                'december_cur_budget': sum(ocif_total_line.mapped('december_cur_budget')) + sum(
                    noocif_total_line.mapped('december_cur_budget')),
                'january_cur_budget': sum(ocif_total_line.mapped('january_cur_budget')) + sum(
                    noocif_total_line.mapped('january_cur_budget')),
                'february_cur_budget': sum(ocif_total_line.mapped('february_cur_budget')) + sum(
                    noocif_total_line.mapped('february_cur_budget')),
                'march_cur_budget': sum(ocif_total_line.mapped('march_cur_budget')) + sum(
                    noocif_total_line.mapped('march_cur_budget')),
            })
            surples_sum_line.write({
                'april_cur_budget': sum(cash_inflow.mapped('april_cur_budget')) - sum(
                    cash_outflow.mapped('april_cur_budget')),
                'may_cur_budget': sum(cash_inflow.mapped('may_cur_budget')) - sum(
                    cash_outflow.mapped('may_cur_budget')),
                'june_cur_budget': sum(cash_inflow.mapped('june_cur_budget')) - sum(
                    cash_outflow.mapped('june_cur_budget')),
                'july_cur_budget': sum(cash_inflow.mapped('july_cur_budget')) - sum(
                    cash_outflow.mapped('july_cur_budget')),
                'august_cur_budget': sum(cash_inflow.mapped('august_cur_budget')) - sum(
                    cash_outflow.mapped('august_cur_budget')),
                'september_cur_budget': sum(cash_inflow.mapped('september_cur_budget')) - sum(
                    cash_outflow.mapped('september_cur_budget')),
                'october_cur_budget': sum(cash_inflow.mapped('october_cur_budget')) - sum(
                    cash_outflow.mapped('october_cur_budget')),
                'november_cur_budget': sum(cash_inflow.mapped('november_cur_budget')) - sum(
                    cash_outflow.mapped('november_cur_budget')),
                'december_cur_budget': sum(cash_inflow.mapped('december_cur_budget')) - sum(
                    cash_outflow.mapped('december_cur_budget')),
                'january_cur_budget': sum(cash_inflow.mapped('january_cur_budget')) - sum(
                    cash_outflow.mapped('january_cur_budget')),
                'february_cur_budget': sum(cash_inflow.mapped('february_cur_budget')) - sum(
                    cash_outflow.mapped('february_cur_budget')),
                'march_cur_budget': sum(cash_inflow.mapped('march_cur_budget')) - sum(
                    cash_outflow.mapped('march_cur_budget')),
            })

    show_budget_sum = fields.Boolean('Show budget Sum', related="budget_id.show_budget_sum", store=True)
    company_id = fields.Many2one('res.company', string="Company")
    department_id = fields.Many2one('hr.department', string='Department')

    budget_id = fields.Many2one('crossovered.budget', string="Budget", ondelete='cascade')
    revision_budget_id = fields.Many2one('crossovered.budget', string="Budget", ondelete='cascade')
    budget_department_id = fields.Many2one('budget.department', string="Budget Department", ondelete='cascade')
    budget_line_department_id = fields.Many2one('budget.department', string="Budget Department", ondelete='cascade')
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", related='budget_id.user_type',
                                 store=True)
    budget_position_id = fields.Many2one('account.budget.post', string="Budget \n Position")
    budget_type = fields.Selection([('capex', 'Capex'),
                                    ('opex', 'Opex'),
                                    ('ocif', 'OCIF'),
                                    ('noocif', 'NOOCIF')], store=True, compute='_compute_budget_type',
                                   string="Budget Type")
    april_crr_budget_plan = fields.Float(string="Apr")
    april_cur_budget = fields.Float(string="April Actual", compute="_compute_cur",store=True)
    april_var_budget = fields.Float(string="April Diff", compute='_compute_var', store=True)
    may_crr_budget_plan = fields.Float(string="May")
    may_cur_budget = fields.Float(string="May Actual",compute="_compute_cur",store=True)
    may_var_budget = fields.Float(string="May Diff", compute='_compute_var', store=True)
    june_crr_budget_plan = fields.Float(string="Jun")
    june_cur_budget = fields.Float(string="June Actual",compute="_compute_cur",store=True)
    june_var_budget = fields.Float(string="June Diff", compute='_compute_var', store=True)
    july_crr_budget_plan = fields.Float(string="Jul")
    july_cur_budget = fields.Float(string="July Actual",compute="_compute_cur",store=True)
    july_var_budget = fields.Float(string="July Diff", compute='_compute_var', store=True)
    august_crr_budget_plan = fields.Float(string="Aug")
    august_cur_budget = fields.Float(string="August Actual",compute="_compute_cur",store=True)
    august_var_budget = fields.Float(string="August Diff", compute='_compute_var', store=True)
    september_crr_budget_plan = fields.Float(string="Sep")
    september_cur_budget = fields.Float(string="September Actual",compute="_compute_cur",store=True)
    september_var_budget = fields.Float(string="September Diff", compute='_compute_var', store=True)
    october_crr_budget_plan = fields.Float(string="Oct")
    october_cur_budget = fields.Float(string="October Actual",compute="_compute_cur",store=True)
    october_var_budget = fields.Float(string="October Diff", compute='_compute_var', store=True)
    november_crr_budget_plan = fields.Float(string="Nov")
    november_cur_budget = fields.Float(string="November Actual",compute="_compute_cur",store=True)
    november_var_budget = fields.Float(string="November Diff", compute='_compute_var', store=True)
    december_crr_budget_plan = fields.Float(string="Dec")
    december_cur_budget = fields.Float(string="December Actual",compute="_compute_cur",store=True)
    december_var_budget = fields.Float(string="December Diff", compute='_compute_var', store=True)
    january_crr_budget_plan = fields.Float(string="Jan")
    january_cur_budget = fields.Float(string="January Actual",compute="_compute_cur",store=True)
    january_var_budget = fields.Float(string="January Diff", compute='_compute_var', store=True)
    febuary_crr_budget_plan = fields.Float(string="Feb")
    february_cur_budget = fields.Float(string="February Actual",compute="_compute_cur",store=True)
    february_var_budget = fields.Float(string="February Diff", compute='_compute_var', store=True)
    march_cur_budget = fields.Float(string="March Actual",compute="_compute_cur",store=True)
    march_var_budget = fields.Float(string="March Diff", compute='_compute_var', store=True)
    march_crr_budget_plan = fields.Float(string="Mar")
    quarter_1_crr_budget_plan = fields.Float('Q1', compute='_compute_to_get_quarter_values')
    quarter_1_cur_budget = fields.Float('Q1 CUR', compute='_compute_to_get_quarter_values')
    quarter_1_var_budget = fields.Float('Q1 VAR', compute='_compute_to_get_quarter_values')
    quarter_2_crr_budget_plan = fields.Float('Q2', compute='_compute_to_get_quarter_values')
    quarter_2_cur_budget = fields.Float('Q2 CUR', compute='_compute_to_get_quarter_values')
    quarter_2_var_budget = fields.Float('Q2 VAR', compute='_compute_to_get_quarter_values')
    quarter_3_crr_budget_plan = fields.Float('Q3', compute='_compute_to_get_quarter_values')
    quarter_3_cur_budget = fields.Float('Q3 CUR', compute='_compute_to_get_quarter_values')
    quarter_3_var_budget = fields.Float('Q3 VAR', compute='_compute_to_get_quarter_values')
    quarter_4_crr_budget_plan = fields.Float('Q4', compute='_compute_to_get_quarter_values')
    quarter_4_cur_budget = fields.Float('Q4 CUR', compute='_compute_to_get_quarter_values')
    quarter_4_var_budget = fields.Float('Q4 VAR', compute='_compute_to_get_quarter_values')
    crr_budget_total = fields.Float('Annual Total', compute='_compute_to_get_total')
    cur_budget_total = fields.Float('CUR Annual Total', compute='_compute_to_get_total')
    var_budget_total = fields.Float('VAR Annual Total', compute='_compute_to_get_total')
    cash_type = fields.Selection([('cash_payment', 'Cash Payment'),
                                  ('cash_receipt', 'Cash Receipt')], string="Cash Type")
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    budget_name = fields.Char('Budget Position')
    is_budget_out_sum_line = fields.Boolean('Is Budget Line', default=False)
    is_budget_in_sum_line = fields.Boolean('Is Budget Line', default=False)
    is_budget_surples_sum_line = fields.Boolean('Is Budget Line', default=False)
    is_actual_surples = fields.Boolean('Is Actual Surplus',default=False)
    is_budget_total = fields.Boolean('Is Budget Total',default=False)
    is_consolidated = fields.Boolean('Is Consolidated',default=False)
    is_buget_categ = fields.Boolean('Is Budget category',default=False)
    sequence = fields.Integer('SEQ')

    rf_freez_april_month = fields.Boolean("Freeze April", related='budget_id.rf_freez_april_month')
    rf_freez_may_month = fields.Boolean("Freeze May", related='budget_id.rf_freez_may_month')
    rf_freez_june_month = fields.Boolean("Freeze June", related='budget_id.rf_freez_june_month')
    rf_freez_july_month = fields.Boolean("Freeze July", related='budget_id.rf_freez_july_month')
    rf_freez_august_month = fields.Boolean("Freeze August", related='budget_id.rf_freez_august_month')
    rf_freez_september_month = fields.Boolean("Freeze September", related='budget_id.rf_freez_september_month')
    rf_freez_october_month = fields.Boolean("Freeze October", related='budget_id.rf_freez_october_month')
    rf_freez_november_month = fields.Boolean("Freeze November", related='budget_id.rf_freez_november_month')
    rf_freez_december_month = fields.Boolean("Freeze December", related='budget_id.rf_freez_december_month')
    rf_freez_january_month = fields.Boolean("Freeze January", related='budget_id.rf_freez_january_month')
    rf_freez_february_month = fields.Boolean("Freeze February", related='budget_id.rf_freez_february_month')
    rf_freez_march_month = fields.Boolean("Freeze March", related='budget_id.rf_freez_march_month')

    version = fields.Integer("Version", default=1, readonly=True, store=True, copy=False)
    version_name = fields.Char("Version", compute='_compute_version_name', store=True, copy=False)

    @api.depends('budget_id.state', 'budget_position_id', 'budget_position_id.budget_type')
    def _compute_budget_type(self):
        for rec in self:
            if rec.budget_position_id and rec.budget_id and rec.budget_id.state not in 'done':
                rec.budget_type = rec.budget_position_id.budget_type
            elif not rec.budget_id and rec.budget_department_id:
                rec.budget_type = rec.budget_position_id.budget_type

    @api.depends('version')
    def _compute_version_name(self):
        for record in self:
            record.version_name = 'Version ' + str(record.version)

    @api.depends('april_crr_budget_plan', 'april_cur_budget',
                 'may_crr_budget_plan', 'may_cur_budget',
                 'june_crr_budget_plan', 'june_cur_budget',
                 'july_crr_budget_plan', 'july_cur_budget',
                 'august_crr_budget_plan', 'august_cur_budget',
                 'september_crr_budget_plan', 'september_cur_budget',
                 'october_crr_budget_plan', 'october_cur_budget',
                 'november_crr_budget_plan', 'november_cur_budget',
                 'december_crr_budget_plan', 'december_cur_budget',
                 'january_crr_budget_plan', 'january_cur_budget',
                 'febuary_crr_budget_plan', 'february_cur_budget',
                 'march_crr_budget_plan', 'march_cur_budget')
    def _compute_var(self):
        for record in self:
            record.april_var_budget = abs(record.april_crr_budget_plan) - abs(record.april_cur_budget)
            record.may_var_budget = abs(record.may_crr_budget_plan) - abs(record.may_cur_budget)
            record.june_var_budget = abs(record.june_crr_budget_plan) - abs(record.june_cur_budget)
            record.july_var_budget = abs(record.july_crr_budget_plan) - abs(record.july_cur_budget)
            record.august_var_budget = abs(record.august_crr_budget_plan) - abs(record.august_cur_budget)
            record.september_var_budget = abs(record.september_crr_budget_plan) - abs(record.september_cur_budget)
            record.october_var_budget = abs(record.october_crr_budget_plan) - abs(record.october_cur_budget)
            record.november_var_budget = abs(record.november_crr_budget_plan) - abs(record.november_cur_budget)
            record.december_var_budget = abs(record.december_crr_budget_plan) - abs(record.december_cur_budget)
            record.january_var_budget = abs(record.january_crr_budget_plan) - abs(record.january_cur_budget)
            record.february_var_budget = abs(record.febuary_crr_budget_plan) - abs(record.february_cur_budget)
            record.march_var_budget = abs(record.march_crr_budget_plan) - abs(record.march_cur_budget)

    @api.onchange('budget_position_id')
    def _onchange_budget_position_id(self):
        for rec in self:
            rec.budget_name = rec.budget_position_id.name
            # rec.budget_type = rec.budget_position_id.budget_type if rec.budget_position_id.budget_type else ''

    @api.onchange('budget_type')
    def _onchange_budget_type(self):
        sequence_map = {
            'opex': 1,
            'capex': 2,
            'ocif': 4,
            'noocif': 5
        }
        for rec in self:
            if rec.user_type == 'non_odoo' and rec.budget_type in sequence_map:
                rec.sequence = sequence_map[rec.budget_type]


class CrrBudgetLineConsolidate(models.Model):
    _name = 'crr.budget.line.consolidate'
    _description = 'Crr Budget Line Consolidate'

    def update_cash_outflow_inflow_calculation(self):
        self._compute_to_get_quarter_values()

    @api.depends(
        'quarter_1_crr_budget_plan', 'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan',
        'quarter_4_crr_budget_plan',
        'april_crr_budget_plan', 'may_crr_budget_plan', 'june_crr_budget_plan', 'july_crr_budget_plan',
        'august_crr_budget_plan',
        'september_crr_budget_plan', 'october_crr_budget_plan', 'november_crr_budget_plan', 'december_crr_budget_plan',
        'january_crr_budget_plan', 'febuary_crr_budget_plan', 'march_crr_budget_plan'
    )
    def _compute_to_get_quarter_values(self):
        def _compute_crr_monthly_budget_plan(self):
            budget_types = ['opex', 'capex', 'ocif', 'noicf']

            # Define a mapping of field names for months
            field_mapping = {
                'april_crr_budget_plan': 'april_crr_budget_plan',
                'may_crr_budget_plan': 'may_crr_budget_plan',
                'june_crr_budget_plan': 'june_crr_budget_plan',
                'july_crr_budget_plan': 'july_crr_budget_plan',
                'august_crr_budget_plan': 'august_crr_budget_plan',
                'september_crr_budget_plan': 'september_crr_budget_plan',
                'october_crr_budget_plan': 'october_crr_budget_plan',
                'november_crr_budget_plan': 'november_crr_budget_plan',
                'december_crr_budget_plan': 'december_crr_budget_plan',
                'january_crr_budget_plan': 'january_crr_budget_plan',
                'febuary_crr_budget_plan': 'febuary_crr_budget_plan',  # Fixed typo
                'march_crr_budget_plan': 'march_crr_budget_plan',
            }
            crr_budget_lines1 = self.env['crr.budget.line'].sudo().search([
                ('budget_id', '=', self.budget_id.id),
                ('budget_type', '=', 'opex'),
                ('is_budget_total', '=', False)
            ])
            crr_budget_lines2 = self.env['crr.budget.line'].sudo().search([
                ('budget_id', '=', self.budget_id.id),
                ('budget_type', '=', 'capex'),
                ('is_budget_total', '=', False)
            ])
            crr_budget_lines3 = self.env['crr.budget.line'].sudo().search([
                ('budget_id', '=', self.budget_id.id),
                ('budget_type', '=', 'ocif'),
                ('is_budget_total', '=', False)
            ])
            crr_budget_lines4 = self.env['crr.budget.line'].sudo().search([
                ('budget_id', '=', self.budget_id.id),
                ('budget_type', '=', 'noocif'),
                ('is_budget_total', '=', False)
            ])
            opex_rec = self.env['crr.budget.line.consolidate'].sudo().search([('budget_id', '=', self.budget_id.id),
                                                                              ('budget_type', '=', 'opex')])
            capex_rec = self.env['crr.budget.line.consolidate'].sudo().search([('budget_id', '=', self.budget_id.id),
                                                                               ('budget_type', '=', 'capex')])
            ocif_rec = self.env['crr.budget.line.consolidate'].sudo().search([('budget_id', '=', self.budget_id.id),
                                                                              ('budget_type', '=', 'ocif')])
            nocif_rec = self.env['crr.budget.line.consolidate'].sudo().search([('budget_id', '=', self.budget_id.id),
                                                                               ('budget_type', '=', 'noocif')])

            if opex_rec:
                for field, mapped_field in field_mapping.items():
                    setattr(opex_rec, field, sum(crr_budget_lines1.mapped(mapped_field)))
            if capex_rec:
                for field, mapped_field in field_mapping.items():
                    setattr(capex_rec, field, sum(crr_budget_lines2.mapped(mapped_field)))
            if ocif_rec:
                for field, mapped_field in field_mapping.items():
                    setattr(ocif_rec, field, sum(crr_budget_lines3.mapped(mapped_field)))
            if nocif_rec:
                for field, mapped_field in field_mapping.items():
                    setattr(nocif_rec, field, sum(crr_budget_lines4.mapped(mapped_field)))

        def compute_quarters(record):
            _compute_crr_monthly_budget_plan(self)
            record.quarter_1_crr_budget_plan = record.april_crr_budget_plan + record.may_crr_budget_plan + record.june_crr_budget_plan
            record.quarter_2_crr_budget_plan = record.july_crr_budget_plan + record.august_crr_budget_plan + record.september_crr_budget_plan
            record.quarter_3_crr_budget_plan = record.october_crr_budget_plan + record.november_crr_budget_plan + record.december_crr_budget_plan
            record.quarter_4_crr_budget_plan = record.january_crr_budget_plan + record.febuary_crr_budget_plan + record.march_crr_budget_plan

        def sum_budget_fields(search_dom, fields):
            return {field: sum(self.env['crr.budget.line'].search(search_dom).mapped(field)) for field in fields}

        fields = [
            'april_crr_budget_plan', 'may_crr_budget_plan', 'june_crr_budget_plan', 'july_crr_budget_plan',
            'august_crr_budget_plan',
            'september_crr_budget_plan', 'october_crr_budget_plan', 'november_crr_budget_plan',
            'december_crr_budget_plan',
            'january_crr_budget_plan', 'febuary_crr_budget_plan', 'march_crr_budget_plan', 'quarter_1_crr_budget_plan',
            'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan', 'quarter_4_crr_budget_plan'
        ]

        for rec in self:
            compute_quarters(rec)  # Compute initial quarter values

            if rec.is_budget_out_sum_line or rec.is_budget_in_sum_line or rec.is_budget_surples_sum_line:
                if rec.is_budget_out_sum_line:
                    search_dom = [('budget_type', 'in', ['capex', 'opex']), ('budget_id', '=', rec.budget_id.id)]
                    # search_dom = [('cash_type', '=', 'cash_payment'), ('budget_id', '=', rec.budget_id.id)]
                elif rec.is_budget_in_sum_line:
                    search_dom = [('budget_type', 'in', ['ocif', 'noocif']), ('budget_id', '=', rec.budget_id.id)]
                    # search_dom = [('cash_type', '=', 'cash_receipt'), ('budget_id', '=', rec.budget_id.id)]
                elif rec.is_budget_surples_sum_line:
                    search_dom_in = [('is_budget_in_sum_line', '=', True), ('budget_id', '=', rec.budget_id.id)]
                    search_dom_out = [('is_budget_out_sum_line', '=', True), ('budget_id', '=', rec.budget_id.id)]

                    # Calculate surplus by subtracting outflows from inflows
                    surplus = sum_budget_fields(search_dom_in, fields)
                    outflows = sum_budget_fields(search_dom_out, fields)
                    for field in fields:
                        setattr(rec, field, surplus[field] - outflows[field])
                    continue

                if rec.analytic_account_id:
                    search_dom.append(('analytic_account_id', '=', rec.analytic_account_id.id))

                # Sum the values for the specified fields
                budget_sums = sum_budget_fields(search_dom, fields)
                for field, value in budget_sums.items():
                    setattr(rec, field, value)

    @api.depends('quarter_1_crr_budget_plan', 'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan',
                 'quarter_4_crr_budget_plan')
    def _compute_to_get_total(self):
        for rec in self:
            rec.crr_budget_total = rec.quarter_1_crr_budget_plan + rec.quarter_2_crr_budget_plan + rec.quarter_3_crr_budget_plan + rec.quarter_4_crr_budget_plan

    company_id = fields.Many2one('res.company', string="Company")
    budget_id = fields.Many2one('crossovered.budget', string="Budget", ondelete='cascade')
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", related='budget_id.user_type',
                                 store=True)
    user_type_con = fields.Selection([('odoo', 'Odoo User'),
                                      ('non_odoo', 'Non-Odoo User')], string="User Type")
    budget_position_id = fields.Many2one('account.budget.post', string="Budget \n Position")
    budget_type = fields.Selection([('capex', 'Capex'),
                                    ('opex', 'Opex'),
                                    ('ocif', 'OCIF'),
                                    ('noocif', 'NOOCIF')], string="Budget Type")
    april_crr_budget_plan = fields.Float(string="Apr")
    may_crr_budget_plan = fields.Float(string="May")
    june_crr_budget_plan = fields.Float(string="Jun")
    july_crr_budget_plan = fields.Float(string="Jul")
    august_crr_budget_plan = fields.Float(string="Aug")
    september_crr_budget_plan = fields.Float(string="Sep")
    october_crr_budget_plan = fields.Float(string="Oct")
    november_crr_budget_plan = fields.Float(string="Nov")
    december_crr_budget_plan = fields.Float(string="Dec")
    january_crr_budget_plan = fields.Float(string="Jan")
    febuary_crr_budget_plan = fields.Float(string="Feb")
    march_crr_budget_plan = fields.Float(string="Mar")
    cash_type = fields.Selection([('cash_payment', 'Cash Payment'),
                                  ('cash_receipt', 'Cash Receipt')], string="Cash Type")
    quarter_1_crr_budget_plan = fields.Float('Q1', compute='_compute_to_get_quarter_values')
    quarter_2_crr_budget_plan = fields.Float('Q2', compute='_compute_to_get_quarter_values')
    quarter_3_crr_budget_plan = fields.Float('Q3', compute='_compute_to_get_quarter_values')
    quarter_4_crr_budget_plan = fields.Float('Q4', compute='_compute_to_get_quarter_values')
    crr_budget_total = fields.Float('Total', compute='_compute_to_get_total')
    analytic_account_id = fields.Many2one('account.analytic.account', string="Analytic Account")
    budget_name = fields.Char('Budget Position')
    is_budget_out_sum_line = fields.Boolean('Is Budget Line', default=False)
    is_budget_in_sum_line = fields.Boolean('Is Budget Line', default=False)
    is_budget_surples_sum_line = fields.Boolean('Is Budget Line', default=False)
    is_actual_surples = fields.Boolean("Is Actual Surplus",default=False)
    sequence = fields.Integer('SEQ')

    @api.onchange('budget_position_id')
    def _onchange_budget_position_id(self):
        for rec in self:
            rec.budget_name = rec.budget_position_id.name
            rec.budget_type = rec.budget_position_id.budget_type if rec.budget_position_id.budget_type else ''

    @api.onchange('budget_type')
    def _onchange_budget_type(self):
        sequence_map = {
            'opex': 1,
            'capex': 2,
            'ocif': 4,
            'noocif': 5
        }
        for rec in self:
            if rec.user_type == 'non_odoo' and rec.budget_type in sequence_map:
                rec.sequence = sequence_map[rec.budget_type]


class CRRShareLines(models.Model):
    _name = "crr.share.line"
    _description = "Cash Share"

    entity = fields.Many2one('res.company', string='Entity')
    ref_company = fields.Char(string='Company')
    company_id = fields.Many2one('res.company', string='Company')
    budget_id = fields.Many2one('crossovered.budget', string="Budget", ondelete='cascade')
    revision_budget_id = fields.Many2one('crossovered.budget', string="Budget", ondelete='cascade')

    fund_id = fields.Many2one('fund.management', string='Fund')
    te_consolidate_id = fields.Many2one('te.consolidation', string='TE Consolidation')
    crr_consolidate_id = fields.Many2one('crr.budget.line.consolidate', string='Consolidate ID')
    crr_share_april = fields.Float(string="Apr")
    crr_share_may = fields.Float(string="May")
    crr_share_june = fields.Float(string="Jun")
    crr_share_july = fields.Float(string="Jul")
    crr_share_august = fields.Float(string="Aug")
    crr_share_september = fields.Float(string="Sep")
    crr_share_october = fields.Float(string="Oct")
    crr_share_november = fields.Float(string="Nov")
    crr_share_december = fields.Float(string="Dec")
    crr_share_january = fields.Float(string="Jan")
    crr_share_february = fields.Float(string="Feb")
    crr_share_march = fields.Float(string="Mar")
    crr_share_q1 = fields.Float(string="Q1", compute='_compute_to_get_quarter_values')
    crr_share_q2 = fields.Float(string="Q2", compute='_compute_to_get_quarter_values')
    crr_share_q3 = fields.Float(string="Q3", compute='_compute_to_get_quarter_values')
    crr_share_q4 = fields.Float(string="Q4", compute='_compute_to_get_quarter_values')

    version = fields.Integer("Version", readonly=True, store=True, copy=False)
    version_name = fields.Char("Version", compute='_compute_version_name', store=True, copy=False)
    tax_entity_percentage = fields.Float(string="Tax Entity %", copy=True, tracking=True)

    # share_rev_effective_from = fields.Char(string="Share Revision Effective From", default='April')
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
    ], string="Share Revision Effective from", default='april')

    revision_date = fields.Date(string="Revision Date")

    def action_open_overall_company_share(self):
        print(self.id,self.crr_consolidate_id,'gggggggggg')
        consolidate_ids = self.env['crr.budget.line.consolidate'].sudo().search([
            ('id', 'in', self.crr_consolidate_id.ids)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'CRR Line Items',
            'view_mode': 'tree',
            # 'view_id': view_id,
            'res_model': 'crr.budget.line.consolidate',
            'domain': [('id', 'in', consolidate_ids.ids)],
            # 'domain': [('id', 'in', self.crr_consolidate_id.id)],
        }


    @api.depends('version')
    def _compute_version_name(self):
        for record in self:
            record.version_name = 'Version ' + str(record.version)

    @api.depends('crr_share_q4', 'crr_share_q3', 'crr_share_q2', 'crr_share_q1', 'crr_share_march',
                 'crr_share_february', 'crr_share_january',
                 'crr_share_december', 'crr_share_november', 'crr_share_october', 'crr_share_september',
                 'crr_share_august', 'crr_share_july',
                 'crr_share_june', 'crr_share_may', 'crr_share_april')
    def _compute_to_get_quarter_values(self):

        def compute_quater(self):
            for rec in self:
                rec.crr_share_q1 = rec.crr_share_april + rec.crr_share_may + rec.crr_share_june
                rec.crr_share_q2 = rec.crr_share_july + rec.crr_share_august + rec.crr_share_september
                rec.crr_share_q3 = rec.crr_share_october + rec.crr_share_november + rec.crr_share_december
                rec.crr_share_q4 = rec.crr_share_january + rec.crr_share_february + rec.crr_share_march

        for rec in self:
            compute_quater(rec)

class CRROtherShareLines(models.Model):
    _name = "crr.other.share.line"
    _description = "Cash Other Share"

    ref_company = fields.Char(string='Company')
    te_consolidate_id = fields.Many2one('te.consolidation', string='Consolidate ID')
    crr_share_april = fields.Float(string="Apr")
    crr_share_may = fields.Float(string="May")
    crr_share_june = fields.Float(string="Jun")
    crr_share_july = fields.Float(string="Jul")
    crr_share_august = fields.Float(string="Aug")
    crr_share_september = fields.Float(string="Sep")
    crr_share_october = fields.Float(string="Oct")
    crr_share_november = fields.Float(string="Nov")
    crr_share_december = fields.Float(string="Dec")
    crr_share_january = fields.Float(string="Jan")
    crr_share_february = fields.Float(string="Feb")
    crr_share_march = fields.Float(string="Mar")
    crr_share_q1 = fields.Float(string="Q1")
    crr_share_q2 = fields.Float(string="Q2")
    crr_share_q3 = fields.Float(string="Q3")
    crr_share_q4 = fields.Float(string="Q4")

class ConfidentialAttachments(models.Model):
    _name = 'doc.attach'
    _description = 'Attachments'

    budget_id = fields.Many2one('crossovered.budget', string='Budget')
    doc_name = fields.Char(string='Description')
    doc_attach = fields.Binary(string='Attachments')
