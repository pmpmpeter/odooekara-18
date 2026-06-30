# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models,_
from datetime import datetime, timedelta,timezone
from odoo.exceptions import UserError, ValidationError
import base64
import pdb
import mimetypes
from datetime import date

class DocumentRequest(models.Model):
    _name = 'document.request'
    _description = "Document Request"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date DESC"

    user_id = fields.Many2one('res.users', string="Requested By", tracking=True, default=lambda self: self.env.uid)
    request_date = fields.Date(string='Request Date', tracking=True, default=datetime.today())
    name = fields.Char(string='Name', default='New', copy=False)
    document_id = fields.Many2one('document.item', string="Document Requested", copy=False, tracking=True)
    documents_id = fields.Many2one('documents.document', string="Documents")
    company_id = fields.Many2one('res.company', string='Company', tracking=True)
    approved_date = fields.Datetime(string='Approved Date', tracking=True, copy=False)
    approve_uid = fields.Many2one('res.users', string="Approved By", tracking=True, readonly=True)
    pdf_document = fields.Binary(string="Generated PDF")
    pdf_filename = fields.Char(string="PDF Filename")
    documents_pdf_document = fields.Binary(string="Additional PDF")
    documents_pdf_filename = fields.Char(string="Additional PDF Filename")
    pdf_expiry_date = fields.Datetime(string="PDF Expiry Date")
    document_available_till = fields.Date(string='Document Available Till')
    state = fields.Selection([
        ('draft','Draft'),
        ('to_approve','To Approve'),
        ('approved','Approved'),
        ('rejected','Rejected'),
        ('expired','Expired'),
    ], default='draft', string="State", tracking=True, copy=False, readonly=True)
    multi_download = fields.Boolean("Multiple Download")
    download_reason = fields.Text("Download Reason")
    purpose = fields.Text("Purpose", copy=False)
    is_watermark = fields.Boolean(string="Is Watermark",copy=False)
    watermark_content = fields.Html(string="Watermark Content", copy=False)
    is_doc_expired = fields.Boolean(string='Is Expired')
    x_review_result = fields.Char(string="Review Result")


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('document.request') or 'New'
        return super().create(vals_list)

    # @api.model
    # def create(self, vals):
    #     if vals.get('name', 'New') == 'New':
    #         vals['name'] = self.env['ir.sequence'].next_by_code('document.request') or 'New'
    #     return super(DocumentRequest, self).create(vals)

    def unlink(self):
        for rec in self:
            if rec.state != 'draft':
                raise UserError(_("Alert !! Only records in the 'Draft' state can be deleted."))
        return super(DocumentRequest, self).unlink()

    def action_reset_to_draft(self):
        for rec in self:
            rec.state = "draft"

    @api.model
    def delete_old_files(self):
        # Calculate the time limit (24 hours ago)
        time_limit = datetime.now() - timedelta(hours=24)

        # Search for records with files generated more than 24 hours ago
        old_files = self.search(
            [('request_time', '<', time_limit), ('attachment_binary', '!=', False)])

        # Delete the files
        for record in old_files:
            record.sudo().write({'attachment_binary': False, 'attachment_binary_filename': False})

    def action_send_approval_request(self):
        for rec in self:
            document_manager_group = self.env.ref('document_access_mgmt.group_document_manager')
            group_emails = []
            partner_ids_to_follow = []
            if document_manager_group.users:
                for user in document_manager_group.users:
                    user_name = user.name
                    if not user.email:
                        raise UserError(_('Please configure Email for %s.', user_name))
                    group_emails.append(user.email)
                    partner_ids_to_follow.append(user.partner_id.id)

                rec.message_subscribe(partner_ids=partner_ids_to_follow)
                follower_emails = rec.message_follower_ids.mapped('partner_id.email')
                all_emails = list(set(group_emails + follower_emails))

                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                action_id = self.env['ir.model.data']._xmlid_lookup('document_access_mgmt.document_request_action')[1]
                subject = "Document Access Approval Request: " + rec.name
                mail_content = """<div style="font-family: 'Lucica Grande', Ubuntu, Arial, Verdana, sans-serif; font-size: 12px; color: rgb(34, 34, 34); background-color: rgb(255, 255, 255); ">
                                                <p>Dear """ + str(user_name) + """,</p>
                                                Please review the details and provide your approval at your earliest convenience.
                                                <br/><br/>

                                                You can view the details here: 
                                                <a href=""" + str(base_url) + """/web#id=""" + str(
                    rec.id) + """&view_type=form&model=document.request&action=""" + str(action_id) + """>
                                               """ + str(rec.name) + """

                                                </a>
                                                <br/>
                                                <br/>
                                                Your prompt response would be highly appreciated.
                                                <br/>
                                                <br/>
                                                <p/>
                                                Thanks,
                                                <br/>
                                                <br/>
                                                <br/><br/>
                                                <p style="color:#808080"><i>
                                                Do not reply to this email as its an automatic alert send by ERP

                                            </div>"""
                # email_to = [user.email]
                # main_content = {
                #     'subject': subject,
                #     'author_id': self.env.user.partner_id.id,
                #     'body_html': mail_content,
                #     'email_to': ','.join(email_to),
                # }
                if all_emails:
                    self.env['mail.mail'].sudo().create({
                        'subject': subject,
                        'author_id': self.env.user.partner_id.id,
                        'body_html': mail_content,
                        'email_to': ','.join(all_emails),
                    }).send()
                # self.env['mail.mail'].create(main_content).send()
            else:
                raise UserError(_('Please configure Document Access Manager'))
            rec.state = 'to_approve'

    def download_pdf(self):
        for rec in self.filtered(lambda d: d.state in ['approved']):
            # pdb.set_trace()
            if rec.multi_download == True:
                 return {
                    'name': 'Multiple Download Reason',
                    'type': 'ir.actions.act_window',
                    'res_model': 'download.reason.wizard',
                    'view_mode': 'form',
                    'target': 'new',
                    'context': {'active_id': self.id},
                }
            if rec.pdf_expiry_date and fields.Datetime.now() < rec.pdf_expiry_date:
                rec.multi_download = True
                return {
                    'type': 'ir.actions.act_url',
                    'url': f'/document/download/pdf/{rec.id}',
                    'target': 'self',
                }
            else:
                raise UserError("The document is no longer available for download.")
        for rec in self.filtered(lambda d: d.state in ['expired']):
            raise UserError("The document is no longer available for download.")

    def action_approve(self):
        for rec in self.filtered(lambda d: d.state == 'to_approve'):
            values_to_write = {
                'state': 'approved',
                'approve_uid': self.env.user.id,
                'approved_date': fields.Datetime.now(),
            }

            if rec.document_id:
                pdf_content = rec._generate_pdf(rec.document_id)
                values_to_write.update({
                    'pdf_document': pdf_content,
                    'pdf_filename': f'{rec.document_id.name}.pdf',
                    'pdf_expiry_date': datetime.now() + timedelta(hours=rec.document_id.doc_available_hours),
                })

            if rec.documents_id:
                documents_pdf = rec.documents_id.datas
                doc_name = rec.documents_id.name or 'document'

                if '.' not in doc_name:
                    extension = mimetypes.guess_extension(rec.documents_id.mimetype or '') or '.bin'
                    doc_name += extension

                values_to_write.update({
                    'documents_pdf_document': documents_pdf,
                    'documents_pdf_filename': doc_name,
                })
            if not self.document_available_till:
                raise UserError(_("kindly set the document validity period."))
            rec.write(values_to_write)

    # def action_approve(self):
    #     for rec in self.filtered(lambda d: d.state in ['to_approve']):
    #         pdf_content = self._generate_pdf()
    #         rec.write({
    #             'state': 'approved',
    #             'approve_uid': self.env.user.id,
    #             'approved_date': fields.Datetime.now(),
    #             'pdf_document': pdf_content,
    #             'pdf_filename': f'{rec.document_id.name}.pdf',
    #             'pdf_expiry_date': datetime.now() + timedelta(hours=rec.document_id.doc_available_hours),
    #         })

    def action_reject(self):
        for rec in self:
            rec.state = 'rejected'

    def _generate_pdf(self, document):
        custom_context = {
            'generation_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'username': self.env.user.name,
            'add_watermark':True,
            'purpose':self.purpose,
            'is_watermark':self.is_watermark,
            'watermark_content':self.watermark_content
        }
        report = self.env['ir.actions.report'].with_context(custom_context)._render_qweb_pdf("document_access_mgmt.action_document_report", document.id)[0]
        return base64.b64encode(report)

    # def submit_document_request(self):
    #     # Retrieve the email template for the approval request
    #     template = self.env.ref(
    #         'document_access_mgmt.email_template_document_approval_request',
    #         raise_if_not_found=True)

    #     # Get the list of users who have a partner with a valid email
    #     users = self.env.ref('document_access_mgmt.document_manager_access').users
    #     partner_emails = ",".join(users.mapped('partner_id.email'))

    #     if partner_emails:
    #         # Set the recipients for the email template
    #         template.email_to = partner_emails
    #         base_url = self.env['ir.config_parameter'].sudo().get_param(
    #             'web.base.url')
    #         record_url = f"{base_url}/web#id={self.id}&model={self._name}&view_type=form"

    #         # Send the email
    #         template.with_context(URL=record_url).send_mail(res_id=self.id,
    #                                                    force_send=True)

    #     # Update the document state to 'submitted'
    #     self.state = 'submit'

    @api.model
    def cron_move_to_expired_state(self):

            today = date.today()  # Get current date
            print(today, 'kkkkkkkkk')
            expired_records = self.sudo().search([
                ('pdf_expiry_date', '<', today),
                ('state', '!=', 'expired')
            ])

            for record in expired_records:
                record.write({'state': 'expired'})
            expired_doc_records = self.sudo().search([
                ('document_available_till', '<', today),
                ('state', '!=', 'expired')
            ])
            print(expired_doc_records,'qqqqqqqqqqqq')
            for record in expired_doc_records:
                record.write({'state': 'expired'})
                record.is_doc_expired = True
