from odoo import models, fields, api
import xlsxwriter
import base64
import calendar
from io import BytesIO
from datetime import date, timedelta, datetime
from collections import defaultdict,Counter
from dateutil.relativedelta import relativedelta


class AccountCURReportWizard(models.TransientModel):
    _name = 'account.cur.report.wizard'
    _description = 'Cash Utilization Report Wizard'

    def _default_start_date(self):
        """Calculate the start date of the current financial year."""
        today = date.today()
        return date(today.year, today.month, 1)

    def _default_end_date(self):
        """Set the end date to the current date."""
        return date.today()

    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    start_date = fields.Date(string='Start Date', default=_default_start_date, required=True, )
    end_date = fields.Date(
        string='End Date',
        default=_default_end_date,
        required=True,
    )
    groupby_month = fields.Boolean(string='Group By Month',default=False)
    report_file = fields.Binary('Report File', readonly=True)
    file_name = fields.Char('File Name', readonly=True)

    def action_generate_cur_report(self):
        report_content = self._generate_excel_report()
        self.report_file = base64.b64encode(report_content)
        self.file_name = f"Cash_Utilization_Report_{datetime.now().strftime('%d%m%y')}.xlsx"
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'account.cur.report.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }

    def get_month_list(self, start, end):
        months = []
        current = start.replace(day=1)  # Start from 1st of month
        while current <= end:
            months.append(current)  # keep the datetime object
            # Move to next month
            if current.month == 12:
                current = current.replace(year=current.year + 1, month=1)
            else:
                current = current.replace(month=current.month + 1)
        return months
    # def get_month_list(self,start, end):
    #     months = []
    #     current = start.replace(day=1)  # Start from 1st of month
    #     while current <= end:
    #         months.append(current.strftime("%b").upper())  # 'APR', 'MAY'
    #         # Move to next month
    #         if current.month == 12:
    #             current = current.replace(year=current.year + 1, month=1)
    #         else:
    #             current = current.replace(month=current.month + 1)
    #     return months

    def _generate_excel_report(self):
        """Generate an Excel file from CRR data, including company and transaction details."""
        buffer = BytesIO()
        workbook = xlsxwriter.Workbook(buffer)
        sheet = workbook.add_worksheet('Fund Utilization Report')
        title_format = workbook.add_format({'bold': True, 'font_size': 12, 'text_wrap': True})
        sheet.set_column('A:A', 40)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:D', 15)
        sheet.set_row(13, 30)
        sheet.freeze_panes(1, 0)
        # sheet.protect()
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#D9E1F2',
            'font_color': '#000000',
            'border': 1,
            'align': 'right',
            'font_size': 10})
        header_format1 = workbook.add_format({
            'bold': True,
            'font_color': '#000000',
            'border': 1,
            'align': 'right',
            'font_size': 10})
        header_format_num = workbook.add_format({
            'bold': True,
            'font_color': '#000000',
            'num_format': '#,##0.00',
            'border': 1,
            'align': 'right',
            'font_size': 10})
        value_format = workbook.add_format(
            {'num_format': '#,##0.00',
             'border': 1,
             'align': 'right',
             'font_size': 9})  # Float format and border
        value_format1 = workbook.add_format(
            {'num_format': '#,##0.00',
             'border': 1,
             'align': 'right',
             'bg_color': '#FFFF00',
             'font_size': 10})
        name_format = workbook.add_format({
            'align': 'right',
            'border': 1,
            'font_size': 9
        })
        border_fmt = workbook.add_format({'border': 1})
        formatted_date = self.start_date.strftime('%d-%b-%Y')
        formatted_en_date = self.end_date.strftime('%d-%b-%Y')
        # month_list = self.get_month_list(self.start_date, self.end_date)
        month_list_year = self.get_month_list(self.start_date, self.end_date)
        sheet.write(1, 0, 'Particulars  ', header_format)
        sheet.write(1, 1, 'GL Code', header_format)
        sheet.write(1, 2, 'Amount', header_format)
        if not self.groupby_month:
            sheet.write(2, 0, 'Opening Balance as on %s' % (formatted_date), header_format_num)
            sheet.write(2, 1, '', header_format_num)
        else:
            sheet.write(2, 0, 'Opening Balance', value_format)
            sheet.write(2, 1, '', header_format_num)

        records_debit = self.get_cash_bank_utilization_debit(self.start_date, self.end_date, self.company_id)
        records_credit = self.get_cash_bank_utilization_credit(self.start_date, self.end_date, self.company_id)
        # record_credit_card = self.credit_card_expenses(self.start_date, self.end_date, self.company_id)
        year = date.today().year
        year_suffix = str(year)[-2:]
        month_list = []
        if self.groupby_month:
            base_col = 2
            row_num = 0
            for idx, month in enumerate(month_list_year):
                start_col = base_col + idx
                year_suffix = str(month.year)[-2:]
                month_name = month.strftime("%b").upper()
                month_list.append(month_name)
                sheet.write(0, start_col, f"{month_name} {year_suffix}", header_format)
                sheet.write(1, start_col, 'Amount', header_format)
                sheet.set_column(0, start_col, 15)
            sheet.set_column(0, 0, 35)
            # for idx, month in enumerate(month_list):
            #     start_col = base_col + idx
            #     sheet.write(0,start_col, f"{month} {year_suffix}", header_format)
            #     sheet.write(1, start_col, 'Amount', header_format)
            #     sheet.set_column(0, start_col, 15)
            row_num += 1
        if not self.groupby_month:
            opening_balance_1 = 0
            query8 =  """
                        SELECT
                        am.journal_id AS journal_id,
                        aj.name->>'en_US' AS account_name,
                        aj.code AS account_code,
                        SUM(absl.amount) AS balance
                    FROM account_bank_statement_line absl
                    JOIN account_move am ON am.id = absl.move_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    JOIN account_account aa ON aa.id = aj.default_account_id
                    WHERE am.date < %s
                    AND aa.account_type = 'asset_cash'"""
            # Add company_id condition if it exists
            if self.company_id:
                query8 += " AND am.company_id = %s"
                query8 += " GROUP BY aj.code,am.journal_id, aj.name ORDER BY aj.code"
                query_params8 = (self.start_date, self.company_id.id)
            else:
                query_params8 = (self.start_date,)
            self.env.cr.execute(query8, query_params8)
            lines8 = self.env.cr.dictfetchall()
            if not self.groupby_month:
                if lines8 and lines8[0].get('balance') != None:
                    opening_balance_1 = lines8[0].get('balance')
                    sheet.write(2, 2, opening_balance_1, value_format)
                query9 = """
                        SELECT
                        am.journal_id AS journal_id,
                        aj.name->>'en_US' AS account_name,
                        aa.code AS account_code,
                        SUM(absl.amount) AS balance
                    FROM account_bank_statement_line absl
                    JOIN account_move am ON am.id = absl.move_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    JOIN account_account aa ON aa.id = aj.default_account_id
                    WHERE am.date < %s
                    AND aa.account_type = 'asset_cash'"""

                if self.company_id:
                    query9 += " AND am.company_id = %s"

                query9 += " GROUP BY aa.code,am.journal_id, aj.name ORDER BY aa.code"

                if self.company_id:
                    query_params9 = (self.start_date, self.company_id.id)
                else:
                    query_params9 = (self.start_date,)

                self.env.cr.execute(query9, query_params9)
                split_lines = self.env.cr.dictfetchall()
                row_num = 3
                for line in split_lines:
                    sheet.write(row_num, 0, line['account_name'], value_format)
                    sheet.write(row_num, 1, line['account_code'], value_format)
                    sheet.write(row_num, 2, line['balance'] or 0.0, value_format)
                    row_num += 1
                row_num += 1

            #opening balance
            print("opening balance-------------------------------------")
            first_tx_query = """
                             SELECT
                                am.journal_id AS journal_id,
                                aj.name->>'en_US' AS account_name,
                                aa.code AS account_code,
                                am.date AS first_date,
                                absl.amount AS balance
                            FROM account_bank_statement_line absl
                            JOIN account_move am ON am.id = absl.move_id
                            JOIN account_journal aj ON aj.id = am.journal_id
                            JOIN account_account aa ON aa.id = aj.default_account_id
                            WHERE aa.account_type = 'asset_cash'"""
            if self.company_id:
                first_tx_query += " AND am.company_id = %s"
                first_tx_query += " GROUP BY aa.code,am.journal_id, aj.name,am.date,absl.amount ORDER BY am.date ASC LIMIT 1"
                self.env.cr.execute(first_tx_query, (self.company_id.id,))
            else:
                self.env.cr.execute(first_tx_query)
            first_tx = self.env.cr.dictfetchone()
            first_date = first_tx['first_date']
            if first_tx and first_tx.get('first_date') and self.start_date <= first_date <= self.end_date:
                first_month = first_date.strftime('%b').upper()
                first_balance_query = """
                    SELECT
                        am.journal_id AS journal_id,
                        aj.name->>'en_US' AS account_name,
                        aa.code AS account_code,
                        SUM(absl.amount) AS balance
                    FROM account_bank_statement_line absl
                    JOIN account_move am ON am.id = absl.move_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    JOIN account_account aa ON aa.id = aj.default_account_id
                    WHERE aa.account_type = 'asset_cash'
                      AND DATE_TRUNC('month', am.date) = DATE_TRUNC('month', %s)
                """
                if self.company_id:
                    first_balance_query += " AND am.company_id = %s"

                first_balance_query += " GROUP BY am.journal_id, aa.code,am.date, aj.name ORDER BY am.date ASC LIMIT 1"
                if self.company_id:
                    self.env.cr.execute(first_balance_query, (first_date, self.company_id.id))
                else:
                    self.env.cr.execute(first_balance_query, (first_date,))
                first_month_lines = self.env.cr.dictfetchall()
                opening_balance_1 = first_tx.get('balance')
                sheet.write(2, 2, opening_balance_1, value_format)
                row_num = 4
                for line in first_month_lines:
                    sheet.write(row_num, 0, line['account_name'], value_format)  # Account Name
                    sheet.write(row_num, 1, line['account_code'], value_format)  # Account Code
                    sheet.write(row_num, 2, line['balance'] or 0.0, value_format)  # Balance
                    row_num += 1
        else:
            row_num = 2
            opening_balances = {}
            opb_list = []
            for idx, month in enumerate(month_list):
                month_start = (self.start_date.replace(day=1) + relativedelta(months=idx))
                query81 = """
                    SELECT
                        am.journal_id AS journal_id,
                        aj.name->>'en_US' AS account_name,
                        aa.code AS account_code,
                        SUM(absl.amount) AS balance
                    FROM account_bank_statement_line absl
                    JOIN account_move am ON am.id = absl.move_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    JOIN account_account aa ON aa.id = aj.default_account_id
                    WHERE am.date < %s
                    AND aa.account_type = 'asset_cash'
                """
                if self.company_id:
                    query81 += " AND am.company_id = %s"
                query81 += " GROUP BY am.journal_id,aa.code, aj.name ORDER BY aa.code"

                if self.company_id:
                    query_params81 = (month_start, self.company_id.id)
                else:
                    query_params81 = (month_start,)

                self.env.cr.execute(query81, query_params81)
                res = self.env.cr.dictfetchall()
                balance = sum(r.get('balance', 0.0) or 0.0 for r in res) if res else 0.0
                opening_balances[month] = balance
                if balance != 0:
                    col_number = 2 + idx
                    sheet.write(2, col_number, balance, value_format)

            if res and res[0].get('balance') is not None:
                query91 = """
                    SELECT
                        am.journal_id AS journal_id,
                        aj.name->>'en_US' AS account_name,
                        aa.code AS account_code,
                        SUM(absl.amount) AS balance
                    FROM account_bank_statement_line absl
                    JOIN account_move am ON am.id = absl.move_id
                    JOIN account_journal aj ON aj.id = am.journal_id
                    JOIN account_account aa ON aa.id = aj.default_account_id
                    WHERE am.date < %s
                    AND aa.account_type = 'asset_cash'
                """
                if self.company_id:
                    query91 += " AND am.company_id = %s"
                query91 += " GROUP BY am.journal_id,aa.code, aj.name ORDER BY aa.code"

                if self.company_id:
                    query_params91 = (self.end_date, self.company_id.id)
                else:
                    query_params91 = (self.end_date,)

                self.env.cr.execute(query91, query_params91)
                accounts = self.env.cr.dictfetchall()
                row_num = row_num + 1
                base_col = 2
                account_row_map = {}
                for acc in accounts:
                    monthly_balances = []
                    for idx, month in enumerate(month_list):
                        month_start = (self.start_date.replace(day=1) + relativedelta(months=idx))
                        if self.company_id:
                            self.env.cr.execute(query91, (month_start, self.company_id.id))
                        else:
                            self.env.cr.execute(query91, (month_start,))
                        res = self.env.cr.dictfetchall()

                        balance = 0.0
                        for r in res:
                            if r['account_code'] == acc['account_code']:
                                balance = r['balance']
                                break
                        monthly_balances.append(balance)

                    if any(b != 0.0 for b in monthly_balances):
                        sheet.write(row_num, 0, acc['account_name'], value_format)
                        sheet.write(row_num, 1, acc['account_code'], value_format)
                        account_row_map[acc['account_code']] = row_num  # ✅ store row for this account
                        for idx, balance in enumerate(monthly_balances):
                            col_number = base_col + idx
                            sheet.write(row_num, col_number, balance if balance else 0, value_format)
                        row_num += 1
            month_col_map = {
                'JAN': 11, 'FEB': 12, 'MAR': 13, 'APR': 2, 'MAY': 3, 'JUN': 4,
                'JUL': 5, 'AUG': 6, 'SEP': 7, 'OCT': 8, 'NOV': 9, 'DEC': 10
            }
            query91 = """
                                            SELECT
                                                am.journal_id AS journal_id,
                                                aj.name->>'en_US' AS account_name,
                                                aa.code AS account_code,
                                                SUM(absl.amount) AS balance
                                            FROM account_bank_statement_line absl
                                            JOIN account_move am ON am.id = absl.move_id
                                            JOIN account_journal aj ON aj.id = am.journal_id
                                            JOIN account_account aa ON aa.id = aj.default_account_id
                                            WHERE am.date < %s
                                            AND aa.account_type = 'asset_cash'
                                        """
            if self.company_id:
                query91 += " AND am.company_id = %s"
            query91 += " GROUP BY am.journal_id,aa.code, aj.name ORDER BY aa.code"

            if self.company_id:
                query_params91 = (self.end_date, self.company_id.id)
            else:
                query_params91 = (self.end_date,)

            self.env.cr.execute(query91, query_params91)
            accounts = self.env.cr.dictfetchall()
            op = 0
            for acc in accounts:
                first_tx_query = """
                                SELECT
                                    am.id AS move_id,
                                    am.journal_id AS journal_id,
                                    aj.name->>'en_US' AS account_name,
                                    aa.code AS account_code,
                                    am.date AS first_date,
                                    absl.amount AS balance
                                FROM account_bank_statement_line absl
                                JOIN account_move am ON am.id = absl.move_id
                                JOIN account_journal aj ON aj.id = am.journal_id
                                JOIN account_account aa ON aa.id = aj.default_account_id
                                WHERE aa.account_type = 'asset_cash'
                            """
                if self.company_id:
                    first_tx_query += " AND am.company_id = %s AND aj.id=%s"
                    first_tx_query += " GROUP BY aa.code,am.journal_id,am.id, aj.name,am.date,absl.amount ORDER BY am.date ASC"
                    self.env.cr.execute(first_tx_query, (self.company_id.id,acc['journal_id']))
                else:
                    self.env.cr.execute(first_tx_query)

                first_tx = self.env.cr.dictfetchone()
                if first_tx and first_tx.get('first_date'):
                    first_date = first_tx['first_date']
                    if self.start_date <= first_date <= self.end_date:
                        first_month = first_date.strftime('%b').upper()
                        if first_month in month_col_map:
                            col = month_col_map[first_month]
                            journal_ids = tuple(item['journal_id'] for item in accounts)
                            first_balance_query = """
                                            SELECT
                                                am.journal_id AS journal_id,
                                                aj.name->>'en_US' AS account_name,
                                                aa.code AS account_code,
                                                SUM(absl.amount) AS balance
                                            FROM account_bank_statement_line absl
                                            JOIN account_move am ON am.id = absl.move_id
                                            JOIN account_journal aj ON aj.id = am.journal_id
                                            JOIN account_account aa ON aa.id = aj.default_account_id
                                            WHERE aa.account_type = 'asset_cash' AND am.id = %s
                                            GROUP BY am.journal_id, aa.code, aj.name
                                            ORDER BY aa.code
                                        """
                            # journal_ids = [item['journal_id'] for item in accounts]
                            self.env.cr.execute(first_balance_query, (first_tx['move_id'],))
                            first_month_lines = self.env.cr.dictfetchall()
                            opening_balance_1 = first_tx.get('balance')
                            if first_date:
                                first_month = first_date.strftime('%b').upper()

                                for idx, month in enumerate(month_list):
                                    if first_month in month:
                                        opening_balances[month] += opening_balance_1
                                # sheet.write(2, col, new_value, value_format)
                            for line in first_month_lines:
                                acc_code = line['account_code']
                                balance = line['balance'] or 0.0
                                if acc_code in account_row_map:
                                    row_idx = account_row_map[acc_code]
                                    sheet.write(row_idx, col, balance, value_format)
            for month,balances in opening_balances.items():
                col = month_col_map[month]
                sheet.write(2, col, balances, value_format)
                # print(opening,"oooooooooooooooooooooooooooooooooooooooo")
            # first_tx_query = """
            #     SELECT
            #         am.id AS move_id,
            #         am.journal_id AS journal_id,
            #         aj.name->>'en_US' AS account_name,
            #         aa.code AS account_code,
            #         am.date AS first_date,
            #         absl.amount AS balance
            #     FROM account_bank_statement_line absl
            #     JOIN account_move am ON am.id = absl.move_id
            #     JOIN account_journal aj ON aj.id = am.journal_id
            #     JOIN account_account aa ON aa.id = aj.default_account_id
            #     WHERE aa.account_type = 'asset_cash'
            # """
            # if self.company_id:
            #     first_tx_query += " AND am.company_id = %s"
            #     first_tx_query += " GROUP BY aa.code,am.journal_id,am.id, aj.name,am.date,absl.amount ORDER BY am.date ASC LIMIT 1"
            #     self.env.cr.execute(first_tx_query, (self.company_id.id,))
            # else:
            #     self.env.cr.execute(first_tx_query)
            #
            # first_tx = self.env.cr.dictfetchone()
            # if first_tx and first_tx.get('first_date'):
            #     first_date = first_tx['first_date']
            #     if self.start_date <= first_date <= self.end_date:
            #         first_month = first_date.strftime('%b').upper()
            #         if first_month in month_col_map:
            #             col = month_col_map[first_month]
            #
            #             first_balance_query = """
            #                 SELECT
            #                     am.journal_id AS journal_id,
            #                     aj.name->>'en_US' AS account_name,
            #                     aa.code AS account_code,
            #                     SUM(absl.amount) AS balance
            #                 FROM account_bank_statement_line absl
            #                 JOIN account_move am ON am.id = absl.move_id
            #                 JOIN account_journal aj ON aj.id = am.journal_id
            #                 JOIN account_account aa ON aa.id = aj.default_account_id
            #                 WHERE aa.account_type = 'asset_cash' AND am.id = %s
            #                 GROUP BY am.journal_id, aa.code, aj.name
            #                 ORDER BY aa.code
            #             """
            #             self.env.cr.execute(first_balance_query, (first_tx['move_id'],))
            #             first_month_lines = self.env.cr.dictfetchall()
            #             opening_balance_1 = first_tx.get('balance')
            #             if first_date:
            #                 first_month = first_date.strftime('%b').upper()
            #                 for idx, month in enumerate(month_list):
            #                     if first_month in month:
            #                         opening_balances[month] = opening_balance_1 # Adjust offset to your month column
            #                         sheet.write(2, 2, opening_balance_1, value_format)
            #             for line in first_month_lines:
            #                 acc_code = line['account_code']
            #                 balance = line['balance'] or 0.0
            #                 if acc_code in account_row_map:
            #                     row_idx = account_row_map[acc_code]
            #                     sheet.write(row_idx, col, balance, value_format)
            row_num += 1
        end_balance1 = """SELECT
                    am.journal_id AS journal_id,
                    aj.name->>'en_US' AS account_name,
                    aa.code AS account_code,
                    SUM(absl.amount) AS balance
                FROM account_bank_statement_line absl
                JOIN account_move am ON am.id = absl.move_id
                JOIN account_journal aj ON aj.id = am.journal_id
                JOIN account_account aa ON aa.id = aj.default_account_id
                WHERE am.date <= %s
                AND aa.account_type = 'asset_cash'
            """
        if self.company_id:
            end_balance1 += " AND am.company_id = %s"
            end_balance1 += " GROUP BY am.journal_id,aa.code, aj.name ORDER BY aa.code"
            end_balance_params = (self.end_date, self.company_id.id)
            end_balance_params1 = (self.end_date, self.company_id.id)
        else:
            end_balance_params = (self.end_date,)
            end_balance_params1 = (self.end_date,)
        end_balance = self.env.cr.dictfetchall()
        self.env.cr.execute(end_balance1, end_balance_params1)
        end_balance1 = self.env.cr.dictfetchall()

        if end_balance1 and (end_balance1[0].get('balance') != None):
            end_balance_1 = end_balance1[0].get('balance')
        credit_accounts = [record for record in records_credit if record['total_credit'] > 0]
        debit_accounts = [record for record in records_debit if record['total_debit'] > 0]
        # credit_card_accounts = [record for record in record_credit_card if record['total_debit'] > 0]
        row_num = row_num
        for account in credit_accounts:
            if not self.groupby_month:
                sheet.write(row_num, 0, account['account_name'], value_format1)
                sheet.write(row_num, 1, account['account_code'], value_format1)
                sheet.write(row_num, 2, account['total_credit'], value_format1)
                row_num +=1
                partner_totals = {}
                for detail in account['entries']:
                    partner_id = detail.get('partner_id')
                    credit = detail.get('credit') or 0
                    if partner_id:
                        partner_totals[partner_id] = partner_totals.get(partner_id, 0) + credit
                if account['account_name'] != "Internal Bank Transfer":
                    if len(partner_totals) > 1:
                        # row_num += 1
                        for partner_id, total_credit in partner_totals.items():
                            sheet.write(row_num, 0, partner_id, name_format)
                            sheet.write(row_num, 1, account['account_code'], value_format)
                            sheet.write(row_num, 2, total_credit, value_format)
                            row_num += 1
                            sheet.write(row_num, 0, '', header_format_num)
                            sheet.write(row_num, 1, '', header_format_num)
                            sheet.write(row_num, 2, '', header_format_num)
                else:
                    merged_totals = {}
                    for partner_id, total_credit in partner_totals.items():
                        merged_totals[partner_id] = merged_totals.get(partner_id, 0) + total_credit
                    for partner_id, total_credit in merged_totals.items():
                        sheet.write(row_num, 0, partner_id, name_format)
                        sheet.write(row_num, 1, account['account_code'], value_format)
                        sheet.write(row_num, 2, total_credit, value_format)
                        row_num += 1
                    sheet.write(row_num, 0, '', header_format_num)
                    sheet.write(row_num, 1, '', header_format_num)
                    sheet.write(row_num, 2, '', header_format_num)
            else:
                # Monthly totals for header row
                monthly_totals = defaultdict(float)
                for detail in account['entries']:
                    if detail.get('credit'):
                        detail_month = (
                            detail.get('statement_date').strftime('%b').upper()
                            if detail.get('statement_date')
                            else detail.get('date').strftime('%b').upper()
                        )
                        monthly_totals[detail_month] += detail.get('credit')

                # Write account header
                sheet.write(row_num, 0, account['account_name'], value_format1)
                sheet.write(row_num, 1, account['account_code'], value_format1)

                base_month_col = 2
                for month in month_list:
                    month_index = month_list.index(month)
                    col_number = base_month_col + month_index
                    amount = monthly_totals.get(month, 0.0)
                    sheet.write(row_num, col_number, amount if amount != 0 else '', value_format1)

                sheet.write(row_num, 2, '', value_format1)
                sheet.write(row_num, 3, '', value_format1)
                for month, amount in monthly_totals.items():
                    if month in month_list:
                        month_index = month_list.index(month)
                        col_number = base_month_col + month_index
                        sheet.write(row_num, col_number, amount, value_format1)
                row_num += 1
                sheet.write(row_num, 0, '', header_format_num)
                sheet.write(row_num, 1, '', header_format_num)
                sheet.write(row_num, 2, '', header_format_num)
                # row_num +=1
                partner_month_totals = defaultdict(lambda: defaultdict(float))
                for detail in account['entries']:
                    if detail.get('credit'):
                        detail_month = (
                            detail.get('statement_date').strftime('%b').upper()
                            if detail.get('statement_date')
                            else detail.get('date').strftime('%b').upper()
                        )
                        partner_id = detail.get('partner_id')
                        partner_month_totals[partner_id][detail_month] += detail.get('credit')
                if account['account_name'] != "Internal Bank Transfer":
                        if len(partner_month_totals) > 1:
                            # row_num += 1
                            for partner_id, month_data in sorted(partner_month_totals.items()):
                                sheet.write(row_num, 0, partner_id, name_format)
                                sheet.write(row_num, 1, account['account_code'], value_format)

                                for month in month_list:
                                    col_number = base_month_col + month_list.index(month)
                                    amount = month_data.get(month, 0.0)
                                    sheet.write(row_num, col_number, amount if amount != 0 else '', value_format)
                                row_num += 1
                else:
                            combined_totals = defaultdict(lambda: defaultdict(float))
                            for partner_id, month_data in partner_month_totals.items():
                                for month, value in month_data.items():
                                    combined_totals[partner_id][month] += value

                            for partner_id, month_data in sorted(combined_totals.items()):
                                sheet.write(row_num, 0, partner_id, name_format)
                                sheet.write(row_num, 1, account['account_code'], value_format)

                                for month in month_list:
                                    col_number = base_month_col + month_list.index(month)
                                    amount = month_data.get(month, 0.0)
                                    sheet.write(row_num, col_number, amount if amount != 0 else '', value_format)

                                row_num += 1
                    # row_num += 1
        total_c = 0.0
        for rec in credit_accounts:
            total_c = total_c + rec['total_credit']
        if not self.groupby_month:
            sheet.write(row_num, 0, 'Receipts', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            sheet.write(row_num, 2, total_c, header_format_num)
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            sheet.write(row_num, 2, '', header_format_num)

        else:
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            sheet.write(row_num, 2, '', header_format_num)
            monthly_receipts = defaultdict(float)
            for rec in credit_accounts:
                for detail in rec['entries']:
                    if detail.get('credit'):
                        detail_month = detail.get('statement_date').strftime('%b').upper() if detail.get(
                            'statement_date') else detail.get('date').strftime('%b').upper()
                        if detail_month in month_list:
                            monthly_receipts[detail_month] += detail.get('credit')
            sheet.write(row_num, 0, 'Receipts', header_format_num)
            base_month_col = 2
            for month in month_list:
                month_index = month_list.index(month)
                col_number = base_month_col + month_index
                amount = monthly_receipts.get(month, 0.0)
                sheet.write(row_num, col_number, amount if amount != 0 else '', header_format_num)
            row_num += 1
        if not self.groupby_month:
            sheet.write(row_num, 0, 'Total Cash Inflow', header_format_num)
            sheet.write(row_num, 1,'',header_format_num)
            sheet.write(row_num, 2, total_c+opening_balance_1, header_format_num)
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            sheet.write(row_num, 2, '', header_format_num)
            row_num += 1
        else:
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            sheet.write(row_num, 2, '', header_format_num)

            monthly_receipts = defaultdict(float)
            for rec in credit_accounts:
                for detail in rec['entries']:
                    if detail.get('credit'):
                        detail_month = (
                            detail.get('statement_date').strftime('%b').upper()
                            if detail.get('statement_date')
                            else detail.get('date').strftime('%b').upper()
                        )
                        if detail_month in month_list:
                            monthly_receipts[detail_month] += detail.get('credit')

            sheet.write(row_num, 0, 'Total Cash Inflow', header_format_num)

            base_month_col = 2
            for month in month_list:
                month_index = month_list.index(month)
                col_number = base_month_col + month_index

                opening = opening_balances.get(month, 0.0)
                receipts = monthly_receipts.get(month, 0.0)
                amount = opening + receipts

                sheet.write(row_num, col_number, amount if amount != 0 else '', header_format_num)

            row_num += 1
        capex_accounts = [account for account in debit_accounts if account['expense_type'] == 'capex']
        opex_accounts = [account for account in debit_accounts if account['expense_type'] == 'opex']

        if capex_accounts:
            sheet.write(row_num, 0, 'CAPEX:', header_format1)
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            base_month_col = 2
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1
            for account in capex_accounts:
                if not self.groupby_month:
                    sheet.write(row_num, 0, account['account_name'], value_format1)
                    sheet.write(row_num, 1, account['account_code'], value_format1)
                    sheet.write(row_num, 2, account['total_debit'], value_format1) if account[
                                                                                          'total_debit'] != 0 else sheet.write(
                        row_num, 2, '', value_format)
                    # row_num += 1
                    # sheet.write(row_num, 0, '', header_format_num)
                    # sheet.write(row_num, 1, '', header_format_num)
                    # sheet.write(row_num, 2, '', header_format_num)
                    row_num += 1
                    partner_totals = {}
                    for detail in account['entries']:
                        partner_id = detail.get('partner_id')
                        debit = detail.get('debit') or 0
                        if partner_id:
                            partner_totals[partner_id] = partner_totals.get(partner_id, 0) + debit
                    if account['account_name'] != "Internal Bank Transfer":
                        if len(partner_totals) > 1:
                            # row_num += 1
                            for partner_id, total_debit in partner_totals.items():
                                sheet.write(row_num, 0, partner_id, name_format)
                                sheet.write(row_num, 1, account['account_code'], value_format)
                                sheet.write(row_num, 2, total_debit, value_format)
                                row_num += 1
                                sheet.write(row_num, 0, '', header_format_num)
                                sheet.write(row_num, 1, '', header_format_num)
                                sheet.write(row_num, 2, '', header_format_num)
                    else:
                        merged_totals = {}
                        for partner_id, total_debit in partner_totals.items():
                            merged_totals[partner_id] = merged_totals.get(partner_id, 0) + total_debit
                        for partner_id, total_debit in merged_totals.items():
                            sheet.write(row_num, 0, partner_id, name_format)
                            sheet.write(row_num, 1, account['account_code'], value_format)
                            sheet.write(row_num, 2, total_debit, value_format)
                            row_num += 1
                        sheet.write(row_num, 0, '', header_format_num)
                        sheet.write(row_num, 1, '', header_format_num)
                        sheet.write(row_num, 2, '', header_format_num)
                else:
                    monthly_totals = defaultdict(float)
                    for detail in account['entries']:
                        if detail.get('debit'):
                            detail_month = (
                                detail.get('statement_date').strftime('%b').upper()
                                if detail.get('statement_date')
                                else detail.get('date').strftime('%b').upper()
                            )
                            monthly_totals[detail_month] += detail.get('debit')

                    # Write account header
                    sheet.write(row_num, 0, account['account_name'], value_format1)
                    sheet.write(row_num, 1, account['account_code'], value_format1)

                    base_month_col = 2
                    for month in month_list:
                        month_index = month_list.index(month)
                        col_number = base_month_col + month_index
                        amount = monthly_totals.get(month, 0.0)
                        sheet.write(row_num, col_number, amount if amount != 0 else '', value_format1)

                    sheet.write(row_num, 2, '', value_format1)
                    sheet.write(row_num, 3, '', value_format1)
                    # row_num += 1
                    # sheet.write(row_num, 0, '', header_format_num)
                    # sheet.write(row_num, 1, '', header_format_num)
                    # sheet.write(row_num, 2, '', header_format_num)
                    # row_num += 1
                    partner_month_totals = defaultdict(lambda: defaultdict(float))
                    for detail in account['entries']:
                        if detail.get('debit'):
                            detail_month = (
                                detail.get('statement_date').strftime('%b').upper()
                                if detail.get('statement_date')
                                else detail.get('date').strftime('%b').upper()
                            )
                            partner_id = detail.get('partner_id')
                            partner_month_totals[partner_id][detail_month] += detail.get('debit')
                    if len(partner_month_totals) > 1:
                        # row_num += 1
                        for partner_id, month_data in sorted(partner_month_totals.items()):
                            sheet.write(row_num, 0, partner_id, name_format)
                            sheet.write(row_num, 1, account['account_code'], value_format)

                            for month, amount in month_data.items():
                                if month in month_list:
                                    month_index = month_list.index(month)
                                    col_number = base_month_col + month_index
                                    sheet.write(row_num, col_number, amount, value_format)
                            row_num += 1
                        # row_num += 1
        if not capex_accounts:
            sheet.write(row_num, 0, 'CAPEX:', header_format1)
            base_month_col = 2
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            base_month_col = 2
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1
        grand_totals = defaultdict(float)
        if opex_accounts:
            sheet.write(row_num, 0, 'OPEX:', header_format1)
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            base_month_col = 2
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1
            for account in opex_accounts:
                if not self.groupby_month:
                    sheet.write(row_num, 0, account['account_name'], value_format1)
                    sheet.write(row_num, 1, account['account_code'], value_format1)
                    sheet.write(row_num, 2, account['total_debit'], value_format1) if account[
                                            'total_debit'] != 0 else sheet.write(row_num, 2, '', value_format)
                    # row_num +=1
                    # sheet.write(row_num, 0, '', header_format_num)
                    # sheet.write(row_num, 1, '', header_format_num)
                    # sheet.write(row_num, 2, '', header_format_num)
                    row_num +=1
                    partner_totals = {}
                    for detail in account['entries']:
                        partner_id = detail.get('partner_id')
                        debit = detail.get('debit') or 0
                        if partner_id:
                            partner_totals[partner_id] = partner_totals.get(partner_id, 0) + debit
                    if account['account_name'] != "Internal Bank Transfer":
                        if len(partner_totals) > 1:
                            # row_num += 1
                            for partner_id, total_debit in partner_totals.items():
                                sheet.write(row_num, 0, partner_id, name_format)
                                sheet.write(row_num, 1, account['account_code'], value_format)
                                sheet.write(row_num, 2, total_debit, value_format)
                                row_num += 1
                                sheet.write(row_num, 0, '', header_format_num)
                                sheet.write(row_num, 1, '', header_format_num)
                                sheet.write(row_num, 2, '', header_format_num)
                    else:
                        merged_totals = {}
                        for partner_id, total_debit in partner_totals.items():
                            merged_totals[partner_id] = merged_totals.get(partner_id, 0) + total_debit
                        for partner_id, total_debit in merged_totals.items():
                            sheet.write(row_num, 0, partner_id, name_format)
                            sheet.write(row_num, 1, account['account_code'], value_format)
                            sheet.write(row_num, 2, total_debit, value_format)
                            row_num += 1
                        sheet.write(row_num, 0, '', header_format_num)
                        sheet.write(row_num, 1, '', header_format_num)
                        sheet.write(row_num, 2, '', header_format_num)
                else:
                    monthly_totals = defaultdict(float)
                    for detail in account['entries']:
                        if detail.get('debit'):
                            detail_month = (
                                detail.get('statement_date').strftime('%b').upper()
                                if detail.get('statement_date')
                                else detail.get('date').strftime('%b').upper()
                            )
                            monthly_totals[detail_month] += detail.get('debit')

                    # 🔹 Aggregate debit by partner and month (to avoid duplicates)
                    partner_month_totals = defaultdict(lambda: defaultdict(float))
                    for detail in account['entries']:
                        if detail.get('debit'):
                            partner_id = detail.get('partner_id')
                            detail_month = (
                                detail.get('statement_date').strftime('%b').upper()
                                if detail.get('statement_date')
                                else detail.get('date').strftime('%b').upper()
                            )
                            partner_month_totals[partner_id][detail_month] += detail.get('debit')

                    partners = list(partner_month_totals.keys())

                    if account['account_name'] not in ("Internal Bank Transfer","Credit Card"):
                        sheet.write(row_num, 0, account['account_name'], value_format1)
                        sheet.write(row_num, 1, account['account_code'], value_format1)

                        base_month_col = 2
                        for month in month_list:
                            col_number = base_month_col + month_list.index(month)
                            amount = monthly_totals.get(month, 0.0)
                            sheet.write(row_num, col_number, amount if amount != 0 else '', value_format1)

                        # ✅ Only write subentries if there is more than 1 unique partner
                        if len(partners) > 1:
                            for partner_id, month_data in sorted(partner_month_totals.items()):
                                row_num += 1
                                sheet.write(row_num, 0, partner_id, value_format)
                                sheet.write(row_num, 1, account['account_code'], value_format)

                                for month in month_list:
                                    col_number = base_month_col + month_list.index(month)
                                    amount = month_data.get(month, 0.0)
                                    sheet.write(row_num, col_number, amount if amount != 0 else '', value_format)
                        row_num += 1
                        sheet.write(row_num, 0, '', header_format_num)
                        sheet.write(row_num, 1, '', header_format_num)
                        sheet.write(row_num, 2, '', header_format_num)
                    partner_month_totals = defaultdict(lambda: defaultdict(float))
                    for detail in account['entries']:
                        if detail.get('debit'):
                            detail_month = (
                                detail.get('statement_date').strftime('%b').upper()
                                if detail.get('statement_date')
                                else detail.get('date').strftime('%b').upper()
                            )
                            partner_id = detail.get('partner_id')
                            partner_month_totals[partner_id][detail_month] += detail.get('debit')
                    if account['account_name'] == "Internal Bank Transfer":
                        if not locals().get('ibt_written', False):
                            sheet.write(row_num, 0, account['account_name'], value_format1)
                            sheet.write(row_num, 1, account['account_code'], value_format1)
                            for month in month_list:
                                col_number = base_month_col + month_list.index(month)
                                amount = monthly_totals.get(month, 0.0)
                                sheet.write(row_num, col_number, amount if amount != 0 else '', value_format1)
                            row_num += 1
                            ibt_written = True  # mark as written
                        for partner_id, month_data in sorted(partner_month_totals.items()):
                                sheet.write(row_num, 0, partner_id, name_format)
                                sheet.write(row_num, 1, account['account_code'], value_format)
                                for month in month_list:
                                    col_number = base_month_col + month_list.index(month)
                                    amount = month_data.get(month, 0.0)
                                    sheet.write(row_num, col_number, amount if amount != 0 else '', value_format)
                                row_num += 1
                    if account['account_name'] == "Credit Card":
                        if not locals().get('cc_written', False):
                            sheet.write(row_num, 0, account['account_name'], value_format1)
                            sheet.write(row_num, 1, account['account_code'], value_format1)
                            for month in month_list:
                                col_number = base_month_col + month_list.index(month)
                                amount = monthly_totals.get(month, 0.0)
                                sheet.write(row_num, col_number, amount if amount != 0 else '', value_format1)
                            row_num += 1
                            cc_written = True  # mark as written
                        for partner_id, month_data in sorted(partner_month_totals.items()):
                                sheet.write(row_num, 0, partner_id, name_format)
                                sheet.write(row_num, 1, account['account_code'], value_format)
                                for month in month_list:
                                    col_number = base_month_col + month_list.index(month)
                                    amount = month_data.get(month, 0.0)
                                    sheet.write(row_num, col_number, amount if amount != 0 else '', value_format)
                                row_num += 1
        if not opex_accounts:
            sheet.write(row_num, 0, 'OPEX:', header_format1)
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            base_month_col = 2
            for month in month_list:
                col_number = base_month_col + month_list.index(month)
                sheet.write(row_num, col_number, '', header_format_num)
            row_num += 1

        total_d = 0.0
        total_credit_entry = 0.0
        for rec in debit_accounts:
            total_d = total_d + rec['total_debit']
        if not self.groupby_month:
            sheet.write(row_num, 0, 'Total Cash Outflow', header_format_num)
            sheet.write(row_num, 2, total_d, header_format_num)
            row_num += 1
        else:
            row_num += 1
            sheet.write(row_num, 0, '', header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            sheet.write(row_num, 2, '', header_format_num)

            monthly_payments = defaultdict(float)
            for rec in debit_accounts:
                for detail in rec['entries']:
                    if detail.get('debit'):
                        detail_month = (
                            detail.get('statement_date').strftime('%b').upper()
                            if detail.get('statement_date')
                            else detail.get('date').strftime('%b').upper()
                        )
                        if detail_month in month_list:
                            monthly_payments[detail_month] += detail.get('debit')

            sheet.write(row_num, 0, 'Total Cash Outflow', header_format_num)

            base_month_col = 2
            for month in month_list:
                month_index = month_list.index(month)
                col_number = base_month_col + month_index
                receipts = monthly_payments.get(month, 0.0)
                amount = receipts
                sheet.write(row_num, col_number, amount if amount != 0 else '', header_format_num)
            row_num += 1

        if not self.groupby_month:
            sheet.write(row_num, 0, 'Balance as per book as on %s' % (formatted_en_date), header_format_num)
            sheet.write(row_num, 1, '', header_format_num)
            sheet.write(row_num, 2, total_c + opening_balance_1 - (total_d), header_format_num)
            row_num += 1
            for line in end_balance1:
                sheet.write(row_num, 0, line['account_name'], value_format)
                sheet.write(row_num, 1, line['account_code'], value_format)
                sheet.write(row_num, 2, line['balance'] or 0.0, value_format)
                row_num += 1
        else:
            end_balance_query = """
                SELECT
                    am.journal_id AS journal_id,
                    aj.name->>'en_US' AS account_name,
                    aa.code AS account_code,
                    SUM(absl.amount) AS balance
                FROM account_bank_statement_line absl
                JOIN account_move am ON am.id = absl.move_id
                JOIN account_journal aj ON aj.id = am.journal_id
                JOIN account_account aa ON aa.id = aj.default_account_id
                WHERE am.date <= %s
                AND aa.account_type = 'asset_cash'
            """
            if self.company_id:
                end_balance_query += " AND am.company_id = %s"

            end_balance_query += " GROUP BY am.journal_id,aj.name,aa.code"

            if self.company_id:
                query_params = (self.end_date, self.company_id.id)
            else:
                query_params = (self.end_date,)

            self.env.cr.execute(end_balance_query, query_params)
            accounts = self.env.cr.dictfetchall()
            row_num += 1
            base_col = 2
            sheet.write(row_num, 0, "Total Inflow (-) Outflow", header_format_num)
            sheet.write(row_num, 1, "", header_format_num)
            for idx, month in enumerate(month_list):
                col_number = base_col + idx
                month_key = month.upper()
                receipts = monthly_receipts.get(month_key, 0.0)
                payments = monthly_payments.get(month_key, 0.0)
                opb = opening_balances.get(month_key,0.0)
                diff = (opb+receipts) - payments
                sheet.write(row_num, col_number, diff, header_format_num)
            row_num += 1
            monthly_end_total_balances=[]
            for acc in accounts:
                monthly_end_balances = []
                total_balances = {}
                s_no=0
                for idx, month in enumerate(month_list):

                    month_start = self.start_date.replace(day=1) + relativedelta(months=idx)
                    month_end = (month_start + relativedelta(months=1)) - relativedelta(days=1)
                    if self.company_id:
                        self.env.cr.execute(end_balance_query, (month_end, self.company_id.id))
                    else:
                        self.env.cr.execute(end_balance_query, (month_end,))
                    res = self.env.cr.dictfetchall()
                    balance = 0.0
                    for r in res:
                        if r['account_code'] == acc['account_code']:
                            balance = r['balance']
                            break
                    monthly_end_balances.append(balance)
                if any(b != 0.0 for b in monthly_end_balances):
                    sheet.write(row_num, 0, acc['account_name'], value_format)
                    sheet.write(row_num, 1, acc['account_code'], value_format)

                    for idx, balance in enumerate(monthly_end_balances):
                        s_no += 1
                        col_number = base_col + idx
                        total = {'sno': s_no, 'balance': balance}
                        monthly_end_total_balances.append(total)
                        sheet.write(row_num, col_number, balance or 0.0, value_format)

                    row_num += 1
            sums = {}
            for entry in monthly_end_total_balances:
                sno = entry['sno']
                balance = entry['balance']
                sums[sno] = sums.get(sno, 0) + balance

            final_balance = [round(balance,2) for sno, balance in sums.items()]
            sheet.write(row_num, 0, "Balance as per book", header_format_num)
            sheet.write(row_num, 1, "", header_format_num)
            for idx, balance in enumerate(final_balance):
                col_number = base_col + idx
                sheet.write(row_num, col_number, balance or 0.0, header_format_num)

        workbook.close()


        buffer.seek(0)
        return buffer.read()

    def get_cash_bank_utilization_debit(self, date_from, date_to,company_id):

        result = defaultdict(lambda: {
            'account_name': '',
            'account_code': '',
            'expense_type': '',
            'total_debit': 0.0,
            'total_credit': 0.0,
            'entries': []
        })
        #internal transfer entry
        pay_rec = self.env['account.payment'].sudo().search([
            ('state', '=', 'posted'),
            ('is_internal_transfer','=', True),
            ('company_id', '=', company_id.id),
            ('move_id.state', '=', 'posted')])
        groups_by_match = defaultdict(set)
        seen_matches = set()

        for rec1 in pay_rec:
            for rec in rec1.move_id.line_ids:
                reconciled_lines = rec._all_reconciled_lines().filtered(
                    lambda l: l.matched_debit_ids or l.matched_credit_ids
                )
                for line in reconciled_lines:
                    if line.matching_number and line.matching_number not in seen_matches:
                        # store all lines of this matching_number once
                        groups_by_match[line.matching_number].update(
                            reconciled_lines.ids
                        )
                        seen_matches.add(line.matching_number)
        groups_by_match = {k: list(v) for k, v in groups_by_match.items()}

        for match_no, ids in groups_by_match.items():
            groups_with_statement = []
            move_lines = self.env['account.move.line'].browse(ids)
            if any(l.statement_line_id and date_from <= l.date <= date_to for l in move_lines):
                groups_with_statement.append(ids)

                for g in groups_with_statement:
                    r1 = self.env['account.move.line'].browse(g)
                    if not all(line.account_id.code == '100801' for line in r1):
                        # continue
                        for r in r1:
                            if not r.statement_line_id and not r.move_id.journal_id.is_credit_card_bank:
                                r = r.move_id.payment_id.paired_internal_transfer_payment_id.move_id.line_ids.filtered(
                                    lambda l: l.debit > 0)
                                if r.move_id.payment_id.payment_type != 'outbound':
                                    key = ('Internal Bank Transfer', r.move_id.expense_type)
                                    result[key]['account_name'] = 'Internal Bank Transfer'
                                    result[key]['account_code'] = r.account_id.code
                                    result[key]['expense_type'] = r.move_id.expense_type
                                    result[key]['total_debit'] += r.debit
                                    result[key]['entries'].append({
                                        'move_name': r.move_id.name,
                                        'mov_id': r.id,
                                        'partner_id': (
                                            r.move_id.journal_id.name
                                            if r.move_id.payment_id and r.move_id.payment_id.is_internal_transfer
                                            else r.partner_id.name if r.partner_id
                                            else r.account_id.name
                                        ),
                                        'debit': r.debit,
                                        'date': r.date,
                                    })
                                else:
                                    key = ('Credit Card', r.move_id.expense_type)
                                    result[key]['account_name'] = 'Credit Card'
                                    result[key]['account_code'] = r.account_id.code
                                    result[key]['expense_type'] = r.move_id.expense_type
                                    result[key]['total_debit'] += r.debit
                                    result[key]['entries'].append({
                                        'move_name': r.move_id.name,
                                        'mov_id': r.id,
                                        'partner_id': (
                                            r.move_id.journal_id.name
                                            if r.move_id.payment_id and r.move_id.payment_id.is_internal_transfer
                                            else r.partner_id.name if r.partner_id
                                            else r.account_id.name
                                        ),
                                        'debit': r.debit,
                                        'date': r.date,
                                    })
                                # print(result,'kkkkkkkkkkkkkkkkkkkkkkkkkkkkkzzzzzzzzzzzzzzz')
        moves = self.env['account.move.line'].sudo().search([
            ('move_id.state', '=', 'posted'),
            ('move_id.journal_id.type', 'in', ('bank', 'cash')),
            ('move_id.company_id','=',company_id.id),
            ('move_id.move_type', '=', 'entry'),
        ])
        grouped = defaultdict(list)
        duplicates = defaultdict(list)
        stat_line = set()
        l = set()
        l_grp =  defaultdict(list)
        state_grp = defaultdict(list)
        outstanding =[]
        for line in moves:
            if line.matching_number:
                grouped[line.matching_number].append(line)
            elif not line.matching_number and line.statement_line_id:
                if line.move_id.journal_id.type in ('bank','cash') and line.date >= date_from and line.date <= date_to:
                    stat_line.add((line.move_id.name, line.id))
                    state_grp[line.move_name].append(line)
        for name, lines in list(state_grp.items()):
            for line in lines:
                move_line = self.env['account.move.line'].sudo().search([('move_id','=',line.move_id.id),('debit','=',line.credit)])
                if move_line:
                    for rec in move_line:
                        if not rec.matching_number:
                            outstanding.append(rec)
                else:
                    move_line = self.env['account.move.line'].sudo().search(
                        [('move_id', '=', line.move_id.id),('matching_number','=',False),('debit','!=',0)])
                    for rec in move_line:
                        outstanding.append(rec)


        for match_no, group_lines in grouped.items():
            statement_line = next((l for l in group_lines if l.statement_line_id), None)

            if not statement_line:
                continue
            if statement_line.journal_id.type in ('bank','cash'):
                stmt_date = statement_line.statement_line_id.date
                if not (date_from <= stmt_date <= date_to):
                    continue
                for line in group_lines:

                    if not line.statement_line_id:
                        move_line = line.move_id
                        if move_line.journal_id.type in ('bank','cash'):
                            for rec in move_line.line_ids:
                                if rec.debit > 0 and rec.account_id.code not in ('100202','100203','100204'):
                                    if not rec.move_id.payment_id.is_credit_payment and not rec.move_id.payment_id.is_internal_transfer and not rec.move_id.is_payment_approval and not rec.move_id.journal_id.is_credit_card_bank:
                                        l.add((rec.move_id.name, rec.id))
                                        key = (rec.account_id.id, line.move_id.expense_type)

                                        result[key]['account_name'] = rec.account_id.name
                                        result[key]['account_code'] = rec.account_id.code
                                        result[key]['expense_type'] = rec.move_id.expense_type
                                        result[key]['total_debit'] += rec.debit
                                        result[key]['entries'].append({
                                            'move_name':rec.move_id.name,
                                            'mov_id':rec.id,
                                            'partner_id': rec.move_id.journal_id.name if rec.move_id.payment_id and rec.move_id.payment_id.is_internal_transfer
                                                          else rec.partner_id.name if rec.partner_id
                                                          else rec.account_id.name,
                                            'debit': rec.debit,
                                            'date': rec.date,
                                            'statement_date': stmt_date
                                        })
                                elif rec.debit > 0 and rec.account_id.code in ('100203') and not rec.move_id.payment_id:
                                    skip_entry = False
                                    if rec.matching_number:
                                        matching_lines = self.env['account.move.line'].sudo().search([
                                            ('matching_number', '=', rec.matching_number)
                                        ])
                                        for m in matching_lines.move_id:
                                            if not m.statement_line_id:
                                                for lines in m.line_ids:
                                                    if lines.credit > 0 and lines.account_id.account_type != 'asset_cash':
                                                        skip_entry = True
                                        if skip_entry:
                                            continue
                                        l.add((rec.move_id.name, rec.id))
                                        key = (rec.account_id.id, line.move_id.expense_type)
                                        result[key]['account_name'] = rec.account_id.name
                                        result[key]['account_code'] = rec.account_id.code
                                        result[key]['expense_type'] = rec.move_id.expense_type
                                        result[key]['total_debit'] += rec.debit
                                        result[key]['entries'].append({
                                            'move_name': rec.move_id.name,
                                            'mov_id': rec.id,
                                            'partner_id': (
                                                rec.move_id.journal_id.name
                                                if rec.move_id.payment_id and rec.move_id.payment_id.is_internal_transfer
                                                else rec.partner_id.name if rec.partner_id
                                                else rec.account_id.name
                                            ),
                                            'debit': rec.debit,
                                            'date': rec.date,
                                            'statement_date': stmt_date
                                        })
        #outstanding entries
        # for rec in outstanding:
        #     if rec.debit > 0 and rec.account_id.account_type != 'asset_cash' and rec.move_id.has_reconciled_entries:
        #          print(rec.move_id.name,'zzzzzzzzzzzzzzzz')
        #          key = (rec.account_id.id, rec.move_id.expense_type)
        #          result[key]['account_name'] = rec.account_id.name
        #          result[key]['account_code'] = rec.account_id.code
        #          result[key]['expense_type'] = rec.move_id.expense_type
        #          result[key]['total_debit'] += rec.debit
        #          result[key]['entries'].append({
        #                             'move_name':rec.move_id.name,
        #                             'mov_id':rec.id,
        #                             'partner_id':  rec.move_id.journal_id.name if rec.move_id.payment_id and rec.move_id.payment_id.is_internal_transfer
        #                                               else rec.partner_id.name if rec.partner_id
        #                                               else rec.account_id.name,
        #                             'debit': rec.debit,
        #                             'date': rec.date,
        #                         })

        #Misc entries

        # mis = self.env['account.move.line'].sudo().search([
        #     ('move_id.state', '=', 'posted'),
        #     ('move_id.move_type','=','entry'),
        #     ('move_id.journal_id.type', '=','general'),
        #     ('move_id.company_id','=',company_id.id),
        # ])
        # grouped = defaultdict(list)
        # for line in mis:
        #     if line.matching_number:
        #         same_group = self.env['account.move.line'].sudo().search([
        #             ('matching_number', '=', line.matching_number)
        #         ])
        #         grouped[line.matching_number].extend(same_group)
        # filtered_groups = {
        #     match_no: lines
        #     for match_no, lines in grouped.items()
        #     if any(l.statement_line_id for l in lines)
        # }
        # # stop
        # for match,recs in list(filtered_groups.items()):
        #     for rec in recs:
        #         if not rec.statement_line_id and rec.matching_number:
        #             if (date_from <= rec.date <= date_to):
        #                 move = rec.move_id
        #                 for r in move.line_ids:
        #                     if r.debit > 0:
        #                         print(r.debit,'kkkkkkkkkkkkkkkkkkkkkkkkkkkkk')
        #                         key = (r.account_id.id, r.move_id.expense_type)
        #                         result[key]['account_name'] = r.account_id.name
        #                         result[key]['account_code'] = r.account_id.code
        #                         result[key]['expense_type'] = r.move_id.expense_type
        #                         result[key]['total_debit'] += r.debit
        #                         result[key]['entries'].append({
        #                             'move_name': r.move_id.name,
        #                             'mov_id': r.id,
        #                             'partner_id': r.move_id.journal_id.name if r.move_id.payment_id and r.move_id.payment_id.is_internal_transfer
        #                             else r.partner_id.name if r.partner_id
        #                             else r.account_id.name,
        #                             'debit': r.debit,
        #                             'date': r.date,
        #                         })

        #Credit Card Expense
        # credit_card_expense = self.env['account.move.line'].sudo().search([
        #     ('move_id.state', '=', 'posted'),
        #     ('move_id.journal_id.type', 'in', ('bank', 'cash')),
        #     ('move_id.company_id', '=', company_id.id),
        #     ('move_id.is_payment_approval', '=', True),
        # ])
        # for rec in credit_card_expense:
        #     if rec.matching_number:
        #         move_line = self.env['account.move.line'].sudo().search(
        #             [('matching_number', '=', rec.matching_number), ('id', '!=', rec.id)])
        #         for move_line1 in move_line:
        #             if (date_from <= move_line1.date <= date_to) and move_line1.statement_line_id:
        #                 for r in rec.move_id.line_ids:
        #                     if r.debit > 0:
        #                         key = (r.account_id.id, r.move_id.expense_type)
        #                         result[key]['account_name'] = r.account_id.name
        #                         result[key]['account_code'] = r.account_id.code
        #                         result[key]['expense_type'] = r.move_id.expense_type
        #                         result[key]['total_debit'] += r.debit
        #                         result[key]['entries'].append({
        #                             'move_name': r.move_id.name,
        #                             'mov_id': r.id,
        #                             'partner_id': r.move_id.journal_id.name if r.move_id.payment_id and r.move_id.payment_id.is_internal_transfer
        #                             else r.partner_id.name if r.partner_id
        #                             else r.account_id.name,
        #                             'debit': r.debit,
        #                             'date': r.date,
        #                             'statement_date': move_line.statement_line_id.date
        #                         })
        #FD Entries
        # fd_entry = self.env['account.move.line'].sudo().search([
        #     ('move_id.state', '=', 'posted'),
        #     ('move_id.move_type', '=', 'entry'),
        #     ('move_id.journal_id.type', 'in', ('bank','cash')),
        #     ('move_id.company_id', '=', company_id.id)])
        # for rec in fd_entry.move_id:
        #     if (date_from <= rec.date <= date_to):
        #         if not rec.has_reconciled_entries:
        #             for r in rec.line_ids:
        #                 if not r.matching_number and r.account_id.group_id.code_prefix_start == '30602':
        #                     if r.debit > 0:
        #                         key = (r.account_id.id, r.move_id.expense_type)
        #                         result[key]['account_name'] = r.account_id.name
        #                         result[key]['account_code'] = r.account_id.code
        #                         result[key]['expense_type'] = r.move_id.expense_type
        #                         result[key]['total_debit'] += r.debit
        #                         result[key]['entries'].append({
        #                             'move_name': r.move_id.name,
        #                             'mov_id': r.id,
        #                             'partner_id': r.move_id.journal_id.name if r.move_id.payment_id and r.move_id.payment_id.is_internal_transfer
        #                             else r.partner_id.name if r.partner_id
        #                             else r.account_id.name,
        #                             'debit': r.debit,
        #                             'date': r.date,
        #                         })
        return list(result.values())

    def get_cash_bank_utilization_credit(self, date_from, date_to,company_id):
        """
        Get cash/bank utilization summary using ORM (no raw SQL).
        """
        # Get moves in given date range, posted, with bank_date filter
        moves = self.env['account.move.line'].sudo().search([
            ('move_id.state', '=', 'posted'),
            ('move_id.move_type','=','entry'),
            ('move_id.journal_id.type', 'in', ('bank', 'cash')),
            ('move_id.company_id','=',company_id.id),
        ])
        grouped = defaultdict(list)
        duplicates = defaultdict(list)
        stat_line = set()
        l = set()
        state_grp = defaultdict(list)
        outstanding = []
        for line in moves:
            if line.matching_number:
                grouped[line.matching_number].append(line)
            elif not line.matching_number and line.statement_line_id:
                # lines = self.env['account.move.line'].sudo().search([('statement_line_id','=',line.statement_line_id.id),('move_id.journal_id.default_account_id.account_type','=','asset_cash'),('date','>=',date_from),('date','<=',date_to)])
                if line.move_id.journal_id.default_account_id.account_type in 'asset_cash' and line.date >= date_from and line.date <= date_to:
                    stat_line.add((line.move_id.name,line.id))
                    state_grp[line.move_name].append(line)
        for name, lines in list(state_grp.items()):
            for line in lines:
                move_line = self.env['account.move.line'].sudo().search([('move_id','=',line.move_id.id),('credit','=',line.debit)])
                if move_line:
                    for rec in move_line:
                        if not rec.matching_number:
                            outstanding.append(rec)
                else:
                    move_line = self.env['account.move.line'].sudo().search(
                        [('move_id', '=', line.move_id.id),('matching_number','=',False),('credit','!=',0)])
                    for rec in move_line:
                        outstanding.append(rec)
        result = defaultdict(lambda: {
            'account_name': '',
            'account_code': '',
            'expense_type': '',
            'total_credit': 0.0,
            'entries': []
        })
        for match_no, group_lines in grouped.items():
            statement_line = next((l for l in group_lines if l.statement_line_id), None)
            if not statement_line:
                continue
            if statement_line.journal_id.default_account_id.account_type == 'asset_cash':
                stmt_date = statement_line.statement_line_id.date
                if not (date_from <= stmt_date <= date_to):
                    continue
                for line in group_lines:
                    if not line.statement_line_id:
                        move_line = line.move_id
                        if move_line.journal_id.type in ('bank','cash'):
                            for rec in move_line.line_ids:
                                if rec.credit > 0 and rec.account_id.code not in ('100203','100204','100801'):
                                    if not rec.move_id.payment_id.is_internal_transfer and rec.account_id.account_type not in ('asset_cash'):
                                        l.add((rec.move_id.name, rec.id))
                                        key = (rec.account_id.id, line.move_id.expense_type)
                                        result[key]['account_name'] = rec.account_id.name
                                        result[key]['account_code'] = rec.account_id.code
                                        result[key]['expense_type'] = rec.move_id.expense_type
                                        result[key]['total_credit'] += rec.credit
                                        result[key]['entries'].append({
                                            'move_name':rec.move_id.name,
                                            'mov_id':rec.id,
                                            'partner_id': rec.move_id.journal_id.name if rec.move_id.payment_id and rec.move_id.payment_id.is_internal_transfer
                                                          else rec.partner_id.name if rec.partner_id
                                                          else rec.account_id.name,
                                            'credit': rec.credit,
                                            'date':rec.date,
                                            'statement_date':stmt_date
                                        })

                                elif rec.credit > 0 and rec.account_id.code in (
                                '100204') and not rec.move_id.payment_id:
                                    skip_entry = False
                                    if rec.matching_number:
                                        matching_lines = self.env['account.move.line'].sudo().search([
                                            ('matching_number', '=', rec.matching_number)
                                        ])
                                        for m in matching_lines.move_id:
                                            if not m.statement_line_id:
                                                for lines in m.line_ids:
                                                    if lines.debit > 0 and lines.account_id.account_type != 'asset_cash':
                                                        skip_entry = True
                                        if skip_entry:
                                            continue
                                        l.add((rec.move_id.name, rec.id))
                                        key = (rec.account_id.id, line.move_id.expense_type)
                                        result[key]['account_name'] = rec.account_id.name
                                        result[key]['account_code'] = rec.account_id.code
                                        result[key]['expense_type'] = rec.move_id.expense_type
                                        result[key]['total_credit'] += rec.credit
                                        result[key]['entries'].append({
                                            'move_name': rec.move_id.name,
                                            'mov_id': rec.id,
                                            'partner_id': (
                                                rec.move_id.journal_id.name
                                                if rec.move_id.payment_id and rec.move_id.payment_id.is_internal_transfer
                                                else rec.partner_id.name if rec.partner_id
                                                else rec.account_id.name
                                            ),
                                            'credit': rec.credit,
                                            'date': rec.date,
                                            'statement_date': stmt_date
                                        })
        #Bank To Bank Transfer
        pay_rec = self.env['account.payment'].sudo().search([
            ('state', '=', 'posted'),
            ('is_internal_transfer','=', True),
            ('company_id', '=', company_id.id),
            ('move_id.state', '=', 'posted')])
        groups_by_match = defaultdict(set)
        seen_matches = set()
        for rec1 in pay_rec:
            for rec in rec1.move_id.line_ids:
                reconciled_lines = rec._all_reconciled_lines().filtered(
                    lambda l: l.matched_debit_ids or l.matched_credit_ids
                )
                for line in reconciled_lines:
                    if line.matching_number and line.matching_number not in seen_matches:
                        groups_by_match[line.matching_number].update(
                            reconciled_lines.ids
                        )
                        seen_matches.add(line.matching_number)
        groups_by_match = {k: list(v) for k, v in groups_by_match.items()}

        for match_no, ids in groups_by_match.items():
            groups_with_statement = []
            move_lines = self.env['account.move.line'].browse(ids)
            if any(l.statement_line_id and date_from <= l.date <= date_to for l in move_lines):
                groups_with_statement.append(ids)
                for g in groups_with_statement:
                    r1 =  self.env['account.move.line'].browse(g)
                    for r in r1:
                        if not all(line.account_id.code == '100801' for line in r1):
                            # continue
                            if not r.statement_line_id and r.credit > 0 and not r.move_id.journal_id.is_credit_card_bank:
                                # if r.move_id.payment_id.payment_type != 'inbound':
                                        key = (r.account_id.id, r.move_id.expense_type)
                                        result[key]['account_name'] = 'Internal Bank Transfer'
                                        result[key]['account_code'] = r.account_id.code
                                        result[key]['expense_type'] = r.move_id.expense_type
                                        result[key]['total_credit'] += r.credit
                                        result[key]['entries'].append({
                                            'move_name': r.move_id.name,
                                            'mov_id': r.id,
                                            'partner_id': r.move_id.journal_id.name if r.move_id.payment_id and r.move_id.payment_id.is_internal_transfer
                                            else r.partner_id.name if r.partner_id
                                            else r.account_id.name,
                                            'credit': r.credit,
                                            'date': r.date,
                                        })
        return list(result.values())

    def credit_card_expenses(self, date_from, date_to,company_id):

        result = defaultdict(lambda: {
            'account_name': '',
            'account_code': '',
            'expense_type': '',
            'total_debit': 0.0,
            'entries': []
        })

        #credit card expenses

        credit_card_expense = self.env['account.move.line'].sudo().search([
            ('move_id.state', '=', 'posted'),
            ('move_id.journal_id.type', 'in', ('bank', 'cash')),
            ('move_id.company_id', '=', company_id.id),
            ('move_id.is_payment_approval','=',True),
        ])
        for rec in credit_card_expense:
            if rec.matching_number:
                move_line = self.env['account.move.line'].sudo().search([('matching_number', '=', rec.matching_number), ('id', '!=', rec.id)])
                for move_line1 in move_line:
                    if (date_from <= move_line1.date <= date_to) and move_line1.statement_line_id:
                        for r in rec.move_id.line_ids:
                            if r.debit > 0:
                                key = (r.account_id.id, r.move_id.expense_type)
                                result[key]['account_name'] = r.account_id.name
                                result[key]['account_code'] = r.account_id.code
                                result[key]['expense_type'] = r.move_id.expense_type
                                result[key]['total_debit'] += r.debit
                                result[key]['entries'].append({
                                    'move_name': r.move_id.name,
                                    'mov_id': r.id,
                                    'partner_id': r.move_id.journal_id.name if r.move_id.payment_id and r.move_id.payment_id.is_internal_transfer
                                    else r.partner_id.name if r.partner_id
                                    else r.account_id.name,
                                    'debit': r.debit,
                                    'date': r.date,
                                    'statement_date': move_line.statement_line_id.date
                                })
        return list(result.values())
