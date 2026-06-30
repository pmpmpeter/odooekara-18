from odoo import models, api, _, fields

class AccountJournalDashboardWizard(models.TransientModel):
    _name = "account.journal.wizard"

    liquidity_end_date = fields.Date(string="Date To", default=lambda self: fields.Date.today())
    journal_id = fields.Many2one("account.journal", string="Journal ID")

    def action_submit(self):
        self.journal_id.update({
            'liquidity_end_date':self.liquidity_end_date
        })
        self.journal_id._get_journal_dashboard_data_batched()
        return
