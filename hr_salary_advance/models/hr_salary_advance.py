# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError,UserError
from dateutil.relativedelta import relativedelta


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    advance_journal_id = fields.Many2one(
        'account.journal',
        string='Salary Advance Journal',
        domain=[('type', 'in', ['general', 'cash', 'bank'])],
        config_parameter='hr_salary_advance.advance_journal_id'
    )
    finance_head_id = fields.Many2one(
        'res.users',
        string='Finance Head (Notifications)',
        config_parameter='hr_salary_advance.finance_head_id'
    )
    advance_debit_account_id = fields.Many2one(
        'account.account',
        string='Advance Debit Account',
        domain=[('deprecated', '=', False)],
        config_parameter='hr_salary_advance.advance_debit_account_id'
    )
    advance_credit_account_id = fields.Many2one(
        'account.account',
        string='Advance Credit Account',
        domain=[('deprecated', '=', False)],
        config_parameter='hr_salary_advance.advance_credit_account_id'
    )

class HrSalaryAdvance(models.Model):
    _name = 'hr.salary.advance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Hr Salary Advance'

    @api.model
    def _get_default_employee(self):
        employee = self.env['hr.employee'].sudo().search([('user_id', '=', self.env.user.id)], limit=1)
        return employee.id if employee else False

    name = fields.Char(string='Name', copy=False, readonly=True, default=lambda x: _('New'))
    employee_id = fields.Many2one('hr.employee', string='Employee', required=True, tracking=True, default=_get_default_employee)
    user_id = fields.Many2one('res.users', string='User', related='employee_id.user_id')
    parent_id = fields.Many2one('hr.employee', string='Manager', required=True, related='employee_id.parent_id')
    hr_id = fields.Many2one('hr.employee', string='HR', required=True, related='employee_id.hr_id')
    company_id = fields.Many2one('res.company', string= 'Company', default=lambda self: self.env.company)
    state = fields.Selection([('draft', 'Draft'),
                              ('waiting_for_approval', 'Waiting For Approval'),
                              ('approved', 'Approved'),
                              ('reject', 'Rejected'),
                              ('in_progress', 'In Progress'),
                              ('closed', 'Closed')], string='Status',
                             default='draft', copy=False, tracking=True)
    department_id = fields.Many2one('hr.department', string='Department', related='employee_id.department_id')
    job_id = fields.Many2one('hr.job', string='Job Position', related='employee_id.job_id')
    job_level_id = fields.Many2one('hr.job.levels', string='Job Level', related='employee_id.job_level_id')
    amount = fields.Float(string='Advance Amount')
    reason = fields.Text(string='Reason')
    requested_date = fields.Datetime(string='Requested Date')
    approved_amount = fields.Float(string='Approved Amount')
    approved_date = fields.Datetime(string='Approved Date')
    salary_advance_line_ids = fields.One2many('hr.salary.advance.line', 'salary_advance_id', string='Salary Advance', copy=False)
    approval_history_line_ids = fields.One2many('hr.salary.advance.approval.history', 'salary_advance_id', string='Salary Advance Approval History', copy=False)
    is_approver = fields.Boolean(string='Is Approver', compute='compute_is_approver')
    move_id = fields.Many2one('account.move', string='Journal Entry', readonly=True, copy=False)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.salary.advance.seq') or _('New')
        return super().create(vals_list)

    def compute_is_approver(self):
        for rec in self:
            if rec.approval_history_line_ids:
                pending_approval_lines = rec.approval_history_line_ids.filtered(lambda x: x.approval_state == 'waiting').sorted('id')
                if pending_approval_lines and self.env.user.id in pending_approval_lines[0].approval_user_ids.ids:
                    rec.is_approver = True
                else:
                    rec.is_approver = False
            else:
                rec.is_approver = False

    @api.onchange('amount')
    def onchange_advance_amount(self):
        self.approved_amount = self.amount

    def action_request(self):
        if not self.amount > 0:
            raise ValidationError('Requesting amount should be greater than 0')
        approval_history_vals = []
        if self.hr_id:
            hr_approval_vals = {
                'approval_user_ids': [(6, 0, [self.hr_id.user_id.id])],
            }
            approval_history_vals.append((0, 0, hr_approval_vals))
            user =self.hr_id.user_id
            if user:
                self.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary="Salary Advance Approval Required",
                    note=f"Salary Advance for {self.employee_id.name} has been sent for your approval.",
                    user_id=user.id,
                    date_deadline=fields.Date.today(),
                )
        if self.parent_id:
            parent_approval_vals = {
                'approval_user_ids': [(6, 0, [self.parent_id.user_id.id])],
            }
            approval_history_vals.append((0, 0, parent_approval_vals))
        director = self.env['hr.employee'].sudo().search([('company_id', '=', self.company_id.id), ('job_level_id.code', '=', 'Director')])
        if director:
            director_approval_vals = {
                'approval_user_ids': [(6, 0, [director.user_id.id])],
            }
            approval_history_vals.append((0, 0, director_approval_vals))
        self.write({'approval_history_line_ids': approval_history_vals, 'state': 'waiting_for_approval', 'requested_date': fields.Datetime.now()})

    def _get_move_line_name(self):
        self.ensure_one()
        return _('Salary Advance for %s') % (self.employee_id.name or '')

    def _get_advance_config_params(self):
        ICP = self.env['ir.config_parameter'].sudo()
        journal_id = ICP.get_param('hr_salary_advance.advance_journal_id')
        debit_account_id = ICP.get_param('hr_salary_advance.advance_debit_account_id')
        credit_account_id = ICP.get_param('hr_salary_advance.advance_credit_account_id')
        finance_head_id = ICP.get_param('hr_salary_advance.finance_head_id')

        if not journal_id or not debit_account_id or not credit_account_id:
            raise UserError(_('Please configure journal and accounts in Settings before confirming.'))

        journal = self.env['account.journal'].browse(int(journal_id))
        debit_account = self.env['account.account'].browse(int(debit_account_id))
        credit_account = self.env['account.account'].browse(int(credit_account_id))
        finance_head = self.env['res.users'].browse(int(finance_head_id)) if finance_head_id else False

        # Basic validations
        if not journal.exists():
            raise UserError(_('Configured journal is missing.'))
        if not debit_account.exists() or not credit_account.exists():
            raise UserError(_('Configured accounts are missing.'))

        return {
            'journal': journal,
            'debit_account': debit_account,
            'credit_account': credit_account,
            'finance_head': finance_head,
        }

    def _notify_finance_head(self, finance_head):
        self.ensure_one()
        if not finance_head:
            return
        # Schedule a simple To-Do activity on the Salary Advance record
        todo = self.env.ref('mail.mail_activity_data_todo')
        self.activity_schedule(
            activity_type_id=todo.id,
            user_id=finance_head.id,
            note=_('Please review Salary Advance %s. Journal entry created: %s') % (
                self.name, self.move_id.name or self.move_id.ref or ''
            )
        )

    def action_approve(self):
        approval_lines = self.approval_history_line_ids.filtered(lambda x: self.env.user.id in x.approval_user_ids.ids and x.approval_state == 'waiting').sorted('id')
        if approval_lines:
            for line in approval_lines:
                line.write({'approved_user_id': self.env.user.id, 'approved_date': fields.Datetime.now(), 'approval_state': 'approved'})
                if line and line.id == self.approval_history_line_ids[-1].id:
                    self.write({'state': 'approved', 'approved_date': fields.Datetime.now()})
                    params = self._get_advance_config_params()
                    line_vals = [
                        {
                            'name': self._get_move_line_name(),
                            'account_id': params['debit_account'].id,
                            'debit': self.approved_amount,
                            'credit': 0.0,
                            'partner_id': self.employee_id.related_partner_id.id,
                            # 'currency_id': rec.currency_id.id,
                            'company_id': self.company_id.id,
                        },
                        {
                            'name': self._get_move_line_name(),
                            'account_id': params['credit_account'].id,
                            'debit': 0.0,
                            'credit': self.approved_amount,
                            'partner_id': self.employee_id.related_partner_id.id,
                            # 'currency_id': rec.currency_id.id,
                            'company_id': self.company_id.id,
                        },
                    ]

                    move_vals = {
                        'move_type': 'entry',
                        'journal_id': params['journal'].id,
                        'date': fields.Date.context_today(self),
                        'ref': self.name if self.name and self.name != 'New' else _('Salary Advance'),
                        'line_ids': [(0, 0, lv) for lv in line_vals],
                        'company_id': self.company_id.id,
                    }

                    move = self.env['account.move'].create(move_vals)
                    self.move_id = move.id
                    self._notify_finance_head(params['finance_head'])
        not_approval_lines = self.approval_history_line_ids.filtered(lambda x:x.approval_state == 'waiting').sorted('id')
        if not_approval_lines:
            user = not_approval_lines[0].approval_user_ids[0]
            if user:
                self.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary="Salary Advance Approval Required",
                    note=f"Salary Advance for {self.employee_id.name} has been sent for your approval.",
                    user_id=user.id,
                    date_deadline=fields.Date.today(),
                )

    def action_view_journal_entry(self):
        self.ensure_one()
        if not self.move_id:
            raise UserError(_('No journal entry available.'))
        return {
            'name': _('Journal Entry'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.move',
            'view_mode': 'form',
            'res_id': self.move_id.id,
            'target': 'current',
        }

    def action_reject(self):
        approval_history = self.approval_history_line_ids.filtered(lambda x: x.approval_state == 'waiting' and self.env.user.id in x.approval_user_ids.ids)
        if approval_history:
            return {
                'name': 'Reject Reason',
                'type': 'ir.actions.act_window',
                'res_model': 'hr.salary.advance.reject.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'approval_history_id': approval_history[0].id,
                    'salary_advance_id': self.id,
                }
            }
        else:
            raise ValidationError('You have no access to reject this Salary Advance Request')

    def action_disburse_amount(self):
        if not self.approved_amount > 0:
            raise ValidationError('Approved Amount should be greater than 0')
        if not self.job_level_id.repayment_tenure > 0:
            raise ValidationError('The Repayment Tenure configured in Job Level should be greater than 0')
        start_date = fields.Date.today()
        installment_amount = self.approved_amount / self.job_level_id.repayment_tenure
        installment_vals = []
        for i in range(self.job_level_id.repayment_tenure):
            installment_date = (start_date + relativedelta(months=i)).replace(day=1)
            line_vals = {
                'employee_id': self.employee_id.id,
                'installment_date': installment_date,
                'installment_amount': installment_amount,
                'installment_state': 'not_paid',
            }
            installment_vals.append((0, 0, line_vals))
        self.write({'salary_advance_line_ids': installment_vals, 'state': 'in_progress'})
        domain = [('employee_id', '=', self.employee_id.id)]
        contract_self_rating_id = self.env['hr.contract'].sudo().search(domain,limit=1)
        lines = self.salary_advance_line_ids.sorted(key=lambda l: l.installment_date)
        from_date = lines[0].installment_date
        to_date = lines[-1].installment_date
        contract_self_rating_id.write({'recovery_of_advances':True,'recovery_of_advances_amount':self.approved_amount,'recovery_from_date':from_date,'recovery_to_date':to_date})

    @api.onchange('salary_advance_line_ids')
    def onchange_salary_advance_lines(self):
        if self.salary_advance_line_ids and all(advance_line.installment_state == 'paid' for advance_line in self.salary_advance_line_ids):
            self.state = 'closed'


class HrSalaryAdvanceLine(models.Model):
    _name = 'hr.salary.advance.line'
    _description = 'Salary Advance Lines'

    salary_advance_id = fields.Many2one('hr.salary.advance', string='Salary Advance')
    employee_id = fields.Many2one('hr.employee', string='Employee', related='salary_advance_id.employee_id')
    installment_date = fields.Date(string='Date')
    installment_amount = fields.Float(string='Installment Amount')
    paid_date = fields.Datetime(string='Paid Date')
    installment_state = fields.Selection([('not_paid', 'Not Paid'), ('paid', 'Paid')], string='Installment Status')


class HrSalaryAdvanceApprovalHistory(models.Model):
    _name = 'hr.salary.advance.approval.history'
    _description = 'Salary Advance Approval History'

    salary_advance_id = fields.Many2one('hr.salary.advance', string='Salary Advance')
    approval_user_ids = fields.Many2many('res.users', 'approval_user_ids_rel', string='Approval Users')
    approved_user_id = fields.Many2one('res.users', string='Approved User')
    approved_date = fields.Datetime(string='Approved Date')
    rejected_user_id = fields.Many2one('res.users', string='Rejected User')
    rejected_date = fields.Datetime(string='Rejected Date')
    approval_state = fields.Selection([('waiting', 'Waiting For Approval'), ('approved', 'Approved'), ('reject', 'Rejected')], string='Approval Status', default='waiting')
    reject_reason = fields.Text(string='Reject Reason')

