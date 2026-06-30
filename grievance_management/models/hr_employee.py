from odoo import models, fields, api, _


class EmployeeGR(models.Model):
    _inherit = 'hr.employee'

    employee_grievance_ids = fields.Many2many('grievance.management',
                                                   compute='_compute_employee_grievance',
                                                   string='Employee Grievance ID', copy=False)
    employee_grievance_count = fields.Integer("Employee Grievance Count",
                                                   compute='_compute_employee_grievance', default=0, copy=False)

    def _compute_employee_grievance(self):
        for record in self:
            domain = [('employee_id', '=', record.id)]
            employee_grievance_ids = self.env['grievance.management'].sudo().search(domain)
            record.employee_grievance_ids = employee_grievance_ids
            record.employee_grievance_count = len(employee_grievance_ids)

    def action_get_employee_grievance(self):
        action = self.env.ref('grievance_management.grievance_management_action')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.employee_grievance_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.employee_grievance_ids.ids)) + "])]"
        elif len(self.employee_grievance_ids.ids) == 1:
            res = self.env.ref('grievance_management.grievance_management_form_view', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.employee_grievance_ids.ids and self.employee_grievance_ids.ids[0] or False
        return result
