# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrJobLevels(models.Model):
    _inherit = 'hr.job.levels'

    salary_advance_percentage = fields.Float(string='Salary Advance(%)')
    salary_advance_calculation_period = fields.Float(string='Advance Amount Calculation Period (In Months)')
    eligibility_duration = fields.Integer(string='Eligibility(In Years)')
    repayment_tenure = fields.Integer(string='Repayment Tenure(In Months)')