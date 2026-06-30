from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RequestApproval(models.TransientModel):
    _inherit = "request.approval"

    def action_request(self):
        if self.origin_ref._name in ['purchase.request','purchase.order']:
            pr = self.origin_ref
            if pr.budget_id:
                line_ids = pr.line_ids if self.origin_ref._name == 'purchase.request' else pr.order_line
                lines_excluded = line_ids.filtered(lambda line: not line.analytic_distribution)
                if lines_excluded:
                    raise UserError(
                        'Please select Analytic Account of selected Budget Code "%s" in Analytic Distributions of the Products:- %s' % (
                            pr.budget_id.analytic_account_id.name, ", ".join(lines_excluded.mapped('product_id.name'))))

                lines_excluded = line_ids.filtered(
                    lambda line: line.analytic_distribution != {str(pr.budget_id.analytic_account_id.id): 100.0})
                if lines_excluded:
                    raise UserError(
                        'Please select Analytic Account "%s" only in Analytic Distributions of the Products:- %s' % (
                        pr.budget_id.analytic_account_id.name, ", ".join(lines_excluded.mapped('product_id.name'))))
        return super().action_request()
