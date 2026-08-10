import ast
from babel.dates import format_datetime, format_date
from collections import defaultdict
from datetime import datetime, timedelta
import json
import random

from odoo import models, api, _, fields
from odoo.exceptions import UserError
from odoo.osv import expression
from odoo.release import version
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF, SQL
from odoo.tools.misc import formatLang, format_date as odoo_format_date, get_lang
import pdb

def group_by_journal(vals_list):
    res = defaultdict(list)
    for vals in vals_list:
        res[vals['journal_id']].append(vals)
    return res

class AccountsJournal(models.Model):
    _inherit = 'account.journal'

    is_credit_card_bank = fields.Boolean(string='Is Credit Card Payment?',default=False)
    is_opening_balance = fields.Boolean(string='Is Opening Balance?',default=False)

    def _get_journal_dashboard_bank_running_balance_dated(self,till_date):
        print(till_date,'bbbbbbbbbbbbbbbbbbbbb')
        if till_date:
            self._cr.execute("""
                SELECT journal.id AS journal_id,
                       statement.id AS statement_id,
                       COALESCE(statement.balance_end_real, 0) AS balance_end_real,
                       without_statement.amount AS unlinked_amount,
                       without_statement.count AS unlinked_count
                  FROM account_journal journal
             LEFT JOIN LATERAL (  -- select latest statement based on the date
                               SELECT id,
                                      first_line_index,
                                      balance_end_real
                                 FROM account_bank_statement
                                WHERE journal_id = journal.id
                                  AND company_id = ANY(%s)
                                  AND date <= %s
                             ORDER BY date DESC, id DESC
                                LIMIT 1
                       ) statement ON TRUE
             LEFT JOIN LATERAL (  -- sum all the lines not linked to a statement with a higher index than the last line of the statement
                               SELECT COALESCE(SUM(stl.amount), 0.0) AS amount,
                                      COUNT(*)
                                 FROM account_bank_statement_line stl
                                 JOIN account_move move ON move.id = stl.move_id
                                WHERE stl.statement_id IS NULL
                                  AND move.state != 'cancel'
                                  AND move.journal_id = journal.id
                                  AND move.company_id = ANY(%s)
                                  AND move.date <= %s
                                  AND stl.internal_index >= COALESCE(statement.first_line_index, '')
                                LIMIT 1
                       ) without_statement ON TRUE
                 WHERE journal.id = ANY(%s)
            """, [self.env.companies.ids,till_date, self.env.companies.ids, till_date,self.ids])
            query_res = {res['journal_id']: res for res in self.env.cr.dictfetchall()}
            result = {}
            for journal in self:
                journal_vals = query_res[journal.id]
                result[journal.id] = (
                    bool(journal_vals['statement_id'] or journal_vals['unlinked_count']),
                    journal_vals['balance_end_real'] + journal_vals['unlinked_amount'],
                )
        else:
            self._cr.execute("""
                            SELECT journal.id AS journal_id,
                                   statement.id AS statement_id,
                                   COALESCE(statement.balance_end_real, 0) AS balance_end_real,
                                   without_statement.amount AS unlinked_amount,
                                   without_statement.count AS unlinked_count
                              FROM account_journal journal
                         LEFT JOIN LATERAL (  -- select latest statement based on the date
                                           SELECT id,
                                                  first_line_index,
                                                  balance_end_real
                                             FROM account_bank_statement
                                            WHERE journal_id = journal.id
                                              AND company_id = ANY(%s)
                                         ORDER BY date DESC, id DESC
                                            LIMIT 1
                                   ) statement ON TRUE
                         LEFT JOIN LATERAL (  -- sum all the lines not linked to a statement with a higher index than the last line of the statement
                                           SELECT COALESCE(SUM(stl.amount), 0.0) AS amount,
                                                  COUNT(*)
                                             FROM account_bank_statement_line stl
                                             JOIN account_move move ON move.id = stl.move_id
                                            WHERE stl.statement_id IS NULL
                                              AND move.state != 'cancel'
                                              AND move.journal_id = journal.id
                                              AND move.company_id = ANY(%s)
                                              AND stl.internal_index >= COALESCE(statement.first_line_index, '')
                                            LIMIT 1
                                   ) without_statement ON TRUE
                             WHERE journal.id = ANY(%s)
                        """, [self.env.companies.ids, self.env.companies.ids, self.ids])
            query_res = {res['journal_id']: res for res in self.env.cr.dictfetchall()}
            result = {}
            for journal in self:
                journal_vals = query_res[journal.id]
                result[journal.id] = (
                    bool(journal_vals['statement_id'] or journal_vals['unlinked_count']),
                    journal_vals['balance_end_real'] + journal_vals['unlinked_amount'],
                )
        return result

    # def _fill_bank_cash_dashboard_data(self, dashboard_data):
    #     """Populate all bank and cash journal's data dict with relevant information for the kanban card."""
    #     bank_cash_journals = self.filtered(lambda journal: journal.type in ('bank', 'cash'))
    #     if not bank_cash_journals:
    #         return

    #     # Number to reconcile
    #     self._cr.execute("""
    #         SELECT st_line_move.journal_id,
    #                COUNT(st_line.id)
    #           FROM account_bank_statement_line st_line
    #           JOIN account_move st_line_move ON st_line_move.id = st_line.move_id
    #          WHERE st_line_move.journal_id IN %s
    #            AND NOT st_line.is_reconciled
    #            AND st_line_move.state = 'posted'
    #            AND st_line_move.company_id IN %s
    #       GROUP BY st_line_move.journal_id
    #     """, [tuple(bank_cash_journals.ids), tuple(self.env.companies.ids)])
    #     number_to_reconcile = {
    #         journal_id: count
    #         for journal_id, count in self.env.cr.fetchall()
    #     }

    #     # Last statement
    #     bank_cash_journals.last_statement_id.mapped(lambda s: s.balance_end_real)  # prefetch

    #     outstanding_pay_account_balances = bank_cash_journals._get_journal_dashboard_outstanding_payments()

    #     # Payment with method outstanding account == journal default account
    #     direct_payment_balances = bank_cash_journals._get_direct_bank_payments()

    #     # Misc Entries (journal items in the default_account not linked to bank.statement.line)
    #     misc_domain = []
    #     for journal in bank_cash_journals:
    #         date_limit = journal.last_statement_id.date or journal.company_id.fiscalyear_lock_date
    #         misc_domain.append(
    #             [('account_id', '=', journal.default_account_id.id), ('date', '>', date_limit)]
    #             if date_limit else
    #             [('account_id', '=', journal.default_account_id.id)]
    #         )
    #     misc_domain = [
    #         *self.env['account.move.line']._check_company_domain(self.env.companies),
    #         ('statement_line_id', '=', False),
    #         ('parent_state', '=', 'posted'),
    #         ('payment_id', '=', False),
    #   ] + expression.OR(misc_domain)

    #     misc_totals = {
    #         account: (balance, count_lines, currencies)
    #         for account, balance, count_lines, currencies in self.env['account.move.line']._read_group(
    #             domain=misc_domain,
    #             aggregates=['amount_currency:sum', 'id:count', 'currency_id:recordset'],
    #             groupby=['account_id'])
    #     }

    #     # To check
    #     to_check = {
    #         journal: (amount, count)
    #         for journal, amount, count in self.env['account.bank.statement.line']._read_group(
    #             domain=[
    #                 ('journal_id', 'in', bank_cash_journals.ids),
    #                 ('move_id.company_id', 'in', self.env.companies.ids),
    #                 # ('move_id.to_check', '=', True),
    #                 ('move_id.state', '=', 'posted'),
    #             ],
    #             groupby=['journal_id'],
    #             aggregates=['amount:sum', '__count'],
    #         )
    #     }

    #     for journal in bank_cash_journals:
    #         # User may have read access on the journal but not on the company
    #         currency = journal.currency_id or self.env['res.currency'].browse(journal.company_id.sudo().currency_id.id)
    #         has_outstanding, outstanding_pay_account_balance = outstanding_pay_account_balances[journal.id]
    #         to_check_balance, number_to_check = to_check.get(journal, (0, 0))
    #         misc_balance, number_misc, misc_currencies = misc_totals.get(journal.default_account_id, (0, 0, currency))
    #         currency_consistent = misc_currencies == currency
    #         accessible = journal.company_id.id in journal.company_id._accessible_branches().ids
    #         nb_direct_payments, direct_payments_balance = direct_payment_balances[journal.id]
    #         # if journal.id ==78:
    #         #     pdb.set_trace()
    #         journal_closing_balance = 0
    #         bank_closing_balance1 = 45
    #         query = """
    #             select sum(balance) as balance FROM account_move_line aml 
    #             join account_move am on am.id=aml.move_id 
    #             where am.state='posted' and aml.account_id=%s
    #             """
    #         params = tuple(journal.default_account_id.ids)
    #         data_get8= self.env.cr.execute(query, params)
    #         lines8 = self.env.cr.dictfetchall()
    #         if (lines8[0].get('balance') != None):
    #             journal_closing_balance = lines8[0].get('balance') or 0
    #         ####Bank Closing Balance
    #         bank_closing_balance1 = 0.0

    #         latest_lines = self.env['account.bank.statement.line'].sudo().search([
    #             ('journal_id', '=', journal.id),
    #             ('move_id.state', '=', 'posted'),('is_reconciled', '=', True)
    #         ], order='internal_index desc', limit=1)
    #         if latest_lines:
    #             latest_lines._compute_running_balance()
    #             bank_closing_balance1 = latest_lines[0].running_balance
    #         dashboard_data[journal.id].update({
    #             'number_to_check': number_to_check,
    #             'to_check_balance': currency.format(to_check_balance),
    #             'number_to_reconcile': number_to_reconcile.get(journal.id, 0),
    #             'account_balance': currency.format(journal_closing_balance),
    #             'bank_closing_balance1': currency.format(bank_closing_balance1),
    #             'has_at_least_one_statement': bool(journal.last_statement_id),
    #             'nb_lines_bank_account_balance': (bool(journal.has_statement_lines) or bool(nb_direct_payments)) and accessible,
    #             'outstanding_pay_account_balance': currency.format(outstanding_pay_account_balance),
    #             'nb_lines_outstanding_pay_account_balance': has_outstanding,
    #             'last_balance': currency.format(journal.last_statement_id.balance_end_real),
    #             'last_statement_id': journal.last_statement_id.id,
    #             'bank_statements_source': journal.bank_statements_source,
    #             'is_sample_data': journal.has_statement_lines,
    #             'nb_misc_operations': number_misc,
    #             'misc_class': 'text-warning' if not currency_consistent else '',
    #             'misc_operations_balance': currency.format(misc_balance) if currency_consistent else None,
    #         })

class AccountBankStatementLine(models.Model):
    _inherit = 'account.bank.statement.line'

    x_review_result = fields.Char(string="Review Result",related="move_id.x_review_result")

    def _get_default_amls_matching_domain(self):
        self.ensure_one()
        domain = super()._get_default_amls_matching_domain()
        if self.journal_id:
            # domain.append(('journal_id', '=', self.journal_id.id))
            domain.extend([('journal_id', '=', self.journal_id.id),('statement_line_id', '=', False)])
            account_ids = []
            if self.company_id.account_journal_payment_debit_account_id:
                account_ids.append(self.company_id.account_journal_payment_debit_account_id.id)
            if self.company_id.account_journal_payment_credit_account_id:
                account_ids.append(self.company_id.account_journal_payment_credit_account_id.id)
            param = self.env['ir.config_parameter'].sudo().get_param('brs_account_ids')
            if param:
                try:
                    account_ids.extend([int(x) for x in param.split(',') if x])
                except ValueError:
                    pass  # ignore bad values
            if account_ids:
                domain.append(('account_id', 'in', account_ids))

        return domain

