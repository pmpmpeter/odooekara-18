# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, AccessError, UserError
from bs4 import BeautifulSoup


class GrievanceManagement(models.Model):
    _name = 'grievance.management'
    _description = "Grievance Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char()
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True,
                                  domain=lambda self: self._compute_employee_domain())
    manager_id = fields.Many2one('hr.employee', string='Manager', domain=lambda self: [('company_id', '=', self.env.company.id)], required=True, tracking=True)
    company_id = fields.Many2one('res.company', string= 'Company', default=lambda self: self.env.company, domain=lambda self: [('id', '=', (self.env.company.id))])
    representative_id = fields.Many2one('hr.employee', string='Representative', domain=lambda self: [('company_id', '=', self.env.company.id)], copy=False, tracking=True)
    management_representative_id = fields.Many2one('hr.employee', string='Management Representative', copy=False, domain=lambda self: [('company_id', '=', self.env.company.id)],
                                                   tracking=True)
    state = fields.Selection([('draft', 'Draft'),
                              ('submit', 'Submit'),
                              ('satisfied', 'Satisfied'),
                              ('un_satisfied', 'UnSatisfied')], string='Status',
                             default='draft', copy=False, tracking=True)
    type = fields.Many2one('grievance.type.names', string='Types of Grievance',domain=lambda self: [('company_id', '=', self.env.company.id)], copy=False, tracking=True)
    subject = fields.Char(string='Subject', copy=False, tracking=True)
    description = fields.Html(string='Description', copy=False)
    create_date = fields.Date(string='Create Date', readonly=True, default=fields.Datetime.now)
    date_timeline = fields.Date(string='Timeline', store=True, copy=False, tracking=True)
    resolution = fields.Text(string='Resolution', copy=False, tracking=True)
    management_resolution = fields.Text(string='Management Resolution', copy=False, tracking=True)
    # is_manager = fields.Boolean(compute='_compute_is_manager')
    unsatisfied = fields.Boolean(string="Unsatisfied", copy=False)
    employee_grievance_ids = fields.Many2many('hr.employee',
                                              compute='_compute_employee_grievance',
                                              string='Employee Prob', copy=False)
    employee_grievance_count = fields.Integer("Employee Prob Count",
                                              compute='_compute_employee_grievance', default=0, copy=False)

    @api.model
    def _compute_employee_domain(self):
        """ Dynamically restrict employee selection based on user group """
        user = self.env.user
        if user.has_group('hr.group_hr_user') or user.has_group('hr.group_hr_manager'):
            return [('company_id', '=', self.env.company.id)]
        else:
            return [('user_id', '=', user.id)]

    @api.onchange('employee_id')
    def OnchangeEmployee(self):
        if self.employee_id:
            self.manager_id = self.employee_id.parent_id.id

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def action_un_satisfied(self):
        for record in self:
            record.unsatisfied = True
            record.state = 'un_satisfied'

    # to make the resolution comment and timeline field readonly for other users
    # @api.depends('manager_id')
    # def _compute_is_manager(self):
    #     for record in self:
    #         if record.manager_id.user_id.id == self.env.user.id:
    #             record.is_manager = True
    #         else:
    #             record.is_manager = False

    def send_activity_notification(self):
        notify_type = self.env.ref("mail.mail_activity_data_todo", False)
        if not notify_type:
            return

        for req in self:
            users_to_notify = set()
            if req.manager_id:
                users_to_notify.add(req.manager_id.user_id.id)
            else:
                raise ValidationError("Please select the Manager")

            if not req.manager_id.user_id.id:
                raise ValidationError(
                    "The selected manager does not have a linked user account. Please ensure the manager is linked to a user.")

            if not req.type.respective_hod_id.user_id.id:
                raise ValidationError(
                    "The respective HOD for the grievance type does not have a linked user account. Please ensure the HOD is linked to a user.")

            if req.type and req.type.respective_hod_id:
                users_to_notify.add(req.type.respective_hod_id.user_id.id)
            else:
                raise ValidationError("The HOD for the grievance type is not set.")

            summary = _("The grievance {code} needs to be reviewed by the respective persons.").format(
                code=req.type.name)

            for user_id in users_to_notify:
                self.env["mail.activity"].sudo().create(
                    {
                        "res_id": req.id,
                        "res_model_id": self.env["ir.model"]._get(req._name).id,
                        "activity_type_id": notify_type.id,
                        "summary": summary,
                        "user_id": user_id,
                    }
                )

    def finalize_activity_or_message(self, msg):
        users_to_notify = set()
        if self.manager_id:
            users_to_notify.add(self.manager_id.user_id.id)

        if self.type and self.type.respective_hod_id:
            users_to_notify.add(self.type.respective_hod_id.user_id.id)

        notify_type = self.env.ref("mail.mail_activity_data_todo", False)
        if not notify_type:
            return

        for user_id in users_to_notify:
            activities = self.activity_ids.filtered(
                lambda a: a.activity_type_id == notify_type and a.user_id.id == user_id
            )
            activities._action_done(msg)

        self.message_post(body=msg)

    def action_submit_to_manager(self):
        # if not self.manager_id.work_email:
        #     raise ValidationError("The manager work mail is required to send a mail.")
        #
        # template = self.env.ref('grievance_management.employee_grievance_template_to_manager')
        # for rec in self:
        #     if rec.manager_id.work_email:
        #         template.send_mail(rec.id, force_send=True)
        self.send_activity_notification()
        self.state = 'submit'

    def send_mail_to_employee(self):
        """Open email wizard to send resolution email."""
        self.ensure_one()

        if not (self.resolution or self.date_timeline):
            raise ValidationError(_("Please ensure that 'Timeline' or 'Resolution' fields are not empty."))

        if not self.employee_id.work_email:
            raise ValidationError(_("The employee does not have a valid work email."))

        template = self.env.ref('grievance_management.employee_grievance_template_reply_with_resolution',
                                raise_if_not_found=False)
        if not template:
            raise ValidationError(_("The email template is not configured."))

        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

        self.sudo().message_follower_ids.filtered(lambda f: f.partner_id.email != self.employee_id.work_email).unlink()

        ctx = {
            'default_model': 'grievance.management',
            'default_res_ids': self.ids,
            'default_template_id': template.id,
            'default_composition_mode': 'comment',
            'default_email_layout_xmlid': "mail.mail_notification_light",
            'default_email_to': self.employee_id.work_email,
        }

        return {
            'name': _('Compose Grievance Reply Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def _compute_employee_grievance(self):
        for record in self:
            domain = [('id', '=', record.employee_id.id)]
            employee_grievance_ids = self.env['hr.employee'].sudo().search(domain)
            record.employee_grievance_ids = employee_grievance_ids
            record.employee_grievance_count = len(employee_grievance_ids)

    def action_open_grievance_employee(self):
        action = self.env.ref('hr.open_view_employee_tree')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.employee_grievance_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.employee_grievance_ids.ids)) + "])]"
        elif len(self.employee_grievance_ids.ids) == 1:
            res = self.env.ref('hr.view_employee_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.employee_grievance_ids.ids and self.employee_grievance_ids.ids[0] or False
        return result

    @api.model
    def create(self, values):
        values['name'] = self.env['ir.sequence'].sudo().next_by_code('grievance.management')
        res = super(GrievanceManagement, self).create(values)
        return res

    def action_satisfied(self):
        for record in self:
            msg = _("%s submitted the request.") % self.env.user.name
            self.finalize_activity_or_message(msg)
            record.state = 'satisfied'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only records in the 'Draft' state can be deleted."))
        return super(GrievanceManagement, self).unlink()
