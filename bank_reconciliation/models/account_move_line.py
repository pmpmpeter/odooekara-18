# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import RedirectWarning, UserError, ValidationError, AccessError
import pdb

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    bank_statement_id = fields.Many2one('bank.statement', 'Bank Statement', copy=False)
    statement_date = fields.Date('Bank.St Date', copy=False)
    bank_indicator=fields.Boolean(default=False)
    ref_date = fields.Date('Ref Date', readonly=True, \
        help="Effective date for payment Reference")
    counter_part_ledger=fields.Char('Counter Party Ledger')

    # @api.onchange('statement_date','date')
    # def _onchange_bank_date_restriction(self):
    #     for line in self:
    #         if line.statement_date and line.date:
    #             if line.statement_date < line.date:
    #                 raise UserError("Alert!! You cannot enter a bank date behind the system entry date.")
    #         if line.statement_date and line.bank_statement_id.date_to:
    #             if not (line.date <= line.statement_date <= line.bank_statement_id.date_to):
    #                 raise UserError("Alert!! The statement date must be within the range of the system entry date and date to.")

    # def write(self, vals):
    #     if not vals.get("statement_date"):
    #         vals.update({"reconciled": False})
    #         for record in self:
    #             if record.payment_id and record.payment_id.state == 'reconciled':
    #                 record.payment_id.state = 'posted'
    #     elif vals.get("statement_date"):
    #         # pdb.set_trace()
    #         if vals.get("statement_date")<str(self.date):
    #             raise UserError("Alert !! You cannot enter a bank date behind the system entry date.")
    #         vals.update({"reconciled": True})
    #         for record in self:
    #             if record.payment_id:
    #                 record.payment_id.state = 'reconciled'
    #     res = super(AccountMoveLine, self).write(vals)
    #     return res
