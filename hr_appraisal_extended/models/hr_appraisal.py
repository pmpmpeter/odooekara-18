from odoo import models, fields, api, _
from odoo.exceptions import ValidationError, UserError

#not using
class HrAppraisal(models.Model):
    """inherited the model to add some fields"""
    _inherit = 'hr.appraisal'

    def send_increment_letter_job_level_approved(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_increment_letters')
            if not template_id:
                raise UserError(_("Increment letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            ctx = dict(
                default_model='hr.appraisal',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Increment Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def send_appraisal_letter(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_appraisal_letters')
            if not template_id:
                raise UserError(_("Increment letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            ctx = dict(
                default_model='hr.appraisal',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Appraisal Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def send_annual_increment_promotion_letter(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_annual_increment_promotion_letters')
            if not template_id:
                raise UserError(_("Increment letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            ctx = dict(
                default_model='hr.appraisal',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Annual Increment Promotion Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

    def send_increment_redesignation_letter(self):
        for record in self:
            template_id = self.env.ref('hr_appraisal_extended.mail_increment_redesignation_letter_iim_job_approved')
            if not template_id:
                raise UserError(_("Increment letter template not found."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)

            if not compose_form:
                raise UserError(_("Email composition form not found."))

            ctx = dict(
                default_model='hr.appraisal',
                default_res_ids=record.ids,
                default_template_id=template_id.id,
                default_composition_mode='comment',
                default_email_layout_xmlid="mail.mail_notification_light",
            )

            return {
                'name': _('Compose Increment & Redesignation Letter Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }

