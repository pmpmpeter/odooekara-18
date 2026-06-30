from odoo import models, fields, api
from odoo.exceptions import UserError


class ManpowerBudgetWizard(models.TransientModel):
    _name = 'manpower.budget.wizard'
    _description = 'Manpower Budget Report Wizard'

    start_date = fields.Date(string="Start Date", required=True)
    end_date = fields.Date(string="End Date", required=True)

    def generate_report(self):
        if self.start_date > self.end_date:
            raise UserError("End Date must be greater than or equal to Start Date.")
        return self.env.ref('hr_extended.manpower_budget_report_action').report_action(self)
