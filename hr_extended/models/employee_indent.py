# -*- coding: utf-8 -*-
import base64

from odoo import models, fields, api, _
from odoo.exceptions import *
from datetime import datetime, timedelta, date
from odoo.exceptions import ValidationError, UserError
from lxml import etree


class EmployeeIndent(models.Model):
    _name = 'employee.indent'
    _description = 'Employee Indent'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    @api.depends('department', 'grade_job_level', 'position_name')
    def _compute_approved_budget(self):
        today = date.today()
        if today.month >= 4:  # Financial year starts from April
            start_of_financial_year = date(today.year, 4, 1)
            end_of_financial_year = date(today.year + 1, 3, 31)
        else:
            start_of_financial_year = date(today.year - 1, 4, 1)
            end_of_financial_year = date(today.year, 3, 31)
        for rec in self:
            rec.approved_budget = self.env['manpower.budget'].search([
                ('state', '=', 'done'),
                ('create_date', '>=', start_of_financial_year),
                ('create_date', '<=', end_of_financial_year),
                ('department_id', '=', rec.department.id),
                ('job_level_id', '=', rec.grade_job_level.id),
                ('position_id', '=', rec.position_name.id),
            ], limit=1).ctc_annual or 0

    name = fields.Char(string='Name', required=True)
    tax_entity = fields.Many2one('res.company', string='Tax Entity', default=lambda self: self.env.company)
    organization = fields.Many2one('res.company', string='Organization', default=lambda self: self.env.company,
                                   domain=lambda self: self._organization_domain())
    # company_id = fields.Many2one('res.company', string='Company ID', default=lambda self: self.env.company)
    user_id = fields.Many2one('res.users', string='User ID', default=lambda self: self.env.user)
    # location = fields.Many2one(
    #     'res.partner', "Job Location", copy=False
    #     domain=lambda self: self._address_id_domain(),
    #     help="Select the location where the applicant will work. Addresses listed here are defined on the company's contact information.")
    # location_id = fields.Many2one('ekara.location', string="Location", copy=False)
    locations_id = fields.Many2one('location.master', domain="[('company_id', '=', organization)]", string="Location")

    department = fields.Many2one(
        'hr.department',  # The model name of the HR department
        string='Department',
        required=True,
        domain="[('company_id', '=', organization)]",
        help="Select the department from HR departments"
    )

    grade_job_level = fields.Many2one('hr.job.levels', string='Grade/ Job Level',
                                      domain="[('company_id', '=', organization)]", required=True)

    position_name = fields.Many2one('hr.position.names', string='Position Name / Designations',
                                    domain="[('company_id', '=', organization)]", required=True)

    reporting_to = fields.Many2one(
        'res.users',
        string='Reporting To',
        help='Select the employee to whom this position reports.'
    )

    employment_type = fields.Many2one('hr.contract.type', string="Employment Type")

    target = fields.Integer(string='No. of Vacancies', required=True, default=1,
                            help="Number of vacancies for this position.")

    is_replacement = fields.Boolean(string='Is Replacement?', default=False, copy=False,
                                    help="Indicate if this position is a replacement.")

    replacement_employee_id = fields.Many2one(
        'hr.employee',
        domain="[('company_id', '=', organization)]",
        string='Replacement Employee Name',
        help='Select the employee being replaced if this is a replacement position.'
    )

    expected_indent_closure_date = fields.Date(
        string='Expected Indent Closure Date',
        required=True,
        default=lambda self: self._default_expected_closure_date(),
        help='Select the expected date for closing this indent.'
    )

    is_recruitment_manager = fields.Boolean(
        string="Is Recruitment Manager",
        compute="_compute_is_recruitment_manager",
        store=False
    )

    budgeting_unit = fields.Selection([
        ('ekara_capex', 'Ekara Partnership - Capex'),
        ('ekara_opex', 'Ekara Partnership - Opex'),
        ('statutory_payments', 'Statutory Payments & Other B/S Items')
    ], string='Budgeting Units', help="Select the appropriate budgeting unit.")

    budgeting_unit_id = fields.Many2one('budgeting.units', string='Budgeting Units',
                                        domain="[('company_id', '=', organization)]",
                                        help="Select the appropriate budgeting unit.")

    is_budgeted = fields.Boolean(string='Is Budgeted?', default=False, copy=False,
                                 help="Indicate if this position is budgeted.")

    # have to add the BU/Department Total Approved Budget (dont know about that)
    start_date = fields.Date(string='Fiscal Year', default=fields.Date.today, copy=False)
    end_date = fields.Date(string='End Date', copy=False)

    approved_budget = fields.Monetary(
        string='BU/Department Total Approved Budget',
        compute='_compute_approved_budget',
        currency_field='currency_id',
        help="Specify the total approved budget for the Business Unit (BU) or Department.", copy=False
    )

    budgeted_amount = fields.Monetary(
        string='Budgeted Amount for Position',
        currency_field='currency_id',
        help="Specify the budgeted amount for this position.", copy=False
    )

    utilized_budget = fields.Monetary(
        string='Utilized Budget',
        currency_field='currency_id',
        help="Amount already utilized from the budget for this position.", copy=False
    )

    balance_budget = fields.Monetary(
        string='Balance Budget',
        compute='_compute_balance_budget',
        currency_field='currency_id',
        store=True,
        help="Remaining budget after utilization.", copy=False
    )
    proposed_annual_ctc = fields.Float(string='Proposed Annual CTC')

    currency_id = fields.Many2one(
        'res.currency',
        string='Currency',
        default=lambda self: self.env.company.currency_id,
        help="Currency for the budget amounts."
    )

    unit_head_id = fields.Many2one(
        'res.users',
        string='1st approval / HOD', required=True,
        help="Select the Unit Head from available employees."
    )

    recruitment_spoc_mgr_id = fields.Many2one(
        'res.users',
        string='2nd approval / Recruitment SPOC/ Mgr', required=True,
        help="Select the Recruitment SPOC/Mgr from available employees."
    )

    director_approval_id = fields.Many2one(
        'res.users',
        string='3rd approval / Director', required=True,
        help="Select the Director for approval."
    )

    preferences = fields.Text(
        string='Preferences',
        help="Enter any specific preferences related to the indent."
    )

    notes = fields.Text(
        string='Notes',
        help="Add any relevant notes or comments here."
    )

    document_id = fields.Many2one('documents.document', string="Document", copy=False)

    request_date = fields.Date(default=fields.Datetime.now, copy=False, readonly=True)
    submit_date = fields.Date(readonly=True, copy=False)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('waiting_approval', 'Waiting for Approval'),
        ('open', 'Open'),
        ('job_created', 'Job Position Created'),
        ('cancel', 'Cancelled')
    ], string='Status', default='draft', required=True, tracking=True, copy=False)

    # Job Description template details

    # business_unit = fields.Char(string="Business Unit")
    business_unit_id = fields.Many2one('business.units', domain="[('company_id', '=', organization)]",
                                       string="Business Units", required=True)
    # source = fields.Selection([
    #     ('new_role', 'New Role'),
    #     ('replacement', 'Replacement')
    # ], string="Source")
    priority = fields.Selection([
        ("1", "Medium"),
        ("2", "High"),
        ("3", "Very High")], string="Priority", copy=False)
    no_of_vacancy = fields.Integer(string="Number of Vacancies",
                                   help="The Target in general Info and this field are same")
    purpose_of_job = fields.Text(string="Purpose of the Job")
    job_description = fields.Text(string="Job Description")
    technical_qualification = fields.Text(string="Technical Qualification")
    work_experience = fields.Text(string="Essential Years of Work Experience and Qualification")
    industry_preferences = fields.Text(string="Industry Preferences")
    mandatory_skills = fields.Text(string="Mandatory Skills/Competencies")
    job_responsibility = fields.Text(string="Job Responsibility")
    professional_requirements = fields.Text(string="Professional Requirements")
    educational_requirements = fields.Text(string="Educational and Experience Requirements")
    desirable = fields.Text(string="Desirable")
    approved_by_hod_id = fields.Many2one('hr.employee', domain="[('company_id', '=', organization)]",
                                         string="Approved by (HOD)")
    approved_by_director_id = fields.Many2one('hr.employee', domain="[('company_id', '=', organization)]",
                                              string="Approved by (Director)")
    job_id = fields.Many2one('hr.job', domain="[('company_id', '=', organization)]", string="Job Position")
    approved_by_hod = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Approved by (HOD)', required=True, default='no', copy=False)
    approved_by_director = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No')
    ], string='Approved by (Director)', required=True, default='no', copy=False)
    kra_document = fields.Binary(string="KRA Document")
    kra_document_filename = fields.Char(string="File Name")
    x_review_result = fields.Char(string="Review Result")

    def _organization_domain(self):
        return [('id', '=', self.env.companies.ids)]

    @api.onchange('proposed_annual_ctc', 'approved_budget')
    def _onchange_proposed_annual_ctc(self):
        for rec in self:
            rec.utilized_budget = (rec.approved_budget - rec.proposed_annual_ctc)

    @api.onchange('business_unit_id')
    def _onchange_business_unit_id(self):
        """Set tax_entity based on the selected business_unit_id."""
        for rec in self:
            if rec.business_unit_id:
                rec.tax_entity = rec.business_unit_id.tax_entity
            else:
                rec.tax_entity = False

    # to check the fields values are active
    def write(self, vals):
        for record in self:
            position_id = vals.get('position_name', record.position_name.id)
            if position_id:
                position = self.env['hr.position.names'].browse(position_id)
                if not position.active:
                    raise ValidationError(
                        "The selected Position Name/Designation is not active. Please choose an active position."
                    )

            location_id = vals.get('locations_id', record.locations_id.id)
            if location_id:
                location = self.env['location.master'].browse(location_id)
                if not location.active:
                    raise ValidationError(
                        "The selected Location is not active. Please choose an active location."
                    )

            grade_id = vals.get('grade_job_level', record.grade_job_level.id)
            if grade_id:
                grade = self.env['hr.job.levels'].browse(grade_id)
                if not grade.active:
                    raise ValidationError(
                        "The selected Grade/Job Level is not active. Please choose an active grade."
                    )

            bu_unit_id = vals.get('business_unit_id', record.business_unit_id.id)
            if grade_id:
                grade = self.env['business.units'].browse(bu_unit_id)
                if not grade.active:
                    raise ValidationError(
                        "The selected Business Unit is not active. Please choose an active business unit."
                    )

        return super(EmployeeIndent, self).write(vals)

    # @api.onchange('target')
    # def _number_of_vacancy(self):
    #     for record in self:
    #         record.no_of_vacancy = record.target

    @api.constrains('target')
    def _validate_negative(self):
        for record in self:
            if record.target <= 0:
                raise UserError(_("Please give the positive values in No. of Vacancies"))

    @api.constrains('is_replacement')
    def _is_replacement_or_not(self):
        for record in self:
            if record.is_replacement and not record.replacement_employee_id:
                raise UserError(_("Please select the Replacement Employee Name"))
            if not record.is_replacement:
                record.replacement_employee_id = ''

    @api.model
    def _default_expected_closure_date(self):
        request_date = fields.Date.context_today(self)
        return request_date + timedelta(days=120)

    @api.depends('expected_indent_closure_date')
    def _compute_is_recruitment_manager(self):
        for record in self:
            record.is_recruitment_manager = self.env.user.has_group('hr_recruitment.group_hr_recruitment_manager')

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError(
                    _("You can only delete records in the 'Draft' state.")
                )
        return super(EmployeeIndent, self).unlink()

    def action_open_related_jobs(self):
        self.ensure_one()  # Ensure it's called for one record
        return {
            'name': 'Related Jobs',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'hr.job',
            'view_id': self.env.ref('hr.view_hr_job_form').id,
            'res_id': self.job_id.id,
            'target': 'current',
        }

    def _address_id_domain(self):
        return ['|', '&', '&', ('type', '!=', 'contact'), ('type', '!=', 'private'),
                ('id', 'in', self.sudo().env.companies.partner_id.child_ids.ids),
                ('id', 'in', self.sudo().env.companies.partner_id.ids)]

    @api.constrains('budgeted_amount', 'utilized_budget', 'approved_budget')
    def _check_budget(self):
        for record in self:
            if record.utilized_budget > record.approved_budget:
                raise ValidationError("The utilized amount exceeds the approved budget!")

    @api.depends('approved_budget', 'budgeted_amount', 'utilized_budget')
    def _compute_balance_budget(self):
        for record in self:
            record.balance_budget = record.approved_budget - record.utilized_budget

    def action_approve(self):
        # To make the reapprove functionality and then stop raising error if multi approval not installed
        if hasattr(self, 'x_has_request_approval'):
            self.x_has_request_approval = False

        for record in self:
            unit_head_user = record.unit_head_id.id
            recruitment_spoc_mgr_user = record.recruitment_spoc_mgr_id.id
            director_approval_user = record.director_approval_id.id

            if not unit_head_user:
                raise UserError("Recruitment SPOC Manager does not have a corresponding user.")

            if not recruitment_spoc_mgr_user:
                raise UserError("Recruitment SPOC Manager does not have a corresponding user.")

            if not director_approval_user:
                raise UserError("Director Approval does not have a corresponding user.")

            record.submit_date = fields.Datetime.now()
            record.state = 'waiting_approval'

            # # passing two level approvers from employee.indent others(>2) are static
            # approval_type_model = self.env['multi.approval.type']
            # approval_type_line_model = self.env['multi.approval.type.line']
            #
            # for record in self:
            #     approval_type = approval_type_model.search([
            #         ('model_id', '=', 'employee.indent'),
            #         ('domain', 'ilike', '"state"')
            #     ], limit=1)
            #
            #     # if not approval_type:
            #     #     raise ValueError("No matching approval type found for the Employee Indent.")
            #     if approval_type and approval_type.state == 'confirm':
            #         lines = approval_type_line_model.search([('type_id', '=', approval_type.id)], limit=2)
            #
            #         while len(lines) < 2:
            #             # Create missing lines
            #             new_line = approval_type_line_model.create({
            #                 'type_id': approval_type.id,
            #                 'name': f"L{len(lines) + 1}",
            #                 'sequence': len(lines) + 1,  # Assign a sequence for clarity
            #             })
            #             lines += new_line
            #
            #         # if len(lines) != 2:
            #         #     raise ValueError(
            #         #         "There must be exactly two records in 'multi.approval.type.line' with the same 'type_id'.")
            #
            #         for index, line in enumerate(lines):
            #             line.write({
            #                 'user_id': [(6, 0, [])]
            #             })
            #             if index == 0:
            #                 unit_head_user = record.unit_head_id.id
            #                 recruitment_spoc_mgr_user = record.recruitment_spoc_mgr_id.id
            #
            #                 if unit_head_user and recruitment_spoc_mgr_user:
            #                     line.write({
            #                         'user_id': [(4, unit_head_user), (4, recruitment_spoc_mgr_user)]
            #                     })
            #                 else:
            #                     raise ValueError(
            #                         "Unit Head or Recruitment SPOC Manager does not have a corresponding user.")
            #                 print(f"Line ID: {line.id}, Updated User IDs: {line.user_id}")
            #
            #             elif index == 1:
            #                 director_approval_user = record.director_approval_id.id
            #
            #                 if director_approval_user:
            #                     line.write({
            #                         'user_id': [(4, director_approval_user)]
            #                     })
            #                 else:
            #                     raise ValueError("Director Approval does not have a corresponding user.")
            #                 print(f"Line ID: {line.id}, Updated User IDs: {line.user_id}")
            #
            #         record.state = 'waiting_approval'
            #         record.submit_date = fields.Datetime.now()
            #
            #     else:
            #         record.state = 'waiting_approval'
            #         record.submit_date = fields.Datetime.now()

        # else:
        #     for record in self:
        #         record.state = 'waiting_approval'
        #         record.submit_date = fields.Datetime.now()

    def action_open(self):
        for record in self:
            record.state = 'open'

    def action_create_job_position(self):
        hr_job_model = self.env['hr.job']
        for record in self:
            existing_job = hr_job_model.search(
                [('name', '=', record.position_name.name), ('company_id', '=', record.organization.id)], limit=1)

            if existing_job:
                existing_job.sudo().write({
                    'no_of_recruitment': existing_job.no_of_recruitment + record.target,
                    'website_published': True,
                })

            else:
                job_id = hr_job_model.sudo().create({
                    'name': record.position_name.name,
                    'department_id': record.department.id,
                    'address_id': record.organization.partner_id.id,
                    'contract_type_id': record.employment_type.id,
                    'company_id': record.organization.id,
                    'no_of_recruitment': record.target,
                    'user_id': record.reporting_to.id,
                    'website_published': True,
                })
            record.job_id = existing_job.id or job_id.id

            # To store the job description in documents
            report_action = self.env.ref('hr_extended.action_employee_indent_report')
            if not report_action:
                raise ValueError("Report action 'hr_extended.action_employee_indent_report' not found.")

            pdf_content = self.env['ir.actions.report'].sudo()._render_qweb_pdf(
                report_action, [record.id], data=None)[0]
            if not pdf_content:
                raise ValueError("hai")

            pdf_name = f"{record.name}_Job_Description.pdf"

            folder = self.env['documents.folder'].search([('name', '=', 'Job Descriptions')], limit=1)
            if not folder:
                folder = self.env['documents.folder'].create({'name': 'Job Descriptions'})

            attachment = self.env['documents.document'].create({
                'name': pdf_name,
                'type': 'binary',
                'datas': base64.b64encode(pdf_content),
                'mimetype': 'application/pdf',
                'res_model': 'employee.indent',
                'res_id': record.id,
                'folder_id': folder.id,
            })

            record.document_id = attachment.id
            record.state = 'job_created'

    def action_reset(self):
        for record in self:
            record.state = 'draft'

    def action_cancel(self):
        for record in self:
            record.state = 'cancel'

    def action_view_document(self):
        self.ensure_one()

        if not self.document_id:
            raise ValidationError(_("No document is attached to this record."))

        document_folder = self.env['documents.folder'].search([('name', '=', 'Job Descriptions')], limit=1)
        action = self.env['ir.actions.act_window']._for_xml_id('documents.document_action')

        action['context'] = {
            'default_res_id': self.id,
            'default_res_model': 'employee.indent',
            'searchpanel_default_folder_id': document_folder.id if document_folder else False,
        }
        action['domain'] = [('res_id', '=', self.id), ('res_model', '=', 'employee.indent')]

        return action

    def get_indent_url(self):
        """Generate the full URL for the current record."""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        menu = self.env['ir.ui.menu'].search([('name', '=', 'Employee Indent')], limit=1)  # Adjust menu name
        # cant able to use this for normal users (ir.actions.act_window) only accessible by administration/settings
        action = self.env['ir.actions.act_window'].search([('res_model', '=', 'employee.indent')], limit=1)
        menu_id = menu.id if menu else 0
        action_id = action.id if action else 0
        if self:
            return f"{base_url}/web#id={self.id}&cids=1&menu_id={menu_id}&action={action_id}&model=employee.indent&view_type=form"
        return f"{base_url}/web#menu_id={menu_id}&action={action_id}&model=employee.indent&view_type=list"


