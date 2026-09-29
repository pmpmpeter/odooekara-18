# -*- coding: utf-8 -*-
from contextlib import nullcontext

from odoo import api, fields, models, _, tools, Command
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError
from odoo.tools.sql import SQL
from bisect import bisect_left
from collections import defaultdict
import logging
import re

_logger = logging.getLogger(__name__)

ACCOUNT_REGEX = re.compile(r'(?:(\S*\d+\S*))?(.*)')
ACCOUNT_CODE_REGEX = re.compile(r'^[A-Za-z0-9.]+$')
bypass_token = object()

class AccountAccount(models.Model):
    _inherit = 'account.account'

    report_code = fields.Char(
        compute="_compute_report_code",
        store=True,
    )

    active = fields.Boolean(string="Active",default=True, copy=False)
    is_cash_rounding = fields.Boolean(string="Disable Budget Code",copy=False,default=False)
    subgroup = fields.Many2one('account.subgroup',string='SubGroup',company_dependent = True)

    group_id = fields.Many2one('account.group', compute='_compute_account_group',search='_search_account_group',
                               help="Account prefixes can determine account groups.")

    def _search_account_group(self, operator, value):
        if operator not in ('=', '!=', 'in', 'not in'):
            raise NotImplementedError(
                "Operator %s is not supported for group_id" % operator
            )

        if not value:
            return [('id', 'in', [])] if operator in ('=', 'in') else []

        if isinstance(value, int):
            group_ids = [value]
        else:
            group_ids = list(value)

        groups = self.env['account.group'].browse(group_ids).exists()

        if not groups:
            return [('id', 'in', [])] if operator in ('=', 'in') else []

        # Use the active company's root company,
        # exactly like Odoo's standard _compute_account_group().
        root_company = self.env.company.root_id

        accounts = self.with_company(self.env.company).sudo().search([])

        matching_account_ids = []

        for account in accounts:
            code = account.code
            if not code:
                continue

            matching_groups = groups.filtered(
                lambda group:
                    group.company_id == root_company
                    and group.code_prefix_start <= code[:len(group.code_prefix_start)]
                    and group.code_prefix_end >= code[:len(group.code_prefix_end)]
            )

            if matching_groups:
                matching_group = matching_groups.sorted(
                    key=lambda g: (-len(g.code_prefix_start), g.id)
                )[0]

                if matching_group.id in group_ids:
                    matching_account_ids.append(account.id)

        if operator in ('=', 'in'):
            return [('id', 'in', matching_account_ids)]

        return [('id', 'not in', matching_account_ids)]

    @api.depends_context('company')
    @api.depends('code')
    def _compute_account_group(self):
        accounts_with_code = self.filtered(lambda a: a.code)

        (self - accounts_with_code).group_id = False

        if not accounts_with_code:
            return

        codes = accounts_with_code.mapped('code')
        account_code_values = SQL(','.join(['(%s)'] * len(codes)), *codes)
        results = self.env.execute_query(SQL(
            """
                 SELECT DISTINCT ON (account_code.code)
                        account_code.code,
                        agroup.id AS group_id
                   FROM (VALUES %(account_code_values)s) AS account_code (code)
              LEFT JOIN account_group agroup
                     ON agroup.code_prefix_start <= LEFT(account_code.code, char_length(agroup.code_prefix_start))
                        AND agroup.code_prefix_end >= LEFT(account_code.code, char_length(agroup.code_prefix_end))
                        AND agroup.company_id = %(root_company_id)s
               ORDER BY account_code.code, char_length(agroup.code_prefix_start) DESC, agroup.id
            """,
            account_code_values=account_code_values,
            root_company_id=self.env.company.root_id.id,
        ))
        group_by_code = dict(results)

        for account in accounts_with_code:
            account.group_id = group_by_code[account.code]

    @api.onchange('group_id')
    def update_alt_group_id(self):
        for line in self:
            if line.group_id:
                line.alt_group_id = line.group_id

    @api.depends("code")
    def _compute_report_code(self):
        for rec in self:
            rec.report_code = rec.code

    @api.model
    def cron_sync_report_code(self):
        self.search([]).action_sync_report_code()

    @api.constrains('opening_debit', 'opening_credit')
    def _check_opening_credit_balance(self):
        for line in self.filtered(lambda a: a.opening_debit !=0 or a.opening_credit !=0):
            if line.company_id.account_opening_move_id.filtered(lambda s: s.state in ['posted']):
                raise UserError(_("Opening Balance for %s is already posted.")
                    %line.company_id.name)

    # @api.model
    # def _load_precommit_update_opening_move(self):
    #     """ precommit callback to recompute the opening move according the opening balances that changed.
    #     This is particularly useful when importing a csv containing the 'opening_balance' column.
    #     In that case, we don't want to use the inverse method set on field since it will be
    #     called for each account separately. That would be quite costly in terms of performances.
    #     Instead, the opening balances are collected and this method is called once at the end
    #     to update the opening move accordingly.
    #     """
    #     data = self._cr.precommit.data.pop('import_account_opening_balance', {})
    #     accounts = self.browse(data.keys())
    #     accounts_per_company = defaultdict(lambda: self.env['account.account'])
    #     for account in accounts:
    #         accounts_per_company[account.company_id] |= account
    #     for company, company_accounts in accounts_per_company.items():
    #         if self.opening_debit == 0 and self.opening_credit ==0:
    #             continue
    #         if company_accounts.company_id.account_opening_move_id.journal_id.is_opening_balance:
    #         # if company_accounts.company_id.account_opening_move_id.state in ['draft']:
    #             # pdb.set_trace()
    #             if self in company_accounts.company_id.account_opening_move_id.line_ids.mapped('account_id'):
    #                 company._update_opening_move({account: data[account.id] for account in company_accounts})
    #     self.env.flush_all()

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get("skip_subgroup_sync"):
            for rec in self:
                if rec.subgroup:
                    # add account to subgroup without wiping existing ones
                    rec.subgroup.with_context(skip_subgroup_sync=True).write({
                        'account_id': [(4, rec.id)]
                    })
                else:
                    # if subgroup cleared, remove it from any subgroup M2M
                    groups = self.env['account.subgroup'].sudo().search([('account_id', 'in', rec.id)])
                    for grp in groups:
                        grp.with_context(skip_subgroup_sync=True).write({
                            'account_id': [(3, rec.id)]
                        })
        return res

    # class MailMessage(models.Model):
    #     _inherit = 'mail.message'
    #
    #     @api.ondelete(at_uninstall=True)
    #     def _except_audit_log(self):
    #         if self.env.context.get('bypass_audit') is bypass_token:
    #             return
    #         to_check = self
    #         partner_message = self.filtered(lambda m: m.account_audit_log_partner_id)
    #         if partner_message:
    #             # The audit trail uses the cheaper check on `customer_rank`, but that field could be set
    #             # without actually having an invoice linked (i.e. creation of the contact through the
    #             # Invoicing/Customers menu)
    #             has_related_move = self.env['account.move'].sudo().search_count([
    #                 ('partner_id', 'in', partner_message.account_audit_log_partner_id.ids),
    #                 ('company_id.check_account_audit_trail', '=', True),
    #             ], limit=1)
    #             if not has_related_move:
    #                 to_check -= partner_message
    #         for message in to_check:
    #             if message.show_audit_log and not (
    #                     message.account_audit_log_move_id
    #                     and not message.account_audit_log_move_id.posted_before
    #             ):
    #                 pass
    #                 # raise UserError(_("You cannot remove parts of the audit trail. Archive the record instead."))
    #
    #
