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
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        sheet = workbook.add_worksheet('Payroll Data')

        # Define styles
        title_format = workbook.add_format({'bold': True, 'align': 'left', 'font_size': 14})
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'border': 1})
        data_format = workbook.add_format({'align': 'left', 'border': 1,'num_format': '0.00'})
        char_format = workbook.add_format({'align': 'left', 'border': 1})
        merge_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'bold': True,
                'border': 1
            })

        # Title
        sheet.merge_range('A1:Z1','ENTITY - '+self.env.company.name, title_format)
        if self.report_based_on == 'batch':
            sheet.merge_range('A2:E2','Payroll Data for Batch'+' - '+self.batch_id.name , title_format)
        elif self.report_based_on =='date':
            sheet.merge_range('A2:E2','Payroll Data From'+' '+datetime.strftime(self.from_date,"%d-%m-%Y")+' '+'To' +' ' +datetime.strftime(self.to_date,"%d-%m-%Y") , title_format)
        elif self.report_based_on == 'department':
            sheet.merge_range('A2:Z2', f'Payroll Data for Department {self.department_id.name}', title_format)
        sheet.set_column('A:A',7)
        sheet.set_column('B:C', 20)
        sheet.set_column('D:E',10)
        sheet.set_column('F:F',15)
        sheet.set_column('G:H',20)
        sheet.set_column('I:I',15)
        sheet.set_column('J:J',25)
        sheet.set_column('K:AN',20)
        sheet.set_row(3,28)
        # Headers
        headers = [
            "Sl #", "Employee","Employment Status", "Empl. No.", "UAN", "Date of Joining",
            "Last Working Day", "Location", "Annual Fixed Compensation",
            "Days Paid \nThis Month"]
        if self.report_based_on == 'batch':
            payslips = self.env['hr.payslip'].search([
                ('payslip_run_id', '=', self.batch_id.id),
                ('state', '=', self.state)
            ])
        elif self.report_based_on == 'department':
            payslips = self.env['hr.payslip'].search([
                ('date_from','>=', self.from_date),
                ('date_to', '<=', self.to_date),
                ('employee_id.department_id', '=', self.department_id.id),
                ('state', '=', self.state)
            ])
        elif self.report_based_on =='date':
            payslips = self.env['hr.payslip'].search([
                ('date_from','>=', self.from_date),
                ('date_to', '<=', self.to_date),
                ('state', '=', self.state)
            ])
        row = 3
        col = 0
        for header in headers:
            sheet.merge_range(2,col,3,col,header, merge_format)
            col += 1
        work_col = col
        for leave_name in ['CL this month','EL this month','LoP this month']:
            sheet.write(row,work_col,leave_name,header_format)
            work_col +=1
        wrk_names =['CL this month','EL this month','LoP this month']
        comp_col = work_col
        components = payslips.struct_id.rule_ids.filtered(
            lambda l: any(rule.category_id.name in ['Basic', 'Allowance'] and rule.appears_on_payslip for rule in l)
        )
        for comp_name in components.mapped('name'):
            sheet.write(row, comp_col, comp_name, header_format)
            comp_col += 1
        sheet.write(row, comp_col,'Total', header_format)
        comp_col += 1
        ded_col = comp_col
        deduction = payslips.struct_id.rule_ids.filtered(
            lambda l: any(rule.category_id.name in ['Deduction'] and rule.appears_on_payslip for rule in l)
        )
        for comp_name in deduction.mapped('name'):
            sheet.write(row, ded_col, comp_name, header_format)
            ded_col += 1
        sheet.write(row, ded_col,'Total Deductions', header_format)
        ded_col += 1
        pay_col = ded_col
        payments = payslips.struct_id.rule_ids.filtered(
            lambda l: any(rule.category_id.name in ['Payments'] and rule.appears_on_payslip for rule in l)
        )
        for comp_name in payments.mapped('name'):
            sheet.write(row, pay_col, comp_name, header_format)
            pay_col += 1
        sheet.write(row, pay_col, 'Batch Payments', header_format)
        pay_col += 1
        sheet.write(row, pay_col,'Total Payments', header_format)
        # for comp_name in payslips.struct_id.rule_ids.mapped('name'):
        #     sheet.write(row,comp_col,comp_name,header_format)
        #     comp_col +=1
        sheet.merge_range(2,col,2,work_col-1, 'Worked and Leave Days', merge_format) if len(wrk_names) > 1 else sheet.write(2,col,'Worked and Leave Days',header_format)
        sheet.merge_range(2,work_col,2,comp_col-1, 'Components', merge_format)
        sheet.merge_range(2,comp_col,2,ded_col-1, 'Deductions', merge_format)
        sheet.merge_range(2, ded_col, 2, pay_col, 'Payments', merge_format)
        comp_names = components.mapped('name')
        ded_names = deduction.mapped('name')
        pay_names = payments.mapped('name')
        row = 4
        comp_fin_list = []
        wrk_fin_list = []
        ded_fin_list = []
        pay_fin_list = []
        for slip in payslips.filtered(
                lambda l: any(rule.category_id.name in ['Basic', 'Allowance'] for rule in l.struct_id.rule_ids)
        ).sorted(key=lambda l: min(
                (rule.sequence for rule in l.struct_id.rule_ids if rule.category_id.name in ['Basic', 'Allowance']),
                default=0)):
            comp_list = []
            wrk_list = []
            for line in slip.line_ids:
                comp_list.append({line.name:line.total})
            comp_fin_list.append(comp_list)
            for line in slip.worked_days_line_ids:
                lv_name = ''
                code = (line.work_entry_type_id.external_code or '').strip().upper()
                #if line.work_entry_type_id.code == 'CL':
                if code == 'CL':
                    lv_name = 'CL this month'
                elif code == 'LOP':
                    lv_name = 'LoP this month'
                elif code == 'EL':
                    lv_name = 'EL this month' 
                wrk_list.append({lv_name:line.number_of_days})
            wrk_fin_list.append(wrk_list)
        for slip in payslips.filtered(
            lambda l: any(rule.category_id.name in ['Deduction'] for rule in l.struct_id.rule_ids)).sorted(key=lambda l: min(
                (rule.sequence for rule in l.struct_id.rule_ids if rule.category_id.name in ['Deduction']),
                default=0)):
            ded_list = []
            total = 0
            for line in slip.line_ids:
                ded_list.append({line.name:line.total})
                total = total + line.total
            ded_fin_list.append(ded_list)
        for slip in payslips.filtered(
            lambda l: any(rule.category_id.name in ['Payments'] for rule in l.struct_id.rule_ids)).sorted(key=lambda l: min(
                (rule.sequence for rule in l.struct_id.rule_ids if rule.category_id.name in ['Payments']),
                default=0)):
            pay_list = []
            for line in slip.line_ids:
                pay_list.append({line.name:line.total})
            pay_fin_list.append(pay_list)
        start_row = row
        start_col = col
        value = 0
        for wrk in wrk_fin_list:
            for idx, work in enumerate(wrk_names):
                for item in wrk:
                    value = 0
                    if work in item:
                        value = item[work]
                        break
                sheet.write(start_row, start_col + idx, value, data_format)
            start_row += 1
        start_row = row
        start_col = work_col
        comp_list = []
        for comp in comp_fin_list:
            total = 0
            for idx, component in enumerate(comp_names):
                for item in comp:
                    value = 0
                    if component in item:
                        value = item[component]
                        total = total + int(item[component])

                        break
                sheet.write(start_row, start_col + idx, value, data_format)
                sheet.write(start_row, start_col+1 + idx, total, data_format)
            comp_list.append(total)
            start_row += 1
        start_row = row
        start_col = comp_col
        ded_list = []
        for comp in ded_fin_list:
            total = 0
            for idx, component in enumerate(ded_names):
                for item in comp:
                    value = 0
                    if component in item:
                        value = item[component]
                        total = total + int(item[component])

                        break
                sheet.write(start_row, start_col + idx, value, data_format)
                sheet.write(start_row, start_col + 1 + idx, total, data_format)
            ded_list.append(total)
            start_row += 1
        start_row = row
        start_col = ded_col
        index = 0
        for comp in pay_fin_list:
            total = 0

            for idx, component in enumerate(pay_names):
                for item in comp:
                    value = 0

                    if component in item:
                        value = item[component]

                        break
                diff_value = comp_list[index] - ded_list[index]
                total = total + int(item[component])+diff_value
                sheet.write(start_row, start_col + idx, value, data_format)
                sheet.write(start_row, start_col + 1 + idx, diff_value, data_format)
                sheet.write(start_row, start_col + 2 + idx, total, data_format)
                index =index+1
            start_row += 1
        for idx, slip in enumerate(payslips, start=1):
            col = 0
            resig_date = self.env['hr.resignation'].search([('employee_id','=',slip.employee_id.id),('state','=','hr_approved')])
            payroll_status_field = slip.employee_id._fields['employee_status_payroll']
            payroll_status_label = dict(payroll_status_field.selection).get(slip.employee_id.employee_status_payroll, '')
            sheet.write(row, col, idx, char_format)  # Sl #
            sheet.write(row, col + 1, slip.employee_id.name, char_format)  # Employee
            sheet.write(row, col + 2, payroll_status_label,char_format)  # Employment Status
            sheet.write(row, col + 3, slip.employee_id.new_emp_no if slip.employee_id.new_emp_no else '', char_format)  # Employee No.
            sheet.write(row, col + 4, slip.employee_id.uan_no if slip.employee_id.uan_no else '', char_format)  # UAN
            sheet.write(row, col + 5, datetime.strftime((slip.employee_id.joining_date),"%d-%m-%Y") if slip.employee_id.joining_date else '' , char_format)  # Date of Joining
            # sheet.write(row, col + 6, datetime.strftime((resig_date.hr_approved_reliving_date),"%d-%m-%Y") if resig_date else '', char_format)  # Date of Resignation Acceptance
            sheet.write(row, col + 6, datetime.strftime(resig_date.expected_revealing_date,"%d-%m-%Y") if resig_date.expected_revealing_date else '' , char_format)  # Last Working Day
            sheet.write(row, col + 7, slip.employee_id.work_location_id.name if slip.employee_id.work_location_id else '', char_format)  # Location
            sheet.write(row, col + 8, slip.contract_id.final_yearly_costs, data_format)  # Annual Compensation
            # sheet.write(row, col + 9, sum(slip.worked_days_line_ids.mapped('number_of_days')), data_format)  # Days Paid
            total_days = sum(slip.worked_days_line_ids.mapped('number_of_days'))
            lop_days = sum(
                line.number_of_days
                for line in slip.worked_days_line_ids
                if (line.work_entry_type_id.external_code or '').strip().upper() == 'LOP'
            )
            # days_paid = total_days - lop_days
            date = self.batch_id.date_start  # current date
            year = date.year
            month = date.month
            days_in_month = calendar.monthrange(year, month)[1]
            days_paid = days_in_month - lop_days
            sheet.write(row, col + 9, days_paid, data_format)
            # sheet.write(row, col + comp_col,'', data_format)
            row += 1

        workbook.close()
        buffer.seek(0)
        return buffer.read()

