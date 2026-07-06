from odoo import api, fields, models, _
from odoo.exceptions import UserError, AccessError,ValidationError
import logging, re
from datetime import datetime
from odoo.tools import SQL
from markupsafe import Markup


class ResPartnerApproval(models.Model):
    _name = 'res.partner.approval'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'partner_id'

    partner_id = fields.Many2one('res.partner', required=True, tracking=True)
    request_note = fields.Text("Change Request", tracking=True)
    rejection_reason = fields.Text("Rejection Reason", tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], default='draft', tracking=True)

    # ---------------------------------
    # 🔔 Reusable Bus Notification
    # ---------------------------------
    def _send_bus_notification(self, users, title, message, notif_type='info'):
        for user in users:
            if user.partner_id:
                self.env['bus.bus']._sendone(
                    user.partner_id,
                    'simple_notification',
                    {
                        'type': notif_type,
                        'title': title,
                        'message': message,
                        'sticky': False,
                    }
                )

    # ---------------------------------
    # Submit
    # ---------------------------------
    def action_submit(self):
        self.state = 'pending'

        group = self.env.ref('res_partner_extended.group_contact_admin_access')
        users = group.users.filtered(lambda u: u != self.env.user)

        message_text = _("New Approval Request: %s") % (self.request_note or '')

        # 🔔 Real-time popup to managers
        self._send_bus_notification(users, _('Approval Request'), message_text, 'info')

        # 💬 Chatter
        self.partner_id.message_post(
            body=f"🟡 New Approval Request<br/>Request: {self.request_note}",
            partner_ids=users.mapped('partner_id').ids,
            message_type='notification'
        )


    # ---------------------------------
    # Approve
    # ---------------------------------
    def action_approve(self):
        self.state = 'approved'

        creator_user = self.create_uid
        creator_partner = creator_user.partner_id

        self.partner_id.is_request_approved = True

        # 🔹 Message (HTML)
        message_html = Markup(
            "✅ Change Approved<br/>"
            "Request: %s<br/>"
            "Requested by: <a href='#' data-oe-model='res.partner' data-oe-id='%s'>@%s</a><br/>"
            "Approved by: %s"
        ) % (
            self.request_note or '',
            creator_partner.id,
            creator_partner.name,
            self.env.user.name
        )

        # 💬 Chatter
        self.partner_id.message_post(
            body=message_html,
            subject="Contact Change Approved",
            partner_ids=[creator_partner.id],
            message_type="notification"
        )

        # 🔔 Real-time popup to creator
        popup_msg = _("Your request has been approved: %s") % (self.request_note or '')
        self._send_bus_notification([creator_user], _('Approved'), popup_msg, 'success')


    # ---------------------------------
    # Reject (open wizard)
    # ---------------------------------
    def action_reject(self):
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reject Reason',
            'res_model': 'partner.approval.reject.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'active_id': self.id},
        }

    # ---------------------------------
    # Reset
    # ---------------------------------
    def action_reset_draft(self):
        self.state = 'draft'
        self.partner_id.is_request_approved = False


# ---------------------------------
# Reject Wizard
# ---------------------------------

class PartnerApprovalRejectWizard(models.TransientModel):
    _name = 'partner.approval.reject.wizard'
    _description = 'Reject Approval'

    reason = fields.Text("Reason", required=True)

    def action_confirm_reject(self):
        approval = self.env['res.partner.approval'].browse(self.env.context.get('active_id'))

        approval.rejection_reason = self.reason
        approval.state = 'rejected'
        approval.partner_id.is_request_approved = False

        creator_user = approval.create_uid
        creator_partner = creator_user.partner_id

        # 🔹 HTML Message
        message_html = Markup(
            "❌ Change Rejected<br/>"
            "Request: %s<br/>"
            "Reason: %s<br/>"
            "Requested by: <a href='#' data-oe-model='res.partner' data-oe-id='%s'>@%s</a><br/>"
            "Rejected by: %s"
        ) % (
            approval.request_note or '',
            self.reason or '',
            creator_partner.id,
            creator_partner.name,
            self.env.user.name
        )

        # 💬 Chatter
        approval.partner_id.message_post(
            body=message_html,
            subject="Contact Change Rejected",
            partner_ids=[creator_partner.id],
            message_type="notification"
        )

        # 🔔 Real-time popup to creator
        popup_msg = _("Your request has been rejected.\nReason: %s") % (self.reason or '')
        approval._send_bus_notification([creator_user], _('Rejected'), popup_msg, 'danger')