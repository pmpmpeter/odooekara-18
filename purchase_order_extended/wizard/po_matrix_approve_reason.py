from odoo import models, fields, api, _
from odoo.exceptions import UserError

class PurchaseOrderApprovalWizard(models.TransientModel):
    _name = 'purchase.order.approval.wizard'
    _description = 'Capture Approval Reason'

    approval_reason = fields.Text(string="Approval Reason", required=True)
    
    def submit_reason(self):
        # Get the active Purchase Order
        active_id = self.env.context.get('active_id')
        purchase_order = self.env['purchase.order'].browse(active_id)
        if not purchase_order:
            raise UserError(_("No Purchase Order found."))

        # Capture reason with user and timestamp
        user = self.env.user
        current_datetime = fields.Datetime.now()
        approval_entry = f"User: {user.name}, Reason: {self.approval_reason}, Date: {current_datetime}\n"
        if purchase_order.approval_history:
            purchase_order.approval_history += approval_entry
        else:
            purchase_order.approval_history = approval_entry

        # Move to the next approval level
        if purchase_order.quote_matrix_approval_state == 'quote_exceeds':
            purchase_order.quote_matrix_approval_state = 'to_department_head'
        elif user.has_group('purchase_order_extended.group_purchase_depaertment_head') and purchase_order.quote_matrix_approval_state == 'to_department_head':
            purchase_order.write({'quote_matrix_approval_state': 'to_account_head'})
        elif user.has_group('account.group_account_manager') and purchase_order.quote_matrix_approval_state == 'to_account_head':
            purchase_order.write({'quote_matrix_approval_state': 'to_tax_entity_head'})
        # elif user.has_group('accounts_extended.group_tax_entity_director') and purchase_order.quote_matrix_approval_state == 'to_tax_entity_head':
            # purchase_order.write({'quote_matrix_approval_state': 'approved'})
        else:
            raise UserError(_("You are not authorized to approve this PO."))


        return True
