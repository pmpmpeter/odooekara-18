# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command, tools
from odoo.exceptions import *
from odoo.exceptions import UserError, ValidationError
import math, re
from num2words import num2words

class SalaryBreakupLine(models.Model):
    _name = "salary.breakup.lines"
    _description = "Salary Breakup Lines"

    applicant_id = fields.Many2one("hr.applicant", string="Applicant")
    salary_proposed = fields.Float(string="Proposed Salary")
    salary_breakup_type = fields.Selection([
        ('breakup_one', 'One'),
        ('breakup_two', 'Two'),
        ('breakup_three', 'Three'),
    ], string="Type", required=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', string="Director Approval Status")
    final_state = fields.Selection([
        ('draft', 'Draft'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', string="HR Approval Status")

    # Compensation basic input fields
    monthly_fixed_salary = fields.Float(string="Monthly Fixed Salary (excl PF & all incentive pay)")

    statutory_bonus_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Statutory Bonus Applicable",
        default='no',
        required=True,
    )
    provident_fund_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Provident Fund Applicable",
        default='no',
        required=True,
    )
    esi_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="ESI Applicable",
        default='no',
        required=True,
    )

    variable_pay_percentage = fields.Float(string="Percentage of Variable Pay")

    grade = fields.Selection([
        ('spl_grade', 'Spl Grade'),
        ('grade_a', 'Grade A'),
        ('grade_b', 'Grade B'),
        ('grade_c', 'Grade C'),
        ('grade_d', 'Grade D'),
        ('grade_e', 'Grade E'),
        ('grade_f', 'Grade F'),
        ('grade_g', 'Grade G'),
    ], string="Grade", default='spl_grade', required=True)

    locations_id = fields.Many2one(
        'location.master',
        string="Location"
    )

    medical_insurance = fields.Float(string="Medical Insurance")
    group_personal_accident_insurance = fields.Float(string="Group Personal Accident Insurance")
    health_benefit_plan = fields.Float(string="Health Benefit Plan")
    indicative_take_home_salary = fields.Float(string="Indicative Take Home Salary Per Month")

    # Salary breakup – Per Annum
    basic_da_per_annum = fields.Float(string='Basic & DA')
    hra_per_annum = fields.Float(string='House Rent Allowance')
    special_allowance_per_annum = fields.Float(string='Special Allowance')
    sub_total_a_per_annum = fields.Float(string='Sub-total Part A')

    statutory_bonus_per_annum = fields.Float(string='Statutory Bonus')
    pf_employer_per_annum = fields.Float(string="Provident Fund (Employer Contribution)")
    esic_employer_per_annum = fields.Float(string='ESIC (Employer Contribution)')
    sub_total_b_per_annum = fields.Float(string='Sub-total Part B')

    store_performance_incentive_annum = fields.Float(string="Store Performance Incentive")
    monthly_performance_incentive_annum = fields.Float(string="Monthly Performance Incentive")
    variable_pay_per_annum = fields.Float(string='Performance Linked Variable Pay')
    performance_linked_pay_annum = fields.Float(string='Performance Linked Pay')
    sub_total_c_per_annum = fields.Float(string='Sub-total Part C')

    total_salary_per_annum = fields.Float(string='Total Salary')

    medical_insurances = fields.Float(string='Medical Insurance')
    group_personal_acc_insurance = fields.Float(string='Group Personal Accident Insurance')
    health_ben_plan = fields.Float(string='Health Benefit Plan')
    sub_total_d = fields.Float(string='Sub-total Part D')

    total_ctc_annum = fields.Float(string='Total Cost to Company')

    # Salary breakup – Per Month
    basic_da_per_month = fields.Float(string='Basic & DA')
    hra_per_month = fields.Float(string='House Rent Allowance')
    special_allowance_per_month = fields.Float(string='Special Allowance')
    sub_total_a_per_month = fields.Float(string='Sub-total Part A')

    statutory_bonus_per_month = fields.Float(string='Statutory Bonus')
    pf_employer_per_month = fields.Float(string="Provident Fund (Employer Contribution)")
    esic_employer_per_month = fields.Float(string='ESIC (Employer Contribution)')
    sub_total_b_per_month = fields.Float(string='Sub-total Part B')

    store_performance_incentive_month = fields.Float(string="Store Performance Incentive")
    monthly_performance_incentive_month = fields.Float(string="Monthly Performance Incentive")
    variable_pay_per_month = fields.Float(string='Performance Linked Variable Pay')
    performance_linked_pay_month = fields.Float(string='Performance Linked Pay')
    sub_total_c_per_month = fields.Float(string='Sub-total Part C')

    total_salary_per_month = fields.Float(string='Total Salary')

    total_ctc_month = fields.Float(string='Total Cost to Company')


    def calculate_salary(self):
        if not self.locations_id:
            raise UserError("Warning!! Kindly Select Location")
        self.applicant_id.salary_proposed= self.salary_proposed
        self.applicant_id.monthly_fixed_salary= self.monthly_fixed_salary
        self.applicant_id.statutory_bonus_applicable = self.statutory_bonus_applicable
        self.applicant_id.provident_fund_applicable = self.provident_fund_applicable
        self.applicant_id.esi_applicable = self.esi_applicable
        self.applicant_id.variable_pay_percentage = self.variable_pay_percentage
        self.applicant_id.grade = self.grade
        self.applicant_id.locations_id = self.locations_id.id
        self.applicant_id.medical_insurance = self.medical_insurance
        self.applicant_id.group_personal_accident_insurance = self.group_personal_accident_insurance
        self.applicant_id.health_benefit_plan = self.health_benefit_plan
        self.applicant_id._onchange_calculate_salary_breakup()
        self.indicative_take_home_salary = self.applicant_id.indicative_take_home_salary
        # Per Annum
        self.basic_da_per_annum = self.applicant_id.basic_da_per_annum
        self.hra_per_annum = self.applicant_id.hra_per_annum
        self.special_allowance_per_annum = self.applicant_id.special_allowance_per_annum
        self.sub_total_a_per_annum = self.applicant_id.sub_total_a_per_annum
        self.statutory_bonus_per_annum = self.applicant_id.statutory_bonus_per_annum
        self.pf_employer_per_annum = self.applicant_id.pf_employer_per_annum
        self.esic_employer_per_annum = self.applicant_id.esic_employer_per_annum
        self.sub_total_b_per_annum = self.applicant_id.sub_total_b_per_annum
        self.store_performance_incentive_annum = self.applicant_id.store_performance_incentive_annum
        self.monthly_performance_incentive_annum = self.applicant_id.monthly_performance_incentive_annum
        self.variable_pay_per_annum = self.applicant_id.variable_pay_per_annum
        self.performance_linked_pay_annum = self.applicant_id.performance_linked_pay_annum
        self.sub_total_c_per_annum = self.applicant_id.sub_total_c_per_annum
        self.total_salary_per_annum = self.applicant_id.total_salary_per_annum
        self.medical_insurances = self.applicant_id.medical_insurances
        self.group_personal_acc_insurance = self.applicant_id.group_personal_acc_insurance
        self.health_ben_plan = self.applicant_id.health_ben_plan
        self.sub_total_d = self.applicant_id.sub_total_d
        self.total_ctc_annum = self.applicant_id.total_ctc_annum
        # Per Month
        self.basic_da_per_month = self.applicant_id.basic_da_per_month
        self.hra_per_month = self.applicant_id.hra_per_month
        self.special_allowance_per_month = self.applicant_id.special_allowance_per_month
        self.sub_total_a_per_month = self.applicant_id.sub_total_a_per_month
        self.statutory_bonus_per_month = self.applicant_id.statutory_bonus_per_month
        self.pf_employer_per_month = self.applicant_id.pf_employer_per_month
        self.esic_employer_per_month = self.applicant_id.esic_employer_per_month
        self.sub_total_b_per_month = self.applicant_id.sub_total_b_per_month
        self.store_performance_incentive_month = self.applicant_id.store_performance_incentive_month
        self.monthly_performance_incentive_month = self.applicant_id.monthly_performance_incentive_month
        self.variable_pay_per_month = self.applicant_id.variable_pay_per_month
        self.performance_linked_pay_month = self.applicant_id.performance_linked_pay_month
        self.sub_total_c_per_month = self.applicant_id.sub_total_c_per_month
        #Total
        self.total_salary_per_month = self.applicant_id.total_salary_per_month
        self.total_ctc_month = self.applicant_id.total_ctc_month

        return {
            'type': 'ir.actions.act_window',
            'name': 'Salary Breakup',
            'view_mode': 'form',
            'res_model': 'salary.breakup.lines',
            'res_id': self.id,
            'target': 'new',  # Popup
        }



    def action_hr_approve(self):
        self.write({'final_state': 'approved'})
        line_ids = self.search([('applicant_id','=',self.applicant_id.id),('id','!=',self.id)])
        line_ids.update({'final_state':'rejected'})
        self.applicant_id.salary_proposed = self.salary_proposed
        self.applicant_id.monthly_fixed_salary = self.monthly_fixed_salary
        self.applicant_id.statutory_bonus_applicable = self.statutory_bonus_applicable
        self.applicant_id.provident_fund_applicable = self.provident_fund_applicable
        self.applicant_id.esi_applicable = self.esi_applicable
        self.applicant_id.variable_pay_percentage = self.variable_pay_percentage
        self.applicant_id.grade = self.grade
        self.applicant_id.locations_id = self.locations_id.id
        self.applicant_id.medical_insurance = self.medical_insurance
        self.applicant_id.group_personal_accident_insurance = self.group_personal_accident_insurance
        self.applicant_id.health_benefit_plan = self.health_benefit_plan
        self.applicant_id._onchange_calculate_salary_breakup()
        self.applicant_id.salary_breakup_approved = True

    def action_approve(self):
        self.write({'state': 'approved'})


    def action_hr_reject(self):
        self.write({'final_state': 'rejected'})

    def action_reject(self):
        self.write({'state': 'rejected','final_state':'rejected'})

    def action_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Salary Breakup',
            'view_mode': 'form',
            'res_model': 'salary.breakup.lines',
            'res_id': self.id,
            'target': 'new',  # Popup
        }
