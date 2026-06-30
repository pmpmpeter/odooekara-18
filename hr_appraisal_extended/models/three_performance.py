from odoo import models, fields, api, _
from odoo.exceptions import *
from datetime import datetime

import pytz


class ThreePerformanceReviewLine(models.Model):
    _name = 'threeperformance.review.line'
    _description = '360 Performance Review Line'
    _inherit = ['mail.thread', 'mail.activity.mixin']


    review_id = fields.Many2one('threeperformance.review', string="Performance Review", required=True,
                                ondelete="cascade")
    config_id = fields.Many2one('performance.config', string="Name", required=True)
    review_type = fields.Selection([
        ('communication', 'Communication'),
        ('team_working', 'Team Working'),
        ('problem_solving', 'Problem-solving and Decision-Making'),
        ('continuous', 'Continuous Improvement'),
        ('organisation_time', 'Organisation and Time Management'),
        ('customer_focus', 'Customer Focus'),
        ('interpersonal_skills', 'Interpersonal Skills'),
        ('motivation', 'Motivation'),
    ], string="Review Type", compute="_compute_review_type", store=True)
    rating = fields.Selection([
        ('A', 'Excellent'),
        ('B', 'Very capable'),
        ('C', 'Capable'),
        ('D', 'Gets by'),
        ('E', 'Current weakness'),
        ('X', 'Unable to rate')], string="Rating")
    rating_marks = fields.Integer(string="Rating Marks")



    @api.depends('config_id')
    def _compute_review_type(self):
        for record in self:
            record.review_type = record.config_id.review_types if record.config_id else False

    @api.onchange('rating')
    def _onchange_rating(self):
        mapping = {
            'A': 5,
            'B': 4,
            'C': 3,
            'D': 2,
            'E': 1,
            'X': 0,
        }
        for rec in self:
            rec.rating_marks = mapping.get(rec.rating, 0)


