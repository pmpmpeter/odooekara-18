from odoo import api, fields, models, _, Command, tools
from odoo.addons.base.models.decimal_precision import DecimalPrecision
from odoo.exceptions import UserError, ValidationError, AccessError, RedirectWarning
import re
import pdb
import datetime
from datetime import date, timedelta, datetime


class DocumentUpdateInterviewStatus(models.Model):
    _name = 'document.update.interview.status'
    _description = "Document Update Interview Status"

    name = fields.Html(string="Subject")
    active = fields.Boolean('Active', default=True, copy=False)

    def unlink(self):
        for record in self:
            if record.active:
                raise UserError("You can't delete a record in Active.")
        return super(DocumentUpdateInterviewStatus, self).unlink()


class RecruitmentInvitation(models.Model):
    _name = 'recruitment.invitation.letter.config'
    _description = "Recruitment Invitation Configuration"

    name = fields.Html(string="Subject")
    active = fields.Boolean('Active', default=True, copy=False)

    def unlink(self):
        for record in self:
            if record.active:
                raise UserError("You can't delete a record in Active.")
        return super(RecruitmentInvitation, self).unlink()
    # stage_id = fields.Many2one('hr.recruitment.stage', string="Stage", required=True, unique=True)
    #
    # _sql_constraints = [
    #     ('stage_id_unique', 'unique(stage_id)', 'Each stage should only have one corresponding subject configuration.')
    # ]


class ApplicantInvitation(models.Model):
    _name = "applicant.invitation.letter"
    _description = "Applicant Invitation Letter"
    _inherit = ['portal.mixin', 'mail.thread', 'mail.activity.mixin', 'utm.mixin']
    _order = 'id desc'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals['name'] == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('hr.job.nvitation.letter') or _('New')
        return super().create(vals_list)

    def _get_default_subject(self):
        subject_id = self.env['recruitment.invitation.letter.config'].sudo().search([], limit=1)
        return subject_id.name if subject_id else False

    name = fields.Char('Reference', required=True, index='trigram', copy=False, default='New', readonly=True)
    applicant_id = fields.Many2one('hr.applicant', 'Applicant', readonly=False)
    applicant_name = fields.Char(string="Applicant Name", related='applicant_id.partner_name')
    # stage_id = fields.Char(string="Stage_id")
    user_id = fields.Many2one('res.users', 'Responsible', readonly=False)
    job_id = fields.Many2one('hr.job', 'Job Position', readonly=True, related='applicant_id.job_id', store=True)
    interviewer_ids = fields.Many2many('res.users', string='Interviewers', readonly=True, store=True)
    company_id = fields.Many2one('res.company', 'Company', readonly=True, related='applicant_id.company_id', store=True)
    active = fields.Boolean('Active', default=True)
    invitation_date = fields.Date("Date", default=fields.Datetime.now)
    state = fields.Selection([
        ('draft', 'Draft'), ('sent', 'Sent'), ('active', 'Accepted'), ('expired', 'Expired'), ('cancel', 'Cancelled')
    ], default='draft', tracking=1, string='Status', readonly=True, copy=False)
    letter_subject = fields.Html(string="Body", default=_get_default_subject)
    letter_heading = fields.Char(string="Subject")

    
    def action_draft(self):
        for record in self.filtered(lambda s: s.state not in ['draft']):
            record.write({'state': 'draft'})

    # for set the next level name in mail
    def get_next_stage_name(self):
        self.ensure_one()
        stage_mapping = {
            'new': 'initial',
            'initial': 'first_level',
            'first_level': 'second_interview',
            'second_interview': 'shortlist',
        }
        next_stage_key = stage_mapping.get(self.applicant_id.stage_id.stage)
        next_stage = self.env['hr.recruitment.stage'].search([('stage', '=', next_stage_key)], limit=1)
        return next_stage.name if next_stage else "No Next Stage Defined"

    def action_set_as_accepted(self):
        for record in self.filtered(lambda s: s.state in ['sent']):
            record.write({'state': 'active'})
            current_stage = record.applicant_id.stage_id
            stage_mapping = {
                'new': 'initial',
                'initial': 'first_level',
                'first_level': 'second_interview',
                # 'second_interview': 'shortlist',
            }
            next_stage_key = stage_mapping.get(current_stage.stage, False)
            if next_stage_key:
                next_stage = self.env['hr.recruitment.stage'].search([('stage', '=', next_stage_key)], limit=1)
                if next_stage:
                    record.applicant_id.stage_id = next_stage.id
                else:
                    raise UserError(
                        f"{next_stage_key.replace('_', ' ').capitalize()} stage not found! Please create it in Recruitment stages.")
            else:
                raise UserError("No valid stage transition defined for the current stage.")

    
    def action_cancel(self):
        for record in self.filtered(lambda s: s.state in ['sent']):
            record.write({'state': 'cancel'})

    def action_send_by_email(self):
        self.ensure_one()
        for record in self:
            template_id = self.env.ref('hr_extended.recruitement_first_invitiation_email_template',
                                       raise_if_not_found=False)
            if not record.letter_subject:
                raise UserError(_("The subject to send mail is missing."))

            if not template_id:
                raise UserError(
                    _("The email template for sending First Invitation letter for Recruitment does not exist."))
            recipient_email = record.applicant_id.email_from
            if not recipient_email:
                raise UserError(_("The recipient does not have a valid email address."))
            current_user_email = record.env.user.email
            if not current_user_email:
                raise UserError(_("The current user does not have a valid email address."))
            template_id.with_context(
                email_to=record.applicant_id.email_from
            ).send_mail(
                record.id, force_send=True
            )
            for interviewer in record.interviewer_ids:
                if not interviewer.partner_id:
                    raise UserError(_("The Partner Id does not exist."))
                record.activity_schedule(
                    activity_type_id=self.env.ref('mail.mail_activity_data_todo').id,
                    summary="Interview Notification",
                    note="You have been notified about the interview process.",
                    user_id=interviewer.id,
                )
            record.write({'state': 'sent'})

    def unlink(self):
        for record in self:
            if record.active or record.state !='draft':
                raise UserError("You can't delete a record in Active or the state is not in 'Draft'.")
        return super(ApplicantInvitation, self).unlink()
