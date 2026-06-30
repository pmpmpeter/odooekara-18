from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import calendar
from datetime import datetime
from datetime import date,datetime

class FundManagementCRR(models.Model):
    _name = "fund.management"
    _description = "Fund Requirement Report"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name")
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'),
                              ('inprogress', 'In Progress'),
                              ('done', 'Done')], string='', default='draft')
    # crr_share_line = fields.One2many('crr.share.line', 'fund_id', string='CRR Lines')
    cash_pool_line = fields.One2many('cash.pool.lines', 'fund_management_id', string='Cash Pool')
    cash_pool = fields.Many2many('cash.pool', string='Cash Pool')
    te_consolidate_id = fields.Many2one('te.consolidation', string="TE Consolidation", ondelete='cascade')
    is_share_updated = fields.Boolean('Is share Updated', default=False)
    version = fields.Integer("Version", default=1, readonly=True, store=True, copy=False)
    revision_date = fields.Datetime(string="Revision Date")

    @api.onchange('cash_pool_line')
    def _onchange_cash_pool_line(self):
        for record in self:
            for line in record.cash_pool_line:
                if line.cash_pool and line.cash_pool.current_balance <= 0:
                    raise ValidationError("The selected cash pool has a current balance of 0.")

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('fund.management')
        return super().create(vals_list)

    # @api.constrains('april_cash_pool','may_cash_pool','june_cash_pool','july_cash_pool','august_cash_pool','september_cash_pool',
    #               'october_cash_pool','november_cash_pool','december_cash_pool','january_cash_pool','febuary_cash_pool','march_cash_pool')
    @api.constrains('start_date', 'end_date')
    def _change_date_constrains(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise UserError('End Date Cannot be before Start Date.')

    def _action_revise(self):
        for rec in self:
            prev_version = rec.version
            version = rec.version + 1
            rec.cash_pool_line.sudo().write({
                'version': version,
                # 'revision_date': fields.Datetime.now(),
            })
            # pool_lines_history = self.env['crr.budget.line'].sudo().search(
            #     ['|', ('fund_management_id', 'in', rec.ids), ('rev_fund_management_id', 'in', rec.ids)])
            # sequence = len(pool_lines_history) + 1
            for line in rec.cash_pool_line:
                line.copy({
                    # 'sequence': sequence,
                    # 'revision_date': fields.Datetime.now(),
                    'fund_management_id': False,
                    'rev_fund_management_id': rec.id,
                    'version': prev_version,
                })
                # sequence += 1

            rec.sudo().write({
                'version': version,
                'revision_date': fields.Datetime.now(),
            })

    def _allocate_cash_pool(self):
        for rec in self:
            # rec._action_revise()
            rec.cash_pool_line.sudo().write({
                'revision_date': fields.Datetime.now(),
            })
            rec.state = 'done'
            if rec.te_consolidate_id:
                rec.te_consolidate_id.state = 'done'

    # @api.constrains('cash_pool_line')

    def reset_to_draft(self):
        for rec in self:
            print('hjjjsss')
            rec.write({'state':'draft'})
    

    def write(self, vals):
        for rec in self:
            print('hhhhhhhhh')
            res = super().write(vals)
            if rec.cash_pool_line:
                    cash_p = rec.cash_pool_line
                    pool = cash_p.mapped('cash_pool')
                    for p in pool:
                        total_amount = 0
                        for line in rec.cash_pool_line:
                            if line.cash_pool == p:
                                total_amount += abs(
                                    line.april_cash_pool + line.may_cash_pool + line.june_cash_pool + line.july_cash_pool + line.august_cash_pool + line.september_cash_pool +
                                    line.october_cash_pool + line.november_cash_pool + line.december_cash_pool + line.january_cash_pool + line.febuary_cash_pool + line.march_cash_pool)
                        if p.current_balance < total_amount:
                            raise ValidationError(
                                f"The cash pool '{p.name}' has a  balance of '{p.available_balance}'.\n"
                                f"Kindly Allocate fund within available balance."
                            )
                    print(cash_p,'hhhhhhhhhhhhhh')
        return res

    def action_draft(self):
        for rec in self:
            rec.state = 'draft'

    def action_update_share_lines(self):
        if not self.te_consolidate_id and not self.start_date or not self.end_date:
            raise UserError('kindly update Start and End date.')
        # share_ids = self.env['crr.share.line'].sudo().search([('budget_id.date_from','>=',self.start_date),('budget_id.date_to','<=',self.end_date),('entity','=',self.company_id.id),('budget_id.state','=','to approve')])
        if self.te_consolidate_id:
            share_ids = self.te_consolidate_id.sudo().crr_share_line_ids
            self.start_date = self.te_consolidate_id.start_date
            self.end_date = self.te_consolidate_id.end_date
        else:
            share_ids = self.env['crr.share.line'].sudo().search([('budget_id.date_from', '>=', self.start_date),
                                                                  ('budget_id.date_to', '<=', self.end_date),
                                                                  ('entity', '=', self.company_id.id),
                                                                  ('budget_id.state', '=', 'to approve')])

        self.crr_share_line = share_ids
        for rec in self.crr_share_line:
            if rec.sudo().budget_id.user_type == 'odoo':
                rec.ref_company = rec.sudo().budget_id.company_id.name
            elif rec.sudo().budget_id.user_type == 'non_odoo':
                rec.ref_company = rec.sudo().budget_id.partner_id.name
            # rec.fund_id = self.id
        self.is_share_updated = True
        self.state = 'inprogress'

    

    def action_open_cash_pool(self):
        self.ensure_one()
        
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cash Pool',
            'view_mode': 'tree',
            'view_id': self.env.ref('accounts_extended.cash_pool_tree_view_extend').id,
            'res_model': 'cash.pool.lines',
            'context': {'group_by': ['version_name']},
            'domain': ['|', ('fund_management_id', 'in', self.ids), ('rev_fund_management_id', 'in', self.ids)],
        }

   
    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('You can able to delete Draft records only')
        return super(FundManagementCRR, self).unlink()



