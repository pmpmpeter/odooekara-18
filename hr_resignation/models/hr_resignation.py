# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
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
from datetime import timedelta
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

date_format = "%Y-%m-%d"
RESIGNATION_TYPE = [('resigned', 'Normal Separation'),
                    ('fired', 'Fired by the company')]


class HrResignation(models.Model):
    """
     Model for HR Resignations.
     This model is used to track employee resignations.
    """
    _name = 'hr.resignation'
    _description = 'HR Resignation'
    _inherit = 'mail.thread'
    _rec_name = 'employee_id'

    name = fields.Char(string='Order Reference', copy=False,
                       readonly=True, index=True,
                       default=lambda self: _('New'))
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company, readonly=True)
    employee_id = fields.Many2one('hr.employee', string="Employee", copy=False,
                                  default=lambda
                                      self: self.env.user.employee_id.id, domain="[('company_id', '=', company_id)]",
                                  help='Name of the employee for '
                                       'whom the request is creating')
    employee_parent_id = fields.Many2one(related='employee_id.parent_id', readonly=True, related_sudo=False,
                                         domain="[('company_id', '=', company_id)]",
                                         string="Manager")
    coach_id = fields.Many2one(related='employee_id.coach_id', readonly=True,
                               domain="[('company_id', '=', company_id)]", related_sudo=False, string="HR")
    department_id = fields.Many2one('hr.department', string="Department", readonly=True,
                                    domain="[('company_id', '=', company_id)]",
                                    related='employee_id.department_id',
                                    help='Department of the employee')
    designation_id = fields.Many2one('hr.job', string="Designation", readonly=True,
                                     domain="[('company_id', '=', company_id)]",
                                     related='employee_id.job_id')
    resign_confirm_date = fields.Date(string="Confirmed Date", copy=False,
                                      help='Date on which the request '
                                           'is confirmed by the employee.',
                                      track_visibility="always")
    manager_approved_date = fields.Date(
        string="Manager Approved Date", copy=False,
        help='Date on which the request is confirmed by the manager.',
        track_visibility="always")
    hr_approved_date = fields.Date(
        string="HR Approved Date", copy=False,
        help='Date on which the request is confirmed by the HR.',
        track_visibility="always")
    hr_approved_reliving_date = fields.Date(
        string="Approved Last Day of Employee", copy=False,
        help='Date on which the request is confirmed by the manager.',
        track_visibility="always")
    joined_date = fields.Date(string="Join Date", copy=False,
                              help='Joining date of the employee.'
                                   'i.e Start date of the first contract')
    expected_revealing_date = fields.Date(string="Request Last Day", copy=False,
                                          help='Employee requested date on '
                                               'which employee is revealing '
                                               'from the company.')
    reason = fields.Text(string="Reason", required=True,
                         help='Specify reason for leaving the company')
    notice_period = fields.Char(string="Notice Period", copy=False,
                                help="Notice Period of the employee.")
    state = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('manager_approved', 'Manager Approved'),
         ('hr_approved', 'HR Approved'),
         ('cancel', 'Rejected')],
        string='Status', default='draft', track_visibility="always")
    resignation_type = fields.Selection(selection=RESIGNATION_TYPE,
                                        help="Select the type of resignation: "
                                             "normal resignation or "
                                             "fired by the company")
    change_employee = fields.Boolean(string="Change Employee",
                                     compute="_compute_change_employee",
                                     help="Checks , if the user has permission"
                                          " to change the employee")
    employee_contract = fields.Char(string="Contract", copy=False)
    is_employee = fields.Boolean(string="Is Employee", compute="_compute_is_employee")
    state_manager = fields.Selection(
        [('draft', 'Draft'), ('confirm', 'Confirm'), ('manager_approved', 'Manager Approved'),
         ('hr_approved', 'HR Approved'),
         ('cancel', 'Rejected')],
        string='Status Manager', default='manager_approved')
    status_boolean = fields.Boolean(string="Status Boolean", default=False)
    x_review_result = fields.Char(string="Review Result")

    @api.depends('employee_id')
    def _compute_is_employee(self):
        for record in self:
            record.is_employee = record.employee_id.user_id.id == self.env.uid

    @api.depends('employee_id')
    def _compute_change_employee(self):
        """ Check whether the user
        has the permission to change the employee"""
        res_user = self.env['res.users'].browse(self._uid)
        self.change_employee = res_user.has_group('hr.group_hr_user')

    @api.constrains('employee_id')
    def _check_employee_id(self):
        """" Constraint method to check if the current user has the permission
        to create
         a resignation request for the specified employee.
        """
        for resignation in self:
            if not self.env.user.has_group('hr.group_hr_user'):
                if (resignation.employee_id.user_id.id and
                        resignation.employee_id.user_id.id != self.env.uid):
                    raise ValidationError(
                        _('You cannot create a request for other employees'))

    # @api.constrains('joined_date')
    # def _check_joined_date(self):
    #     """
    #     Check if there is an active resignation request for the
    #     same employee with a confirmed or approved state, based on the
    #     'joined_date'
    #     of the current resignation.
    #     """
    #     for resignation in self:
    #         resignation_request = self.env['hr.resignation'].sudo().search(
    #             [('employee_id', '=', resignation.employee_id.id),
    #              ('state', 'not in', ['cancel'])])
    #         if resignation_request:
    #             print("resignation_request", resignation_request)
    #             raise ValidationError(
    #                 _('There is a resignation request in confirmed or'
    #                   ' approved state for this employee'))

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        """
        Method triggered when the 'employee_id' field is changed.
        """
        self.joined_date = self.employee_id.joining_date
        if self.employee_id:
            resignation_request = self.env['hr.resignation'].sudo().search(
                [('employee_id', '=', self.employee_id.id),
                 ('state', 'in', ['confirm', 'manager_approved', 'hr_approved'])])
            if resignation_request:
                print("resignation_request", resignation_request)
                raise ValidationError(
                    _('There is a resignation request in confirmed or'
                      ' approved state for this employee'))
            employee_contract = self.env['hr.contract'].search(
                [('employee_id', '=', self.employee_id.id)])
            for contracts in employee_contract:
                if contracts.state == 'open':
                    self.employee_contract = contracts.name
                    self.notice_period = contracts.notice_days

    @api.model
    def create(self, vals):
        """
            Override of the create method to assign a sequence for the record.
        """
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'hr.resignation') or _('New')
        return super(HrResignation, self).create(vals)

    def action_confirm_resignation(self):
        """
        Method triggered by the 'Confirm' button to confirm the resignation request.
        This sets up an approval workflow and updates the resignation state.
        """
        for resignation in self:
            # handling the approvers in request_approval.py in multi approval
            # handling the state change in mail_compose_message.py in hr resignation
            if hasattr(self, 'x_has_request_approval'):
                self.x_has_request_approval = False

            manager_id = resignation.employee_parent_id.user_id.id
            if not manager_id:
                raise ValidationError("Manager does not have a corresponding user.")

            hr_coach_id = resignation.coach_id.user_id.id
            if not hr_coach_id:
                raise ValidationError("HR Coach does not have a corresponding user.")

                # approval_type_model = self.env['multi.approval.type']
                # approval_type_line_model = self.env['multi.approval.type.line']
                #
                # approval_type = approval_type_model.search([
                #     ('model_id', '=', 'hr.resignation'),
                #     ('domain', 'ilike', '"state"')
                # ], limit=1)
                #
                # if approval_type and approval_type.state == 'confirm':
                #     lines = approval_type_line_model.search([('type_id', '=', approval_type.id)])
                #
                #     while len(lines) < 2:
                #         new_line = approval_type_line_model.create({
                #             'type_id': approval_type.id,
                #             'name': f"L{len(lines) + 1}",
                #             'sequence': len(lines) + 1,
                #         })
                #         lines += new_line
                #
                #     for index, line in enumerate(lines):
                #
                #         if index == 0:
                #             line.user_id = [(6, 0, [])]
                #             manager_id = resignation.employee_parent_id.user_id.id
                #             if manager_id:
                #                 line.user_id = [(4, manager_id)]
                #             else:
                #                 raise ValidationError("Manager does not have a corresponding user.")
                #
                #         elif index == 1:
                #             line.user_id = [(6, 0, [])]
                #             hr_coach_id = resignation.coach_id.user_id.id
                #             if hr_coach_id:
                #                 line.user_id = [(4, hr_coach_id)]
                #             else:
                #                 raise ValidationError("HR Coach does not have a corresponding user.")

                #     # resignation.state = 'confirm'
                # else:
                #     raise ValidationError("No Approval Type found for this Separation Model.")

            # handling the state and resign_confirm_date move in mail_compose_message.py
            # resignation.state = 'confirm'
            # resignation.resign_confirm_date = fields.Datetime.now()
        self.ensure_one()

        if not self.employee_parent_id.work_email:
            raise UserError(_("The Manager does not have a valid email address."))

        if not self.coach_id.work_email:
            raise UserError(_("The HR does not have a valid email address."))

        template = self.env.ref('hr_resignation.email_template_resignation_confirm', raise_if_not_found=False)
        if not template:
            raise UserError(_("The email template for the resignation submission does not exist."))

        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

        ctx = dict(
            default_model='hr.resignation',
            default_res_ids=self.ids,
            default_template_id=template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid="mail.mail_notification_light",
            force_email=True,
        )

        return {
            'name': _('Send Separation Letter'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        # template_id = self.env.ref('hr_resignation.email_template_resignation_confirm', raise_if_not_found=False)
        # if template_id:
        #     template_id.send_mail(resignation.id, force_send=True)

    def action_cancel_resignation(self):
        """
        Method triggered by the 'Cancel' button to cancel the
        resignation request.
        """
        for resignation in self:
            resignation.state = 'cancel'

    def action_reject_resignation(self):
        """
            Method triggered by the 'Reject' button to reject the
            resignation request.
        """

        self.ensure_one()

        if not self.employee_id.work_email:
            raise UserError(_("The Employee does not have a valid email address."))

        if not self.employee_parent_id.work_email:
            raise UserError(_("The Manager does not have a valid email address."))

        if not self.coach_id.work_email:
            raise UserError(_("The HR does not have a valid email address."))

        template = self.env.ref('hr_resignation.email_template_resignation_reject', raise_if_not_found=False)
        if not template:
            raise UserError(_("The email template for the resignation rejection does not exist."))

        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

        ctx = dict(
            default_model='hr.resignation',
            default_res_ids=self.ids,
            default_template_id=template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid="mail.mail_notification_light",
            force_email=True,
        )

        return {
            'name': _('Send Separation Rejection Letter'),
            'type': 'ir.actions.act_window',
            'res_model': 'mail.compose.message',
            'view_mode': 'form',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
        # resignation.state = 'cancel'
        # template_id = self.env.ref('hr_resignation.email_template_resignation_reject')
        # if template_id:
        #     template_id.send_mail(resignation.id, force_send=True)

    def action_reset_to_draft(self):
        """
        Method triggered by the 'Set to Draft' button to reset the
        resignation request to the 'draft' state.
        """
        for resignation in self:
            # Reset resignation state
            resignation.state = 'draft'

            # Restore employee's state
            resignation.employee_id.active = True  # Reactivate employee
            resignation.employee_id.resigned = False  # Reset resigned flag
            resignation.employee_id.fired = False  # Reset fired flag

            # Reset resignation-related dates
            resignation.employee_id.resign_date = None

            # Reactivate user if a user is linked to the employee
            if resignation.employee_id.user_id:
                resignation.employee_id.user_id.active = True  # Reactivate user
                resignation.employee_id.user_id = resignation.employee_id.user_id.id

            # Revert employee's state to 'employment' in the employee table
            resignation.employee_id.sudo().write({'state': 'employment'})

            # Revert contract state changes
            employee_contract = self.env['hr.contract'].search(
                [('employee_id', '=', resignation.employee_id.id)]
            )
            for contract in employee_contract:
                if contract.state == 'cancel':  # Reactivate contract if it was canceled
                    contract.state = 'open'

            # Reset resignation-specific fields
            resignation.employee_contract = False
            resignation.hr_approved_reliving_date = None
            resignation.hr_approved_date = None
            resignation.manager_approved_date = None

    # def action_manager_approve_resignation(self):
    #     for resignation in self:
    #         if (resignation.expected_revealing_date and
    #             resignation.resign_confirm_date):
    #                 resignation.state = 'manager_approved'
    #                 resignation.manager_approved_date = str(fields.Datetime.now())
    #                 template_id = self.env.ref('hr_resignation.email_template_resignation_approve')
    #                 if template_id:
    #                     template_id.send_mail(resignation.id, force_send=True)
    #         else:
    #             raise ValidationError(_('Please Enter Valid Dates.'))

    def action_hr_approve_resignation(self):
        if not self.employee_id.work_email:
            raise UserError(_("The Employee does not have a valid email address."))

        if not self.employee_parent_id.work_email:
            raise UserError(_("The Manager does not have a valid email address."))

        if not self.coach_id.work_email:
            raise UserError(_("The HR does not have a valid email address."))

        for resignation in self:
            if resignation.resign_confirm_date:
                employee_contract = self.env['hr.contract'].search(
                    [('employee_id', '=', self.employee_id.id)])
                if not employee_contract:
                    raise ValidationError(
                        _("There are no Compensation master found for this employee"))
                for contract in employee_contract:
                    if contract.state == 'open':
                        if not self.notice_period:
                            raise ValidationError(
                                _("There is no notice period found for this employee. "
                                  "Please add a notice period in the compensation master.")
                            )
                            # Validate hr_approved_reliving_date if notice period is 0
                        if self.notice_period == 0 and not self.hr_approved_reliving_date:
                            raise ValidationError(
                                _("Notice period is 0. HR needs to fill the HR Approved Relieving Date.")
                            )
                        resignation.employee_contract = contract.name
                        resignation.state = 'hr_approved'
                        resignation.hr_approved_date = str(fields.Datetime.now())
                        resignation.hr_approved_reliving_date = (
                                resignation.resign_confirm_date + timedelta(
                            days=contract.notice_days))
                        # template_id = self.env.ref('hr_resignation.email_template_resignation_approve_hr')
                        # if template_id:
                        #     template_id.send_mail(resignation.id, force_send=True)
                    else:
                        if not self.hr_approved_reliving_date:
                            raise ValidationError(
                                _("Please enter the Approved Last Day of Employee in resignation"))
                        resignation.state = 'hr_approved'
                        # template_id = self.env.ref('hr_resignation.email_template_resignation_approve_hr')
                        # if template_id:
                        #     template_id.send_mail(resignation.id, force_send=True)
                    # Cancelling contract
                    contract.state = 'cancel' if contract.state == "open" else \
                        contract.state

                resignation.employee_id.sudo().write({'state': 'relieved'})

                # Changing state of the employee if resigning today
                if (resignation.hr_approved_reliving_date <= fields.Date.today()
                        and resignation.employee_id.active):
                    resignation.employee_id.active = False
                    # Changing fields in the employee table
                    # with respect to resignation
                    resignation.employee_id.resign_date = (
                        resignation.hr_approved_reliving_date)
                    if resignation.resignation_type == 'resigned':
                        resignation.employee_id.resigned = True
                    else:
                        resignation.employee_id.fired = True
                    # Removing and deactivating user
                    if resignation.employee_id.user_id:
                        resignation.employee_id.user_id.active = False
                        resignation.employee_id.user_id = None
            else:
                raise ValidationError(_('Please Enter Valid Dates.'))

    def update_employee_status(self):
        resignation = self.env['hr.resignation'].search(
            [('state', '=', 'manager_approved')])
        for rec in resignation:
            if rec.hr_approved_reliving_date <= fields.Date.today():
                if rec.employee_id.active:
                    rec.employee_id.active = False

                # Changing fields in the employee  table with
                # respect to resignation
                rec.employee_id.resign_date = rec.hr_approved_reliving_date
                if rec.resignation_type == 'resigned':
                    rec.employee_id.resigned = True
                    departure_reason_id = self.env[
                        'hr.departure.reason'].search(
                        [('name', '=', 'Resigned')])
                else:
                    rec.employee_id.fired = True
                    departure_reason_id = self.env[
                        'hr.departure.reason'].search(
                        [('name', '=', 'Fired')])

                today = fields.Date.today()
                running_contract_ids = self.env['hr.contract'].search([
                    ('employee_id', '=', rec.employee_id.id),
                    ('company_id', '=', rec.employee_id.company_id.id),
                    ('state', '=', 'open'),
                ]).filtered(lambda c: c.date_start <= today and (
                        not c.date_end or c.date_end >= today))
                running_contract_ids.state = 'close'
                rec.employee_id.departure_reason_id = departure_reason_id
                rec.employee_id.departure_date = rec.hr_approved_reliving_date

                # Removing and deactivating user
                if rec.employee_id.user_id:
                    rec.employee_id.user_id.active = False
                    rec.employee_id.user_id = None

    # def action_send_reliving_letter(self):
    #     for resignation in self:
    #         template_id = self.env.ref('hr_resignation.email_template_reliving_letter')
    #         if template_id:
    #             template_id.send_mail(resignation.id, force_send=True)

    def action_send_reliving_letter(self):
        self.ensure_one()
        template = self.env.ref('hr_resignation.email_template_reliving_letter', False)
        if not template:
            raise UserError(_("Relieving Letter template not found."))

        compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
        if not compose_form:
            raise UserError(_("Email composition form not found."))
        if not self.employee_id.private_email:
            raise ValidationError(
                _("There are no Private email found for this employee"))

        ctx = dict(
            default_model='hr.resignation',
            default_res_ids=self.ids,
            default_template_id=template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid="mail.mail_notification_light",
        )
        return {
            'name': _('Compose Separation Confirmation Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }
