# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class HrSalaryAdvanceRejectWizard(models.TransientModel):
    _name = 'hr.salary.advance.reject.wizard'
    _description = 'Hr Salary Advance Reject Wizard'

    approval_history_id = fields.Many2one('hr.salary.advance.approval.history', 'Approval History')
    salary_advance_id = fields.Many2one('hr.salary.advance', 'Salary Advance')
    reject_reason = fields.Text(string='Reason')

    def action_reject(self):
        if not self.reject_reason:
            raise ValidationError('Enter the Reject Reason')
        if self.approval_history_id and self.salary_advance_id:
            self.approval_history_id.write({'reject_reason': self.reject_reason, 'rejected_user_id': self.env.user.id, 'rejected_date': fields.Datetime.now()})
            self.write({'state': 'reject'})