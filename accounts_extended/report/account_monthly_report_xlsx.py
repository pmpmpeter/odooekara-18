from odoo import models


class AccountMonthlyXlsx(models.AbstractModel):
    _name = 'report.accounts_extended.account_monthly_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, records):
        header_format = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#D3D3D3'})
        bold_format = workbook.add_format({'bold': True})
        currency_format = workbook.add_format({'num_format': '#,##0.00'})

        sheet = workbook.add_worksheet()

        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        quarters = {"Q1": months[3:6],"Q2": months[6:9],"Q3": months[9:12],"Q4": months[0:3]}

        sheet.write(0, 0, 'Account Type', header_format)
        col = 1
        for month in months:
            sheet.write(0, col, month, header_format)
            col += 1
        for quarter in quarters.keys():
            sheet.write(0, col, quarter, header_format)
            col += 1

        row = 1
        for line in data['account_ids']:
            query = """
                        SELECT
                            TO_CHAR(aml.date, 'Month') AS month,
                            SUM(aml.debit) - SUM(aml.credit) AS total
                        FROM account_move_line aml
                        WHERE aml.account_id = %s
                          AND aml.date >= %s
                          AND aml.date <= %s
                        GROUP BY TO_CHAR(aml.date, 'Month')
                    """
            self.env.cr.execute(query, (line, data.get('start_date'), data.get('end_date')))
            results = self.env.cr.fetchall()
            monthly_data = {month.strip(): total for month, total in results}
            account = self.env['account.account'].browse(line)
            sheet.write(row, 0, account.name, bold_format)  # Account Type

            monthly_totals = {month: 0 for month in months}  # Default to 0 for all months
            for month, total in monthly_data.items():
                monthly_totals[month] = total

            col = 1
            for month in months:
                sheet.write(row, col, monthly_totals.get(month, 0), currency_format)
                col += 1

            for quarter, quarter_months in quarters.items():
                quarter_total = sum(monthly_totals[month] for month in quarter_months)
                sheet.write(row, col, quarter_total, currency_format)
                col += 1

            row += 1

        sheet.set_column('A:A', 30)
        sheet.set_column('B:N', 15)
