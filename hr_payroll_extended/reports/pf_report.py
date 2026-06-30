from odoo import models, fields
import io
import base64
import xlsxwriter
from datetime import datetime,date
import calendar

class ExcelReportWizard(models.TransientModel):
    _name = 'pf.report.wizard'
    _description = 'PF Report Wizard'

    file_name = fields.Char(string="File Name", default="report.xlsx")
    file_data = fields.Binary(string="Excel File")
    month = fields.Selection([
        ('01', 'January'),
        ('02', 'February'),
        ('03', 'March'),
        ('04', 'April'),
        ('05', 'May'),
        ('06', 'June'),
        ('07', 'July'),
        ('08', 'August'),
        ('09', 'September'),
        ('10', 'October'),
        ('11', 'November'),
        ('12', 'December'),
    ], string="Month")

    year = fields.Selection(
        selection=lambda self: [(str(y), str(y)) for y in range(2000, datetime.today().year + 2)],
        string='Year',
        default=lambda self: str(datetime.today().year)
    )
    date_from = fields.Date(string='Date From', default=lambda self: date.today().replace(day=1))
    date_to = fields.Date(string='Date To', default=lambda self: date.today().replace(
            day=calendar.monthrange(date.today().year, date.today().month)[1]))
    company_id = fields.Many2one('res.company',string='Company',default=lambda self:self.env.company)

    def generate_excel_report(self):
        # Generate Excel file in memory
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        bold = workbook.add_format({'bold': True,'font_size':16})
        header_bold = workbook.add_format({'bold': True,'font_size': 12,'border':True})
        text_bold = workbook.add_format({'border':True})
        wrap_format = workbook.add_format({
            'text_wrap': True,
            'align': 'center',
            'valign': 'vcenter',
            'font_size': 12,
            'fg_color': '#D3D3D3',
            'bold':True,
            'border':True
        })
        amount_format = workbook.add_format({'num_format': '#,##0.00','border':True})
        amount_format1 = workbook.add_format({'num_format': '#,##0.00','fg_color': '#D3D3D3','border':True})
        worksheet = workbook.add_worksheet('Prov.Fund')
        worksheet.merge_range('A1:H1',self.company_id.name, bold)
        worksheet.merge_range('A3:H3','')
        # worksheet.merge_range(5,0,6,7,'')
        worksheet.write(3, 0, 'Financial Year', header_bold)
        worksheet.write(3, 3, 'Month Year', header_bold)
        worksheet.write(5,0, 'Person',wrap_format)
        worksheet.write(5,1, 'UAN',wrap_format)
        worksheet.write(5,2, 'Date of Severance',wrap_format)
        worksheet.write(5,3, 'Choice',wrap_format)
        worksheet.write(5,4, 'Gross Pay for the month',wrap_format)
        worksheet.merge_range('F6:G6', 'Basic',wrap_format)
        worksheet.write(6, 0, '',wrap_format)
        worksheet.write(6, 1, '',wrap_format)
        worksheet.write(6, 2, '',wrap_format)
        worksheet.write(6, 3, '',wrap_format)
        worksheet.write(6, 4, '',wrap_format)
        worksheet.write(6, 5, 'Actual',wrap_format)
        worksheet.write(6, 6, 'For PF',wrap_format)

        # month  = self.month
        # current_year = date.today().year
        # selected_month = int(self.month)
        # from_date = date(current_year, selected_month, 1)
        # if selected_month == 12:
        #     to_date = date(current_year + 1, 1, 1)
        # else:
        #     to_date = date(current_year, selected_month + 1, 1)

        payslips = self.env['hr.payslip'].search([
            ('date_from', '>=', self.date_from),
            ('date_to', '<', self.date_to),('company_id','=',self.company_id.id)
        ])
        total_salary_per_month = 0
        basic_da_per_month = 0
        row = 8
        for index, line in enumerate(payslips, start=1):
            worksheet.write(row, 0, line.employee_id.name or '',text_bold)
            worksheet.write(row, 1, line.employee_id.uan_no or '',text_bold)
            worksheet.write(row, 2, '',text_bold)
            worksheet.write(row, 3, '',text_bold)
            worksheet.write(row, 4, line.employee_id.contract_ids.total_salary_per_month or '0.0', amount_format)
            worksheet.write(row, 5, line.employee_id.contract_ids.basic_da_per_month or '0.0', amount_format)
            worksheet.write(row, 6, '',text_bold)
            total_salary_per_month = total_salary_per_month+line.employee_id.contract_ids.total_salary_per_month
            basic_da_per_month = basic_da_per_month+line.employee_id.contract_ids.basic_da_per_month

            row += 1
        row = row + 1
        worksheet.write(row, 0, '', wrap_format)
        worksheet.write(row, 1, 'Total',wrap_format)
        worksheet.write(row, 2, '', wrap_format)
        worksheet.write(row, 3, '', wrap_format)
        worksheet.write(row, 4, total_salary_per_month,amount_format1)
        worksheet.write(row, 5, basic_da_per_month,amount_format1)
        worksheet.write(row, 6, '',wrap_format)

        worksheet.set_column(5, 0, 15)
        worksheet.set_column(5, 1, 10)
        worksheet.set_column(5, 2, 10)
        worksheet.set_column(5, 4, 10)
        worksheet.set_row(5, 40, wrap_format)
        # worksheet.set_row(5, 2, 7)
        # worksheet.set_row(5, 3, 7)
        # worksheet.set_row(5, 4, 7)
        # worksheet.set_row(5, 5, 7)
        # worksheet.set_row(5, 6, 7)

        workbook.close()
        buffer.seek(0)

        # Save file to binary field
        file_data = base64.b64encode(buffer.read())
        buffer.close()
        attachment = self.env['ir.attachment'].create({
            'name': f'PF_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'store_fname': f'PF_Report.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'res_model': 'pf.report.wizard',
            'res_id': self.id,
        })
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }


