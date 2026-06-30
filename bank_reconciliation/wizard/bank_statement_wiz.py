# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
from odoo.tools.misc import formatLang, format_date, get_lang
from dateutil.parser import parse
from datetime import datetime, timedelta
from babel.dates import format_datetime, format_date
from collections import defaultdict
from datetime import date, timedelta
from itertools import groupby
import pdb


class BankStatement(models.Model):
    _name = 'bank.statement'
    _inherit = ['mail.thread']
    _description = 'BRS Report'
    _order = 'date_to desc'
    _rec_name = 'display_name'

    @api.constrains('date_to', 'journal_id')
    def _check_date_to_unique(self):
        for record in self:
            duplicate = self.sudo().search([
                ('date_to', '=', record.date_to),
                ('journal_id', '=', record.journal_id.id),
                ('id', '!=', record.id),
            ], limit=1)
            if duplicate:
                raise ValidationError(
                    f"Duplicate date {record.date_to} for journal {record.journal_id.name}!"
                )

    @api.onchange('journal_id', 'date_from', 'date_to')
    def _get_lines(self):
        # self.account_id = self.journal_id.default_debit_account_id.id or self.journal_id.default_credit_account_id.id
        self.account_id = self.journal_id.default_account_id.id
        self.currency_id = self.journal_id.currency_id or self.journal_id.company_id.currency_id or \
                           self.env.user.company_id.currency_id
        domain = [('account_id', '=', self.account_id.id), ('statement_date', '=', False),\
            ('date', '<=', self.date_to), ('move_id.state', '=', 'posted')]
        if self.date_from:
            domain += [('date', '>=', self.date_from)]
        s_lines = []
        lines = self.env['account.move.line'].sudo().search(domain)
        #for line in self.statement_lines:
            #line.bank_statement_id = self.id
        self.statement_lines = lines
        for line in self.statement_lines:
            counter_domain=[('move_id', '=', line.move_id.id),('account_id', '!=', self.account_id.id)]
            counter_part_ledger_ids = self.env['account.move.line'].sudo().search(counter_domain)
            # pdb.set_trace()
            if len(counter_part_ledger_ids)==1:
                line.counter_part_ledger = counter_part_ledger_ids.account_id.display_name
            from datetime import datetime, date
            from dateutil.relativedelta import relativedelta
            today = datetime.today()
            delta = (today.date() - line.date).days
            if delta>5:
                line.bank_indicator=True
        last_manual_bank_stmt = self.search([('journal_id', '=', self.journal_id.id),\
            ('state', '=', 'posted')], order="date_to desc", limit=1)
        if last_manual_bank_stmt:
            self.start_bank_balance = last_manual_bank_stmt[0].bank_balance or 0

    @api.depends('statement_lines.statement_date', 'start_bank_balance')
    def _compute_amount(self):
        for record in self:
            gl_balance = 0
            receipt_balance = 0
            payments_balance = 0
            bank_balance = 0
            current_update = 0
            current_receipts = 0
            current_payments = 0
            start_bank_balance = 0
            if record.account_id and record.date_to:
                # domain = [('account_id', '=', record.account_id.id), ('date', '<=', record.date_to), ('move_id.state', '=', 'posted')]
                # lines = self.env['account.move.line'].sudo().search(domain)
                # gl_balance += sum([line.debit - line.credit for line in lines])
                query1 = """
                        SELECT sum(aml.balance) as gl_balance
                        FROM account_move_line aml
                        where aml.account_id=%s and aml.date<=%s and aml.parent_state=%s;
                        """
                query_params1 = (record.account_id.id, str(record.date_to), 'posted')
                data_get1= self.env.cr.execute(query1, query_params1)
                lines1 = self.env.cr.dictfetchall()
                if lines1[0].get('gl_balance') and lines1[0].get('gl_balance') != None:
                    gl_balance = lines1[0].get('gl_balance')
                # domain_new=[('account_id', '=', record.account_id.id), ('statement_date', '=', False),\
                #     ('date', '<=', record.date_to), ('move_id.state', '=', 'posted')]
                # domain += [('id', 'not in', record.statement_lines.ids), ('statement_date', '!=', False)]
                # lines = self.env['account.move.line'].sudo().search(domain)
                # bank_balance += sum([line.balance for line in lines])
                ids_to_exclude = tuple(record.statement_lines.ids) or (-1,)
                query2 = """
                        SELECT sum(aml.balance) as bank_balance
                        FROM account_move_line aml
                        where aml.account_id=%s and aml.date<=%s and aml.parent_state=%s and aml.id not in %s 
                        and aml.statement_date is not Null;
                        """
                query_params2 = (record.account_id.id, str(record.date_to), 'posted', ids_to_exclude)
                data_get2= self.env.cr.execute(query2, query_params2)
                lines2 = self.env.cr.dictfetchall()
                if lines2[0].get('bank_balance') and lines2[0].get('bank_balance') != None:
                    bank_balance = lines2[0].get('bank_balance')
            current_update += sum(
                [line.debit - line.credit if line.statement_date else 0 for line in record.statement_lines])
            receipt_balance += sum([line.debit for line in record.statement_lines])
            payments_balance += sum([line.credit for line in record.statement_lines])
            current_receipts += sum([line.debit if line.statement_date else 0 for line in record.statement_lines])
            current_payments += sum([line.credit if line.statement_date else 0 for line in record.statement_lines])
            start_bank_balance = record.start_bank_balance
            record.gl_balance = gl_balance
            record.bank_balance = start_bank_balance + current_update
            record.balance_difference = record.gl_balance - current_update
            record.receipts_difference = receipt_balance - current_receipts
            record.payments_difference = payments_balance - current_payments

    display_name = fields.Char(string="Display Name", compute="_compute_display_name", store=True)
    journal_id = fields.Many2one('account.journal', 'Bank', domain=[('type', '=', 'bank')])
    account_id = fields.Many2one('account.account', 'Bank Account')
    date_from = fields.Date('Date From')
    date_to = fields.Date('Date To')
    posted_date = fields.Date(string='Posted Date', readonly=True)
    statement_lines = fields.One2many('account.move.line', 'bank_statement_id')
    gl_balance = fields.Monetary('Balance as per Company Books', readonly=True, compute='_compute_amount')
    start_bank_balance = fields.Monetary('Starting Balance as per Bank', states={'confirm': [('readonly', True)]})
    bank_balance = fields.Monetary('Balance as per Bank', readonly=True, compute='_compute_amount', store=True)
    balance_difference = fields.Monetary('Amounts not Reflected in Bank', readonly=True, compute='_compute_amount', store=True)
    receipts_difference = fields.Monetary('Receipts not Reflected in Bank', readonly=True, compute='_compute_amount', store=True)
    payments_difference = fields.Monetary('Payments not Reflected in Bank', readonly=True, compute='_compute_amount', store=True)
    current_update = fields.Monetary('Balance of entries updated now')
    currency_id = fields.Many2one('res.currency', string='Currency')
    state = fields.Selection([('draft', 'Draft'), ('posted', 'Posted')], string='State', copy=False, default='draft',track_visibility='onchange')
    company_id = fields.Many2one('res.company', string='Company', related='journal_id.company_id', store=True)

    @api.depends('account_id', 'date_from', 'date_to')
    def _compute_display_name(self):
        """Compute the display name based on account and date range."""
        for record in self:
            name = ''
            if record.account_id:
                name = f"{record.account_id.code} - {record.account_id.name}"
            if record.date_from:
                date_from_formatted = parse(str(record.date_from)).strftime("%d/%m/%Y")
                name += f" from {date_from_formatted}"
            if record.date_to:
                date_to_formatted = parse(str(record.date_to)).strftime("%d/%m/%Y")
                name += f" - {date_to_formatted}"
            record.display_name = name

    # def action_post(self):
    #     for record in self:
    #         for line in record.statement_lines:
    #             if line.statement_date:
    #                 line.sudo().write({'reconciled': True})
    #                 if line.payment_id.state=='posted':
    #                     line.payment_id.sudo().write({'state': 'reconciled'})
    #                 for item in line.move_id.line_ids.filtered(lambda r: r.account_type in ['asset_receivable','liability_payable']):
    #                     item.sudo().write({'brs_status': True})
    #             elif not line.statement_date:
    #                 line.sudo().write({'reconciled': False})
    #                 if line.payment_id.state=='reconciled':
    #                     line.payment_id.sudo().write({'state': 'posted'})
    #         record.write({
    #             'state':'posted',
    #             'posted_date' : fields.Date.today(),
    #         })
    #     return True

    def action_post(self):
        for record in self:
            for line in record.statement_lines:
                if line.statement_date:
                    line.sudo().write({'reconciled': True})
                    if line.payment_id.is_reconciled:
                        line.payment_id.sudo().write({'is_reconciled': True})
                    else:
                        pass
                    # for item in line.move_id.line_ids.filtered(lambda r: r.account_type in ['asset_receivable', 'liability_payable']):
                    #     item.sudo().write({'brs_status': True})
                else:
                    line.sudo().write({'reconciled': False})
                    if line.payment_id.is_reconciled:
                        line.payment_id.sudo().write({'is_reconciled': False})

            record.write({
                'state': 'posted',
                'posted_date': fields.Date.today(),
            })
        return True

    def reset_to_draft(self):
        for record in self:
            record.write({
                'state' :'draft',
                'posted_date' : False,
            })
        return True

    def unlink(self):
        if self.state =='posted':
            raise UserError(_('You cannot perform this action on an posted Bank Reconciliation.'))
        return super(BankStatement, self).unlink()

    def action_update_brs(self):
        for record in self:
            if not record.date_to:
                raise UserError('Please Add the Date to.')
            if not record.account_id:
                raise UserError('Please Add a Bank Account.')

            query1 = """update account_move_line set bank_statement_id=%s where id in (select aml.id from account_move_line aml
                        join account_move am on am.id=aml.move_id
                        where am.state='posted' and aml.account_id=%s and aml.statement_date is Null
                        and aml.date<='%s');"""%(record.id, record.account_id.id, str(record.date_to))
            self.env.cr.execute(query1)

            query2 = """update account_move_line set bank_statement_id=Null where id in (select aml.id from account_move_line aml
                        join account_move am on am.id=aml.move_id
                        where am.state='draft' and aml.bank_statement_id=%s);"""%(record.id)
            self.env.cr.execute(query2)

        # print("Sumit 1")
        # s_lines = []
        # move_line_id = []
        # print("Sumit 2")
        # # pdb.set_trace()
        # for line in self.statement_lines:
        #     # line.bank_statement_id = self.id
        #     move_line_id.append(line.id)
        # print("Sumit 3")
        # domain = [('account_id', '=', self.account_id.id), ('id', 'not in', move_line_id), ('bank_statement_id', '=', False),('date', '<=', str(self.date_to)),('move_id.state', '=', 'posted')]
        # if self.date_from:
        #     domain += [('date', '>=', self.date_from)]
        # new_lines = self.env['account.move.line'].search(domain)
        # # pdb.set_trace()
        # for line in new_lines:
        #     line.write({'bank_statement_id': self.id})
        # for line in self.statement_lines:
        #     if line.move_id.state not in ['posted']:
        #         line.write({'bank_statement_id': False})
