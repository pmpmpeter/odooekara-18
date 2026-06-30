##############################################################################
#
#    Copyright Domiup (<http://domiup.com>).
#
##############################################################################

import logging

from odoo import _, api, fields, models
from odoo.exceptions import UserError,ValidationError
import base64
from datetime import datetime
from bs4 import BeautifulSoup

_logger = logging.getLogger(__name__)


class MultiApproval(models.Model):
    _name = "multi.approval"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _description = "Multi Approval"

    code = fields.Char(default="New")
    name = fields.Char(string="Title", required=True)
    user_id = fields.Many2one(
        string="Request by",
        comodel_name="res.users",
        required=True,
        default=lambda self: self.env.uid,
    )
    priority = fields.Selection(
        [("0", "Normal"), ("1", "Medium"), ("2", "High"), ("3", "Very High")],
        default="0",
    )
    request_date = fields.Datetime(copy=False)
    submit_date = fields.Datetime(default=fields.Datetime.now, copy=False)
    complete_date = fields.Datetime(copy=False)
    type_id = fields.Many2one(
        string="Type", comodel_name="multi.approval.type", required=True
    )
    image = fields.Binary(related="type_id.image")
    description = fields.Html()
    state = fields.Selection(
        [
            ("Draft", "Draft"),
            ("Submitted", "Submitted"),
            ("Approved", "Approved"),
            ("Refused", "Refused"),
            ("Cancel", "Cancelled"),
        ],
        default="Draft",
        tracking=True,
        copy=False,
    )

    document_opt = fields.Selection(
        string="Document opt", readonly=True, related="type_id.document_opt"
    )
    attachment_ids = fields.Many2many("ir.attachment", string="Documents")

    contact_opt = fields.Selection(
        string="Contact opt", readonly=True, related="type_id.contact_opt"
    )
    contact_id = fields.Many2one("res.partner", string="Contact")

    date_opt = fields.Selection(
        string="Date opt", readonly=True, related="type_id.date_opt"
    )
    date = fields.Date()

    period_opt = fields.Selection(
        string="Period opt", readonly=True, related="type_id.period_opt"
    )
    date_start = fields.Date("Start Date")
    date_end = fields.Date("End Date")

    item_opt = fields.Selection(string="Item opt", related="type_id.item_opt")
    item_id = fields.Many2one("product.product", string="Item")

    multi_items_opt = fields.Selection(
        string="Multi Items opt", readonly=True, related="type_id.multi_items_opt"
    )
    item_ids = fields.Many2many("product.product", string="Items")

    quantity_opt = fields.Selection(
        string="Quantity opt", readonly=True, related="type_id.quantity_opt"
    )
    quantity = fields.Float()

    amount_opt = fields.Selection(readonly=True, related="type_id.amount_opt")
    amount = fields.Float()

    payment_opt = fields.Selection(readonly=True, related="type_id.payment_opt")
    payment = fields.Float()

    reference_opt = fields.Selection(readonly=True, related="type_id.reference_opt")
    reference = fields.Char()

    location_opt = fields.Selection(readonly=True, related="type_id.location_opt")
    location = fields.Char()
    line_ids = fields.One2many("multi.approval.line", "approval_id", string="Lines")
    line_id = fields.Many2one("multi.approval.line", string="Line", copy=False)
    deadline = fields.Date(string="Deadline", related="line_id.deadline")
    pic_id = fields.Many2many("res.users", string="Approver", related="line_id.user_id")
    is_pic = fields.Boolean(string="Is Pic",compute="_compute_is_pic")
    follower = fields.Text("Following Users", default="[]", copy=False)
    refused_reason = fields.Text(string="Refused Reason")

    # copy the idea of hr_expense
    attachment_number = fields.Integer(
        "Number of Attachments", compute="_compute_attachment_number"
    )

    show_approve_button = fields.Boolean(string="Show Approve Button",compute="_compute_show_approve_button")

    @api.depends("line_id.approved_users")
    def _compute_show_approve_button(self):
        for rec in self:
            # Check if the current user is in the approved_users of the current line
            rec.show_approve_button = self.env.uid not in rec.line_id.approved_users.ids

    @api.depends("pic_id")
    @api.depends_context("uid")
    def _compute_is_pic(self):
        for r in self:
            r.is_pic = self.env.uid in r.pic_id.ids
            # r.is_pic = r.pic_id.id == self.env.uid

    def _compute_attachment_number(self):
        attachment_data = self.env["ir.attachment"].read_group(
            [("res_model", "=", "multi.approval"), ("res_id", "in", self.ids)],
            ["res_id"],
            ["res_id"],
        )
        attachment = dict(
            (data["res_id"], data["res_id_count"]) for data in attachment_data
        )
        for r in self:
            r.attachment_number = attachment.get(r.id, 0)

    def action_cancel(self):
        recs = self.filtered(lambda x: x.state == "Draft")
        recs.write({"state": "Cancel"})

    def action_submit(self):
        recs = self.filtered(lambda x: x.state == "Draft")
        for r in recs:
            # Check if document is required
            if r.document_opt == "Required" and r.attachment_number < 1:
                raise UserError(_("Document is required !"))
            if not r.type_id.line_ids:
                raise UserError(
                    _(f'There is no approver of the type "{r.type_id.name}" !')
                )
            r.state = "Submitted"
        recs._create_approval_lines()
        recs.send_request_mail()
        recs.send_activity_notification()

    @api.model
    def get_follow_key(self, user_id=None):
        if not user_id:
            user_id = self.env.uid
        k = f"[res.users:{user_id}]"
        return k

    def update_follower(self, user_id):
        self.ensure_one()
        k = self.get_follow_key(user_id)
        follower = self.follower
        if k not in follower:
            self.follower = follower + k

    # 13.0.1.1
    def set_approved(self, send_mail=True):
        self.ensure_one()
        self.state = "Approved"
        self.complete_date = fields.Datetime.now()
        if send_mail:
            self.send_approved_mail()

    def set_refused(self, reason="", send_mail=True):
        self.ensure_one()
        self.state = "Refused"
        self.refused_reason = reason
        self.complete_date = fields.Datetime.now()
        if send_mail:
            self.send_refused_mail()

    def action_approve(self):
        ret_act = None
        recs = self.filtered(lambda x: x.state == "Submitted")
        for rec in recs:
            if not rec.is_pic:
                msg = _(
                    "%s do not have the authority to approve this request !",
                    rec.env.user.name,
                )
                rec.sudo().message_post(body=msg)
                return False
            line = rec.line_id

            model_display_name = self.env['ir.model'].sudo().search([('model', '=', self.type_id.model_id)],
                                                                    limit=1).name
            log_msg = _("{} - {} has been approved by {}!").format(line.name, model_display_name, self.env.user.name)
            if log_msg and hasattr(rec.origin_ref, "message_post"):
                rec.origin_ref.message_post(body=log_msg)

            if not line or line.state != "Waiting for Approval":
                # Something goes wrong!
                rec.message_post(body=_("Something goes wrong!"))
                return False

            # Update follower
            rec.update_follower(self.env.uid)

            # Mark the current user as approved
            line.approved_users = [(4, self.env.uid)]

            # Check if all required approvers at this level have approved
            if line.require_opt == "Required" and set(line.user_id.ids) <= set(line.approved_users.ids):
                # All required approvers have approved; move to the next level or mark approved
                # check if this line is required
                other_lines = rec.line_ids.filtered(
                    lambda x, _l=line: x.sequence >= _l.sequence and x.state == "Draft"
                )
                if not other_lines:
                    ret_act = rec.set_approved()
                    if rec.type_id.model_id == "cash.management":
                        if not rec.origin_ref.tax_entity:
                            raise ValidationError(
                                "Kindly fill the tax entity details."
                            )
                        rec.origin_ref.approval_status ='approved'
                        rec.origin_ref.approved_by = self.env.user.id
                        rec.origin_ref.approved_date = datetime.now() 
                        rec.origin_ref.approved_file = rec.origin_ref.submitted_file 
                        rec.origin_ref.approved_name = rec.origin_ref.submitted_name 
                    # if rec.type_id.model_id == "crossovered.budget":
                    #     for budget_line in rec.origin_ref.crossovered_budget_line:
                    #         if budget_line.additional_amount > 0:
                    #             self.env['revision.history'].create({
                    #                 'budget_post_id': budget_line.general_budget_id.id,
                    #                 'budget_code': budget_line.budget_code,
                    #                 'analytic_account_id': budget_line.analytic_account_id.id,
                    #                 'initial_allocate': budget_line.planned_amount,
                    #                 'additional_amount': budget_line.additional_amount,
                    #                 'budget_id':rec.origin_ref.id,
                    #                 'revision_date':fields.Datetime.now()
                    #                 })
                    #             budget_line.planned_amount += budget_line.additional_amount
                    #             budget_line.additional_amount = 0
                else:
                    next_line = other_lines.sorted("sequence")[0]
                    next_line.write(
                        {
                            "state": "Waiting for Approval",
                        }
                    )
                    rec.line_id = next_line
                    rec.send_request_mail()
                    recs.send_activity_notification()
                line.set_approved()

            elif line.require_opt != "Required":
                # Optional approval; any single approver can mark this level as approved
                line.set_approved()

                # Check if there are any other lines to approve
                other_lines = rec.line_ids.filtered(
                    lambda x, _l=line: x.sequence > _l.sequence and x.state == "Draft"
                )
                if other_lines:
                    # If there are more lines, move to the next one
                    next_line = other_lines.sorted("sequence")[0]
                    next_line.write({"state": "Waiting for Approval"})
                    rec.line_id = next_line
                    rec.send_request_mail()
                    rec.send_activity_notification()
                # If there are no more lines, finalize the approval process
                else:
                    rec.set_approved()
                    msg = _("%s approved the request.") % self.env.user.name
                    rec.finalize_activity_or_message("approved", msg)

            # For employee.indent to change the value of the job description page
            if rec.type_id.model_id == "employee.indent":
                employee_indent = self.env['employee.indent'].search([('id', '=', rec.origin_ref.id)])
                if employee_indent:
                    first_line = rec.line_ids.sorted("sequence")[0]
                    second_line = rec.line_ids.sorted("sequence")[1]
                    if first_line.state == "Approved":
                        employee_indent.approved_by_hod = "yes"
                    if second_line.state == "Approved":
                        employee_indent.approved_by_director = "yes"

            #For Cash Pool to write the approved user in Cash Pool Fund Line
            if rec.type_id.model_id == "cash.pool":
                cash_pool = self.env['cash.pool'].search([('id', '=', rec.origin_ref.id)])
                if cash_pool:
                    for line in cash_pool.fund_line_ids:
                        line.approved_by_id = self.env.user.id


            # to assign the date and state
            if rec.type_id.model_id == "hr.resignation":
                hr_resignation = self.env['hr.resignation'].search([('id', '=', rec.origin_ref.id)])
                if hr_resignation:
                    lines_sorted = rec.line_ids.sorted("sequence")
                    first_line = lines_sorted[0] if len(lines_sorted) > 0 else None
                    second_line = lines_sorted[1] if len(lines_sorted) > 1 else None

                    if first_line and first_line.state == 'Approved':
                        hr_resignation.manager_approved_date = fields.Date.today()
                        hr_resignation.status_boolean = True

                    if second_line and second_line.state == 'Approved':
                        hr_resignation.status_boolean = False

                # rec.finalize_related_document()

            if rec.type_id.model_id == 'hr.expense.sheet':
                rec_id = self.env['hr.expense.sheet'].search([('id', '=', rec.origin_ref.id)])
                if rec_id:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Approve Reason',
                        'res_model': 'approve.reason',
                        'view_mode': 'form',
                        'view_id': self.env.ref('multi_level_approval.approve_reason_view_form').id,
                        'target': 'new',
                        'context': {'expense': int(rec_id.id)}
                    }
            if rec.type_id.model_id == 'account.payment':
                rec_id = self.env['account.payment'].search([('id', '=', rec.origin_ref.id)])
                if rec_id and rec_id.is_fund_requsiting:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': 'Approve Reason',
                        'res_model': 'approve.reason',
                        'view_mode': 'form',
                        'view_id': self.env.ref('multi_level_approval.approve_reason_view_form').id,
                        'target': 'new',
                        'context': {'fund': int(rec_id.id)}
                    }
            msg = _("%s approved the request.") % self.env.user.name
            rec.finalize_activity_or_message("approved", msg)
        if ret_act:
            return ret_act
        return True

    def action_refuse(self, reason=""):
        # added employee.indent yes or no values here
        if self.type_id.model_id == "employee.indent":
            employee_indent = self.env['employee.indent'].search([('id', '=', self.origin_ref.id)])
            employee_indent.approved_by_hod = "no"
            employee_indent.approved_by_director = "no"

        ret_act = None
        recs = self.filtered(lambda x: x.state == "Submitted")
        for rec in recs:
            if not rec.is_pic:
                msg = _(
                    "%s do not have the authority to approve this request !",
                    rec.env.user.name,
                )
                self.sudo().message_post(body=msg)
                return False
            line = rec.line_id
            if not line or line.state != "Waiting for Approval":
                # Something goes wrong!
                self.message_post(body=_("Something goes wrong!"))
                return False

            # Update follower
            rec.update_follower(self.env.uid)

            # check if this line is required
            # if line.require_opt == "Required":
            if line.require_opt:
                ret_act = rec.set_refused(reason)
                draft_lines = rec.line_ids.filtered(lambda x: x.state == "Draft")
                if draft_lines:
                    draft_lines.state = "Cancel"
            else:  # optional
                other_lines = rec.line_ids.filtered(
                    lambda x, _l=line: x.sequence >= _l.sequence and x.state == "Draft"
                )
                if not other_lines:
                    ret_act = rec.set_refused(reason)
                else:
                    next_line = other_lines.sorted("sequence")[0]
                    next_line.state = "Waiting for Approval"
                    rec.line_id = next_line
            line.set_refused(reason)
            msg = _(f"I refused due to this reason: {reason}")
            rec.finalize_activity_or_message("refused", msg)

        if ret_act:
            return ret_act

    def finalize_activity_or_message(self, action, msg):
        requests = self.filtered(lambda r: r.type_id.activity_notification)
        notify_type = self.env.ref("mail.mail_activity_data_todo", False)
        if requests and notify_type:
            activities = requests.mapped("activity_ids").filtered(
                lambda a: a.activity_type_id == notify_type
                          and a.user_id == self.env.user
            )
            activities._action_done(msg)

        requests2 = self - requests
        if requests2:
            requests2.message_post(body=msg)

    def _create_approval_lines(self):
        ApprovalLine = self.env["multi.approval.line"]
        for r in self:
            lines = r.type_id.line_ids.sorted("sequence")
            last_seq = 0
            for _l in lines:
                line_seq = _l.sequence
                if not line_seq or line_seq <= last_seq:
                    line_seq = last_seq + 1
                last_seq = line_seq
                vals = {
                    "name": _l.name,
                    # "user_id": _l.get_user(),
                    "user_id": [(6, 0, _l.get_user())],
                    "sequence": line_seq,
                    "require_opt": _l.require_opt,
                    "approval_id": r.id,
                }
                if _l == lines[0]:
                    vals.update({"state": "Waiting for Approval"})
                approval = ApprovalLine.create(vals)
                if _l == lines[0]:
                    r.line_id = approval

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            seq_date = vals.get("submit_date", fields.Datetime.now())
            # seq_date = vals.get("request_date", fields.Datetime.now())
            vals["code"] = self.env["ir.sequence"].next_by_code(
                "multi.approval", sequence_date=seq_date
            ) or _("New")
        result = super().create(vals_list)
        return result

    # 12.0.1.3
    def send_request_mail(self):
        requests = self.filtered(
            lambda r: r.type_id.mail_notification and
                      r.pic_id
                      and r.state == "Submitted"
        )
        for req in requests:
            # Check if origin_ref is of type 'employee.indent'
            if req.origin_ref and req.origin_ref._name == 'employee.indent':
                # New behavior for 'employee.indent' model
                for user in req.pic_id:
                    print("Sending request to: %s", user.name)
                    print(self.origin_ref.name, "origin_ref")
                    template = self.env.ref('hr_extended.employee_indent_approval_request_email')  # Email template
                    report_action = self.env.ref('hr_extended.action_employee_indent_report')

                    if not report_action:
                        raise ValueError("Report action 'hr_extended.action_employee_indent_report' not found.")

                    pdf_content, content = report_action._render_qweb_pdf(report_action.id, res_ids=self.origin_ref.ids)
                    attachment = self.env['ir.attachment'].create({
                        'name': f"Employee_Indent_{self.origin_ref.name}.pdf",
                        'type': 'binary',
                        'datas': base64.b64encode(pdf_content).decode('utf-8'),
                        'res_model': 'employee.indent',
                        'res_id': self.origin_ref.id,
                        'mimetype': 'application/pdf',
                    })

                    # if template:
                    #     email_values = {
                    #         'email_from': req.user_id.email,  # Company's email
                    #         'email_to': user.email,  # User's email
                    #         'attachment_ids': [(6, 0, [attachment.id])],  # Attach the PDF
                    #     }
                    #     self.env['mail.template'].browse(template.id).send_mail(self.origin_ref.id, force_send=True,
                    #                                                             email_values=email_values)
                    #     req.message_post(
                    #         body=_("The Approval request for the employee indent was sent successfully to %s.") %
                    #              email_values['email_to'])
                    # else:
                    message = self.env["mail.message"].create(
                        {
                            "subject": _("{request_name}").format(
                                request_name=BeautifulSoup(req.display_name,'lxml').get_text(strip=True)),
                            "model": req._name,
                            "res_id": req.id,
                            "body": self.description,
                            "attachment_ids": [(4, attachment.id)],
                        }
                    )
                    print(message)
                    self.env["mail.mail"].sudo().create(
                        {
                            "mail_message_id": message.id,
                            "body_html": self.description,
                            "email_to": user.email,
                            "email_from": req.user_id.email,
                            "auto_delete": True,
                            "is_notification": True,
                            "state": "outgoing",
                        }
                    )
            else:
                # Base Code for Other Modules
                print(self.origin_ref._name)
                for user in req.pic_id:
                    if req.type_id.mail_template_id:
                        req.type_id.mail_template_id.send_mail(req.id)
                    else:
                        message = self.env["mail.message"].create(
                            {
                                "subject": _("Request the approval for: {request_name}").format(
                                    request_name=BeautifulSoup(req.display_name,'lxml').get_text(strip=True)),
                                "model": req._name,
                                "res_id": req.id,
                                "body": self.description,
                            }
                        )
                        self.env["mail.mail"].sudo().create(
                            {
                                "mail_message_id": message.id,
                                "body_html": self.description,
                                "email_to": user.email,
                                "email_from": req.user_id.email,
                                "auto_delete": True,
                                "is_notification":True,
                                "state": "outgoing",
                            }
                        )

    def send_approved_mail(self):
        requests = self.filtered(
            lambda r: r.type_id.approve_mail_template_id and r.state == "Approved"
        )
        for req in requests:
            req.type_id.approve_mail_template_id.send_mail(req.id)

    def send_refused_mail(self):
        requests = self.filtered(
            lambda r: r.type_id.refuse_mail_template_id and r.state == "Refused"
        )
        for req in requests:
            req.type_id.refuse_mail_template_id.send_mail(req.id)

    def send_activity_notification(self):
        requests = self.filtered(
            lambda r: r.type_id.activity_notification
                      and r.pic_id
                      and r.state == "Submitted"
        )
        notify_type = self.env.ref("mail.mail_activity_data_todo", False)
        if not notify_type:
            return
        for req in requests:
            summary = _("The request {code} need to be reviewed").format(code=BeautifulSoup(req.code,'lxml').get_text(strip=True))
            for user in req.pic_id:
                self.env["mail.activity"].create(
                    {
                        "res_id": req.id,
                        "res_model_id": self.env["ir.model"]._get(req._name).id,
                        "activity_type_id": notify_type.id,
                        "summary": summary,
                        "user_id": user.id,
                    }
                )
