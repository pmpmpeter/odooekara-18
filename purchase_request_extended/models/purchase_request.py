from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import format_amount, format_date, formatLang, groupby
from odoo.tools.float_utils import float_is_zero
from markupsafe import Markup




class PurchaseRequest(models.Model):
    _inherit = "purchase.request"
    _description = "Purchase Request"

    # budget_id = fields.Many2one('crossovered.budget.lines', 'Budget Code', copy=False, required=1)
    # budget_balance_warning = fields.Html(
    #     compute='_compute_budget_balance_warning',
    # )
    approval_state = fields.Char(string='Approval Status', compute='compute_approval_state', store=True, copy=False,
                                 tracking=True)
    approval_document = fields.Many2one('multi.approval', string='Approval Record', copy=False)
    revision_reason = fields.Text(string="Revision Reasons", readonly=True, default="")
    purchase_type = fields.Many2one(comodel_name='purchase.orders.type')
    unregistered_vendor = fields.Char(string='Unregistered Vendor',copy=False)

    @api.depends("state")
    def _compute_is_editable(self):
        for rec in self:
            if rec.state in ("to_approve","to approve", "approved", "rejected", "done"):
                rec.is_editable = False
            else:
                rec.is_editable = True

    @api.depends('approval_document.type_id.state', 'approval_document.line_ids.state')
    def compute_approval_state(self):
        for record in self:
            if record.approval_document:
                line_states = record.approval_document.line_ids.mapped('state')
                if all(state == 'Draft' for state in line_states):
                    record.approval_state = 'Waiting For Approval'
                elif 'Waiting for Approval' in line_states:
                    waiting_lines = record.approval_document.line_ids.filtered(
                        lambda l: l.state == 'Waiting for Approval')
                    if waiting_lines:
                        record.approval_state = f"Waiting for {', '.join(waiting_lines.mapped('name'))} Approval"
                elif all(state == 'Approved' for state in line_states):
                    record.approval_state = 'Approved'
                elif 'Refused' in line_states:
                    record.approval_state = 'Rejected'
                elif 'Cancel' in line_states:
                    record.approval_state = 'Cancelled'
            else:
                rec = self.env['multi.approval.type'].sudo().search(
                    [('model_id', '=', 'purchase.request'), ('state', '=', 'confirm')], limit=1)
                if rec:
                    record.approval_state = 'To Submit for Approval'
                else:
                    record.approval_state = 'Not Applicable'


    # @api.depends('budget_id','company_id', 'estimated_cost', 'currency_id', 'line_ids.product_qty', 'line_ids.estimated_cost')
    # def _compute_budget_balance_warning(self):
    #     msg=''
    #     for order in self.filtered(lambda s: s.budget_id):
    #         order.with_company(order.company_id)
    #         order.budget_balance_warning = ''
    #         #po_date = order.date_order or fields.Date.today()
    #         # domain1 = [('date_from', '<=', po_date), ('date_to', '>=', po_date),('id', '=', order.budget_id.id)]
    #         domain1 = [('id', '=', order.budget_id.id)]
    #         budget_allocated_id = self.env['crossovered.budget.lines'].sudo().search(domain1, limit=1)
    #         if budget_allocated_id:
    #             allocated_amount= budget_allocated_id.planned_amount
    #             spent_amount = (abs(budget_allocated_id.practical_amount)+budget_allocated_id.reserved_amount)
    #             available_amount = allocated_amount - spent_amount
    #             allocated_amount_formatted = formatLang(self.env, allocated_amount, currency_obj=order.company_id.currency_id)
    #             available_amount_formatted = formatLang(self.env, available_amount, currency_obj=order.company_id.currency_id)
    #             if order.estimated_cost > available_amount:
    #                 msg = Markup(
    #                           "<span style='color: red;'>Alert !! Budget is exceeding for %s."
    #                           "Allocated budget is %s and Available balance is %s.</span>"
    #                       ) % (order.budget_id.display_name, allocated_amount_formatted, available_amount_formatted)
    #             else:
    #                 msg = Markup(
    #                           "For %s Allocated budget is %s and Available balance is %s."
    #                       ) % (order.budget_id.display_name, allocated_amount_formatted, available_amount_formatted)
    #         else:
    #             msg = Markup("Alert !! No active budget found.</span>")
    #     self.budget_balance_warning = msg

class PurchaseRequestLineMakePurchaseOrder(models.TransientModel):
        _inherit = "purchase.request.line.make.purchase.order"
        _description = "Purchase Request Line Make Purchase Order"

        budget_id = fields.Many2one(comodel_name="crossovered.budget.lines", string='Budget')
        purchase_type = fields.Many2one(comodel_name='purchase.orders.type')

        @api.model
        def default_get(self, fields):
            res = super().default_get(fields)
            active_model = self.env.context.get("active_model", False)
            request_line_ids = []
            if active_model == "purchase.request.line":
                request_line_ids += self.env.context.get("active_ids", [])
            elif active_model == "purchase.request":
                request_ids = self.env.context.get("active_ids", False)
                request_line_ids += (
                    self.env[active_model].browse(request_ids).mapped("line_ids.id")
                )
            if not request_line_ids:
                return res
            res["item_ids"] = self.get_items(request_line_ids)
            request_lines = self.env["purchase.request.line"].browse(request_line_ids)
            supplier_ids = request_lines.mapped("supplier_id").ids
            if len(supplier_ids) == 1:
                res["supplier_id"] = supplier_ids[0]
            request_rec = self.env["purchase.request"].browse(request_ids)
            res["budget_id"] = request_rec.budget_id.id
            res["purchase_type"] = request_rec.purchase_type.id
            return res

        @api.model
        def _prepare_purchase_order(self, picking_type, group_id, company, origin):
            if not self.supplier_id:
                raise UserError(_("Enter a supplier."))
            supplier = self.supplier_id
            data = {
                "origin": origin,
                "partner_id": self.supplier_id.id,
                "payment_term_id": self.supplier_id.property_supplier_payment_term_id.id,
                "fiscal_position_id": supplier.property_account_position_id
                                      and supplier.property_account_position_id.id
                                      or False,
                "picking_type_id": picking_type.id,
                "company_id": company.id,
                "group_id": group_id.id,
                "budget_id": self.budget_id.id,
                "purchase_type": self.purchase_type.id
            }
            return data