class ThreePerformanceReview(models.Model):
    _name = 'threeperformance.review'
    _description = '360 Performance Review'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', string='Who are you leaving feedback for? (Employee Name)',
                                  domain="[('company_id', '=', company_id)]",
                                  required=True)
    job_id = fields.Many2one('hr.job', string='What is their job title:',domain="[('company_id', '=', company_id)]", required=True)
    grade = fields.Char(string="Grade(if applicable):")
    grade_selection = fields.Selection([
        ('spl_grade', 'Spl Grade'),
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
        ('grade_d', 'Grade D'),
        ('grade_e', 'Grade E'),
        ('grade_f', 'Grade F'),
        ('grade_g', 'Grade G'),
    ], default='spl_grade', string="Grade(if applicable):", tracking=True, required=True)
    company_id = fields.Many2one('res.company', string='Company', default=lambda self: self.env.company, domain=lambda self: [('id', '=', (self.env.company.id))])

    review_submitted_by = fields.Many2one('hr.employee',domain="[('company_id', '=', company_id)]", string="Review Submitted By")
    review_designation = fields.Many2one('hr.job',domain="[('company_id', '=', company_id)]", string="Reviewer Designation")
    review_department = fields.Many2one('hr.department',domain="[('company_id', '=', company_id)]", string="Reviewer Department")
    review_bu_ids = fields.Many2many('hr.employee',domain="[('company_id', '=', company_id)]", string="Reviewer BU")
    review_date_time = fields.Datetime(string="Review Date and Time", readonly=True, copy=False)
    review_date_time_prob = fields.Datetime(help="Just storing to show them in pdf and excel", copy=False)
    # review_type = fields.Selection(related='review_line_ids.config_id.review_types', string="Review Type", store=True)
    missing_reviews = fields.Char(string="Missing Reviews", compute='_compute_missing_reviews')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
    ], string="Status", default='draft', tracking=True)
    review_type = fields.Selection([
        ('communication', 'Communication'),
        ('team_working', 'Team Working'),
        ('problem_solving', 'Problem-solving and Decision-Making'),
        ('continuous', 'Continuous Improvement'),
        ('organisation_time', 'Organisation and Time Management'),
        ('customer_focus', 'Customer Focus'),
        ('interpersonal_skills', 'Interpersonal Skills'),
        ('motivation', 'Motivation'),
    ], string="Review Type")

    review_line_ids = fields.One2many('threeperformance.review.line', 'review_id', string="Review Lines")
    line_created = fields.Boolean(string="Lines Created", default=False, copy=False)

    review_line_ids_communication = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_communication', store=False
    )

    review_line_ids_team_working = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_team_working', store=False
    )
    review_line_ids_problem_solving = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_problem_solving', store=False
    )
    review_line_ids_continuous = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_continuous', store=False
    )
    review_line_ids_organisation_time = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_organisation_time', store=False
    )
    review_line_ids_customer_focus = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_customer_focus', store=False
    )
    review_line_ids_interpersonal_skills = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_interpersonal_skills', store=False
    )
    review_line_ids_motivation = fields.One2many(
        'threeperformance.review.line', 'review_id', string="Communication Review Lines",
        compute='_compute_review_line_ids_motivation', store=False
    )

    communication_complete = fields.Boolean(
        string="Communication Complete", compute='_compute_section_complete', store=False)
    team_working_complete = fields.Boolean(
        string="Team Working Complete", compute='_compute_section_complete', store=False)
    problem_solving_complete = fields.Boolean(
        string="Problem Solving Complete", compute='_compute_section_complete', store=False)
    continuous_improvement_complete = fields.Boolean(
        string="Continuous Improvement Complete", compute='_compute_section_complete', store=False)
    organisation_time_complete = fields.Boolean(
        string="Organisation and Time Management Complete", compute='_compute_section_complete', store=False)
    customer_focus_complete = fields.Boolean(
        string="Customer Focus Complete", compute='_compute_section_complete', store=False)
    interpersonal_skills_complete = fields.Boolean(
        string="Interpersonal Skills Complete", compute='_compute_section_complete', store=False)
    motivation_complete = fields.Boolean(
        string="Motivation Complete", compute='_compute_section_complete', store=False)
    emp_category = fields.Selection(
        [
            ('self', 'SELF'),
            ('peer', 'PEER'),
            ('subordinate', 'SUBORDINATE'),
            ('supervisor', 'SUPERVISOR'),
        ],
        string="Category",
    )


    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.job_id = record.sudo().employee_id.job_id
                record.grade = record.employee_id.contract_id.sudo().grade

    @api.onchange('review_submitted_by')
    def _onchange_review_submitted_by(self):
        for record in self:
            if record.review_submitted_by:
                record.review_designation = record.sudo().review_submitted_by.job_id
                record.review_department = record.sudo().review_submitted_by.department_id

    @api.depends('review_line_ids.rating')
    def _compute_section_complete(self):
        for record in self:
            record.communication_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'communication')

            record.team_working_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'team_working')

            record.problem_solving_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'problem_solving')

            record.continuous_improvement_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'continuous')

            record.organisation_time_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'organisation_time')

            record.customer_focus_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'customer_focus')

            record.interpersonal_skills_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'interpersonal_skills')

            record.motivation_complete = all(
                line.rating for line in record.review_line_ids if line.review_type == 'motivation')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_communication(self):
        for record in self:
            record.review_line_ids_communication = record.review_line_ids.filtered(
                lambda line: line.review_type == 'communication')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_team_working(self):
        for record in self:
            record.review_line_ids_team_working = record.review_line_ids.filtered(
                lambda line: line.review_type == 'team_working')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_problem_solving(self):
        for record in self:
            record.review_line_ids_problem_solving = record.review_line_ids.filtered(
                lambda line: line.review_type == 'problem_solving')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_continuous(self):
        for record in self:
            record.review_line_ids_continuous = record.review_line_ids.filtered(
                lambda line: line.review_type == 'continuous')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_organisation_time(self):
        for record in self:
            record.review_line_ids_organisation_time = record.review_line_ids.filtered(
                lambda line: line.review_type == 'organisation_time')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_customer_focus(self):
        for record in self:
            record.review_line_ids_customer_focus = record.review_line_ids.filtered(
                lambda line: line.review_type == 'customer_focus')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_interpersonal_skills(self):
        for record in self:
            record.review_line_ids_interpersonal_skills = record.review_line_ids.filtered(
                lambda line: line.review_type == 'interpersonal_skills')

    @api.depends('review_line_ids')
    def _compute_review_line_ids_motivation(self):
        for record in self:
            record.review_line_ids_motivation = record.review_line_ids.filtered(
                lambda line: line.review_type == 'motivation')

    def action_generate_review_lines(self):
        """Generate review lines and mark as created."""
        self.ensure_one()
        if not self.line_created:
            configs = self.env['performance.config'].search([('active', '=', True)], order='sequence')

            review_lines = [(0, 0, {'config_id': config.id}) for config in configs]
            self.write({
                'review_line_ids': review_lines,
                'line_created': True
            })

    @api.depends('review_line_ids.rating')
    def _compute_missing_reviews(self):
        for record in self:
            missing = set()
            for line in record.review_line_ids:
                if not line.rating:  # If rating is not filled
                    missing.add(line.review_type)  # Add the review_type to the missing list
            if missing:
                missing_labels = [dict(record._fields['review_type'].selection).get(review_type, review_type) for review_type in missing]
                record.missing_reviews = ', '.join(missing_labels)

    def action_submit(self):
        for record in self:
            review_ids = self.env['threeperformance.review.line'].search([('review_id','=',self.id)])
            for line in review_ids:
                line._onchange_rating()
            if any(not line.rating for line in record.review_line_ids):
                raise UserError(f"Please fill in the rating for all review lines in {record.missing_reviews} before proceeding.")

            for review_bu_id in record.review_bu_ids:
                if not review_bu_id.work_email:
                    raise UserError(f"The reviewer {review_bu_id.name} doesn't have an email address.")

            template = self.env.ref('hr_appraisal_extended.mail_three60_performance_reviewer')
            if not template:
                raise UserError("Email template not found. Please check the template configuration.")

            for reviewer in record.review_bu_ids:
                self.env['mail.template'].browse(template.id).send_mail(
                    record.id,
                    email_values={'email_to': reviewer.work_email},
                    force_send=True
                )

            record.write({'state': 'in_progress'})

    def action_mark_completed(self):
        for record in self:
            utc_time = datetime.now(pytz.utc)
            india_time = utc_time.astimezone(pytz.timezone('Asia/Kolkata'))
            india_time_naive = india_time.replace(tzinfo=None)
            record.review_date_time_prob = india_time_naive
            record.write({
                'state': 'completed',
                'review_date_time': datetime.now()
            })

    def action_set_to_drat(self):
        for record in self:
            record.write({'state': 'draft'})
