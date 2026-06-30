from odoo import models, fields, api, _
import xlwt
# from cStringIO import StringIO
import io
import base64
from xlwt import easyxf
from odoo.exceptions import UserError
import datetime
from datetime import datetime
from dateutil.relativedelta import relativedelta, MO
import calendar
import pdb
import time

date = datetime.now()
date_format = date.strftime('%Y-%m-%d')
date_format_1 = date.strftime('%d.%m.%Y')
date_format_2 = date.strftime("%B")
first_day_year = date.strftime('%Y-01-01')
previous_month = date - relativedelta(months=1)
date_format_3 = previous_month.strftime("%B")
MONTH_LIST= [('1', 'Jan'), ('2', 'Feb'), ('3', 'Mar'), 
            ('4', 'Apr'), ('5', 'May'), ('6', 'Jun'), 
            ('7', 'Jul'), ('8', 'Aug'), ('9', 'Sep'), 
            ('10', 'Oct'), ('11', 'Nov'),('12', 'Dec')]


class BalanceLeavesReportWizard(models.TransientModel):
    _name = "balance.leave.report.wizard"
    
    summary_file = fields.Binary('Balance Leave Report')
    file_name = fields.Char('File Name')
    report_printed = fields.Boolean('Balance Leave Report')
    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date', default=fields.Datetime.now)
    company_id = fields.Many2one('res.company', string="Company", default=lambda self: self.env.company)
    
    def last_day_of_month(self,any_day):
        import datetime
        next_month = any_day.replace(day=28) + datetime.timedelta(days=4)
        return next_month - datetime.timedelta(days=next_month.day)

    def monthlist(self,date_from,date_end):
        import datetime
        begin = self.date_from
        end = self.date_to
        result = []
        while True:
            print(type(begin),begin)
            if begin.month == 12:
                next_month = begin.replace(year=begin.year+1,month=1, day=1)
            else:
                next_month = begin.replace(month=begin.month+1, day=1)
            if next_month > end:
                break
            result.append ([begin.strftime("%Y-%m-%d"),self.last_day_of_month(begin).strftime("%Y-%m-%d")])
            begin = next_month
        result.append ([begin.strftime("%Y-%m-%d"),end.strftime("%Y-%m-%d")])
        return result
    
   #  def action_get_balance_leave_report(self):
   #      workbook = xlwt.Workbook()
   #      worksheet1 = workbook.add_sheet('Balance Leaves-%s'%(date_format_1))
   #      design_1 = easyxf('align: horiz right;font: bold 1;')
   #      design_2 = easyxf('align: horiz left;font: bold 1;')
   #      design_3 = easyxf('align: horiz left')
   #      design_14 = easyxf('align: horiz left; pattern: pattern solid, fore_colour blue;')
   #      design_16 = easyxf('align: horiz left; pattern: pattern solid, fore_colour pink;')
   #      design_11 = easyxf('align: horiz left; pattern: pattern solid, fore_colour green;font: bold 1;')
   #      design_12 = easyxf('align: horiz left; pattern: pattern solid, fore_colour green;')
   #
   #      rows = 0
   #      worksheet1.set_panes_frozen(True)
   #      worksheet1.set_horz_split_pos(rows+1)
   #      worksheet1.set_remove_splits(True)
   #
   #      worksheet1.write(rows, 0, _('Sl. No.'), design_2)
   #      worksheet1.write(rows, 1, _('Employee Name'), design_2)
   #      worksheet1.write(rows, 2, _('Employee Code'), design_2)
   #      worksheet1.write(rows, 3, _('PL Allocation'), design_11)
   #      worksheet1.write(rows, 4, _('PL Balance'), design_11)
   #      worksheet1.write(rows, 5, _('SL Allocation'), design_11)
   #      worksheet1.write(rows, 6, _('SL Balance'), design_11)
   #      import datetime
   #      date_list1 = self.monthlist(self.date_from,self.date_to)
   #      col_1=7
   #      print(col_1,"col_1")
   #      for m in range(len(date_list1)):
   #          row_1=0
   #          a=date_list1[m]
   #          date_from = a[0]
   #          date_to = a[1]
   #          month_a1 = date_from.strftime("%B") if isinstance(date_from, datetime.date) else datetime.datetime.strptime(
   #              date_from, '%Y-%m-%d').strftime("%B")
   #          # worksheet1.write(rows, col_1, _('EL In %s'%(month_a1)), design_14)
   #          worksheet1.write(rows, col_1, _('PL In %s'%(month_a1)), design_14)
   #          worksheet1.write(rows, col_1+1, _('SL In %s'%(month_a1)), design_14)
   #          # worksheet1.write(rows, col_1+2, _('Absent In %s'%(month_a1)), design_16)
   #          col_1+=2
   #          print(col_1,"test2")
   #      # worksheet1.write(rows, 6, _('Absent In %s'%(date_format_2)), design_2)
   #      # worksheet1.write(rows, 7, _('Total Absent'), design_2)
   #
   #      worksheet1.col(0).width = 2000
   #      worksheet1.col(1).width = 7000
   #      worksheet1.col(2).width = 3800
   #      worksheet1.col(3).width = 3500
   #      worksheet1.col(4).width = 3500
   #      worksheet1.col(5).width = 3500
   #      worksheet1.col(6).width = 3500
   #      for n in range(50):
   #          if n<4:
   #              continue
   #          worksheet1.col(n).width = 4000
   #          # worksheet1.col(n).width = 5000
   #          # worksheet1.col(n).width = 5000
   #
   #      employee_id = self.env['hr.employee'].search([])
   #      row_pq = 1
   #      col = 2
   #      sl_no = 1
   #      for each in employee_id:
   #          if each.name=='Administrator':
   #              continue
   #          ###----Calculation of Casual Leaves-----####
   #          year_from = self.date_from.year if self.date_from else None
   #          year_to = self.date_to.year if self.date_to else None
   #          added_leaves_pl = removed_leaves_pl = total_pl_leaves_balance = t_leaves_pl = 0
   #          pl_leave_status_id = self.env['hr.leave.type'].search([('name','=','Paid Time Off')])
   #          paid_leaves_days_ids1 = self.env['hr.leave.allocation'].search([('employee_id','=',each.id),
   #                      ('holiday_status_id','=',pl_leave_status_id.id),
   #                      # ('date_to','<=',self.date_to),
   #                      ('state','=','validate')]).filtered(lambda leave:
   #                      leave.date_to and leave.date_to.year == year_to and
   #                      leave.date_from and leave.date_from.year == year_from
   #                  )
   #          print(date_to, "date to" , self.date_to,  )
   #          paid_leaves_days_ids2 = self.env['hr.leave'].search([('employee_id','=',each.id),
   #                      ('holiday_status_id','=',pl_leave_status_id.id),
   #                      ( 'date_from','>=',self.date_from),
   #                      ('date_to','<=',self.date_to),
   #                      ('state','=','validate')])
   #
   #          paid_leaves_days_ids3 = self.env['hr.leave'].search([('employee_id','=',each.id),
   #                      ('holiday_status_id','=',pl_leave_status_id.id),
   #                      ('state','=','validate')]).filtered(lambda pl_leave:
   #                      pl_leave.date_to and pl_leave.date_to.year == year_to and
   #                      pl_leave.date_from and pl_leave.date_from.year == year_from
   #                                                          )
   #
   #          print(paid_leaves_days_ids1,paid_leaves_days_ids2,pl_leave_status_id)
   #          # casual_leaves_days_ids =list(set(casual_leaves_days_ids1+casual_leaves_days_ids2))
   #          for remove in paid_leaves_days_ids2:
   #              removed_leaves_pl += remove.number_of_days
   #          for add in paid_leaves_days_ids1:
   #              added_leaves_pl += add.number_of_days
   #          for t_pl in paid_leaves_days_ids3:
   #              t_leaves_pl += t_pl.number_of_days
   #          total_pl_leaves_balance = added_leaves_pl-t_leaves_pl
   #
   #
   #          added_leaves_sl = removed_leaves_sl = total_sl_leaves_balance = t_leaves_sl = 0
   #          sl_leave_status_id = self.env['hr.leave.type'].search([('name','=','Sick Leave')])
   #          sick_leaves_days_ids1 = self.env['hr.leave.allocation'].search([('employee_id','=',each.id),
   #                      ('holiday_status_id','=',sl_leave_status_id.id),
   #                      # ('date_to','<=',self.date_to),
   #                      ('state','=','validate')]).filtered(lambda sleave:
   #                      sleave.date_to and sleave.date_to.year == year_to and
   #                      sleave.date_from and sleave.date_from.year == year_from
   #                  )
   #          sick_leaves_days_ids2 = self.env['hr.leave'].search([('employee_id','=',each.id),
   #                      ('holiday_status_id','=',sl_leave_status_id.id),
   #                      ( 'date_from','>=',self.date_from),
   #                      ('date_to','<=',self.date_to),
   #                      ('state','=','validate')])
   #
   #          sick_leaves_days_ids3 = self.env['hr.leave'].search([('employee_id','=',each.id),
   #                      ('holiday_status_id','=',sl_leave_status_id.id),
   #                      ('state','=','validate')]).filtered(lambda sl_leave:
   #                      sl_leave.date_to and sl_leave.date_to.year == year_to and
   #                      sl_leave.date_from and sl_leave.date_from.year == year_from
   #                                                          )
   #
   #          # casual_leaves_days_ids =list(set(casual_leaves_days_ids1+casual_leaves_days_ids2))
   #          for remove in sick_leaves_days_ids2:
   #              removed_leaves_sl += remove.number_of_days
   #          for add in sick_leaves_days_ids1:
   #              added_leaves_sl += add.number_of_days
   #          for t_sl in sick_leaves_days_ids3:
   #              t_leaves_sl += t_sl.number_of_days
   #          total_sl_leaves_balance = added_leaves_sl-t_leaves_sl
   #
   #          ###----Calculation of Earned Leaves-----####
   #          #
   #          # added_leaves_el = removed_leaves_el = total_el_leaves_balance = 0
   #          # el_leave_status_id = self.env['hr.holidays.status'].search([('name','=','Earned Leave')])
   #          # earned_leaves_ids1 = self.env['hr.holidays'].search([('employee_id','=',each.id),
   #          #             ('holiday_status_id','=',el_leave_status_id.id),
   #          #             ('type','=','add'),('date_to','<=',self.date_to),
   #          #             ('state','=','validate')])
   #          # earned_leaves_ids2 = self.env['hr.holidays'].search([('employee_id','=',each.id),
   #          #             ('holiday_status_id','=',el_leave_status_id.id),
   #          #             ('type','=','remove'),('date_to','<=',self.date_to),
   #          #             ('state','=','validate')])
   #          # earned_leaves_ids =list(set(earned_leaves_ids1+earned_leaves_ids2))
   #          # for remove in earned_leaves_ids2:
   #          #     removed_leaves_el += remove.number_of_days_temp
   #          # for add in earned_leaves_ids1:
   #          #     added_leaves_el += add.number_of_days_temp
   #          # total_el_leaves_balance = added_leaves_el-removed_leaves_el
   #          # if each.emp_category =='blue':
   #          #     emp_category='Worker'
   #          # elif each.emp_category =='contract':
   #          #     emp_category='Contract'
   #          # elif each.emp_category=='white':
   #          #     emp_category='Staff'
   #          # else:
   #          #     emp_category=''
   #          worksheet1.write(row_pq, 0, sl_no, design_3)
   #          worksheet1.write(row_pq, 1, each.name)
   #          worksheet1.write(row_pq, 2, each.employee_number)
   #          # worksheet1.write(row_pq, 3, emp_category)
   #          # worksheet1.write(row_pq, 4, total_el_leaves_balance,design_12)
   #          worksheet1.write(row_pq, 3, added_leaves_pl,design_12)
   #          worksheet1.write(row_pq, 4, total_pl_leaves_balance,design_12)
   #          worksheet1.write(row_pq, 5, added_leaves_sl,design_12)
   #          worksheet1.write(row_pq, 6, total_sl_leaves_balance,design_12)
   #          # worksheet1.write(row_pq, 5, removed_leaves_pl,design_12)
   #
   #          ######### Total Absent in Current Month ###########
   #          # import datetime
   # #          start_date = datetime.datetime.today().replace(day=1)
   # #          start_format = start_date.strftime('%Y-%m-%d')
   # #          date = datetime.datetime.now()
   # #          end_date=datetime.datetime(date.year,date.month,1) + datetime.timedelta(days=calendar.monthrange(date.year,date.month)[1] - 1)
   # #          end_format = end_date.strftime('%Y-%m-%d')
   #
   # #          leave_date_from = start_format + " 00:00:00"
   # #          leave_date_to = end_format + " 23:59:59"
   # #          month_start_date = datetime.datetime.strptime(leave_date_from,'%Y-%m-%d %H:%M:%S').date()
   # #          month_end_date = datetime.datetime.strptime(leave_date_to,'%Y-%m-%d %H:%M:%S').date()
   # #          leave_status_id = self.env['hr.leave.type'].search([('unpaid','=',True)])
   #          import datetime
   #          dt1 = self.date_from
   #          dt2 = self.date_to
   #          date_list = self.monthlist(self.date_from,self.date_to)
   #          col_1=7
   #          print(col_1, "test3")
   #          for m in range(len(date_list)):
   #              a=date_list[m]
   #
   #              date_from = datetime.datetime.strptime(a[0], '%Y-%m-%d').date()
   #              date_to = datetime.datetime.strptime(a[1], '%Y-%m-%d').date()
   #
   #              date_from = datetime.datetime.combine(date_from, datetime.time.min)
   #              date_to = datetime.datetime.combine(date_to, datetime.time.max)
   #              added_leaves_el1=removed_leaves_el1=0
   #              added_leaves_cl1=removed_leaves_cl1=0
   #              removed_leaves_pl121=removed_leaves_sl121=0
   #              total_absent_in_month =absent_in_current_month=0
   #              total_cl_leaves_balance12=total_el_leaves_balance12=casual_leaves_ids121=0
   #              total_cl_leaves_balance21=total_el_leaves_balance21=earned_leaves_ids121=0
   #              # earned_leaves_ids12 = self.env['hr.holidays'].search([('employee_id','=',each.id),
   #              #             ('holiday_status_id','=',el_leave_status_id.id),
   #              #             ('type','=','remove'),('date_from','>=',date_from),('date_from','<=',date_to),
   #              #             ('state','=','validate')])
   #              # earned_leaves_ids21 = self.env['hr.holidays'].search([('employee_id','=',each.id),
   #              #             ('holiday_status_id','=',el_leave_status_id.id),
   #              #             ('type','=','remove'),('date_to','>=',date_from),('date_to','<=',date_to),
   #              #             ('state','=','validate')])
   #              # earned_leaves_ids121 =list(set(earned_leaves_ids21+earned_leaves_ids12))
   #              # for remove1 in earned_leaves_ids121:
   #              #     removed_leaves_el121 += remove1.number_of_days_temp
   #              # total_el_leaves_balance121 = removed_leaves_el121
   #              # worksheet1.write(row_pq, col_1, total_el_leaves_balance121 or '__',design_14)
   #
   #              paid_leaves_ids = self.env['hr.leave'].search([
   #                  ('employee_id', '=', each.id),
   #                  ('holiday_status_id', '=', pl_leave_status_id.id),
   #                  '|',
   #                  ('date_from', '>=', date_from), ('date_from', '<=', date_to),
   #                  '|',
   #                  ('date_to', '>=', date_from), ('date_to', '<=', date_to),
   #                  ('state', '=', 'validate')
   #              ])
   #              removed_leaves_pl121 = sum(paid_leaves_ids.mapped('number_of_days'))
   #              worksheet1.write(row_pq, col_1, removed_leaves_pl121 or 0, design_14)
   #              col_1 += 1
   #
   #              sick_leaves_ids = self.env['hr.leave'].search([
   #                  ('employee_id', '=', each.id),
   #                  ('holiday_status_id', '=', sl_leave_status_id.id),
   #                  '|',
   #                  ('date_from', '>=', date_from), ('date_from', '<=', date_to),
   #                  '|',
   #                  ('date_to', '>=', date_from), ('date_to', '<=', date_to),
   #                  ('state', '=', 'validate')
   #              ])
   #              removed_leaves_sl121 = sum(sick_leaves_ids.mapped('number_of_days'))
   #              worksheet1.write(row_pq, col_1, removed_leaves_sl121 or 0, design_14)
   #              col_1 += 1
   #
   #
   #
   #              # domain1=[('employee_id','=',each.id),('holiday_status_id','=',leave_status_id.id),
   #              #         ('date_from','>=',date_from),('date_from','<=',date_to),('state','=','validate')]
   #              # domain2=[('employee_id','=',each.id),('holiday_status_id','=',leave_status_id.id),
   #              #         ('date_to','>=',date_from),('date_to','<=',date_to),('state','=','validate')]
   #              # absent_leaves_days_ids11 = self.env['hr.leave.allocation'].search(domain1)
   #              # adsent_leaves_days_ids22 = self.env['hr.leave'].search(domain2)
   #              # # absent_leaves_days_ids123 =list(set(absent_leaves_days_ids11+adsent_leaves_days_ids22))
   #              # removed_leaves_absent  = added_leaves_absent = total_absent_leaves_balance = 0
   #              # for remove in adsent_leaves_days_ids22:
   #              #     removed_leaves_absent += remove.number_of_days
   #              # for add in absent_leaves_days_ids11:
   #              #     added_leaves_absent += add.number_of_days
   #              # total_absent_leaves_balance = added_leaves_absent - removed_leaves_absent
   #              #
   #              # # for val in absent_leaves_days_ids123:
   #              # #     absent_in_current_month += val.number_of_days
   #              # # total_absent_in_month = absent_in_current_month
   #              # worksheet1.write(row_pq, col_1+2, total_absent_leaves_balance or '__',design_16)
   #              print(col_1, "test3")
   #              # col_1 += 2
   #          row_pq += 1
   #          sl_no += 1
   #          print(col_1, "test4")
   #
   #          ######### Total Absent in Previous Month ###########
   #
   #          # now = time.localtime()
   #          # last = datetime.date(now.tm_year, now.tm_mon, 1) - datetime.timedelta(1)
   #          # first = last.replace(day=1)
   #          # last_date = last.strftime('%Y-%m-%d')
   #          # first_date= first.strftime('%Y-%m-%d')
   #          # leave_status_id1 = self.env['hr.holidays.status'].search([('name','=','Unpaid')])
   #          # alpha = first_date + " 00:00:00"
   #          # beta = last_date + " 23:59:59"
   #          # last_month_start = datetime.datetime.strptime(alpha,'%Y-%m-%d %H:%M:%S').date()
   #          # last_month_end = datetime.datetime.strptime(beta,'%Y-%m-%d %H:%M:%S').date()
   #          # domain3=[('employee_id','=',each.id),('holiday_status_id','=',leave_status_id1.id),('type','=','remove'),
   #          #       ('date_from','>=',alpha),('date_from','<=',beta),('state','=','validate')]
   #
   #          # domain4=[('employee_id','=',each.id),('holiday_status_id','=',leave_status_id1.id),('type','=','remove'),
   #          #       ('date_to','>=',alpha),('date_to','<=',beta),('state','=','validate')]
   #
   #          # absent_leaves_days_ids3 = self.env['hr.holidays'].search(domain3)
   #
   #          # adsent_leaves_days_ids4 = self.env['hr.holidays'].search(domain4)
   #          # absent_leaves_days_ids_last_month =list(set(absent_leaves_days_ids3+adsent_leaves_days_ids4))
   #
   #          # absent_in_last_month = 0
   #          # for val in absent_leaves_days_ids_last_month:
   #          #     absent_in_last_month += val.number_of_days_temp
   #
   #          #####Total Absent##############
   #
   #          # start_year = datetime.datetime.today().replace(day=1,month=1)
   #          # start_year_format = start_year.strftime('%Y-%m-%d')
   #          # current_date=datetime.datetime.today()
   #          # current_date_format = current_date.strftime('%Y-%m-%d')
   #
   #          # leave_status_id3 = self.env['hr.holidays.status'].search([('name','=','Unpaid')])
   #          # leave_start_y = start_year_format + " 00:00:00"
   #          # leave_end_y = current_date_format + " 23:59:59"
   #          # year_start_z = datetime.datetime.strptime(leave_start_y,'%Y-%m-%d %H:%M:%S').date()
   #          # year_end_z = datetime.datetime.strptime(leave_end_y,'%Y-%m-%d %H:%M:%S').date()
   #
   #          # domain5=[('employee_id','=',each.id),('holiday_status_id','=',leave_status_id3.id),('type','=','remove'),
   #          #       ('date_from','>=',leave_start_y),('date_from','<=',leave_end_y),('state','=','validate')]
   #
   #          # domain6=[('employee_id','=',each.id),('holiday_status_id','=',leave_status_id3.id),('type','=','remove'),
   #          #       ('date_to','>=',leave_start_y),('date_to','<=',leave_end_y),('state','=','validate')]
   #
   #          # absent_leaves_days_ids5 = self.env['hr.holidays'].search(domain5)
   #
   #          # adsent_leaves_days_ids6 = self.env['hr.holidays'].search(domain6)
   #          # total_absent_leaves_days_ids =list(set(absent_leaves_days_ids5+adsent_leaves_days_ids6))
   #
   #          # total_absent = 0
   #          # for vals in total_absent_leaves_days_ids:
   #          #     total_absent += vals.number_of_days_temp
   #
   #
   #      fp = io.BytesIO()
   #      workbook.save(fp)
   #      fp.seek(0)
   #      excel_file = base64.b64encode(fp.getvalue()).decode('utf-8')
   #      self.summary_file = excel_file
   #      self.file_name = 'Leave Balance-%s.xls'%(date_format_1)
   #      self.report_printed = True
   #      fp.close()
   #      return {
   #              'view_mode': 'form',
   #              'res_id': self.id,
   #              'res_model': 'balance.leave.report.wizard',
   #              'view_type': 'form',
   #              'type': 'ir.actions.act_window',
   #              'context': self.env.context,
   #              'target': 'new',
   #              }

    import xlwt
    from xlwt import easyxf
    import io
    import base64
    from datetime import datetime

    def action_get_balance_leave_report(self):
        workbook = xlwt.Workbook()
        worksheet = workbook.add_sheet('Leave Balance Report')

        # Styles
        design_header = easyxf('align: horiz center; font: bold 1; pattern: pattern solid, fore_colour blue;')
        design_data = easyxf('align: horiz left')

        # Column Setup
        row_idx = 0
        col_idx = 0
        col_widths = {}

        # Static Columns
        static_headers = [_('Sl. No.'), _('Employee Name'), _('Employee Code')]
        for header in static_headers:
            worksheet.write(row_idx, col_idx, header, design_header)
            col_widths[col_idx] = max(len(header), col_widths.get(col_idx, 0))
            col_idx += 1

        # Dynamic Leave Type Headers
        leave_types = self.env['hr.leave.type'].search([('requires_allocation', '=', 'yes')])
        leave_columns = []
        for leave_type in leave_types:
            allocation_header = f"{leave_type.name} Allocation"
            balance_header = f"{leave_type.name} Balance"

            worksheet.write(row_idx, col_idx, _(allocation_header), design_header)
            col_widths[col_idx] = max(len(allocation_header), col_widths.get(col_idx, 0))
            leave_columns.append({'name': leave_type.name, 'allocation_col': col_idx})
            col_idx += 1

            worksheet.write(row_idx, col_idx, _(balance_header), design_header)
            col_widths[col_idx] = max(len(balance_header), col_widths.get(col_idx, 0))
            leave_columns[-1]['balance_col'] = col_idx
            col_idx += 1

        # Fetch Employees Based on Company
        employees = self.env['hr.employee'].search([
            ('company_id', '=', self.company_id.id)
        ])
        row_idx += 1
        sl_no = 1

        for employee in employees:
            col_idx = 0
            worksheet.write(row_idx, col_idx, sl_no, design_data)
            col_widths[col_idx] = max(len(str(sl_no)), col_widths.get(col_idx, 0))
            col_idx += 1

            worksheet.write(row_idx, col_idx, employee.name or '', design_data)
            col_widths[col_idx] = max(len(employee.name or ''), col_widths.get(col_idx, 0))
            col_idx += 1

            worksheet.write(row_idx, col_idx, employee.employee_number or '', design_data)
            col_widths[col_idx] = max(len(employee.employee_number or ''), col_widths.get(col_idx, 0))
            col_idx += 1

            for leave in leave_columns:
                # Fetch Allocation
                allocation = self.env['hr.leave.allocation'].search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id.name', '=', leave['name']),
                    ('state', '=', 'validate'),
                    '|',
                    ('date_to', '=', False),
                    ('date_to', '>', self.date_from),
                ])
                total_allocation = round(sum(allocation.mapped('number_of_days')),2) if allocation else 0

                # Fetch Taken Leaves
                taken_leaves = self.env['hr.leave'].search([
                    ('employee_id', '=', employee.id),
                    ('holiday_status_id.name', '=', leave['name']),
                    ('state', '=', 'validate'),
                    ('date_from', '>=', self.date_from),
                    ('date_to', '<=', self.date_to),
                ])
                total_taken = round(sum(taken_leaves.mapped('number_of_days')),2) if taken_leaves else 0

                # Calculate Balance
                total_balance = total_allocation - total_taken

                # Write Data
                worksheet.write(row_idx, leave['allocation_col'], total_allocation, design_data)
                col_widths[leave['allocation_col']] = max(len(str(total_allocation)),
                                                          col_widths.get(leave['allocation_col'], 0))

                worksheet.write(row_idx, leave['balance_col'], total_balance, design_data)
                col_widths[leave['balance_col']] = max(len(str(total_balance)), col_widths.get(leave['balance_col'], 0))

            row_idx += 1
            sl_no += 1

        # Adjust Column Widths
        for col_idx, width in col_widths.items():
            worksheet.col(col_idx).width = 256 * (width + 2)

        # Save and Encode Workbook
        fp = io.BytesIO()
        workbook.save(fp)
        fp.seek(0)
        excel_file = base64.b64encode(fp.getvalue()).decode('utf-8')
        fp.close()

        # Save File in Model Fields
        self.summary_file = excel_file
        self.file_name = f'Leave Balance-{datetime.now().strftime("%Y-%m-%d")}.xls'
        self.report_printed = True

        return {
            'view_mode': 'form',
            'res_id': self.id,
            'res_model': 'balance.leave.report.wizard',
            'view_type': 'form',
            'type': 'ir.actions.act_window',
            'context': self.env.context,
            'target': 'new',
        }
