from odoo import api, models, fields, _
from odoo.tools.translate import _
from odoo.exceptions import ValidationError, AccessError, UserError
import math
import pdb
import calendar
import datetime
import logging
from odoo import tools
import time
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from time import gmtime, strftime
from dateutil import rrule


class ParticularLedgerMonthlyReport(models.AbstractModel):
    _name = 'report.account_ledger_balance.balance_monthly_report'

    def _get_account_id(self, account_id):
        account_id = data['form']['account_id'][0]
        return account_id

    def _get_period_date_from(self, data):
        date_from = data['form']['date_from']
        return date_from

    def get_account_data(self, o):
        import datetime
        dt1 = datetime.datetime.strptime(o.date_from, '%Y-%m-%d')
        dt2 = datetime.datetime.strptime(o.date_to, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
        analytic_account_ids = o.analytic_account_ids.ids
        journals = o.journal_ids.ids
        date1 = dt1 - timedelta(days=1)
        lines = {}
        query1 = """
                SELECT l.date,l.name as name, l.credit,l.debit,l.balance as balance,l.move_id,m.name as move
                FROM account_move_line l
                JOIN account_move m ON (l.move_id=m.id)
                where 
                    l.account_id=%s and l.journal_id in %s and m.state in ('posted') and l.date>=%s and l.date<=%s
                """
        query_params1 = (account_id, tuple(o.journal_ids.ids), o.date_from, o.date_to)
        if account_id and not partner and not analytic_account_ids:
            query1 += """ group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance
                        order by l.date,l.id,l.move_id; """
        if account_id and partner and not analytic_account_ids:
            query1 += """ and l.partner_id = %s 
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
            query_params1 += (tuple(o.partner_id.ids))
        if account_id and partner and analytic_account_ids:
            query1 += """ and l.partner_id = %s and l.analytic_account_id in %s
                        group by l.date,l.name,l.move_id,l.id,l.credit,l.debit,m.name,l.balance,l.partner_id,l.analytic_account_id
                        order by l.date,l.id,l.move_id,l.partner_id;"""
            query_params1 += (tuple(o.partner_id.ids), tuple(o.analytic_account_ids.ids))
        data_get = self.env.cr.execute(query1, query_params1)
        lines = self.env.cr.dictfetchall()
        return lines

    def get_period_bal_debit(self, o):
        import datetime
        dt1 = datetime.datetime.strptime(o.date_from, '%Y-%m-%d')
        dt2 = datetime.datetime.strptime(o.date_to, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
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
        if account_id and partner and not analytic_account_ids:
            query1 += """ and l.partner_id = %s """
            query_params1 += (tuple(o.partner_id.ids))
        if account_id and partner and analytic_account_ids:
            query1 += """ and l.partner_id = %s and l.analytic_account_id in %s"""
            query_params1 += (tuple(o.partner_id.ids), tuple(o.analytic_account_ids.ids))
        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['debit'] > 0:
                r['debit'] = r['debit']
            else:
                r['debit'] = 0.0
        return r['debit']

    def get_period_bal_credit(self, o):
        import datetime
        dt1 = datetime.datetime.strptime(o.date_from, '%Y-%m-%d')
        dt2 = datetime.datetime.strptime(o.date_to, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
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
        if account_id and partner and not analytic_account_ids:
            query1 += """ and l.partner_id = %s """
            query_params1 += (tuple(o.partner_id.ids))
        if account_id and partner and analytic_account_ids:
            query1 += """ and l.partner_id = %s and l.analytic_account_id in %s"""
            query_params1 += (tuple(o.partner_id.ids), tuple(o.analytic_account_ids.ids))
        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['credit'] > 0:
                r['credit'] = r['credit']
            else:
                r['credit'] = 0.0
        return r['credit']

    def get_open_bal_debit(self, o):
        import datetime
        date1 = datetime.datetime.strptime(o.date_from, '%Y-%m-%d')
        dt1 = date1 - timedelta(days=1)
        account_id = o.account_id.id
        partner = o.partner_id.id
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
        if account_id and partner and not analytic_account_ids:
            query1 += """ and l.partner_id = %s """
            query_params1 += (tuple(o.partner_id.ids))
        if account_id and partner and analytic_account_ids:
            query1 += """ and l.partner_id = %s and l.analytic_account_id in %s"""
            query_params1 += (tuple(o.partner_id.ids), tuple(o.analytic_account_ids.ids))
        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['debit'] > 0:
                r['debit'] = r['debit']
            else:
                r['debit'] = 0.0
        return r['debit']

    def get_open_bal_credit(self, o):
        import datetime
        date1 = datetime.datetime.strptime(o.date_from, '%Y-%m-%d')
        dt1 = date1 - timedelta(days=1)
        account_id = o.account_id.id
        partner = o.partner_id.id
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
        if account_id and partner and not analytic_account_ids:
            query1 += """ and l.partner_id = %s """
            query_params1 += (tuple(o.partner_id.ids))
        if account_id and partner and analytic_account_ids:
            query1 += """ and l.partner_id = %s and l.analytic_account_id in %s"""
            query_params1 += (tuple(o.partner_id.ids), tuple(o.analytic_account_ids.ids))
        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['credit'] > 0:
                r['credit'] = r['credit']
            else:
                r['credit'] = 0.0
        return r['credit']

    def get_closing_balance_end(self, o):
        import datetime
        dt1 = datetime.datetime.strptime(o.date_from, '%Y-%m-%d')
        dt2 = datetime.datetime.strptime(o.date_to, '%Y-%m-%d')
        account_id = o.account_id.id
        partner = o.partner_id.id
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
        if account_id and partner and not analytic_account_ids:
            query1 += """ and l.partner_id = %s """
            query_params1 += (tuple(o.partner_id.ids))
        if account_id and partner and analytic_account_ids:
            query1 += """ and l.partner_id = %s and l.analytic_account_id in %s"""
            query_params1 += (tuple(o.partner_id.ids), tuple(o.analytic_account_ids.ids))
        data_get = self.env.cr.execute(query1, query_params1)
        data = self.env.cr.dictfetchall()
        for r in data:
            if r['balance'] > 0:
                r['balance'] = r['balance']
            else:
                pass
        return r['balance']

    @api.model
    def _get_report_values(self, docids, data=None):
        if not data.get('form') or not self.env.context.get('active_model'):
            raise UserError(_("Form content is missing, this report cannot be printed."))

        self.model = self.env.context.get('active_model')
        docs = self.env[self.model].browse(self.env.context.get('active_id'))
        return {
            'doc_ids': self.ids,
            'doc_model': self.model,
            'docs': docs,
            'account_id': self._get_account_id,
            'date_from': self._get_period_date_from,
            'get_account_data': self.get_account_data,
            'get_period_bal_debit': self.get_period_bal_debit,
            'get_period_bal_credit': self.get_period_bal_credit,
            'get_open_bal_debit': self.get_open_bal_debit,
            'get_open_bal_credit': self.get_open_bal_credit,
            'get_closing_balance': self.get_closing_balance_end,
        }
