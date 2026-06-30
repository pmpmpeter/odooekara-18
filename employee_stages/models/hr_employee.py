# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Gayathri v (odoo@cybrosys.com)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class HrEmployee(models.Model):
    """This is used to inherit the employee model"""
    _inherit = 'hr.employee'

    state = fields.Selection([('joined', 'Slap On'),
                              ('grounding', 'On Probation'),
                              ('test_period', 'Test Period'),
                              ('employment', 'Employment'),
                              ('notice_period', 'Notice Period'),
                              ('relieved', 'Resigned'),
                              ('terminate', 'Terminated')], string='Status',
                             default='joined',
                             track_visibility='always', copy=False,
                             help="Employee Stages.\nSlap On: "
                                  "Joined\nGrounding: Training\nTest period : "
                                  "Probation")
    stages_history_ids = fields.One2many('hr.employee.status.history',
                                         'employee_id', string='Stage History',
                                         help='It shows the duration and '
                                              'history of history stages')

    @api.model_create_multi
    def create(self, vals_list):
        """This is used to create the default stage as 'Slap On'"""
        result = super().create(vals_list)
        result.stages_history_ids.sudo().create({'start_date': fields.Date.today(),
                                                 'employee_id': result.id,
                                                 'state': 'joined'})
        return result

    def action_start_grounding(self):
        """This is used to create the ground stage on staging history"""
        self.ensure_one()

        if not self.work_email:
            raise UserError(_("Please fill the Work Email for the Employee"))
        if not self.department_id:
            raise UserError(_("Please select the Department for the Employee"))
        if not self.parent_id:
            raise UserError(_("Please select the Manager for the Employee"))

        employee_probation = self.env['employee.probation'].sudo().search(
            [('employee_id', '=', self.id)], limit=1
        )
        if employee_probation:
            self.write({'state': 'grounding'})
        else:
            vals = {
                'employee_id': self.id,
            }
            employee_probation = self.env['employee.probation'].sudo().create(vals)
            if not employee_probation:
                raise UserError(_("Failed to create the Employee Probation record."))

        self.state = 'grounding'
        self.stages_history_ids.sudo().create({'start_date': fields.Date.today(),
                                               'employee_id': self.id,
                                               'state': 'grounding'})
        user = self.env.user
        if user.has_group('emp_prob_extended.group_employee_probation_manager'):
            return {
                'name': _('Employee Probation'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'employee.probation',
                'view_id': self.env.ref('emp_prob_extended.employee_probation_form_view').id,
                'context': {
                    'default_employee_id': self.id,
                },
                'res_id': employee_probation.id,
            }

    def set_as_employee(self):
        """This is used to create the employee stage on staging history"""
        self.state = 'employment'
        stage_history_ids = self.stages_history_ids.search(
            [('employee_id', '=', self.id),
             ('state', '=', 'test_period')])
        if stage_history_ids:
            stage_history_ids.sudo().write({'end_date': fields.Date.today()})
        self.stages_history_ids.sudo().create({'start_date': fields.Date.today(),
                                               'employee_id': self.id,
                                               'state': 'employment'})

    def action_start_notice_period(self):
        """This is used to create the notice period stage on staging history"""
        self.state = 'notice_period'
        stage_history_ids = self.stages_history_ids.search(
            [('employee_id', '=', self.id),
             ('state', '=', 'employment')])
        if stage_history_ids:
            stage_history_ids.sudo().write({'end_date': fields.Date.today()})
        self.stages_history_ids.sudo().create({'start_date': fields.Date.today(),
                                               'employee_id': self.id,
                                               'state': 'notice_period'})

    def action_relived(self):
        """This is used to create the relived stage on staging history"""
        self.state = 'relieved'
        self.active = False
        stage_history_ids = self.stages_history_ids.search(
            [('employee_id', '=', self.id),
             ('state', '=',
              'notice_period')])
        if stage_history_ids:
            stage_history_ids.sudo().write({'end_date': fields.Date.today()})
        self.stages_history_ids.sudo().create({'end_date': fields.Date.today(),
                                               'employee_id': self.id,
                                               'state': 'relieved'})

    def action_start_test_period(self):
        """This is used to create the test period stage on staging history"""
        self.state = 'test_period'
        self.stages_history_ids.search([('employee_id', '=', self.id),
                                        ('state', '=',
                                         'grounding')]).sudo().write(
            {'end_date': fields.Date.today()})
        self.stages_history_ids.sudo().create({'start_date': fields.Date.today(),
                                               'employee_id': self.id,
                                               'state': 'test_period'})

    def action_terminate(self):
        """This is used to create the terminate stage on staging history"""
        self.state = 'terminate'
        self.active = False
        stage_history_ids = self.stages_history_ids.search(
            [('employee_id', '=', self.id),
             ('state', '=', 'employment')])
        if stage_history_ids:
            stage_history_ids.sudo().write({'end_date': fields.Date.today()})
        else:
            self.stages_history_ids.search([('employee_id', '=', self.id),
                                            ('state', '=',
                                             'grounding')]).sudo().write(
                {'end_date': fields.Date.today()})
        self.stages_history_ids.sudo().create({'end_date': fields.Date.today(),
                                               'employee_id': self.id,
                                               'state': 'terminate'})


class EmployeeStageHistory(models.Model):
    """This is used to show the employee stages history"""
    _name = 'hr.employee.status.history'
    _description = 'Status History'

    start_date = fields.Date(string='Start Date',
                             help="Start date of the status period")
    end_date = fields.Date(string='End Date',
                           help="End date of the status period")
    duration = fields.Integer(compute='_compute_get_duration',
                              string='Duration(days)',
                              help="Duration of the stage")
    state = fields.Selection([('joined', 'Slap On'),
                              ('grounding', 'On Probation'),
                              ('test_period', 'Test Period'),
                              ('employment', 'Employment'),
                              ('notice_period', 'Notice Period'),
                              ('relieved', 'Resigned'),
                              ('terminate', 'Terminated')], string='Stage')
    employee_id = fields.Many2one('hr.employee', help="Stage "
                                                      "of the employee",
                                  invisible=1, string="Employee")

    @api.depends('start_date', 'end_date')
    def _compute_get_duration(self):
        """This is used to calculate the duration for the stages"""
        for history in self:
            history.duration = 0
            if history.end_date and history.start_date:
                duration = fields.Date.from_string(
                    history.end_date) - fields.Date.from_string(history.start_date)
                history.duration = duration.days
