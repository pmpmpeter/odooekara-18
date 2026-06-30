from odoo import models, fields, api
from datetime import datetime,timedelta
from odoo.exceptions import UserError, ValidationError

class DownloadReasonWizard(models.TransientModel):
    _name = 'download.reason.wizard'
    _description = 'Download Reason Wizard'

    reason = fields.Char(string="Multiple Download Reason", required=True)
    doc_id = fields.Many2one('document.request',string='Doc Request')

    def action_get_reason(self):
        active_model = self.env.context.get('active_model')
        active_id = self.env.context.get('active_id')  # Get the active budget record
        record = self.env[active_model].browse(active_id)
        if record:
            user_name = self.env.user.name  # Current user's name
            current_time = datetime.now()  # Current date and time
            revision_time = (current_time + timedelta(hours=5, minutes=30)).strftime('%Y-%m-%d %H:%M:%S')  # Add 5:30 hours
            # Calculate the new revision number
            current_reason = record.download_reason or ''
            new_reason = f"{self.reason} (by {user_name} on {revision_time})"
            # Append the new reason to the existing reasons
            record.download_reason = f"{new_reason}\n {current_reason}".strip()
            if record.pdf_expiry_date and fields.Datetime.now() < record.pdf_expiry_date:
                record.multi_download = True
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/document/download/pdf/{record.id}',
                    'target': 'self',
                }
            else:
                raise UserError("The document is no longer available for download.")

