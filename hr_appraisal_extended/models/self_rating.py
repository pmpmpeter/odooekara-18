from odoo import models, fields, api, _
from odoo.exceptions import *
from odoo.exceptions import ValidationError, UserError
from num2words import num2words
from datetime import timedelta
import math

class PBVPReference(models.Model):
    _name = 'pbvp.reference'
    _description = 'PBVP Reference Table'
    _rec_name = 'score_range'

    score_range = fields.Char(string='Final Score/Rating')
    payout_percentage = fields.Char(string='Applicable PBVP Payout')
    rating_id = fields.Many2one('self.rating', string='Rating Link')



class SelfRating(models.Model):
    _name = 'self.rating'
    _description = 'Self Rating'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'employee_id'

    pbvp_reference_ids = fields.One2many(
        'pbvp.reference',
        'rating_id',
        string='PBVP Reference',
        readonly=True
    )
    employee_id = fields.Many2one('hr.employee', string='Employee', domain="[('company_id', '=', company_id)]",
                                  tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', domain="[('company_id', '=', company_id)]",
                                    tracking=True,
                                    related='employee_id.department_id')
    company_id = fields.Many2one('res.company', required=True, default=lambda self: self.env.company,
                                 domain=lambda self: [('id', '=', (self.env.company.id))])
    date_of_joining = fields.Date(string='Date of Joining', tracking=True, related='employee_id.joining_date')
    designation_id = fields.Many2one('hr.job', string="Designation", domain="[('company_id', '=', company_id)]",
                                     tracking=True)
    job_level = fields.Many2one('hr.job.levels', string="Job Level", domain="[('company_id', '=', company_id)]",
                                     tracking=True)
    reporting_to_id = fields.Many2one('hr.employee', string='Reporting to', tracking=True,
                                      domain="[('company_id', '=', company_id)]",
                                      related='employee_id.parent_id', )
    location = fields.Selection([
        ('corporate', 'Corporate'),
        ('bangalore', 'Bangalore'),
        ('ttc', 'TTC'),
        ('ttk', 'TTK'),
        ('cbm', 'CBM'),
        ('lilac1', 'Lilac 1'),
        ('lilac2', 'Lilac 2'),
        ('tta', 'TTA'),
        ('tvm_obt', 'TVM/OBT'),
    ], default='corporate', string="Location", tracking=True, required=True)
    location_id = fields.Many2one('location.master', domain="[('company_id', '=', company_id)]", string="Location",
                                  required=True)
    is_appraisal_manager = fields.Boolean(string="Is Appraisal Manager", store=False, copy=False)
    appraisal_date = fields.Date(string='Appraisal Date', tracking=True)
    reviewer_id = fields.Many2one('hr.employee', domain="[('company_id', '=', company_id)]", string='Reviewer',
                                  tracking=True)
    state = fields.Selection([
        ('request_appraisal', 'Request Appraisal'),
        ('preparation', 'Preparation'),
        ('preparation_clarification', 'Preparation - In Clarification'),
        ('half_year_pending', 'Half Year Goals Pending'),
        ('half_year_clarification', 'Half Year Goals Clarification'),
        ('full_year_pending', 'Full Year Goals Pending'),
        ('full_year_clarification', 'Full Year Goals Clarification'),
        ('review_completed', 'Review Completed'),
    ], default='request_appraisal', string="Status", tracking=True)
    kra_ids = fields.One2many('self.rating.kra', 'rating_id', string="KRA Details")
    assessment_kra_ids = fields.One2many(
        'self.rating.assessment.kra', 'rating_id', string="Assessment KRA Details"
    )
    appraiser_overall_rating = fields.Float(string="Appraiser’s Overall Rating")
    appraiser_remarks = fields.Text(string="Appraiser’s Remarks")
    employee_signature = fields.Many2one('hr.employee', string="Employee’s Signature")
    reporting_manager_signature = fields.Many2one('hr.employee', string="Reporting Manager’s Signature")
    reviewer_signature = fields.Many2one('hr.employee', string="Reviewer’s Signature")
    development_plan_ids = fields.One2many(
        'self.rating.development.plan', 'rating_id', string="Employee Development Plan"
    )
    employee_signature_dev = fields.Many2one('hr.employee', string="Employee’s Signature")
    reporting_manager_signature_dev = fields.Many2one('hr.employee', string="Reporting Manager’s Signature")
    goal_sets_kras = fields.One2many('performance.review.kra', 'rating_id', string="Goal Sets/KRAs")
    goal_review_comments = fields.One2many('performance.review.comment', 'rating_id', string="Goal Review Comments")
    manager_rating_ids = fields.One2many('manager.rating', 'rating_id', string="Manager Ratings")
    # director_rating_ids = fields.One2many('director.rating', 'rating_id', string="Director Ratings")
    supporting_document = fields.Binary(string="Supporting Document")
    action_needed = fields.Text(string="Action Needed")

    emp_number = fields.Char(string="Employee Number")
    organisation = fields.Char(string="Organisation")
    department = fields.Char(string="Department")
    status = fields.Char(string="Status")
    pending_from_date = fields.Date(string="Pending From Date")
    pending_days = fields.Integer(string="Pending Number of Days")
    total_weightage = fields.Float(string="Total Weightage")
    weightage_avg_achieved = fields.Float(string="Weightage Average Achieved")
    fy_final_rating = fields.Float(string="Final Rating (Out of 5)")
    mgr_recommended_rating = fields.Float(string="Manager Recommended Rating")

    # Fields for Review Completed
    final_rating = fields.Float(string="Final Rating")

    review_line_ids = fields.One2many('performance.review.line', 'review_id', string='Review Details')
    total_score_employee = fields.Float(string='Total', compute='_compute_totals', store=True)

    appraisal_meeting_confirmation = fields.Boolean(string="Meeting Confirmation", default=False, copy=False)
    meeting_date_time = fields.Datetime(string="Meeting Datetime", copy=False)
    total_employee_weighted_score = fields.Float(string='Total Employee Weighted Score', compute='_compute_totals',
                                                 store=True)
    total_score_manager = fields.Float(string='Total', compute='_compute_totals', store=True)
    total_manager_weighted_score = fields.Float(string='Total Manager Weighted Score', compute='_compute_totals',
                                                store=True)
    employee_final_score = fields.Float(string='Overall Rating', compute='_compute_totals', store=True)
    manager_final_score = fields.Float(string='Manager Overall Rating', compute='_compute_totals', store=True)
    is_employee = fields.Boolean(string="Is Employee", compute="_compute_is_employee", store=False)

    recommended_increment = fields.Float(string="Recommended Increment (%)", help="Recommended Increment percentage")
    recommended_pbvp_payout = fields.Float(string="Recommended PBVP Payout (%) based on overall rating",
                                           help="To be released on a pro-rata basis")
    pbvp_payout = fields.Float(string="PBVP Payout (%)",
                               help="To be released on a pro-rata basis")
    eligible_for_promotion = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Eligible for Promotion?")
    new_job_level = fields.Char(string="Job Level")
    new_designation = fields.Char(string="Redesignation (if applicable)")
    remark = fields.Char(string="Remark")
    refuse_reason = fields.Text(string="Refuse Reason")
    director_remark = fields.Text(string="Director Remark")
    is_performance_record = fields.Boolean(string="Is Performance Record", compute="_compute_is_performance_record",
                                           store=True)

    basic_da_per_annum = fields.Float(string='Basic & DA', copy=False)
    basic_da_per_month = fields.Float(string='Basic & DA', copy=False)
    hra_per_annum = fields.Float(string='House Rent Allowance', copy=False)
    hra_per_month = fields.Float(string='House Rent Allowance', copy=False)
    special_allowance_per_annum = fields.Float(string='Special Allowance', copy=False)
    special_allowance_per_month = fields.Float(string='Special Allowance', copy=False)
    sub_total_a_per_annum = fields.Float(string='Sub-total Part A', copy=False)
    sub_total_a_per_month = fields.Float(string='Sub-total Part A', copy=False)
    statutory_bonus_per_annum = fields.Float(string='Statutory Bonus', copy=False)
    statutory_bonus_per_month = fields.Float(string='Statutory Bonus', copy=False)
    pf_employer_per_annum = fields.Float(string="Provident Fund (Employer's Contribution)", copy=False)
    pf_employer_per_month = fields.Float(string="Provident Fund (Employer's Contribution)", copy=False)
    esic_employer_per_annum = fields.Float(string='ESIC (Employer Contribution)', copy=False)
    esic_employer_per_month = fields.Float(string='ESIC (Employer Contribution)', copy=False)
    sub_total_b_per_annum = fields.Float(string='Sub-total Part B', copy=False)
    sub_total_b_per_month = fields.Float(string='Sub-total Part B', copy=False)
    variable_pay_per_annum = fields.Float(string='Performance Linked Variable Pay', copy=False)
    variable_pay_per_month = fields.Float(string='Performance Linked Variable Pay', copy=False)
    sub_total_c_per_annum = fields.Float(string='Sub-total Part C', copy=False)
    sub_total_c_per_month = fields.Float(string='Sub-total Part C', copy=False)
    total_salary_per_annum = fields.Float(string='Total Salary', copy=False)
    total_salary_per_month = fields.Float(string='Total Salary', copy=False)
    medical_insurances = fields.Float(string='Medical Insurance', copy=False)
    group_personal_acc_insurance = fields.Float(string='Group Personal Accident Insurance', copy=False)
    health_ben_plan = fields.Float(string='Health Benefit Plan', copy=False)
    sub_total_d = fields.Float(string='Sub-total Part D', copy=False)
    total_ctc_annum = fields.Float(string='Total Cost to Company', copy=False)
    total_ctc_month = fields.Float(string='Total Cost to Company', copy=False)
    monthly_fixed_salary = fields.Float(string="Monthly Fixed Salary (excl PF & all incentive pay)", copy=False)
    stat_bonus_amount = fields.Float(string="Statutory Bonus Amount", store=True, copy=False)
    provident_fund = fields.Float(string="Provident Fund", store=True, copy=False)
    esi_amount = fields.Float(string="ESI Amount", store=True, copy=False)
    variable_pay_percentage = fields.Float(string="Percentage of Variable Pay", store=True, copy=False)
    annual_store_performance_incentive = fields.Float(string="Annual Store Performance Incentive", store=True,
                                                      copy=False)
    store_performance_incentive_annum = fields.Float(string="Store Performance Incentive", store=True,
                                                     copy=False)
    store_performance_incentive_month = fields.Float(string="Store Performance Incentive", store=True,
                                                     copy=False)
    annual_performance_linked_pay = fields.Float(string="Annual Performance Linked Pay", store=True, copy=False)
    performance_linked_pay_annum = fields.Float(string="Performance Linked Pay", store=True, copy=False)
    performance_linked_pay_month = fields.Float(string="Performance Linked Pay", store=True, copy=False)
    monthly_performance_incentive = fields.Float(string="Monthly Performance Incentive", store=True, copy=False)
    monthly_performance_incentive_annum = fields.Float(string="Monthly Performance Incentive", store=True,
                                                       copy=False)
    monthly_performance_incentive_month = fields.Float(string="Monthly Performance Incentive", store=True,
                                                       copy=False)
    medical_insurance = fields.Float(string="Medical Insurance", store=True, copy=False)
    group_personal_accident_insurance = fields.Float(string="Group Personal Accident Insurance", store=True, copy=False)
    health_benefit_plan = fields.Float(string="Health Benefit Plan", store=True, copy=False)
    solis_health_benefit_beacon_plan = fields.Float(string="Solis Health Benefit Beacon Plan", store=True, copy=False)
    indicative_take_home_salary = fields.Float(string="Indicative Take Home Salary Per Month", store=True, copy=False)
    statutory_bonus_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="Statutory Bonus Applicable", default='no', required=True,
        copy=False
    )
    provident_fund_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="Provident Fund Applicable", default='no', required=True,
        copy=False
    )
    esi_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="ESI Applicable", default='no', required=True, copy=False
    )
    grade = fields.Selection([
        ('spl_grade', 'Spl Grade'),
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
        ('grade_d', 'Grade D'),
        ('grade_e', 'Grade E'),
        ('grade_f', 'Grade F'),
        ('grade_g', 'Grade G'),
    ], default='spl_grade', string="Grade", tracking=True, required=True)

    contract_self_rating_ids = fields.Many2many('hr.contract',
                                                compute='_compute_contract_self_rating',
                                                string='Compensation Master', copy=False)
    contract_self_rating_count = fields.Integer("Compensation Master Count",
                                                compute='_compute_contract_self_rating', default=0,
                                                copy=False)
    current_running_contract = fields.Many2one('hr.contract',compute='_compute_contract_self_rating',
                                                string='Compensation Master')

    total_ctc_in_words = fields.Char(string="Total CTC In Words", compute='_compute_total_ctc_in_words')
    revised_increment_per = fields.Float(string='Revised Increment %')
    variable_pay_amount = fields.Float(string="Variable Pay Amount", compute="_compute_variable_pay_amount")
    # To be filled by Manager
    manager_eligible_for_promotion = fields.Selection([('yes', 'Yes'), ('no', 'No')], string="Eligible for Promotion?")
    manager_new_designation = fields.Char(string="Redesignation (if applicable)")
    manager_remark = fields.Char(string="Remark")




    @api.depends('contract_self_rating_ids.variable_pay_per_annum','recommended_pbvp_payout','variable_pay_percentage')
    def _compute_variable_pay_amount(self):
        for rec in self:
            rec.variable_pay_amount = 0.0
            if rec.contract_self_rating_ids:
                contract = rec.contract_self_rating_ids[0]
                variable_pay = contract.variable_pay_per_annum or 0.0
                payout_percentage = rec.recommended_pbvp_payout or 0.0
                rec.variable_pay_amount = variable_pay * (payout_percentage / 100.0)

    @api.onchange('recommended_increment','revised_increment_per')
    def _onchange_increment(self):
        if self.contract_self_rating_ids:
            if self.revised_increment_per > 0:
                contract_id = self.contract_self_rating_ids.ids[0]
                if contract_id:
                    contract_id = self.env['hr.contract'].browse(contract_id)
                    current_salary = contract_id.monthly_fixed_salary
                    increment_amount = (current_salary * self.revised_increment_per) / 100.0
                    # New salary
                    new_salary = current_salary + increment_amount
                    self.monthly_fixed_salary = new_salary
            elif self.recommended_increment > 0:
                contract_id = self.contract_self_rating_ids.ids[0]
                if contract_id:
                    contract_id = self.env['hr.contract'].browse(contract_id)
                    current_salary = contract_id.monthly_fixed_salary
                    increment_amount = (current_salary * self.recommended_increment) / 100.0
                    # New salary
                    new_salary = current_salary + increment_amount
                    self.monthly_fixed_salary = new_salary
            else:
                contract_id = self.contract_self_rating_ids.ids[0]
                if contract_id:
                    contract_id = self.env['hr.contract'].browse(contract_id)
                    self.monthly_fixed_salary = contract_id.monthly_fixed_salary



    @api.model
    def default_get(self, fields):
        defaults = super(SelfRating, self).default_get(fields)
        if 'is_appraisal_manager' in fields:
            defaults['is_appraisal_manager'] = self.env.user.has_group('hr_appraisal.group_hr_appraisal_manager')
        return defaults

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for record in self:
            if record.employee_id:
                record.date_of_joining = record.sudo().employee_id.joining_date
                record.designation_id = record.sudo().employee_id.job_id
                record.department_id = record.sudo().employee_id.department_id
                record.grade = record.sudo().employee_id.contract_id.grade
                record.location_id = record.sudo().employee_id.contract_id.location_id
                contract_id = record.contract_self_rating_ids.ids[0]
                if contract_id:
                    contract_id = self.env['hr.contract'].browse(contract_id)
                    record.monthly_fixed_salary = contract_id.monthly_fixed_salary
                    record.statutory_bonus_applicable = contract_id.statutory_bonus_applicable
                    record.provident_fund_applicable = contract_id.provident_fund_applicable = record.provident_fund_applicable
                    record.esi_applicable = contract_id.esi_applicable
                    record.variable_pay_percentage = contract_id.variable_pay_percentage
                    record.medical_insurance = contract_id.medical_insurance
                    record.group_personal_accident_insurance = contract_id.group_personal_accident_insurance
                    record.health_benefit_plan = contract_id.health_benefit_plan
                    record._onchange_calculate_salary_breakup()
            record.pbvp_reference_ids = [
                (0, 0, {'score_range': 'Above 4.7', 'payout_percentage': '100%'}),
                (0, 0, {'score_range': '4.5 to 4.7', 'payout_percentage': '90%'}),
                (0, 0, {'score_range': '4.0 to 4.5', 'payout_percentage': '80%'}),
                (0, 0, {'score_range': '3.5 to 4.0', 'payout_percentage': '70%'}),
                (0, 0, {'score_range': '3.0 to 3.5', 'payout_percentage': '50%'}),
                (0, 0, {'score_range': '2.5 to 3.0', 'payout_percentage': '30%'}),
                (0, 0, {'score_range': 'Below 2.5', 'payout_percentage': '0%'}),
            ]



    @api.onchange('total_ctc_annum')
    def _compute_total_ctc_in_words(self):
        for record in self:
            if record.total_ctc_annum:
                total_ctc_integer = int(record.total_ctc_annum)
                record.total_ctc_in_words = num2words(total_ctc_integer, lang='en_IN').title()
            else:
                record.total_ctc_in_words = 'None'

    @api.onchange('location_id', 'monthly_fixed_salary', 'statutory_bonus_applicable', 'provident_fund_applicable',
                  'esi_applicable', 'grade',
                  'variable_pay_percentage', 'annual_store_performance_incentive', 'annual_performance_linked_pay',
                  'monthly_performance_incentive',
                  'medical_insurance', 'group_personal_accident_insurance', 'health_benefit_plan')
    def _onchange_calculate_salary_breakup(self):
        for record in self:
            # Fetch the salary structure based on location and grade
            if record.variable_pay_percentage > 100:
                raise ValidationError(
                    f"The variable pay percentage should not exceed 100."
                )
            salary_structure = self.env['salary.master'].search([
                ('location_id', '=', record.location_id.id),
                ('grade', '=', record.grade)
            ], limit=1)

            # Initialize fields
            record.basic_da_per_annum = 0
            record.basic_da_per_month = 0
            record.hra_per_annum = 0
            record.hra_per_month = 0
            record.statutory_bonus_per_annum = 0
            record.statutory_bonus_per_month = 0
            record.special_allowance_per_annum = 0
            record.special_allowance_per_month = 0
            record.sub_total_a_per_annum = 0
            record.sub_total_a_per_month = 0
            record.pf_employer_per_annum = 0
            record.pf_employer_per_month = 0
            record.esic_employer_per_annum = 0
            record.esic_employer_per_month = 0
            record.sub_total_b_per_annum = 0
            record.sub_total_b_per_month = 0
            record.sub_total_c_per_annum = 0
            record.sub_total_c_per_month = 0
            record.total_salary_per_annum = 0
            record.total_salary_per_month = 0
            record.medical_insurances = 0
            record.group_personal_acc_insurance = 0
            record.health_ben_plan = 0
            record.total_ctc_annum = 0
            record.total_ctc_month = 0
            record.indicative_take_home_salary = 0

            if salary_structure and (record.monthly_fixed_salary < 54000):
                if record.location_id.name == 'TTA' and record.grade == 'grade_d':
                    record.basic_da_per_annum = salary_structure.annual_salary
                    record.basic_da_per_month = round(record.basic_da_per_annum / 12)
                    record.statutory_bonus_per_annum = min(16800, (
                            record.monthly_fixed_salary * 12) - record.basic_da_per_annum)
                    record.statutory_bonus_per_month = round(record.statutory_bonus_per_annum / 12)
                    record.hra_per_annum = 0
                    record.hra_per_month = round(record.hra_per_annum / 12)

                    record.special_allowance_per_annum = 0
                    record.special_allowance_per_month = round(record.special_allowance_per_annum / 12)

                    # Calculate Provident Fund
                    if record.provident_fund_applicable == 'yes':
                        if record.monthly_fixed_salary < 15000:
                            record.pf_employer_per_month = round(record.monthly_fixed_salary * 0.12)
                        else:
                            record.pf_employer_per_month = round(15000 * 0.12)
                    record.pf_employer_per_annum = record.pf_employer_per_month * 12

                    # Calculate ESIC
                    if record.esi_applicable == 'yes':
                        record.esic_employer_per_month = round(
                            record.monthly_fixed_salary * 0.0325) if record.monthly_fixed_salary <= 21000 else 0
                    record.esic_employer_per_annum = record.esic_employer_per_month * 12

                    # Subtotals
                    record.sub_total_b_per_annum = record.statutory_bonus_per_annum + record.pf_employer_per_annum + record.esic_employer_per_annum
                    record.sub_total_b_per_month = record.statutory_bonus_per_month + record.pf_employer_per_month + record.esic_employer_per_month

                    # Other calculations
                    record.store_performance_incentive_annum = record.annual_store_performance_incentive
                    record.store_performance_incentive_month = round(record.store_performance_incentive_annum / 12)
                    record.performance_linked_pay_annum = record.annual_performance_linked_pay
                    record.performance_linked_pay_month = round(record.performance_linked_pay_annum / 12, 0)
                    record.monthly_performance_incentive_annum = record.monthly_performance_incentive
                    record.monthly_performance_incentive_month = round(record.monthly_performance_incentive_annum / 12)
                    record.variable_pay_per_annum = round(
                        (record.monthly_fixed_salary * 12 + record.pf_employer_per_annum) * (
                                record.variable_pay_percentage / 100))
                    record.variable_pay_per_month = round(record.variable_pay_per_annum / 12)

                    # record.sub_total_c_per_annum = record.store_performance_incentive_annum + record.performance_linked_pay_annum + record.monthly_performance_incentive_annum + record.variable_pay_per_annum
                    record.sub_total_c_per_annum = record.variable_pay_per_annum
                    record.sub_total_c_per_month = round(record.sub_total_c_per_annum / 12)

                    record.total_salary_per_annum = record.sub_total_a_per_annum + record.sub_total_b_per_annum + record.sub_total_c_per_annum
                    record.total_salary_per_month = round(record.total_salary_per_annum / 12)
                    record.medical_insurances = record.medical_insurance
                    record.group_personal_acc_insurance = record.group_personal_accident_insurance
                    record.health_ben_plan = record.health_benefit_plan
                    record.sub_total_d = record.medical_insurance + record.group_personal_acc_insurance + record.health_ben_plan

                    # CTC Calculations
                    record.total_ctc_annum = record.total_salary_per_annum + record.medical_insurances + record.group_personal_acc_insurance + record.health_ben_plan
                    record.total_ctc_month = round(record.total_ctc_annum / 12)
                    profession_tax = 200 if (
                                                    record.sub_total_a_per_month + record.statutory_bonus_per_month + record.pf_employer_per_month) > 15000 else 0

                    # Indicative Take Home Salary
                    record.indicative_take_home_salary = math.ceil(
                        record.sub_total_a_per_month + record.statutory_bonus_per_month - record.pf_employer_per_month - round(
                            record.esic_employer_per_month / 0.0325 * 0.0075) - profession_tax)
                else:
                    record.basic_da_per_annum = max(round((record.monthly_fixed_salary * 12 * 0.4) / 12000) * 12000,
                                                    salary_structure.annual_salary)
                    record.basic_da_per_month = round(record.basic_da_per_annum / 12)

                    if (record.basic_da_per_annum / 12) <= 21000:
                        record.statutory_bonus_per_annum = min(16800, (
                                record.monthly_fixed_salary * 12) - record.basic_da_per_annum)

                    record.statutory_bonus_per_month = round(record.statutory_bonus_per_annum / 12)

                    record.hra_per_annum = min(record.basic_da_per_annum * 0.40, (
                            record.monthly_fixed_salary * 12) - record.basic_da_per_annum - record.statutory_bonus_per_annum)
                    record.hra_per_month = round(record.hra_per_annum / 12)

                    record.special_allowance_per_annum = (
                                                                 record.monthly_fixed_salary * 12) - record.basic_da_per_annum - record.hra_per_annum - record.statutory_bonus_per_annum
                    record.sub_total_a_per_annum = record.basic_da_per_annum + record.hra_per_annum + record.special_allowance_per_annum
                    record.special_allowance_per_month = round(record.special_allowance_per_annum / 12)
                    record.sub_total_a_per_month = round(record.sub_total_a_per_annum / 12)

                    # Calculate Provident Fund
                    if record.provident_fund_applicable == 'yes':
                        if record.monthly_fixed_salary < 15000:
                            record.pf_employer_per_month = round(record.monthly_fixed_salary * 0.12)
                        else:
                            record.pf_employer_per_month = round(15000 * 0.12)
                    record.pf_employer_per_annum = record.pf_employer_per_month * 12

                    # Calculate ESIC
                    if record.esi_applicable == 'yes':
                        record.esic_employer_per_month = round(
                            record.monthly_fixed_salary * 0.0325) if record.monthly_fixed_salary <= 21000 else 0
                    record.esic_employer_per_annum = record.esic_employer_per_month * 12

                    # Subtotals
                    record.sub_total_b_per_annum = record.statutory_bonus_per_annum + record.pf_employer_per_annum + record.esic_employer_per_annum
                    record.sub_total_b_per_month = record.statutory_bonus_per_month + record.pf_employer_per_month + record.esic_employer_per_month

                    # Other calculations
                    record.store_performance_incentive_annum = record.annual_store_performance_incentive
                    record.store_performance_incentive_month = round(record.store_performance_incentive_annum / 12)
                    record.performance_linked_pay_annum = record.annual_performance_linked_pay
                    record.performance_linked_pay_month = round(record.performance_linked_pay_annum / 12, 0)
                    record.monthly_performance_incentive_annum = record.monthly_performance_incentive
                    record.monthly_performance_incentive_month = round(record.monthly_performance_incentive_annum / 12)
                    record.variable_pay_per_annum = round(
                        (record.monthly_fixed_salary * 12 + record.pf_employer_per_annum) * (
                                record.variable_pay_percentage / 100))
                    record.variable_pay_per_month = round(record.variable_pay_per_annum / 12)

                    # record.sub_total_c_per_annum = record.store_performance_incentive_annum + record.performance_linked_pay_annum + record.monthly_performance_incentive_annum + record.variable_pay_per_annum
                    record.sub_total_c_per_annum = record.variable_pay_per_annum
                    record.sub_total_c_per_month = round(record.sub_total_c_per_annum / 12)

                    record.total_salary_per_annum = record.sub_total_a_per_annum + record.sub_total_b_per_annum + record.sub_total_c_per_annum
                    record.total_salary_per_month = round(record.total_salary_per_annum / 12)
                    record.medical_insurances = record.medical_insurance
                    record.group_personal_acc_insurance = record.group_personal_accident_insurance
                    record.health_ben_plan = record.health_benefit_plan
                    record.sub_total_d = record.medical_insurance + record.group_personal_acc_insurance + record.health_ben_plan

                    # CTC Calculations
                    record.total_ctc_annum = record.total_salary_per_annum + record.medical_insurances + record.group_personal_acc_insurance + record.health_ben_plan
                    record.total_ctc_month = round(record.total_ctc_annum / 12)
                    profession_tax = 200 if (
                                                    record.sub_total_a_per_month + record.statutory_bonus_per_month + record.pf_employer_per_month) > 15000 else 0

                    # Indicative Take Home Salary
                    record.indicative_take_home_salary = math.ceil(
                        record.sub_total_a_per_month + record.statutory_bonus_per_month - record.pf_employer_per_month - round(
                            record.esic_employer_per_month / 0.0325 * 0.0075) - profession_tax)

            elif salary_structure and (record.monthly_fixed_salary >= 54000):
                record.basic_da_per_annum = round((record.monthly_fixed_salary * 12 * 0.4) / 12000) * 12000
                record.basic_da_per_month = round(record.basic_da_per_annum / 12)
                record.hra_per_annum = record.basic_da_per_annum * 0.40
                record.hra_per_month = round(record.hra_per_annum / 12)
                record.statutory_bonus_per_annum = 0
                record.statutory_bonus_per_month = round(record.statutory_bonus_per_annum / 12)

                # Special Allowance Calculation
                record.special_allowance_per_annum = (record.monthly_fixed_salary * 12) - (
                        record.basic_da_per_annum + record.hra_per_annum + record.statutory_bonus_per_annum)
                record.sub_total_a_per_annum = record.basic_da_per_annum + record.hra_per_annum + record.special_allowance_per_annum
                record.special_allowance_per_month = round(record.special_allowance_per_annum / 12)
                record.sub_total_a_per_month = round(record.sub_total_a_per_annum / 12)

                if record.provident_fund_applicable == 'yes':
                    if record.monthly_fixed_salary < 15000:
                        record.pf_employer_per_month = round(record.monthly_fixed_salary * 0.12)
                    else:
                        record.pf_employer_per_month = round(15000 * 0.12)
                record.pf_employer_per_annum = record.pf_employer_per_month * 12

                # ESIC Calculation
                if record.esi_applicable == 'yes':
                    record.esic_employer_per_month = round(
                        record.monthly_fixed_salary * 0.0325) if record.monthly_fixed_salary <= 21000 else 0
                record.esic_employer_per_annum = record.esic_employer_per_month * 12

                # Subtotals
                record.sub_total_b_per_annum = record.statutory_bonus_per_annum + record.pf_employer_per_annum + record.esic_employer_per_annum
                record.sub_total_b_per_month = record.statutory_bonus_per_month + record.pf_employer_per_month + record.esic_employer_per_month

                # Other calculations
                record.store_performance_incentive_annum = record.annual_store_performance_incentive
                record.store_performance_incentive_month = round(record.store_performance_incentive_annum / 12)
                record.performance_linked_pay_annum = record.annual_performance_linked_pay
                record.performance_linked_pay_month = round(record.performance_linked_pay_annum / 12)
                record.monthly_performance_incentive_annum = record.monthly_performance_incentive
                record.monthly_performance_incentive_month = round(record.monthly_performance_incentive_annum / 12)
                record.variable_pay_per_annum = round(
                    (record.monthly_fixed_salary * 12 + record.pf_employer_per_annum) * (
                            record.variable_pay_percentage / 100))
                record.variable_pay_per_month = round(record.variable_pay_per_annum / 12)

                # record.sub_total_c_per_annum = record.store_performance_incentive_annum + record.performance_linked_pay_annum + record.monthly_performance_incentive_annum + record.variable_pay_per_annum
                record.sub_total_c_per_annum = record.variable_pay_per_annum
                record.sub_total_c_per_month = round(record.sub_total_c_per_annum / 12)

                record.total_salary_per_annum = record.sub_total_a_per_annum + record.sub_total_b_per_annum + record.sub_total_c_per_annum
                record.total_salary_per_month = round(record.total_salary_per_annum / 12)
                record.medical_insurances = record.medical_insurance
                record.group_personal_acc_insurance = record.group_personal_accident_insurance
                record.health_ben_plan = record.health_benefit_plan
                record.sub_total_d = record.medical_insurance + record.group_personal_acc_insurance + record.health_ben_plan

                # CTC Calculations
                record.total_ctc_annum = record.total_salary_per_annum + record.medical_insurances + record.group_personal_acc_insurance + record.health_ben_plan
                record.total_ctc_month = round(record.total_ctc_annum / 12)
                profession_tax = 200 if (
                                                record.sub_total_a_per_month + record.statutory_bonus_per_month + record.pf_employer_per_month) > 15000 else 0

                # Indicative Take Home Salary
                record.indicative_take_home_salary = math.ceil(
                    record.sub_total_a_per_month + record.statutory_bonus_per_month - record.pf_employer_per_month - round(
                        record.esic_employer_per_month / 0.0325 * 0.0075) - profession_tax)

            elif (record.location_id.name not in ['tta', 'tvm_obt']) and (record.monthly_fixed_salary >= 54000):
                # Calculate Basic & DA (Per Annum)
                record.basic_da_per_annum = round((record.monthly_fixed_salary * 12 * 0.4) / 12000) * 12000
                record.hra_per_annum = record.basic_da_per_annum * 0.40

                # Calculate (Per Month)
                record.basic_da_per_month = round(record.basic_da_per_annum / 12)
                record.hra_per_month = round(record.hra_per_annum / 12)

                # Statutory Bonus Logic
                if record.location_id.name == 'TTA' and record.grade == 'grade_d':
                    record.statutory_bonus_per_annum = min(16800, (
                            record.monthly_fixed_salary * 12) - record.basic_da_per_annum)
                elif record.statutory_bonus_applicable == 'yes':
                    if (record.basic_da_per_annum / 12) <= 21000:
                        record.statutory_bonus_per_annum = min(record.basic_da_per_annum, 84000) * 0.20

                record.statutory_bonus_per_month = round(record.statutory_bonus_per_annum / 12)

                # Special Allowance Calculation
                record.special_allowance_per_annum = (record.monthly_fixed_salary * 12) - (
                        record.basic_da_per_annum + record.hra_per_annum + record.statutory_bonus_per_annum)
                record.sub_total_a_per_annum = record.basic_da_per_annum + record.hra_per_annum + record.special_allowance_per_annum
                record.special_allowance_per_month = round(record.special_allowance_per_annum / 12)
                record.sub_total_a_per_month = round(record.sub_total_a_per_annum / 12)

                # Provident Fund Calculation
                if record.provident_fund_applicable == 'yes':
                    if record.monthly_fixed_salary < 15000:
                        record.pf_employer_per_month = round(record.monthly_fixed_salary * 0.12)
                    else:
                        record.pf_employer_per_month = round(15000 * 0.12)
                record.pf_employer_per_annum = record.pf_employer_per_month * 12

                # ESIC Calculation
                if record.esi_applicable == 'yes':
                    record.esic_employer_per_month = round(
                        record.monthly_fixed_salary * 0.0325) if record.monthly_fixed_salary <= 21000 else 0
                record.esic_employer_per_annum = record.esic_employer_per_month * 12

                # Subtotals
                record.sub_total_b_per_annum = record.statutory_bonus_per_annum + record.pf_employer_per_annum + record.esic_employer_per_annum
                record.sub_total_b_per_month = record.statutory_bonus_per_month + record.pf_employer_per_month + record.esic_employer_per_month

                # Other calculations
                record.store_performance_incentive_annum = record.annual_store_performance_incentive
                record.store_performance_incentive_month = round(record.store_performance_incentive_annum / 12)
                record.performance_linked_pay_annum = record.annual_performance_linked_pay
                record.performance_linked_pay_month = round(record.performance_linked_pay_annum / 12)
                record.monthly_performance_incentive_annum = record.monthly_performance_incentive
                record.monthly_performance_incentive_month = round(record.monthly_performance_incentive_annum / 12)
                record.variable_pay_per_annum = round(
                    (record.monthly_fixed_salary * 12 + record.pf_employer_per_annum) * (
                            record.variable_pay_percentage / 100))
                record.variable_pay_per_month = round(record.variable_pay_per_annum / 12)

                # record.sub_total_c_per_annum = record.store_performance_incentive_annum + record.performance_linked_pay_annum + record.monthly_performance_incentive_annum + record.variable_pay_per_annum
                record.sub_total_c_per_annum = record.variable_pay_per_annum
                record.sub_total_c_per_month = round(record.sub_total_c_per_annum / 12)

                record.total_salary_per_annum = record.sub_total_a_per_annum + record.sub_total_b_per_annum + record.sub_total_c_per_annum
                record.total_salary_per_month = round(record.total_salary_per_annum / 12)
                record.medical_insurances = record.medical_insurance
                record.group_personal_acc_insurance = record.group_personal_accident_insurance
                record.health_ben_plan = record.health_benefit_plan
                record.sub_total_d = record.medical_insurance + record.group_personal_acc_insurance + record.health_ben_plan

                # CTC Calculations
                record.total_ctc_annum = record.total_salary_per_annum + record.medical_insurances + record.group_personal_acc_insurance + record.health_ben_plan
                record.total_ctc_month = round(record.total_ctc_annum / 12)
                profession_tax = 200 if (
                                                record.sub_total_a_per_month + record.statutory_bonus_per_month + record.pf_employer_per_month) > 15000 else 0

                # Indicative Take Home Salary
                record.indicative_take_home_salary = math.ceil(
                    record.sub_total_a_per_month + record.statutory_bonus_per_month - record.pf_employer_per_month - round(
                        record.esic_employer_per_month / 0.0325 * 0.0075) - profession_tax)

            elif (record.location_id.name not in ['tta', 'tvm_obt']) and (record.monthly_fixed_salary < 54000):
                # Calculate Basic & DA (Per Annum)
                record.basic_da_per_annum = round((record.monthly_fixed_salary * 12 * 0.4) / 12000) * 12000
                record.hra_per_annum = record.basic_da_per_annum * 0.40

                # Calculate (Per Month)
                record.basic_da_per_month = round(record.basic_da_per_annum / 12)
                record.hra_per_month = round(record.hra_per_annum / 12)

                # Statutory Bonus Logic
                if record.location_id.name == 'TTA' and record.grade == 'grade_d':
                    record.statutory_bonus_per_annum = min(16800, (
                            record.monthly_fixed_salary * 12) - record.basic_da_per_annum)
                elif record.statutory_bonus_applicable == 'yes':
                    if (record.basic_da_per_annum / 12) <= 21000:
                        record.statutory_bonus_per_annum = min(record.basic_da_per_annum, 84000) * 0.20

                record.statutory_bonus_per_month = round(record.statutory_bonus_per_annum / 12)

                # Special Allowance Calculation
                record.special_allowance_per_annum = (record.monthly_fixed_salary * 12) - (
                        record.basic_da_per_annum + record.hra_per_annum + record.statutory_bonus_per_annum)
                record.sub_total_a_per_annum = record.basic_da_per_annum + record.hra_per_annum + record.special_allowance_per_annum
                record.special_allowance_per_month = round(record.special_allowance_per_annum / 12)
                record.sub_total_a_per_month = round(record.sub_total_a_per_annum / 12)

                # Provident Fund Calculation
                if record.provident_fund_applicable == 'yes':
                    if record.monthly_fixed_salary < 15000:
                        record.pf_employer_per_month = round(record.monthly_fixed_salary * 0.12)
                    else:
                        record.pf_employer_per_month = round(15000 * 0.12)
                record.pf_employer_per_annum = record.pf_employer_per_month * 12

                # ESIC Calculation
                if record.esi_applicable == 'yes':
                    record.esic_employer_per_month = round(
                        record.monthly_fixed_salary * 0.0325) if record.monthly_fixed_salary <= 21000 else 0
                record.esic_employer_per_annum = record.esic_employer_per_month * 12

                # Subtotals
                record.sub_total_b_per_annum = record.statutory_bonus_per_annum + record.pf_employer_per_annum + record.esic_employer_per_annum
                record.sub_total_b_per_month = record.statutory_bonus_per_month + record.pf_employer_per_month + record.esic_employer_per_month

                # Other calculations
                record.store_performance_incentive_annum = record.annual_store_performance_incentive
                record.store_performance_incentive_month = round(record.store_performance_incentive_annum / 12)
                record.performance_linked_pay_annum = record.annual_performance_linked_pay
                record.performance_linked_pay_month = round(record.performance_linked_pay_annum / 12)
                record.monthly_performance_incentive_annum = record.monthly_performance_incentive
                record.monthly_performance_incentive_month = round(record.monthly_performance_incentive_annum / 12)
                record.variable_pay_per_annum = round(
                    (record.monthly_fixed_salary * 12 + record.pf_employer_per_annum) * (
                            record.variable_pay_percentage / 100))
                record.variable_pay_per_month = round(record.variable_pay_per_annum / 12)

                # record.sub_total_c_per_annum = record.store_performance_incentive_annum + record.performance_linked_pay_annum + record.monthly_performance_incentive_annum + record.variable_pay_per_annum
                record.sub_total_c_per_annum = record.variable_pay_per_annum
                record.sub_total_c_per_month = round(record.sub_total_c_per_annum / 12)

                record.total_salary_per_annum = record.sub_total_a_per_annum + record.sub_total_b_per_annum + record.sub_total_c_per_annum
                record.total_salary_per_month = round(record.total_salary_per_annum / 12)
                record.medical_insurances = record.medical_insurance
                record.group_personal_acc_insurance = record.group_personal_accident_insurance
                record.health_ben_plan = record.health_benefit_plan
                record.sub_total_d = record.medical_insurance + record.group_personal_acc_insurance + record.health_ben_plan

                # CTC Calculations
                record.total_ctc_annum = record.total_salary_per_annum + record.medical_insurances + record.group_personal_acc_insurance + record.health_ben_plan
                record.total_ctc_month = round(record.total_ctc_annum / 12)
                profession_tax = 200 if (
                                                record.sub_total_a_per_month + record.statutory_bonus_per_month + record.pf_employer_per_month) > 15000 else 0

                # Indicative Take Home Salary
                record.indicative_take_home_salary = math.ceil(
                    record.sub_total_a_per_month + record.statutory_bonus_per_month - record.pf_employer_per_month - round(
                        record.esic_employer_per_month / 0.0325 * 0.0075) - profession_tax)

            else:
                pass

    def _compute_contract_self_rating(self):
        for record in self:
            domain = [('employee_id', '=', record.employee_id.id)]
            contract_self_rating_ids = self.env['hr.contract'].sudo().search(domain)
            record.contract_self_rating_ids = contract_self_rating_ids
            record.contract_self_rating_count = len(contract_self_rating_ids)
            record.current_running_contract = self.env['hr.contract'].sudo().search([('employee_id', '=', record.employee_id.id),('state','=','open')],limit=1)

    def action_open_contract_self_rating(self):
        action = self.env.ref('hr_contract.action_hr_contract')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.contract_self_rating_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.contract_self_rating_ids.ids)) + "])]"
        elif len(self.contract_self_rating_ids.ids) == 1:
            res = self.env.ref('hr_contract.hr_contract_view_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.contract_self_rating_ids.ids and self.contract_self_rating_ids.ids[
                0] or False
        return result

    def action_create_new_contract(self):
        if not self.monthly_fixed_salary:
            raise ValidationError("Please fill the Salary Breakup Details")
        if self.employee_id:
            # Search for an existing contract for the employee
            existing_contract = self.env['hr.contract'].search(
                [('employee_id', '=', self.employee_id.id), ('state', '=', 'open')], limit=1)
            self.employee_id.job_level_id = self.job_level.id
            # Prepare contract values
            contract_vals = {
                'name': f'{self.employee_id.name} Compensation master',
                'employee_id': self.employee_id.id,
                'date_start': fields.Date.today(),
                'wage': 0.0,
                'department_id': self.employee_id.department_id.id,
                'job_id': self.employee_id.job_id.id,
                'basic_da_per_annum': self.basic_da_per_annum,
                'basic_da_per_month': self.basic_da_per_month,
                'hra_per_annum': self.hra_per_annum,
                'hra_per_month': self.hra_per_month,
                'special_allowance_per_annum': self.special_allowance_per_annum,
                'special_allowance_per_month': self.special_allowance_per_month,
                'sub_total_a_per_annum': self.sub_total_a_per_annum,
                'sub_total_a_per_month': self.sub_total_a_per_month,
                'statutory_bonus_per_annum': self.statutory_bonus_per_annum,
                'statutory_bonus_per_month': self.statutory_bonus_per_month,
                'pf_employer_per_annum': self.pf_employer_per_annum,
                'pf_employer_per_month': self.pf_employer_per_month,
                'esic_employer_per_annum': self.esic_employer_per_annum,
                'esic_employer_per_month': self.esic_employer_per_month,
                'sub_total_b_per_annum': self.sub_total_b_per_annum,
                'sub_total_b_per_month': self.sub_total_b_per_month,
                'variable_pay_per_annum': self.variable_pay_per_annum,
                'variable_pay_per_month': self.variable_pay_per_month,
                'sub_total_c_per_annum': self.sub_total_c_per_annum,
                'sub_total_c_per_month': self.sub_total_c_per_month,
                'total_salary_per_annum': self.total_salary_per_annum,
                'total_salary_per_month': self.total_salary_per_month,
                'medical_insurances': self.medical_insurances,
                'group_personal_acc_insurance': self.group_personal_acc_insurance,
                'health_ben_plan': self.health_ben_plan,
                'sub_total_d': self.sub_total_d,
                'total_ctc_annum': self.total_ctc_annum,
                'total_ctc_month': self.total_ctc_month,
                'monthly_fixed_salary': self.monthly_fixed_salary,
                'stat_bonus_amount': self.stat_bonus_amount,
                'provident_fund': self.provident_fund,
                'esi_amount': self.esi_amount,
                'variable_pay_percentage': self.variable_pay_percentage,
                'annual_store_performance_incentive': self.annual_store_performance_incentive,
                'store_performance_incentive_annum': self.store_performance_incentive_annum,
                'store_performance_incentive_month': self.store_performance_incentive_month,
                'annual_performance_linked_pay': self.annual_performance_linked_pay,
                'performance_linked_pay_annum': self.performance_linked_pay_annum,
                'performance_linked_pay_month': self.performance_linked_pay_month,
                'monthly_performance_incentive': self.monthly_performance_incentive,
                'monthly_performance_incentive_annum': self.monthly_performance_incentive_annum,
                'monthly_performance_incentive_month': self.monthly_performance_incentive_month,
                'medical_insurance': self.medical_insurance,
                'group_personal_accident_insurance': self.group_personal_accident_insurance,
                'health_benefit_plan': self.health_benefit_plan,
                'solis_health_benefit_beacon_plan': self.solis_health_benefit_beacon_plan,
                'indicative_take_home_salary': self.indicative_take_home_salary,
                'statutory_bonus_applicable': self.statutory_bonus_applicable,
                'provident_fund_applicable': self.provident_fund_applicable,
                'esi_applicable': self.esi_applicable,
                'location_id': self.location_id.id,
                'grade': self.grade,
                'state': 'open',  # Set the state of the new contract to Running
            }

            if existing_contract:
                # Update the existing contract to Expired state and set its end date
                existing_contract.write({
                    'state': 'close',  # Set state to Expired
                    'date_end': fields.Date.today() - timedelta(days=1)
                    # End date is the day before the new contract starts
                })

            # Create a new contract
            contract = self.env['hr.contract'].create(contract_vals)

            # Prepare the action to open the contract form view
            action = self.env.ref('hr_contract.action_hr_contract')
            result = action.sudo().read()[0]
            result.pop('id', None)  # Remove action ID
            result['views'] = [(self.env.ref('hr_contract.hr_contract_view_form').id, 'form')]
            result['res_id'] = contract.id

            return result

    @api.constrains('kra_ids')
    def _check_kra_weightage(self):
        for record in self:
            total_weightage = sum(line.weightage for line in record.kra_ids)
            if total_weightage != 100:
                raise ValidationError(
                    f"The total weightage of Self Rating must equal 100. Currently, it is {total_weightage}."
                )

    @api.constrains('manager_rating_ids')
    def _check_manager_rating_weightage(self):
        for record in self:
            total_weightage = sum(line.weightage for line in record.manager_rating_ids)
            if total_weightage != 100:
                raise ValidationError(
                    f"The total weightage of Manager Rating details must equal 100. Currently, it is {total_weightage}."
                )

    @api.constrains('goal_sets_kras')
    def _check_goal_sets_weightage(self):
        for record in self:
            total_weightage = sum(line.weightage for line in record.goal_sets_kras)
            if total_weightage != 100:
                raise ValidationError(
                    f"The total weightage of Goal Sets KRAs must equal 100. Currently, it is {total_weightage}."
                )

    @api.constrains('assessment_kra_ids')
    def _check_assessment_kra_weightage(self):
        for record in self:
            total_weightage = sum(line.weightage for line in record.assessment_kra_ids)
            if total_weightage != 100:
                raise ValidationError(
                    f"The total weightage of Assessment KRAs must equal 100. Currently, it is {total_weightage}."
                )

    @api.depends('state')
    def _compute_is_performance_record(self):
        """
        Automatically sets 'is_performance_record' to True if the state is not 'request_appraisal'.
        """
        for record in self:
            record.is_performance_record = record.state != 'request_appraisal'

    @api.depends('employee_id')
    def _compute_is_employee(self):
        current_user = self.env.user
        for record in self:
            if self.env.is_admin():
                record.is_employee = False
            elif record.employee_id:
                record.is_employee = record.employee_id.user_id == current_user
            else:
                record.is_employee = False

    # @api.depends('kra_ids', 'kra_ids.employee_weighted_score', 'manager_rating_ids',
    #              'manager_rating_ids.manager_weighted_score')
    @api.depends('kra_ids', 'manager_rating_ids')
    def _compute_totals(self):
        for record in self:
            # Initialize totals
            total_employee_score = 0.0
            total_manager_score = 0.0
            total_weightage = 0.0
            line_count_self = len(record.kra_ids) if record.kra_ids else 1
            line_count_manager = len(record.manager_rating_ids) if record.manager_rating_ids else 1

            # Calculate totals based on kra_ids
            for kra in record.kra_ids:
                total_employee_score += kra.self_rating
                # total_employee_score += kra.employee_weighted_score
                total_weightage += kra.weightage

            # Calculate totals based on manager_rating_ids
            for manager_rating in record.manager_rating_ids:
                total_manager_score += manager_rating.manager_rating
                # total_manager_score += manager_rating.manager_weighted_score

            # Assign computed values to the record
            record.total_score_employee = total_employee_score
            record.total_score_manager = total_manager_score
            # record.total_employee_weighted_score = ((record.total_score_employee / 100) / 100) * line_count_self
            # record.total_manager_weighted_score = ((record.total_score_manager / 100) / 100) * line_count_manager
            record.total_employee_weighted_score = ((record.total_score_employee) / 100) * 5
            record.total_manager_weighted_score = ((record.total_score_manager) / 100) * 5
            record.employee_final_score = record.total_employee_weighted_score
            record.manager_final_score = record.total_manager_weighted_score
            if record.manager_final_score > 4.7:
                record.pbvp_payout = 100
            elif 4.5 <= record.manager_final_score <= 4.7:
                record.pbvp_payout = 90
            elif 4.0 <= record.manager_final_score < 4.5:
                record.pbvp_payout = 80
            elif 3.5 <= record.manager_final_score < 4.0:
                record.pbvp_payout = 70
            elif 3.0 <= record.manager_final_score < 3.5:
                record.pbvp_payout = 50
            elif 2.5 <= record.manager_final_score < 3.0:
                record.pbvp_payout = 30
            else:
                record.pbvp_payout = 0

    def action_request_appraisal(self):
        for record in self:
            record.state = 'preparation'

    def action_submit_performance_review(self):
        """Move state to 'preparation_clarification' after submission."""
        for record in self:
            if any(not kra.employee_response or not kra.self_rating for kra in record.kra_ids):
                raise ValidationError(
                    _("You must fill in the Employee Justification and Self Rating before submission."))
            record.state = 'preparation_clarification'

    def action_manager_review(self):
        """Move state to 'half_year_pending' after Manager Review."""
        for record in self:
            if any(not manager.manager_rating or not manager.manager_remark for manager in record.manager_rating_ids):
                raise ValidationError(_("You must fill in the Rating and Remark before proceeding."))
            record.state = 'half_year_pending'
            record.recommended_pbvp_payout = record.pbvp_payout

    def action_hod_review(self):
        """Move state to 'full_year_pending' after HOD Review."""
        for record in self:
            if not record.remark:
                raise ValidationError(_("You must fill in the Remark field before proceeding."))
            record.state = 'full_year_pending'

    def action_director_review(self):
        """Move state to 'review_completed' after Director Review."""
        for record in self:
            for record in self:
                if not record.director_remark:
                    raise ValidationError(_("You must fill in the Remark field before proceeding."))
            record.state = 'review_completed'

    def action_refuse_request(self):
        return {
            'name': 'Refuse Form',
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'performance.review.refuse.popup',
            'view_id': self.env.ref('hr_appraisal_extended.view_performance_review_refuse_popup').id,
            'target': 'new',
            'context': {'default_employee_rating_id': self.id},
        }

    def send_increment_letter_job_level_approved(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_increment_letters_new')
            if not template_id:
                raise UserError(_("Increment letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            if record.monthly_fixed_salary <= 0:
                raise ValidationError("Please fill the Salary Breakup Details")

            ctx = dict(
                default_model='self.rating',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Increment Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def send_appraisal_letter(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_appraisal_letters')
            if not template_id:
                raise UserError(_("Increment letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            if record.monthly_fixed_salary <= 0:
                raise ValidationError("Please fill the Salary Breakup Details")

            ctx = dict(
                default_model='self.rating',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Appraisal Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def send_annual_increment_promotion_letter(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_annual_increment_promotion_letters')
            if not template_id:
                raise UserError(_("Increment letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            if record.monthly_fixed_salary <= 0:
                raise ValidationError("Please fill the Salary Breakup Details")

            ctx = dict(
                default_model='self.rating',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Annual Increment Promotion Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def send_increment_redesignation_letter(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_increment_redesignation_letter_iim_job_approved')
            if not template_id:
                raise UserError(_("Increment Redesignation letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            if record.monthly_fixed_salary <= 0:
                raise ValidationError("Please fill the Salary Breakup Details")

            ctx = dict(
                default_model='self.rating',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Increment & Redesignation Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }


    def send_variable_pay_letter(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_variable_pay_letters')
            if not template_id:
                raise UserError(_("Variable Pay template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            if record.monthly_fixed_salary <= 0:
                raise ValidationError("Please fill the Salary Breakup Details")

            ctx = dict(
                default_model='self.rating',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Variable Pay Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }


class PerformanceReviewKRA(models.Model):
    _name = 'performance.review.kra'
    _description = 'Performance Review KRA'

    rating_id = fields.Many2one('self.rating', string="Review")
    category = fields.Char(string="Category")
    kra = fields.Char(string="KRA")
    goal_description = fields.Text(string="Goal Description")
    weightage = fields.Float(string="Weightage (%)")


class SelfRatingKRA(models.Model):
    _name = 'self.rating.kra'
    _description = 'KRA Details'

    rating_id = fields.Many2one('self.rating', string="Self Rating Reference", ondelete='cascade')
    name = fields.Char(string="KRA")
    weightage = fields.Float(string="Weightage (%)")
    employee_response = fields.Text(string="Employee's Justification")
    appraiser_remarks = fields.Text(string="Appraiser's Remarks")
    self_rating = fields.Float(string="Self Rating", help="Rating given by the Employee")
    goal_description = fields.Text(string="Goal Description")
    achieved_percentage = fields.Integer(string="Achieved Percentage", compute="_compute_achieved_percentage",
                                         store=True)
    employee_weighted_score = fields.Float(string='Employee Weighted Score', compute='_compute_weighted_scores',
                                           store=True)

    @api.depends('weightage', 'achieved_percentage')
    def _compute_weighted_scores(self):
        for line in self:
            line.employee_weighted_score = 0.0
            # line.employee_weighted_score = (line.weightage * line.achieved_percentage)

    @api.depends('self_rating', 'weightage')
    def _compute_achieved_percentage(self):
        for record in self:
            if record.weightage:
                record.achieved_percentage = (record.self_rating / record.weightage) * 100
            else:
                record.achieved_percentage = 0

    @api.constrains('self_rating', 'weightage')
    def _validate_self_rating_values(self):
        for record in self:
            if record.self_rating < 0 or record.weightage < 0:
                raise ValidationError("Negative values are not allowed for Self Rating or Weightage.")
            if record.self_rating > record.weightage:
                raise ValidationError("Self Rating cannot exceed the given Weightage.")


class ManagerRating(models.Model):
    _name = 'manager.rating'
    _description = 'Manager Rating'

    rating_id = fields.Many2one('self.rating', string="Self Rating", ondelete='cascade')
    name = fields.Char(string="KRA")
    weightage = fields.Float(string="Weightage (%)")
    manager_rating = fields.Float(string="Manager Rating", help="Rating given by the manager")
    manager_remark = fields.Text(string="Manager Remark")
    achieved_percentage = fields.Integer(string="Achieved Percentage", compute="_compute_achieved_percentage",
                                         store=True)
    manager_weighted_score = fields.Float(string='Manager Weighted Score', compute='_compute_weighted_scores',
                                          store=True)

    def write(self, vals):
        """
        Restrict editing if appraisal_meeting_confirmation is True but meeting_date_time is empty.
        """
        for record in self:
            appraisal = record.rating_id
            if appraisal and not appraisal.meeting_date_time:
                raise ValidationError(
                    "You cannot edit values because the Meeting Date & Time is not set in Self Rating Page.")
        return super(ManagerRating, self).write(vals)

    @api.depends('weightage', 'achieved_percentage')
    def _compute_weighted_scores(self):
        for line in self:
            line.manager_weighted_score = 0.0
            # line.manager_weighted_score = (line.weightage * line.achieved_percentage)

    @api.depends('manager_rating', 'weightage')
    def _compute_achieved_percentage(self):
        for record in self:
            if record.weightage:
                record.achieved_percentage = (record.manager_rating / record.weightage) * 100
            else:
                record.achieved_percentage = 0

    @api.constrains('manager_rating', 'weightage')
    def _validate_manager_rating_values(self):
        for record in self:
            if record.manager_rating < 0 or record.weightage < 0:
                raise ValidationError("Negative values are not allowed for Manager Rating or Weightage.")
            if record.manager_rating > record.weightage:
                raise ValidationError("Manager Rating cannot exceed the given Weightage.")


# class DirectorRating(models.Model):
#     _name = 'director.rating'
#     _description = 'Director Rating'
#
#     rating_id = fields.Many2one('self.rating', string="Self Rating", ondelete='cascade')
#     name = fields.Char(string="KRA", readonly=True)
#     weightage = fields.Float(string="Weightage (%)", readonly=True)
#     overall_final_rating = fields.Float(string="Overall Final Rating", help="Final Rating given by the Director")
#     director_remark = fields.Text(string="Director Remark")


class SelfRatingAssessmentKRA(models.Model):
    _name = 'self.rating.assessment.kra'
    _description = 'Assessment KRA Details'

    rating_id = fields.Many2one('self.rating', string="Self Rating Reference", ondelete='cascade')
    name = fields.Char(string="KRA")
    weightage = fields.Float(string="Weightage (%)")
    employee_rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Satisfactory'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string="Employee's Rating", default='3')
    appraiser_rating = fields.Selection([
        ('1', '1 - Poor'),
        ('2', '2 - Satisfactory'),
        ('3', '3 - Good'),
        ('4', '4 - Very Good'),
        ('5', '5 - Excellent'),
    ], string="Appraiser's Rating")


class SelfRatingDevelopmentPlan(models.Model):
    _name = 'self.rating.development.plan'
    _description = 'Employee Development Plan'

    rating_id = fields.Many2one('self.rating', string="Self Rating Reference", ondelete='cascade')
    action = fields.Char(string="Action")
    timeline = fields.Char(string="Time Line")
    by_whom = fields.Many2one('hr.employee', string="By Whom")
    remarks = fields.Text(string="Remarks")


class PerformanceReviewComment(models.Model):
    _name = 'performance.review.comment'
    _description = 'Performance Review Comment'

    rating_id = fields.Many2one('self.rating', string="Review")
    commented_by = fields.Many2one('res.users', string="Commented By")
    comments = fields.Text(string="Comments")
    commented_date = fields.Datetime(string="Commented Date", default=fields.Datetime.now)
    need_response_from = fields.Many2one('hr.employee', string="Need Response From")


class PerformanceReviewLine(models.Model):
    _name = 'performance.review.line'
    _description = 'Performance Review Line'

    review_id = fields.Many2one('self.rating', string='Performance Review', ondelete='cascade')
    kra = fields.Char(string='KRA')
    description = fields.Char(string='Description')
    weightage = fields.Float(string='Weightage (%)')
    employee_score = fields.Float(string='Employee Score (%)')
    employee_weighted_score = fields.Float(string='Employee Weighted Score', compute='_compute_weighted_scores',
                                           store=True)
    manager_weightage = fields.Float(string='Manager Weightage (%)')
    manager_score = fields.Float(string='Manager Score (%)')
    manager_weighted_score = fields.Float(string='Manager Weighted Score', compute='_compute_weighted_scores',
                                          store=True)

    @api.depends('weightage', 'employee_score', 'manager_weightage', 'manager_score')
    def _compute_weighted_scores(self):
        for line in self:
            line.employee_weighted_score = 0.0
            line.manager_weighted_score = 0.0
            # line.employee_weighted_score = (line.weightage * line.employee_score)
            # line.manager_weighted_score = (line.manager_weightage * line.manager_score)


class SalaryMaster(models.Model):
    _name = 'salary.master'
    _description = 'Salary Structure'

    name = fields.Char()
    location = fields.Selection([
        ('corporate', 'Corporate'),
        ('bangalore', 'Bangalore'),
        ('ttc', 'TTC'),
        ('ttk', 'TTK'),
        ('cbm', 'CBM'),
        ('lilac1', 'Lilac 1'),
        ('lilac2', 'Lilac 2'),
        ('tta', 'TTA'),
        ('tvm_obt', 'TVM/OBT'),
    ], string="Location", required=True)
    location_id = fields.Many2one('location.master', string="Location")

    grade = fields.Selection([
        ('spl_grade', 'Spl Grade'),
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
        ('grade_d', 'Grade D'),
        ('grade_e', 'Grade E'),
        ('grade_f', 'Grade F'),
        ('grade_g', 'Grade G'),
    ], string="Grade", required=True)

    monthly_salary = fields.Float(string="Monthly Salary", required=True)
    annual_salary = fields.Float(string="Annual Salary", required=True)
