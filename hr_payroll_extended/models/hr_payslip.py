from odoo import models, fields, api, _
from datetime import datetime, date
import calendar

class HrPayslip(models.Model):
    _inherit = "hr.payslip"

    def generate_payslip(self):
        return self.env.ref('hr_payroll_extended.report_action_custom_payslip').report_action(self)

    def compute_ytd_value(self,emp):
            self.ensure_one()
            fiscal_year = self.env['account.fiscal.year'].sudo().search([
                ('company_id', '=', self.company_id.id),
                ('date_from', '<=', self.date_from),
                ('date_to', '>=', self.date_from)
            ], limit=1)
            if not fiscal_year:
                return 0
            fiscal_start = fiscal_year.date_from
            date_to = self.date_to
            payslips = self.env['hr.payslip'].sudo().search([
                ('employee_id', '=', emp.id),
                ('date_from', '>=', fiscal_start),
                ('date_to','<=',date_to)
            ])
            income_total = 0
            earnings_ytd = 0
            recoveries = 0
            for pay in payslips:
                if pay:
                    for income_totals in pay.line_ids:
                        if income_totals.salary_rule_id.code == 'INC-T':
                            income_total += income_totals.total
                        if income_totals.salary_rule_id.code == 'Other_earnings_through_payroll':
                            earnings_ytd += income_totals.total
                        if income_totals.salary_rule_id.code == 'Other_recoveries':
                            recoveries += income_totals.total
            months = {(p.date_from.year, p.date_from.month) for p in payslips}
            recoveries_of_advance = 0
            if self.contract_id.recovery_of_advances:
                if self.contract_id.recovery_from_date:
                    date_from = self.date_from
                    recovery_from = self.contract_id.recovery_from_date
                    # Calculate month difference
                    month_diff = (date_from.year - recovery_from.year) * 12 + (date_from.month - recovery_from.month)+1
                    # If in same month, count as 1
                    count_months = month_diff
                    recoveries_of_advance = (
                            sum(
                                line.total
                                for line in self.line_ids
                                if line.salary_rule_id.code == 'Recovery_of_advances'
                            ) * count_months
                    ) if count_months > 0 else 0
                else:
                    recoveries_of_advance = 0
            date = self.date_from
            year = date.year
            month = date.month
            lop_days=sum(self.worked_days_line_ids.filtered(
                lambda x: x.work_entry_type_id.external_code == 'LOP'
            ).mapped('number_of_days'))
            if lop_days:
                days_in_month = calendar.monthrange(year, month)[1] - lop_days
            else:
                days_in_month = calendar.monthrange(year, month)[1]

            return {
                'month_total': int(len(months)),
                'income_total': income_total,
                'ytd_april':earnings_ytd,
                'recoveries':recoveries,
                'recoveries_of_advance':recoveries_of_advance,
                'days_in_month':days_in_month,
            }

class HRSalaryRule(models.Model):
    _inherit = 'hr.salary.rule'

    appears_on_batch_report = fields.Boolean(string='Appears on Batch JV')