class RecruitmentStage(models.Model):
    _inherit = "hr.recruitment.stage"

    stage = fields.Selection(
        selection=[
            ('new', 'New'),
            ('initial', 'Initial Qualification'),
            ('first_level', 'First Level Interview'),
            ('second_interview', 'Second Interview'),
            ('shortlist', 'Shortlist'),
            ('document_validated', 'Document Validated'),
            ('director_approval', 'Director Approved'),
            ('offer_accepted', 'Offer Accepted'),
            ('hold', 'Hold')
        ],
        string='Stage',
    )


class HrJobKra(models.Model):
    _inherit = "hr.job"

    kra_master = fields.Many2one('kra.master', string='KRA', copy=False,
                                 help="Select the Key Result Area (KRA) Master associated with this applicant.")

    def unlink(self):
        """Check if the record is referenced before deletion."""
        related_fields = self.env['ir.model.fields'].search([
            ('ttype', 'in', ['many2one', 'many2many']),
            ('relation', '=', 'hr.job'),
        ])
        for record in self:
            for field in related_fields:
                model = self.env[field.model]
                if field.ttype == 'many2one':
                    references = model.search([(field.name, '=', record.id)])
                elif field.ttype == 'many2many':
                    references = model.search([(field.name, 'in', [record.id])])
                else:
                    continue

                if references:
                    model_name = self.env['ir.model']._get(field.model).name
                    referenced_ids = references.mapped('id')
                    raise ValidationError(
                        f"You cannot delete the record '{record.name}' as it is referenced in the model '{model_name}'."
                    )
        return super(HrJobKra, self).unlink()


