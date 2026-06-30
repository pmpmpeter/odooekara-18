import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone

class AnnualPerformanceReview(models.AbstractModel):
    _name = 'report.hr_appraisal_extended.report_performance_review'
    _inherit = "report.report_xlsx.abstract"


    def generate_xlsx_report(self, workbook,data,employee):

        # main_product = data
        # company_name = main_product['company_name']
        # company_id = main_product['company_id']
        # date_from = main_product['date_from']
        # date_to = main_product['date_to']

        worksheet = workbook.add_worksheet('performance_review')

        worksheet.protect()
        merge_format1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'bg_color': '#e7eae6',
            'valign': 'vcenter',
            # 'text_wrap': True,
        })

        merge_format2 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'bg_color': '#FFFF00',
            'valign': 'vcenter',
            # 'text_wrap': True,
        })





        worksheet.set_column('A:A', 30)
        worksheet.set_column('B:B', 30)
        worksheet.set_column('C:C', 30)
        worksheet.set_column('D:D', 30)
        worksheet.set_column('E:E', 30)
        worksheet.set_column('F:F', 30)
        worksheet.set_column('G:G', 30)
        worksheet.set_column('H:H', 30)
        worksheet.set_column('I:I', 30)
        worksheet.set_column('J:J', 30)
        worksheet.set_column('K:K', 30)
        worksheet.set_column('L:L', 30)
        worksheet.set_column('M:M', 30)
        worksheet.set_column('N:N', 30)
        worksheet.set_column('O:O', 30)
        worksheet.set_column('P:P', 30)
        worksheet.set_column('Q:Q', 30)
        worksheet.set_column('R:R', 30)
        worksheet.set_column('S:S', 30)
        worksheet.set_column('T:T', 30)
        worksheet.set_column('U:U', 30)
        worksheet.set_column('V:V', 30)
        worksheet.set_column('W:W', 30)
        worksheet.set_column('X:X', 30)
        worksheet.set_column('Y:Y', 30)
        worksheet.set_column('Z:Z', 30)
        worksheet.set_column('AA:AA', 30)
        worksheet.write('V7', "", merge_format1)
        # worksheet.merge_range('B2:L2', 'GMC Details', merge_format1)

        # worksheet.merge_range('A2:I2', datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d-%m-%Y') +' ' 'To' ' ' + datetime.datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d-%m-%Y'), format_date)
        worksheet.write(1, 0, "Employee Self Rating", merge_format2)
        worksheet.write(4, 0, "Mgr /BU Head /Director Page", merge_format2)
        worksheet.write(6, 0, "Completed List", merge_format2)

        worksheet.write(1, 1, "", merge_format1)
        worksheet.write(4, 1, "", merge_format1)
        worksheet.write(6, 1, "", merge_format1)

        worksheet.write(1, 2, "id", merge_format1)
        worksheet.write(4, 2, "id", merge_format1)
        worksheet.write(6, 2, "id", merge_format1)

        worksheet.write(1, 3, "emp_id", merge_format1)
        worksheet.write(4, 3, "emp_id", merge_format1)
        worksheet.write(6, 3, "emp_id", merge_format1)

        worksheet.write(1, 4, "Emp_No", merge_format1)
        worksheet.write(4, 4, "Emp_No", merge_format1)
        worksheet.write(6, 4, "Emp_No", merge_format1)
        worksheet.write(1, 5, "Eff_Yr", merge_format1)
        worksheet.write(4, 5, "Eff_Yr", merge_format1)
        worksheet.write(6, 5, "Eff_Yr", merge_format1)
        worksheet.write(1, 6, "Eff_Mth", merge_format1)
        worksheet.write(4, 6, "Eff_Mth", merge_format1)
        worksheet.write(6, 6, "Eff_Mth", merge_format1)
        worksheet.write(1, 7, "organization", merge_format1)
        worksheet.write(4, 7, "organization", merge_format1)
        worksheet.write(6, 7, "organization", merge_format1)
        worksheet.write(1, 8, "location_id", merge_format1)
        worksheet.write(4, 8, "location_id", merge_format1)
        worksheet.write(6, 8, "location_id", merge_format1)
        worksheet.write(1, 9, "Emp_Name", merge_format1)
        worksheet.write(4, 9, "Emp_Name", merge_format1)
        worksheet.write(6, 9, "Emp_Name", merge_format1)
        worksheet.write(1, 10, "Self_Rating", merge_format1)
        worksheet.write(4, 10, "Self_Rating", merge_format1)
        worksheet.write(6, 10, "Self_Rating", merge_format1)
        worksheet.write(1, 11, "Mgr_Rating", merge_format1)
        worksheet.write(4, 11, "Mgr_Rating", merge_format1)
        worksheet.write(6, 11, "Mgr_Rating", merge_format1)
        worksheet.write(1, 12, "BU_Head_Rating", merge_format1)
        worksheet.write(4, 12, "BU_Head_Rating", merge_format1)
        worksheet.write(6, 12, "BU_Head_Rating", merge_format1)
        worksheet.write(1, 13, "DIR_Rating", merge_format1)
        worksheet.write(4, 13, "DIR_Rating", merge_format1)
        worksheet.write(6, 13, "DIR_Rating", merge_format1)
        worksheet.write(1, 14, "Promotion", merge_format1)
        worksheet.write(4, 14, "Promotion", merge_format1)
        worksheet.write(6, 14, "Promotion", merge_format1)
        worksheet.write(1, 15, "Promotion%", merge_format1)
        worksheet.write(4, 15, "Promotion%", merge_format1)
        worksheet.write(6, 15, "Promotion%", merge_format1)
        worksheet.write(1, 16, "New_Desig", merge_format1)
        worksheet.write(4, 16, "New_Desig", merge_format1)
        worksheet.write(6, 16, "New_Desig", merge_format1)
        worksheet.write(1, 17, "Correction%", merge_format1)
        worksheet.write(4, 17, "Correction%", merge_format1)
        worksheet.write(6, 17, "Correction%", merge_format1)
        # worksheet.write(1, 5, "Enter Ratings", merge_format1)
        worksheet.write(4, 18, "Enter Ratings", merge_format1)
        worksheet.write(6, 18, "New Comp Plan", merge_format1)
        # worksheet.write(1, 5, "Enter Ratings", merge_format1)
        worksheet.write(4, 19, "comparative_salary", merge_format1)
        worksheet.write(6, 19, "Revised VP", merge_format1)
        # worksheet.write(1, 5, "Enter Ratings", merge_format1)
        worksheet.write(4, 20, "Existing_Job_Level", merge_format1)
        worksheet.write(6, 20, "status", merge_format1)
        # worksheet.write(1, 5, "Enter Ratings", merge_format1)
        worksheet.write(4, 21, "New_Job_Level", merge_format1)
        # worksheet.write(6, 5, "New Comp Plan", merge_format1)
        worksheet.write(6, 22, "Existing_Job_Level", merge_format1)
        worksheet.write(6, 23, "New_Job_Level", merge_format1)
        worksheet.write(6, 24, "comparative_salary", merge_format1)
        worksheet.write(6, 25, "modified", merge_format1)
        worksheet.write(6, 26, "modified_by", merge_format1)
        # worksheet.merge_range('B9:E9', 'Total', merge_format1)
        # worksheet.write(8, 6, "", merge_format1)
        # worksheet.merge_range('G9:H9', 'Total', merge_format1)





