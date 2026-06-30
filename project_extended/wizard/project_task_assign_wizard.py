# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProjectTaskAssignWizard(models.TransientModel):
    _name = 'project.task.assign.wizard'

    task_id = fields.Many2one('project.task', 'Project Task')
    assign_to_user_id = fields.Many2one('res.users', string='Assign To')
    assign_reason = fields.Text(string='Reason')

    def action_assign(self):
        if not self.assign_to_user_id:
            raise ValidationError("Select the Assign To")
        if not self.assign_reason:
            raise ValidationError("Enter the Assigning Reason")
        if self.assign_to_user_id.id in self.task_id.user_ids.ids:
            raise ValidationError(_("%s has already been assigned to this task") % self.assign_to_user_id.name)
        line_ids = self.task_id.task_assign_line_ids.filtered(lambda x: x.assign_state == 'in_progress')
        line_ids.update({'assign_state': 'done'})
        task_assign_vals = {
            'assigned_by_user_id': self.env.user.id,
            'assigned_user_id': self.assign_to_user_id.id,
            'assigned_reason': self.assign_reason,
            'assigned_date': fields.Datetime.now(),
            'assign_state':'draft',
        }
        self.task_id.write({'user_ids': [(4, self.assign_to_user_id.id)], 'task_assign_line_ids': [(0, 0, task_assign_vals)]})
        assigning_user_line = self.task_id.task_assign_line_ids.filtered(lambda x: x.assigned_user_id.id == self.env.user.id)
        if assigning_user_line:
            assigning_user_line[0].write({'completed_date': fields.Datetime.now(), 'assign_state': 'done'})
        self.task_id.task_accepted = False
