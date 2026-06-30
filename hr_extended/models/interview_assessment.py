# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import *
from odoo.exceptions import ValidationError, UserError
from datetime import timedelta, datetime


class InterviewAssessment(models.Model):
    _name = 'interview.assessment'
    _description = 'Interview Assessment'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name of Candidate', required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', '=', (self.env.company.id))])
    user_id = fields.Many2one('res.users', string='User ID', default=lambda self: self.env.user)
    applicant_id = fields.Many2one('hr.applicant', 'Applicant', readonly=False)
    position_interviewed_for = fields.Char(string='Position Interviewed for')
    date_of_interview = fields.Date(string='Date of Interview')
    nature_of_employment = fields.Many2one('hr.contract.type', string='Nature of Employment')
    present_company = fields.Char(string='Present Company')
    present_designation = fields.Char(string='Present Designation')
    total_experience = fields.Float(string='Total Experience (Years)')
    relevant_experience = fields.Float(string='Relevant Experience (Years)')
    education_qualifications = fields.Char(string='Education Qualifications')
    notice_period = fields.Char(string='Notice Period')
    current_ctc = fields.Float(string='Current CTC')
    expected_ctc = fields.Float(string='Expected CTC')
    rating_scale = [('1', 'Poor'), ('2', 'Average'), ('3', 'Good'), ('4', 'Excellent'),
                    ('5', 'Outstanding')]

    education_qualification_skills = fields.Selection(rating_scale, string='Educational Qualification', )
    interpersonal_skills = fields.Selection(rating_scale, string='Interpersonal Skills/Attitude')
    personality = fields.Selection(rating_scale, string='Personality (Individualistic/Team Player)')
    comprehension_analytical_ability = fields.Selection(rating_scale,
                                                        string='Comprehension, Analytical & Mental Ability')
    relevance_of_experience = fields.Selection(rating_scale, string='Relevance of Previous Experience')
    job_product_technical_knowledge = fields.Selection(rating_scale, string='Job/Product/Technical Knowledge')

    functional_comments = fields.Text(string="Functional Interviewer's Comments")
    hr_comments = fields.Text(string="HR Interviewer's Comments")

    interview_result = fields.Selection(
        [
            ('selected', 'Select'),
            ('rejected', 'Reject'),
            ('on_hold', 'On Hold')
        ],
        string='Interview Result / Feedback',
        required=True,
        default='selected',
    )

    position_offered = fields.Many2one('hr.job', string='Designation / Position to be Offered')
    division = fields.Char(string='Division / Business Unit')
    grade_level = fields.Char(string='Grade / Level')
    ctc_recommended = fields.Float(string='CTC Recommended')
    expected_date_of_joining = fields.Date(string='Expected Date of Joining')

    panel_comments_ids = fields.One2many(
        'interview.panel.comments',
        'interview_assessment_id',
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('done', 'Done'), ], default='draft', string='Status')
    start_time = fields.Datetime(string="Start Time")
    end_time = fields.Datetime(string="End Time")
    adjusted_time_start = fields.Datetime('Adjusted Time Start', compute='_compute_adjusted_time')
    adjusted_time_end = fields.Datetime('Adjusted Time End', compute='_compute_adjusted_time')
    applicant_original_ids = fields.Many2many('hr.applicant',
                                              compute='_compute_applicant_record',
                                              string='Applicant', copy=False)
    applicant_original_count = fields.Integer("Applicant",
                                              compute='_compute_applicant_record', default=0, copy=False)

    def _compute_applicant_record(self):
        for record in self:
            domain = [('id', '=', record.applicant_id.id)]
            applicant_original_ids = self.env['hr.applicant'].sudo().search(domain)
            record.applicant_original_ids = applicant_original_ids
            record.applicant_original_count = len(applicant_original_ids)

    def action_open_applicant_record(self):
        action = self.env.ref('hr_recruitment.crm_case_categ0_act_job')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.applicant_original_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.applicant_original_ids.ids)) + "])]"
        elif len(self.applicant_original_ids.ids) == 1:
            res = self.env.ref('hr_recruitment.hr_applicant_view_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.applicant_original_ids.ids and self.applicant_original_ids.ids[0] or False
        return result

    @api.onchange('start_time', 'end_time')
    def _compute_adjusted_time(self):
        for record in self:
            if record.start_time and record.end_time:
                record.adjusted_time_start = record.start_time + timedelta(hours=5, minutes=30)
                record.adjusted_time_end = record.end_time + timedelta(hours=5, minutes=30)
            else:
                record.adjusted_time_start = False
                record.adjusted_time_end = False

    def action_submit(self):
        for record in self:
            if not record.start_time or not record.end_time:
                raise UserError(_("Start Time and End Time are required to submit."))
            record.state = 'done'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    def unlink(self):
        for record in self:
            if record.state == 'done':
                raise UserError(_("Only records in the 'Draft' state can be deleted."))
        return super().unlink()


class InterviewPanelComments(models.Model):
    _name = 'interview.panel.comments'
    _description = 'Interview Panel Comments'

    interview_assessment_id = fields.Many2one(
        'interview.assessment',
        string='Interview Assessment',
        ondelete='cascade',
    )
    panel_member_name = fields.Many2one('hr.employee', string='Name of Panel Member')
    panel_member_department = fields.Many2one('hr.department', string='Department')
    panel_member_designation = fields.Many2one('hr.job', string='Job Position')
    final_comments = fields.Text(string='Final Comments')

    @api.onchange('panel_member_name')
    def _onchange_panel_member_name(self):
        if self.panel_member_name:
            self.panel_member_department = self.panel_member_name.department_id
            self.panel_member_designation = self.panel_member_name.job_id
        else:
            self.panel_member_department = False
            self.panel_member_designation = False
