from odoo import models, fields, api
from datetime import datetime,date
import calendar
import base64
from io import BytesIO
import xlsxwriter

from odoo.exceptions import UserError, ValidationError

class PayrollReportWizard(models.TransientModel):
    _name = 'payroll.report.wizard'
    _description = 'Payroll Report Wizard'

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    salary_structure_id = fields.Many2one('hr.payroll.structure', string="Salary Structure")
    state = fields.Selection([
        ('draft', 'Draft'),
        ('verify', 'Verify'),
        ('paid', 'Paid'),
        ('done', 'Done')
    ], string="PaySheet Status", required=True, default='verify')
    report_based_on = fields.Selection([
        ('batch', 'Batch'),
        ('department', 'Department'),
        ('date', 'Only From and To Date'),
    ], string="Report Based on", required=True, default='batch')
    batch_id = fields.Many2one('hr.payslip.run',string='Batch')
    department_id = fields.Many2one('hr.department',string='Department')
    report_file = fields.Binary(string="Report File", readonly=True)
    file_name = fields.Char(string="File Name", readonly=True)
    partner_ids = fields.Many2many('res.partner', string="Email To")
    employee_id = fields.Many2many('hr.employee',string='Email To')
    user_id = fields.Many2many(
        'res.users',
        'payroll_report_wizard_res_users_rel',  # relation table name
        'wizard_id',  # column referring to this model
        'user_id',  # column referring to res.users
        string="In-App Notifications"
    )

    def action_send_payroll_report_mail(self):
        template = self.env.ref('hr_extended.payroll_report_share_email_template')
        for record in self:
            if not record.partner_ids:
                raise ValidationError("Please add at least one partner to send the email.")

            missing = [p.name for p in record.partner_ids if not p.email]
            if missing:
                raise ValidationError(f"Missing email for: {', '.join(missing)}")

            if not record.report_file:
                raise ValidationError("Please upload the report file before sending the email.")

            attachment = self.env['ir.attachment'].create({
                'name': record.file_name or 'report.pdf',
                'type': 'binary',
                'datas': record.report_file,
                'res_model': record._name,
                'res_id': record.id,
                'mimetype': 'application/pdf',
            })

            template.send_mail(record.id, force_send=True, email_values={
                'attachment_ids': [attachment.id],
            })
            self.send_activity_notification()

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Success',
                'message': 'Email sent to selected recipients.',
                'type': 'success',
                'sticky': True,
            }
        }

    def send_activity_notification(self):
        # notify_type = self.env.ref("mail.mail_activity_data_todo", False)
        # if not notify_type:
        #     return
        #
        # for req in self:
        #     summary = 'Email Notification'
        #     # res_model: req._name
        #     for partner in req.employee_id:
        #         # Get all users linked to this partner
        #         for user in partner:
        #             # print('')
        #             print(user, '2222222')
        #             self.env["mail.activity"].sudo().create({
        #                 "res_id": req.id,
        #                 "res_model": self.env['ir.model']._get_id(req._name),
        #                 "activity_type_id": notify_type.id,
        #                 "summary": summary,
        #                 "user_id": user.id,  # This must be res.users.id
        #             })
        users = self.user_id
        for user_id in users:
            if not user_id:
                raise ValidationError("In-app notifications can be sent to employees who are linked to users")
            self.batch_id.activity_schedule(
                activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                summary="Batch Payroll Reminder: Payroll reminder",
                note=f"Kindly Verify the Batch Payroll:{self.batch_id.name} .",
                user_id=user_id.id,
                date_deadline=fields.Date.today()
            )


    def action_generate_report(self):
        workbook = self._prepare_excel_workbook()
        self.report_file = base64.b64encode(workbook)
        self.file_name = f"Payroll_Report.xlsx"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'payroll.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _prepare_excel_workbook(self):
        """
        Prepare Payroll Batch JV Excel report.

        The report is generated employee/payslip-wise so that:
            - Worked days
            - Components
            - Deductions
            - Payments

        are always taken from the same payslip.

        Salary rule codes are used where available for reliable
        identification of payroll lines.
        """

        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        sheet = workbook.add_worksheet('Payroll Data')

        # -------------------------------------------------------------------------
        # Formats
        # -------------------------------------------------------------------------

        title_format = workbook.add_format({'bold': True,'align': 'left','font_size': 14,})

        header_format = workbook.add_format({'bold': True,'align': 'center','valign': 'vcenter','border': 1,'text_wrap': True,})

        data_format = workbook.add_format({'align': 'right','border': 1,'num_format': '0.00',})

        char_format = workbook.add_format({'align': 'left','border': 1,})

        merge_format = workbook.add_format({'align': 'center','valign': 'vcenter','bold': True,'border': 1,})

        date_format = workbook.add_format({'align': 'left','border': 1,'num_format': 'dd-mm-yyyy',})

        # -------------------------------------------------------------------------
        # Report Title
        # -------------------------------------------------------------------------

        sheet.merge_range('A1:Z1','ENTITY - %s' % self.env.company.name,title_format,)

        if self.report_based_on == 'batch':
            sheet.merge_range('A2:E2','Payroll Data for Batch - %s' % self.batch_id.name,title_format,)

        elif self.report_based_on == 'date':
            sheet.merge_range('A2:E2','Payroll Data From %s To %s' % (self.from_date.strftime('%d-%m-%Y'),self.to_date.strftime('%d-%m-%Y'),),title_format,)

        elif self.report_based_on == 'department':
            sheet.merge_range('A2:Z2','Payroll Data for Department %s' % self.department_id.name,title_format,)

        # -------------------------------------------------------------------------
        # Column Widths
        # -------------------------------------------------------------------------

        sheet.set_column('A:A', 7)
        sheet.set_column('B:C', 20)
        sheet.set_column('D:E', 15)
        sheet.set_column('F:F', 15)
        sheet.set_column('G:H', 20)
        sheet.set_column('I:I', 20)
        sheet.set_column('J:J', 25)
        sheet.set_column('K:AN', 20)

        sheet.set_row(2, 28)
        sheet.set_row(3, 40)

        # -------------------------------------------------------------------------
        # Get Payslips
        # -------------------------------------------------------------------------

        payslip_domain = [
            ('state', '=', self.state),
        ]

        if self.report_based_on == 'batch':
            payslip_domain.append(('payslip_run_id', '=', self.batch_id.id))

        elif self.report_based_on == 'department':
            payslip_domain += [
                ('date_from', '>=', self.from_date),
                ('date_to', '<=', self.to_date),
                ('employee_id.department_id', '=', self.department_id.id),
            ]

        elif self.report_based_on == 'date':
            payslip_domain += [
                ('date_from', '>=', self.from_date),
                ('date_to', '<=', self.to_date),
            ]

        payslips = self.env['hr.payslip'].search(
            payslip_domain,
            order='employee_id, date_from, id',
        )

        # -------------------------------------------------------------------------
        # Basic Headers
        # -------------------------------------------------------------------------

        headers = [
            'Sl #',
            'Employee',
            'Employment Status',
            'Empl. No.',
            'UAN',
            'Date of Joining',
            'Last Working Day',
            'Location',
            'Annual Fixed Compensation',
            'Days Paid\nThis Month',
        ]

        row = 2
        col = 0

        for header in headers:
            sheet.merge_range(row,col,row + 1,col,header,merge_format,)
            col += 1

        # -------------------------------------------------------------------------
        # Worked and Leave Days
        # -------------------------------------------------------------------------

        worked_day_names = [
            'CL this month',
            'EL this month',
            'LoP this month',
        ]

        work_col = col

        for work_name in worked_day_names:
            sheet.write(row + 1,work_col,work_name,header_format,)
            work_col += 1

        sheet.merge_range(row,col,row,work_col - 1,'Worked and Leave Days',merge_format,)

        # -------------------------------------------------------------------------
        # Salary Rules
        # -------------------------------------------------------------------------

        # Get all salary rules used by the selected payslips.
        #
        # We use the actual payslip line salary rules instead of relying only
        # on the structure. This makes the report work even if multiple salary
        # structures are present in the selected payslips.
        salary_rules = payslips.mapped('line_ids.salary_rule_id').filtered(
            lambda rule: rule and rule.appears_on_payslip
        )

        # -------------------------------------------------------------------------
        # Components
        # -------------------------------------------------------------------------

        component_rules = salary_rules.filtered(
            lambda rule: rule.category_id.name in ('Basic', 'Allowance')
        ).sorted(
            key=lambda rule: (rule.sequence, rule.id)
        )

        component_names = component_rules.mapped('name')

        comp_col = work_col

        for component_name in component_names:
            sheet.write(row + 1,comp_col,component_name,header_format,)
            comp_col += 1

        sheet.write(row + 1,comp_col,'Total',header_format,)

        component_total_col = comp_col
        comp_col += 1

        sheet.merge_range(row,work_col,row,comp_col - 1,'Components',merge_format,)

        # -------------------------------------------------------------------------
        # Deductions
        # -------------------------------------------------------------------------

        deduction_rules = salary_rules.filtered(
            lambda rule: rule.category_id.name == 'Deduction'
        ).sorted(
            key=lambda rule: (rule.sequence, rule.id)
        )

        deduction_names = deduction_rules.mapped('name')

        ded_col = comp_col

        for deduction_name in deduction_names:
            sheet.write(row + 1,ded_col,deduction_name,header_format,)
            ded_col += 1

        sheet.write(row + 1,ded_col,'Total Deductions',header_format,)

        deduction_total_col = ded_col
        ded_col += 1

        sheet.merge_range(row,comp_col,row,ded_col - 1,'Deductions',merge_format,)

        # -------------------------------------------------------------------------
        # Payments
        # -------------------------------------------------------------------------

        payment_rules = salary_rules.filtered(lambda rule: rule.category_id.name == 'Payments').sorted(key=lambda rule: (rule.sequence, rule.id))

        payment_names = payment_rules.mapped('name')

        pay_col = ded_col

        for payment_name in payment_names:
            sheet.write(row + 1,pay_col,payment_name,header_format,)
            pay_col += 1

        # Batch Payments
        batch_payment_col = pay_col

        sheet.write(row + 1,batch_payment_col,'Batch Payments',header_format,)

        pay_col += 1

        # Total Payments
        total_payment_col = pay_col

        sheet.write(row + 1,total_payment_col,'Total Payments',header_format,)

        pay_col += 1

        sheet.merge_range(row,ded_col,row,pay_col - 1,'Payments',merge_format,)

        # -------------------------------------------------------------------------
        # Helper Methods
        # -------------------------------------------------------------------------

        def get_line_values_by_code(slip):
            """
            Return payslip values indexed by salary rule code.

            Example:

                {
                    'BASIC': 84981.00,
                    'HRA': 42491.00,
                    'FOOD': 4400.00,
                    'FOOD-R': 4400.00,
                    'FC': 4400.00,
                }

            This is preferred over matching only by line name.
            """

            values = {}

            for line in slip.line_ids:
                rule = line.salary_rule_id

                if not rule:
                    continue

                code = (rule.code or '').strip()

                if not code:
                    continue

                values[code] = values.get(code, 0.0) + line.total

            return values

        def get_line_values_by_name(slip):
            """
            Fallback mapping by salary rule/line name.

            This is useful if a salary rule does not have a code.
            """

            values = {}

            for line in slip.line_ids:
                rule = line.salary_rule_id

                name = rule.name if rule else line.name

                if not name:
                    continue

                values[name] = values.get(name, 0.0) + line.total

            return values

        def get_rule_value(slip, rule):
            """
            Get a specific salary rule value from a payslip.

            Rule code is preferred.
            Rule name is used as fallback.
            """

            code_values = get_line_values_by_code(slip)
            name_values = get_line_values_by_name(slip)

            rule_code = (rule.code or '').strip()

            if rule_code:
                return code_values.get(rule_code, 0.0)

            return name_values.get(rule.name, 0.0)

        # -------------------------------------------------------------------------
        # Data Rows
        # -------------------------------------------------------------------------

        data_row = 4

        for sequence, slip in enumerate(payslips, start=1):

            employee = slip.employee_id

            # ---------------------------------------------------------------------
            # Salary Rule Values
            # ---------------------------------------------------------------------

            component_values = {}
            component_total = 0.0

            for rule in component_rules:
                value = get_rule_value(slip, rule)

                component_values[rule.id] = value
                component_total += value

            deduction_values = {}
            deduction_total = 0.0

            for rule in deduction_rules:
                value = get_rule_value(slip, rule)

                deduction_values[rule.id] = value
                deduction_total += value

            payment_values = {}
            payment_total = 0.0

            for rule in payment_rules:
                value = get_rule_value(slip, rule)

                payment_values[rule.id] = value
                payment_total += value

            # ---------------------------------------------------------------------
            # Net / Batch Payment
            # ---------------------------------------------------------------------

            batch_payment = component_total - deduction_total

            total_payments = batch_payment + payment_total

            # ---------------------------------------------------------------------
            # Worked Days
            # ---------------------------------------------------------------------

            worked_day_values = {
                'CL this month': 0.0,
                'EL this month': 0.0,
                'LoP this month': 0.0,
            }

            for worked_day in slip.worked_days_line_ids:
                external_code = (
                    worked_day.work_entry_type_id.external_code or ''
                ).strip().upper()

                if external_code == 'CL':
                    worked_day_values['CL this month'] += (
                        worked_day.number_of_days
                    )

                elif external_code == 'EL':
                    worked_day_values['EL this month'] += (
                        worked_day.number_of_days
                    )

                elif external_code == 'LOP':
                    worked_day_values['LoP this month'] += (
                        worked_day.number_of_days
                    )

            # ---------------------------------------------------------------------
            # Days Paid
            # ---------------------------------------------------------------------

            lop_days = worked_day_values['LoP this month']

            if slip.date_from:
                days_in_month = calendar.monthrange(
                    slip.date_from.year,
                    slip.date_from.month,
                )[1]
            else:
                days_in_month = 0

            days_paid = days_in_month - lop_days

            # ---------------------------------------------------------------------
            # Last Working Day
            # ---------------------------------------------------------------------

            last_working_day = ''

            resignation = self.env['hr.resignation'].search(
                [
                    ('employee_id', '=', employee.id),
                    ('state', '=', 'hr_approved'),
                ],
                order='id desc',
                limit=1,
            )

            if resignation and resignation.expected_revealing_date:
                last_working_day = resignation.expected_revealing_date.strftime(
                    '%d-%m-%Y'
                )

            # ---------------------------------------------------------------------
            # Employment Status
            # ---------------------------------------------------------------------

            payroll_status_label = ''

            if 'employee_status_payroll' in employee._fields:
                payroll_status_field = employee._fields[
                    'employee_status_payroll'
                ]

                payroll_status_label = dict(
                    payroll_status_field.selection
                ).get(
                    employee.employee_status_payroll,
                    '',
                )

            # ---------------------------------------------------------------------
            # Employee Information
            # ---------------------------------------------------------------------

            current_col = 0

            sheet.write(data_row,current_col,sequence,char_format,)
            current_col += 1

            sheet.write(data_row,current_col,employee.name or '',char_format,)
            current_col += 1

            sheet.write(data_row,current_col,payroll_status_label,char_format,)
            current_col += 1

            sheet.write(data_row,current_col,employee.new_emp_no or '',char_format,)
            current_col += 1

            sheet.write(data_row,current_col,employee.uan_no or '',char_format,)
            current_col += 1

            sheet.write(
                data_row,
                current_col,
                employee.joining_date.strftime('%d-%m-%Y')
                if employee.joining_date
                else '',
                char_format,
            )
            current_col += 1

            sheet.write(data_row,current_col,last_working_day,char_format,)
            current_col += 1

            sheet.write(
                data_row,
                current_col,
                employee.work_location_id.name
                if employee.work_location_id
                else '',
                char_format,
            )
            current_col += 1

            annual_compensation = (
                slip.contract_id.final_yearly_costs
                if slip.contract_id
                else 0.0
            )

            sheet.write(data_row,current_col,annual_compensation,data_format,)
            current_col += 1

            sheet.write(data_row,current_col,days_paid,data_format,)
            current_col += 1

            # ---------------------------------------------------------------------
            # Worked and Leave Days
            # ---------------------------------------------------------------------

            for work_name in worked_day_names:
                sheet.write(
                    data_row,
                    current_col,
                    worked_day_values[work_name],
                    data_format,
                )
                current_col += 1

            # ---------------------------------------------------------------------
            # Components
            # ---------------------------------------------------------------------

            for rule in component_rules:
                sheet.write(data_row,current_col,component_values[rule.id],data_format,)
                current_col += 1

            sheet.write(data_row,current_col,component_total,data_format,)
            current_col += 1

            # ---------------------------------------------------------------------
            # Deductions
            # ---------------------------------------------------------------------

            for rule in deduction_rules:
                sheet.write(data_row,current_col,deduction_values[rule.id],data_format,)
                current_col += 1

            sheet.write(data_row,current_col,deduction_total,data_format,)
            current_col += 1

            # ---------------------------------------------------------------------
            # Payments
            # ---------------------------------------------------------------------

            for rule in payment_rules:
                sheet.write(data_row,current_col,payment_values[rule.id],data_format,)
                current_col += 1

            # Batch Payments
            sheet.write(data_row,current_col,batch_payment,data_format,)
            current_col += 1

            # Total Payments
            sheet.write(data_row,current_col,total_payments,data_format,)

            data_row += 1

        # -------------------------------------------------------------------------
        # Freeze Panes
        # -------------------------------------------------------------------------

        sheet.freeze_panes(4, 0)

        # -------------------------------------------------------------------------
        # Workbook
        # -------------------------------------------------------------------------

        workbook.close()
        buffer.seek(0)

        return buffer.read()

