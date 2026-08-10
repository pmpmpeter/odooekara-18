# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools.misc import formatLang


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    liquidity_end_date = fields.Date(string="Date To")
    
    def create_bank_statement(self):
        context = self._context.copy()
        """return action to create a bank statements. This button should be called only on journals with type =='bank'"""
        action = self.env.ref('bank_reconciliation.action_bank_statement_wiz').read()[0]
        
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

   