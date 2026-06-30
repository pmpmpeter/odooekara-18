from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

#reason for creating this class (renaming Payslips-> Payroll Input Sheet)
class HrPayslipRun(models.Model):
    _inherit = 'hr.payslip.run'

    def action_open_payslips(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.payslip",
            "views": [[False, "tree"], [False, "form"]],
            "domain": [['id', 'in', self.slip_ids.ids]],
            "context": {'default_payslip_run_id': self.id},
            "name": "Payroll Input Sheet",
        }