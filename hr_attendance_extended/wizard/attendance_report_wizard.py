from odoo import models, fields, api
import calendar
from datetime import datetime,date,timedelta

class AttendanceReportWizard(models.TransientModel):
    _name = 'attendance.report.wizard'
    _description = 'Attendance Report Wizard'

    company_id = fields.Many2one('res.company', string="Company", required=True, default=lambda self: self.env.company)
    start_date = fields.Date(string="Start Date", default=lambda self: self._default_start_date())
    end_date = fields.Date(string="End Date", default=lambda self: self._default_end_date())

    report_type = fields.Selection([
        ('hr_compliances','HR Compliances'),
        ('form_f', 'Form F'),
        ('form_h', 'Form H'),
        ('form_t', 'Form T'),
    ], string='Report Type', required=True,default='form_f')
    month = fields.Selection(
        [(str(i), calendar.month_name[i]) for i in range(1, 13)],
        string="Select Month",default=lambda self: str(datetime.now().month),
    )
    year = fields.Char(
        string="Year",
        default=lambda self: fields.Date.today().year
    )

    @api.model
    def _default_start_date(self):
        """Set the start date to the first day of the current month."""
        today = date.today()
        return today.replace(day=1)

    @api.model
    def _default_end_date(self):
        """Set the end date to the last day of the current month."""
        today = date.today()
        next_month = today.replace(day=28) + timedelta(days=4)  # Go to the next month
        last_day_of_month = next_month - timedelta(days=next_month.day)
        return last_day_of_month

    @api.model
    def get_days_in_month(self):
        if self.month and self.year:
            month = int(self.month)
            year = self.year
            return calendar.monthrange(int(year), month)[1]  # Returns (weekday, number_of_days)
        return 0

    @api.model
    def get_start_datetime(self):
        if self.month and self.year:
            # Start of the month
            start_datetime = datetime(int(self.year), int(self.month), 1, 00, 00, 00)

            # Last day of the month
            _, last_day = calendar.monthrange(int(self.year), int(self.month))
            end_datetime = datetime(int(self.year), int(self.month), last_day, 23, 59, 59)
            return start_datetime
        return None

    @api.model
    def get_end_datetime(self):
        if self.month and self.year:
            # Start of the month
            start_datetime = datetime(int(self.year), int(self.month), 1, 00, 00, 00)

            # Last day of the month
            _, last_day = calendar.monthrange(int(self.year), int(self.month))
            end_datetime = datetime(int(self.year), int(self.month), last_day, 23, 59, 59)
            return end_datetime
        return None

    def generate_pdf_report(self):
        attendance_rec=[]
        emp_rec=[]
        employee = self.env['hr.employee'].sudo().search([])
        print(employee,'bbbbbbbbbbbbbbbbbbbbbbbb')

        for rec in employee:
            emp_rec.append(rec.id)
        for rec in employee:
            attendance_rec.append(rec)
        data = {
            'comp_id': self.company_id.id,
            'start_date': self.start_date,
            'end_date': self.end_date,
            # 'attendance':attendance_rec,
        }
        leaves_types = []
        leave_types = self.env['hr.leave.type'].sudo().search([])
        for rec in leave_types:
            leaves_types.append(rec.name)

        days_in_month = self.get_days_in_month()
        startdate = self.get_start_datetime()
        enddate = self.get_end_datetime()
        month = int(self.month)
        year = int(self.year)
        month_start = datetime(year, month, 1).date()
        _, last_day = calendar.monthrange(year, month)
        month_end = datetime(year, month, last_day).date()
        #leave_rec = self.env['hr.leave'].sudo().search([('state','=','validate'),('request_date_from','&gt;=',month_start),('request_date_to','&lt;=',month_end)])
        data1 = {
            'month_name': calendar.month_name[int(self.month)],
            'days_in_month': days_in_month,
            'employee': emp_rec,
            'leaves_types': leaves_types,
            'startdate':startdate,
            'enddate':enddate,
            'month_start':month_start,
            'month_end':month_end,
            'comp_id':self.company_id.id
        }
        if self.report_type == 'form_f':
            return self.env.ref('hr_attendance_extended.form_f_report').report_action(self,data=data)
        elif self.report_type == 'form_h':
            return self.env.ref('hr_attendance_extended.form_h_report').report_action(self,data=data)
        elif self.report_type == 'form_t':
            return self.env.ref('hr_attendance_extended.form_t_report').report_action(self,data=data1)
        elif self.report_type == 'hr_compliances':
            return self.env.ref('hr_attendance_extended.get_hr_compliances').report_action(self)
