# -*- coding: utf-8 -*-

from ast import literal_eval

from odoo import models, fields, api
from odoo.exceptions import ValidationError


class DocumentShare(models.Model):
    _inherit = 'documents.share'

    partner_ids = fields.Many2many('res.partner', string="Email To")

    def action_send_custom_share_mail(self):
        template = self.env.ref('document_validity_management.documents_share_email_template_custom')
        for record in self:
            if not record.partner_ids:
                raise ValidationError("Please add at least one partner to send the email.")
            if record.partner_ids:
                template.send_mail(record.id, force_send=True)
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': 'Success',
                    'message': 'Email sent to selected recipients.',
                    'type': 'success',
                    'sticky': True,
                }
            }