class Job_Applicant(models.Model):
    _inherit = "hr.applicant"

    # sourcing_type = fields.Selection(
    #     [('internal_sourcing', 'Internal Sourcing'), ('external_sourcing', 'External Sourcing')],
    #     string="Sourcing Type", default='external_sourcing', required=True, copy=False,
    #     help="This field specifies the source of the candidate's CV")
    #
    # referred_by = fields.Many2one(
    #     'res.users',
    #     string='Referred By', copy=False,
    #     help="The employee who referred this candidate."
    # )
    document_sent = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Document Sent", default='no', copy=False, readonly=True)
    offer_letter_approved = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Offer Letter Approval", default='no', copy=False, readonly=True)
    offer_letter_sent_director = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Offer Letter Sent", default='no', copy=False, readonly=True)

    offer_letter_sent = fields.Selection([
        ('yes', 'Yes'),
        ('no', 'No'),
    ], string="Offer Letter Sent", default='no', copy=False, readonly=True)
    grade_job_level_id = fields.Many2one('hr.job.levels', string='Job Levels', copy=False)
    verification_date = fields.Date(string="Verification Due Date", copy=False)

    # is_pre_emp_form_clicked = fields.Boolean(string="Pre-Employment Form Clicked", default=False, copy=False)

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
    total_ctc_in_words = fields.Char(string="Total CTC In Words", compute='_compute_total_ctc_in_words')

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
    ], default='corporate', string="Location", tracking=True, required=False)
    locations_id = fields.Many2one('location.master', string="Location", tracking=True)
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

    last_stage_id = fields.Many2one('hr.recruitment.stage', string='Last Stage', copy=False)
    stage_status = fields.Selection(
        related='stage_id.stage',
        string='Stage Status',
        store=True,
        readonly=False,  # Allows updates if required
    )
    first_invitation_letter_ids = fields.Many2many('applicant.invitation.letter',
                                                   compute='_compute_first_invitation_letter',
                                                   string='Invitation Letters', copy=False)
    first_invitation_letter_count = fields.Integer("Invitation Letter Count",
                                                   compute='_compute_first_invitation_letter', default=0, copy=False)
    interview_assessment_letter_ids = fields.Many2many('interview.assessment',
                                                       compute='_compute_interview_assessment_letter',
                                                       string='Assessment Letters', copy=False)
    interview_assessment_letter_count = fields.Integer("Assessment Letter Count",
                                                       compute='_compute_interview_assessment_letter', default=0,
                                                       copy=False)
    # base field
    interviewer_ids = fields.Many2many('res.users', 'hr_applicant_res_users_interviewers_rel',
                                       compute='_compute_interviewer_ids',
                                       string='Interviewers', index=True, tracking=True, store=True, readonly=False,
                                       domain="[('share', '=', False), ('company_ids', 'in', company_id)]")
    document_ids = fields.One2many("hr.applicant.document", "applicant_id", string="Documents")
    refuse_count = fields.Integer(string="Refusal Count")
    salary_breakup_ids = fields.One2many(
        "salary.breakup.lines",
        "applicant_id",
        string="Salary Breakup"
    )
    salary_breakup_added = fields.Boolean(default=False)
    salary_breakup_approved = fields.Boolean(default=False)

    def action_create_breakup_lines(self):
        """
        # Ensures existing and new applicants always have 3 breakup lines:
        # breakup one, breakup two, breakup three
        # """
        if not self.salary_breakup_added and not self.salary_breakup_ids:
            for rec in self:
                required = ['breakup_one', 'breakup_two', 'breakup_three']
                existing = rec.salary_breakup_ids.mapped('salary_breakup_type')

                missing = list(set(required) - set(existing))

                for m in missing:
                    self.env['salary.breakup.lines'].create({
                        'applicant_id': rec.id,
                        'salary_breakup_type': m,
                    })
            self.salary_breakup_added = True

    def action_send_offer_offer_letter_for_approval(self):
        for record in self:
            user = self.env['employee.indent'].search([('job_id','=',record.job_id.id)]).director_approval_id
            if user:
                record.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary="Offer Letter – Director Approval Required",
                    note=f"Offer letter for {record.partner_name} has been sent for your approval.",
                    user_id=user.id,
                    date_deadline=fields.Date.today(),
                )

            record.offer_letter_sent_director = "yes"

    def action_refuse_employee_documents(self):
        self.document_sent='no'
        return True

    def action_approve_employee_documents(self):
        next_stage = self.env['hr.recruitment.stage'].search([('stage', '=', 'document_validated')], limit=1)
        if not next_stage:
            raise UserError("The 'Document Validated' stage is not configured. Please create it in Recruitment Stages.")
        self.stage_id = next_stage.id

    def action_view_documents(self):
        return {
            "type": "ir.actions.act_window",
            "name": "Applicant Documents",
            "res_model": "hr.applicant.document",
            "view_mode": "list,form",
            "domain": [("applicant_id", "=", self.id)],
            "context": {"default_applicant_id": self.id},
        }

    def get_document_upload_link(self):
        """Generate public link (no login needed)"""
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        link =  f"{base_url}/applicant/upload/{self.id}"
        raise ValidationError(link)
        return link
        # return f"{base_url}/applicant/upload/{self.id}"

    @api.onchange('total_ctc_annum')
    def _compute_total_ctc_in_words(self):
        for record in self:
            if record.total_ctc_annum:
                total_ctc_integer = int(record.total_ctc_annum)
                record.total_ctc_in_words = num2words(total_ctc_integer, lang='en_IN').title()
            else:
                record.total_ctc_in_words = 'None'

    def write(self, vals):
        result = super(Job_Applicant, self).write(vals)
        for record in self:
            if not record.email_from:
                raise ValidationError("Please fill the Email")
            if not record.partner_phone:
                raise ValidationError("Please fill the Phone Number")
            if not record.linkedin_profile:
                raise ValidationError("Please fill the LinkedIn Profile")
        return result

    def unlink(self):
        for record in self:
            if record.stage_id.stage != 'new':
                raise ValidationError(_("You can only delete applications that are in the 'New' state."))

        return super(Job_Applicant, self).unlink()

    @api.depends('job_id')
    def _compute_interviewer_ids(self):
        for applicant in self:
            applicant.interviewer_ids = applicant.job_id.interviewer_ids.ids

    @api.constrains('email_from', 'email_cc', 'partner_phone')
    def validate_contact_info(self):
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        phone_regex = r'^(\+91)?[6-9][0-9]{9}$'

        for record in self:
            if not record.email_from:
                raise ValidationError("Please fill the Email")

            if record.email_from and not re.match(email_regex, record.email_from):
                raise ValidationError(f"Expected format: example@domain.com")

            if record.email_cc and not re.match(email_regex, record.email_cc):
                raise ValidationError(f"Invalid email: '{record.email_cc}'.\n"
                                      "Expected format: example@domain.com")

            if not record.partner_phone:
                raise ValidationError("Please fill the Phone Number")

            if record.partner_phone:
                record.partner_phone = record.partner_phone.replace(" ", "")
                if not re.match(phone_regex, record.partner_phone):
                    raise ValidationError(f"Invalid Phone Number: '{record.partner_phone}'.\n"
                                          "Expected format: A 10-digit number starting with 6-9, "
                                          "optionally prefixed with +91. Example: +919876543210")

            # if record.partner_mobile:
            #     record.partner_mobile = record.partner_mobile.replace(" ", "")
            #     if not re.match(phone_regex, record.partner_mobile):
            #         raise ValidationError(f"Invalid Mobile Number: '{record.partner_mobile}'.\n"
            #                               "Expected format: A 10-digit number starting with 6-9, "
            #                               "optionally prefixed with +91. Example: +919876543210")

            if not record.linkedin_profile:
                raise ValidationError("Please fill the LinkedIn Profile")

    @api.onchange('locations_id', 'monthly_fixed_salary', 'statutory_bonus_applicable', 'provident_fund_applicable',
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
                ('location_id', '=', record.locations_id.id),
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
                if record.locations_id.name == 'TTA' and record.grade == 'grade_d':
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

            elif (record.locations_id.name not in ['tta', 'tvm_obt']) and (record.monthly_fixed_salary >= 54000):
                # Calculate Basic & DA (Per Annum)
                record.basic_da_per_annum = round((record.monthly_fixed_salary * 12 * 0.4) / 12000) * 12000
                record.hra_per_annum = record.basic_da_per_annum * 0.40

                # Calculate (Per Month)
                record.basic_da_per_month = round(record.basic_da_per_annum / 12)
                record.hra_per_month = round(record.hra_per_annum / 12)

                # Statutory Bonus Logic
                if record.locations_id.name == 'TTA' and record.grade == 'grade_d':
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

            elif (record.locations_id.name not in ['tta', 'tvm_obt']) and (record.monthly_fixed_salary < 54000):
                # Calculate Basic & DA (Per Annum)
                record.basic_da_per_annum = round((record.monthly_fixed_salary * 12 * 0.4) / 12000) * 12000
                record.hra_per_annum = record.basic_da_per_annum * 0.40

                # Calculate (Per Month)
                record.basic_da_per_month = round(record.basic_da_per_annum / 12)
                record.hra_per_month = round(record.hra_per_annum / 12)

                # Statutory Bonus Logic
                if record.locations_id.name == 'TTA' and record.grade == 'grade_d':
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

    def _compute_interview_assessment_letter(self):
        for record in self:
            domain = [('applicant_id', '=', record.id)]
            interview_assessment_letter_ids = self.env['interview.assessment'].sudo().search(domain)
            record.interview_assessment_letter_ids = interview_assessment_letter_ids
            record.interview_assessment_letter_count = len(interview_assessment_letter_ids)

    def action_open_interview_assessment_letter(self):
        action = self.env.ref('hr_extended.action_interview_assessment')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.interview_assessment_letter_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.interview_assessment_letter_ids.ids)) + "])]"
        elif len(self.interview_assessment_letter_ids.ids) == 1:
            res = self.env.ref('hr_extended.view_interview_assessment_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.interview_assessment_letter_ids.ids and self.interview_assessment_letter_ids.ids[
                0] or False
        return result

    def _compute_first_invitation_letter(self):
        for record in self:
            domain = [('applicant_id', '=', record.id)]
            first_invitation_letter_ids = self.env['applicant.invitation.letter'].sudo().search(domain)
            record.first_invitation_letter_ids = first_invitation_letter_ids
            record.first_invitation_letter_count = len(first_invitation_letter_ids)

    def action_open_invitation_letter(self):
        action = self.env.ref('hr_extended.applicant_invitation_letter_action')
        result = action.sudo().read()[0]
        result.pop('id', None)
        result['context'] = {}
        if len(self.first_invitation_letter_ids.ids) > 1:
            result['domain'] = "[('id','in',[" + ','.join(map(str, self.first_invitation_letter_ids.ids)) + "])]"
        elif len(self.first_invitation_letter_ids.ids) == 1:
            res = self.env.ref('hr_extended.applicant_invitation_letter_form_view', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.first_invitation_letter_ids.ids and self.first_invitation_letter_ids.ids[0] or False
        return result

    def get_next_stage_name_applicant(self):
        self.ensure_one()
        stage_mapping = {
            'new': 'initial',
            'initial': 'first_level',
            'first_level': 'second_interview',
            'second_interview': 'shortlist',
        }
        next_stage_key = stage_mapping.get(self.stage_id.stage)
        next_stage = self.env['hr.recruitment.stage'].search([('stage', '=', next_stage_key)], limit=1)
        return next_stage.name if next_stage else "No Next Stage Defined"

    def action_send_first_invitiation(self):
        # self.get_document_upload_link()
        if not self.interviewer_ids:
            raise ValidationError("The 'Interviewer' field is required to create an Invitation.")
        if not self.job_id:
            raise ValidationError("Please fill the Job details.")
        if not self.partner_name:
            raise UserError(_("Please fill the name of the Applicant"))
        if not self.email_from:
            raise UserError(_("Please fill the Email of the Applicant"))
        if not self.user_id:
            raise UserError(_("Please fill the Recruiter for the Applicant"))
        next_stage = self.get_next_stage_name_applicant()
        letter_heading = 'Invitation Letter - ' + str(next_stage)

        existing_letter = self.env['applicant.invitation.letter'].search([
            ('applicant_id', '=', self.id),
            ('state', 'in', ['draft', 'sent'])
        ], limit=1)

        if existing_letter:
            raise ValidationError(_("A invitation letter already exists for this applicant."))

        vals = {
            'applicant_id': self.id,
            'user_id': self.user_id.id,
            'interviewer_ids': self.interviewer_ids.ids,
            'letter_heading': letter_heading,
            # 'stage_id':self.stage_id.name
        }
        first_invitation_id = self.env['applicant.invitation.letter'].create(vals)
        # self.write({'stage_id': 1})
        ctx = self.env.context.copy()
        # ctx.update({'default_move_type': 'out_receipt'})
        return {
            'name': _('Invitation Letter'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'applicant.invitation.letter',
            'view_id': self.env.ref('hr_extended.applicant_invitation_letter_form_view').id,
            'context': ctx,
            'res_id': first_invitation_id.id,
        }

    # def action_open_related_candidate(self):
    #     self.ensure_one()
    #     candidate = self.env['preemp.check'].search(
    #         [('applicant_id', '=', self.id), ('candidate_name', '=', self.partner_name),
    #          ('candidate_email', '=', self.email_from)], limit=1)
    #
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

    def get_document_update_interview_subject(self):
        """Fetch the active subject from document.update.interview.status."""
        # self.get_document_upload_link()
        document_update = self.env['document.update.interview.status'].search([('active', '=', True)], limit=1)
        if not document_update:
            raise UserError(_("No active interview update subject found."))
        return document_update.name

    

    def action_send_document_update_mail(self):
        for applicant in self.filtered(lambda s: not s.stage_id.stage):
            raise UserError(_("Alert !! Configure %s stage properly.") % (applicant.stage_id.display_name))
        for applicant in self.filtered(lambda s: s.stage_id.stage not in ['shortlist']):
            raise UserError(
                _("Alert !! You cannot send document update at %s stage") % (applicant.stage_id.display_name))
        for applicant in self.filtered(lambda s: s.stage_id.stage in ['shortlist']):
            if not applicant.get_document_update_interview_subject():
                raise UserError(_("Kindly update the document subject email."))
            template = self.env.ref('hr_extended.document_update_interview_status_mail')
            if not template:
                raise UserError(_("Alert !! Offer Letter template not found."))
            if not applicant.email_from:
                raise UserError(_("Alert !! Update applicant email address."))
            if applicant.email_from and template:
                template.send_mail(applicant.id, force_send=True)
                applicant.write({'document_sent': 'yes'})

    # def action_send_offer_offer_letter_for_approval(self):
    #     for record in self:
    #         record.offer_letter_sent_director = "yes"

    def action_approve_offer_letter(self):
        for record in self:
            record.offer_letter_approved = "yes"
            next_stage = self.env['hr.recruitment.stage'].search([('stage', '=', 'director_approval')], limit=1)
            if not next_stage:
                raise UserError(
                    "The 'Director Approved' stage is not configured. Please create it in Recruitment Stages.")
            record.stage_id = next_stage.id


    def action_refuse_offer_letter(self):
        """Open wizard to capture refusal reason"""
        return {
            "type": "ir.actions.act_window",
            "res_model": "hr.applicant.refuse.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"default_applicant_id": self.id},
        }
# surya
    def action_send_offer_letter_mail(self):
        for applicant in self.filtered(lambda s: not s.stage_id.stage):
            raise UserError(_("Alert !! Configure %s stage properly.") % (applicant.stage_id.display_name))
        for applicant in self.filtered(lambda s: s.stage_id.stage not in ['director_approval']):
            raise UserError(
                _("Alert !! You cannot send document update at %s stage") % (applicant.stage_id.display_name))
        for applicant in self.filtered(lambda s: s.stage_id.stage in ['director_approval']):
            template = self.env.ref('hr_extended.offer_letter_mail')
            if not template:
                raise UserError(_("Alert !! Offer Letter template not found."))
            if not applicant.email_from:
                raise UserError(_("Alert !! Update applicant email address."))
            if applicant.email_from and template:
                template.send_mail(applicant.id, force_send=True)
                applicant.write({'offer_letter_sent': 'yes'})

            # compose_form = self.env.ref('mail.email_compose_message_wizard_form', False)
            # if not compose_form:
            #     raise UserError(_("Email composition form not found."))
            # ctx = {
            #     'default_model': 'hr.applicant',
            #     'default_res_ids': applicant.ids,
            #     'default_template_id': template.id,
            #     'default_composition_mode': 'comment',
            #     'force_email': True,
            # }
            # # applicant.write({'offer_letter_sent': 'yes'})
            # return {
            #     'name': _('Compose Offer Letter Email'),
            #     'type': 'ir.actions.act_window',
            #     'view_mode': 'form',
            #     'res_model': 'mail.compose.message',
            #     'views': [(compose_form.id, 'form')],
            #     'view_id': compose_form.id,
            #     'target': 'new',
            #     'context': ctx,
            # }

    def action_first_stage_new(self):
        """move to 'New' stage"""
        for record in self:
            new_stage = self.env['hr.recruitment.stage'].search([('stage', '=', 'new')], limit=1)
            if new_stage:
                record.stage_id = new_stage.id
            else:
                raise UserError("New stage not found! Please create one in Recruitment stages.")

    def action_approve(self):
        """move to 'Shortlisted' stage"""
        for record in self:
            if hasattr(self, 'x_has_request_approval'):
                self.x_has_request_approval = False
            shortlist_stage = self.env['hr.recruitment.stage'].search([('stage', '=', 'shortlist')], limit=1)
            if shortlist_stage:
                record.stage_id = shortlist_stage.id
            else:
                raise UserError("Shortlist stage not found! Please create one in Recruitment stages.")

    def action_offer_accepted(self):
        """move to 'Offer Accepted' stage"""
        for record in self:
            offer_accepted_stage = self.env['hr.recruitment.stage'].search([('stage', '=', 'offer_accepted')], limit=1)
            if offer_accepted_stage:
                record.stage_id = offer_accepted_stage.id
            else:
                raise UserError("Offer Accepted stage not found! Please create map in Recruitment stages.")

    def action_hold(self):
        """Mark as on hold"""
        for record in self:
            hold_stage = self.env['hr.recruitment.stage'].search([('stage', '=', 'hold')], limit=1)
            record.last_stage_id = record.stage_id.id
            if hold_stage:
                record.stage_id = hold_stage.id
            else:
                raise UserError("Hold stage not found! Please create one in Recruitment stages.")

    def action_reopen(self):
        """Reopen the application from hold status"""
        for record in self:
            record.stage_id = record.last_stage_id.id

    def _create_kra_for_employee(self, employee, job_position):
        """
        Create a KRA record for the newly created employee based on the job position.
        """
        kra_model = self.env['employee.kra']
        kra_values = {
            'employee_id': employee.id,
            'emp_job_id': job_position.id,  # Explicitly set job_id
            'kra_master': job_position.kra_master.id,
        }
        kra_record = kra_model.sudo().create(kra_values)
        return kra_record

    def _create_jonining_documents_for_employee(self, employee, job_position):
        for record in self:
            joining_doc_employee = self.env['joining.documents']
            domain1 = [('active', '=', True), ('company_id', '=', self.company_id.id)]
            joining_docs = self.env['employee.join.doc.config'].sudo().search(domain1)
            if joining_docs:
                for doc in joining_docs:
                    vals = {
                        'join_doc_id': doc.id,
                        'name': doc.name,
                        'document_type': doc.document_type,
                        'subject': doc.subject,
                        'employee_id': employee.id,
                        'reference_file': doc.file,
                        'reference_filename': doc.file_name,
                        'job_position_id': employee.job_id.id,
                        'department_id': employee.department_id.id,
                        'company_id': doc.company_id.id,
                        'joining_date': self.availability,
                        'contact_id': doc.contact_id.id if doc.contact_id else False,
                    }
                    joining_record = joining_doc_employee.sudo().create(vals)
                    print(joining_record, joining_record.join_doc_id, joining_record.join_doc_id.name,
                          joining_record.sequence)
                    # raise ValidationError(888)

                    # preemp_check_vals = {
                    #     'applicant_id': self.id,
                    #     'candidate_name': self.partner_name,
                    #     'candidate_email': self.email_from,
                    # }
                    # self.env['preemp.check'].sudo().create(preemp_check_vals)

    def create_employee_from_applicant(self):
        if not self.grade_job_level_id:
            raise ValidationError("Please set the Job Level before creating an employee.")
        if not self.job_id:
            raise ValidationError("Please set the Applied Job before creating an employee.")
        if not self.department_id:
            raise ValidationError("Please set the Department before creating an employee.")
        action = super(Job_Applicant, self).create_employee_from_applicant()

        employee_id = action.get('res_id')
        if employee_id:
            employee = self.env['hr.employee'].browse(employee_id)
            if employee and self.job_id:
                employee.write({
                    'job_level_id': self.grade_job_level_id.id,  # Set job level on employee
                })
                self._create_kra_for_employee(employee, self.job_id)
                self._create_jonining_documents_for_employee(employee, self.job_id)
                self._attach_documents_to_employee(employee)
        return action

    def _attach_documents_to_employee(self, employee):
        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'hr.applicant'),
            ('res_id', '=', self.id)
        ])
        for attachment in attachments:
            attachment.copy({
                'res_model': 'hr.employee',
                'res_id': employee.id
            })

    def action_create_interview_assessment(self):
        if not self.interviewer_ids:
            raise ValidationError("The 'Interviewer' field is required to create an Interview Assessment Form.")

        for interviewer in self.interviewer_ids:
            if not interviewer.email:
                raise ValidationError(
                    f"Interviewer {interviewer.name} does not have an email address. Please provide a valid email.")

        vals = {
            'name': self.partner_name,
            'position_interviewed_for': self.job_id.name,
            'position_offered': self.job_id.id,
            'applicant_id': self.id,
            'expected_date_of_joining': self.availability,
        }

        interview_assessment_id = self.env['interview.assessment'].create(vals)

        return {
            'name': _('Interview Assessment'),
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'interview.assessment',
            'view_id': self.env.ref('hr_extended.view_interview_assessment_form').id,
            'res_id': interview_assessment_id.id,
        }

    # monthly_fixed_salary = fields.Float(string="Monthly Fixed Salary (excl PF & all incentive pay)", store=True,
    #                                     copy=False)
    # statutory_bonus_applicable = fields.Selection(
    #     [('yes', 'Yes'), ('no', 'No')], string="Statutory Bonus Applicable (per month)", default='no', required=True,
    #     copy=False
    # )
    # stat_bonus_amount = fields.Float(string="Statutory Bonus Amount", store=True, copy=False)
    # provident_fund_applicable = fields.Selection(
    #     [('yes', 'Yes'), ('no', 'No')], string="Provident Fund Applicable (per month)", default='no', required=True,
    #     copy=False
    # )
    # provident_fund = fields.Float(string="Provident Fund", store=True, copy=False, readonly=True)
    # esi_applicable = fields.Selection(
    #     [('yes', 'Yes'), ('no', 'No')], string="ESI Applicable (per month)", default='no', required=True, copy=False
    # )
    # esi_amount = fields.Float(string="ESI Amount", store=True, copy=False, readonly=True)
    # variable_pay_percentage = fields.Float(string="Percentage of Variable Pay (per annum)", store=True, copy=False)
    variable_pay_amount = fields.Float(string="Variable Pay Amounts", store=True, readonly=True, copy=False)
    # annual_store_performance_incentive = fields.Float(string="Annual Store Performance Incentive", store=True,
    #                                                   copy=False)
    # annual_performance_linked_pay = fields.Float(string="Annual Performance Linked Pay", store=True, copy=False)
    # monthly_performance_incentive = fields.Float(string="Monthly Performance Incentive", store=True, copy=False)
    # medical_insurance = fields.Float(string="Medical Insurance", store=True, copy=False)
    # group_personal_accident_insurance = fields.Float(string="Group Personal Accident Insurance", store=True, copy=False)
    # solis_health_benefit_beacon_plan = fields.Float(string="Solis Health Benefit Beacon Plan", store=True, copy=False)
    # indicative_take_home_salary = fields.Float(string="Indicative Take Home Salary Per Month", store=True, copy=False)
    basic_da = fields.Float(string="Basic & DA (PA)", store=True, copy=False)
    house_rent_allowance = fields.Float(string="House Rent Allowance (PA)", store=True, copy=False)
    special_allowance = fields.Float(string="Special Allowance (PA)", store=True, copy=False)
    # there is calculation for this take home salary
    grade_id = fields.Many2one('hr.job.levels', string="Grade",
                               copy=False)  # Create a custom model for grades if needed
    location_id = fields.Many2one('res.country.state', string="Location",
                                  copy=False)  # Using states as an example for locations

