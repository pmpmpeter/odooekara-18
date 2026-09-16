from odoo import fields, models


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    encashment_count = fields.Integer(
        compute='_compute_encashment_count'
    )

    def _compute_encashment_count(self):
        for rec in self:
            rec.encashment_count = self.env[
                'leave.encashment'
            ].search_count([
                ('employee_id', '=', rec.id)
            ])

    def action_view_encashments(self):
        self.ensure_one()

        return {
            'type': 'ir.actions.act_window',
            'name': 'Leave Encashments',
            'res_model': 'leave.encashment',
            'view_mode': 'tree,form',
            'domain': [('employee_id', '=', self.id)],
            'context': {
                'default_employee_id': self.id
            }
        }