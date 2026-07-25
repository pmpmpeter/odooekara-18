from odoo import api, fields, models, _, Command
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
from collections import defaultdict



class CrrBudgetLine(models.Model):
    _name = 'crr.budget.line'
    _description = 'Crr Budget Line'
    _order = 'sequence'

    def _compute_total_budget_value(self, budget_id):
        budget = self.env['budget.analytic'].sudo().search([('id', '=', budget_id)])
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

    budget_id = fields.Many2one('budget.analytic', string="Budget", ondelete='cascade')
    revision_budget_id = fields.Many2one('budget.analytic', string="Budget", ondelete='cascade')
    budget_department_id = fields.Many2one('budget.department', string="Budget Department", ondelete='cascade')
    budget_line_department_id = fields.Many2one('budget.department', string="Budget Department", ondelete='cascade')
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", related='budget_id.user_type',
                                 store=True)
    budget_position_id = fields.Many2one('account.report.budget', string="Budget \n Position")
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
    budget_id = fields.Many2one('budget.analytic', string="Budget", ondelete='cascade')
    user_type = fields.Selection([('odoo', 'Odoo User'),
                                  ('non_odoo', 'Non-Odoo User')], string="User Type", related='budget_id.user_type',
                                 store=True)
    user_type_con = fields.Selection([('odoo', 'Odoo User'),
                                      ('non_odoo', 'Non-Odoo User')], string="User Type")
    budget_position_id = fields.Many2one('account.report.budget', string="Budget \n Position")
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
    budget_id = fields.Many2one('budget.analytic', string="Budget", ondelete='cascade')
    revision_budget_id = fields.Many2one('budget.analytic', string="Budget", ondelete='cascade')

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
            'view_mode': 'list',
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

    budget_id = fields.Many2one('budget.analytic', string='Budget')
    doc_name = fields.Char(string='Description')
    doc_attach = fields.Binary(string='Attachments')
