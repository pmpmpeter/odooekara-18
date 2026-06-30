from odoo import models, fields, api, _
import base64
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from odoo.exceptions import *


class ProbationReviewForm(models.Model):
    _name = 'prob.review.form'
    _description = 'Probation Review Form'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_probation_id = fields.Many2one('employee.probation', string='Employee Probation')

    employee_id = fields.Many2one('hr.employee',string='Employee Name', required=True, tracking=True)
    job_title_id = fields.Many2one('hr.job', string='Job Title', tracking=True,related='employee_id.job_id')
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company, domain=lambda self: [('id', '=', (self.env.company.id))])
    grade = fields.Char(string='Grade', tracking=True)
    department_id = fields.Many2one('hr.department', string='Department / Section', tracking=True)
    date_of_joining = fields.Date(string='Date of Joining', tracking=True)
    reporting_manager_id = fields.Many2one('hr.employee', string='Reporting Manager',
                                        tracking=True)
    reporting_manager_designation_id = fields.Many2one('hr.job',string='Manager Designation',related='reporting_manager_id.job_id', tracking=True)
    three_month_review_due = fields.Date(string='Due Date', tracking=True)
    three_month_review_completed = fields.Date(string='Completed On', tracking=True)
    six_month_review_due = fields.Date(string='Due Date', tracking=True)
    six_month_review_completed = fields.Date(string='Completed On', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('review1_done', 'Initial Review'),
        ('review2_done', 'Final Review'),
        ('done', 'Done'),
        ('cancel','Cancelled'),
    ], string='Status', default='draft', tracking=True)

    REVIEW_RATING_SELECTION = [
        ('improvement_required', 'Improvement required'),
        ('satisfactory', 'Satisfactory'),
        ('good', 'Good'),
        ('excellent', 'Excellent')
    ]

    quality_of_work = fields.Selection(REVIEW_RATING_SELECTION, string='Quality and accuracy of work',
                                       default='satisfactory', required=True, tracking=True)
    efficiency = fields.Selection(REVIEW_RATING_SELECTION, string='Efficiency', default='satisfactory', required=True,
                                  tracking=True)
    attendance = fields.Selection(REVIEW_RATING_SELECTION, string='Attendance', default='satisfactory', required=True,
                                  tracking=True)
    time_keeping = fields.Selection(REVIEW_RATING_SELECTION, string='Time Keeping', default='satisfactory',
                                    required=True,
                                    tracking=True)
    work_relationships = fields.Selection(REVIEW_RATING_SELECTION,
                                          string='Work relationships',
                                          default='satisfactory', required=True, tracking=True)
    competency_in_role = fields.Selection(REVIEW_RATING_SELECTION, string='Competency in the role',
                                          default='satisfactory', required=True, tracking=True)

    performance_improvement_details = fields.Text(
        string='Areas of Performance, Conduct or Attendance Requiring Improvement')
    concerns_addressed_summary = fields.Text(string='How Concerns Will Be Addressed')
    performance_progress_summary = fields.Text(string='Employee Performance and Progress Summary')

    objectives_met = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True, string='Have the objectives identified for the period of the probation been met?', default='yes')

    training_needs_met = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True, string='Have the training / development needs identified for this period of the probation been addressed?',
        default='yes')

    objectives_met_reason = fields.Text(string="Reason for not meeting objectives",
                                        help="Provide details if objectives have not been met")
    objectives_review_date = fields.Date(string='Objectives Review Date', help="Date of review for objectives")
    training_needs_met_reason = fields.Text(string="Reason for not addressing training needs",
                                            help="Provide details if training needs have not been addressed")
    training_review_date = fields.Date(string='Training Review Date', help="Date of review for training needs")
    employee_signature_id = fields.Many2one('hr.employee', string="Employee's Signature")
    manager_signature_id = fields.Many2one('hr.employee', string="Manager's Signature")
    date_part_1 = fields.Date(string="Date")