class DocumentsDocument(models.Model):
    _inherit = 'documents.document'

    def action_archive(self):
        job_description_folder = self.env['documents.folder'].search([('name', '=', 'Job Descriptions')], limit=1)
        if job_description_folder:
            restricted_documents = self.filtered(lambda doc: doc.folder_id == job_description_folder)
            if restricted_documents:
                raise ValidationError(_(
                    "You cannot move the documents to Trash that belong to the 'Job Descriptions' folder."
                ))

        return super(DocumentsDocument, self).action_archive()

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'kanban':
            arch = etree.fromstring(result['arch'])
            print(arch, 'arch\n')
            nodes = arch.xpath("//kanban")
            print(nodes, 'nodes\n')
            if nodes:
                print(self.env.user.name, self.env.user.has_group('hr_extended.group_view_own_document'), 'has group\n')
                if self.env.user.has_group('hr_extended.group_view_own_document'):
                    for node in nodes:
                        node.set("js_class", "")
            result['arch'] = etree.tostring(arch, encoding='unicode')
        return result

    # def _get_view(self, view_id=None, view_type='form', **options):
    #     print('gggggggggggggggggggggggggggggggggggg')
    #     arch, view = super()._get_view(view_id, view_type, **options)
    #     # inject into rendering context
    #     print(view_type, 'view_type\n')
    #     if view_type == 'kanban':
    #         nodes = arch.xpath("//kanban")
    #         print(nodes, 'node\n')
    #         if nodes:
    #             print(self.env.user.name, self.env.user.has_group('hr_extended.group_view_own_document'), 'has group\n')
    #             if self.env.user.has_group('hr_extended.group_view_own_document'):
    #                 for node in nodes:
    #                     node.set("js_class", "")
    #     return arch, view

    # def unlink(self):
    #     for document in self:
    #         if document.res_model == 'employee.indent' and self.env.user.has_group('documents.group_documents_user'):
    #             raise UserError(_("You are not allowed to delete documents linked to Employee Indent."))
    #     return super(DocumentsDocument, self).unlink()
