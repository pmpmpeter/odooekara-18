from odoo import models, fields, api, _
import xlwt
from io import BytesIO
import base64
from xlwt import easyxf
import datetime
from odoo.exceptions import UserError
from datetime import datetime
from dateutil.relativedelta import relativedelta
import pdb

class BRSReport(models.TransientModel):
    _name = "bank.reconciliation.statement.report"

    summary_file = fields.Binary('BRS Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('BRS Report Printed')
    date=fields.Date("Date", default=fields.Date.context_today, required=True)

    def action_get_bank_reconciliation_report(self):
        workbook = xlwt.Workbook()  
        worksheet1 = workbook.add_sheet('Unreconciled Transactions')
        design_7 = easyxf('align: horiz left;font: bold 1;')
        design_8 = easyxf('align: horiz left;')
        design_9 = easyxf('align: horiz right;')
        design_10 = easyxf('align: horiz right; pattern: pattern solid, fore_colour red;')
        design_11 = easyxf('align: horiz right; pattern: pattern solid, fore_colour green;')
        design_12 = easyxf('align: horiz right; pattern: pattern solid, fore_colour gray25;')
        style2 = xlwt.XFStyle()
        style2.num_format_str = '#,##0.00'

        worksheet1.col(0).width = 2000
        worksheet1.col(1).width = 7000
        worksheet1.col(2).width = 5000
        worksheet1.col(3).width = 8000
        worksheet1.col(4).width = 12000
        worksheet1.col(5).width = 12000
        worksheet1.col(6).width = 4000
        worksheet1.col(7).width = 3000
        worksheet1.col(8).width = 3000
        worksheet1.col(9).width = 6000

        rows = 0
        cols = 0
        row_pq = 0
        
        worksheet1.set_panes_frozen(True)
        worksheet1.set_horz_split_pos(rows+1)
        worksheet1.set_remove_splits(True)

        col_1=0

        worksheet1.write(rows, col_1, _('Sl.No'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Ledger'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Journal Entry'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Partner'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Label'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Reference'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Date'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Debit'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Credit'), design_7)
        col_1+=1
        worksheet1.write(rows, col_1, _('Counter Party Ledger'), design_7)
        col_1+=1

        sl_no = 1
        row_pq = row_pq+1
        active_id = self._context.get('active_id')
        brs_id = self.env['bank.statement'].search([('id','=',active_id)])
        for record in self:
            unreconciled_debit_total =0
            unreconciled_credit_total =0
            domain1 = [('account_id', '=', brs_id.account_id.id),('date', '<=', brs_id.date_to)\
            , ('move_id.state', '=', 'posted'), ('statement_date', '=', False)]
            cr_dr_lines1 = self.env['account.move.line'].search(domain1)
            for m in range(len(cr_dr_lines1)):
                ref_date1 = cr_dr_lines1[m].date                
                import datetime
                d11 = str(ref_date1)
                dt21 = datetime.datetime.strptime(d11, '%Y-%m-%d')
                date1 = dt21.strftime("%d/%m/%Y")
                worksheet1.write(row_pq, 0, sl_no, design_8)
                worksheet1.write(row_pq, 1, cr_dr_lines1[m].account_id.display_name, design_8)
                worksheet1.write(row_pq, 2, cr_dr_lines1[m].move_id.name, design_8)
                if cr_dr_lines1[m].partner_id:
                    worksheet1.write(row_pq, 3, cr_dr_lines1[m].partner_id.display_name, design_8)
                worksheet1.write(row_pq, 4, cr_dr_lines1[m].name, design_8)
                worksheet1.write(row_pq, 5, cr_dr_lines1[m].ref, design_8)
                worksheet1.write(row_pq, 6, date1, design_8)
                worksheet1.write(row_pq, 7, cr_dr_lines1[m].debit, style2)
                unreconciled_debit_total+=cr_dr_lines1[m].debit
                worksheet1.write(row_pq, 8, cr_dr_lines1[m].credit, style2)
                unreconciled_credit_total+=cr_dr_lines1[m].credit
                counter_domain=[('move_id', '=', cr_dr_lines1[m].move_id.id),('account_id', '!=', cr_dr_lines1[m].account_id.id)]
                counter_part_ledger_ids = self.env['account.move.line'].search(counter_domain)
                if len(counter_part_ledger_ids)==1:
                    worksheet1.write(row_pq, 9, counter_part_ledger_ids.account_id.display_name, design_8)
                row_pq += 1
                sl_no += 1
        row_pq += 1
        worksheet1.write(row_pq, 1, 'Unreconciled Debit Total', design_7)
        worksheet1.write(row_pq, 2, unreconciled_debit_total, style2)
        row_pq += 1
        worksheet1.write(row_pq, 1, 'Unreconciled Credit Total', design_7)
        worksheet1.write(row_pq, 2, unreconciled_credit_total, style2)
        row_pq += 1
        worksheet1.write(row_pq, 1, 'Balance as per Bank', design_7)
        worksheet1.write(row_pq, 2, brs_id.bank_balance, style2)
        row_pq += 1
        worksheet1.write(row_pq, 1, 'Balance as per Books', design_7)
        worksheet1.write(row_pq, 2, brs_id.gl_balance, style2)

        import datetime
        brs_idd1 = str(brs_id.date_to)
        brs_iddt2 = datetime.datetime.strptime(brs_idd1, '%Y-%m-%d')
        brs_iddate = brs_iddt2.strftime("%d.%m.%Y") 

        worksheet2 = workbook.add_sheet('BRS - %s'%(brs_iddate))

        worksheet2.col(0).width = 2000
        worksheet2.col(1).width = 7000
        worksheet2.col(2).width = 5000
        worksheet2.col(3).width = 8000
        worksheet2.col(4).width = 12000
        worksheet2.col(5).width = 12000
        worksheet2.col(6).width = 4000
        worksheet2.col(7).width = 3000
        worksheet2.col(8).width = 3000
        worksheet2.col(9).width = 3000
        worksheet2.col(10).width = 6000

        rows = 0
        cols = 0
        row_pq = 0
        
        worksheet2.set_panes_frozen(True)
        worksheet2.set_horz_split_pos(rows+1)
        worksheet2.set_remove_splits(True)

        col_1=0

        worksheet2.write(rows, col_1, _('Sl.No'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Ledger'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Journal Entry'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Partner'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Label'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Reference'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Date'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Bank St.Date'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Debit'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Credit'), design_7)
        col_1+=1
        worksheet2.write(rows, col_1, _('Counter Party Ledger'), design_7)
        col_1+=1

        sl_no = 1
        row_pq = row_pq+1
        for record in self:
            brs_today_debit_total =0
            brs_today_credit_total =0
            domain2 = [('account_id', '=', brs_id.account_id.id),('date', '<=', brs_id.date_to)\
            , ('move_id.state', '=', 'posted'), ('statement_date', '!=', False), ('bank_statement_id', '=', brs_id.id)]
            cr_dr_lines2 = self.env['account.move.line'].search(domain2)
            for m in range(len(cr_dr_lines2)):                
                ref_date = cr_dr_lines2[m].date                
                import datetime
                d1 = str(ref_date)
                dt2 = datetime.datetime.strptime(d1, '%Y-%m-%d')
                date = dt2.strftime("%d/%m/%Y")           
                worksheet2.write(row_pq, 0, sl_no, design_8)
                worksheet2.write(row_pq, 1, cr_dr_lines2[m].account_id.display_name, design_8)
                worksheet2.write(row_pq, 2, cr_dr_lines2[m].move_id.name, design_8)
                worksheet2.write(row_pq, 3, cr_dr_lines2[m].partner_id.display_name or '', design_8)
                worksheet2.write(row_pq, 4, cr_dr_lines2[m].name or '', design_8)
                worksheet2.write(row_pq, 5, cr_dr_lines2[m].ref or '', design_8)
                worksheet2.write(row_pq, 6, date, design_8)
                worksheet2.write(row_pq, 7, cr_dr_lines2[m].statement_date.strftime("%d/%m/%Y"), design_8)
                worksheet2.write(row_pq, 8, cr_dr_lines2[m].debit, style2)
                brs_today_debit_total+=cr_dr_lines2[m].debit
                worksheet2.write(row_pq, 9, cr_dr_lines2[m].credit, style2)
                brs_today_credit_total+=cr_dr_lines2[m].credit
                counter_domain=[('move_id', '=', cr_dr_lines2[m].move_id.id),('account_id', '!=', cr_dr_lines2[m].account_id.id)]
                counter_part_ledger_ids = self.env['account.move.line'].search(counter_domain)
                if len(counter_part_ledger_ids)==1:
                    worksheet2.write(row_pq, 10, counter_part_ledger_ids.account_id.display_name, design_8)
                row_pq += 1
                sl_no += 1

        row_pq += 1
        worksheet2.write(row_pq, 1, 'BRS Debit Total', design_7)
        worksheet2.write(row_pq, 2, brs_today_debit_total, style2)
        row_pq += 1
        worksheet2.write(row_pq, 1, 'BRS Credit Total', design_7)
        worksheet2.write(row_pq, 2, brs_today_credit_total, style2)

        fp = BytesIO()
        o = workbook.save(fp)
        fp.read()
        excel_file = base64.b64encode(fp.getvalue())
        self.write({'summary_file': excel_file, 'file_name': 'BRS.xls','report_printed':True})
        fp.close()
        return {
                'view_mode': 'form',
                'res_id': self.id,
                'res_model': 'bank.reconciliation.statement.report',
                'view_type': 'form',
                'type': 'ir.actions.act_window',
                'context': self.env.context,
                'target': 'new',
                }
        
