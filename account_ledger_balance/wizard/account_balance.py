from odoo import api, models, fields, _
from odoo.tools.translate import _
from odoo.exceptions import ValidationError, AccessError, UserError
from dateutil.parser import parse
import math
import time
import pdb
import calendar
import logging
from odoo import tools
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from time import gmtime, strftime

MONTH_LIST = [('1', 'Jan'), ('2', 'Feb'), ('3', 'Mar'),
              ('4', 'Apr'), ('5', 'May'), ('6', 'Jun'),
              ('7', 'Jul'), ('8', 'Aug'), ('9', 'Sep'),
              ('10', 'Oct'), ('11', 'Nov'), ('12', 'Dec')]


class AccountLedgerReportLines(models.Model):
    _name = 'ledger.monthly.report.lines'
    _order = 'date_from'

    @api.onchange('date_from', 'date_to')
    def _onchange_date_from(self):
        for record in self:
            month = str(int(parse(str(record.date_from)).strftime('%m')))
            self.month = month
            self.year = int(parse(str(record.date_from)).strftime('%Y'))

    wizard_id = fields.Many2one('accounting.balance.report', string='Selected Indent')
    account_id = fields.Many2one('account.account', 'Account')
    partner_id = fields.Many2one('res.partner', 'Partner')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    date_from = fields.Date("From Date")
    date_to = fields.Date("To Date")
    debit = fields.Float('Debit')
    credit = fields.Float('Credit')
    balance = fields.Float('Balance')
    cl_balance = fields.Float('Closing Balance')
    op_balance = fields.Float('Opening Balance')
    month = fields.Selection(MONTH_LIST, string='Month')
    year = fields.Integer('Year')
    partner_ids = fields.Many2many('res.partner', string="Partners", related='wizard_id.partner_ids')
    analytic_account_ids = fields.Many2many('account.analytic.account', string="Analytic Account",
                                            related='wizard_id.analytic_account_ids')
    journal_ids = fields.Many2many('account.journal', string='Journals', related='wizard_id.journal_ids')
    company_id = fields.Many2one('res.company', related='wizard_id.company_id')

    def _get_account_id(self, data):
        account_id = data['form']['account_id'][0]
        return account_id

    def _get_period_date_from(self, data):
        date_from = data['form']['date_from']
        return date_from

    def get_account_data(self, o):
        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        date1 = dt1 - timedelta(days=1)
        lines = {}
        query1 = """
                SELECT to_char(l.date, 'DD/MM/YYYY') as date,l.name as name, l.credit,l.debit,l.balance as balance,l.move_id,m.name as move
                FROM account_move_line l
                JOIN account_move m ON (l.move_id=m.id)
                where 
                    l.account_id=%s and l.journal_id in %s and m.state in ('posted') and l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)

        if account_id and not partners and not analytic_account_ids:
            query1 += """ group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance
                        order by l.date,l.id,l.move_id; """

        elif account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """ and l.partner_id = %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

            elif len(partners) > 1:
                query1 += """ and l.partner_id in %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """ and l.analytic_account_id = %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """ and l.analytic_account_id in %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """ and l.partner_id = %s and l.analytic_account_id = %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """ and l.partner_id in %s and l.analytic_account_id in %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """ and l.partner_id in %s and l.analytic_account_id = %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """ and l.partner_id = %s and l.analytic_account_id in %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        lines = self.env.cr.dictfetchall()
        return lines

    def get_period_bal_debit(self, o):
        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        query1 = """
                SELECT sum(l.debit) as debit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where 
                l.account_id = %s and l.journal_id in %s and m.state in ('posted') and\
                l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)
        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))


        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['debit']:
                if r['debit'] > 0:
                    r['debit'] = r['debit']
                else:
                    r['debit'] = 0.0
            else:
                r['debit'] = 0.0
        return r['debit']

    def get_period_bal_credit(self, o):
        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        query1 = """
                SELECT sum(l.credit) as credit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where 
                l.account_id = %s and l.journal_id in %s and m.state in ('posted') and\
                l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)
        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))


        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['credit']:
                if r['credit'] > 0:
                    r['credit'] = r['credit']
                else:
                    r['credit'] = 0.0
            else:
                r['credit'] = 0.0
        return r['credit']

    def get_open_bal_debit(self, o):
        d1 = str(o.date_from)
        date1 = datetime.strptime(d1, '%Y-%m-%d')
        dt1 = date1 - timedelta(days=1)
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        data = {}
        query1 = """
                SELECT sum(l.debit) as debit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where l.account_id = %s and l.journal_id in %s and l.date <= %s\
                and m.state in ('posted')
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), dt1.strftime('%Y-%m-%d'))

        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()

        for r in data:
            if r['debit']:
                if r['debit'] > 0:
                    r['debit'] = r['debit']
                else:
                    r['debit'] = 0.0
            else:
                r['debit'] = 0.0
        return r['debit']

    def get_open_bal_credit(self, o):
        d1 = str(o.date_from)
        date1 = datetime.strptime(d1, '%Y-%m-%d')
        dt1 = date1 - timedelta(days=1)
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        data = {}
        query1 = """
                SELECT sum(l.credit) as credit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where l.account_id = %s and l.journal_id in %s and l.date <= %s\
                and m.state in ('posted')
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), dt1.strftime('%Y-%m-%d'))
        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()

        for r in data:
            if r['credit']:
                if r['credit'] > 0:
                    r['credit'] = r['credit']
                else:
                    r['credit'] = 0.0
            else:
                r['credit'] = 0.0
        return r['credit']

    def get_closing_balance_end(self, o):
        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        data = {}
        query1 = """
                SELECT sum(l.balance) as balance \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where l.account_id = %s and l.journal_id in %s and m.state in ('posted') and\
                and l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)
        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))


        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['balance']:
                if r['balance'] > 0:
                    r['balance'] = r['balance']
                else:
                    pass
            else:
                pass
        return r['balance']

    def check_monthly_report(self):
        return self.env.ref('account_ledger_balance.account_ledger_balance_monthly_report_wizard').report_action(self)

    def _print_monthly_report(self, data):
        data['form'].update(self.read(['account_id'])[0])
        account_id = data['form']['account_id'][0]
        return self.env['report'].get_action(self, 'account_ledger_balance.balance_monthly_report', data=data)


