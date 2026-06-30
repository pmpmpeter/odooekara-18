# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import *
from odoo.exceptions import ValidationError, UserError
from datetime import datetime, date


class JoiningDocuments(models.Model):
    _name = 'joining.documents'
    _description = 'Joining Documents'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string="Name", copy=False, required=True)
    employee_id = fields.Many2one('hr.employee', string="Employee Name", domain="[('company_id', '=', company_id)]", copy=False, required=True)
    department_id = fields.Many2one('hr.department', string="Department", related="employee_id.department_id",domain="[('company_id', '=', company_id)]", copy=False)
    job_position_id = fields.Many2one('hr.job', string="Job Position", related="employee_id.job_id",domain="[('company_id', '=', company_id)]", copy=False)
    joining_date = fields.Date(string="Joining Date", related="employee_id.joining_date", copy=False)
    reference_file = fields.Binary(string='Reference File', copy=False)
    reference_filename = fields.Char(string='Reference Filename', copy=False)
    submitted_file = fields.Binary(string='Submitted File', attachment="True", copy=False)
    submitted_filename = fields.Char(string='Submitted Filename', copy=False)
    subject = fields.Html(string="Subject")
    document_type = fields.Selection(
        [('it_declaration', 'IT Declaration'),
         ('ebp_claim', 'EBP Claim Form'),  #
         ('app_order_form', 'Appointment Order Form'),
         ('bgv', 'BGV Email Template'),
         ('code_of_conduct', 'CODE OF CONDUCT'),
         ('consent', 'Consent Form'),
         ('criminal_case', 'Criminal Case'),
         ('emp_verifi_form', 'Employee Verification Form'),
         ('epf', 'EPF Form 11 Declaration Doc'),  #
         ('ex_media_comm', 'External Media Communication - Declaration (IIM)'),
         ('gmc', 'GMC and GPA Details'),
         ('joining_form', 'Joining form'),  #
         ('nda', 'NDA (Intellectual Property) Form'),
         ('pf_nomination', 'PF Nomination Form'),
         ('emp_ref_check', 'Pre - Employment Reference Check Form'),  # check we have separate module for this
         ('she_nda', 'SHE NDA- 2022 updated Form')],
        string="Document Type")

    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', '=', (self.env.company.id))])
    user_id = fields.Many2one('res.users', string='User ID', default=lambda self: self.env.user)
    contact_id = fields.Many2one('res.partner', 'Contact', copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        # ('mail_sent','Mail Sent'),
        ('waiting_confirmation', 'Waiting Confirmation'),
        ('done', 'Done'),
        ('reject', 'Rejected')
    ], string='Status', default='draft', required=True, tracking=True, copy=False)
    is_manager = fields.Boolean(string="Is Manager", store=False, copy=False)
    # GMC and GPA details
    emp_code = fields.Char(string="Employee Code")
    email = fields.Char(string="Email")
    contact_no = fields.Char(string="Contact Number")

    dependent_name = fields.Char(string="Dependent Name")
    relationship = fields.Char(string="Relationship")
    age = fields.Integer(string="Age")
    gender = fields.Selection([('male', 'Male'),
                               ('female', 'Female'),
                               ('other', 'Other')], string="Gender")

    designation = fields.Char(string="Designation")  # job_title
    doj = fields.Date(string="Date of Joining")
    dob = fields.Date(string="Date of Birth", required=False)
    lwd = fields.Date(string="Last Working Day", required=False)

    sum_insured_gmc = fields.Float(string="GMC Sum Insured")
    sum_insured_gpa = fields.Float(string="GPA Sum Insured")
    insurance_type = fields.Selection([('gmc', 'GMC'), ('gpa', 'GPA')], string="Insurance Type")
    insurance_status = fields.Selection(
        selection=[
            ('active', 'Active'),
            ('expired', 'Expired'),
            ('pending', 'Pending'),
            ('renewed', 'Renewed'),
            ('cancelled', 'Cancelled'),
            ('under_review', 'Under Review'),
            ('suspended', 'Suspended'),
            ('inactive', 'Inactive'),
            ('claimed', 'Claimed'),
            ('not_applicable', 'Not Applicable'),
        ],
        string="Insurance Status",
        default='active',
        help="Current status of the insurance coverage"
    )
    location = fields.Char(string="Location", copy=False)
    tax_entity = fields.Many2one('res.company', string='Tax Entity', default=lambda self: self.env.company)

    remarks = fields.Text(string="Remarks")
    join_doc_id = fields.Many2one('employee.join.doc.config', string='Joining document')
    sequence = fields.Integer(string='Sequence', compute='_compute_sequence', store=True, index=True)

    @api.depends('join_doc_id')
    def _compute_sequence(self):
        for record in self:
            record.sequence = record.join_doc_id.sequence

    @api.model
    def default_get(self, fields):
        """Set default values for 'is_manager' when creating a record."""
        defaults = super(JoiningDocuments, self).default_get(fields)
        if 'is_manager' in fields:
            defaults['is_manager'] = self.env.user.has_group('hr.group_hr_manager')
        return defaults

    def create(self, vals):
        if vals.get('employee_id'):
            employee = self.env['hr.employee'].browse(vals['employee_id'])
            vals.update({
                # 'emp_code': employee.employee_number,
                'email': employee.work_email,
                'contact_no': employee.work_phone,
                'designation': employee.job_title,
                'company_id': employee.company_id.id,
            })
        return super(JoiningDocuments, self).create(vals)

    @api.onchange('dob')
    def _compute_age(self):
        for record in self:
            if record.dob:
                today = date.today()
                dob = record.dob
                record.age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
            else:
                record.age = 0

    def write(self, vals):
        for record in self:
            if record.state == 'draft' and record.sequence > 1:
                previous_record = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('sequence', '=', record.sequence - 1),
                    ('state', '=', 'done')
                ], limit=1)

                if not previous_record:
                    previous_doc = self.env['employee.join.doc.config'].search([
                        ('sequence', '=', record.sequence - 1)
                    ], limit=1)
                    previous_doc_name = dict(previous_doc._fields['document_type'].selection).get(
                        previous_doc.document_type, 'Unknown Document'
                    )
                    raise ValidationError(
                        f"The '{previous_doc_name}' document must be 'Done' before submitting this.")

        return super(JoiningDocuments, self).write(vals)

    def action_submit(self):
        for record in self:
            if record.document_type in ['it_declaration', 'ebp_claim', 'bgv', 'epf'] and not record.submitted_file:
                raise UserError(_("The attachment is missing. Please attach the required document before submitting."))

            if record.sequence > 1:
                previous_record = self.search([
                    ('employee_id', '=', record.employee_id.id),
                    ('sequence', '=', record.sequence - 1),
                    ('state', '=', 'done')
                ], limit=1)

                if not previous_record:
                    previous_doc = self.env['employee.join.doc.config'].search([
                        ('sequence', '=', record.sequence - 1)
                    ], limit=1)
                    previous_doc_name = dict(previous_doc._fields['document_type'].selection).get(
                        previous_doc.document_type, 'Unknown Document'
                    )
                    raise ValidationError(
                        f"The '{previous_doc_name}' document must be 'Done' before submitting this.")

            record.state = 'waiting_confirmation'
            employee = record.employee_id.sudo()
            hr_user_id = employee.coach_id.user_id
            if not hr_user_id:
                raise ValidationError(
                    f"No HR user (coach) found for the employee {employee.name}. Please set a coach for the employee."
                )

            # Schedule the activity
            record.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary=f"Review and Approve Document: {record.name}",
                note=(
                    f"<p><b>Document Name:</b> {record.name}</p>"
                    f"<p><b>Employee:</b> {record.employee_id.name}</p>"
                    f"<p><b>Department:</b> {record.department_id.name or 'N/A'}</p>"
                    f"<p><b>Job Position:</b> {record.job_position_id.name or 'N/A'}</p>"
                    f"<p><b>Direct Link:</b> <a href='#id={record.id}&model=joining.documents' target='_blank'>Access Document</a></p>"
                ),
                user_id=hr_user_id.id,
                date_deadline=fields.Date.today()
            )
        return True

    def action_confirm(self):
        for record in self:
            record.state = 'done'

    def action_reset(self):
        for record in self:
            record.state = 'draft'

    def action_reject(self):
        for record in self:
            record.state = 'reject'

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only records in the 'Draft' state can be deleted."))
        return super(JoiningDocuments, self).unlink()

    def action_send_document_by_email(self):
        self.ensure_one()

        # Define the templates and document types in a mapping
        template_mapping = {
            'bgv': 'hr_extended.mail_template_bgv',
            'it_declaration': 'hr_extended.mail_template_it_declaration',
            'ebp_claim': 'hr_extended.mail_template_ebp_claim_form',
            'epf': 'hr_extended.mail_template_epf_11'
        }

        if self.document_type not in template_mapping:
            raise UserError(_("No email template defined for the document type '%s'.") % self.document_type)

        template_ref = template_mapping[self.document_type]
        template = self.env.ref(template_ref, raise_if_not_found=False)
        if not template:
            raise UserError(_("The email template for '%s' does not exist.") % self.document_type)

        compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

        if not self.contact_id.email:
            raise UserError(_("The recipient does not have a valid email address."))

        if not self.submitted_file:
            raise UserError(_("The attachment is missing. Please attach the required document before sending."))

        employee_name = self.employee_id.name if self.employee_id else "Unknown Employee"
        current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
        attachment_name = f"{employee_name}_{self.document_type.replace('_', ' ').title()}_{current_datetime}"
        attachment = self.env['ir.attachment'].create({
            'name': attachment_name,
            'type': 'binary',
            'datas': self.submitted_file,
            'mimetype': 'application/octet-stream',
            'res_model': 'joining.documents',
            'res_id': self.id,
        })

        self.sudo().message_follower_ids.filtered(lambda f: f.partner_id.email != self.contact_id.email).unlink()

        ctx = dict(
            default_model='joining.documents',
            default_res_ids=self.ids,
            default_template_id=template.id,
            default_composition_mode='comment',
            default_email_layout_xmlid="mail.mail_notification_light",
            default_attachment_ids=[attachment.id],
        )

        return {
            'name': _('Compose Email'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(compose_form.id, 'form')],
            'view_id': compose_form.id,
            'target': 'new',
            'context': ctx,
        }

    def action_print_document(self):
        self.ensure_one()
        if not self.document_type:
            raise UserError("Please select a Document Type before printing.")
        if self.document_type == 'gmc':
            return self.env.ref('hr_extended.get_cmg_and_gpa_details').report_action(self)
        else:
            return self.env.ref('hr_extended.report_joining_doc_form_template').report_action(self)

        
    # def _print_she_nda(self):
    #     return self.env.ref('hr_extended.nda_form_template').report_action(self)
    #
    # def _print_app_order_form(self):
    #     return self.env.ref('hr_extended.appointment_order_form_template').report_action(self)
    #
    # def _print_code_of_conduct(self):
    #     return self.env.ref('hr_extended.code_of_conduct_template').report_action(self)
    #
    # def _print_consent(self):
    #     return self.env.ref('hr_extended.consent_form_template').report_action(self)
    #
    # def _print_criminal_case(self):
    #     return self.env.ref('hr_extended.criminal_case_form_template').report_action(self)
    #
    # def _print_emp_verifi_form(self):
    #     return self.env.ref('hr_extended.employee_verification_form_template').report_action(self)
    #
    # def _print_ex_media_comm(self):
    #     return self.env.ref('hr_extended.media_declare_form_template').report_action(self)
    #
    # def _print_pf_nomination(self):
    #     return self.env.ref('hr_extended.report_nomination_form_template').report_action(self)
    #
    # def _print_gmc_gpa_details(self):
    #     return self.env.ref('hr_extended.get_cmg_and_gpa_details').report_action(self)
    #
    # def _print_nda_details(self):
    #     return self.env.ref('hr_extended.report_nda_intellectual_property_form_template').report_action(self)

    # def action_open_related_candidate(self):
    #     self.ensure_one()
    #     candidate = self.env['preemp.check'].search(
    #         [('applicant_id', '=', self.employee_id.applicant_id.id)], limit=1)
    #     if candidate:
    #         return {
    #             'name': _('Referral Candidate'),
    #             'type': 'ir.actions.act_window',
    #             'view_mode': 'form',
    #             'res_model': 'preemp.check',
    #             'view_id': self.env.ref('hr_extended.view_pre_employment_reference_check_form').id,
    #             'res_id': candidate.id,
    #             'target': 'current',
    #         }

    # def action_send_bgv_by_email(self):
    #     """ Open a window to compose an email, with the template 'mail_template_bgv' loaded by default """
    #     self.ensure_one()
    #
    #     # Fetch the email template
    #     template = self.env.ref('hr_extended.mail_template_bgv', raise_if_not_found=False)
    #     if not template:
    #         raise UserError(_("The email template for sending Background Verification does not exist."))
    #
    #     # Fetch the compose form
    #     compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)
    #
    #     # Check if recipient email exists
    #     if not self.contact_id.email:
    #         raise UserError(_("The recipient does not have a valid email address."))
    #
    #     # Check if the attachment exists
    #     if not self.submitted_file:
    #         raise UserError(
    #             _("The attachment is missing. Please attach the documents as a single file in the submitted file before submitting."))
    #
    #     # Create the attachment
    #     employee_name = self.employee_id.name if self.employee_id else "Unknown Employee"
    #     current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    #     attachment = self.env['ir.attachment'].create({
    #         'name': f'{employee_name}_BGV_{current_datetime}',
    #         'type': 'binary',
    #         'datas': self.submitted_file,
    #         'mimetype': 'application/octet-stream',
    #         'res_model': 'joining.documents',
    #         'res_id': self.id,
    #     })
    #
    #     # Context for email composition
    #     ctx = dict(
    #         default_model='joining.documents',
    #         default_res_ids=self.ids,
    #         default_template_id=template.id,
    #         default_composition_mode='comment',
    #         default_email_layout_xmlid="mail.mail_notification_light",
    #         default_attachment_ids=[attachment.id],
    #     )
    #
    #     # Return the compose email wizard
    #     return {
    #         'name': _('Compose Email'),
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'mail.compose.message',
    #         'views': [(compose_form.id, 'form')],
    #         'view_id': compose_form.id,
    #         'target': 'new',
    #         'context': ctx,
    #     }
    #
    # def action_send_it_declaration_by_email(self):
    #     self.ensure_one()
    #     for record in self:
    #         template_id = self.env.ref('hr_extended.mail_template_it_declaration',
    #                                    raise_if_not_found=False)
    #         if not template_id:
    #             raise UserError(
    #                 _("The email template for sending IT declaration does not exist."))
    #
    #         recipient_email = record.contact_id.email
    #         if not recipient_email:
    #             raise UserError(_("The Contact does not have a valid email address."))
    #
    #         current_user_email = record.env.user.email
    #         if not current_user_email:
    #             raise UserError(_("The current user does not have a valid email address."))
    #
    #         attachment_ids = []
    #         if record.submitted_file:
    #             employee_name = record.employee_id.name if record.employee_id else "Unknown Employee"
    #             current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    #
    #             attachment = self.env['ir.attachment'].create({
    #                 'name': f'{employee_name}_IT_Declaration_{current_datetime}',
    #                 'type': 'binary',
    #                 'datas': record.submitted_file,
    #                 'mimetype': 'application/octet-stream',
    #                 'res_model': 'joining.documents',
    #                 'res_id': record.id,
    #             })
    #
    #             attachment_ids = [(4, attachment.id)]
    #         else:
    #             raise UserError("The IT Declaration form is missing. Please attach the form before submitting.")
    #
    #         template_id.send_mail(record.id, force_send=True, email_values={'attachment_ids': attachment_ids})
    #
    #         # record.write({'state': 'mail_sent'})
    #
    # def action_send_ebp_claim_form_by_email(self):
    #     self.ensure_one()
    #     for record in self:
    #         template_id = self.env.ref('hr_extended.mail_template_ebp_claim_form',
    #                                    raise_if_not_found=False)
    #         if not template_id:
    #             raise UserError(
    #                 _("The email template for sending IT declaration does not exist."))
    #
    #         recipient_email = record.contact_id.email
    #         if not recipient_email:
    #             raise UserError(_("The Contact does not have a valid email address."))
    #
    #         current_user_email = record.env.user.email
    #         if not current_user_email:
    #             raise UserError(_("The current user does not have a valid email address."))
    #
    #         attachment_ids = []
    #         if record.submitted_file:
    #             employee_name = record.employee_id.name if record.employee_id else "Unknown Employee"
    #             current_datetime = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    #
    #             attachment = self.env['ir.attachment'].create({
    #                 'name': f'{employee_name}_EBP_Claim_Form_{current_datetime}',
    #                 'type': 'binary',
    #                 'datas': record.submitted_file,
    #                 'mimetype': 'application/octet-stream',
    #                 'res_model': 'joining.documents',
    #                 'res_id': record.id,
    #             })
    #
    #             attachment_ids = [(4, attachment.id)]
    #         else:
    #             raise UserError("The EBP Claim form is missing. Please attach the form before submitting.")
    #
    #         template_id.send_mail(record.id, force_send=True, email_values={'attachment_ids': attachment_ids})
    #
    #         # record.write({'state': 'mail_sent'})
