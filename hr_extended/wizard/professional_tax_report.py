from odoo import models, fields, api
from datetime import datetime
import base64
from io import BytesIO
import xlsxwriter

from odoo.exceptions import UserError, ValidationError

class TaxReportWizard(models.TransientModel):
    _name = 'tax.report.wizard'
    _description = 'Tax Report Wizard'

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

    def action_send_tax_report_mail(self):
        template = self.env.ref('hr_extended.tax_report_share_email_template')
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
        notify_type = self.env.ref("mail.mail_activity_data_todo", False)
        if not notify_type:
            return

        for req in self:
            summary = 'Email Notification'
            for partner in req.partner_ids:
                # Get all users linked to this partner
                for user in partner:
                    # print('')
                    mail = self.env["mail.activity"].sudo().create({
                        "res_id": req.id,
                        "res_model_id": self.env["ir.model"]._get('res.partner').id,
                        "activity_type_id": notify_type.id,
                        "summary": summary,
                        "user_id": user.id,  # This must be res.users.id
                    })

    def action_generate_report(self):
        workbook = self._prepare_excel_workbook()
        self.report_file = base64.b64encode(workbook)
        self.file_name = f"Tax_Report.xlsx"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'tax.report.wizard',
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
        title_format1 = workbook.add_format({'bold': True, 'align': 'left', 'font_size': 14,'color':'#FF0000'})
        char_format = workbook.add_format({'align': 'left', 'border': 1})
        merge_format = workbook.add_format({
                'align': 'center',
                'valign': 'vcenter',
                'bold': True,
                'border': 1
            })

        # Title
        sheet.merge_range('A1:E1',self.env.company.name, title_format)
        if self.report_based_on == 'batch':
            sheet.merge_range('A2:E2','Employee Payroll'+' '+self.batch_id.name , title_format)
        else:
            sheet.merge_range('A2:E2','Employee Payroll', title_format)
        sheet.merge_range('A3:B3', f'Financial year:{datetime.now().strftime("%Y")}', title_format)
        sheet.merge_range('D3:E3', f'Month, Year:{datetime.now().strftime("%B %Y")}', title_format)
        sheet.merge_range('A4:B4', 'PROFESSION TAX - KARNATAKA', title_format1)
        sheet.set_column('A:A',20)
        sheet.set_column('B:C', 20)
        sheet.set_column('D:E',20)
        sheet.set_column('F:F',20)
        sheet.set_column('G:H',20)
        sheet.set_column('I:I',15)
        sheet.set_column('J:J',25)
        sheet.set_column('K:AN',20)
        sheet.set_row(3,28)
        # Headers
        headers = [
            "More than", " But less than ", "Tax", " No. of employees", " Tax payable"]
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
        row = 7
        col = 0
        for header in headers:
            sheet.merge_range(5,col,6,col,header, merge_format)
            col += 1
        row += 1
        emp_count = 0
        print(payslips,'qqqqqqqqqqqqqqqqqq')
        for rec in payslips.line_ids:
            if rec.name == 'Basic Salary':
                if rec.total > 25000:
                    emp_count += 1
        rec_row = row
        rec_col = 0
        sheet.write(rec_row, rec_col,25000, char_format)
        sheet.write(rec_row, rec_col + 1, '-' , char_format)
        sheet.write(rec_row, rec_col + 2, 200, char_format)
        sheet.write(rec_row, rec_col + 3, emp_count, char_format)
        sheet.write(rec_row, rec_col + 4, emp_count*200, char_format)

        workbook.close()
        buffer.seek(0)
        return buffer.read()

