from odoo import fields, models, api
import math
from odoo.exceptions import ValidationError, UserError
from num2words import num2words
from lxml import etree
from dateutil.relativedelta import relativedelta


class HrContract(models.Model):
    _inherit = 'hr.contract'

    basic_da_per_annum = fields.Float(string='Basic & DA', copy=False)
    basic_da_per_month = fields.Float(string='Basic & DA', copy=False)
    hra_per_annum = fields.Float(string='House Rent Allowance', copy=False)
    hra_per_month = fields.Float(string='House Rent Allowance', copy=False)
    special_allowance_per_annum = fields.Float(string='Other excluded Allowances', copy=False)
    special_allowance_per_month = fields.Float(string='Other excluded Allowances', copy=False)
    food_coupon_per_annum = fields.Float(string='Food Coupon', copy=False)
    food_coupon_per_month = fields.Float(string='Food Coupon', copy=False)
    lta_per_annum = fields.Float(string='Leave Travel Allowance', copy=False)
    lta_per_month = fields.Float(string='Leave Travel Allowance', copy=False)
    conveyances_per_annum = fields.Float(string='Conveyances', copy=False)
    conveyances_per_month = fields.Float(string='Conveyances', copy=False)
    sub_total_a_per_annum = fields.Float(string='Sub-total Part A', copy=False)
    sub_total_a_per_month = fields.Float(string='Sub-total Part A', copy=False)
    statutory_bonus_per_annum = fields.Float(string='Statutory Bonus', copy=False)
    statutory_bonus_per_month = fields.Float(string='Statutory Bonus', copy=False)
    pf_employer_per_annum = fields.Float(string="Provident Fund (Employer's Contribution)", copy=False)
    pf_employer_per_month = fields.Float(string="Provident Fund (Employer's Contribution)", copy=False)
    pf_employee_per_annum = fields.Float(string="Provident Fund (Employee's Contribution)", copy=False)
    pf_employee_per_month = fields.Float(string="Provident Fund (Employee's Contribution)", copy=False)
    nps_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="NPS Applicable", default='no',
        copy=False
    )
    nps_cal_perc = fields.Float(string='NPS Percentage')
    nps_applicable_from = fields.Date(string='NPS Applicable From')
    nps_employer_per_month = fields.Float(string="NPS(Employer's Contribution)", copy=False)
    nps_employer_per_annum = fields.Float(string="NPS(Employer's Contribution)", copy=False)
    esic_employer_per_annum = fields.Float(string='ESIC (Employer Contribution)', copy=False)
    esic_employer_per_month = fields.Float(string='ESIC (Employer Contribution)', copy=False)
    income_tax_month = fields.Float(string='Income Tax', copy=False)
    income_tax_annual = fields.Float(string='Income Tax', copy=False)
    sub_total_b_per_annum = fields.Float(string='Sub-total Part B', copy=False)
    sub_total_b_per_month = fields.Float(string='Sub-total Part B', copy=False)
    variable_pay_per_annum = fields.Float(string='Performance Linked Variable Pay', copy=False)
    variable_pay_per_month = fields.Float(string='Performance Linked Variable Pay', copy=False)
    sub_total_c_per_annum = fields.Float(string='Sub-total Part C', copy=False)
    sub_total_c_per_month = fields.Float(string='Sub-total Part C', copy=False)
    cess_applicable =  fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="CESS Applicable", default='yes',
        copy=False
    )
    cess_percentage = fields.Float(string="CESS Percentage",default='4')
    cess_month = fields.Float(string='CESS',copy=False,compute="compute_cess_cal")
    cess_annum = fields.Float(string='CESS', copy=False,compute="compute_cess_cal")
    total_salary_per_annum = fields.Float(string='Total Salary', copy=False)
    total_salary_per_month = fields.Float(string='Total Salary', copy=False)
    medical_insurances = fields.Float(string='Medical Insurance', copy=False)
    group_personal_acc_insurance = fields.Float(string='Group Personal Accident Insurance', copy=False)
    health_ben_plan = fields.Float(string='Health Benefit Plan', copy=False)
    sub_total_d = fields.Float(string='Sub-total Part D', copy=False)
    total_ctc_annum = fields.Float(string='Total Cost to Company',compute='compute_total_ctc_annum', copy=False)
    total_ctc_annum_exc = fields.Float(string='Total Cost to Company(excl PF & NPS)',copy=False)
    total_ctc_month = fields.Float(string='Total Cost to Company',compute='compute_total_ctc_annum', copy=False)
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
    net_taxable_income = fields.Float(string='Net Taxable Amount')
    standard_deduction = fields.Float(string='Standard Deduction')
    statutory_bonus_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="Statutory Bonus Applicable", default='no',
        copy=False
    )
    provident_fund_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="Provident Fund Applicable", default='no',
        copy=False
    )
    income_tax_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="Income Tax Applicable", default='no',
        copy=False
    )
    esi_applicable = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')], string="ESI Applicable", default='no', copy=False
    )
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
    location_id = fields.Many2one('location.master', string="Location", tracking=True, required=False)
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

    total_ctc_in_words = fields.Char(string="Total CTC In Words", compute='_compute_total_ctc_in_words')
    tax_slab_1 = fields.Float(string='- to 4,00,000')
    tax_slab_2 = fields.Float(string='4,00,001 to 8,00,000')
    tax_slab_3 = fields.Float(string='8,00,001 to 12,00,000')
    tax_slab_4 = fields.Float(string='12,00,001 to 16,00,000')
    tax_slab_5 = fields.Float(string='16,00,001 to 20,00,000')
    tax_slab_6 = fields.Float(string='20,00,001 to 24,00,000')
    tax_slab_7 = fields.Float(string='24,00,001 to -')
    is_pf_contribution = fields.Boolean(string='PF Contribution')
    employee_pf_contribution = fields.Float(string='Employee Contribution')
    is_parental_insurance = fields.Boolean(string='Parental Insurance')
    insurance_amount = fields.Float(string='Insurance Amount')
    applicable_from = fields.Selection(
        selection=[('01', 'January'), ('02', 'February'), ('03', 'March'),
                   ('04', 'April'), ('05', 'May'), ('06', 'June'),
                   ('07', 'July'), ('08', 'August'), ('09', 'September'),
                   ('10', 'October'), ('11', 'November'), ('12', 'December')],
        string="Month From")
    applicable_to = fields.Selection(
        selection=[('01', 'January'), ('02', 'February'), ('03', 'March'),
                   ('04', 'April'), ('05', 'May'), ('06', 'June'),
                   ('07', 'July'), ('08', 'August'), ('09', 'September'),
                   ('10', 'October'), ('11', 'November'), ('12', 'December')],
        string="Month To")
    applicable_from_date = fields.Date(string="Month From")
    applicable_to_date = fields.Date(string="Month To")
    recovery_of_advances = fields.Boolean(string="Recovery of Advances")
    recovery_of_advances_amount = fields.Float(string="Recovery of Advances Amount")
    recovery_from_date = fields.Date(string="From Date")
    recovery_to_date = fields.Date(string="To Date")

    def get_advance_recovery_amount_for_month(self, slip_date):
        """
        slip_date: date object of the payslip month (e.g. slip.date_from)
        """

        self.ensure_one()

        if not self.recovery_of_advances:
            return 0

        start = self.recovery_from_date
        end = self.recovery_to_date

        # If today is before start or after end, no deduction
        if not (start <= slip_date <= end):
            return 0

        total_amount = self.recovery_of_advances_amount

        # Calculate number of months
        diff = relativedelta(end, start)
        total_months = diff.years * 12 + diff.months + 1  # inclusive

        if total_months <= 0:
            return 0

        emi = total_amount / total_months
        return round(emi, 2)

    @api.model
    def get_view(self, view_id=None, view_type='form', **options):
        result = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form':
            arch = etree.fromstring(result['arch'])
            print(arch, 'arch\n')
            nodes = arch.xpath("//form")
            print(nodes, 'nodes\n')
            if nodes:
                print(self.env.user.name, self.env.user.has_group('hr_extended.group_view_own_contract'), 'has group\n')
                if self.env.user.has_group('hr_extended.group_view_own_contract'):
                    for node in nodes:
                        node.set("edit", "false")
            result['arch'] = etree.tostring(arch, encoding='unicode')
        return result

    @api.depends("cess_applicable","cess_percentage")
    def compute_cess_cal(self):
        for rec in self:
            if rec.cess_applicable == 'yes':
                if rec.cess_percentage >0:
                    # rec.cess_month = rec.basic_da_per_month *(rec.cess_percentage/100)
                    # rec.cess_annum = rec.basic_da_per_annum *(rec.cess_percentage/100)
                    a1 = round(rec.income_tax_month)
                    if rec.net_taxable_income > 5000000:
                        tax = round(rec.income_tax_month * 0.10)
                    else:
                        tax = 0
                    tax_inc_sur = a1 + tax
                    a2 = round(tax_inc_sur * (rec.cess_percentage/100))
                    rec.cess_month = a2
                    rec.cess_annum = a2*12
                else:
                    rec.cess_month = 0
                    rec.cess_annum = 0
            else:
                rec.cess_month = 0
                rec.cess_annum = 0


    # @api.onchange('nps_cal_perc', 'nps_applicable', 'nps_applicable_from')
    def _onchange_nps_calculation(self):
        for rec in self:
            rec.nps_employer_per_month = 0
            rec.nps_employer_per_annum = 0

            if rec.nps_applicable == 'yes' and rec.nps_cal_perc > 0:
                # Only apply NPS calculation if today's date is >= applicable date
                today = fields.Date.today()

                if rec.nps_applicable_from and rec.nps_applicable_from <= today:
                    rec.nps_employer_per_month = rec.basic_da_per_month * (rec.nps_cal_perc / 100)
                    rec.nps_employer_per_annum = rec.basic_da_per_annum * (rec.nps_cal_perc / 100)

            # Recompute totals
            rec.total_ctc_annum_exc = rec.total_ctc_annum - (
                    rec.pf_employer_per_annum + rec.nps_employer_per_annum
            )
            rec.net_taxable_income = (rec.total_ctc_annum_exc + rec.variable_pay_per_annum)- rec.standard_deduction

    @api.depends('final_yearly_costs')
    def compute_total_ctc_annum(self):
        for rec in self:
            if rec.final_yearly_costs:
                rec.total_ctc_annum = round(rec.final_yearly_costs)
                rec.total_ctc_month = round(rec.total_ctc_annum / 12)
                rec._onchange_calculate_income_tax()
                rec.compute_cess_cal()
            else:
                rec.total_ctc_annum = 0
                rec.total_ctc_month = 0

    @api.onchange('total_ctc_annum')
    def _compute_total_ctc_in_words(self):
        for record in self:
            if record.total_ctc_annum:
                total_ctc_integer = int(record.total_ctc_annum)
                record.total_ctc_in_words = num2words(total_ctc_integer, lang='en_IN').title()
            else:
                record.total_ctc_in_words = 'None'

    # @api.onchange('variable_pay_per_annum')
    def _onchange_variable_pay_per_annum(self):
        for rec in self:
            if rec.variable_pay_per_annum>0:
                rec.net_taxable_income = (rec.total_ctc_annum_exc + rec.variable_pay_per_annum)- rec.standard_deduction
            else:
                rec.net_taxable_income = rec.total_ctc_annum_exc - rec.standard_deduction

    # @api.onchange('location_id', 'monthly_fixed_salary', 'statutory_bonus_applicable', 'provident_fund_applicable',
    #               'esi_applicable', 'grade',
    #               'variable_pay_percentage', 'annual_store_performance_incentive', 'annual_performance_linked_pay',
    #               'monthly_performance_incentive',
    #               'medical_insurance', 'group_personal_accident_insurance', 'health_benefit_plan')
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
                    # if record.provident_fund_applicable == 'yes':
                    #     record.pf_employer_per_month = round(record.basic_da_per_month * 0.12)
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
                    record.basic_da_per_annum = max(round((record.monthly_fixed_salary * 12 * 0.4) / 12000) * 12000,salary_structure.annual_salary)
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
                    # if record.provident_fund_applicable == 'yes':
                    #     record.pf_employer_per_month = round(record.basic_da_per_month * 0.12)
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

                # if record.provident_fund_applicable == 'yes':
                #     record.pf_employer_per_month = round(record.basic_da_per_month * 0.12)
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
                # if record.provident_fund_applicable == 'yes':
                #     record.pf_employer_per_month = round(record.basic_da_per_month * 0.12)
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

                # if record.provident_fund_applicable == 'yes':
                #     record.pf_employer_per_month = round(record.basic_da_per_month * 0.12)
                if record.provident_fund_applicable == 'yes':
                    if record.monthly_fixed_salary < 15000:
                        record.pf_employer_per_month = round(record.monthly_fixed_salary * 0.12)
                    else:
                        record.pf_employer_per_month = round(15000 * 0.12)
                record.pf_employer_per_annum = record.pf_employer_per_month * 12

                record.indicative_take_home_salary = math.ceil(
                    record.sub_total_a_per_month + record.statutory_bonus_per_month - record.pf_employer_per_month - round(
                        record.esic_employer_per_month / 0.0325 * 0.0075) - profession_tax)

            else:
                pass

    # @api.onchange('monthly_fixed_salary','standard_deduction','total_ctc_annum','income_tax_applicable')
    def  _onchange_calculate_income_tax(self):
        for record in self:
            if record.monthly_fixed_salary:
                total_ctc = record.total_ctc_annum
                deduction = record.standard_deduction
                record.total_ctc_annum_exc = total_ctc - (
                        record.pf_employer_per_annum + record.nps_employer_per_annum)
                record.net_taxable_income = (record.total_ctc_annum_exc + record.variable_pay_per_annum) - deduction if deduction > 0 else record.total_ctc_annum_exc
            balance1 = 0
            balance2 = 0
            balance3 = 0
            balance4 = 0
            balance5 = 0
            balance6 = 0
            balance7 = 0
            appl_amount1 = 400000
            appl_amount2 = 0
            appl_amount3 = 0
            appl_amount4 = 0
            appl_amount5 = 0
            appl_amount6 = 0
            appl_amount7 = 0
            if record.income_tax_applicable == 'yes' and record.net_taxable_income > 1200000:
                if appl_amount1 < record.net_taxable_income:
                    if appl_amount1 > 0:
                        balance1 = record.net_taxable_income - appl_amount1
                        record.tax_slab_1 = 0
                        appl_amount2 = appl_amount1*2
                        record.tax_slab_2 = 0
                        record.tax_slab_3 = 0
                        record.tax_slab_4 = 0
                        record.tax_slab_5 = 0
                        record.tax_slab_6 = 0
                        record.tax_slab_7 = 0
                        if appl_amount2 <= record.net_taxable_income:
                            if appl_amount2 > 0:
                                balance2 = balance1 - appl_amount1
                                record.tax_slab_2 = appl_amount1 * 0.05
                                appl_amount3 = appl_amount1 * 3
                                record.tax_slab_3 = 0
                                record.tax_slab_4 = 0
                                record.tax_slab_5 = 0
                                record.tax_slab_6 = 0
                                record.tax_slab_7 = 0
                                if appl_amount3 <= record.net_taxable_income:
                                    if appl_amount3 > 0:
                                        balance3 = balance2 - appl_amount1
                                        record.tax_slab_3 = appl_amount1 * 0.10
                                        appl_amount4 = appl_amount1 * 4
                                        record.tax_slab_4 = 0
                                        record.tax_slab_5 = 0
                                        record.tax_slab_6 = 0
                                        record.tax_slab_7 = 0
                                        if appl_amount4 <= record.net_taxable_income:
                                            if appl_amount4 > 0:
                                                balance4 = balance3 - appl_amount1
                                                record.tax_slab_4 = appl_amount1 * 0.15
                                                appl_amount5 = appl_amount1 * 5
                                                record.tax_slab_5 = 0
                                                record.tax_slab_6 = 0
                                                record.tax_slab_7 = 0
                                                if appl_amount5 <= record.net_taxable_income:

                                                    if appl_amount5 > 0:
                                                        balance5 = balance4 - appl_amount1
                                                        record.tax_slab_5 = appl_amount1 * 0.20
                                                        appl_amount6 = appl_amount1 * 6
                                                        record.tax_slab_6 = 0
                                                        record.tax_slab_7 = 0
                                                        if appl_amount6 <= record.net_taxable_income:
                                                            if appl_amount6 > 0:
                                                                balance6 = balance5 - appl_amount1
                                                                record.tax_slab_6 = appl_amount1 * 0.25
                                                                appl_amount7 += appl_amount1 * 7
                                                                record.tax_slab_7 = 0
                                                                if appl_amount7 <= record.net_taxable_income:
                                                                    if appl_amount7 > 0:
                                                                        record.tax_slab_7 = balance6 * 0.30
                                                                else:
                                                                    record.tax_slab_7 = balance6 * 0.30
                                                                    break
                                                        else:
                                                            record.tax_slab_6 = balance5 * 0.25
                                                            break
                                                else:
                                                    record.tax_slab_5 = balance4 * 0.20
                                                    break
                                        else:
                                            record.tax_slab_4 = balance3 * 0.15
                                            break
                                else:
                                    record.tax_slab_3 = balance2 * 0.10
                                    break
                        else:
                            break


                    else:
                        record.income_tax_annual = 0
                        record.income_tax_month = 0
            else:

                record.income_tax_annual = 0
                record.income_tax_month = 0
                record.tax_slab_1 = 0
                record.tax_slab_2 = 0
                record.tax_slab_3 = 0
                record.tax_slab_4 = 0
                record.tax_slab_5 = 0
                record.tax_slab_6 = 0
                record.tax_slab_7 = 0
        record.income_tax_annual = record.tax_slab_1 + record.tax_slab_2 + record.tax_slab_3 + record.tax_slab_4 + record.tax_slab_5 + record.tax_slab_6 + record.tax_slab_7
        record.income_tax_month = round(record.income_tax_annual / 12)

    basic_da = fields.Float(string="Basic & DA (PA)", store=True, copy=False, )
    house_rent_allowance = fields.Float(string="House Rent Allowance (PA)", store=True, copy=False)
    special_allowance = fields.Float(string="Special Allowance (PA)", store=True, copy=False)

    # monthly_fixed_salary = fields.Float(string="Monthly Fixed Salary (excl PF & all incentive pay)", store=True,
    #                                     copy=False,)
    # stat_bonus_amount = fields.Float(string="Statutory Bonus Amount", store=True, copy=False)
    # provident_fund = fields.Float(string="Provident Fund", store=True, copy=False)
    # esi_amount = fields.Float(string="ESI Amount", store=True, copy=False)
    # variable_pay_percentage = fields.Float(string="Percentage of Variable Pay  (per annum)", store=True, copy=False)
    variable_pay_amount = fields.Float(string="Variable Pay Amounts", store=True, copy=False)
    # annual_store_performance_incentive = fields.Float(string="Annual Store Performance Incentive", store=True,
    #                                                   copy=False)
    # annual_performance_linked_pay = fields.Float(string="Annual Performance Linked Pay", store=True, copy=False)
    # monthly_performance_incentive = fields.Float(string="Monthly Performance Incentive", store=True, copy=False)
    # medical_insurance = fields.Float(string="Medical Insurance", store=True, copy=False)
    # group_personal_accident_insurance = fields.Float(string="Group Personal Accident Insurance", store=True, copy=False)
    # solis_health_benefit_beacon_plan = fields.Float(string="Solis Health Benefit Beacon Plan", store=True, copy=False)
    # indicative_take_home_salary = fields.Float(string="Indicative Take Home Salary Per Month", store=True, copy=False)
    #
    # statutory_bonus_applicable = fields.Selection(
    #     [('yes', 'Yes'), ('no', 'No')], string="Statutory Bonus Applicable (per month)", default='no',
    #     copy=False
    # )
    # provident_fund_applicable = fields.Selection(
    #     [('yes', 'Yes'), ('no', 'No')], string="Provident Fund Applicable (per month)", default='no',
    #     copy=False
    # )
    # esi_applicable = fields.Selection(
    #     [('yes', 'Yes'), ('no', 'No')], string="ESI Applicable (per month)", default='no', copy=False
    # )
    # fixed_pay = fields.Float(string="Fixed Pay", store=False, copy=False)
    # fixed_pay newly added but not know
    # def action_open_contract_list(self):
    #     self.ensure_one()
    #     action = self.env["ir.actions.actions"]._for_xml_id('hr_contract.action_hr_contract')
    #     action.update({'domain': [('employee_id', '=', self.employee_id.id)],
    #                   'views':  [[False, 'list'], [False, 'kanban'], [False, 'activity'], [False, 'form']],
    #                    'context': {'default_employee_id': self.employee_id.id}})
    #     return action
