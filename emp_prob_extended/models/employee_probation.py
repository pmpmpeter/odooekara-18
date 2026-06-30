from odoo import models, fields, api, _
import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import *
from odoo.exceptions import UserError, ValidationError


class Employee(models.Model):
    _inherit = 'hr.employee'

    employee_probation_ids = fields.Many2many('employee.probation',
                                              compute='_compute_employee_probation',
                                              string='Employee Probation ID', copy=False)
    employee_probation_count = fields.Integer("Employee Probation Count",
                                              compute='_compute_employee_probation', default=0, copy=False)
    hr_id = fields.Many2one('hr.employee',string='HR')

    def _compute_employee_probation(self):
        for record in self:
            domain = [('employee_id', '=', record.id)]
            employee_probation_ids = self.env['employee.probation'].sudo().search(domain)
            record.employee_probation_ids = employee_probation_ids
            record.employee_probation_count = len(employee_probation_ids)

    def action_get_employee_probation(self):
        action = self.env.ref('emp_prob_extended.employee_probation_action')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.employee_probation_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.employee_probation_ids.ids)) + "])]"
        elif len(self.employee_probation_ids.ids) == 1:
            res = self.env.ref('probation_management.employee_probation_form_view', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.employee_probation_ids.ids and self.employee_probation_ids.ids[0] or False
        return result


class EmployeeProbation(models.Model):
    _name = 'employee.probation'
    _description = 'Employee Probation'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char('Sequence', readonly=True, index=True, default=lambda self: _('New'))
    employee_id = fields.Many2one('hr.employee', 'Employee', domain=lambda self: self._compute_employee_domain())
    email = fields.Char('Email', related='employee_id.work_email')
    department_id = fields.Many2one('hr.department', 'Department', related='employee_id.department_id',
                                    domain="[('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company,
                                 domain=lambda self: [('id', '=', (self.env.company.id))])
    parent_id = fields.Many2one('hr.employee', 'Manager', related='employee_id.parent_id',
                                domain="[('company_id', '=', company_id)]")
    employee_reviews_ids = fields.One2many('employee.reviews.details', 'probation_id', 'Employee Reviews')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('review', 'Reviewed'),
        ('confirm', 'Confirmed'),
        ('cancel', 'Canceled'),
    ], string='Status', default='draft', required=True, tracking=True)

    based_on = fields.Selection([
        ('months', 'Months'),
        ('days', 'Days'),
    ], string="Based On", default='months', required=True, copy=False)

    employee_prob_ids = fields.Many2many('hr.employee',
                                         compute='_compute_employee_prob',
                                         string='Employee Prob', copy=False)
    employee_prob_count = fields.Integer("Employee Prob Count",
                                         compute='_compute_employee_prob', default=0, copy=False)

    review_form_ids = fields.Many2many(
        'prob.review.form',
        compute='_compute_review_forms',
        string='Review Forms',
        copy=False
    )
    review_form_count = fields.Integer(
        "Review Form Count",
        compute='_compute_review_forms',
        default=0,
        copy=False
    )

    start_date = fields.Date('Start Date', compute='_compute_start_date', store=True)
    end_date = fields.Date('End Date', compute='_compute_end_date', store=True)
    number_of_months = fields.Integer(string='Number of Months', default=6, store=True, copy=False)
    number_of_days = fields.Integer(string='Number of Days', default=15, store=True, copy=False)
    review_form_id = fields.Many2one('prob.review.form', string="Probation Review Form", copy=False)
    hr_id = fields.Many2one('hr.employee',string='HR',related='employee_id.hr_id')
    manager_user = fields.Many2one('res.users',string='Manager user',related='employee_id.parent_id.user_id')
    hr_user = fields.Many2one('res.users',string='Manager user',related='employee_id.hr_id.user_id')

    @api.onchange('employee_id')
    def _check_employee_probation(self):
        if self.employee_id:
            probation_request = self.env['employee.probation'].sudo().search(
                [('employee_id', '=', self.employee_id.id),
                 ('state', 'in', ['in_progress', 'review', 'confirm'])])
            if probation_request:
                raise ValidationError(
                    _('A probation form for this employee is already in progress, under review, or confirmed.')
                )

    @api.constrains('email', 'department_id', 'parent_id')
    def _check_fields_null(self):
        for record in self:
            if not record.email:
                raise ValidationError(_('Please fill the Email for the employee'))
            if not record.department_id:
                raise ValidationError(_('Please fill the Department for the employee'))
            if not record.parent_id:
                raise ValidationError(_('Please fill the Manager for the employee'))

    @api.model
    def _compute_employee_domain(self):
        """ Dynamically restrict employee selection based on user group """
        user = self.env.user
        if user.has_group('hr.group_hr_user') or user.has_group('hr.group_hr_manager'):
            return [('company_id', '=', self.env.company.id)]
        else:
            return [('user_id', '=', user.id)]

    @api.depends('employee_id')
    def _compute_start_date(self):
        for record in self:
            if record.employee_id:
                contract = self.env['hr.contract'].search(
                    [('employee_id', '=', record.employee_id.id)],
                    order='date_start asc',
                    limit=1
                )
                if contract:
                    record.start_date = contract.date_start
                else:
                    raise ValidationError(
                        "No contract found for the selected employee. Please ensure the employee has a valid contract."
                    )
            else:
                record.start_date = False

    @api.depends('start_date', 'number_of_months', 'number_of_days', 'based_on')
    def _compute_end_date(self):
        for record in self:
            if not record.start_date:
                record.end_date = False
                continue

            if record.based_on == 'months':
                if record.number_of_months <= 0 or record.number_of_months > 12:
                    raise UserError("The number of months must be between 1 and 12.")
                record.end_date = record.start_date + relativedelta(months=record.number_of_months)
            elif record.based_on == 'days':
                if record.number_of_days <= 0:
                    raise UserError("The number of days must be greater than 0.")
                record.end_date = record.start_date + relativedelta(days=record.number_of_days)
            else:
                record.end_date = False

    def create(self, vals):
        vals['name'] = self.env['ir.sequence'].next_by_code('employee.probation.sequence') or 'New'
        return super(EmployeeProbation, self).create(vals)

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("You can delete a record only in the 'draft' state.")
        return super(EmployeeProbation, self).unlink()

    # def print_employee_probation(self):
    #     return self.env.ref('emp_prob_extended.report_probation_review_template').report_action(self.id)

    def employee_probation_confirm(self):
        if not self.review_form_id:
            raise UserError("No associated Probation Review Form found.")

        # Change the state to 'confirm'
        self.state = 'confirm'

    def action_send_probation_confirmation_mail(self):
        for record in self:
            if not record.review_form_id:
                raise UserError("No associated Probation Review Form found.")

            report = self.env.ref('emp_prob_extended.report_probation_review_template')
            pdf_content = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                report, [record.review_form_id.id], data=None)[0]
            data_record = base64.b64encode(pdf_content)

            attachment = self.env['ir.attachment'].create({
                'name': f"Probation_Confirmation_{record.employee_id.name}.pdf",
                'type': 'binary',
                'datas': data_record,
                'mimetype': 'application/pdf',
                'res_model': 'employee.probation',
                'res_id': record.id,
            })

            template = self.env.ref('emp_prob_extended.mail_probation_confirmation_mailsss', False)
            if not template:
                raise UserError(_("Probation Confirmation template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
            self.sudo().message_follower_ids.filtered(
                lambda f: f.partner_id.email != self.employee_id.work_email).unlink()

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            ctx = dict(
                default_model='employee.probation',
                default_res_ids=self.ids,
                default_template_id=template.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
                default_attachment_ids=[attachment.id],
                default_email_to=self.employee_id.work_email,
            )
            return {
                'name': _('Compose Probation Confirmation Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def employee_probation_cancel(self):
        for record in self:
            record.state = 'cancel'
            if record.review_form_id:
                record.review_form_id.write({'state': 'cancel'})

    def employee_probation_review(self):
        for record in self:
            if not record.employee_id:
                raise UserError("Please select an employee to create the probation review form.")

            record.state = 'in_progress'

            existing_form = self.env['prob.review.form'].search([('employee_probation_id', '=', record.id)], limit=1)

            if existing_form:
                record.review_form_id = existing_form.id
            else:
                review_form = self.env['prob.review.form'].create({
                    'employee_id': record.employee_id.id,
                    'job_title_id': record.employee_id.job_id.id,
                    'department_id': record.employee_id.department_id.id,
                    'date_of_joining': record.start_date,
                    'reporting_manager_id': record.employee_id.parent_id.id,
                    'reporting_manager_designation_id': record.employee_id.parent_id.job_id.id,
                    'employee_probation_id': record.id,
                })
                record.review_form_id = review_form.id
            if not self.parent_id.user_id:
                raise ValidationError(
                    _('Kindly check if the manager has a valid mail ID.')
                )
            else:
                user = self.parent_id.user_id
                self.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary="Employee Probation : Initial Review",
                    note=f"Kindly review the employee probation.",
                    user_id=user.id,
                    date_deadline=fields.Date.today()
                )
            if self.env.user.has_group('emp_prob_extended.group_employee_probation_manager'):
                return {
                    'type': 'ir.actions.act_window',
                    'name': 'Probation Review Form',
                    'res_model': 'prob.review.form',
                    'view_mode': 'form',
                    'res_id': record.review_form_id.id,
                    'target': 'current',
                }

            return

    def _compute_review_forms(self):
        for record in self:
            domain = [('employee_probation_id', '=', record.id)]
            review_forms = self.env['prob.review.form'].sudo().search(domain)
            record.review_form_ids = review_forms
            record.review_form_count = len(review_forms)

    def action_open_review_forms(self):
        action = self.env.ref('emp_prob_extended.probation_review_form_action')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.review_form_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.review_form_ids.ids)) + "])]"
        elif len(self.review_form_ids.ids) == 1:
            res = self.env.ref('emp_prob_extended.probation_review_form_form_view', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.review_form_ids.ids and self.review_form_ids.ids[0] or False
        return result

    def _compute_employee_prob(self):
        for record in self:
            domain = [('id', '=', record.employee_id.id)]
            employee_prob_ids = self.env['hr.employee'].sudo().search(domain)
            record.employee_prob_ids = employee_prob_ids
            record.employee_prob_count = len(employee_prob_ids)

    def action_open_employee(self):
        action = self.env.ref('hr.open_view_employee_tree')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.employee_prob_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.employee_prob_ids.ids)) + "])]"
        elif len(self.employee_prob_ids.ids) == 1:
            res = self.env.ref('hr.view_employee_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.employee_prob_ids.ids and self.employee_prob_ids.ids[0] or False
        return result


class EmployeeProbationReview(models.Model):
    _name = 'employee.reviews.details'
    _description = 'Employee Probation Review Details'

    probation_id = fields.Many2one('employee.probation', 'Probation ID')
    date = fields.Date('Date')
    reviewer = fields.Many2one('hr.employee', 'Reviewer')
    review_details = fields.Text('Review Details')
    performance = fields.Selection(
        [('excellent ', 'Excellent '),
         ('good ', 'Good '), ('average ', 'Average '),
         ('poor ', 'Poor '), ('worst ', 'Worst ')],
        string="Performance",
        required=False
    )
    rating = fields.Selection(
        [('0 ', 'Low '), ('1 ', 'Worst '),
         ('2 ', 'Poor '), ('3 ', 'Good '),
         ('4 ', 'Average '), ('5', 'Excellent')],
        string="Rating",
    )
