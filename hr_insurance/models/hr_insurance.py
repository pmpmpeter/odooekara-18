# -- coding: utf-8 --
###################################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2024-TODAY Cybrosys Technologies (<https://www.cybrosys.com>).
#    Author:  Anjhana A K(<https://www.cybrosys.com>)
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
from odoo import fields, models, api
from odoo.exceptions import UserError

class HrInsurance(models.Model):
    """created a new model for employee insurance"""
    _name = 'hr.insurance'
    _description = 'HR Insurance'
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Employee', domain="[('company_id', '=', company_id)]",
                                  required=True, help="Employee")
    policy_id = fields.Many2one('insurance.policy', domain="[('company_id', '=', company_id)]",
                                string='Policy', required=True, help="Policy")
    amount = fields.Float(string='Premium', required=True, help="Policy amount")
    sum_insured = fields.Float(string="Sum Insured", required=True,
                               help="Insured sum")
    policy_coverage = fields.Selection([('monthly', 'Monthly'),
                                        ('yearly', 'Yearly')],
                                       required=True, default='monthly',
                                       string='Policy Coverage',
                                       help="During of the policy")
    date_from = fields.Date(string='Date From',
                            default=fields.date.today(), readonly=True,
                            help="Start date")
    date_to = fields.Date(string='Date To', help="End date")
    state = fields.Selection([('active', 'Active'),
                              ('expired', 'Expired'), ],
                             default='active', string="Status",
                             compute='get_status')
    company_id = fields.Many2one('res.company', string='Company',
                                 required=True, help="Company",
                                 default=lambda self: self.env.company, readonly=True)
    is_manager = fields.Boolean(string="Is Manager",compute='_compute_is_manager', default=lambda self: self._default_is_manager(), store=False, copy=False)

    def _default_is_manager(self):
        user = self.env.user
        return user.has_group('hr.group_hr_user')

    @api.depends()
    def _compute_is_manager(self):
        for record in self:
            user = self.env.user
            if user.has_group('hr.group_hr_user'):
                record.is_manager = True
            else:
                record.is_manager = False

    def get_status(self):
        """this function is get and set state"""
        current_date = fields.date.today()
        for rec in self:
            if rec.policy_coverage == 'monthly':
                rec.date_to = fields.Date.end_of(self.date_from, 'month')
            if rec.policy_coverage == 'yearly':
                rec.date_to = fields.Date.end_of(self.date_from, 'year')
            if rec.date_from <= current_date:
                if rec.date_to and rec.date_to >= current_date:
                    rec.state = 'active'
                else:
                    rec.state = 'expired'

    def unlink(self):
        for record in self:
            if record.state == 'active':
                raise UserError("You can not delete the Active Policy record.")
        return super(HrInsurance, self).unlink()