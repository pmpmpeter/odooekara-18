import pytz
import xlsxwriter
import base64

from odoo import fields, models, api
from io import BytesIO
from datetime import datetime
from pytz import timezone


class HRCompliances(models.AbstractModel):
    _name = 'report.hr_attendance_extended.report_hr_compliances'
    _inherit = "report.report_xlsx.abstract"


    def generate_xlsx_report(self, workbook,data,employee):

        # main_product = data
        # company_name = main_product['company_name']
        # company_id = main_product['company_id']
        # date_from = main_product['date_from']
        # date_to = main_product['date_to']

        worksheet = workbook.add_worksheet('hr_compliances')

        worksheet.protect()
        merge_format1 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'valign': 'vcenter', })
        left_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'left',
            'text_wrap': True,

            'valign': 'vcenter', })



        worksheet.set_column('A:A', 10)
        # worksheet.set_row(2, 20)

        worksheet.set_column('B:B', 20)
        worksheet.set_column('C:C', 20)
        worksheet.set_column('D:D', 20)
        worksheet.set_column('E:E', 20)
        worksheet.set_column('F:F', 20)
        worksheet.set_column('G:G', 20)
        worksheet.set_column('H:H', 20)
        worksheet.set_column('I:I', 20)
        worksheet.set_column('J:J', 20)

        worksheet.merge_range('B1:H1', 'FORM XII', merge_format1)
        worksheet.merge_range('B2:H2', '[See rule 74]', merge_format1)
        worksheet.merge_range('B3:H3', 'Register of Particular of Contractor', merge_format1)
        worksheet.set_row(4, 80)
        worksheet.merge_range('B5:H5', '(1) Name and address of the principal employer:  \n'' Bangalore Street, BENGALURU  \n''(BANGALORE) URBAN, KARNATAKA - 560001 \n''(2) Name and address of the establishment: \n'' Same as above ', left_format)
        # worksheet.merge_range('B3:H3', 'Register of Particular of Contractor', merge_format1)
        # worksheet.merge_range(4, 1, 5, 7, data, merge_format1)

        worksheet.merge_range('B8:B9', 'Sl No.', merge_format1)
        worksheet.merge_range('C8:C9', 'Name and Address of Contractor', merge_format1)
        worksheet.merge_range('D8:D9', 'Nature of Work of Contract', merge_format1)
        worksheet.merge_range('E8:E9', 'Location Contract Work', merge_format1)
        worksheet.merge_range('F8:G8', 'Period of contract', merge_format1)
        worksheet.write(8, 5, "From", merge_format1)
        worksheet.write(8, 6, "To", merge_format1)
        worksheet.merge_range('H8:H9', 'Maximum Number of Workmen Employed by Contractor ', merge_format1)


        # worksheet.merge_range('A2:I2', datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d-%m-%Y') +' ' 'To' ' ' + datetime.datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d-%m-%Y'), format_date)
        worksheet.write(16, 1, "Place", left_format)
        worksheet.write(17, 1, "Date",left_format)
        # worksheet.write(16, 6, "Signature of the Licensing Officer", merge_format1)
        worksheet.merge_range('G17:H17', 'Signature of the Licensing Officer', left_format)






        worksheet2 = workbook.add_worksheet('Register and overtime Payment')

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
        # worksheet.set_row(2, 20)

        worksheet2.set_column('B:B', 15)
        worksheet2.set_column('C:C', 15)
        worksheet2.set_column('D:D', 15)
        worksheet2.set_column('E:E', 15)
        worksheet2.set_column('F:F', 15)
        worksheet2.set_column('G:G', 15)
        worksheet2.set_column('H:H', 15)
        worksheet2.set_column('I:I', 15)
        worksheet2.set_column('J:J', 15)
        worksheet2.set_column('K:K', 15)
        worksheet2.set_column('L:L', 15)
        worksheet2.set_column('M:M', 15)
        worksheet2.set_column('N:N', 15)
        worksheet2.set_column('O:O', 30)
        worksheet2.set_column('P:P', 10)

        worksheet2.merge_range('B1:O1', '[FORM  No. 9', merge_format3)
        worksheet2.merge_range('B2:O2', '[See Rule 107]', merge_format3)
        worksheet2.merge_range('B3:O3', 'REGISTER OF OVERTIME AND PAYMENT', merge_format3)

        worksheet2.merge_range('B5:O5', 'Form No. 9 under Rule 107 of Karnataka Factories Rules, 1969.', left_format)
        worksheet2.merge_range('B7:O7', 'Form No. IV under Rule 28(2) of Karnataka Minimum Wages Rules, 1958.', left_format)
        worksheet2.merge_range('B6:O6', 'Form No. XIII under Rule 78(1) (a)(iii) of Contract Labour (Regulation and Abolition) Karnataka Rules, 1974. ', left_format)

        worksheet2.merge_range('B9:C9', 'Name and Address of the Establishment', merge_format2)
        worksheet2.merge_range('D9:E9', '', merge_format3)
        worksheet2.merge_range('F9:G9', 'Name and Address of the  Principal Employer ', merge_format2)
        worksheet2.merge_range('H9:I9', ' ', merge_format3)
        # worksheet2.merge_range('H9:I9', ' ', merge_format3)
        worksheet2.merge_range('K9:L9', ' NIL', merge_format3)
        worksheet2.write(8, 9, "Name and Address of the the Contractor (if any) :", merge_format2)
        worksheet2.write(8, 12, "Place of Work", merge_format2)
        worksheet2.write(8, 13, "Bangalore", merge_format2)
        worksheet2.write(9, 12, " Month/Year", merge_format2)


        worksheet2.merge_range('B12:B13', 'Sl. No. ', merge_format3)
        worksheet2.merge_range('C12:C13', ' Employee Name', merge_format3)
        worksheet2.merge_range('D12:D13', ' Father/Husband Name', merge_format3)
        worksheet2.merge_range('E12:E13', ' Sex', merge_format3)
        worksheet2.merge_range('F12:F13', 'Designation/Employment No. ', merge_format3)
        worksheet2.merge_range('G12:H12', 'Particulars of OT Work ', merge_format3)


        worksheet2.merge_range('I12:I13', ' Normal rate of wages per hour', merge_format3)
        worksheet2.merge_range('J12:J13', 'Overtime wages per hour', merge_format3)
        worksheet2.merge_range('K12:K13', 'Normal piece rate of wages ', merge_format3)
        worksheet2.merge_range('L12:L13', 'OT piece rate of wages ', merge_format3)
        worksheet2.merge_range('M12:M13', ' Total OT earnings', merge_format3)
        worksheet2.merge_range('N12:N13', ' Date of payment', merge_format3)
        worksheet2.merge_range('O12:O13', ' Signature/Thumb impression of the Employee', merge_format3)
        worksheet2.write(12, 6, "Date", merge_format2)
        worksheet2.write(12, 7, "Hours", merge_format2)




        # worksheet2.merge_range('A2:I2', datetime.datetime.strptime(str(date_from), '%Y-%m-%d').strftime('%d-%m-%Y') +' ' 'To' ' ' + datetime.datetime.strptime(str(date_to), '%Y-%m-%d').strftime('%d-%m-%Y'), format_date)
        worksheet2.write(13, 1, "1", merge_format2)
        worksheet2.write(13, 2, "", merge_format2)
        worksheet2.write(13, 3, "2", merge_format2)
        worksheet2.write(13, 4, "3", merge_format2)
        worksheet2.write(13, 5, "4", merge_format2)
        worksheet2.write(13, 6, "5", merge_format2)
        worksheet2.write(13, 7, "6", merge_format2)
        worksheet2.write(13, 8, "7", merge_format2)
        worksheet2.write(13, 9, "8", merge_format2)
        worksheet2.write(13, 10, "9", merge_format2)
        worksheet2.write(13, 11, "10", merge_format2)
        worksheet2.write(13, 12, "11", merge_format2)
        worksheet2.write(13, 13, "12", merge_format2)
        worksheet2.write(13, 14, "13", merge_format2)
        # worksheet2.write(13, 10, "Individual Sum Insured per parent", merge_format2)



        worksheet3 = workbook.add_worksheet('Form D_Eql Remuneration')

        worksheet3.protect()
        merge_format3 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'fg_color': '#d8d8d8',
            'valign': 'vcenter', })
        yelow_format = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'fg_color': '#FFFF00',
            'valign': 'vcenter', })

        worksheet3.set_column('A:A', 10)
        # worksheet.set_row(2, 20)

        worksheet3.set_column('B:B', 30)
        worksheet3.set_column('C:C', 20)
        worksheet3.set_column('D:D', 20)
        worksheet3.set_column('E:E', 20)
        worksheet3.set_column('F:F', 20)
        worksheet3.set_column('G:G', 20)
        worksheet3.set_column('H:H', 20)
        worksheet3.set_column('I:I', 20)
        worksheet3.set_column('J:J', 30)
        worksheet3.set_column('K:K', 20)
        worksheet3.set_column('L:L', 20)
        worksheet3.set_column('M:M', 20)
        worksheet3.set_column('N:N', 20)
        worksheet3.set_column('O:O', 20)
        worksheet3.set_column('P:P', 20)

        worksheet3.merge_range('A2:J2', 'Equal Remuneration Act \n' ' FORM D See\n' 'Rule 6 \n ', merge_format3)
        worksheet3.merge_range('A3:J3', 'Register to maintained by the employer under Rule 6 of  the Equal Remuneration Rules, 1976 ', merge_format3)
        worksheet3.merge_range('A6:B6', 'Name of the Establishment with full address: ', merge_format3)


        worksheet3.merge_range('A8:B8', 'Total number of men workers employed: ', yelow_format)
        worksheet3.merge_range('A9:B9', 'Total number of women workers employed: ', yelow_format)
        worksheet3.merge_range('A10:B10', 'Total number of workers employed: ', yelow_format)

        worksheet3.merge_range('A12:A13', 'Category of workers  ', merge_format3)
        worksheet3.merge_range('B12:B13', 'Brief description of work  ', merge_format3)
        worksheet3.merge_range('C12:C13', 'No. of men employed  ', merge_format3)
        worksheet3.merge_range('D12:D13', 'No. of women employed  ', merge_format3)
        worksheet3.merge_range('E12:E13', 'Rate of remuneration paid  ', merge_format3)
        worksheet3.merge_range('F12:F13', 'Basic wage or salary   ', merge_format3)
        worksheet3.write(12, 6, "Dearness allowance ", merge_format2)

        worksheet3.merge_range('H12:I12', 'Components of remuneration   ', merge_format3)
        worksheet3.write(12, 7, "House Rent allowance ", merge_format2)
        worksheet3.write(12, 8, "Other allowances ", merge_format2)
        worksheet3.write(12, 9, "Cash value of concessional supply of essential commodities ", merge_format2)
        worksheet3.write(11, 9, "", merge_format2)

        worksheet3.write(13, 0, "1", merge_format2)
        worksheet3.write(13, 1, "2", merge_format2)
        worksheet3.write(13, 2, "3", merge_format2)
        worksheet3.write(13, 3, "4", merge_format2)
        worksheet3.write(13, 4, "5", merge_format2)
        worksheet3.write(13, 5, "6", merge_format2)
        worksheet3.write(13, 6, "7", merge_format2)
        worksheet3.write(13, 7, "8", merge_format2)
        worksheet3.write(13, 8, "9", merge_format2)
        worksheet3.write(13, 9, "10", merge_format2)
        worksheet3.write(7, 2, "", yelow_format)
        worksheet3.write(7, 3, "", yelow_format)
        worksheet3.write(8, 2, "", yelow_format)
        worksheet3.write(8, 3, "", yelow_format)
        worksheet3.write(9, 2, "", yelow_format)
        worksheet3.write(9, 3, "", yelow_format)
        worksheet3.write(11, 6, "", merge_format3)
        # worksheet3.write(13, 10, "11", merge_format2)





        worksheet4 = workbook.add_worksheet('Form R-working women nite shift')

        worksheet4.protect()
        merge_format4 = workbook.add_format({
            'bold': 1,
            'border': 1,
            'align': 'center',
            'text_wrap': True,
            'fg_color': '#d8d8d8',
            'valign': 'vcenter', })

        top_format = workbook.add_format({
            'bold': 1,
            'border': 3,
            'top': 1, })
        leftt_format = workbook.add_format({
            'bold': 1,
            'border': 3,
            'left': 1, })
        right_format = workbook.add_format({
            'bold': 1,
            'border': 3,
            'right': 1, })
        bot_format = workbook.add_format({
            'bold': 1,
            'border': 3,
            'bottom': 1, })

        worksheet4.set_column('A:A', 5)
        # worksheet.set_row(2, 20)

        worksheet4.set_column('B:B',5)
        worksheet4.set_column('C:C', 30)
        worksheet4.set_column('D:D', 30)
        worksheet4.set_column('E:E', 40)
        worksheet4.set_column('F:F', 30)
        worksheet4.set_column('G:G', 5)
        worksheet4.set_column('H:H', 20)
        worksheet4.set_column('I:I', 20)
        worksheet4.set_column('J:J', 30)
        worksheet4.set_column('K:K', 20)
        worksheet4.set_column('L:L', 20)
        worksheet4.set_column('M:M', 20)
        worksheet4.set_column('N:N', 20)
        worksheet4.set_column('O:O', 20)
        worksheet4.set_column('P:P', 20)

        worksheet4.merge_range('B2:G2', '', top_format)
        worksheet4.merge_range('B3:B29', '', leftt_format)
        worksheet4.merge_range('G3:G29', '', right_format)
        worksheet4.merge_range('C29:F29', '', bot_format)

        worksheet4.merge_range('C3:F3', 'Form R  ', merge_format3)
        worksheet4.merge_range('C5:D5', 'Name and address of the establishment  ',left_format)
        worksheet4.merge_range('C6:D6', 'Name and address of employer/ Director ', left_format)
        worksheet4.merge_range('C7:D7', 'Postal address for communication:  ', left_format)
        worksheet4.merge_range('C9:C10', 'Total number of employees  ', left_format)
        worksheet4.merge_range('D9:D11', ' Men \nWomen \nTotal', left_format)
        # worksheet4.write(8, 3, "Men", merge_format2)
        # worksheet4.write(9, 3, "Women", merge_format2)
        # worksheet4.write(10, 3, "Total", merge_format2)
        # worksheet4.write('D9', 'Men', left_border_format)
        worksheet4.write('E6', 'G F - 2, Greenery 16 Plain, Bangalore Street, BENGALURU(BANGALORE) URBAN, KARNATAKA - 560001', left_format)
        worksheet4.write('E7', 'G F - 2, Greenery 16 Plain, Bangalore Street, BENGALURU(BANGALORE) URBAN, KARNATAKA - 560001', left_format)
        worksheet4.write('E9', '', merge_format1)
        worksheet4.write('E10', '', merge_format1)
        worksheet4.write('E11', '', merge_format1)
        worksheet4.merge_range('C13:F13', 'Particulars of Women Employees who are willing to work during night shifts', merge_format1)

        worksheet4.merge_range('C21:F24', 'Any other information employer may also wish to furnish.\n \n NO WOMAN EMPLOYEE WORKS IN NIGHT SHIFT', merge_format1)
        worksheet4.write('C14', 'Name and residential address of the Women employee', merge_format1)
        worksheet4.write('D14', 'Sl. No Nature of work', merge_format1)
        worksheet4.write('E14', 'Mode of transportation provided', merge_format1)
        worksheet4.write('F14', 'Whether security will be provided at work place', merge_format1)
        worksheet4.write('C27', 'Place',left_format)
        worksheet4.write('C28', 'Date', left_format)
        worksheet4.write('E27', 'Signature of the Employer', left_format)
        worksheet4.write('E28', 'Seal of Establishment', left_format)
        # for col in range(1, 8): # Columns B (1) to H (7) (0-based index) worksheet.write(1, col, "", top_border_format)








