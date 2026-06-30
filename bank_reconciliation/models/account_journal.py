# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    liquidity_end_date = fields.Date(string="Date To")
    # bank_statements_source = fields.Selection([('manual', 'Record Manually'), ('undefined', 'Undefined')],
    #                                           string='Bank Feeds', default='undefined', help="Defines how the bank statements will be registered")

    def create_bank_statement(self):
        context = self._context.copy()
        """return action to create a bank statements. This button should be called only on journals with type =='bank'"""
        action = self.env.ref('bank_reconciliation.action_bank_statement_wiz').read()[0]
        # action.update({
        #     'context': "{'default_journal_id': " + str(self.id) + "}",
        # })
        return action

    def action_journal_wizard(self):
        # pass
        return {
            'name': _('Update GL Balance'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.journal.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('bank_reconciliation.account_journal_wizard_view_form').id,
            'target': 'new',
            'context': dict(self._context, **{
                'default_journal_id': self.id,
            })
        }

    def _get_journal_dashboard_data_batched(self):
        res = super(AccountJournal, self)._get_journal_dashboard_data_batched()
        for journal in self:
            bank_closing_balance = 0.0
            gl_balance = 0.0
            currency = journal.currency_id or journal.company_id.currency_id
            if journal.liquidity_end_date:
                date_to_apply = journal.liquidity_end_date
            else:
                date_to_apply = fields.Date.today()
            account_id = journal.default_account_id.id
            # print(account_id,journal.name)
            if account_id:
                amount_field = 'balance' if (
                        not journal.currency_id or journal.currency_id == journal.company_id.currency_id
                ) else 'amount_currency'

                query_gl = f"""
                    SELECT SUM({amount_field}) AS sum
                    FROM account_move_line
                    WHERE account_id = %s
                    AND date <= %s AND parent_state = %s
                """
                self.env.cr.execute(query_gl, (account_id, date_to_apply, 'posted'))
                result_gl = self.env.cr.dictfetchone()
                gl_balance = result_gl.get('sum') or 0.0

            bank_stmt = self.env['bank.statement'].search(
                [('journal_id', '=', journal.id), ('state', '=', 'posted'), ('date_to', '<=', date_to_apply)],
                order='date_to desc, id desc',
                limit=1
            )
            if bank_stmt:
                bank_closing_balance = bank_stmt.bank_balance
            else:
                bank_closing_balance = 0.0

            res[journal.id].update({
                'gl_balance': formatLang(self.env, currency.round(gl_balance), currency_obj=currency),
                'bank_closing_balance': formatLang(self.env, currency.round(bank_closing_balance), currency_obj=currency),
            })
            # print(res[journal.id], "check_dashboard_values")
        return res

    # def get_journal_dashboard_datas(self):
    #     res = super(AccountJournal, self).get_journal_dashboard_datas()
    #     account_sum = 0.0
    #     bank_balance = 0.0
    #     currency = self.currency_id or self.company_id.currency_id
    #     # account_ids = tuple(ac for ac in [self.default_debit_account_id.id, self.default_credit_account_id.id] if ac)
    #     account_ids = tuple(ac for ac in [self.default_account_id.id] if ac)
    #     if account_ids:
    #         amount_field = 'balance' if (
    #                 not self.currency_id or self.currency_id == self.company_id.currency_id) else 'amount_currency'
    #         query = """SELECT sum(%s) FROM account_move_line WHERE account_id in %%s AND date <= %%s;""" % (
    #             amount_field,)
    #         self.env.cr.execute(query, (account_ids, fields.Date.today(),))
    #         query_results = self.env.cr.dictfetchall()
    #         if query_results and query_results[0].get('sum') != None:
    #             account_sum = query_results[0].get('sum')
    #         query = """SELECT sum(%s) FROM account_move_line WHERE account_id in %%s AND date <= %%s AND
    #                     statement_date is not NULL;""" % (amount_field,)
    #         self.env.cr.execute(query, (account_ids, fields.Date.today(),))
    #         query_results = self.env.cr.dictfetchall()
    #         if query_results and query_results[0].get('sum') != None:
    #             bank_balance = query_results[0].get('sum')
    #     difference = currency.round(account_sum - bank_balance) + 0.0
    #     res.update({
    #         'last_balance': formatLang(self.env, currency.round(bank_balance) + 0.0, currency_obj=currency),
    #         'difference': formatLang(self.env, currency.round(difference) + 0.0, currency_obj=currency)
    #     })
    #
    #     return res

    # def _get_journal_dashboard_data_batched(self):
    #     res = super(AccountJournal, self)._get_journal_dashboard_data_batched()
    #     for journal in self:
    #         account_sum = 0.0
    #         bank_balance = 0.0
    #         closing_balance = 0.0
    #
    #         currency = journal.currency_id or journal.company_id.currency_id
    #
    #         account_ids = tuple(ac for ac in [journal.default_account_id.id] if ac)
    #         if account_ids:
    #             amount_field = 'balance' if (
    #                     not journal.currency_id or journal.currency_id == journal.company_id.currency_id) else 'amount_currency'
    #
    #             today = fields.Date.today()
    #
    #             # 1. Closing Balance = SUM(balance) of today only
    #             query_closing = f"""
    #                                 SELECT SUM({amount_field}) AS sum
    #                                 FROM account_move_line
    #                                 WHERE account_id IN %s AND date = %s;
    #                             """
    #             self.env.cr.execute(query_closing, (account_ids, today))
    #             result_closing = self.env.cr.dictfetchone()
    #             closing_balance = result_closing.get('sum') or 0.0
    #
    #             # 2. Account Sum = SUM(balance) till today (<= today)
    #             query_account_sum = f"""
    #                         SELECT sum({amount_field}) as sum
    #                         FROM account_move_line
    #                         WHERE account_id in %s AND date <= %s;
    #                     """
    #             print(query_account_sum,"check1")
    #             self.env.cr.execute(query_account_sum, (account_ids, fields.Date.today()))
    #             result_account = self.env.cr.dictfetchall()
    #             if result_account and result_account[0].get('sum') is not None:
    #                 account_sum = result_account[0]['sum']
    #
    #             # 3. Bank Balance = SUM(balance) till today + statement_date not null
    #             query_bank_balance = f"""
    #                         SELECT sum({amount_field}) as sum
    #                         FROM account_move_line
    #                         WHERE account_id in %s AND date <= %s AND statement_date IS NOT NULL;
    #                     """
    #             print(query_bank_balance, "check2")
    #             self.env.cr.execute(query_bank_balance, (account_ids, fields.Date.today()))
    #             result_bank = self.env.cr.dictfetchall()
    #             if result_bank and result_bank[0].get('sum') is not None:
    #                 bank_balance = result_bank[0]['sum']
    #
    #         difference = currency.round(account_sum - bank_balance) + 0.0
    #
    #         bank_stmt = self.env['bank.statement'].search(
    #             [('journal_id', '=', journal.id), ('state', '=', 'posted')],
    #             order='date_to desc, id desc',
    #             limit=1
    #         )
    #         if bank_stmt:
    #             gl_balance = bank_stmt.gl_balance
    #             bank_balance = bank_stmt.bank_balance
    #         else:
    #             gl_balance = 0.0
    #             bank_balance = 0.0
    #
    #         res[journal.id].update({
    #             'closing_balance': formatLang(self.env, currency.round(closing_balance), currency_obj=currency),
    #             'last_balance': formatLang(self.env, currency.round(bank_balance) + 0.0, currency_obj=currency),
    #             'difference': formatLang(self.env, currency.round(difference) + 0.0, currency_obj=currency),
    #             'gl_balance': formatLang(self.env, gl_balance, currency_obj=currency),
    #             'bank_balance': formatLang(self.env, bank_balance, currency_obj=currency),
    #         })
    #         print(res[journal.id],"chekc3")
    #     return res
