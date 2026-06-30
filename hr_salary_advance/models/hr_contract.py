# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'

    job_level_id = fields.Many2one('hr.job.levels', string='Job Level', related='employee_id.job_level_id')
    salary_advance_eligible_amount = fields.Float(string='Eligible Amount', compute='compute_salary_advance_eligible_amount')
    salary_advance_availed_amount = fields.Float(string='Amount Availed', compute='compute_salary_advance_details')
    salary_advance_current_month = fields.Float(string='Amount Due(Current Month)', compute='compute_salary_advance_details')
    salary_advance_status = fields.Selection([('not_active', 'Not Active'), ('in_progress', 'In Progress'), ('closed', 'Closed')], string='Status', compute='compute_salary_advance_details')

    @api.depends('job_level_id', 'job_level_id.salary_advance_percentage', 'job_level_id.salary_advance_calculation_period', 'total_ctc_month')
    def compute_salary_advance_eligible_amount(self):
        for rec in self:
            rec.salary_advance_eligible_amount = 0
            if rec.job_level_id and rec.job_level_id.salary_advance_percentage > 0 and rec.job_level_id.salary_advance_calculation_period > 0:
                rec.salary_advance_eligible_amount = rec.job_level_id.salary_advance_percentage * (rec.total_ctc_month * rec.job_level_id.salary_advance_calculation_period)


    def compute_salary_advance_details(self):
        for rec in self:
            rec.salary_advance_availed_amount = 0
            rec.salary_advance_current_month = 0
            rec.salary_advance_status = 'not_active'
            salary_advance = self.env['hr.salary.advance'].sudo().search([('employee_id', '=', rec.employee_id.id), ('state', 'in', ['approved', 'in_progress'])])
            salary_advance_line = self.env['hr.salary.advance.line'].sudo().search([('salary_advance_id', 'in', salary_advance.ids), ('installment_date', '=', fields.Date.today().replace(day=1)), ('installment_state', '=', 'not_paid')])
            if salary_advance:
                rec.salary_advance_availed_amount = sum(salary_advance.mapped('approved_amount'))
                rec.salary_advance_status = 'in_progress'
            if salary_advance_line:
                rec.salary_advance_current_month = sum(salary_advance_line.mapped('installment_amount'))