class TeConsolidation(models.Model):
    _name = "te.consolidation"
    _description = "TE Consolidation"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", default=lambda self: _('New'))
    start_date = fields.Date(string="Start Date")
    end_date = fields.Date(string="End Date")
    revised_date = fields.Date(string="Last Revised Date")
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'),
                              ('inprogress', 'In Progress'),
                              ('done', 'Done')], string='', default='draft')
    crr_consolidate_ids = fields.One2many('te.consolidation.line', 'te_consolidate_id',
                                          string="Cash Outflow/Cash Inflow - Consolidate")
    crr_company_share = fields.One2many('crr.company.share', 'te_consolidate_id', string='Company Share')
    is_consolidate_updated = fields.Boolean(string='Is Consolidation Updated', default=False, copy=False)
    is_fund_management = fields.Boolean(string='Is Fund Management', default=False, copy=False)
    crr_other_share_line = fields.One2many('crr.other.share.line', 'te_consolidate_id', string='CRR Lines')
    crr_share_line_ids = fields.One2many('crr.share.line', 'te_consolidate_id', string='CRR Consolidation Lines')
    budget_contribution_line_ids = fields.One2many('budget.contribution.te.line', 'te_id', string='Budget Contribution')

    @api.constrains('start_date', 'end_date', 'company_id')
    def _check_date_range_overlap(self):
        for record in self:
            # Skip if dates are not set
            if not record.start_date or not record.end_date:
                continue

            # Check for overlapping date ranges in the same company
            overlapping = self.search([
                ('id', '!=', record.id),
                ('company_id', '=', record.company_id.id),
                ('start_date', '<=', record.end_date),
                ('end_date', '>=', record.start_date)
            ], limit=1)

            if overlapping:
                raise ValidationError(
                    "Date range cannot overlap with existing records for the same Entity!\nExisting Record: %s" % overlapping.name)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals['name'] = self.env['ir.sequence'].next_by_code('te.consolidation')
        return super().create(vals_list)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError('You can able to delete Draft records only.')
        return super(TeConsolidation, self).unlink()

    def action_revise(self):
        for rec in self:
            rec.state = 'inprogress'
            rec.revised_date = fields.Date.today()
            fund_id = self.env['fund.management'].sudo().search([('te_consolidate_id', '=', self.id)])
            fund_id._action_revise()
            fund_id.state = 'inprogress'

    @api.constrains('start_date', 'end_date')
    def _change_date_constrains(self):
        for rec in self:
            if rec.end_date and rec.start_date and rec.end_date < rec.start_date:
                raise UserError('End Date Cannot be before Start Date.')

   
    def action_open_budget_contribution(self):
        self.action_monthwise_budget_contribution()
        contribution_ids = self.env['budget.contribution.te.line'].search([('te_id','=',self.id)])
        if contribution_ids:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Budget Contribution',
                'view_mode': 'tree',
                'res_model': 'budget.contribution.te.line',
                'domain': [('id', 'in', contribution_ids.ids)],
                'context': {'group_by': ['company_id']},
            }

    def action_open_share_view(self):
        share_ids = self.env['crr.share.line'].sudo().search([('budget_id.date_from', '>=', self.start_date),
                                                              ('budget_id.date_to', '<=', self.end_date),
                                                              ('entity', '=', self.company_id.id),
                                                              ('budget_id.state', 'in', ['to approve', 'done'])])
        if share_ids:
            return {
                'type': 'ir.actions.act_window',
                'name': 'View Share',
                'view_mode': 'tree',
                'res_model': 'crr.share.line',
                'domain': [('id', 'in', share_ids.ids)],
                'context': {'group_by': ['ref_company']},
            }

    def action_create_fund_management(self):
        fund_id = self.env['fund.management'].sudo().search([('te_consolidate_id', '=', self.id)])
        if not fund_id:
            fund_id = self.env['fund.management'].create({
                'start_date': self.start_date,
                'end_date': self.end_date,
                'te_consolidate_id': self.id
            })
        fund_id.action_update_share_lines()
        fund_id.is_share_updated = True
        self.is_fund_management = True
        self.state = 'inprogress'
        return True

    def action_open_fund_management(self):
        self.ensure_one()
        fund_id = self.env['fund.management'].sudo().search([('te_consolidate_id', '=', self.id)])
        return {
            'type': 'ir.actions.act_window',
            'name': 'Fund Management',
            'view_mode': 'form',
            'view_id': self.env.ref('accounts_extended.view_fund_mangemnt_view').id,
            'res_model': 'fund.management',
            'context': {'create': False},
            'res_id': fund_id.id,  # Pass the fund record ID here
            'target': 'current',
        }

    def action_open_consolidation(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'CRR Consolidation',
            'view_mode': 'tree',
            'res_model': 'te.consolidation.line',
            'domain': [('id', 'in', self.crr_consolidate_ids.ids)],
            'context': {'group_by': ['user_type', 'requested_from']},
        }

    def action_monthwise_budget_contribution(self):
        """Generate report lines based on financial year and current date"""
        self.ensure_one()

        today = fields.Date.today()
        fy_start = date(today.year, 4, 1)
        if today.month < 4:  # Jan-Mar belongs to previous financial year
            fy_start = date(today.year - 1, 4, 1)


        # Clear old lines
        self.budget_contribution_line_ids.unlink()

        vals_list = []

        # Generate month list from FY start to current month
        months = []
        current = fy_start
        while current <= today:
            months.append((current.year, current.month))
            # next month
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        entity_ids = self.env['res.company.tax.entity'].sudo().search([('entity_id','=',self.company_id.id)])
        for entity in entity_ids:
            company = entity.company_id
            # budget_id = self.env['crossovered.budget'].sudo().search([('user_type','in',('odoo','non_odoo')),('company_id','=',company.id)
            #                                                       # ,('date_from','=',self.start_date),('date_to','=',self.end_date)
            #                                                    ],limit=1)
            for year, month in months:
                month_start = date(year, month, 1)
                month_end = date(year, month, calendar.monthrange(year, month)[1])

                # Budget
                budget_req = 0.0
                # line = budget_id.crr_share_ids.filtered(lambda l: l.entity.id == entity.entity_id.id)
                # if line:
                #     month_map = {
                #         1: "crr_share_january", 2: "crr_share_february", 3: "crr_share_march",
                #         4: "crr_share_april", 5: "crr_share_may", 6: "crr_share_june",
                #         7: "crr_share_july", 8: "crr_share_august", 9: "crr_share_september",
                #         10: "crr_share_october", 11: "crr_share_november", 12: "crr_share_december",
                #     }
                #     budget_req = getattr(line[0], month_map[month], 0.0)

                # Actual contribution from account.move.line
                actual = 0.0
                if entity.loan_account_id:
                    aml = self.env["account.move.line"].sudo().read_group(
                        domain=[
                            ("account_id", "=", entity.loan_account_id.id),
                            ("date", ">=", month_start),
                            ("date", "<=", month_end),
                            ("move_id.state", "=", "posted"),
                        ],
                        fields=["debit:sum", "credit:sum"],
                        groupby=[]
                    )
                    if aml:
                        actual = aml[0].get("credit", 0.0)

                # CRR Requirement from cash.requirement.report
                cash_recs = self.env['cash.requirement.report'].sudo().search([
                    ('budget_id', '=', budget_id.id),
                    ('state', '=', 'done'),
                    ('start_date', '>=', month_start),
                    ('end_date', '<=', month_end),
                ])
                crr_req = sum(cash_recs.mapped('total_fund_required')) * (entity.share / 100.0)

                diff = crr_req - actual
                diff_percent = (diff / crr_req * 100.0) if crr_req else 0.0

                vals_list.append({
                    "te_id": self.id,
                    "company_id": company.id,
                    "month": f"{date(year, month, 1):%b-%y}",
                    "budget_contribution": abs(budget_req),
                    "budget_percent": entity.share,
                    "crr_requirement": crr_req,
                    "crr_percent": entity.share,
                    "actual_contribution": actual,
                    "actual_percent": (actual / crr_req * 100.0) if crr_req else 0.0,
                    "diff": diff,
                    "diff_percent": diff_percent,
                })

        if vals_list:
            self.env["budget.contribution.te.line"].create(vals_list)


