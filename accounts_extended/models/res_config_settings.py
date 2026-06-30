from odoo import api, fields, models, _, tools
from datetime import datetime

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    company_code = fields.Char('Code', related='company_id.company_code')
    tcs_limit = fields.Boolean('Enable TCS Limit', related='company_id.tcs_limit', readonly=False)
    tcs_limit_amount = fields.Float(
        'Maximum TCS Amount', related='company_id.tcs_limit_amount',
        help="By adding maximum limit amount will let users know about the TCS limit", readonly=False)
    tds_limit = fields.Boolean('Enable TDS Limit', related='company_id.tds_limit', readonly=False)
    tds_limit_amount = fields.Float(
        'Maximum TDS Amount', related='company_id.tds_limit_amount',
        help="By adding maximum limit amount will let users know about the TDS limit", readonly=False)
    tds_tax_id = fields.Many2one('account.tax', string="TDS Tax", required=False, related='company_id.tds_tax_id',
                                 readonly=False)
    tax_entity1 = fields.Many2one(string="Tax Entity1", related='company_id.tax_entity1', readonly=False)
    share1 = fields.Integer('Share %', related='company_id.share1', readonly=False)
    tax_entity2 = fields.Many2one(string="Tax Entity2", related='company_id.tax_entity2', readonly=False)
    share2 = fields.Integer('Share %', related='company_id.share2', readonly=False)
    crr_reminder_users = fields.Many2many(related='company_id.crr_reminder_users', string="CRR & CUR Reminder Users",
                                          help="Users who will receive monthly CRR & CUR reminders", readonly=False)
    po_threshold_amount = fields.Float(string="PO Threshold Amount", related='company_id.po_threshold_amount', readonly=False)
    brs_account_ids = fields.Many2many(
        'account.account',
        'brs_account_rel',  # relation table name
        'config_id',  # column for config
        'account_id',  # column for account
        string='BRS Accounts'
    )

    def set_values(self):
        super().set_values()
        self.env['ir.config_parameter'].sudo().set_param(
            'brs_account_ids',
            ','.join(map(str, self.brs_account_ids.ids))
        )

    def get_values(self):
        res = super().get_values()
        param = self.env['ir.config_parameter'].sudo().get_param('brs_account_ids')
        res.update(
            brs_account_ids=[(6, 0, list(map(int, param.split(','))))] if param else False
        )
        return res
    @api.model
    def send_crr_reminder(self):
        """Send CRR & CUR reminder emails on the 20th of each month."""
        today = datetime.today()
        if today.day != 20:
            return  # Ensure it runs only on the 20th

        companies = self.env['res.company'].search([])
        for company in companies:
            # param_key = 'monthly_crr_reminder_users_%s' % company.id
            user_ids = company.crr_reminder_users.ids
            if not user_ids:
                continue

            users = self.env['res.users'].sudo().browse(user_ids)
            for user in users:
                self._send_email(user, company)

    def _send_email(self, user, company):
        """Helper method to send email."""
        mail_template = self.env.ref('accounts_extended.crr_reminder_email_template')
        if mail_template:
            mail_template.sudo().send_mail(user.id, force_send=True)

class MultiApproval(models.Model):
    _inherit = "multi.approval"

    company_id = fields.Many2one('res.company',string="Company ID")
