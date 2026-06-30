# -- coding: utf-8 --
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2024-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author:  Anjhana A K (<https://www.cybrosys.com>)
#    You can modify it under the terms of the GNU AFFERO
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU AFFERO GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU AFFERO GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import models, fields


class HrEmployee(models.Model):
    """inherited the model to add some fields"""
    _inherit = 'hr.employee'

    insurance_percentage = fields.Float(string="Company Percentage ",
                                        help="Company insurance percentage")
    deduced_amount_per_month = fields.Float(string="Salary deduced per month",
                                            compute="get_deduced_amount",
                                            help="Amount that is deduced from "
                                                 "the salary per month")
    deduced_amount_per_year = fields.Float(string="Salary deduced per year",
                                           compute="get_deduced_amount",
                                           help="Amount that is deduced from "
                                                "the salary per year")
    insurance_ids = fields.One2many('hr.insurance',
                                    'employee_id',
                                    string="Insurance", help="Insurance",
                                    domain=[('state', '=', 'active')])

    employee_insurance_ids = fields.Many2many('hr.insurance',
                                              compute='_compute_employee_insurance',
                                              string='Employee Insurance ID', copy=False)
    employee_insurance_count = fields.Integer("Employee Insurance Count",
                                              compute='_compute_employee_insurance', default=0, copy=False)

    def _compute_employee_insurance(self):
        for record in self:
            domain = [('employee_id', '=', record.id)]
            employee_insurance_ids = self.env['hr.insurance'].sudo().search(domain)
            record.employee_insurance_ids = employee_insurance_ids
            record.employee_insurance_count = len(employee_insurance_ids)

    def action_get_employee_insurance(self):
        action = self.env.ref('hr_insurance.hr_insurance_action')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.employee_insurance_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.employee_insurance_ids.ids)) + "])]"
        elif len(self.employee_insurance_ids.ids) == 1:
            res = self.env.ref('hr_insurance.hr_insurance_view_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.employee_insurance_ids.ids and self.employee_insurance_ids.ids[0] or False
        return result

    def get_deduced_amount(self):
        """used to get deduced amount"""
        current_date = fields.date.today()
        for emp in self:
            ins_amount = 0
            for ins in emp.insurance_ids:
                if ins.date_from <= current_date:
                    if ins.date_to >= current_date:
                        if ins.policy_coverage == 'monthly':
                            ins_amount = ins_amount + (ins.amount*12)
                        else:
                            ins_amount = ins_amount + ins.amount
            emp.deduced_amount_per_year = ins_amount-((ins_amount*emp.insurance_percentage)/100)
            emp.deduced_amount_per_month = emp.deduced_amount_per_year/12
