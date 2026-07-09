from odoo import api, fields, models, _, tools
from datetime import datetime
from odoo.exceptions import ValidationError
from odoo import fields, models, api, _, Command
from collections import defaultdict


class ResCompanyInherited(models.Model):
    _inherit = 'res.company'

    tax_entity1 = fields.Many2one('res.company', string="Tax Entity1")
    share1 = fields.Integer('Share %')
    tax_entity2 = fields.Many2one('res.company', string="Tax Entity2")
    share2 = fields.Integer('Share %')
    crr_reminder_users = fields.Many2many('res.users', string="CRR & CUR Reminder Users",
                                          help="Users who will receive monthly CRR & CUR reminders")
    po_threshold_amount = fields.Float('PO Thresshold Amount')
    tax_entity_ids = fields.One2many(
        "res.company.tax.entity",
        "company_id",
        string="Tax Entities",
    )
    disable_budget_company = fields.Boolean(string='Disable Budget',default=False)

    def _update_opening_move(self, to_update):
        """ Create or update the opening move for the accounts passed as parameter.

        :param to_update:   A dictionary mapping each account with a tuple (debit, credit).
                            A separated opening line is created for both fields. A None value on debit/credit means the corresponding
                            line will not be updated.
        """
        self.ensure_one()

        # Don't allow to modify the opening move if not in draft.
        opening_move = self.account_opening_move_id
        # pdb.set_trace()
        # if opening_move and opening_move.state != 'draft':
        #     raise UserError(_(
        #         'TestssssssYou cannot import the "openning_balance" if the opening move (%s) is already posted. \
        #         If you are absolutely sure you want to modify the opening balance of your accounts, reset the move to draft.',
        #         self.account_opening_move_id.name,
        #     ))

        def del_lines(lines):
            nonlocal open_balance
            for line in lines:
                open_balance -= line.balance
                yield Command.delete(line.id)

        def update_vals(account, side, balance, balancing=False):
            nonlocal open_balance
            # pdb.set_trace()
            corresponding_lines = corresponding_lines_per_account[(account, side)]
            currency = account.currency_id or self.currency_id
            amount_currency = balance if balancing else self.currency_id._convert(balance, currency, date=conversion_date)
            open_balance += balance
            if self.currency_id.is_zero(balance):
                yield from del_lines(corresponding_lines)
            elif corresponding_lines:
                line_to_update = corresponding_lines[0]
                open_balance -= line_to_update.balance
                yield Command.update(line_to_update.id, {
                    'balance': balance,
                    'amount_currency': amount_currency,
                })
                yield from del_lines(corresponding_lines[1:])
            else:
                yield Command.create({
                    'name':_("Automatic Balancing Line") if balancing else _("Opening balance"),
                    'account_id': account.id,
                    'balance': balance,
                    'amount_currency': amount_currency,
                    'currency_id': currency.id,
                })

        # Decode the existing opening move.
        corresponding_lines_per_account = defaultdict(lambda: self.env['account.move.line'])
        corresponding_lines_per_account.update(opening_move.line_ids.grouped(lambda line: (
            line.account_id,
            'debit' if line.balance > 0.0 or line.amount_currency > 0.0 else 'credit',
        )))

        # Update the opening move's lines.
        balancing_account = self.get_unaffected_earnings_account()
        open_balance = (
            sum(corresponding_lines_per_account[(balancing_account, 'credit')].mapped('credit'))
            -sum(corresponding_lines_per_account[(balancing_account, 'debit')].mapped('debit'))
        )
        commands = []
        move_values = {'line_ids': commands}
        if opening_move:
            conversion_date = opening_move.date
        else:
            move_values.update(self._get_default_opening_move_values())
            conversion_date = move_values['date']
        for account, (debit, credit) in to_update.items():
            if debit is not None:
                commands.extend(update_vals(account, 'debit', debit))
            if credit is not None:
                commands.extend(update_vals(account, 'credit', -credit))

        commands.extend(update_vals(balancing_account, 'debit', max(-open_balance, 0), balancing=True))
        commands.extend(update_vals(balancing_account, 'credit', -max(open_balance, 0), balancing=True))

        # Nothing to do.
        if not commands:
            return

        if opening_move:
            opening_move.write(move_values)
        else:
            self.account_opening_move_id = self.env['account.move'].create(move_values)



class ResCompanyTaxEntity(models.Model):
    _inherit = "res.company.tax.entity"

    company_id = fields.Many2one("res.company",string="Company",required=True,ondelete="cascade")

    @api.constrains("share", "company_id")
    def _check_share_sum(self):
        for rec in self:
            if rec.company_id:
                total_share = sum(rec.company_id.tax_entity_ids.mapped("share"))
                