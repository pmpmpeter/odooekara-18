# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountAccount(models.Model):
    _inherit = 'account.account'

    group_balance = fields.Float(
        string='Group Balance',
        compute='_compute_group_balance',
    )

    group_company_count = fields.Integer(
        string='Group Companies',
        compute='_compute_group_company_count',
    )

    def _get_group_balance_companies(self):
        """
        Companies which are mapped to this shared account
        and which the current user can access.
        """
        self.ensure_one()

        return self.company_ids & self.env.user.company_ids

    @api.depends('company_ids')
    def _compute_group_balance(self):
        """
        Calculate posted balance across all companies mapped
        to the shared account.

        This does NOT depend on the companies currently selected
        in the company switcher.
        """

        MoveLine = self.env['account.move.line']

        for account in self:
            companies = account._get_group_balance_companies()

            if not companies:
                account.group_balance = 0.0
                continue

            move_line_env = MoveLine.sudo().with_context(
                allowed_company_ids=companies.ids
            )

            move_lines = move_line_env.search([
                ('account_id', '=', account.id),
                ('parent_state', '=', 'posted'),
                ('company_id', 'in', companies.ids),
            ])

            account.group_balance = sum(
                move_lines.mapped('balance')
            )

    @api.depends('company_ids')
    def _compute_group_company_count(self):

        user_companies = self.env.user.company_ids

        for account in self:
            companies = account.company_ids & user_companies
            account.group_company_count = len(companies)

    def action_open_group_balance(self):
        """
        Open Group Journal Items.

        Unlike account.move.line, this temporary model is not
        restricted by the currently selected companies in the
        multi-company switcher.
        """

        self.ensure_one()

        companies = self._get_group_balance_companies()

        GroupLine = self.env['account.group.balance.line']

        # Remove old temporary lines created by this user.
        GroupLine.sudo().search([
            ('user_id', '=', self.env.uid),
        ]).unlink()

        if not companies:
            return {
                'type': 'ir.actions.act_window',
                'name': 'Group Journal Items',
                'res_model': 'account.group.balance.line',
                'view_mode': 'list',
                'domain': [('id', '=', False)],
            }

        # IMPORTANT:
        # sudo() is intentional here because account.move.line has
        # the standard multi-company record rule which uses the
        # companies currently selected in the company switcher.
        #
        # We still explicitly restrict the data to:
        #   1. this account
        #   2. posted entries
        #   3. account.company_ids
        #   4. companies accessible to the user
        move_lines = self.env['account.move.line'].sudo().search([
            ('account_id', '=', self.id),
            ('parent_state', '=', 'posted'),
            ('company_id', 'in', companies.ids),
        ], order='date desc, id desc')

        group_lines = GroupLine.sudo().create_from_move_lines(
            self,
            move_lines,
        )

        return {
            'type': 'ir.actions.act_window',
            'name': 'Group Journal Items',
            'res_model': 'account.group.balance.line',
            'view_mode': 'list',
            'views': [
                (
                    self.env.ref(
                        'account_group_balance.view_group_balance_line_tree'
                    ).id,
                    'list',
                ),
            ],
            'domain': [
                ('id', 'in', group_lines.ids),
                ('user_id', '=', self.env.uid),
            ],
            'context': {
                'default_account_id': self.id,
            },
        }

class AccountGroupBalanceLine(models.TransientModel):
    _name = 'account.group.balance.line'
    _description = 'Group Balance Journal Items'
    _order = 'date desc, id desc'

    user_id = fields.Many2one('res.users',string='User',default=lambda self: self.env.user,required=True,readonly=True)

    account_id = fields.Many2one('account.account',string='Account',readonly=True)

    company_id = fields.Many2one('res.company',string='Company',readonly=True)

    date = fields.Date(string='Date',readonly=True)

    journal_id = fields.Many2one('account.journal',string='Journal',readonly=True)

    move_id = fields.Many2one('account.move',string='Journal Entry',readonly=True)

    partner_id = fields.Many2one('res.partner',string='Partner',readonly=True)

    label = fields.Char(string='Label',readonly=True)

    company_currency_id = fields.Many2one('res.currency',string='Currency',related='company_id.currency_id',readonly=True)

    debit = fields.Float(string='Debit',readonly=True)

    credit = fields.Float(string='Credit',readonly=True)

    balance = fields.Float(string='Balance',readonly=True)

    @api.model
    def create_from_move_lines(self, account, move_lines):
        vals_list = []

        for line in move_lines:
            vals_list.append({
                'user_id': self.env.uid,
                'account_id': line.account_id.id,
                'company_id': line.company_id.id,
                'date': line.date,
                'journal_id': line.journal_id.id,
                'move_id': line.move_id.id,
                'partner_id': line.partner_id.id,
                'label': line.name,
                'debit': line.debit,
                'credit': line.credit,
                'balance': line.balance,
            })

        if not vals_list:
            return self.browse()

        return self.create(vals_list)