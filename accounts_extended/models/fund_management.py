from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import calendar
from datetime import datetime
from datetime import date,datetime

class FundManagementCRR(models.Model):
    _inherit = "fund.management"
    
    cash_pool_line = fields.One2many('cash.pool.lines', 'fund_management_id', string='Cash Pool')
    cash_pool = fields.Many2many('cash.pool', string='Cash Pool')
    
    @api.onchange('cash_pool_line')
    def _onchange_cash_pool_line(self):
        for record in self:
            for line in record.cash_pool_line:
                if line.cash_pool and line.cash_pool.current_balance <= 0:
                    raise ValidationError("The selected cash pool has a current balance of 0.")

   
    def _action_revise(self):
        for rec in self:
            prev_version = rec.version
            version = rec.version + 1
            rec.cash_pool_line.sudo().write({
                'version': version,
            })
            
            for line in rec.cash_pool_line:
                line.copy({
            
                    'fund_management_id': False,
                    'rev_fund_management_id': rec.id,
                    'version': prev_version,
                })
                # sequence += 1

            rec.sudo().write({
                'version': version,
                'revision_date': fields.Datetime.now(),
            })

    def _allocate_cash_pool(self):
        for rec in self:
            rec.cash_pool_line.sudo().write({
                'revision_date': fields.Datetime.now(),
            })
            rec.state = 'done'
            if rec.te_consolidate_id:
                rec.te_consolidate_id.state = 'done'

    
    def share_amount_validate(self):
        for rec in self:
            if not rec.crr_share_line:
                raise UserError('Share Amount is not Available.')
            if not rec.cash_pool_line:
                raise UserError('Please Add Cash Pool lines.')
            if rec.state == 'draft':
                rec.state = 'inprogress'
            if rec.state == 'inprogress':

                cash_p = rec.cash_pool_line
                pool = cash_p.mapped('cash_pool')
                for p in pool:
                    total_amount = 0
                    for line in rec.cash_pool_line:
                        if line.cash_pool == p:
                                total_amount += abs(line.april_cash_pool+line.may_cash_pool+line.june_cash_pool+line.july_cash_pool+line.august_cash_pool+line.september_cash_pool+
                                   line.october_cash_pool+ line.november_cash_pool+line.december_cash_pool+line.january_cash_pool+line.febuary_cash_pool+line.march_cash_pool)
                    if p.current_balance < total_amount:
                        raise ValidationError(
                            f"The cash pool '{p.name}' has a  balance of '{p.available_balance}'\n"
                            f"Kindly Allocate fund within available balance"
                        )
                    else:
                        p.write({
                                    'available_balance':p.current_balance - total_amount
                        })
                        if p.available_balance == 0:
                            p.invalid_cash_pool = True
                        else:
                            p.invalid_cash_pool = False
                        rec._allocate_cash_pool()

    def write(self, vals):
        for rec in self:
            res = super().write(vals)
            if rec.cash_pool_line:
                    cash_p = rec.cash_pool_line
                    pool = cash_p.mapped('cash_pool')
                    for p in pool:
                        total_amount = 0
                        for line in rec.cash_pool_line:
                            if line.cash_pool == p:
                                total_amount += abs(
                                    line.april_cash_pool + line.may_cash_pool + line.june_cash_pool + line.july_cash_pool + line.august_cash_pool + line.september_cash_pool +
                                    line.october_cash_pool + line.november_cash_pool + line.december_cash_pool + line.january_cash_pool + line.febuary_cash_pool + line.march_cash_pool)
                        if p.current_balance < total_amount:
                            raise ValidationError(
                                f"The cash pool '{p.name}' has a  balance of '{p.available_balance}'.\n"
                                f"Kindly Allocate fund within available balance."
                            )
        return res


    def action_update_cash_pool(self):
        cash_lines = []
        if not self.cash_pool:
            raise UserError('Kindly Provide Cash Pool Lines')
        else:
            if self.cash_pool:
                for rec in self.cash_pool:
                    cash_lines.append((0, 0, {
                        'cash_pool': rec.id,
                        'april_cash_pool': (sum(line.crr_share_april for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'may_cash_pool': (sum(line.crr_share_may for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'june_cash_pool': (sum(line.crr_share_june for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'quarter_1_cash_pool': (sum(line.crr_share_q1 for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'july_cash_pool': (sum(line.crr_share_july for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'august_cash_pool': (sum(line.crr_share_august for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'september_cash_pool': (sum(line.crr_share_september for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'quarter_2_cash_pool': (sum(line.crr_share_q2 for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'october_cash_pool': (sum(line.crr_share_october for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'november_cash_pool': (sum(line.crr_share_november for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'december_cash_pool': (sum(line.crr_share_december for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'quarter_3_cash_pool': (sum(line.crr_share_q3 for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'january_cash_pool': (sum(line.crr_share_january for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'febuary_cash_pool': (sum(line.crr_share_february for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'march_cash_pool': (sum(line.crr_share_march for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                        'quarter_4_cash_pool': (sum(line.crr_share_q4 for line in self.crr_share_line) / len(
                            self.crr_share_line)) if self.crr_share_line else 0,
                    }))
                self.cash_pool_line = cash_lines

    def action_open_cash_pool(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Cash Pool',
            'view_mode': 'list',
            'view_id': self.env.ref('accounts_extended.cash_pool_tree_view_extend').id,
            'res_model': 'cash.pool.lines',
            'context': {'group_by': ['version_name']},
            'domain': ['|', ('fund_management_id', 'in', self.ids), ('rev_fund_management_id', 'in', self.ids)],
        }



class TeConsolidation(models.Model):
    _inherit = "te.consolidation"

    def action_revise(self):
        for rec in self:
            fund_id = self.env['fund.management'].sudo().search([('te_consolidate_id', '=', self.id)])
            fund_id._action_revise()
            fund_id.state = 'inprogress'