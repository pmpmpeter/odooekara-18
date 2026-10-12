# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

import datetime

from odoo import models, fields, _
from odoo.tools import SQL
from odoo.tools.misc import format_date

from dateutil.relativedelta import relativedelta
from itertools import chain

from odoo.exceptions import UserError
from odoo.osv import expression

from datetime import timedelta
from collections import defaultdict
from copy import deepcopy



class AgedPartnerBalanceCustomHandlerInherit(models.AbstractModel):
    _inherit = 'account.aged.partner.balance.report.handler'

    def _aged_partner_report_custom_engine_common(
        self,
        options,
        internal_type,
        current_groupby,
        next_groupby,
        offset=0,
        limit=None,
    ):
        """
        Ekara Odoo 18 customization.

        Replicates the employee partner exclusion
        implemented in Odoo 17 for:

        - Aged Payable
        - Aged Receivable

        Preserves Odoo 18 standard aging calculations.
        """

        employee_partner_ids = (
            self.env['hr.employee']
            .sudo()
            .search([
                ('work_contact_id', '!=', False),
            ])
            .mapped('work_contact_id')
            .ids
        )

        # Apply exclusion only if employee partners exist,
        # matching the Odoo 17 implementation.
        if employee_partner_ids and internal_type in (
            'liability_payable',
            'asset_receivable',
        ):
            return super(
                AgedPartnerBalanceCustomHandlerInherit,
                self.with_context(
                    ekara_aged_employee_partner_ids=tuple(
                        employee_partner_ids
                    )
                ),
            )._aged_partner_report_custom_engine_common(
                options,
                internal_type,
                current_groupby,
                next_groupby,
                offset=offset,
                limit=limit,
            )

        return super()._aged_partner_report_custom_engine_common(
            options,
            internal_type,
            current_groupby,
            next_groupby,
            offset=offset,
            limit=limit,
        )

class AccountReport(models.Model):
    _inherit = 'account.report'

    def _get_report_query(
        self,
        options,
        date_scope,
        domain=None,
    ):
        """
        Apply Ekara employee exclusion to Aged
        Payable and Aged Receivable query domains.

        No effect on Partner Ledger or other reports
        unless the custom context is explicitly set.
        """

        domain = list(domain or [])

        employee_partner_ids = self.env.context.get(
            'ekara_aged_employee_partner_ids'
        )

        if employee_partner_ids:
            domain.extend([
                ('partner_id', '!=', False),
                ('partner_id', 'not in', list(employee_partner_ids)),
            ])

        return super()._get_report_query(
            options,
            date_scope,
            domain=domain,
        )

class PartnerLedgerCustomHandlerInherit(models.AbstractModel):
    _inherit = 'account.partner.ledger.report.handler'

    def _get_query_sums(self, report, options) -> SQL:
        """
        Ekara Customization - Odoo 18

        Exclude employee work-contact partners from Partner Ledger,
        reproducing the Odoo 17 Ekara customization.

        Also excludes journal entries without a partner, matching
        the original PostgreSQL NOT IN behavior.

        Retains Odoo 18 standard:
            - Currency conversion
            - Column grouping
            - Reconciliation filtering
            - Zero-balance filtering
            - Date filtering
        """

        queries = []

        # Get employee work-contact partner IDs.
        employee_partner_ids = self.env['hr.employee'].sudo().search([
            ('work_contact_id', '!=', False),
        ]).mapped('work_contact_id').ids

        # Build report queries for each column group.
        for column_group_key, column_group_options in (
            report._split_options_per_column_group(options).items()
        ):

            # Base report domain.
            domain = []

            # Ekara customization:
            # Replicate Odoo 17 employee exclusion.
            if employee_partner_ids:
                domain.extend([
                    ('partner_id', '!=', False),
                    ('partner_id', 'not in', employee_partner_ids),
                ])

            # Odoo 18 report query.
            query = report._get_report_query(
                column_group_options,
                'from_beginning',
                domain=domain,
            )

            date_from = options['date']['date_from']

            queries.append(SQL(
                """
                (
                    WITH partner_sums AS (
                        SELECT
                            account_move_line.partner_id
                                AS groupby,

                            %(column_group_key)s
                                AS column_group_key,

                            SUM(%(debit_select)s)
                                AS debit,

                            SUM(%(credit_select)s)
                                AS credit,

                            SUM(%(balance_select)s)
                                AS amount,

                            SUM(%(balance_select)s)
                                AS balance,

                            BOOL_AND(account_move_line.reconciled)
                                AS all_reconciled,

                            MAX(account_move_line.date)
                                AS latest_date

                        FROM %(table_references)s

                        %(currency_table_join)s

                        WHERE %(search_condition)s

                        GROUP BY account_move_line.partner_id
                    )

                    SELECT *
                    FROM partner_sums

                    WHERE partner_sums.balance != 0
                       OR partner_sums.all_reconciled = FALSE
                       OR partner_sums.latest_date >= %(date_from)s
                )
                """,
                column_group_key=column_group_key,

                debit_select=report._currency_table_apply_rate(
                    SQL("account_move_line.debit")
                ),

                credit_select=report._currency_table_apply_rate(
                    SQL("account_move_line.credit")
                ),

                balance_select=report._currency_table_apply_rate(
                    SQL("account_move_line.balance")
                ),

                table_references=query.from_clause,

                currency_table_join=report._currency_table_aml_join(
                    column_group_options
                ),

                search_condition=query.where_clause,

                date_from=date_from,
            ))

        return SQL(' UNION ALL ').join(queries)
