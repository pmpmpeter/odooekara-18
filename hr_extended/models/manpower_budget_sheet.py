import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone


class ManpowerBudgetSheet(models.AbstractModel):
    _name = 'report.hr_extended.report_manpower_budget_sheet'
    _inherit = "report.report_xlsx.abstract"


    def generate_xlsx_report(self, workbook,data,wiz_data):
        # main_product = data
        # company_name = main_product['company_name']
        # company_id = main_product['company_id']
        # date_from = main_product['date_from']
        # date_to = main_product['date_to']

        sheet = workbook.add_worksheet('manpower_budget_sheet')
        year= self.get_financial_year(wiz_data.start_date)
        y_1 = year['year_one']
        y_2 = year['year_two']

        # sheet.protect()
        merge_format1 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','text_wrap': True,'valign': 'vcenter',})
        merge_format2 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#c5e0b3','text_wrap': True,})
        merge_format3 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#b4c6e7','text_wrap': True,})
        merge_format4 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#FFFF00','text_wrap': True,})
        merge_format5 = workbook.add_format({'bold': 1,'border': 1,'align': 'center','valign': 'vcenter','border_color': '#000000','fg_color': '#fbe4d5','text_wrap': True,})

        sheet.set_column('A:A', 30)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 40)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 20)
        sheet.set_column('F:F', 20)
        sheet.set_column('G:G', 15)
        sheet.set_column('H:H', 15)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.set_column('L:L', 15)
        sheet.set_column('M:M', 15)
        sheet.set_column('N:N', 15)
        sheet.set_column('O:O', 15)
        sheet.set_column('P:J', 15)
        sheet.set_column('Q:Q', 15)
        sheet.set_column('R:R', 15)
        sheet.set_column('S:S', 15)
        sheet.set_column('T:T', 15)
        sheet.set_column('U:U', 15)
        sheet.set_column('V:V', 15)
        sheet.set_column('W:W', 15)
        sheet.set_column('X:X', 15)
        sheet.set_column('Y:Y', 15)
        sheet.set_column('Z:Z', 15)
        sheet.set_column('AA:AA', 15)
        sheet.set_column('AB:AB', 15)
        sheet.set_column('AC:AC', 15)
        sheet.set_column('AD:AD', 15)
        sheet.set_column('AE:AE', 15)
        sheet.set_column('AG:AG', 15)
        sheet.set_column('AH:AH', 15)
        sheet.set_column('AI:AI', 15)
        sheet.write(5, 0, "Tax Entity", merge_format3)
        sheet.write(0, 0, "Guideline", merge_format2)
        sheet.write(3, 0, " Manpower for FY "+str(y_1)+'-'+str(y_2), merge_format1)
        sheet.write(5, 1, "Category", merge_format3)
        sheet.write(5, 2, "Type of \n Manpower Request", merge_format3)
        sheet.write(5, 3, "Business Unit", merge_format3)
        sheet.write(5, 4, "Department", merge_format3)
        sheet.write(5, 5, "Role/Designation", merge_format3)
        sheet.write(5, 6, "Job Level/Grade", merge_format3)
        sheet.write(5, 7, "Justification", merge_format3)
        sheet.write(5, 8, "CTC/Month", merge_format3)
        sheet.merge_range('J5:U5', 'No. of Employees', merge_format1)
        sheet.merge_range('X5:AI5', 'Total Salary Per Month', merge_format1)
        sheet.merge_range('D2:H2', 'If an employee is added in month 1, pls consider that employee for all the 12 months', merge_format1)
        sheet.merge_range('D1:I1', 'Kindly fill the details of existing Manpower/additional Manpower to be recruited for Budget Year FY '+str(y_1)+'-'+str(y_2), merge_format1)
        sheet.write(5, 9, "Apr/"+str(y_1), merge_format4)
        sheet.write(5, 10, "May/"+str(y_1), merge_format4)
        sheet.write(5, 11, "Jun/"+str(y_1), merge_format4)
        sheet.write(5, 12, "Jul/"+str(y_1), merge_format4)
        sheet.write(5, 13, "Aug/"+str(y_1), merge_format4)
        sheet.write(5, 14, "Sep/"+str(y_1), merge_format4)
        sheet.write(5, 15, "Oct/"+str(y_1), merge_format4)
        sheet.write(5, 16, "Nov/"+str(y_1), merge_format4)
        sheet.write(5, 17, "Dec/"+str(y_1), merge_format4)
        sheet.write(5, 18, "Jan/"+str(y_2), merge_format4)
        sheet.write(5, 19, "Feb/"+str(y_2), merge_format4)
        sheet.write(5, 20, "Mar/"+str(y_2), merge_format4)
        sheet.write(5, 21, "FY "+str(y_1)+'-'+str(y_2), merge_format4)
        sheet.write(5, 22, "", merge_format5)
        sheet.write(5, 23, "Apr/"+str(y_1), merge_format4)
        sheet.write(5, 24, "May/"+str(y_1), merge_format4)
        sheet.write(5, 25, "Jun/"+str(y_1), merge_format4)
        sheet.write(5, 26, "Jul/"+str(y_1), merge_format4)
        sheet.write(5, 27, "Aug/"+str(y_1), merge_format4)
        sheet.write(5, 28, "Sep/"+str(y_1), merge_format4)
        sheet.write(5, 29, "Oct/"+str(y_1), merge_format4)
        sheet.write(5, 30, "Nov/"+str(y_1), merge_format4)
        sheet.write(5, 31, "Dec/"+str(y_1), merge_format4)
        sheet.write(5, 32, "Jan/"+str(y_2), merge_format4)
        sheet.write(5, 33, "Feb/"+str(y_2), merge_format4)
        sheet.write(5, 34, "Mar/"+str(y_2), merge_format4)
        sheet.set_row(0,40) 
        sheet.set_row(1,40) 
        sheet.set_row(5,30) 
        row = 6
        manpower_ids = self.env['manpower.budget'].search([('create_date','>=',wiz_data.start_date),('create_date','<=',wiz_data.end_date),('state','=','done')])
        if manpower_ids:
            for manpower in manpower_ids:
                sheet.write(row, 0,manpower.tax_entity_id.name)
                sheet.write(row, 1,manpower.category_id.name)
                sheet.write(row, 2,manpower.manpower_request_type)
                sheet.write(row, 3,manpower.business_unit_id.name)
                sheet.write(row, 4,manpower.department_id.name)
                sheet.write(row, 5,manpower.position_id.name)
                sheet.write(row, 6,manpower.job_level_id.name)
                sheet.write(row, 7,manpower.justification)
                sheet.write(row, 8,manpower.ctc_month)
                col = 9
                for line in manpower.employee_monthly_ids:
                    sheet.write(row,col, line.employee_count)
                    col+=1
                col = 23
                for line in manpower.employee_monthly_ids:
                    sheet.write(row,col, line.employee_count*manpower.ctc_month)
                    col+=1
                row += 1

    def get_financial_year(self,current_date):
        current_year = current_date.year
        # Define fiscal year start month (e.g., April = 4)
        fiscal_start_month = 4
        # Determine financial year range
        if current_date.month >= fiscal_start_month:
            start_year = current_year
            end_year = current_year + 1
        else:
            start_year = current_year - 1
            end_year = current_year

        return {'year_one':start_year,'year_two':end_year}