# # To fix the value as 0.0
# @api.constrains('statutory_bonus_applicable')
# def _check_statutory_bonus(self):
#     for record in self:
#         if record.statutory_bonus_applicable == 'no':
#             record.stat_bonus_amount = 0.0
#
# @api.constrains('provident_fund_applicable')
# def _check_provident_fund(self):
#     for record in self:
#         if record.provident_fund_applicable == 'no':
#             record.provident_fund = 0.0
#
# @api.constrains('esi_applicable')
# def _check_esi(self):
#     for record in self:
#         if record.esi_applicable == 'no':
#             record.esi_amount = 0.0
#
# @api.onchange('monthly_fixed_salary', 'provident_fund_applicable')
# def _onchange_provident_fund(self):
#     for record in self:
#         if record.provident_fund_applicable == 'yes':
#             if record.monthly_fixed_salary < 15000:
#                 record.provident_fund = record.monthly_fixed_salary * 0.12
#             elif record.monthly_fixed_salary >= 15000:
#                 record.provident_fund = 15000 * 0.12
#
# @api.onchange('monthly_fixed_salary', 'esi_applicable')
# def _onchange_esi_amount(self):
#     for record in self:
#         if record.esi_applicable == 'yes':
#             if record.monthly_fixed_salary <= 21000:
#                 record.esi_amount = record.monthly_fixed_salary * 0.0325
#             else:
#                 record.esi_amount = 0.0
#
# @api.onchange('monthly_fixed_salary', 'variable_pay_percentage', 'provident_fund')
# def _onchange_variable_pay_amount(self):
#     for record in self:
#         if record.variable_pay_percentage > 0:
#             monthly_salary = record.monthly_fixed_salary or 0.0
#             provident_fund_annual = (record.provident_fund or 0.0) * 12
#             variable_percentage = record.variable_pay_percentage / 100
#             record.variable_pay_amount = round((monthly_salary * 12 + provident_fund_annual) * variable_percentage,
#                                                0)

