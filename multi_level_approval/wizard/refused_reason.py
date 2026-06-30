##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

from odoo import fields, models
from datetime import datetime,timedelta

class RefusedReason(models.TransientModel):
    _name = "refused.reason"
    _description = "Refused Reason"

    reason = fields.Text(required=True)

    def action_reason_apply(self):

        approval = self.env["multi.approval"].browse(self.env.context.get("active_ids"))
        res_model = self._context.get('active_model')
        active_id = self._context.get('active_id')
        multi_id = self.env['multi.approval'].browse(active_id)
        if multi_id.type_id.model_id == "cash.management":
            user_name = self.env.user.name  # Current user's name
            current_time = datetime.now()  # Current date and time
            revision_time = (current_time + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')  # Add 5:30 hours
            current_revisions = multi_id.origin_ref.revision_reason or ''
            revision_count = current_revisions.count('R') + 1  # Count existing revisions
            new_revision = f"R{revision_count}: {self.reason} (by {user_name} on {revision_time})"
            multi_id.origin_ref.revision_reason = f"{new_revision}\n {current_revisions}".strip()
            multi_id.origin_ref.approval_status = 'draft'
            multi_id.origin_ref.x_has_request_approval = False
            mail_obj = self.env['mail.mail'].sudo().create({
                'subject': f'Revision Mail:{multi_id.origin_ref.name}',
                'email_from':self.env.company.email ,  # Change to a valid email
                'email_to': multi_id.origin_ref.submit_by.work_email,  # Change recipient email
                 'body_html': f"<p>Hello,<br/><br/> your report has been revised because of the following reason:</p><p><strong>{self.reason}</strong></p><br/><p>Thank You.</>",
            })
            mail_obj.sudo().send()
        if multi_id.type_id.model_id == "purchase.request":
            user_name = self.env.user.name  # Current user's name
            current_time = datetime.now()  # Current date and time
            revision_time = (current_time + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')  # Add 5:30 hours
            current_revisions = multi_id.origin_ref.revision_reason or ''
            revision_count = current_revisions.count('R') + 1  # Count existing revisions
            new_revision = f"R{revision_count}: {self.reason} (by {user_name} on {revision_time})"
            multi_id.origin_ref.revision_reason = f"{new_revision}\n {current_revisions}".strip()
            multi_id.origin_ref.state = 'draft'
            multi_id.origin_ref.x_has_request_approval = False
            mail_obj = self.env['mail.mail'].sudo().create({
                'subject': f'Revision Mail:{multi_id.origin_ref.name}',
                'email_from':self.env.company.email ,  # Change to a valid email
                'email_to': multi_id.origin_ref.requested_by.login,  # Change recipient email
                 'body_html': f"<p>Hello,<br/><br/> your purchase request has been revised because of the following reason:</p><p><strong>{self.reason}</strong></p><br/><p>Thank You.</>",
            })
            mail_obj.sudo().send()

        if multi_id.type_id.model_id == "cash.requirement.report":
            user_name = self.env.user.name  # Current user's name
            current_time = datetime.now()  # Current date and time
            revision_time = (current_time + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')  # Add 5:30 hours
            current_revisions = multi_id.origin_ref.revision_reason or ''
            revision_count = current_revisions.count('R') + 1  # Count existing revisions
            new_revision = f"R{revision_count}: {self.reason} (by {user_name} on {revision_time})"
            multi_id.origin_ref.revision_reason = f"{new_revision}\n {current_revisions}".strip()
            multi_id.origin_ref.state = 'draft'
            multi_id.origin_ref.x_has_request_approval = False
            mail_obj = self.env['mail.mail'].sudo().create({
                'subject': f'Revision Mail:{multi_id.origin_ref.name}',
                'email_from':self.env.company.email ,  # Change to a valid email
                'email_to': multi_id.origin_ref.requested_by.login,  # Change recipient email
                 'body_html': f"<p>Hello,<br/><br/> your cash request has been revised because of the following reason:</p><p><strong>{self.reason}</strong></p><br/><p>Thank You.</>",
            })
            mail_obj.sudo().send()

        return approval.action_refuse(reason=self.reason)

class ApproveReason(models.TransientModel):
    _name = "approve.reason"
    _description = "Approve Reason"

    reason = fields.Text(required=True)

    def action_approve_reason_apply(self):
        active_id = self.env.context.get('expense')
        active_id_fund = self.env.context.get('fund')
        if active_id:
            expense_id = self.env['hr.expense.sheet'].browse(active_id)
            user = self.env.user
            current_datetime = fields.Datetime.now()
            approval_entry = f"User: {user.name}, Reason: {self.reason}, Date: {current_datetime}\n"
            if expense_id.reason_approved:
                expense_id.reason_approved += approval_entry
            else:
                expense_id.reason_approved = approval_entry
        if active_id_fund:
            expense_id = self.env['account.payment'].browse(active_id_fund)
            user = self.env.user
            current_datetime = fields.Datetime.now()
            approval_entry = f"User: {user.name}, Reason: {self.reason}, Date: {current_datetime}\n"
            if expense_id.reason_approved:
                expense_id.reason_approved += approval_entry
            else:
                expense_id.reason_approved = approval_entry

        # approval = self.env["multi.approval"].browse(self.env.context.get("active_ids"))
        return True
