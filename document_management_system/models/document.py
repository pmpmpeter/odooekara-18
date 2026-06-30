import datetime
from odoo import models, fields, api
from odoo.exceptions import ValidationError
from markupsafe import Markup


class DocumentWorkflow(models.Model):
    _name = "document.workflow"
    _description = "Document Workflow Management"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    # Fields
    name = fields.Char("Document Title", required=True, tracking=True)

    document_request = fields.Text("Document Handle", tracking=True)
    approval_notes = fields.Text("Approval Notes", tracking=True)

    # Workflow states
    # document_state = fields.Selection([
    #     ('draft', 'Draft'),
    #     ('requested', 'Requested'),
    #     ('waiting_approval', 'Waiting for Approval'),
    #     ('done', 'Done'),
    # ], string="Document Status", default="draft", tracking=True)

    # Tracking Users
    requested_by_id = fields.Many2one('res.users', string="Requested By", readonly=True, tracking=True)
    submitted_by_id = fields.Many2one('res.users', string="Submitted By", readonly=True, tracking=True)
    requested_to_id = fields.Many2one('res.users', string="Requested To",  tracking=True)
    submitted_to_id = fields.Many2one('res.users', string="Submitted To",  tracking=True)
    received_by_id = fields.Many2one('res.users', string="Received By", readonly=True, tracking=True)
    attachment_ids = fields.One2many(
        'document.attachment',
        'workflow_id',
        string="Documents"
    )
    document_history = fields.One2many(
        'document.history',
        'document_workflow_id',
    )

    documents_count = fields.Integer(
        compute="_compute_documents_count",
        string="No. of Documents",
        store=True
    )

    @api.depends('attachment_ids')
    def _compute_documents_count(self):
        for rec in self:
            rec.documents_count = len(rec.attachment_ids)

    # Button actions
    def action_request_document(self):
        for rec in self:
            if not rec.requested_to_id:
                raise ValidationError(
                    "please fill the whom you are requesting to!"
                )
            rec.document_state = "requested"
            rec.requested_by_id = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            document_url = f"{base_url}/web#id={rec.id}&model=document.workflow&view_type=form"

            message = Markup(
                "Document Name: %s<br/>"
                "Requested By: %s<br/>"
                "<a href='%s' target='_blank'>Open Document Request</a>"
            ) % (
                          rec.name,
                          rec.requested_by_id.name,
                          document_url
                      )
            rec.message_post(
                body=message,
                subject="New Document Request Created",
                partner_ids=[rec.requested_to_id.partner_id.id],
                message_type="notification"
            )


    def action_request_approval(self):
        for rec in self:
            if not rec.submitted_to_id:
                raise ValidationError(
                    "please fill the whom you are submitting to!"
                )
            rec.document_state = "waiting_approval"
            rec.submitted_by_id = self.env.user
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            document_url = f"{base_url}/web#id={rec.id}&model=document.workflow&view_type=form"

            message = Markup(
                "Document Name: %s<br/>"
                "Submitted By: %s<br/>"
                "<a href='%s' target='_blank'>Open Document Submitted</a>"
            ) % (
                          rec.name,
                          rec.submitted_by_id.name,
                          document_url
                      )
            rec.message_post(
                body=message,
                subject="New Document has been Submitted",
                partner_ids=[rec.submitted_to_id.partner_id.id],
                message_type="notification"
            )

    def action_mark_done(self):
        for rec in self:
            rec.document_state = "done"
            rec.received_by_id = self.env.user

class DocumentAttachment(models.Model):
    _name = "document.attachment"
    _description = "Document Attachment"

    file_data = fields.Binary("File", required=True)
    file_name = fields.Char("Filename")

    workflow_id = fields.Many2one(
        'document.workflow',
        string="Workflow",
        ondelete='cascade'
    )


