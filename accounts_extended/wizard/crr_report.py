from odoo import models, fields, api
import xlsxwriter
import base64
import calendar
from io import BytesIO
from datetime import date, timedelta,datetime


class AccountQuarterlyReportWizard(models.TransientModel):
    _name = 'account.quarterly.report.wizard'
    _description = 'Quarterly CRR Report Wizard'

    def _default_start_date(self):
        """Calculate the start date of the current financial year."""
        today = date.today()
        fiscal_start_month = 4  # Assuming April is the fiscal start month
        fiscal_year = today.year if today.month >= fiscal_start_month else today.year - 1
        return date(fiscal_year, fiscal_start_month, 1)

    def _default_end_date(self):
        """Set the end date to the current date."""
        return date.today()

    start_date = fields.Date(string='Start Date',default=_default_start_date,required=True,)
    end_date = fields.Date(
        string='End Date',
        default=_default_end_date,
        required=True,
    )
    report_file = fields.Binary('Report File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)
    # account_ids = fields.Many2many("account.account", string="Accounts")

    def action_generate_report(self):

        report_content = self._generate_excel_report()

        self.report_file = base64.b64encode(report_content)
        self.file_name = f"CRR_Quarterly_Report_{datetime.now().strftime('%Y%m%d')}.xlsx"

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.quarterly.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def _fetch_crr_data(self,account_type):
        """Fetch CRR journal entries (Debit - Credit) for each month."""
        crr_data = {}
        start_date = self.start_date
        end_date = self.end_date
        start_year = start_date.year
        end_year = end_date.year

        move_line_obj = self.env['account.move.line']
        months = [
            ('April', 4), ('May', 5), ('June', 6),
            ('July', 7), ('August', 8), ('September', 9),
            ('October', 10), ('November', 11), ('December', 12),
            ('January', 1), ('February', 2), ('March', 3)
        ]
        quarters = {
            'Q1': [4, 5, 6],
            'Q2': [7, 8, 9],
            'Q3': [10, 11, 12],
            'Q4': [1, 2, 3],
        }
        selected_accounts = self.env['account.account'].sudo().search([('account_type','=',account_type)])
        expense_code = []
        month_data = []
        # budget_code = []
        current_date = start_date
        while current_date <= end_date:
            month_data.append((current_date.year, current_date.month))
            # Move to the first day of the next month
            next_month = current_date.month % 12 + 1
            next_year = current_date.year + (1 if next_month == 1 else 0)
            current_date = current_date.replace(year=next_year, month=next_month, day=1)
        for crr in selected_accounts:
            # [('account_id', 'in',self.general_budget_id.account_ids.ids),
            # ('date', '>=', self.date_from),
            # ('date', '<=', self.date_to)
            #             ]
            # budget_id = self.env['crossovered.budget.lines'].search([
            #                                                 ('date_from','>=',start_date),
            #                                                 ('budget_code','!=',False),
            #                                                 ('general_budget_id.account_ids','in',crr.ids),
            #                                                 ('crossovered_budget_id.state','not in',('draft','cancel'))
            #                                                 ])
            # if budget_id.mapped('budget_code'):
            #     budget_code.append(budget_id.mapped('budget_code'))
            crr_data[f"{crr.name}"] = {}
            expense_code.append(crr.code)
            for month_name, month_num in months:
                total = 0
                for year ,num_month in month_data:
                    if month_num == num_month or month_num == num_month:
                        fn_start_date = datetime(year, month_num, 1).date()
                        last_day = calendar.monthrange(year, month_num)[1]
                        fn_end_date = datetime(year, month_num, last_day).date()
                        total = move_line_obj.search([
                            ('account_id', '=', crr.id),
                            ('move_id.state', '=', 'posted'),
                            ('date', '>=', fn_start_date),
                            ('date', '<=', fn_end_date),
                        ]).mapped(lambda l: l.debit - l.credit)
                crr_data[f"{crr.name}"][month_name] = float(sum(total)) if total else 0

            for quarter, months_list in quarters.items():
                quarter_total = sum(
                    crr_data[f"{crr.name}"].get(month_name, 0) for month_name, m in months if m in months_list
                )
                crr_data[f"{crr.name}"][quarter] = quarter_total

        return {'crr_data':crr_data,'expense_code':expense_code}


    def _generate_excel_report(self):
        """Generate an Excel file from CRR data, including company and transaction details."""
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        sheet = workbook.add_worksheet('Quarterly CRR Report')

        # Define formats
        title_format = workbook.add_format({'bold': True, 'font_size': 12,'text_wrap': True})
        sheet.set_column('A:A', 20)  
        sheet.set_column('B:B',35) 
        sheet.set_column('C:D',20) 
        sheet.set_column('E:U',15) 
        sheet.set_row(13,30) 
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'font_color': '#000000',
            'border': 1,
            'align': 'center',
        })
        cell_format = workbook.add_format({'border': 1,'text_wrap': True})
        value_format = workbook.add_format({'num_format': '0.00', 'border': 1})  # Float format and border
        total_value_format = workbook.add_format({'num_format': '0.00', 'border': 1,'bold': True,'bg_color': '#F4B084',})  # Float format and border

        total_format = workbook.add_format({
            'bold': True,
            'bg_color': '#F4B084',
            'border': 1,
        })

        # Add company and transaction details
        sheet.write(0, 1, 'Group Company Name', title_format)
        sheet.write(0, 2, self.env.company.name)  # Replace with actual company name
        sheet.write(1, 1, 'Group Company Code', title_format)
        sheet.write(1, 2, '')  # Replace with actual company code

        sheet.write(3, 1, 'Type of Transaction', title_format)
        sheet.write(3, 2, 'OPEX', cell_format)
        sheet.write(3, 3, 'Operating Expenditure', cell_format)
        sheet.write(4, 2, 'CAPEX', cell_format)
        sheet.write(4, 3, 'Capital Expenditure', cell_format)
        sheet.write(5, 2, 'OCIF', cell_format)
        sheet.write(5, 3, 'Operating Cash In Flow', cell_format)
        sheet.write(6, 2, 'NOCIF', cell_format)
        sheet.write(6, 3, 'Non-Operating Cash In Flow', cell_format)

        # Headers for the CRR table
        headers = [
            'Cash Payments','Cash OutFlow Heads\nExpense account','Budget Code','Expense Code','Year Total', 'April', 'May', 'June', 'Q1',
            'July', 'August', 'September', 'Q2',
            'October', 'November', 'December', 'Q3',
            'January', 'February', 'March', 'Q4']
        header_start_row = 13
        for col_num, header in enumerate(headers):
            sheet.write(header_start_row, col_num, header, header_format)

        # Populate CRR data
        row = header_start_row + 1
        yearly_totals = 0  # Initialize totals for all headers except 'CRR'
        account_type = 'expesne'
        income_data = self._fetch_crr_data(account_type)
        exp_row = row
        bud_row = row
        for crr, values in income_data['crr_data'].items():
            sheet.write(row,1, crr, cell_format)  # crr
            year_total = 0
            for col_num, header in enumerate(headers[2:], start=2):
                value = values.get(header, 0)
                sheet.write(row, col_num, float(value), value_format)
                if 'Q' not in header and 'Year Total' not in header:  # Only aggregate monthly values
                    year_total += value
                    yearly_totals += value

            # Write Year Total
            sheet.write(row,4, year_total, value_format)
            row += 1
        for code in income_data['expense_code']:
            sheet.write(exp_row,2,code, cell_format) 
            exp_row+=1 
        # for code in income_data['budget_code']:
        #     sheet.write(bud_row,3,code, cell_format) 
        #     bud_row+=1 

        # Write totals row
        sheet.write(row, 1, 'Total OutFlow(A)', total_format)
        row +=2
        a_total =yearly_totals
        yearly_totals = 0
        sheet.write(row, 0, 'Cash Receipts ', header_format)
        sheet.write(row, 1, 'Cash Receipts Cash InFlow Heads\nInocme account', header_format)
        sheet.set_row(row,30)  # Row B14
        row +=2


        account_type = 'income'
        exp_row = 0
        bud_row = 0
        expense_data = self._fetch_crr_data(account_type)
        exp_row = row
        bud_row = row

        for crr, values in expense_data['crr_data'].items():
            sheet.write(row,1, crr, cell_format)  # CRR
            year_total = 0
            for col_num, header in enumerate(headers[3:], start=3):
                value = values.get(header,0)
                sheet.write(row, col_num,float(value), value_format)
                if 'Q' not in header and 'Year Total' not in header:  # Only aggregate monthly values
                    year_total += value
                    yearly_totals += value

            # Write Year Total
            sheet.write(row,4, year_total, value_format)
            row += 1
        b_total =yearly_totals
        for code in expense_data['expense_code']:
            sheet.write(exp_row,2,code, cell_format) 
            exp_row+=1 
        # for code in expense_data['budget_code']:
        #     sheet.write(bud_row,3,str(code), cell_format) 
        #     bud_row+=1 

        # Write totals row
        sheet.write(row, 1, 'Total InFlow(B)', total_format)
        sheet.write(row,4, yearly_totals, total_value_format)
        row+=1
        sheet.write(row, 1, 'SURPLUS/DEFICIT (B-A)',total_format)
        sheet.write(row,4, b_total-a_total,total_value_format)
        row+=1
        sheet.write(row, 1, 'Sources of Fund:',total_format)
        row+=1
        sheet.write(row, 1, 'Tax Entity 1',total_format)
        row+=1
        sheet.write(row, 1, 'Tax Entity 2',total_format)
        row+=1
        sheet.write(row, 1, 'Others',total_format)
        row+=1
        sheet.write(row, 1, 'Total Requirement (D = C)',total_format)
        row+=1
        sheet.write(row, 1, 'Difference',total_format)
        workbook.close()
        buffer.seek(0)
        return buffer.read()
