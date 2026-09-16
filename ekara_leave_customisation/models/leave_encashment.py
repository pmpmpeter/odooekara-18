from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from collections import defaultdict
from datetime import date


class LeaveEncashment(models.Model):
    _name = 'leave.encashment'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Leave Encashment'

    name = fields.Char(
        default='New',
        readonly=True
    )

    employee_id = fields.Many2one(
        'hr.employee',
        required=True,
        default=lambda self: self.env.user.employee_id,
        tracking=True
    )
    active = fields.Boolean(
        default=True
    )

    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
        required=True,
        index=True
    )

    user_id = fields.Many2one(
        'res.users',
        string='Created By',
        default=lambda self: self.env.user,
        readonly=True
    )

    request_date = fields.Date(
        default=fields.Date.today
    )

    year = fields.Integer(
        default=lambda self: fields.Date.today().year
    )

    eligible_balance = fields.Float(
        readonly=True
    )

    encash_days = fields.Float(
        string='Days To Encash',
        required=True
    )

    eligible = fields.Boolean(
        compute='_compute_eligibility'
    )

    eligibility_message = fields.Char(
        compute='_compute_eligibility'
    )


    @api.depends('employee_id','year')
    def _compute_eligibility(self):

        for rec in self:

            balance = rec._get_leave_balance_as_of_feb28()

            rec.eligible_balance = balance

            rec.eligible = balance >= 20

            if balance >=20:
                rec.eligibility_message = \
                    "Eligible"

            else:
                rec.eligibility_message = \
                    f"Not Eligible. Balance on Feb 28: {balance}"

    state = fields.Selection([
        ('draft','Draft'),
        ('submitted','Submitted'),
        ('approved','Approved'),
        ('rejected','Rejected')
    ], default='draft', tracking=True)

    _sql_constraints = [
        (
            'unique_employee_year',
            'unique(employee_id,year)',
            'Encashment already submitted for this year.'
        )
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            vals.setdefault('company_id',self.env.company.id)
            vals.setdefault('user_id',self.env.user.id)
            if vals.get('name','New') == 'New':
                vals['name'] = self.env[
                    'ir.sequence'
                ].next_by_code(
                    'leave.encashment.seq'
                )

        return super().create(vals_list)

    def action_submit(self):

        for rec in self:
            balance = rec._get_leave_balance_as_of_feb28()

            rec.eligible_balance = balance

            if balance <= 21:
                raise ValidationError(_(
                    "You cannot submit.\n\n"
                    "Earned Leave balance on Feb 28: %.2f\n"
                    "Required: 21 or above"
                ) % balance)

            if rec.encash_days > balance:
                raise ValidationError(_(
                    "Encashment days cannot exceed "
                    "available balance."
                ))

            rec.state='submitted'

    def action_approve(self):
        self.state='approved'

    def action_reject(self):
        self.state='rejected'

    def _get_leave_balance_as_of_feb28(self):

        self.ensure_one()

        leave_type=self.env[
            'hr.leave.type'
        ].search([
            ('name','=','Earned Leave')
        ],limit=1)

        if not leave_type:
            raise ValidationError(
                _("Earned Leave type not found")
            )

        target_date=date(self.year,2,28)

        consumed,extra=self.employee_id._get_consumed_leaves(
            leave_type,
            target_date=target_date,
            ignore_future=True
        )

        employee_data=consumed[
            self.employee_id
        ][leave_type]

        total_remaining=0

        for allocation in employee_data:

            total_remaining += employee_data[
                allocation
            ].get(
                'remaining_leaves',
                0
            )

        return total_remaining

    def action_approve(self):
        for rec in self:
            leave_type=self.env['hr.leave.type'].search([('name','=','Earned Leave')],limit=1)
            allocation=self.env['hr.leave.allocation'].search([('employee_id','=',rec.employee_id.id),('holiday_status_id','=',leave_type.id),('state','=','validate')],limit=1)
            allocation.number_of_days_display -= rec.encash_days
            rec.state='approved'