# def action_create_pre_form(self):
#     if not self.referred_by:
#         raise ValidationError("The 'Referee' field is required to create a Pre-Employment Check Form.")
#     if not self.email_from:
#         raise ValidationError("The Candidate Email fields is required to create a Pre-Employment Check Form.")
#
#     template = self.env.ref('hr_extended.reference_check_form_template')
#     for rec in self:
#         if rec.referred_by.email:
#             template.send_mail(rec.id, force_send=True)
#
#     vals = {
#         'applicant_id': self.id,
#         'candidate_name': self.partner_name,
#         'candidate_email': self.email_from,
#         'referee_id': self.referred_by.id,
#         'referee_phone': self.referred_by.partner_id.phone,
#         'referee_email': self.referred_by.partner_id.email,
#         'recruiter_id': self.user_id.id,
#     }
#     pre_form = self.env['preemp.check'].create(vals)
#     self.write({'is_pre_emp_form_clicked': True})
#     return pre_form
class HrApplicantDocument(models.Model):
    _name = "hr.applicant.document"
    _description = "Applicant Documents"

    applicant_id = fields.Many2one("hr.applicant", string="Applicant", required=True, ondelete="cascade")
    name = fields.Char(string="Document Name", required=True)
    file = fields.Binary(string="File", required=True)
    filename = fields.Char(string="Filename")


