from odoo import models, fields, api
from datetime import datetime,timedelta


class BudgetRevisionWizard(models.TransientModel):
    _name = 'budget.revision.wizard'
    _description = 'Budget Revision Wizard'

    reason = fields.Char(string="Revision Reason", required=True)
    budget_id = fields.Many2one('budget.analytic',string='Budget')

    def action_confirm_revision(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')  # Get the active budget record
        record = self.env[active_model].browse(active_id)
        if active_id:
            budget = self.env['budget.analytic'].browse(active_id)
            self.budget_id = budget.id
            # Get current user and timestamp
            user_name = self.env.user.name  # Current user's name
            current_time = datetime.now()  # Current date and time
            revision_time = (current_time + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')  # Add 5:30 hours
            # Calculate the new revision number
            current_revisions = budget.revision_reason or ''
            revision_count = current_revisions.count('R') + 1  # Count existing revisions
            new_revision = f"R{revision_count}: {self.reason} (by {user_name} on {revision_time})"
            # Append the new reason to the existing reasons
            budget.revision_reason = f"{new_revision}\n {current_revisions}".strip()
            # for rec in self:
            budget.x_has_request_approval = False
            budget.approval_state = 'To Submit for Approval'
            budget.x_review_result = ''
            budget.state = 'revision'
            budget._action_revise()
            budget.sudo().message_post(body='This document has been revised')
            template = self.env.ref('accounts_extended.email_template_budget_revision_email')
            account_manager_group = self.env.ref('account.group_account_manager')
            emails = [user.email for user in account_manager_group.users if user.email]
            template.write({'email_to': ', '.join(emails)})
            template.send_mail(self.id, force_send=True)

