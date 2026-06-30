from odoo import models, fields, api, _
from odoo.exceptions import *


class ExitInterview(models.Model):
    _name = 'exit.interview'
    _description = 'Exit Interview'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'


    employee_id = fields.Many2one('hr.employee',string='Employee Name',domain="[('company_id', '=', company_id)]", required=True, tracking=True, )
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, domain=lambda self: [('id', '=', (self.env.company.id))])
    department_id = fields.Many2one('hr.department', string="Department", readonly=True,
                                    related='employee_id.department_id',
                                    domain="[('company_id', '=', company_id)]",
                                    help='Department of the employee')
    date_of_joining = fields.Date(string='Date of Joining', tracking=True)
    email = fields.Char(string="Personal Email ID")
    mobile = fields.Char(string="Mobile")
    employee_code = fields.Char(string="Employee Code")
    designation_id = fields.Many2one('hr.job',domain="[('company_id', '=', company_id)]",string="Designation",tracking=True)
    date_of_exit = fields.Date(string='Date of Exit', tracking=True)
    reason_for_separation = fields.Selection([
        ('better_compensation', 'Better Compensation'),
        ('supervisors', 'Supervisors'),
        ('less_travel', 'Less travel to work'),
        ('work_conditions', 'Hours of work, shift duties, etc. (Working Conditions)'),
        ('better_environment', 'Better working Environment'),
        ('going_abroad', 'Going abroad'),
        ('dissatisfied_job', 'Dissatisfied with job content Responsibilities'),
        ('marriage_home', 'Marriage/Home'),
        ('location', 'Location'),
        ('dissatisfied_position', 'Dissatisfied with position'),
        ('higher_education', 'Higher education'),
        ('any_other', 'Any Other reason'),
    ], string="Reason for Separation", required=True, tracking=True)

    please_specify = fields.Char(string="Please Specify", tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Submitted'),
        ('completed', 'Completed'),
    ], string='Status', default='draft', tracking=True)

    reason_for_looking_job = fields.Text(
        string='Reason for looking for a Job Outside')

    inform_manager = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True, string='Did you inform your superior/HR Manager that you were planning to leave?', default='yes')
    inform_manager_reason = fields.Text(string="Response", help="If yes, what was the response?")
    retain_effort = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True, string='Did they make any efforts to retain you? ', default='yes')
    retain_effort_response = fields.Text(string="Response", help="If yes, what was the response?")

    company_policies_explained = fields.Text(string="Company Policies")
    rules_regulations_explained = fields.Text(string="Rules & Regulations")
    entitlements_benefits_explained = fields.Text(string="Entitlements & Benefits")
    nature_of_work_explained = fields.Text(string="Nature of Work")
    work_like = fields.Text(string="Work Feedback")
    career_progress_feedback = fields.Text(string="Career Progress")
    training_development_feedback = fields.Text(string="Training Feedback")
    compensation_policy_feedback = fields.Text(string="Compensation Feedback")
    hr_policies_feedback = fields.Text(string="HR Policies Feedback")
    suggestions_work_improvement = fields.Text(string="Work Suggestions")
    suggestions_training_improvement = fields.Text(string="Training Suggestions")
    suggestions_hr_improvement = fields.Text(string="HR Suggestions")
    working_environment_company = fields.Text(string="Company Environment")
    working_environment_department = fields.Text(string="Department Environment")
    communication_feedback = fields.Text(string="Communication Feedback")
    approachability_feedback = fields.Text(string="Approachability Feedback")
    superior_feedback = fields.Text(string="Superior Feedback")
    colleagues_feedback = fields.Text(string="Colleagues Feedback")
    colleagues_improvement = fields.Text(string="Any improvement?")
    coordination_feedback = fields.Text(string="Coordination Feedback")
    welfare_activities_feedback = fields.Text(string="Welfare Feedback")
    staff_facilities_feedback = fields.Text(string="Staff Facilities Feedback")
    suggestions = fields.Text(string="Suggestions")
    general_suggestions = fields.Text(string="General Suggestions")
    new_employment_organization = fields.Char(string="New Organization")
    new_employment_designation = fields.Char(string="New Designation")
    new_employment_compensation_monthly = fields.Float(string="Monthly Compensation")
    new_employment_compensation_annual = fields.Float(string="Annual Compensation")
    new_employment_working_conditions = fields.Text(string="Working Conditions")
    other_details = fields.Text(string="Other Details")
    signature_employee = fields.Many2one('hr.employee', domain="[('company_id', '=', company_id)]", string="Signature of Employee")
    conducted_by = fields.Char(string="Exit Interview Conducted By")
    conducted_by_signature = fields.Many2one('hr.employee',domain="[('company_id', '=', company_id)]", string="Exit Interview Conducted Signature")
    interview_date = fields.Date(string="Date ")
    supervisor_response = fields.Text(string="Supervisor's Response")
    hod_comments = fields.Text(string="H.O.D. Comments")
    hod_signature = fields.Many2one('hr.employee',domain="[('company_id', '=', company_id)]", string="H.O.D Signature")
    gm_comments = fields.Text(string="GM/BU Head Comments")
    gm_signature = fields.Many2one('hr.employee',domain="[('company_id', '=', company_id)]", string="GM/BU Head Signature")
    hr_received_date = fields.Date(string="Received by HRD (Date)")
    hr_signature = fields.Many2one('hr.employee',domain="[('company_id', '=', company_id)]", string="HR Responsible Signature")


    def exit_interview_submit(self):
        for record in self:
            record.state = 'submitted'

    def exit_interview_draft(self):
        for record in self:
            record.state = 'draft'

    def exit_interview_complete(self):
        for record in self:
            record.state = 'completed'

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.date_of_joining = record.sudo().employee_id.joining_date
                record.designation_id = record.sudo().employee_id.job_id
                record.date_of_exit = record.sudo().employee_id.resign_date
                record.email = record.sudo().employee_id.private_email
                record.mobile = record.sudo().employee_id.private_phone

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Only records in the 'Draft' state can be deleted."))
        return super(ExitInterview, self).unlink()
