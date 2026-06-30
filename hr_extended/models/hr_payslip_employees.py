# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from collections import Counter


class HrPayslipEmployeesInherit(models.TransientModel):
    _inherit = 'hr.payslip.employees'

    @api.onchange('department_id')
    def _onchange_structure_id(self):
        for wizard in self:
            if wizard.department_id:
                employees = self.env['hr.employee'].search([('department_id', 'child_of', wizard.department_id.id)])
            else:
                employees = self.env['hr.employee'].search([('company_id', '=', self.env.company.id)])

            if employees:
                struct_counts = Counter()

                for emp in employees:
                    contract = self.env['hr.contract'].search([
                        ('employee_id', '=', emp.id),
                        ('state', '=', 'open')
                    ], order='date_start desc', limit=1)

                    if contract and contract.structure_type_id.default_struct_id:
                        struct_counts[contract.structure_type_id.default_struct_id.id] += 1

                if struct_counts:
                    most_common_struct = struct_counts.most_common(1)[0][0]
                    wizard.structure_id = most_common_struct
                else:
                    wizard.structure_id = False
            else:
                wizard.structure_id = False