class HrApplicantRefuse(models.Model):
    _name = "hr.applicant.refuse"
    _description = "Offer Letter Refusal Log"
    _order = "create_date desc"

    applicant_id = fields.Many2one("hr.applicant", string="Applicant", required=True, ondelete="cascade")
    user_id = fields.Many2one("res.users", string="Refused By", default=lambda self: self.env.user, readonly=True)
    reason = fields.Text(string="Reason", required=True)

class HrApplicantRefuseWizard(models.TransientModel):
    _name = "hr.applicant.refuse.wizard"
    _description = "Refuse Offer Letter Wizard"

    applicant_id = fields.Many2one("hr.applicant", string="Applicant")
    reason = fields.Text(string="Reason", required=True)

    def action_confirm_refuse(self):
        applicant = self.applicant_id
        director_group = self.env.ref("hr_extended.group_hr_recruitment_director")  # Replace with your module/group XML ID

        # Check refusal count
        if applicant.refuse_count >= 3 and not self.env.user.has_group(director_group.xml_id):
            raise UserError(_("Offer Letter has already been refused 3 times. Only Director can override."))

        # Create refusal log
        self.env["hr.applicant.refuse"].create({
            "applicant_id": applicant.id,
            "reason": self.reason,
            "user_id": self.env.user.id,
        })

        # Update status
        applicant.write({"offer_letter_approved": "no",'offer_letter_sent_director':'no','refuse_count':+1})