class Documenthistory(models.Model):
    _name = "document.history"
    _description = "Document History"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'document_workflow_id'

    # name = fields.Char("Name", required=True)
    submitted_by = fields.Many2one('res.users',"Submitted By",tracking=True,readonly=True)
    submitted_to = fields.Many2one('res.users',"Submitted To",tracking=True)
    received_by = fields.Many2one('res.users',"Received By",tracking=True,readonly=True)
    submitted_date = fields.Datetime(string="Submitted Date")
    received_date = fields.Datetime(string="Received Date")
    partner_id = fields.Many2one('res.partner', string='External Customer')
    status = fields.Selection([('draft', 'Draft'),
        ('requested', 'Requested'),
        ('waiting_approval', 'Waiting for Approval'),
        ('scrapped', 'Scrapped'),
        ('stored', 'Stored'),
        ('done', 'Done'),
    ], string="Document Status", default="draft", tracking=True,readonly=True)
    document_workflow_id = fields.Many2one(
        'document.workflow',
        string="Workflow",readonly=True
    )
    show_scrap = fields.Boolean("Show Scrap", compute="_compute_show_button", default=False)
    show_store = fields.Boolean("Show Store", compute="_compute_show_button", default=False)
    show_requested = fields.Boolean("Show Request", compute="_compute_show_button", default=False)
    show_received = fields.Boolean("Show Received", compute="_compute_show_button", default=False)

    def _compute_show_button(self):
        user_id = self.env.user.id
        self.show_scrap = False
        self.show_store = False
        self.show_requested = False
        self.show_received = False
        for rec in self:
            if rec.submitted_to.id == user_id:
                rec.show_received = True
            if rec.submitted_by.id == user_id or rec.create_uid.id == user_id:
                rec.show_requested = True
            if not rec.id or not rec.document_workflow_id:
                continue
            records = self.search([('document_workflow_id', '=', rec.document_workflow_id.id)], order="id asc")
            if not records:
                continue
            last_record = records[-1]
            if rec.id != last_record.id:
                continue
            if rec.received_by.id == user_id:
                rec.show_scrap = True
                rec.show_store = True

    @api.constrains('submitted_by', 'document_workflow_id')
    def validate_record_creation(self):
        for rec in self:
            if not rec.document_workflow_id:
                continue
            last_record = self.search([('document_workflow_id', '=', rec.document_workflow_id.id), ('id', '!=', rec.id)], order="id desc", limit=1)
            if not last_record:
                continue
            if last_record.status != "done" or last_record.submitted_to.id != self.env.user.id:
                raise ValidationError("You are not allowed to create documents!")







    # def action_request_document(self):
    #     for rec in self:
    #         if not rec.requested_to_id:
    #             raise ValidationError(
    #                 "please fill the whom you are requesting to!"
    #             )
    #         rec.status = "requested"
    #         rec.requested_by_id = self.env.user
    #         base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
    #         document_url = f"{base_url}/web#id={rec.id}&model=document.workflow&view_type=form"
    #
    #         message = Markup(
    #             "Document Name: %s<br/>"
    #             "Requested By: %s<br/>"
    #             "<a href='%s' target='_blank'>Open Document Request</a>"
    #         ) % (
    #                       rec.name,
    #                       rec.requested_by_id.name,
    #                       document_url
    #                   )
    #         rec.message_post(
    #             body=message,
    #             subject="New Document Request Created",
    #             partner_ids=[rec.requested_to_id.partner_id.id],
    #             message_type="notification"
    #         )


    def action_request_approval(self):
        for rec in self:
            if not rec.submitted_to:
                raise ValidationError(
                    "please fill the whom you are submitting to!"
                )
            rec.status = "waiting_approval"
            rec.submitted_by = self.env.user
            rec.submitted_date = fields.Datetime.now()
            base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
            document_url = f"{base_url}/web#id={rec.document_workflow_id.id}&model=document.workflow&view_type=form"

            message = Markup(
                "Document Name: %s<br/>"
                "Submitted By: %s<br/>"
                "<a href='%s' target='_blank'>Open Document Submitted</a>"
            ) % (
                          rec.document_workflow_id.name,
                          rec.submitted_by.name,
                          document_url
                      )
            rec.document_workflow_id.message_post(
                body=message,
                subject="New Document has been Submitted",
                partner_ids=[rec.submitted_to.partner_id.id],
                message_type="notification"
            )

    def add_logger_comment(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        document_url = f"{base_url}/web#id={self.document_workflow_id.id}&model=document.workflow&view_type=form"
        status = "Received" if self.status == 'done' else self.status.title()
        message = Markup("Document Name: %s<br/> %s By: %s<br/><a href='%s' target='_blank'>Open Document Submitted</a>") % (
                      self.document_workflow_id.name, status, self.received_by.name, document_url
                  )
        self.document_workflow_id.message_post(
            body=message,
            subject=f"New Document has been {self.status.title()}",
            partner_ids=[self.received_by.partner_id.id],
            message_type="notification"
        )

    def action_mark_done(self):
        for rec in self:
            rec.status = "done"
            rec.received_by = self.env.user
            rec.received_date = fields.Datetime.now()
            rec.add_logger_comment()

    def action_mark_stored(self):
        for rec in self:
            rec.status = "stored"
            rec.received_by = self.env.user
            rec.received_date = fields.Datetime.now()
            rec.add_logger_comment()

    def action_mark_scrap(self):
        for rec in self:
            rec.status = "scrapped"
            rec.received_by = self.env.user
            rec.received_date = fields.Datetime.now()
            rec.add_logger_comment()
