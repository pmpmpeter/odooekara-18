from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_three60_performance_ids = fields.Many2many('threeperformance.review',
                                              compute='_compute_employee_three60_performance',
                                              string='Employee 360 Performance', copy=False)
    employee_three60_performance_count = fields.Integer("Employee 360 Performance",
                                              compute='_compute_employee_three60_performance', default=0, copy=False)

    def _compute_employee_three60_performance(self):
        for record in self:
            domain = [('employee_id', '=', record.id)]
            employee_three60_performance_ids = self.env['threeperformance.review'].sudo().search(domain)
            record.employee_three60_performance_ids = employee_three60_performance_ids
            record.employee_three60_performance_count = len(employee_three60_performance_ids)

    def action_get_employee_three60_performance(self):
        action = self.env.ref('hr_appraisal_extended.three60_performance_action')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.employee_three60_performance_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.employee_three60_performance_ids.ids)) + "])]"
        elif len(self.employee_three60_performance_ids.ids) == 1:
            res = self.env.ref('hr_appraisal_extended.three60_performance_view', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.employee_three60_performance_ids.ids and self.employee_three60_performance_ids.ids[0] or False
        return result