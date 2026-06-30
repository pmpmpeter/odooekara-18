# -*- coding: utf-8 -*-

from odoo import models, fields, api, _, Command, tools
from odoo.exceptions import *
from odoo.exceptions import UserError, ValidationError

class PreEmpCheck(models.Model):
    _name = 'preemp.check'
    _description = 'Pre Employment Check'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "candidate_name"

    # applicant_id = fields.Many2one('hr.applicant', string='Applicant', ondelete='cascade')
    applicant_id = fields.Integer(string='Applicant',readonly=True)
    candidate_name = fields.Char(string="Candidate",copy=False)
    candidate_email = fields.Char(string="Candidate Email ID", readonly=True)
    date = fields.Date(string="Date",copy=False,default=fields.Date.context_today)
    location = fields.Char(string="Location",copy=False)
    referee_id = fields.Many2one('res.users',string="Name of Referee",copy=False)
    recruiter_id = fields.Many2one('res.users',string="Recruiting Manager",copy=False)
    referee_phone = fields.Char(string="Phone Number",copy=False)
    referee_email = fields.Char(string="Email ID",copy=False)
    referee_title = fields.Char(string="Title of Referee",copy=False)
    referee_relationship = fields.Char(string="Relationship to Candidate",copy=False)
    technical_skills_comments = fields.Text(string="Technical Skills and Expertise",copy=False)
    job_duties_comments = fields.Text(string="Job Duties Handled during the Tenure",copy=False)
    professional_skills_comments = fields.Text(string="Professional Interactive Skills",copy=False)

    integrity_resources = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Integrity or Effectiveness in Handling Organization’s Resources?",copy=False
    )
    integrity_interactions = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Integrity or Effectiveness in Professional Interactions?",copy=False
    )
    responsibility_productivity = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Ability to Accept Responsibility or Maintain Productivity?",copy=False
    )
    maturity_composure = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Maturity, Composure, or Professional Conduct Under Job Stresses?",copy=False
    )
    adaptability = fields.Selection(
        [('yes', 'Yes'), ('no', 'No')],
        string="Ability to Adapt to New or Changing Work Situations?",copy=False
    )

    additional_comments = fields.Text(string="If Yes to Any, Please Comment",copy=False)
    other_comments = fields.Text(string="Other Comments or Recommendation",copy=False)

    state = fields.Selection([
        ('to_submit', 'To Submit'),
        ('done', 'Done')
    ], string='Status', default='to_submit', required=True, tracking=True, copy=False)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Alert !! Only records in the 'Draft' state can be deleted."))
        return super(PreEmpCheck, self).unlink()

    def action_done(self):
        for rec in self:
            rec.state='done'
            if not rec.candidate_email:
                raise UserError(_("Candidate email is missing. Please update the email address."))
            if not rec.referee_id or not rec.referee_phone or not rec.referee_email:
                raise UserError(_("Referee details are incomplete. Please fill in the referee's information."))
            if not rec.technical_skills_comments:
                raise UserError(
                    _("Technical skills comments are missing. Please provide comments on the candidate's technical skills."))
            if not rec.referee_title or not rec.referee_relationship:
                raise UserError(_("Referee details are incomplete. Please fill in the referee's information."))
            if not rec.job_duties_comments:
                raise UserError(
                    _("Job duties comments are missing. Please provide comments on the candidate's job duties."))
            if not rec.professional_skills_comments:
                raise UserError(
                    _("Professional skills comments are missing. Please provide comments on the candidate's professional skills."))
            if not (
                    rec.integrity_resources and rec.integrity_interactions and rec.responsibility_productivity and rec.maturity_composure and rec.adaptability):
                raise UserError(_("Please complete the integrity and competency-related fields."))
            rec.state = 'done'

    def action_send_form_pdf_mail(self):
        template = self.env.ref('hr_extended.reference_check_pdf_form_template')
        for rec in self:
            if not rec.recruiter_id.email:
                raise ValidationError(_("The Recruiter does not have a valid email."))

            if not template:
                raise ValidationError(_("The email template is not configured."))

            compose_form = self.env.ref('mail.email_compose_message_wizard_form', raise_if_not_found=True)
            ctx = {
                'default_model': 'preemp.check',
                'default_res_ids': self.ids,
                'default_template_id': template.id,
                'default_composition_mode': 'comment',
                'default_email_layout_xmlid': "mail.mail_notification_light",
            }

            return {
                'name': _('Compose Pre Employment Reference Email'),
                'type': 'ir.actions.act_window',
                'view_mode': 'form',
                'res_model': 'mail.compose.message',
                'views': [(compose_form.id, 'form')],
                'view_id': compose_form.id,
                'target': 'new',
                'context': ctx,
            }


