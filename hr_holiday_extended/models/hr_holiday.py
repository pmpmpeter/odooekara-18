from odoo import models, api, _, fields
from collections import defaultdict
from odoo.exceptions import ValidationError
from datetime import date
from datetime import datetime, timedelta, time
import pytz


class HolidaysRequest(models.Model):
    _inherit = "hr.leave"

    name = fields.Char('Remarks', compute='_compute_description', inverse='_inverse_description',
                       search='_search_description', compute_sudo=False, copy=False, required=True)
    holiday_status_id = fields.Many2one(
        "hr.leave.type", compute='_compute_from_employee_id',
        store=True, string="Leave Type",
        required=True, readonly=False,
        domain="""[
               ('company_id', 'in', [employee_company_id, False]),
               '|',
                   ('requires_allocation', '=', 'no'),
                   ('has_valid_allocation', '=', True),
           ]""",
        tracking=True)

    leave_subtype_id = fields.Many2one('hr.leave.sub.type', string="Leave Subcategory",
                                       domain="[('company_id','=', company_id),('leave_type_id','=',holiday_status_id)]")
    #to map the leave subcategory without leave type
    # leave_subtype_id = fields.Many2one('hr.leave.sub.type', string="Leave Subcategory",
    #                                    domain="[('company_id','=', company_id),'|',('leave_type_id','=',False),('leave_type_id','=',holiday_status_id)]")

    @api.constrains('date_from', 'date_to', 'employee_id')
    def _check_payslip_generated(self):
        """
        Override to disable payslip-period validation
        """
        return

    @api.onchange('holiday_status_id')
    def _onchange_holiday_status_id(self):
        """ Clears leave_subtype_id when holiday_status_id changes """
        self.leave_subtype_id = False

    @api.constrains('date_from')
    def _check_date_from_in_current_month(self):
        today = date.today()

        for rec in self:
            if not rec.date_from:
                continue

            date_from = rec.date_from.date()  # ✅ convert datetime → date

            # ✅ Allow past dates
            if date_from <= today:
                continue

            # ❌ Future dates must be in current month
            if date_from.month != today.month or date_from.year != today.year:
                raise ValidationError(
                    "Future dates must be within the current month."
                )


    @api.constrains('date_from', 'leave_subtype_id', 'holiday_status_id')
    def _check_leave_days(self):
        for record in self:
            if record.holiday_status_id:
                subtypes = self.env['hr.leave.sub.type'].search([
                    ('leave_type_id', '=', record.holiday_status_id.id)
                ])

                if subtypes and not record.leave_subtype_id:
                    raise ValidationError(_(
                        "You must select a Leave Subcategory because the selected Leave Type has subcategories."
                    ))

            if record.date_from:
                leave_date = record.date_from.date()
                today_date = fields.Date.today()

                if leave_date < today_date:
                    continue

            if record.leave_subtype_id and record.date_from:
                leave_date = record.date_from.date()
                today_date = fields.Date.today()
                required_days = record.leave_subtype_id.days

                if (leave_date - today_date).days < required_days:
                    raise ValidationError(_(
                        "You must request this leave at least %d days in advance." % required_days
                    ))

class HrLeaveType(models.Model):
    _inherit = "hr.leave.type"

    sub_type_ids = fields.One2many(
        'hr.leave.sub.type',
        'leave_type_id',
        string="Leave Sub Types",
        compute="_compute_sub_types",
        store=False
    )

    @api.depends('sub_type_ids.leave_type_id')
    def _compute_sub_types(self):
        for record in self:
            record.sub_type_ids = self.env['hr.leave.sub.type'].search([('leave_type_id', 'in', record.ids)])


class HrLeaveAllocation(models.Model):
    _inherit = 'hr.leave.allocation'

    active = fields.Boolean(string="Active")
    
class HrEmployeeBase(models.AbstractModel):
    _inherit = "hr.employee.base"

    def _get_consumed_leaves(self, leave_types, target_date=False, ignore_future=False):
        employees = self or self._get_contextual_employee()
        leaves_domain = [
            ('holiday_status_id', 'in', leave_types.ids),
            ('employee_id', 'in', employees.ids),
            ('state', 'in', ['confirm', 'validate1', 'validate']),
        ]
        if self.env.context.get('ignored_leave_ids'):
            leaves_domain.append(('id', 'not in', self.env.context.get('ignored_leave_ids')))

        if not target_date:
            target_date = fields.Date.today()
        if ignore_future:
            leaves_domain.append(('date_from', '<=', target_date))
        leaves = self.env['hr.leave'].search(leaves_domain)
        leaves_per_employee_type = defaultdict(lambda: defaultdict(lambda: self.env['hr.leave']))
        for leave in leaves:
            leaves_per_employee_type[leave.employee_id][leave.holiday_status_id] |= leave

        allocations = self.env['hr.leave.allocation'].with_context(active_test=False).search([
            ('employee_id', 'in', employees.ids),
            ('holiday_status_id', 'in', leave_types.ids),
            ('state', '=', 'validate'),
        ])
        allocations_per_employee_type = defaultdict(lambda: defaultdict(lambda: self.env['hr.leave.allocation']))
        for allocation in allocations:
            allocations_per_employee_type[allocation.employee_id][allocation.holiday_status_id] |= allocation

        
        allocations_leaves_consumed = defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: defaultdict(lambda: 0))))

        to_recheck_leaves_per_leave_type = defaultdict(lambda:
            defaultdict(lambda: {
                'excess_days': defaultdict(lambda: {
                    'amount': 0,
                    'is_virtual': True,
                }),
                'exceeding_duration': 0,
                'to_recheck_leaves': self.env['hr.leave']
            })
        )
        for allocation in allocations:
            allocation_data = allocations_leaves_consumed[allocation.employee_id][allocation.holiday_status_id][allocation]
            future_leaves = 0
            if allocation.allocation_type == 'accrual':
                future_leaves = allocation._get_future_leaves_on(target_date)
            max_leaves = allocation.number_of_hours_display\
                if allocation.holiday_status_id.request_unit in ['hour']\
                else allocation.number_of_days_display
            max_leaves += future_leaves
            allocation_data.update({
                'max_leaves': max_leaves,
                'accrual_bonus': future_leaves,
                'virtual_remaining_leaves': max_leaves,
                'remaining_leaves': max_leaves,
                'leaves_taken': 0,
                'virtual_leaves_taken': 0,
            })

        for employee in employees:
            for leave_type in leave_types:
                allocations_with_date_to = self.env['hr.leave.allocation']
                allocations_without_date_to = self.env['hr.leave.allocation']
                for leave_allocation in allocations_per_employee_type[employee][leave_type]:
                    if leave_allocation.date_to:
                        allocations_with_date_to |= leave_allocation
                    else:
                        allocations_without_date_to |= leave_allocation
                sorted_leave_allocations = allocations_with_date_to.sorted(key='date_to') + allocations_without_date_to

                if leave_type.request_unit in ['day', 'half_day']:
                    leave_duration_field = 'number_of_days'
                    leave_unit = 'days'
                else:
                    leave_duration_field = 'number_of_hours'
                    leave_unit = 'hours'

                leave_type_data = allocations_leaves_consumed[employee][leave_type]
                for leave in leaves_per_employee_type[employee][leave_type].sorted('date_from'):
                    leave_duration = leave[leave_duration_field]
                    skip_excess = False

                    # if sorted_leave_allocations.filtered(lambda alloc: alloc.allocation_type == 'accrual') and leave.date_from.date() > target_date:
                    #     to_recheck_leaves_per_leave_type[employee][leave_type]['to_recheck_leaves'] |= leave
                    #     skip_excess = True
                    #     continue

                    if leave_type.requires_allocation == 'yes':
                        for allocation in sorted_leave_allocations:
                            # We don't want to include future leaves linked to accruals into the total count of available leaves.
                            # However, we'll need to check if those leaves take more than what will be accrued in total of those days
                            # to give a warning if the total exceeds what will be accrued.
                            if allocation.date_from > leave.date_to.date() or (allocation.date_to and allocation.date_to < leave.date_from.date()):
                                continue
                            interval_start = max(
                                leave.date_from,
                                datetime.combine(allocation.date_from, time.min)
                            )
                            interval_end = min(
                                leave.date_to,
                                datetime.combine(allocation.date_to, time.max)
                                if allocation.date_to else leave.date_to
                            )
                            duration = leave[leave_duration_field]
                            if leave.date_from != interval_start or leave.date_to != interval_end:
                                duration_info = employee._get_calendar_attendances(interval_start.replace(tzinfo=pytz.UTC), interval_end.replace(tzinfo=pytz.UTC))
                                duration = duration_info['hours' if leave_unit == 'hours' else 'days']
                            max_allowed_duration = min(
                                duration,
                                leave_type_data[allocation]['virtual_remaining_leaves']
                            )

                            if not max_allowed_duration:
                                continue

                            allocated_time = min(max_allowed_duration, leave_duration)
                            leave_type_data[allocation]['virtual_leaves_taken'] += allocated_time
                            leave_type_data[allocation]['virtual_remaining_leaves'] -= allocated_time
                            if leave.state == 'validate':
                                leave_type_data[allocation]['leaves_taken'] += allocated_time
                                leave_type_data[allocation]['remaining_leaves'] -= allocated_time

                            leave_duration -= allocated_time
                            if not leave_duration:
                                break
                        if round(leave_duration, 2) > 0 and not skip_excess:
                            to_recheck_leaves_per_leave_type[employee][leave_type]['excess_days'][leave.date_to.date()] = {
                                'amount': leave_duration,
                                'is_virtual': leave.state != 'validate',
                                'leave_id': leave.id,
                            }
                    else:
                        if leave_unit == 'hours':
                            allocated_time = leave.number_of_hours
                        else:
                            allocated_time = leave.number_of_days
                        leave_type_data[False]['virtual_leaves_taken'] += allocated_time
                        leave_type_data[False]['virtual_remaining_leaves'] = 0
                        leave_type_data[False]['remaining_leaves'] = 0
                        if leave.state == 'validate':
                            leave_type_data[False]['leaves_taken'] += allocated_time

        for employee in to_recheck_leaves_per_leave_type:
            for leave_type in to_recheck_leaves_per_leave_type[employee]:
                content = to_recheck_leaves_per_leave_type[employee][leave_type]
                consumed_content = allocations_leaves_consumed[employee][leave_type]
                if content['to_recheck_leaves']:
                    date_to_simulate = max(content['to_recheck_leaves'].mapped('date_from')).date()
                    latest_accrual_bonus = 0
                    date_accrual_bonus = 0
                    virtual_remaining = 0
                    additional_leaves_duration = 0
                    for allocation in consumed_content:
                        latest_accrual_bonus += allocation and allocation._get_future_leaves_on(date_to_simulate)
                        date_accrual_bonus += consumed_content[allocation]['accrual_bonus']
                        virtual_remaining += consumed_content[allocation]['virtual_remaining_leaves']
                    for leave in content['to_recheck_leaves']:
                        additional_leaves_duration += leave.number_of_hours if leave_type.request_unit == 'hours' else leave.number_of_days
                    latest_remaining = virtual_remaining - date_accrual_bonus + latest_accrual_bonus
                    content['exceeding_duration'] = round(min(0, latest_remaining - additional_leaves_duration), 2)

        return (allocations_leaves_consumed, to_recheck_leaves_per_leave_type)