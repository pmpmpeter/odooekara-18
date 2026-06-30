import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone


class CMGAndGPADetails(models.AbstractModel):
    _name = 'report.hr_extended.report_cmg_and_gpa_details'
    _inherit = "report.report_xlsx.abstract"

    def generate_xlsx_report(self, workbook, data, employee):
        # main_product = data
        # company_name = main_product['company_name']
        # company_id = main_product['company_id']
        # date_from = main_product['date_from']
        # date_to = main_product['date_to']

        worksheet = workbook.add_worksheet('GMC GPA DETAILS')

        worksheet.protect()
        merge_format1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'fg_color': '#f2f2f2',
            'valign': 'vcenter', })

        worksheet.set_column('A:A', 10)
        worksheet.set_default_row(25)

        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 35)
        worksheet.set_column('E:E', 25)
        worksheet.set_column('F:F', 35)
        worksheet.set_column('G:G', 15)
        worksheet.set_column('H:H', 15)
        worksheet.set_column('I:I', 15)
        worksheet.set_column('J:J', 15)
        worksheet.set_column('K:K', 25)
        worksheet.set_column('L:L', 35)
        worksheet.merge_range('B2:L2', 'GMC Details', merge_format1)

        # worksheet.merge_range('A2:I2', datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d-%m-%Y') +' ' 'To' ' ' + datetime.datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d-%m-%Y'), format_date)
        worksheet.write(2, 1, "Sl #", merge_format1)
        worksheet.write(2, 2, "Emp. ID", merge_format1)
        worksheet.write(2, 3, "Name of the Person", merge_format1)
        worksheet.write(2, 4, "Relation to employee", merge_format1)
        worksheet.write(2, 5, "Designation", merge_format1)
        worksheet.write(2, 6, "Date of Birth", merge_format1)
        worksheet.write(2, 7, "Gender-M/F", merge_format1)
        worksheet.write(2, 8, "Sum Insured", merge_format1)
        worksheet.write(2, 9, "Date of Joining", merge_format1)
        worksheet.write(2, 10, "Location", merge_format1)
        worksheet.write(2, 11, "Entity", merge_format1)

        records = self.env['joining.documents'].search([('id', 'in', employee.ids)])

        row = 3
        for idx, record in enumerate(records, start=1):
            worksheet.write(row, 1, idx, merge_format1)
            worksheet.write(row, 2, record.emp_code or '', merge_format1)
            worksheet.write(row, 3, record.dependent_name or '', merge_format1)
            worksheet.write(row, 4, record.relationship or '', merge_format1)
            worksheet.write(row, 5, record.designation or '', merge_format1)
            worksheet.write(row, 6, record.dob.strftime('%d-%m-%Y') if record.dob else '',
                            merge_format1)
            worksheet.write(row, 7, dict(record._fields['gender'].selection).get(record.gender, ''), merge_format1)
            worksheet.write(row, 8, record.sum_insured_gmc or 0, merge_format1)
            worksheet.write(row, 9, record.doj.strftime('%d-%m-%Y') if record.doj else '',
                            merge_format1)
            worksheet.write(row, 10, record.location or '', merge_format1)
            worksheet.write(row, 11, record.tax_entity.name or '', merge_format1)

            row += 1

        worksheet2 = workbook.add_worksheet('GPA DETAILS (OPTIONAL)')

        worksheet2.protect()
        merge_format2 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'fg_color': '#d8d8d8',
            'valign': 'vcenter', })
        merge_format3 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,

            'valign': 'vcenter', })

        worksheet2.set_column('A:A', 10)
        worksheet2.set_default_row(25)

        worksheet2.set_column('B:B', 15)
        worksheet2.set_column('C:C', 15)
        worksheet2.set_column('D:D', 35)
        worksheet2.set_column('E:E', 35)
        worksheet2.set_column('F:F', 35)
        worksheet2.set_column('G:G', 25)
        worksheet2.set_column('H:H', 20)
        worksheet2.set_column('I:I', 20)
        worksheet2.set_column('J:J', 35)
        worksheet2.set_column('K:K', 25)
        worksheet2.merge_range('B2:K2', 'GMC addition - for parental coverage (Optional)', merge_format3)

        # worksheet2.merge_range('A2:I2', datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d-%m-%Y') +' ' 'To' ' ' + datetime.datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d-%m-%Y'), format_date)
        worksheet2.write(2, 1, "Sl #", merge_format2)
        worksheet2.write(2, 2, "Emp. ID", merge_format2)
        worksheet2.write(2, 3, "Employee Name", merge_format2)
        worksheet2.write(2, 4, "Insured Name", merge_format2)
        worksheet2.write(2, 5, "Relation", merge_format2)
        worksheet2.write(2, 6, "DOB", merge_format2)
        worksheet2.write(2, 7, "Age", merge_format2)
        worksheet2.write(2, 8, "Gender", merge_format2)
        worksheet2.write(2, 9, "Entity Name", merge_format2)
        worksheet2.write(2, 10, "Individual Sum Insured per parent", merge_format2)

        records = self.env['joining.documents'].search([('id', 'in', employee.ids)])

        row = 3
        for idx, record in enumerate(records, start=1):
            worksheet2.write(row, 1, idx, merge_format2)
            worksheet2.write(row, 2, record.emp_code or '', merge_format2)
            worksheet2.write(row, 3, record.employee_id.name or '', merge_format2)
            worksheet2.write(row, 4, record.dependent_name or '', merge_format2)
            worksheet2.write(row, 5, record.relationship or '', merge_format2)
            worksheet2.write(row, 6, record.dob.strftime('%d-%m-%Y') if record.dob else '',
                            merge_format2)
            worksheet2.write(row, 7, record.age or '', merge_format2)
            worksheet2.write(row, 8, dict(record._fields['gender'].selection).get(record.gender, ''), merge_format2)
            worksheet2.write(row, 9, record.tax_entity.name or '', merge_format2)
            worksheet2.write(row, 10, record.sum_insured_gmc or 0, merge_format2)
            print(record.sum_insured_gmc)
            row += 1
