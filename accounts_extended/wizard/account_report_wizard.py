# from duplicity.tempdir import default

from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountReportWizard(models.TransientModel):
    _name = 'account.report.wizard'
    _description = 'Account Report Wizard'

    date_from = fields.Date(string="Start Date", required=True, default='2020-01-01')
    date_to = fields.Date(string="End Date", required=True, default='2025-01-01')
    account_ids = fields.Many2many('account.account', string="Account", required=True)

    def add_all_accounts(self):
        self.account_ids = self.env['account.account'].search([]).ids

    def check_date_range(self):
        if self.date_from > self.date_to:
            raise ValidationError(_('End Date should be greater than Start Date.'))

    def print_xlsx(self):
        print("xlsx")
        self.check_date_range()

        date_from = self.date_from
        date_to = self.date_to
        account_ids = self.account_ids.ids
        datas = {
            'id': self.id,
            'start_date': date_from,
            'end_date': date_to,
            'account_ids': account_ids,
        }
        return self.env.ref('accounts_extended.action_coa_report_xlsx').report_action(self, data=datas)