class AccountingBalanceReport(models.Model):
    _name = 'accounting.balance.report'
    _description = "Accounting Balance Report"
    _rec_name = 'account_id'
    # _sql_constraints = [
    #     ('account_id', 'unique(account_id)', 'The selected Account already exists.'),
    # ]

    account_id = fields.Many2one('account.account', 'Account', required=True)
    company_id = fields.Many2one('res.company', 'Company', default=lambda self: self.env.company)
    date_from = fields.Date("From Date")
    date_to = fields.Date("To Date")
    partner_id = fields.Many2one('res.partner', 'Partner')
    analytic_account_id = fields.Many2one('account.analytic.account', 'Analytic Account')
    current_fiscal_year = fields.Boolean('Current Fiscal Year',default=False)
    monthly_report_lines = fields.One2many('ledger.monthly.report.lines', 'wizard_id', string='Report Lines')
    analytic_account_ids = fields.Many2many('account.analytic.account', string="Analytic Account")
    partner_ids = fields.Many2many('res.partner', string="Partners")
    journal_ids = fields.Many2many('account.journal', string='Journals', required=True, \
                                   default=lambda self: self.env['account.journal'].search([]))

    @api.onchange('partner_id')
    def _get_analytic_account_id_domain(self):
        res = dict()
        project_ids = []
        if self.partner_id:
            domain = [('account_id', '=', self.account_id.id), ('partner_id', '=', self.partner_id.id), \
                      ('move_id.state', '=', 'posted')]
            move_lines = self.env['account.move.line'].search(domain)
            for move in move_lines:
                if move.analytic_account_id:
                    project_ids.append(move.analytic_account_id.id)
        res['domain'] = {'analytic_account_ids': [('id', 'in', project_ids)]}
        return res

    @api.constrains('date_from', 'date_to', 'account_id')
    def _check_report_duplicattion(self):
        for record in self:
            if record.account_id:
                report_ids = self.search([('account_id', '=', record.account_id.id), ('id', '!=', record.id)])
                for data in report_ids:
                    if data.date_from and record.date_from and data.date_to:
                        if data.date_from <= record.date_from <= data.date_to:
                            raise UserError(
                                _('The report for %s for selected date already exists.') % (
                                        '(' + record.account_id.display_name + ')'))
                    if data.date_from and record.date_to and data.date_to:
                        if data.date_from <= record.date_to <= data.date_to:
                            raise UserError(
                                _('The report for %s for selected date already exists.') % (
                                        '(' + record.account_id.display_name + ')'))
                    if data.account_id == record.account_id:
                        raise UserError(
                            _('The selected account %s already exists.') % ('(' + record.account_id.display_name + ')'))

    def name_get(self):
        res = []
        if self.date_from and self.date_to:
            begin = parse(str(self.date_from))
            end = parse(str(self.date_to))
            for record in self:
                if record.account_id:
                    name = str(record.account_id.code) + ' - ' + str(record.account_id.name) \
                           + ' from ' + begin.strftime("%d/%m/%Y") + ' - ' + end.strftime("%d/%m/%Y")
                    res.append((record.id, name))
        return res

    def last_day_of_month(self, any_day):
        next_month = any_day.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)

    def monthlist(self, date_from, date_end):
        begin = parse(str(self.date_from))
        end = parse(str(self.date_to))
        result = []
        while True:
            if begin.month == 12:
                next_month = begin.replace(year=begin.year + 1, month=1, day=1)
            else:
                next_month = begin.replace(month=begin.month + 1, day=1)
            if next_month > end:
                break
            result.append([begin.strftime("%Y-%m-%d"), self.last_day_of_month(begin).strftime("%Y-%m-%d")])
            begin = next_month
        result.append([begin.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")])
        return result

    def get_account_data(self, o):
        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        date1 = dt1 - timedelta(days=1)
        lines = {}
        query1 = """
                SELECT to_char(l.date, 'DD/MM/YYYY') as date,l.name as name, l.credit,l.debit,l.balance as balance,l.move_id,m.name as move
                FROM account_move_line l
                JOIN account_move m ON (l.move_id=m.id)
                where 
                    l.account_id=%s and l.journal_id in %s and m.state in ('posted') and l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)

        if account_id and not partners and not analytic_account_ids:
            query1 += """ group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance
                        order by l.date,l.id,l.move_id; """

        elif account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """ and l.partner_id = %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

            elif len(partners) > 1:
                query1 += """ and l.partner_id in %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """ and l.analytic_account_id = %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """ and l.analytic_account_id in %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """ and l.partner_id = %s and l.analytic_account_id = %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """ and l.partner_id in %s and l.analytic_account_id in %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """ and l.partner_id in %s and l.analytic_account_id = %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """ and l.partner_id = %s and l.analytic_account_id in %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        lines = self.env.cr.dictfetchall()
        return lines

    @api.onchange('account_id', 'date_from', 'date_to')
    def _get_lines(self):
        if self.account_id:
            journals = self.env['account.journal'].search([])
            self.update({'journal_ids': journals.ids})

        if not self.account_id:
            self.update({'journal_ids': [(5,)]})

        if self.date_from and not self.date_to:
            self.monthly_report_lines = False
        if self.date_to and not self.date_from:
            self.monthly_report_lines = False
        if self.date_from and self.date_to:
            if self.date_to < self.date_from:
                raise UserError(_('Alert !! From date cannot be behind Date to.Please select the dates properly.'))
            self.monthly_report_lines = False
            # pdb.set_trace()parse(self.date_from)
            dt1 = parse(str(self.date_from))
            dt2 = parse(str(self.date_to))
            date_list = self.monthlist(self.date_from, self.date_to)
            for m in range(len(date_list)):
                a = date_list[m]
                date_from = a[0]
                date_to = a[1]
                date1 = parse(str(date_from)) - timedelta(days=1)
                month = str(int(parse(str(date_from)).strftime('%m')))
                year = int(parse(str(date_from)).strftime('%Y'))
                data_1 = [('month', '=', month), ('year', '=', year), ('account_id', '=', self.account_id.id),
                          ('wizard_id', '=', self.id)]
                if not self.env['ledger.monthly.report.lines'].search(data_1):
                    self.monthly_report_lines += self.monthly_report_lines.new({
                        'date_from': date_from,
                        'date_to': date_to,
                        'account_id': self.account_id.id,
                        'credit': 0,
                        'debit': 0,
                        'balance': 0,
                        'cl_balance': 0,
                        'op_balance': 0,
                        'month': month,
                        'year': year,
                        # 'analytic_account_ids':self.analytic_account_ids.ids,
                        # 'journal_ids':self.journal_ids.ids,
                    })

    def get_open_bal_debit(self, o):
        st_date = str(o.date_from)
        date1 = datetime.strptime(st_date, '%Y-%m-%d')
        dt1 = date1 - timedelta(days=1)
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        data = {}
        query1 = """
                SELECT sum(l.debit) as debit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where l.account_id = %s and l.journal_id in %s and l.date <= %s\
                and m.state in ('posted')
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), dt1.strftime('%Y-%m-%d'))

        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['debit']:
                if r['debit'] > 0:
                    r['debit'] = r['debit']
                else:
                    r['debit'] = 0.0
            else:
                r['debit'] = 0.0
        return r['debit']

    def get_open_bal_credit(self, o):
        st_date = str(o.date_from)
        date1 = datetime.strptime(st_date, '%Y-%m-%d')
        dt1 = date1 - timedelta(days=1)
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        data = {}
        query1 = """
                SELECT sum(l.credit) as credit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where l.account_id = %s and l.journal_id in %s and l.date <= %s\
                and m.state in ('posted')
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), dt1.strftime('%Y-%m-%d'))

        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['credit']:
                if r['credit'] > 0:
                    r['credit'] = r['credit']
                else:
                    r['credit'] = 0.0
            else:
                r['credit'] = 0.0
        return r['credit']

    def get_period_bal_debit(self, o):

        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        query1 = """
                SELECT sum(l.debit) as debit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where 
                l.account_id = %s and l.journal_id in %s and m.state in ('posted') and\
                l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)

        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['debit']:
                if r['debit'] > 0:
                    r['debit'] = r['debit']
                else:
                    r['debit'] = 0.0
            else:
                r['debit'] = 0.0
        return r['debit']

    def get_period_bal_credit(self, o):
        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        query1 = """
                SELECT sum(l.credit) as credit \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where 
                l.account_id = %s and l.journal_id in %s and m.state in ('posted') and\
                l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)

        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))

        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))


            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['credit']:
                if r['credit'] > 0:
                    r['credit'] = r['credit']
                else:
                    r['credit'] = 0.0
            else:
                r['credit'] = 0.0
        return r['credit']

    def update_ledger_report(self):
        for record in self:
            if record.account_id:
                if record.date_from and record.date_to:
                    if record.date_to < record.date_from:
                        raise UserError(
                            _('Alert !! From date cannot be behind Date to.Please select the dates properly.'))
                    for line in record.monthly_report_lines:
                        my_list1 = []
                        line.partner_id = self.partner_id.id
                        debit = credit = balance = cl_balance = op_balance = 0
                        dt1 = parse(str(line.date_from))
                        dt2 = parse(str(line.date_to))
                        date_list = self.monthlist(line.date_from, line.date_to)
                        date_from = line.date_from
                        date_to = line.date_to
                        date_from_con = parse(str(date_from))
                        date1 = date_from_con - timedelta(days=1)
                        domain1 = [('account_id', '=', self.account_id.id), ('date', '>=', date_from), \
                                   ('date', '<=', date_to), ('move_id.state', '=', 'posted')]
                        if line.partner_ids:
                            domain1 += [('partner_id', 'in', line.partner_ids.ids)]
                        if line.analytic_account_ids:
                            domain1 += [('analytic_account_id', 'in', line.analytic_account_ids.ids)]
                        if line.journal_ids:
                            domain1 += [('journal_id', 'in', line.journal_ids.ids)]
                        cr_dr_lines = self.env['account.move.line'].search(domain1)
                        for move_line in cr_dr_lines:
                            debit += move_line.debit
                            credit += move_line.credit
                            balance += move_line.balance
                        #####Opening Balance###
                        domain2 = [('account_id', '=', self.account_id.id), ('date', '<=', date1), \
                                   ('move_id.state', '=', 'posted')]
                        if line.partner_ids:
                            domain2 += [('partner_id', 'in', line.partner_ids.ids)]
                        if line.analytic_account_ids:
                            domain2 += [('analytic_account_id', 'in', line.analytic_account_ids.ids)]
                        if line.journal_ids:
                            domain2 += [('journal_id', 'in', line.journal_ids.ids)]
                        cr_dr_lines2 = self.env['account.move.line'].search(domain2)
                        for move_line2 in cr_dr_lines2:
                            op_balance += move_line2.balance
                        cl_balance = op_balance + debit - credit
                        line.write({
                            'account_id': self.account_id.id,
                            'credit': credit,
                            'debit': debit,
                            'balance': balance,
                            'cl_balance': cl_balance,
                            'op_balance': op_balance,
                            # 'partner_id': self.partner_id.id,
                        })
        return True

    def get_closing_balance(self, o):
        d1 = str(o.date_from)
        d2 = str(o.date_to)
        dt1 = datetime.strptime(d1, '%Y-%m-%d')
        dt2 = datetime.strptime(d2, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        partners = o.partner_ids.ids
        analytic_account_id = o.analytic_account_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        data = {}
        query1 = """
                SELECT sum(l.balance) as balance \
                from account_move_line l \
                JOIN account_move m ON (l.move_id=m.id)\
                where l.account_id = %s and l.journal_id in %s and m.state in ('posted') and\
                l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)

        if account_id and partners and not analytic_account_ids:
            if len(partners) == 1:
                query1 += """and l.partner_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


            elif len(partners) > 1:
                query1 += """and l.partner_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids))


        elif account_id and not partners and analytic_account_ids:
            if len(analytic_account_ids) == 1:
                query1 += """and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

            elif len(analytic_account_ids) > 1:
                query1 += """and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.analytic_account_ids.ids))

        elif account_id and partners and analytic_account_ids:
            if len(partners) == 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) > 1 and len(analytic_account_ids) == 1:
                query1 += """and l.partner_id in %s and l.analytic_account_id = %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

            elif len(partners) == 1 and len(analytic_account_ids) > 1:
                query1 += """and l.partner_id = %s and l.analytic_account_id in %s"""
                query_params1 = (*query_params1, tuple(o.partner_ids.ids), tuple(o.analytic_account_ids.ids))

        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['balance']:
                if r['balance'] > 0:
                    r['balance'] = r['balance']
                else:
                    r['balance'] = 0.0
            else:
                r['balance'] = 0.0
        return r['balance']

    def check_report(self):
        return self.env.ref('account_ledger_balance.account_ledger_balance_report_wizard').report_action(self)

    # def account_ledger_balance_report(self):
    #     return self.env.ref('account_ledger_balance.account_ledger_balance_monthly_report_xlsx').report_action(self)

    def account_ledger_balance_report(self):
        data = {
            'ids': self.ids,
            'journal': self.journal_ids,
            'model': self._name,
            'account_id': self.account_id
        }
        action = self.env.ref(
            'account_ledger_balance.account_ledger_balance_monthly_report_xlsx').report_action(self, data=data)
        self.env.ref(
            'account_ledger_balance.account_ledger_balance_monthly_report_xlsx').name = 'Ledger %s - %s Report' % (
            self.account_id.code, self.account_id.name)
        action.update({'close_on_report_download': True})
        return action