# FINAL REVIEW
    quality_of_work_fr = fields.Selection(REVIEW_RATING_SELECTION, string='Quality and accuracy of work',
                                       default='satisfactory', required=True, tracking=True)
    efficiency_fr = fields.Selection(REVIEW_RATING_SELECTION, string='Efficiency', default='satisfactory', required=True,
                                  tracking=True)
    attendance_fr = fields.Selection(REVIEW_RATING_SELECTION, string='Attendance', default='satisfactory', required=True,
                                  tracking=True)
    time_keeping_fr = fields.Selection(REVIEW_RATING_SELECTION, string='Time Keeping', default='satisfactory',
                                    required=True,
                                    tracking=True)
    work_relationships_fr = fields.Selection(REVIEW_RATING_SELECTION,
                                          string='Work relationships',
                                          default='satisfactory', required=True, tracking=True)
    competency_in_role_fr = fields.Selection(REVIEW_RATING_SELECTION, string='Competency in the role',
                                          default='satisfactory', required=True, tracking=True)
    objectives_met_fr = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True, string='Have the objectives identified for the probationary period been met?', default='yes')
    objectives_met_reason_fr = fields.Text(string="Reason for not meeting objectives",
                                        help="Provide details if objectives have not been met")
    training_needs_met_fr = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True,
        string='Have the training / development needs identified for the probationary period been addressed?',
        default='yes')
    training_needs_met_reason_fr = fields.Text(string="Reason for not addressing training needs",
                                            help="Provide details if training needs have not been addressed")
    performance_progress_summary_fr = fields.Text(string='Employee Performance and Progress Summary')
    emp_appointment_fr = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True,
        string='Is the employee’s appointment to be confirmed?',
        default='yes')
    emp_appointment_reason_fr = fields.Text(string="Reason for not appointment the employee",
                                           help="Provide details if not appoint the employee")
    employee_comment = fields.Text(string="Employee comments about their experience of the probationary process",
                                           help="Provide details about the employee experience of the probationary process")
    emp_probation_extend = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True,
        string='Is the employee’s probationary period be extended?',
        default='no')
    emp_probation_extend_reason = fields.Text(string="Reason for extend the employee's probation period",
                                   help="Provide details to extend the employee's probation period")
    probation_extend_length_ = fields.Char(string='Length of the extension (max 3 months)')
    completion_date = fields.Date(string="New Probation Period completion date")
    employee_signature_fr_id = fields.Many2one('hr.employee', string="Employee's Signature")
    manager_signature_fr_id = fields.Many2one('hr.employee', string="Manager's Signature")
    date_fr = fields.Date(string="Date")
    confirm_letter = fields.Selection([
        ('yes', 'YES'),
        ('no', 'NO')
    ], required=True,
        string='Is the employee receive the confirm letter?',
        default='no')

    probation_form_ids = fields.Many2many(
        'employee.probation',
        compute='_compute_probation_forms',
        string='Probation Forms',
        copy=False
    )
    probation_form_count = fields.Integer(
        "Probation Form Count",
        compute='_compute_probation_forms',
        default=0,
        copy=False
    )

    def _compute_probation_forms(self):
        for record in self:
            domain = [('review_form_id', '=', record.id)]
            probation_forms = self.env['employee.probation'].sudo().search(domain)
            record.probation_form_ids = probation_forms
            record.probation_form_count = len(probation_forms)

    def action_open_probation_forms(self):
        action = self.env.ref('emp_prob_extended.employee_probation_action')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.probation_form_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.probation_form_ids.ids)) + "])]"
        elif len(self.probation_form_ids.ids) == 1:
            res = self.env.ref('emp_prob_extended.employee_probation_form_view',False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.probation_form_ids.ids and self.probation_form_ids.ids[0] or False
        return result

    def mark_review1_done(self):
        for record in self:
            user = self.reporting_manager_id.user_id
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary="Employee Probation : Final Review",
                note=f"Kindly review the employee probation.",
                user_id=user.id,
                date_deadline=fields.Date.today()
            )
            record.state = 'review1_done'

    def mark_review2_done(self):
        for record in self:
            user = self.reporting_manager_id.user_id
            self.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary="Employee Probation : Mark as Done",
                note=f"Kindly review the employee probation.It is still in Final Review State.Kindly mark it as done.",
                user_id=user.id,
                date_deadline=fields.Date.today()
            )
            record.state = 'review2_done'

    def mark_done(self):
        for record in self:
            record.state = 'done'

    def reset_to_draft(self):
        for record in self:
            record.state = 'draft'
            if record.employee_probation_id:
                record.employee_probation_id.write({'state': 'draft'})

    def mark_cancel(self):
        for record in self:
            record.state = 'cancel'
            if record.employee_probation_id:
                record.employee_probation_id.write({'state': 'cancel'})

    def unlink(self):
        for record in self:
            if record.state != 'draft':
                raise UserError("You can delete a record only in the 'draft' state.")
        return super(ProbationReviewForm, self).unlink()

    def write(self, vals):
        res = super(ProbationReviewForm, self).write(vals)
        if 'state' in vals and self.employee_probation_id:
            if vals['state'] == 'done':
                self.employee_probation_id.write({'state': 'review'})
            # else:
            #     self.employee_probation_id.state = 'draft'
        return res

    def print_employee_probation_review_form(self):
        return self.env.ref('emp_prob_extended.report_probation_review_template').report_action(self.id)

