from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from datetime import datetime,date,timedelta
import calendar


class CashRequirementReport(models.Model):
    _name = 'cash.requirement.report'
    _description = 'Cash Requirement Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name",readonly=1, copy=False)
    state = fields.Selection([
        ('draft', 'New'),
        ('to approve','To Approve'),
        ('done', 'Approved'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    requested_date = fields.Date(string="Request Date", readonly=True, tracking=True, copy=False, default=fields.Datetime.now)
    requested_by = fields.Many2one('res.users',string="Requested By", attachment=True, copy=False, default=lambda self: self.env.user)
    journal_bank  =fields.Many2many('account.journal',string='Bank',copy=False)
    cash_requirement_lines = fields.One2many('cash.requirement.lines','cash_req_id',string='Lines',copy=False)
    available_balance  =fields.Float(string='Available Amount Balance',copy=False,compute='compute_available_balance')
    company_id = fields.Many2one('res.company',string ='Company', default=lambda self: self.env.company)
    minimum_balance = fields.Float(string='Minimum Balance',copy=False)
    amount_total = fields.Float(string='Amount Total', copy=False)
    total_fund_required = fields.Float(string='Total Fund Required', copy=False)
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string='End Date')
    revision_reason = fields.Text(string="Revision Reasons", readonly=True, default="", copy=False)
    approval_document = fields.Many2one('multi.approval', string='Approval Record', copy=False)
    active = fields.Boolean(string='Active',default=True)
    contribution_ids = fields.One2many("budget.contribution", "report_id", string="Budget Contributions")
    ytd_contribution_ids = fields.One2many("ytd.budget.contribution", "report_id", string="Budget Contributions")
    # budget_id = fields.Many2one('crossovered.budget',string='Budget')
    has_statement_lines = fields.Boolean(string='Has Statement Lines',default=False)
    bank_balance_date = fields.Date(string='Bank Balance')
    x_review_result = fields.Char(string="Review Result")

    @api.depends('journal_bank','bank_balance_date')
    def compute_available_balance(self):
        for rec1 in self:
            if rec1.journal_bank:
                total_val = 0
                till_date = rec1.bank_balance_date
                for rec in rec1.journal_bank.ids:
                    bank_balance = 0
                    if rec:
                        journal = self.env['account.journal'].sudo().search([('id', '=', rec)])
                        query_result = journal._get_journal_dashboard_bank_running_balance_dated(till_date)
                        rec1.has_statement_lines, bank_balance = query_result.get(journal.id)
                        total_val += bank_balance
                    else:
                        rec1.available_balance = 0
                rec1.available_balance = total_val
            else:
                rec1.available_balance = 0

    def action_print_cash_requirement(self):
        """Return the report action to print the cash requirement report as PDF"""
        self.ensure_one()
        return self.env.ref('accounts_extended.report_action_cash_requirement').report_action(self)

    @api.model
    def default_get(self, fields):
        defaults = super().default_get(fields)

        today = date.today()
        start_date = today.replace(day=1)
        next_month = today.replace(day=28) + timedelta(days=4)
        end_date = next_month.replace(day=1) - timedelta(days=1)
        defaults.update({
            'start_date': start_date,
            'end_date': end_date,
        })

        return defaults

    # def action_open_crr_report_consolidation(self):
    #     self.ensure_one()
    #     action = {
    #         'type': 'ir.actions.act_window',
    #         'name': 'CRR Report',
    #         'view_mode': 'tree',
    #         'res_model': 'cash.requirement.lines',
    #         # 'context': {'group_by': ['version_name']},
    #     }
    #     return action

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('cash.requirement.report')
            vals['active']  =True
        return super().create(vals_list)

    def button_done(self):
        if self.requested_by:
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=f"Cash Requirement Request - {self.name} ",
                note=f"The record {self.name} has been marked as done. Please take action if needed.",
                user_id=self.requested_by.id,
            )
        self.state = 'done'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('You can able to delete Draft records only')
        return super(CashRequirementReport, self).unlink()

    def reset_to_draft(self):
        self.state = 'draft'
        self.x_has_request_approval = False
        self.x_review_result = ''

    def button_cancel(self):
        self.state = 'cancel'

    # @api.onchange('journal_bank')
    # def onchange_journal_bank_test(self):
    #     if self.journal_bank:
    #         closing_balance = 0
    #         query_result = self.env['account.journal'].sudo()._get_journal_dashboard_bank_running_balance()
    #         for journal in self.journal_bank:
    #             print(journal, 'ffffffffffffff')
    #             journal.has_statement_lines, journal.current_statement_balance = query_result.get(journal.id)
    #
    #         for rec in self.journal_bank:
    #             query = """
    #                         select sum(balance) as balance FROM account_move_line aml
    #                         join account_move am on am.id=aml.move_id
    #                         where am.state='posted' and aml.account_id=%s and aml.date <= %s and aml.company_id = %s
    #                         """
    #             params = tuple(rec.default_account_id.ids), datetime.today().strftime('%Y-%m-%d'), self.company_id.id
    #             data_get8 = self.env.cr.execute(query, params)
    #             lines8 = self.env.cr.dictfetchall()
    #             if (lines8[0].get('balance') != None):
    #                 closing_balance += lines8[0].get('balance') or 0
    #         for record in self:
    #             record.available_balance = closing_balance
    #             if self.available_balance > 0:
    #                 if self.amount_total - self.available_balance > 0:
    #                      print(round(self.amount_total - self.available_balance))
    #                      self.total_fund_required = round(self.amount_total - self.available_balance)
    #                 else:
    #                      self.total_fund_required = 0
    #             else:
    #                 self.total_fund_required = round(self.amount_total)

    @api.onchange('cash_requirement_lines','minimum_balance')
    def onchange_minimum_balance(self):
            total = 0
            min_bal =0
            for rec in self.cash_requirement_lines:
                total = total + rec.amount
            self.amount_total = total
            if self.minimum_balance:
                min_bal = self.minimum_balance
            self.amount_total = total + min_bal
            if self.available_balance > 0:
                if self.amount_total - self.available_balance > 0:
                    self.total_fund_required = round(self.amount_total - self.available_balance)
                else:
                    self.total_fund_required = 0
            else:
                self.total_fund_required = round(self.amount_total)

    def action_generate_contributions(self):
        """Generate budget.contribution and ytd.budget.contribution lines"""
        self.ensure_one()
        company = self.env.company  # current company

        # Clear old lines (optional to avoid duplicates)
        self.contribution_ids.unlink()
        self.ytd_contribution_ids.unlink()  # Assuming you have a One2many for YTD contributions

        vals_list = []
        ytd_vals_list = []

        start_date, end_date = self.start_date, self.end_date

        # Determine financial year start (April)
        fy_start = date(self.start_date.year, 4, 1)
        if self.start_date.month < 4:  # Jan-Mar belongs to previous financial year
            fy_start = date(self.start_date.year - 1, 4, 1)

        # Collect contributions for each tax entity
        for entity_line in self.company_id.tax_entity_ids:
            entity = entity_line.entity_id
            share = entity_line.share
            loan_account = entity_line.loan_account_id
            if not entity:
                continue

            # --- Monthly contribution ---
            budget_requirement = 0.0
            # if self.budget_id and self.start_date:
            #     month_number = self.start_date.month
            #     month_map = {
            #         1: "crr_share_january", 2: "crr_share_february", 3: "crr_share_march",
            #         4: "crr_share_april", 5: "crr_share_may", 6: "crr_share_june",
            #         7: "crr_share_july", 8: "crr_share_august", 9: "crr_share_september",
            #         10: "crr_share_october", 11: "crr_share_november", 12: "crr_share_december",
            #     }
            #     month_field = month_map.get(month_number)
            #     print(self.budget_id.crr_share_ids.mapped('entity'),"1111111111",entity)
            #     line = self.budget_id.crr_share_ids.filtered(lambda l: l.entity.id == entity.id)
            #     if line:
            #         budget_requirement = getattr(line[0], month_field, 0.0)

            actual_contribution = 0.0
            if loan_account:
                aml = self.env["account.move.line"].read_group(
                    domain=[
                        ("account_id", "=", loan_account.id),
                        ("date", ">=", start_date),
                        ("date", "<=", end_date),
                        ("move_id.state", "=", "posted"),
                    ],
                    fields=["debit:sum", "credit:sum"],
                    groupby=[]
                )
                if aml:
                    actual_contribution = aml[0].get("credit", 0.0)

            crr_requirement = (self.total_fund_required or 0.0) * (share / 100.0)

            vals_list.append({
                "report_id": self.id,
                "tax_entity_id": entity.id,
                "te_percentage": share,
                "budget_requirement": abs(budget_requirement),
                "crr_requirement": crr_requirement,
                "actual_contribution": actual_contribution,
            })

            # --- YTD contribution ---
            ytd_budget = 0.0
            # if self.budget_id:
            #     # Sum all months from April to current month
            #     month_fields = []
            #     month_fields = []

            #     # months Apr (4) → Dec (12) in same year
            #     if self.start_date.month >= 4:
            #         for m in range(4, self.start_date.month + 1):
            #             month_map = {
            #                 4: "crr_share_april", 5: "crr_share_may", 6: "crr_share_june",
            #                 7: "crr_share_july", 8: "crr_share_august", 9: "crr_share_september",
            #                 10: "crr_share_october", 11: "crr_share_november", 12: "crr_share_december",
            #             }
            #             month_fields.append(month_map[m])

            #     # months Jan (1) → Mar (3) of next year
            #     else:
            #         for m in range(4, 13):  # Apr–Dec last year
            #             month_map = {
            #                 4: "crr_share_april", 5: "crr_share_may", 6: "crr_share_june",
            #                 7: "crr_share_july", 8: "crr_share_august", 9: "crr_share_september",
            #                 10: "crr_share_october", 11: "crr_share_november", 12: "crr_share_december",
            #             }
            #             month_fields.append(month_map[m])
            #         month_map_jan_mar = {1: "crr_share_january", 2: "crr_share_february", 3: "crr_share_march"}
            #         month_fields += [month_map_jan_mar[m] for m in range(1, self.start_date.month + 1)]

            #     line = self.budget_id.crr_share_ids.filtered(lambda l: l.entity.id == entity.id)
            #     if line:
            #         ytd_budget = sum(getattr(line[0], f, 0.0) for f in month_fields)

            # YTD actual contribution
            ytd_actual = 0.0
            if loan_account:
                aml = self.env["account.move.line"].read_group(
                    domain=[
                        ("account_id", "=", loan_account.id),
                        ("date", ">=", fy_start),
                        ("date", "<=", end_date),
                        ("move_id.state", "=", "posted"),
                    ],
                    fields=["debit:sum", "credit:sum"],
                    groupby=[]
                )
                if aml:
                    ytd_actual = aml[0].get("credit", 0.0)
            # Get all cash.requirement records linked to this budget, in 'done' state, and within FY start to end_date
            cash_recs = self.env['cash.requirement.report'].search([
                ('state', '=', 'done'),
                ('start_date', '>=', fy_start),
                ('end_date', '<=', end_date),
            ])
            ytd_crr = (sum(cash_recs.mapped('total_fund_required')) or 0.0) * (share / 100.0)
            ytd_vals_list.append({
                "report_id": self.id,
                "tax_entity_id": entity.id,
                "te_percentage": share,
                "budget_requirement": abs(ytd_budget),
                "crr_requirement": ytd_crr,
                "actual_contribution": ytd_actual,
            })
        if vals_list:
            self.env["budget.contribution"].create(vals_list)
        if ytd_vals_list:
            self.env["ytd.budget.contribution"].create(ytd_vals_list)


class CashRequirementLines(models.Model):
    _name = 'cash.requirement.lines'
    _description = 'Cash Requirement Lines'

    cash_req_id = fields.Many2one('cash.requirement.report', string='Cash Requirement')
    cash_account = fields.Many2one('account.account',string='Account', copy=False)
    partner_id = fields.Many2one('res.partner',string='Partner' ,copy=False)
    requirement_month = fields.Date(string='Date',copy=False, default=fields.Datetime.now)
    requirement_months = fields.Selection(
        selection=[('01', 'January'), ('02', 'February'), ('03', 'March'),
                   ('04', 'April'), ('05', 'May'), ('06', 'June'),
                   ('07', 'July'), ('08', 'August'), ('09', 'September'),
                   ('10', 'October'), ('11', 'November'), ('12', 'December')],
        string="Month",
    )
    amount = fields.Float('Amount', copy=False, tracking=True)
    remarks = fields.Char('Remarks')
    company_id = fields.Many2one('res.company',string ='Company', related='cash_req_id.company_id', store=True)


class BudgetContribution(models.Model):
    _name = "budget.contribution"
    _description = "Budget Vs Actual Contribution"

    report_id = fields.Many2one(
        "cash.requirement.report", string="Cash Requirement Report", ondelete="cascade"
    )

    tax_entity_id = fields.Many2one("res.company", string="Tax Entity", required=True)
    te_percentage = fields.Float("TE %")
    budget_requirement = fields.Float("Budget Requirement")
    crr_requirement = fields.Float("CRR Requirement")
    actual_contribution = fields.Float("Actual Contribution")
    contribution_percent = fields.Float("Contribution %",compute='_compute_difference')

    difference = fields.Float(
        "Difference",
        compute="_compute_difference",
        store=True,
    )
    difference_percent = fields.Float(
        "Difference %",
        compute="_compute_difference",
        store=True,
    )

    @api.depends("crr_requirement", "actual_contribution")
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.crr_requirement - rec.actual_contribution
            rec.difference_percent = (
                (rec.difference / rec.crr_requirement * 100)
                if rec.crr_requirement
                else 0.0
            )
            rec.contribution_percent = (
                (rec.actual_contribution / rec.crr_requirement * 100)
                if rec.actual_contribution
                else 0.0
            )

class YTDBudgetContribution(models.Model):
    _name = "ytd.budget.contribution"
    _description = "YTD Budget Vs Actual Contribution"

    report_id = fields.Many2one(
        "cash.requirement.report", string="Cash Requirement Report", ondelete="cascade"
    )

    tax_entity_id = fields.Many2one("res.company", string="Tax Entity", required=True)
    te_percentage = fields.Float("TE %")
    budget_requirement = fields.Float("Budget Requirement")
    crr_requirement = fields.Float("CRR Requirement")
    actual_contribution = fields.Float("Actual Contribution")
    contribution_percent = fields.Float("Contribution %",compute='_compute_difference')

    difference = fields.Float(
        "Difference",
        compute="_compute_difference",
        store=True,
    )
    difference_percent = fields.Float(
        "Difference %",
        compute="_compute_difference",
        store=True,
    )

    @api.depends("crr_requirement", "actual_contribution")
    def _compute_difference(self):
        for rec in self:
            rec.difference = rec.crr_requirement - rec.actual_contribution
            rec.difference_percent = (
                (rec.difference / rec.crr_requirement * 100)
                if rec.crr_requirement
                else 0.0
            )
            rec.contribution_percent = (
                (rec.actual_contribution / rec.crr_requirement * 100)
                if rec.actual_contribution
                else 0.0
            )