class TeConsolidationLine(models.Model):
    _name = 'te.consolidation.line'
    _description = 'Te Consolidation Line'

   

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):

        result = super(TeConsolidationLine, self).read_group(
            domain, fields, groupby, offset=offset, limit=limit, orderby=orderby, lazy=lazy
        )
        if groupby == ['user_type']:
            for res in result:
                user_type = res.get('user_type')
                if isinstance(user_type, (list, tuple)):
                    user_type_id = user_type[0]
                else:
                    user_type_id = user_type
                sub_domain = domain + [('user_type', '=', user_type_id),
                                       ('budget_name', '=', 'Surplus/ Deficit(IN-OUT)')]
                lines = self.search(sub_domain)
                updated_values = {}
                for f in fields:
                    if f in groupby or f == '__domain':
                        continue
                    updated_values[f] = 0.0

                for line in lines:
                    for f in updated_values:
                        val = getattr(line, f, 0.0)
                        if isinstance(val, (int, float)):
                            updated_values[f] += val
                for f in updated_values:
                    res[f] = updated_values[f]
        if groupby == ['requested_from'] or 'requested_from' in groupby:
            records = self.search(domain)
            surplus_lines = records.filtered(lambda r: r.budget_name == 'Surplus/ Deficit(IN-OUT)')
            surplus_map = {}
            for rec in surplus_lines:
                company_id = rec.requested_from
                if company_id not in surplus_map:
                    surplus_map[company_id] = {f: 0.0 for f in fields if f not in groupby and f != '__domain'}

                for f in surplus_map[company_id]:
                    val = getattr(rec, f, 0.0)
                    if isinstance(val, (int, float)):
                        surplus_map[company_id][f] += val
            for res in result:
                company_info = res.get('requested_from')
                if isinstance(company_info, (list, tuple)):
                    company_id = company_info[0]
                else:
                    company_id = company_info
                if company_id in surplus_map:
                    for f, val in surplus_map[company_id].items():
                        if f in res:
                            res[f] = val

        return result

    @api.depends('quarter_1_crr_budget_plan', 'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan',
                 'quarter_4_crr_budget_plan')
    def _compute_to_get_total(self):
        for rec in self:
            rec.crr_budget_total = rec.quarter_1_crr_budget_plan + rec.quarter_2_crr_budget_plan + rec.quarter_3_crr_budget_plan + rec.quarter_4_crr_budget_plan

    @api.depends(
        'quarter_1_crr_budget_plan', 'quarter_2_crr_budget_plan', 'quarter_3_crr_budget_plan',
        'quarter_4_crr_budget_plan',
        'april_crr_budget_plan', 'may_crr_budget_plan', 'june_crr_budget_plan', 'july_crr_budget_plan',
        'august_crr_budget_plan',
        'september_crr_budget_plan', 'october_crr_budget_plan', 'november_crr_budget_plan', 'december_crr_budget_plan',
        'january_crr_budget_plan', 'febuary_crr_budget_plan', 'march_crr_budget_plan'
    )
    def _compute_to_get_quarter_values(self):
        for record in self:
            record.quarter_1_crr_budget_plan = record.april_crr_budget_plan + record.may_crr_budget_plan + record.june_crr_budget_plan
            record.quarter_2_crr_budget_plan = record.july_crr_budget_plan + record.august_crr_budget_plan + record.september_crr_budget_plan
            record.quarter_3_crr_budget_plan = record.october_crr_budget_plan + record.november_crr_budget_plan + record.december_crr_budget_plan
            record.quarter_4_crr_budget_plan = record.january_crr_budget_plan + record.febuary_crr_budget_plan + record.march_crr_budget_plan

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    te_consolidate_id = fields.Many2one('te.consolidation', string="TE Consolidation", ondelete='cascade')
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type")
    budget_position_id = fields.Many2one('account.budget.post', string="Budget \n Position")
    budget_type = fields.Selection([('capex', 'Capex'),
                                    ('opex', 'Opex'),
                                    ('ocif', 'OCIF'),
                                    ('noocif', 'NOOCIF')], string="Budget Type")
    april_crr_budget_plan = fields.Float(string="Apr")
    requested_from = fields.Char(string='Requested By')
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
    budget_name = fields.Char('Budget Position')
    is_budget_sum_line = fields.Boolean('Is Budget Line', default=False)
    # is_budget_in_sum_line = fields.Boolean('Is Budget Line',default=False)
    # is_budget_surples_sum_line = fields.Boolean('Is Budget Line',default=False)
    # sequence = fields.Integer('SEQ')


class CRRCompanyShare(models.Model):
    _name = 'crr.company.share'
    _description = 'crr.company.share'

    partner_ref = fields.Char(string='Company')
    te_consolidate_id = fields.Many2one('te.consolidation', string="TE Consolidation", ondelete='cascade')
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
    quarter_1_crr_budget_plan = fields.Float('Q1')
    quarter_2_crr_budget_plan = fields.Float('Q2')
    quarter_3_crr_budget_plan = fields.Float('Q3')
    quarter_4_crr_budget_plan = fields.Float('Q4')



class BudgetContributionTELine(models.Model):
    _name = "budget.contribution.te.line"
    _description = "Budget Contribution TE Line"

    te_id = fields.Many2one("te.consolidation", ondelete="cascade")
    company_id = fields.Many2one("res.company", string="Company")
    month = fields.Char("Month")
    budget_contribution = fields.Float("Budget Contribution")
    budget_percent = fields.Float("% Budget Contribution")
    crr_requirement = fields.Float("CRR Requirement")
    crr_percent = fields.Float("CRR Requirement %")
    actual_contribution = fields.Float("Actual Contribution")
    actual_percent = fields.Float("% Actual Contribution")
    diff = fields.Float("Diff")
    diff_percent = fields.Float("Diff %")

