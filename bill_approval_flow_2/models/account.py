from odoo import models, api, _,fields
from lxml import etree
from odoo.exceptions import UserError
from odoo.tools import float_compare
import logging
_logger = logging.getLogger(__name__)  # SPLIT-DBG


class AccountMove(models.Model):
    _inherit = 'account.move'

    approval_id = fields.Many2one('bill.approval', string="Approvals")

    def _copy_approval_attachments(self, approval_id):
        if not approval_id:
            return

        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'bill.approval'),
            ('res_id', '=', approval_id)
        ])

        for att in attachments:
            existing = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.move'),
                ('res_id', '=', self.id),
                ('name', '=', att.name),
            ], limit=1)

            if not existing:
                att.copy({
                    'res_model': 'account.move',
                    'res_id': self.id,
                })

    # ---------------- BILL LIMIT CHECK ----------------
    # CONTROL: bill booking under an approval can never go beyond the
    # approved Taxable amount or the approved GST amount, and each is
    # checked against its own bucket only (taxable vs taxable, GST vs GST):
    #
    #   * Taxable consumed by a bill = its amount_untaxed. TDS never
    #     reduces this. TDS is part of the taxable amount (paid to the
    #     Government on the vendor's behalf), so however TDS is applied
    #     (negative tax line on the invoice lines, TDS smart button on the
    #     bill, TDS smart button on the payment) the full taxable base is
    #     still consumed from the approval.
    #   * GST consumed by a bill = its GST tax lines only (matched by tax
    #     name containing "gst"), so TDS lines can never leak into it.
    #
    # There is deliberately NO total-vs-total comparison any more: it mixed
    # the two buckets (and, being net of tax-line TDS, let taxable slip
    # through). Cancelled bills are ignored so a cancelled bill releases
    # its share of the approval.
    def _get_taxable_gst_amounts(self):
        """(taxable, gst) consumed by the moves in self."""
        taxable = sum(self.mapped('amount_untaxed'))
        gst_lines = self.line_ids.filtered(
            lambda l: l.tax_line_id and 'gst' in (l.tax_line_id.name or '').lower()
        )
        gst = abs(sum(gst_lines.mapped('balance')))
        return taxable, gst

    @api.model
    def _billed_position(self, approval, exclude_ids=None):
        """(billed_taxable, billed_gst) actually BOOKED on this approval's
        bills right now -- not the approved figures. Cancelled bills are
        excluded, so is a bill passed in `exclude_ids` (used when checking
        whether cancelling THAT bill would still be safe)."""
        domain = [('approval_id', '=', approval.id), ('move_type', '!=', 'entry'), ('state', '!=', 'cancel')]
        if exclude_ids:
            domain.append(('id', 'not in', exclude_ids))
        moves = self.env['account.move'].search(domain)
        return moves._get_taxable_gst_amounts()

    def _check_bill_limit(self, approval):
        self.ensure_one()
        # CANCEL-CONTEXT-FLAG: cancelling a bill triggers Odoo's own internal dynamic-line
        # recompute, which does a NESTED write() on this same record for other fields
        # before the state change is applied -- self.state is not reliable at that point
        # (it can still read the pre-cancel state mid-operation). A context flag, set once
        # at the top of the outer write() call, survives that nested re-entry because Odoo
        # carries context through records derived from the same environment.
        if self.env.context.get('_bafc_skip_bill_limit') or self.state == 'cancel':
            return

        moves = self.env['account.move'].search([
            ('approval_id', '=', approval.id),
            ('move_type', '!=', 'entry'),
            ('state', '!=', 'cancel'),
        ])
        booked_taxable, booked_gst = moves._get_taxable_gst_amounts()
        this_taxable, this_gst = (self if self in moves else self.browse())._get_taxable_gst_amounts()

        rounding = self.company_currency_id.rounding or 0.01
        fmt = lambda v: '{:,.2f}'.format(v)

        if float_compare(booked_taxable, approval.taxable_value, precision_rounding=rounding) > 0:
            others = booked_taxable - this_taxable
            raise UserError(_(
                "Bill limit exceeded (Taxable)!\n"
                "Approval: %(ref)s\n"
                "Approved taxable: %(approved)s\n"
                "Booked in other bills: %(others)s\n"
                "This bill: %(this)s\n"
                "Available for this bill: %(avail)s\n\n"
                "Taxable is checked against approved taxable only. TDS "
                "does not reduce the taxable amount a bill uses.",
                ref=approval.name,
                approved=fmt(approval.taxable_value),
                others=fmt(others),
                this=fmt(this_taxable),
                avail=fmt(max(approval.taxable_value - others, 0.0)),
            ))

        if float_compare(booked_gst, approval.gst, precision_rounding=rounding) > 0:
            others = booked_gst - this_gst
            raise UserError(_(
                "Bill limit exceeded (GST)!\n"
                "Approval: %(ref)s\n"
                "Approved GST: %(approved)s\n"
                "Booked in other bills: %(others)s\n"
                "This bill: %(this)s\n"
                "Available for this bill: %(avail)s\n\n"
                "GST is checked against approved GST only.",
                ref=approval.name,
                approved=fmt(approval.gst),
                others=fmt(others),
                this=fmt(this_gst),
                avail=fmt(max(approval.gst - others, 0.0)),
            ))

        self._check_bill_not_below_reserved_advance(  # ADVANCE-RESERVES-BILL
            approval, booked_taxable, booked_gst, this_taxable, this_gst)

    # ---------------- ADVANCE RESERVES BILL CAPACITY ----------------
    # ADVANCE-RESERVES-BILL: an advance payment (Advance Payment ticked) is checked
    # only against the APPROVED amount, not against any bill, because it is paid
    # before a bill exists. But once it has settled taxable or GST, that much of the
    # approved amount is no longer free for a NEW bill to claim -- otherwise the
    # approval's total exposure (bills + unmatched advances) could exceed what was
    # approved even though each side, checked alone, stays within its own limit.
    @api.model
    def _advance_reserved(self, approval):
        """(reserved_taxable, reserved_gst): taxable/GST already settled by posted
        ADVANCE payments on this approval. Matches the same per-payment TDS a payment
        itself carries (its own TDS smart-button entry + its own Other Charges TDS
        line), so an advance's own TDS is reserved along with its cash."""
        payments = self.env['account.payment'].search([
            ('approval_id', '=', approval.id), ('state', '=', 'posted'),
            ('advance_payment', '=', True),
        ])
        reserved_taxable = 0.0
        for pay in payments:
            own_tds = -sum(l.other_charge for l in pay.other_charges_lines if l.other_charge < 0)
            own_tds += pay.move_id.l10n_in_total_withholding_amount or 0.0
            reserved_taxable += pay.taxable_paid_amount + own_tds
        reserved_gst = sum(payments.mapped('gst_paid_amount'))
        return reserved_taxable, reserved_gst

    def _check_bill_not_below_reserved_advance(self, approval, booked_taxable, booked_gst, this_taxable, this_gst):

        # REVERT-TO-APPROVED-ONLY: disabled at the user's request. Bills and payments
        # are checked against the APPROVED taxable/GST amounts only, as originally
        # designed. To re-enable this cross-check later, remove this early return.
        return

        self.ensure_one()
        reserved_taxable, reserved_gst = self._advance_reserved(approval)
        rounding = self.company_currency_id.rounding or 0.01
        fmt = lambda v: '{:,.2f}'.format(v)
        billed_before_t = booked_taxable - this_taxable
        billed_before_g = booked_gst - this_gst
        if reserved_taxable > billed_before_t + 0.01:
            avail = max(approval.taxable_value - reserved_taxable - billed_before_t, 0.0)
            if float_compare(this_taxable, avail, precision_rounding=rounding) > 0:
                raise UserError(_(
                    "Bill limit exceeded (Taxable, reserved by an advance)!\n"
                    "Approval: %(ref)s\n"
                    "Approved taxable: %(approved)s\n"
                    "Already settled by advance payment(s), not yet billed: %(reserved)s\n"
                    "Booked in other bills: %(others)s\n"
                    "This bill: %(this)s\n"
                    "Available for this bill: %(avail)s\n\n"
                    "An advance payment on this approval has already used part of the approved "
                    "taxable amount. That part is reserved until a bill claims it, so it cannot "
                    "also be booked as a new bill on top.",
                    ref=approval.name, approved=fmt(approval.taxable_value),
                    reserved=fmt(reserved_taxable), others=fmt(billed_before_t),
                    this=fmt(this_taxable), avail=fmt(avail)))
        if not approval.is_reverse_charge and reserved_gst > billed_before_g + 0.01:
            avail = max(approval.gst - reserved_gst - billed_before_g, 0.0)
            if float_compare(this_gst, avail, precision_rounding=rounding) > 0:
                raise UserError(_(
                    "Bill limit exceeded (GST, reserved by an advance)!\n"
                    "Approval: %(ref)s\n"
                    "Approved GST: %(approved)s\n"
                    "Already settled by advance payment(s), not yet billed: %(reserved)s\n"
                    "Booked in other bills: %(others)s\n"
                    "This bill: %(this)s\n"
                    "Available for this bill: %(avail)s\n\n"
                    "An advance payment on this approval has already used part of the approved "
                    "GST amount. That part is reserved until a bill claims it.",
                    ref=approval.name, approved=fmt(approval.gst),
                    reserved=fmt(reserved_gst), others=fmt(billed_before_g),
                    this=fmt(this_gst), avail=fmt(avail)))

    # ---------------- EARLY TDS CHECK ON THE BILL ----------------
    # TDS is part of the taxable bucket and must be deducted once. If a bill
    # carries its own TDS line while TDS was already deducted on an earlier
    # payment (or the other way round), taxable paid + TDS goes beyond the
    # approved taxable. The final block is in _post (Confirm); these checks
    # tell the user much earlier: a warning as soon as the bill's lines change,
    # and a block when approval is requested.
    def _bill_tds_now(self):
        """TDS this bill adds through a tax line on its invoice lines
        (untaxed + GST - total). 0 once posted: it is then already in the
        approval's own figures."""
        self.ensure_one()
        if self.state == 'posted':
            return 0.0
        taxable, gst = self._get_taxable_gst_amounts()
        gross = taxable if self.approval_id.is_reverse_charge else taxable + gst
        return max(gross - self.amount_total, 0.0)

    @api.model
    def _resolve_withholding_approval(self, ref_move):
        """Given the move a withholding (TDS) entry points back to (a bill or a
        payment's own journal entry), find the approval it belongs to, if any."""
        if not ref_move or not ref_move.exists():
            return self.env['bill.approval']
        if ref_move.approval_id:
            return ref_move.approval_id
        if 'origin_payment_id' in ref_move._fields and ref_move.origin_payment_id and ref_move.origin_payment_id.approval_id:
            return ref_move.origin_payment_id.approval_id
        return self.env['bill.approval']

    def _check_tds_entry_within_approved(self):
        """TDS-BUTTON-WITHIN-APPROVED: a TDS smart-button entry, once created (or
        linked via a later write), is checked the same way _post() already checks a
        bill or payment posting -- against the approval's actual current position,
        which by now includes this entry. Unlike an invoice-line TDS tax (which is
        locked once a bill is posted, so it is capped once and for all at that point),
        a smart-button entry can otherwise be added with no ceiling at all, on a bill
        OR on a payment, however many times. Run this AFTER the entry exists (created
        or linked), so approval._payment_position() reflects it; raising here rolls
        back the whole transaction, the same pattern _post() already relies on."""
        fmt = lambda v: '{:,.2f}'.format(v)
        approvals = self.env['bill.approval']
        for move in self:
            ref = move.l10n_in_withholding_ref_move_id if 'l10n_in_withholding_ref_move_id' in move._fields else False
            if ref:
                approvals |= self._resolve_withholding_approval(ref)
        for approval in approvals:
            pos = approval._payment_position()
            if pos['taxable_excess'] > 0.01:
                raise UserError(_(
                    "Cannot add this TDS entry: taxable amount would be over-settled.\n"
                    "Approval: %(ref)s\n"
                    "Approved taxable: %(approved)s\n"
                    "Taxable paid: %(paid)s + TDS deducted (all sources): %(tds)s = %(sum)s\n"
                    "Excess: %(excess)s\n\n"
                    "TDS via the smart button has no ceiling of its own -- it is capped here, "
                    "against what this approval was actually approved for. Reduce this TDS "
                    "entry, or check whether TDS has already been entered elsewhere for the "
                    "same amount (the bill's own line, or another TDS button).",
                    ref=approval.name, approved=fmt(approval.taxable_value),
                    paid=fmt(pos['paid_taxable']), tds=fmt(pos['tds']),
                    sum=fmt(pos['paid_taxable'] + pos['tds']), excess=fmt(pos['taxable_excess'])))
            if pos['gst_excess'] > 0.01:
                raise UserError(_(
                    "Cannot add this TDS entry: GST paid would exceed the approved GST.\n"
                    "Approval: %(ref)s\n"
                    "Approved GST: %(approved)s\n"
                    "GST paid: %(paid)s\n"
                    "Excess: %(excess)s",
                    ref=approval.name, approved=fmt(approval.gst),
                    paid=fmt(pos['paid_gst']), excess=fmt(pos['gst_excess'])))

    def _tds_display_amount(self):
        """TDS-COLUMN: one combined TDS figure for this row, whichever kind of
        account.move it is. For a bill: its own line-tax TDS plus its own TDS
        button. For a payment's own journal entry: that payment's own Other
        Charges TDS plus its own TDS button. Read-only display value, not used
        by any control logic (those already read the four sources separately)."""
        self.ensure_one()
        button_tds = self.l10n_in_total_withholding_amount or 0.0
        if self.move_type in ('in_invoice', 'in_refund'):
            is_tds = lambda t: t and ('tds' in (t.name or '').lower()
                                       or (t.amount_type == 'percent' and t.amount < 0))
            if self.state == 'posted':
                line_tds = -sum(self.line_ids.filtered(lambda l: is_tds(l.tax_line_id)).mapped('balance'))
            else:
                base = sum(self.invoice_line_ids.mapped('price_subtotal'))
                taxed = self.invoice_line_ids.tax_ids.filtered(is_tds)
                line_tds = sum(-t.amount / 100.0 * base for t in taxed) if taxed else 0.0
            return line_tds + button_tds
        if self.origin_payment_id:
            own_charges = -sum(l.other_charge for l in self.origin_payment_id.other_charges_lines if l.other_charge < 0)
            return own_charges + button_tds
        return 0.0

    tds_display_amount = fields.Float(
        string='TDS', compute='_compute_tds_display_amount',
        help="TDS on this row: for a bill, its own line-tax TDS plus its own TDS button; "
             "for a payment's own entry, that payment's own Other Charges TDS plus its own TDS button.")

    @api.depends('l10n_in_total_withholding_amount', 'invoice_line_ids.tax_ids', 'invoice_line_ids.price_subtotal',
                 'line_ids.balance', 'line_ids.tax_line_id')
    def _compute_tds_display_amount(self):
        for move in self:
            move.tds_display_amount = move._tds_display_amount()

    # APPROVAL-AMOUNT-TOTALS: plain-number copies of Tax Excluded / Total, used only by the
    # Bills & Journals list of an approval, so its footer can total them like the TDS column.
    approval_untaxed_display = fields.Float(string='Tax Excluded', compute='_compute_approval_amount_display')
    approval_total_display = fields.Float(string='Total', compute='_compute_approval_amount_display')

    @api.depends('amount_untaxed', 'amount_total')
    def _compute_approval_amount_display(self):
        for move in self:
            move.approval_untaxed_display = move.amount_untaxed
            move.approval_total_display = move.amount_total

    # APPROVAL-BUCKET-COLUMNS: one column per bucket, so no total mixes taxable with GST
    # or bills with payments. Display only -- the controls read the real figures themselves.
    approval_gst_display = fields.Float(string='GST Billed', compute='_compute_approval_bucket_display')
    approval_paid_taxable_display = fields.Float(string='Taxable Paid (cash)', compute='_compute_approval_bucket_display')
    approval_paid_gst_display = fields.Float(string='GST Paid (cash)', compute='_compute_approval_bucket_display')

    @api.depends('move_type', 'amount_untaxed', 'line_ids.balance', 'line_ids.tax_line_id',
                 'origin_payment_id.taxable_paid_amount', 'origin_payment_id.gst_paid_amount', 'origin_payment_id.state')
    def _compute_approval_bucket_display(self):
        for move in self:
            gst = paid_taxable = paid_gst = 0.0
            if move.move_type in ('in_invoice', 'in_refund'):
                gst = move._get_taxable_gst_amounts()[1]
            elif move.origin_payment_id and move.origin_payment_id.state == 'posted':
                paid_taxable = move.origin_payment_id.taxable_paid_amount
                paid_gst = move.origin_payment_id.gst_paid_amount
            move.approval_gst_display = gst
            move.approval_paid_taxable_display = paid_taxable
            move.approval_paid_gst_display = paid_gst

    def _has_line_tds(self):
        """Whether this bill carries TDS through a tax on its own invoice lines --
        state-independent (unlike _bill_tds_now, which is only meaningful pre-post).
        Matches the same 'is this tax a TDS deduction' test used elsewhere (a
        negative-rate percent tax, or one named 'tds')."""
        self.ensure_one()
        is_tds = lambda t: t and ('tds' in (t.name or '').lower()
                                   or (t.amount_type == 'percent' and t.amount < 0))
        if self.state == 'posted':
            return bool(self.line_ids.filtered(lambda l: is_tds(l.tax_line_id)))
        return bool(self.invoice_line_ids.tax_ids.filtered(is_tds))

    def _bill_tds_overshoot(self, fresh=True):
        self.ensure_one()
        approval = self.approval_id
        if not approval or self.move_type != 'in_invoice' or self.state == 'posted':
            return None
        if fresh:
            pos = approval._payment_position()
            paid_taxable, tds = pos['paid_taxable'], pos['tds']
        else:
            paid_taxable, tds = approval.total_taxable_paid, approval.tds_deducted_actual
        bill_tds = self._bill_tds_now()
        return {
            'paid_taxable': paid_taxable, 'tds': tds, 'bill_tds': bill_tds,
            'over': paid_taxable + tds + bill_tds - approval.taxable_value,
        }

    def _tds_overshoot_text(self, b):
        fmt = lambda v: '{:,.2f}'.format(v)
        return _(
            "Approval: %(ref)s\n"
            "Approved taxable: %(approved)s\n"
            "Taxable already paid: %(paid)s\n"
            "TDS already deducted (payments / other bills): %(tds)s\n"
            "TDS on this bill (invoice lines): %(bill)s\n"
            "Total: %(sum)s   Excess: %(excess)s\n\n"
            "TDS is part of the taxable amount and should be deducted only once. "
            "Remove the TDS line from this bill if TDS was already deducted on "
            "the payment, or reverse/reduce the payment.",
            ref=self.approval_id.name, approved=fmt(self.approval_id.taxable_value),
            paid=fmt(b['paid_taxable']), tds=fmt(b['tds']), bill=fmt(b['bill_tds']),
            sum=fmt(b['paid_taxable'] + b['tds'] + b['bill_tds']), excess=fmt(b['over']),
        )

    def _check_tds_frozen_ceiling_on_bill(self, b):
        """Once Level 1 has frozen a TDS figure, this bill's own TDS --
        on top of whatever is already committed elsewhere -- must not
        push the total past it. Same ceiling discipline already
        enforced for payments in _check_payment_buckets, reusing the
        same b['tds'] (committed elsewhere) / b['bill_tds'] (this
        bill's own) split _bill_tds_overshoot already computes."""
        if not b:
            return
        approval = self.approval_id
        if not approval.tds_frozen:
            return
        total = b['tds'] + b['bill_tds']
        excess = total - approval.tds_frozen_amount
        if excess > 0.01:
            fmt = lambda v: '{:,.2f}'.format(v)
            raise UserError(_(
                "Cannot request approval: TDS would exceed the amount frozen "
                "at Level 1 approval.\n"
                "Approval: %(ref)s\n"
                "TDS frozen at Level 1: %(frozen)s\n"
                "TDS already committed (bills + payments): %(committed)s\n"
                "TDS on this bill: %(this)s\n"
                "Total if this is approved: %(total)s\n\n"
                "No bill or payment may deduct TDS beyond what Level 1 approved.",
                ref=approval.name, frozen=fmt(approval.tds_frozen_amount),
                committed=fmt(b['tds']), this=fmt(b['bill_tds']), total=fmt(total),
            ))

    def _check_limit_before_request(self):
        """Called by the Request Approval form when it opens for a bill."""
        self.ensure_one()
        b = self._bill_tds_overshoot(fresh=True)
        if b and float_compare(b['over'], 0.0, precision_rounding=0.01) > 0:
            raise UserError(_("Cannot request approval: TDS looks entered twice.\n") + self._tds_overshoot_text(b))
        self._check_tds_frozen_ceiling_on_bill(b)

    @api.onchange('invoice_line_ids', 'approval_id')
    def _onchange_tds_overshoot_warning(self):
        for move in self:
            b = move._bill_tds_overshoot(fresh=False)
            if b and b['over'] > 0.01:
                return {'warning': {
                    'title': _("TDS looks entered twice"),
                    'message': _("This bill will be refused when approval is requested.\n") + move._tds_overshoot_text(b),
                }}
            if b and move.approval_id and move.approval_id.tds_frozen:
                total = b['tds'] + b['bill_tds']
                excess = total - move.approval_id.tds_frozen_amount
                if excess > 0.01:
                    fmt = lambda v: '{:,.2f}'.format(v)
                    return {'warning': {
                        'title': _("TDS would exceed the Level 1 frozen limit"),
                        'message': (
                            _("Approval: %s") % move.approval_id.name + "\n"
                            + _("TDS frozen at Level 1: %s") % fmt(move.approval_id.tds_frozen_amount) + "\n"
                            + _("Already committed elsewhere: %s") % fmt(b['tds']) + "\n"
                            + _("TDS on this bill: %s") % fmt(b['bill_tds']) + "\n"
                            + _("Over the limit by: %s") % fmt(excess) + "\n\n"
                            + _("Reduce the TDS on this bill -- Request Approval will be "
                                "blocked otherwise.")
                        ),
                    }}

    # ---------------- TDS REFRESH HOOK ----------------
    # The approval's TDS Deducted / Total Payable / Remaining figures are
    # stored computed fields. The TDS total on a bill or payment entry is
    # not reliably a stored field, so posting (or cancelling) a TDS entry
    # made through the smart button never triggered a refresh and the
    # approval kept showing the old figure. Whenever a move is posted,
    # reset to draft or cancelled, find the approval it belongs to (directly,
    # or through the bill/payment a withholding entry points back to) and
    # force those figures to recompute.
    def _get_approvals_for_tds_refresh(self):
        approvals = self.env['bill.approval']
        for move in self:
            if move.approval_id:
                approvals |= move.approval_id
            # A payment's own journal entry.
            if 'origin_payment_id' in move._fields and move.origin_payment_id and move.origin_payment_id.approval_id:
                approvals |= move.origin_payment_id.approval_id
            # A TDS (withholding) entry points back, through
            # l10n_in_withholding_ref_move_id, to EITHER the bill it was
            # raised from OR the journal entry of the payment it was raised
            # from (the Odoo 17 wizard stores related_move_id or
            # related_payment_id.move_id in that one field).
            if 'l10n_in_withholding_ref_move_id' in move._fields:
                ref = move.l10n_in_withholding_ref_move_id
                if ref:
                    if ref.approval_id:
                        approvals |= ref.approval_id
                    if 'origin_payment_id' in ref._fields and ref.origin_payment_id and ref.origin_payment_id.approval_id:
                        approvals |= ref.origin_payment_id.approval_id
        return approvals

    def _refresh_approval_tds_figures(self):
        approvals = self._get_approvals_for_tds_refresh()
        if approvals:
            approvals._force_recompute_balances()

    def _post(self, soft=True):
        # CONTROL: never let the vendor be paid more than was approved, per
        # bucket (taxable vs taxable, GST vs GST; TDS belongs to the taxable
        # bucket and counts as paid) and in total. Runs on every posting
        # linked to an approval, so it covers a payment that is too large AND
        # TDS entered after payments were made (TDS entry, or a bill with a
        # TDS line), which is what pushes the taxable bucket over.
        # Anything that creates or increases an excess is blocked. An
        # approval already in excess can still receive posts that do not make
        # it worse, so corrective entries (reversals) are never trapped.
        approvals = self._get_approvals_for_tds_refresh()
        before = {a.id: a._payment_position() for a in approvals}
        posted = super()._post(soft=soft)
        fmt = lambda v: '{:,.2f}'.format(v)
        for approval in approvals:
            if approval.id not in before:
                continue
            pb = before[approval.id]
            pa = approval._payment_position()
            worse = lambda k: float_compare(pa[k], pb[k], precision_rounding=0.01) > 0
            if worse('taxable_excess'):
                raise UserError(_(
                    "Cannot post: taxable amount would be over-settled.\n"
                    "Approval: %(ref)s\n"
                    "Approved taxable: %(approved)s\n"
                    "Taxable paid: %(paid)s + TDS deducted: %(tds)s = %(sum)s\n"
                    "Excess: %(excess)s\n\n"
                    "TDS is part of the taxable amount. Record TDS before the "
                    "vendor is paid in full, or reverse/reduce the payment first.",
                    ref=approval.name, approved=fmt(approval.taxable_value),
                    paid=fmt(pa['paid_taxable']), tds=fmt(pa['tds']),
                    sum=fmt(pa['paid_taxable'] + pa['tds']),
                    excess=fmt(pa['taxable_excess']),
                ))
            if worse('gst_excess'):
                raise UserError(_(
                    "Cannot post: GST paid would exceed the approved GST.\n"
                    "Approval: %(ref)s\n"
                    "Approved GST: %(approved)s\n"
                    "GST paid: %(paid)s\n"
                    "Excess: %(excess)s",
                    ref=approval.name, approved=fmt(approval.gst),
                    paid=fmt(pa['paid_gst']), excess=fmt(pa['gst_excess']),
                ))
            if worse('total_excess'):
                raise UserError(_(
                    "Cannot post: this would leave the vendor paid more than is payable.\n"
                    "Approval: %(ref)s\n"
                    "Payable after TDS: %(cap)s\n"
                    "Already paid: %(paid)s\n"
                    "Excess: %(excess)s\n\n"
                    "Record TDS before the vendor is paid in full, or reverse "
                    "or reduce the payment first.",
                    ref=approval.name, cap=fmt(pa['cap']), paid=fmt(pa['paid']),
                    excess=fmt(pa['total_excess']),
                ))
            approval._check_tds_revision_reminder()
        posted._refresh_approval_tds_figures()
        return posted

    def button_draft(self):
        res = super().button_draft()
        self._refresh_approval_tds_figures()
        return res

    def button_cancel(self):
        res = super().button_cancel()
        self._refresh_approval_tds_figures()
        return res

    @api.model_create_multi
    def create(self, vals_list):
        # TDS-BUTTON-AFTER-APPROVAL (was ONLY-AFTER-POST): a new withholding (TDS smart-button) entry points
        # back to the move it was raised from via l10n_in_withholding_ref_move_id. TDS may
        # be added through the button only once that bill or payment is Approved or Posted --
        # before posting, TDS goes only on the bill's own invoice line, or the payment's
        # Other Charges. All four places may otherwise carry TDS freely for an already-
        # posted record; the only limit is the aggregate approved-amount ceiling (checked
        # separately, in _check_tds_entry_within_approved below).
        for vals in vals_list:
            ref_id = vals.get('l10n_in_withholding_ref_move_id')
            if ref_id:
                ref_move = self.browse(ref_id)
                if ref_move.exists() and ref_move.approval_id and ref_move.state not in ('approved', 'posted'):
                    if ref_move.move_type == 'in_invoice':
                        where = _("the bill's own invoice line")
                        what = _("Bill %s") % ref_move.display_name
                    else:
                        where = _("the payment's Other Charges")
                        what = _("Payment %s") % (ref_move.origin_payment_id.display_name or ref_move.display_name)
                    raise UserError(_(
                        "Cannot add TDS here: %(what)s is not approved yet.\n"
                        "The TDS button can only be used once approval is complete (Approved or Posted). Until then, "
                        "add TDS through %(where)s instead.",
                        what=what, where=where))
                # PROPAGATE-APPROVAL-TO-TDS-ENTRY: Odoo's own withholding
                # wizard builds this entry's vals with no idea approval_id
                # exists, so a TDS entry raised from an approved bill/
                # payment never carried the link forward on its own --
                # confirmed live via BA-00106's MISC/2026/10/0011 ("TDS of
                # PBNK5/2026/00076"), whose Approvals field sat empty
                # despite being unmistakably tied to BA-00106.
                if ref_move.exists() and ref_move.approval_id and not vals.get('approval_id'):
                    vals['approval_id'] = ref_move.approval_id.id

        records = super().create(vals_list)

        for rec, vals in zip(records, vals_list):
            if vals.get('approval_id'):
                approval = self.env['bill.approval'].browse(vals['approval_id'])
                rec._copy_approval_attachments(vals['approval_id'])
                rec._check_bill_limit(approval)

        # TDS-BUTTON-WITHIN-APPROVED: any of the records just created that are TDS
        # (withholding) entries linked to one of our approvals are checked now, with
        # their amount already reflected.
        withholding_new = records.filtered(
            lambda m: 'l10n_in_withholding_ref_move_id' in m._fields and m.l10n_in_withholding_ref_move_id)
        if withholding_new:
            withholding_new._check_tds_entry_within_approved()

        return records

    def write(self, vals):
        # TDS-BUTTON-AFTER-APPROVAL: same guard as create(), for when the withholding
        # wizard links the entry back to its bill/payment via a separate write() instead.
        ref_id = vals.get('l10n_in_withholding_ref_move_id')
        if ref_id:
            ref_move = self.browse(ref_id)
            if ref_move.exists() and ref_move.approval_id and ref_move.state not in ('approved', 'posted'):
                if ref_move.move_type == 'in_invoice':
                    where = _("the bill's own invoice line")
                    what = _("Bill %s") % ref_move.display_name
                else:
                    where = _("the payment's Other Charges")
                    what = _("Payment %s") % (ref_move.origin_payment_id.display_name or ref_move.display_name)
                raise UserError(_(
                    "Cannot add TDS here: %(what)s is not approved yet.\n"
                    "The TDS button can only be used once approval is complete (Approved or Posted). Until then, "
                    "add TDS through %(where)s instead.",
                    what=what, where=where))

        # CANCEL-CONTEXT-FLAG: flag this on the context, not just in a local variable, so
        # nested write() re-entries triggered internally by Odoo's own dynamic-line
        # recompute during this same operation see it too (see _check_bill_limit).
        if vals.get('state') == 'cancel':
            self = self.with_context(_bafc_skip_bill_limit=True)

        # BILLED-VS-PAID: if this write cancels a bill (or bills) under an approval, make
        # sure doing so would not leave already-settled non-advance payments above what
        # remains billed. Checked BEFORE the write, against the state as it is now.
        if vals.get('state') == 'cancel':
            for approval in self.filtered(lambda m: m.approval_id).mapped('approval_id'):
                approval._check_billed_not_below_paid(exclude_bill_ids=self.ids)

        is_cancel = vals.get('state') == 'cancel'  # CANCEL-SKIPS-BILL-LIMIT
        linking_withholding = 'l10n_in_withholding_ref_move_id' in vals and vals.get('l10n_in_withholding_ref_move_id')
        res = super().write(vals)
        if linking_withholding:  # TDS-BUTTON-WITHIN-APPROVED
            self._check_tds_entry_within_approved()

        # GATE-ON-RELEVANT-FIELDS: only re-validate the bill limit when this write actually
        # changes something that can change what is BOOKED -- the bill's own lines, or which
        # approval it belongs to. Odoo's core account.move write() internally performs its own
        # nested writes as part of dynamic-line bookkeeping (and other unrelated code, such as
        # a budget-figure update on cancel, does the same) -- these touch fields that have
        # nothing to do with taxable/GST content, but without this gate they were still
        # re-triggering this check on every such internal write, sometimes mid-operation
        # (e.g. mid-cancel, before the state change was applied), causing false refusals that
        # no state/context flag could reliably catch, because the internal write could come
        # from anywhere. Gating on the actual relevant fields is correct regardless of WHY or
        # WHEN the write happened, not just for cancel.
        relevant_fields = {'invoice_line_ids', 'line_ids', 'approval_id'}
        touches_relevant = bool(relevant_fields & set(vals.keys()))
        for rec in self:
            if rec.approval_id:
                rec._copy_approval_attachments(rec.approval_id.id)
                if not is_cancel and touches_relevant:
                    rec._check_bill_limit(rec.approval_id)

        return res

    # VENDOR-LOCKED-TO-APPROVAL: a bill linked to an approval must bill the
    # SAME vendor the approval itself was raised for. Nothing else in this
    # module checks partner_id anywhere -- every ceiling/TDS/GST check keys
    # off approval_id alone, so without this, a bill under Peter's approval
    # could silently bill (and later pay) a completely different vendor.
    @api.constrains('partner_id', 'approval_id')
    def _check_partner_matches_approval(self):
        for rec in self:
            if rec.approval_id and rec.partner_id != rec.approval_id.supplier_name:
                raise UserError(_(
                    "Vendor mismatch: this bill is linked to approval %(ref)s, "
                    "which was raised for %(approval_vendor)s -- it cannot be "
                    "billed to %(bill_vendor)s instead. Create a separate bill "
                    "(with no approval) for a different vendor.",
                    ref=rec.approval_id.name,
                    approval_vendor=rec.approval_id.supplier_name.name,
                    bill_vendor=rec.partner_id.name or _('(no vendor selected)'),
                ))

    # VENDOR-FIELD-FROZEN-TO-APPROVAL: once a bill is linked to an approval,
    # the Vendor field must be genuinely non-editable in the form -- not
    # just blocked with an error on save (the constrain above already does
    # that). This edits the already-combined view arch at request time
    # instead of adding a new ir.ui.view that inherits
    # account.view_move_form -- the latter forces Odoo to revalidate that
    # view's ENTIRE combined architecture at module-load time, which on
    # this server trips over an unrelated, pre-existing budget_id /
    # approval_id cross-module view coupling (confirmed to crash module
    # upgrades twice). Doing it here instead never touches any stored view
    # record, so that risk doesn't apply. Only affects moves that actually
    # have approval_id set -- every other account.move is unaffected.
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form':
            doc = etree.fromstring(res['arch'])
            # TOP-LEVEL-PARTNER-ID-ONLY: restrict to field nodes that are
            # not nested inside another field's embedded sub-view (a
            # one2many's list/form, e.g. Invoice Lines, Journal Items, or a
            # linked payment's own partner_id column) -- those belong to a
            # different record/model whose evaluation context has no
            # `approval_id` field at all, and stamping this readonly
            # condition onto them crashed with "Name 'approval_id' is not
            # defined" the moment a new invoice line was added (confirmed
            # via a live arch dump: 7 partner_id nodes existed total, only
            # 2 were genuine top-level fields).
            for node in doc.xpath("//field[@name='partner_id'][not(ancestor::field)]"):
                existing = node.get('readonly')
                node.set('readonly', "(%s) or (approval_id)" % existing if existing else "approval_id")
            # APPROVAL-ID-FIELD-DECLARED: the readonly condition above
            # references `approval_id` in a client-evaluated python
            # expression. The web client only lets a modifier expression
            # reference a field when that field is actually declared as a
            # <field> node somewhere in THIS view's own arch -- it is not
            # enough that `approval_id` exists on the account.move model.
            # Nothing in account.move's stock form declares it, so without
            # this the client throws "Name 'approval_id' is not defined"
            # the moment it evaluates the readonly condition above
            # (confirmed live on the Odoo 18 UAT server -- a dump of the
            # combined arch showed the readonly condition correctly
            # stamped, but no <field name="approval_id"> node anywhere in
            # the form). AccountPayment.get_view() below already does the
            # equivalent for its own injected fields -- same fix, applied
            # here. Idempotent: skip if a field node for it already exists
            # (core or another module).
            if not doc.xpath("//field[@name='approval_id'][not(ancestor::field)]"):
                # VISIBLE-NOT-HIDDEN: shown read-only right after Vendor,
                # matching how it displayed on the v17 server (label
                # "Approvals", read-only since it's set by the approval
                # workflow, never edited from this form directly).
                approval_field = etree.Element('field')
                approval_field.set('name', 'approval_id')
                approval_field.set('readonly', '1')
                # FIRST-NOT-LAST: account.move's combined arch has THREE
                # genuine top-level partner_id nodes, not one -- the main
                # Vendor field, its OCR-placeholder variant, and a third
                # one added by odoo_print_cheque (relabeled "Beneficiary
                # Name", in the Other Info tab). They're all legitimately
                # top-level (not nested in another field's subview), so
                # all three correctly get the "(...) or (approval_id)"
                # readonly stamp above -- but anchoring on the LAST match
                # put this field down next to "Beneficiary Name" instead
                # of next to Vendor (confirmed via a live arch dump on the
                # Odoo 18 UAT server). The main Vendor field is always
                # first in document order, so anchor on the first match.
                partner_nodes = doc.xpath("//field[@name='partner_id'][not(ancestor::field)]")
                if partner_nodes:
                    partner_nodes[0].addnext(approval_field)
                else:
                    doc.append(approval_field)
                if 'approval_id' not in (res.get('fields') or {}):
                    res['fields'] = dict(res.get('fields') or {})
                    res['fields'].update(self.fields_get(['approval_id']))
                models_map = dict(res.get('models') or {})
                existing_names = set(models_map.get(self._name, ()))
                existing_names.add('approval_id')
                models_map[self._name] = tuple(existing_names)
                res['models'] = models_map
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res


class AccountPayment(models.Model):
    _inherit = 'account.payment'

    approval_id = fields.Many2one('bill.approval', string='Bill Approval')

    # GST-vs-Taxable payment split, for GST-paid reporting. The ledger
    # itself has no concept of "this rupee was GST, that rupee was
    # taxable" -- a bill's payable balance is one lump sum -- so this is
    # the only way to get a genuine "GST Paid so far" figure for
    # reporting. Auto-split proportionally (by the linked bill's own
    # taxable:GST ratio) whenever amount or the ticked invoice changes,
    # but the user can still manually edit these before saving (e.g. to
    # do a taxable-only payment now, GST-only payment later) -- the
    # onchange won't re-fire and overwrite a manual edit unless amount or
    # the ticked invoice changes again.
    gst_paid_amount = fields.Float(
        string='GST Paid', tracking=True,
        help="How much of this payment's Amount is meant to settle GST, "
             "as opposed to the taxable base. Auto-split proportionally "
             "from the linked bill's own taxable:GST ratio; edit "
             "manually for a taxable-only or GST-only payment."
    )
    taxable_paid_amount = fields.Float(
        string='Taxable Paid', tracking=True,
        help="How much of this payment's Amount is meant to settle the "
             "taxable base, as opposed to GST. Auto-split proportionally "
             "from the linked bill's own taxable:GST ratio; edit "
             "manually for a taxable-only or GST-only payment."
    )

    # NOTE: deliberately NOT a hard @api.constrains here anymore. A
    # blocking constraint on "gst_paid_amount + taxable_paid_amount must
    # equal amount" sounds safe in principle, but in practice `amount`
    # can be changed by several different code paths in sequence within
    # the same transaction (this module's own write(), the "Update
    # Amount" button, other onchange chains) and Odoo's constraint/flush
    # timing does not reliably guarantee our resync logic runs before the
    # constraint is checked. This repeatedly blocked legitimate,
    # otherwise-correct payments/approvals with no way for the user to
    # fix it except discarding and starting over. Since gst_paid_amount/
    # taxable_paid_amount only feed a REPORTING rollup (total_gst_paid /
    # total_taxable_paid on bill.approval) rather than any real ledger
    # entry, silently self-healing (see write()/create() below and
    # action_post() below) is safer than blocking real work over a
    # reporting-field mismatch.
    def _compute_smart_gst_taxable_split(self):
        """The real (taxable, gst) split for this payment's amount,
        derived from whichever bill it is actually ticked/reconciling
        against (_get_gst_taxable_ratio), falling back to an
        approval-wide estimate when no bill is ticked yet (advance
        phase). This is the glue _get_gst_taxable_ratio /
        _already_taxable_paid_for_bill / _compute_default_gst_taxable_split
        were always written for, but which nothing ever called --
        confirmed live via BA-00106 / PBNK5/2026/00076: GST Paid stayed
        0.00 even after reconciling 5,40,000 against a bill carrying
        real GST, because every existing caller used the dumb
        _derive_split() ("nothing is assumed to be GST") instead."""
        self.ensure_one()
        taxable_target, gst_target = self._get_gst_taxable_ratio()
        already_taxable_paid = self._already_taxable_paid_for_bill()
        if already_taxable_paid is None:
            # No bill ticked yet (advance phase) -- same posted-only,
            # self-excluding scope _already_taxable_paid_for_bill uses,
            # just approval-wide instead of bill-specific.
            others = self.env['account.payment'].search([
                ('approval_id', '=', self.approval_id.id),
                ('state', '=', 'posted'),
            ]) - self._origin
            already_taxable_paid = sum(others.mapped('taxable_paid_amount'))
        return self._compute_default_gst_taxable_split(
            already_taxable_paid, self.amount, taxable_target, gst_target
        )

    def _resync_gst_taxable_split(self, force=False):
        """Force gst_paid_amount/taxable_paid_amount back into sync
        with the current amount AND the bill actually being settled,
        silently. Called leniently (force=False) at write()/create()
        time when amount changes without an explicit split -- skips a
        split that already sums to the amount, so as not to fight a
        value mid-edit. Called FORCED (force=True) right before
        posting: the create()-time default (100%% taxable) always sums
        correctly to the amount by construction, so the lenient check
        would otherwise never fire again even after a bill is ticked
        and reconciled later -- confirmed exactly this via BA-00106 /
        PBNK5/2026/00076.
        """
        for rec in self:
            if not rec.approval_id:
                continue
            if not force and abs((rec.gst_paid_amount + rec.taxable_paid_amount) - rec.amount) <= 0.01:
                continue
            taxable_paid, gst_paid = rec._compute_smart_gst_taxable_split()
            super(AccountPayment, rec).write({
                'taxable_paid_amount': taxable_paid,
                'gst_paid_amount': gst_paid,
            })

    def _get_gst_taxable_ratio(self):
        """Return (net_taxable, gst) for whichever bill this payment is
        actually reconciling against (the ticked payment_invoice_ids
        line), using that BILL's OWN real figures.

        IMPORTANT: net_taxable is the bill's taxable amount MINUS that
        same bill's own TDS (tax-line TDS baked into amount_total, PLUS
        any smart-button TDS on it) -- TDS only ever comes out of the
        taxable side, never GST (matching the confirmed design: "TDS is
        from taxable, GST is only GST"). gst is the bill's full real GST,
        completely untouched by TDS.

        This MUST stay scoped to the single ticked bill, not blended with
        approval-wide totals -- mixing an approval-wide "already paid"
        figure against a single bill's gross target was the actual bug
        that caused GST Paid to be massively understated across multiple
        bills (verified: it silently let TDS eat into the GST bucket
        instead of being fully absorbed by taxable).

        Falls back to the approval's own taxable_value/gst (net of the
        estimate) if no bill is ticked yet (advance-payment phase).
        """
        self.ensure_one()
        ticked = self.payment_invoice_ids.filtered(
            lambda l: l.is_reconcile_amount or l.reconcile_amount
        )[:1]
        if ticked and ticked.invoice_id and ticked.invoice_id.move_id:
            move = ticked.invoice_id.move_id
            taxable = move.amount_untaxed
            gst_lines = move.line_ids.filtered(
                lambda l: l.tax_line_id and 'gst' in (l.tax_line_id.name or '').lower()
            )
            gst = abs(sum(gst_lines.mapped('balance')))
            # This bill's own combined TDS: tax-line TDS (the gap between
            # gross taxable+gst and the bill's real amount_total) PLUS
            # any smart-button TDS already posted on it.
            tax_line_tds = (taxable + gst) - move.amount_total
            smart_tds = move.l10n_in_total_withholding_amount
            net_taxable = taxable - tax_line_tds - smart_tds
            return net_taxable, gst
        if self.approval_id:
            return (
                self.approval_id.taxable_value - self.approval_id.tds_deducted_actual,
                self.approval_id.gst,
            )
        return 0.0, 0.0

    def _already_taxable_paid_for_bill(self):
        """Sum of taxable_paid_amount from OTHER already-posted
        payments reconciled against the SAME bill as this payment's
        ticked invoice line -- scoped per-bill, not approval-wide, for
        the same reason _get_gst_taxable_ratio is bill-scoped (see its
        docstring). Returns 0 if no bill is ticked (advance phase, where
        the approval-wide total_taxable_paid is used instead).
        """
        self.ensure_one()
        ticked = self.payment_invoice_ids.filtered(
            lambda l: l.is_reconcile_amount or l.reconcile_amount
        )[:1]
        if not (ticked and ticked.invoice_id and ticked.invoice_id.move_id):
            return None
        move = ticked.invoice_id.move_id
        other_payments = self.env['account.payment'].search([
            ('payment_invoice_ids.invoice_id.move_id', '=', move.id),
            ('state', '=', 'posted'),
        ]) - self._origin
        return sum(other_payments.mapped('taxable_paid_amount'))

    def _compute_default_gst_taxable_split(self, already_taxable_paid, amount, taxable_target, gst_target):
        """Three-tier fill: taxable first, then GST (capped at the
        bill's own real GST -- never more), then any further excess
        spills back into the taxable bucket as a genuine advance toward
        the approval's yet-unbilled remainder.

        `taxable_target` here is already NET of TDS (see
        _get_gst_taxable_ratio) and `already_taxable_paid` is scoped to
        the SAME bill this payment is settling (see
        _already_taxable_paid_for_bill) -- both bases must match, or GST
        gets silently shortchanged (confirmed bug: mixing an
        approval-wide already-paid figure against a single bill's target
        caused GST Paid to be massively understated once more than one
        bill existed).

        The third tier exists because a payment can legitimately be
        LARGER than the specific bill it's reconciling against (e.g.
        partly settling this bill, partly advancing toward a bill not
        yet raised). Without capping GST at the bill's own real GST
        amount, that excess would all get dumped into gst_paid, wildly
        overstating it beyond what this bill could possibly owe in GST
        (confirmed: an 8,00,000 payment against a 5,10,000 bill would
        otherwise report ~3,80,000 GST paid on a bill whose real GST was
        only 90,000).
        """
        remaining_taxable = max(taxable_target - already_taxable_paid, 0.0)
        if amount <= remaining_taxable:
            return amount, 0.0
        taxable_paid = remaining_taxable
        remaining_after_taxable = amount - remaining_taxable
        if remaining_after_taxable <= gst_target:
            return taxable_paid, remaining_after_taxable
        # Overflow beyond even this bill's full GST -- treat as an
        # advance toward the unbilled remainder, not extra GST.
        gst_paid = gst_target
        overflow = remaining_after_taxable - gst_target
        return taxable_paid + overflow, gst_paid

    # ---------------- SPLIT + BUCKET CONTROL ----------------
    # A payment has no GST field on its form, so unless a bill is ticked in
    # the Invoices grid nobody has said any of it is GST: the WHOLE amount
    # counts against the Taxable bucket. GST is only assigned when a bill
    # that carries GST is ticked (bill-scoped split). This stops an advance
    # payment from silently eating the GST bucket.
    def _has_ticked_bill(self):
        self.ensure_one()
        ticked = self.payment_invoice_ids.filtered(
            lambda l: l.is_reconcile_amount or l.reconcile_amount
        )[:1]
        return bool(ticked and ticked.invoice_id and ticked.invoice_id.move_id)

    def _derive_split(self, amount=None):
        """(taxable, gst) parts of `amount` (default: this payment's amount).
        GST-MANUAL: nothing is assumed to be GST. The whole amount counts as
        Taxable and the user types the GST portion themselves."""
        self.ensure_one()
        amount = self.amount if amount is None else amount
        return amount, 0.0

    def _effective_split(self):
        """The split stored on this payment if it is consistent with the
        amount, otherwise what it would be re-derived to."""
        self.ensure_one()
        if abs((self.gst_paid_amount + self.taxable_paid_amount) - self.amount) <= 0.01:
            return self.taxable_paid_amount, self.gst_paid_amount
        return self._derive_split()

    def _bucket_overshoot(self, approval, t_part, g_part, fresh=True):
        """How far this payment's taxable / GST parts would take each bucket
        beyond the approved amount. TDS is part of the taxable bucket."""
        self.ensure_one()
        tds = approval._payment_position()['tds'] if fresh else approval.tds_deducted_actual
        exclude = [self._origin.id] if self._origin.id else []
        # Same blind spot as _payment_position had: a sibling payment that
        # has cleared approval but not yet been Confirmed sits at 'approved',
        # invisible to a posted-only query, letting a second payment for the
        # same bill pass this very check. Count anything that isn't a
        # throwaway draft or cancelled.
        others = self.env['account.payment'].search([
            ('approval_id', '=', approval.id),
            ('state', 'not in', ('draft', 'cancel')),
            ('id', 'not in', exclude),
        ])
        others_t = sum(others.mapped('taxable_paid_amount'))
        others_g = sum(others.mapped('gst_paid_amount'))
        taxable_left = approval.taxable_value - others_t - tds
        gst_left = 0.0 if approval.is_reverse_charge else approval.gst - others_g
        return {
            'tds': tds, 'others_t': others_t, 'others_g': others_g,
            'taxable_left': taxable_left, 'gst_left': gst_left,
            'taxable_over': t_part - taxable_left,
            'gst_over': 0.0 if approval.is_reverse_charge else g_part - gst_left,
        }

    def _check_advance_not_beyond_bill_reserved(self, approval):

        # REVERT-TO-APPROVED-ONLY: disabled at the user's request. Bills and payments
        # are checked against the APPROVED taxable/GST amounts only, as originally
        # designed. To re-enable this cross-check later, remove this early return.
        return

        """ADVANCE-VS-BILL-RESERVED: the mirror of ADVANCE-RESERVES-BILL in account.move.
        An advance payment (Advance Payment ticked) is otherwise exempt from the
        billed-vs-paid check, because it is meant for money paid before any bill exists.
        But once a bill DOES exist, that bill's own taxable (net of its own TDS) is
        reserved for its OWN payment -- an advance is not entitled to draw on it, only
        on whatever approved capacity the existing bill(s) have not already claimed.
        Ceiling = approved taxable/GST minus what is already billed (and, for taxable,
        minus that billed amount's own TDS)."""
        self.ensure_one()
        if self.payment_type != 'outbound' or not getattr(self, 'advance_payment', False):
            return
        t_part, g_part = self._effective_split()
        own_tds = -sum(l.other_charge for l in self.other_charges_lines if l.other_charge < 0)
        own_tds += self.move_id.l10n_in_total_withholding_amount or 0.0
        Move = self.env['account.move']
        billed_taxable, billed_gst = Move._billed_position(approval)
        bill_tds = approval.tds_bill_lines + approval.tds_bill_button
        exclude = [self._origin.id] if self._origin.id else []
        other_advances = self.env['account.payment'].search([
            ('approval_id', '=', approval.id), ('state', '=', 'posted'),
            ('advance_payment', '=', True), ('id', 'not in', exclude),
        ])
        other_adv_t = 0.0
        for pay in other_advances:
            pay_tds = -sum(l.other_charge for l in pay.other_charges_lines if l.other_charge < 0)
            pay_tds += pay.move_id.l10n_in_total_withholding_amount or 0.0
            other_adv_t += pay.taxable_paid_amount + pay_tds
        other_adv_g = sum(other_advances.mapped('gst_paid_amount'))
        fmt = lambda v: '{:,.2f}'.format(v)
        ceiling_t = max(approval.taxable_value - billed_taxable - bill_tds, 0.0)
        this_total_t = other_adv_t + t_part + own_tds
        if float_compare(this_total_t, ceiling_t, precision_rounding=0.01) > 0:
            raise UserError(_(
                "Cannot request approval: an existing bill already reserves this taxable amount.\n"
                "Approval: %(ref)s\n"
                "Approved taxable: %(approved)s\n"
                "Already billed, with its own TDS: %(billed)s + %(tds)s = %(billedtotal)s\n"
                "Left for an advance payment: %(ceiling)s\n"
                "Already settled by other advance payment(s): %(other)s\n"
                "This payment's taxable (incl. its own TDS): %(this)s\n\n"
                "A bill already exists on this approval and its own taxable amount is reserved for "
                "its own payment. Tie this payment to that bill in the Invoices grid instead of "
                "Advance Payment, or reduce this payment.",
                ref=approval.name, approved=fmt(approval.taxable_value),
                billed=fmt(billed_taxable), tds=fmt(bill_tds), billedtotal=fmt(billed_taxable + bill_tds),
                ceiling=fmt(ceiling_t), other=fmt(other_adv_t), this=fmt(t_part + own_tds)))
        if not approval.is_reverse_charge:
            ceiling_g = max(approval.gst - billed_gst, 0.0)
            this_total_g = other_adv_g + g_part
            if float_compare(this_total_g, ceiling_g, precision_rounding=0.01) > 0:
                raise UserError(_(
                    "Cannot request approval: an existing bill already reserves this GST amount.\n"
                    "Approval: %(ref)s\n"
                    "Approved GST: %(approved)s\n"
                    "Already billed: %(billed)s\n"
                    "Left for an advance payment: %(ceiling)s\n"
                    "Already settled by other advance payment(s): %(other)s\n"
                    "This payment's GST: %(this)s\n\n"
                    "A bill already exists on this approval and its own GST is reserved for its own "
                    "payment. Tie this payment to that bill in the Invoices grid instead of Advance "
                    "Payment, or reduce this payment's GST portion.",
                    ref=approval.name, approved=fmt(approval.gst), billed=fmt(billed_gst),
                    ceiling=fmt(ceiling_g), other=fmt(other_adv_g), this=fmt(g_part)))

    def _check_grid_matches_amount(self, approval):

        # REVERT-TO-APPROVED-ONLY: disabled at the user's request. Bills and payments
        # are checked against the APPROVED taxable/GST amounts only, as originally
        # designed. To re-enable this cross-check later, remove this early return.
        return

        """GRID-MATCHES-AMOUNT: a non-advance payment must actually be TAGGED to the
        bill(s) it is meant to settle -- ticked in the Invoices grid, for the same
        money -- not just correct in rupee terms. Without this, a payment could pass
        every taxable/GST/billed-vs-paid check while being reconciled against the
        wrong bill, a partial amount of the grid, or no bill at all (and Advance
        Payment left unticked, which is itself refused elsewhere, at Confirm, by the
        reconcile module -- this check catches the same problem earlier, at Request
        Approval, with a clearer message naming the approval)."""
        self.ensure_one()
        if self.payment_type != 'outbound' or getattr(self, 'advance_payment', False):
            return
        ticked_total = sum(
            l.reconcile_amount for l in self.payment_invoice_ids
            if l.is_reconcile_amount or l.reconcile_amount
        )
        fmt = lambda v: '{:,.2f}'.format(v)
        if float_compare(ticked_total, self.amount, precision_rounding=0.01) != 0:
            raise UserError(_(
                "Cannot request approval: this payment is not tagged to its bill(s).\n"
                "Approval: %(ref)s\n"
                "Payment amount: %(amount)s\n"
                "Reconcile Amount ticked in the Invoices grid: %(grid)s\n\n"
                "Tick the bill(s) this payment settles in the Invoices grid, so that the "
                "Reconcile Amount total equals the payment amount. Use Update Amount to pay "
                "ticked bills in full, or type each Reconcile Amount yourself for a part "
                "payment. If this payment is genuinely not against a specific bill yet, tick "
                "Advance Payment? instead.",
                ref=approval.name, amount=fmt(self.amount), grid=fmt(ticked_total)))

    def _check_payment_not_above_billed(self, approval):

        # REVERT-TO-APPROVED-ONLY: disabled at the user's request. Bills and payments
        # are checked against the APPROVED taxable/GST amounts only, as originally
        # designed. To re-enable this cross-check later, remove this early return.
        return

        """BILLED-VS-PAID: a payment that settles a specific bill (Advance Payment NOT
        ticked) may not, together with everything else already settled the same way,
        take taxable paid + TDS, or GST paid, above what this approval has actually
        BILLED so far. This is tighter than the approved-amount check: it stops a
        vendor being paid for taxable or GST that has not yet been billed at all.
        An advance payment (Advance Payment ticked) is exempt on purpose -- that is
        what an advance is -- and is governed only by the approved-amount limit."""
        self.ensure_one()
        if self.payment_type != 'outbound' or getattr(self, 'advance_payment', False):
            return
        t_part, g_part = self._effective_split()
        tds = approval._payment_position()['tds']
        exclude = [self._origin.id] if self._origin.id else []
        others = self.env['account.payment'].search([
            ('approval_id', '=', approval.id), ('state', '=', 'posted'),
            ('advance_payment', '=', False), ('id', 'not in', exclude),
        ])
        others_t = sum(others.mapped('taxable_paid_amount'))
        others_g = sum(others.mapped('gst_paid_amount'))
        billed_taxable, billed_gst = self.env['account.move']._billed_position(approval)
        fmt = lambda v: '{:,.2f}'.format(v)
        this_taxable_total = others_t + tds + t_part
        if float_compare(this_taxable_total, billed_taxable, precision_rounding=0.01) > 0:
            raise UserError(_(
                "Cannot request approval: this payment is not covered by any bill.\n"
                "Approval: %(ref)s\n"
                "Billed so far (taxable): %(billed)s\n"
                "Already settled (paid + TDS, non-advance): %(settled)s\n"
                "This payment's taxable portion: %(this)s\n"
                "Available against bills already booked: %(avail)s\n\n"
                "A bill has not yet been booked for this much taxable value. Book the bill "
                "first, or tick Advance Payment? if this is genuinely paid ahead of the bill.",
                ref=approval.name, billed=fmt(billed_taxable), settled=fmt(others_t + tds),
                this=fmt(t_part), avail=fmt(max(billed_taxable - others_t - tds, 0.0))))
        this_gst_total = others_g + g_part
        if not approval.is_reverse_charge and float_compare(this_gst_total, billed_gst, precision_rounding=0.01) > 0:
            raise UserError(_(
                "Cannot request approval: this payment's GST is not covered by any bill.\n"
                "Approval: %(ref)s\n"
                "Billed so far (GST): %(billed)s\n"
                "Already settled GST (non-advance): %(settled)s\n"
                "This payment's GST portion: %(this)s\n"
                "Available against bills already booked: %(avail)s\n\n"
                "A bill has not yet been booked for this much GST. Book the bill first, or "
                "tick Advance Payment? if this is genuinely paid ahead of the bill.",
                ref=approval.name, billed=fmt(billed_gst), settled=fmt(others_g),
                this=fmt(g_part), avail=fmt(max(billed_gst - others_g, 0.0))))

    def _check_payment_buckets(self, approval):
        """Taxable to taxable, GST to GST: this payment's own parts against
        the approved buckets (TDS already deducted counts in taxable)."""
        self.ensure_one()
        if self.payment_type != 'outbound':
            return
        t_part, g_part = self._effective_split()
        b = self._bucket_overshoot(approval, t_part, g_part)
        fmt = lambda v: '{:,.2f}'.format(v)
        if float_compare(b['taxable_over'], 0.0, precision_rounding=0.01) > 0:
            no_gst = _(
                "This payment has no GST portion, so its whole amount counts "
                "against the approved taxable amount.\n") if not g_part else ""
            raise UserError(_(
                "Payment limit exceeded (Taxable)!\n"
                "Approval: %(ref)s\n"
                "Approved taxable: %(approved)s\n"
                "Taxable already paid: %(paid)s\n"
                "TDS deducted (part of taxable): %(tds)s\n"
                "Taxable left for this payment: %(left)s\n"
                "This payment counts as taxable: %(this)s\n\n"
                "%(no_gst)sReduce this payment to %(allowed)s or less.",
                ref=approval.name, approved=fmt(approval.taxable_value),
                paid=fmt(b['others_t']), tds=fmt(b['tds']),
                left=fmt(max(b['taxable_left'], 0.0)), this=fmt(t_part),
                no_gst=no_gst,
                allowed=fmt(max(self.amount - b['taxable_over'], 0.0)),
            ))
        if float_compare(b['gst_over'], 0.0, precision_rounding=0.01) > 0:
            raise UserError(_(
                "Payment limit exceeded (GST)!\n"
                "Approval: %(ref)s\n"
                "Approved GST: %(approved)s\n"
                "GST already paid: %(paid)s\n"
                "This payment's GST portion: %(this)s\n\n"
                "GST is checked against approved GST only.",
                ref=approval.name, approved=fmt(approval.gst),
                paid=fmt(b['others_g']), this=fmt(g_part),
            ))

        # TDS bucket: once Level 1 has frozen a TDS figure, no bill or
        # payment may deduct TDS beyond it -- same bucket discipline as
        # taxable/GST above, enforced here (early, at Request Approval)
        # rather than only at Confirm. Must include THIS payment's own
        # prospective TDS (smart-button withholding on its own move, or
        # an Other Charges TDS line) -- at this point the payment is
        # still draft, so it's invisible to _payment_position()'s own
        # committed tally, the same way its taxable/GST split is added
        # in separately above via t_part/g_part.
        if approval.tds_frozen:
            # This payment's own TDS must be counted exactly once.
            # _payment_position()'s own 'pending' search already
            # includes it once this payment's state has been flipped
            # to a non-draft 'pending'/'to approve' status (which the
            # Approvals framework does BEFORE calling this check, not
            # after) -- so back it out first if it's already there,
            # then add it back in exactly once, rather than assume
            # either way.
            billed_moves = approval.account_move_ids.filtered(
                lambda m: m.move_type != 'entry' and m.state == 'posted'
            )
            own_tds = self.move_id.l10n_in_total_withholding_amount or 0.0
            own_tds += approval._get_payment_charges_tds(self, billed_moves)
            pos = approval._payment_position()
            others_tds = pos['tds']
            if self.state not in ('draft', 'cancel', 'posted'):
                others_tds -= own_tds
            tds_total_if_approved = others_tds + own_tds
            tds_excess = max(tds_total_if_approved - approval.tds_frozen_amount, 0.0)
            if float_compare(tds_excess, 0.0, precision_rounding=0.01) > 0:
                raise UserError(_(
                    "Cannot request approval: TDS would exceed the amount frozen "
                    "at Level 1 approval.\n"
                    "Approval: %(ref)s\n"
                    "TDS frozen at Level 1: %(frozen)s\n"
                    "TDS already committed (bills + other payments): %(committed)s\n"
                    "This payment's own TDS: %(this)s\n"
                    "Total if this is approved: %(total)s\n\n"
                    "No bill or payment may deduct TDS beyond what Level 1 approved.",
                    ref=approval.name, frozen=fmt(approval.tds_frozen_amount),
                    committed=fmt(others_tds), this=fmt(own_tds),
                    total=fmt(tds_total_if_approved),
                ))

    @api.onchange('other_charges_lines', 'amount', 'other_charge_applicable')
    def _onchange_tds_ceiling_warning(self):
        """Live heads-up the moment TDS is typed (Other Charges tab or the
        smart-button withholding), well before Request Approval. Can only
        warn, not block -- the hard stops are _check_payment_buckets (at
        Request Approval) and the bill_approval.py backstop (at Confirm)."""
        if self.payment_type != 'outbound' or not self.approval_id:
            return
        approval = self.approval_id
        if not approval.tds_frozen:
            return
        own_tds = self.move_id.l10n_in_total_withholding_amount or 0.0
        if 'other_charges_lines' in self._fields:
            own_tds += -sum(l.other_charge for l in self.other_charges_lines if l.other_charge < 0)
        if own_tds <= 0:
            return
        pos = approval._payment_position()
        total = pos['tds'] + own_tds
        excess = total - approval.tds_frozen_amount
        if excess > 0.01:
            fmt = lambda v: '{:,.2f}'.format(v)
            return {'warning': {
                'title': _("TDS would exceed the Level 1 frozen limit"),
                'message': (
                    _("Approval: %s") % approval.name + "\n"
                    + _("TDS frozen at Level 1: %s") % fmt(approval.tds_frozen_amount) + "\n"
                    + _("Already committed elsewhere: %s") % fmt(pos['tds']) + "\n"
                    + _("This payment's TDS: %s") % fmt(own_tds) + "\n"
                    + _("Over the limit by: %s") % fmt(excess) + "\n\n"
                    + _("Reduce the TDS on this payment -- Request Approval "
                        "will be blocked otherwise.")
                ),
            }}

    @api.onchange('gst_paid_amount')
    def _onchange_gst_paid_amount(self):
        """TAXABLE-GST-BOTH-EDITABLE: the user edits the GST portion
        directly. Taxable Portion is independently editable too (see
        _onchange_taxable_paid_amount below) -- so instead of treating
        Amount as the master and recomputing Taxable as "whatever's
        left" (which forced a choice between paying Taxable OR GST in a
        single transaction), Amount is now the derived figure: Taxable
        + GST. This lets both portions be settled together in one
        payment. Skipped for Other Charges payments, whose Amount is
        driven by the base amount and the charge lines instead
        (unchanged from before)."""
        for rec in self:
            if not rec.approval_id or getattr(rec, 'other_charge_applicable', False):
                continue
            gst = max(rec.gst_paid_amount or 0.0, 0.0)
            rec.gst_paid_amount = gst
            rec.amount = (rec.taxable_paid_amount or 0.0) + gst

    @api.onchange('taxable_paid_amount')
    def _onchange_taxable_paid_amount(self):
        """TAXABLE-GST-BOTH-EDITABLE: mirrors _onchange_gst_paid_amount
        above -- the user edits the Taxable portion directly; Amount is
        recomputed as Taxable + GST. Same Other-Charges exception as
        above."""
        for rec in self:
            if not rec.approval_id or getattr(rec, 'other_charge_applicable', False):
                continue
            taxable = max(rec.taxable_paid_amount or 0.0, 0.0)
            rec.taxable_paid_amount = taxable
            rec.amount = taxable + (rec.gst_paid_amount or 0.0)

    @api.onchange('amount', 'payment_invoice_ids')
    def _onchange_amount_split_gst(self):
        for rec in self:
            if not rec.approval_id:
                continue
            # A split that already adds up to the Amount is what the user just
            # typed directly into Taxable Portion and/or GST Portion (see
            # TAXABLE-GST-BOTH-EDITABLE above), or was just filled in from it:
            # keep it. Any other change of the Amount starts from the real
            # ticked-bill split again.
            if abs(rec.taxable_paid_amount + rec.gst_paid_amount - rec.amount) <= 0.01:
                continue
            taxable_paid, gst_paid = rec._compute_smart_gst_taxable_split()
            rec.taxable_paid_amount = taxable_paid
            rec.gst_paid_amount = gst_paid

    @api.onchange('amount', 'approval_id', 'gst_paid_amount')
    def _onchange_amount_approval_limit_warning(self):
        for rec in self:
            approval = rec.approval_id
            if not approval or rec.payment_type != 'outbound' or not rec.amount:
                continue
            # WARN-NOT-ON-OPEN: do not pop a warning while the form is still showing
            # the amount pre-filled by the Payment button (default_amount): a dialog
            # raised during the opening of the form can leave the page stuck. The
            # warning starts once the user changes the amount or the GST portion.
            default_amount = self.env.context.get('default_amount')
            if (default_amount is not None
                    and float_compare(rec.amount, default_amount, precision_rounding=0.01) == 0):
                continue
            t_part, g_part = rec._effective_split()
            b = rec._bucket_overshoot(approval, t_part, g_part, fresh=False)
            if b['taxable_over'] > 0.01 or b['gst_over'] > 0.01:
                fmt = lambda v: '{:,.2f}'.format(v)
                return {'warning': {
                    'title': _("Amount is above what is payable"),
                    'message': _(
                        "Approval %(ref)s: this payment counts %(t)s against "
                        "Taxable (%(tl)s left after TDS and payments made) and "
                        "%(g)s against GST (%(gl)s left). A payment with no "
                        "GST portion counts entirely as Taxable. It will be "
                        "rejected when you request approval.",
                        ref=approval.name, t=fmt(t_part), tl=fmt(max(b['taxable_left'], 0.0)),
                        g=fmt(g_part), gl=fmt(max(b['gst_left'], 0.0)),
                    ),
                }}

    def _copy_approval_attachments(self, approval_id):
        if not approval_id:
            return

        attachments = self.env['ir.attachment'].search([
            ('res_model', '=', 'bill.approval'),
            ('res_id', '=', approval_id)
        ])

        for att in attachments:
            existing = self.env['ir.attachment'].search([
                ('res_model', '=', 'account.payment'),
                ('res_id', '=', self.id),
                ('name', '=', att.name),
            ], limit=1)

            if not existing:
                att.copy({
                    'res_model': 'account.payment',
                    'res_id': self.id,
                })

    def _sync_budget_from_bill(self, approval):
        """Copy the Budget (budget_analytic_id) from this approval's
        bill onto the payment's own journal entry (move_id).

        budget_analytic_id lives on account.move (accounts_extended)
        and is normally only set via the date-based lookup there, which
        picks a budget purely by date range on the move's own Accounting
        Date -- it has no awareness of which bill a payment is actually
        settling. Left alone, a payment's move can end up with no budget
        at all (blocking Confirm with "Kindly select a Budget"), or with
        a budget that doesn't match the bill it's paying against.

        Instead, inherit the budget directly from the linked bill: the
        payment should always be attributed to the same budget as the
        bill it's settling, not whatever the date-based lookup guesses.
        Only sets it if not already set, so a manually-chosen budget on
        the payment's move is never silently overwritten.

        BUDGET-SYNC-FIELD-NAME-FIX: this used to reference a field
        called "crossovered_budget", which has never actually existed
        on account.move in this codebase (confirmed via a live field
        probe) -- it crashed with AttributeError the first time this
        method actually ran. The real field, used everywhere else in
        accounts_extended's own budget-by-date logic, is
        budget_analytic_id (Many2one to budget.analytic).
        """
        self.ensure_one()
        if not self.move_id or self.move_id.budget_analytic_id:
            return
        if not approval or not approval.account_move_ids:
            return
        bill_with_budget = approval.account_move_ids.filtered(
            lambda m: m.move_type != 'entry' and m.budget_analytic_id
        )[:1]
        if bill_with_budget:
            self.move_id.budget_analytic_id = bill_with_budget.budget_analytic_id.id

    # ---------------- PAYMENT LIMIT CHECK ----------------
    def _get_approval_tds_withheld(self, approval):
        """Total TDS/withholding already deducted against this approval's
        bill(s), via Odoo's l10n_in_withholding "TDS" smart button.

        That flow creates a *separate* account.move (the withholding move,
        linked back to the original bill via l10n_in_withholding_ref_move_id)
        instead of reducing the original bill's amount_total. Because that
        withholding move is never itself linked via approval_id, it's
        invisible to a plain sum of moves/payments on this approval unless
        we explicitly pull it in here.

        TDS entered directly as a tax line on the bill's own invoice lines
        is NOT handled here on purpose: that kind of TDS already reduces
        the bill's own amount_total, so it's already correctly reflected
        by _check_bill_limit()/amount_total and must not be subtracted a
        second time here.

        Coded defensively: l10n_in_withholding is an optional India
        localization module, so we check the field exists before using it
        rather than adding a hard dependency on it.
        """
        moves = self.env['account.move'].search([
            ('approval_id', '=', approval.id), ('move_type', '!=', 'entry'),
        ])
        if 'l10n_in_total_withholding_amount' not in moves._fields:
            return 0.0
        # l10n_in_total_withholding_amount already only sums *posted*
        # withholding entries, so draft/unconfirmed TDS wizards don't
        # prematurely eat into the available payment headroom.
        return sum(moves.mapped('l10n_in_total_withholding_amount'))

    def _check_payment_limit(self, approval):
        self.ensure_one()

        # Only enforce the cap once the payment is actually being
        # finalized (posted). While a payment is still in 'draft', the UI
        # legitimately passes through intermediate/incorrect amounts --
        # e.g. the "Invoices" reconciliation grid (partial_payment_adjustment
        # module) auto-saves the record's current on-screen amount BEFORE
        # its own "Update Amount" button logic runs and corrects it. If we
        # enforce the cap on every draft write, that auto-save trips this
        # check with a transient, not-yet-corrected amount and blocks the
        # user from ever reaching the correct figure. The real, authoritative
        # enforcement now happens in action_post() below.
        if self.state in ('draft', 'cancel'):
            return

        # IMPORTANT: only count payments that are already POSTED, plus
        # self (which is mid-action_post() when this runs). Other unrelated
        # DRAFT payments on the same approval must NOT count towards the
        # cap here -- otherwise posting a single valid payment could be
        # incorrectly blocked just because an unrelated/unfinished draft
        # happens to exist alongside it. Drafts are allowed to coexist
        # (needed for the reconciliation-grid UX above); only actual
        # postings are financially real and must be capped.
        posted_payments = self.env['account.payment'].search([
            ('approval_id', '=', approval.id),
            ('state', '=', 'posted'),
        ])
        total = sum(posted_payments.mapped('amount'))
        if self.id not in posted_payments.ids:
            total += self.amount

        # The cap is ALWAYS measured against the full APPROVED amount --
        # booking a bill (even a partial one) must never shrink the
        # ceiling on its own. Only actual POSTED PAYMENTS reduce
        # available headroom (via `total` below); TDS is netted off using
        # the best figure currently known (the real, combined TDS across
        # whatever's been billed so far if any bill exists, else the
        # approval-time estimate) -- but the BASE stays the full approved
        # taxable+gst throughout, so advance payments can always proceed
        # up to the full approved amount regardless of how much has (or
        # hasn't) been billed yet.
        # Single definition of the ceiling lives on the approval
        # (bill.approval._get_payment_cap) so this check and the
        # "Balance Payable / Excess Paid" columns can never disagree:
        # approved taxable (+ GST unless RCM) minus the TDS known so far,
        # from whichever of the three places it was entered.
        cap = approval._get_payment_cap()

        # Taxable to taxable, GST to GST first (most specific message), then
        # the overall ceiling.
        # Only while the payment is still waiting to be posted: once posted,
        # the post-time guard in account.move._post has already ruled on it,
        # and re-testing a posted (possibly older) payment on every write
        # would trap corrective actions on approvals that are already over.
        if self.state != 'posted':
            self._check_payment_buckets(approval)
            self._check_payment_not_above_billed(approval)  # BILLED-VS-PAID
            self._check_advance_not_beyond_bill_reserved(approval)  # ADVANCE-VS-BILL-RESERVED
            self._check_grid_matches_amount(approval)  # GRID-MATCHES-AMOUNT

        if float_compare(total, cap, precision_rounding=0.01) > 0:
            self._raise_payment_limit_error(cap, total - self.amount)

    def _check_charge_line_accounts(self, commands):
        """CHARGE-ACCOUNT-CHECK: an Other Charges line must post to a usable account.
        A tax with no account is silently skipped when the entry is built, so the
        deduction would reduce the payment but never reach the books; a deprecated
        account cannot be posted at all. Refuse both at save, saying which tax."""
        Tax = self.env['account.tax']
        Acc = self.env['account.account']
        for cmd in commands or []:
            if not (isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] in (0, 1)
                    and isinstance(cmd[2], dict)):
                continue
            lv = cmd[2]
            if not lv.get('tax_id'):
                continue
            tax = Tax.browse(lv['tax_id'])
            acc = Acc.browse(lv['account_id']) if lv.get('account_id') else tax.invoice_repartition_line_ids.filtered(
                lambda l: l.account_id and l.repartition_type != 'base')[:1].account_id
            if not acc:
                raise UserError(_(
                    "The tax %s has no account to post to, so it cannot be used in Other Charges. "
                    "Choose another tax, or set an account on the tax's repartition lines.") % tax.display_name)
            if getattr(acc, 'deprecated', False):
                raise UserError(_(
                    "The tax %(tax)s posts to the account %(acc)s, which is deprecated, so this payment "
                    "cannot be posted. Choose another tax, or replace the account on the tax.") % {
                        'tax': tax.display_name, 'acc': acc.display_name})

    def _raise_payment_limit_error(self, cap, others):
        """One message for every place the payment limit is enforced."""
        fmt = lambda v: '{:,.2f}'.format(v)
        raise UserError(_(
            "Payment limit exceeded!\n"
            "Payable for this approval (after GST-RCM / TDS): %(cap)s\n"
            "Already paid (posted payments): %(others)s\n"
            "This payment: %(this)s\n"
            "Excess: %(excess)s\n\n"
            "Reduce this payment to %(allowed)s or less.",
            cap=fmt(cap), others=fmt(others), this=fmt(self.amount),
            excess=fmt(others + self.amount - cap),
            allowed=fmt(max(cap - others, 0.0)),
        ))

    def _check_limit_before_request(self):
        """Called by the Request Approval form (request.approval.default_get)
        the moment it opens for a payment, so an over-limit payment is
        stopped BEFORE the user fills in and submits the request. Same limit
        as at submit / confirm (fresh TDS, posted payments only)."""
        self.ensure_one()
        approval = self.approval_id
        if not approval or self.payment_type != 'outbound':
            return
        if self.id and self.state != 'posted' and float_compare(self.amount, 0.0, precision_rounding=0.01) <= 0:
            raise UserError(_(
                "Enter the payment amount before requesting approval. The GST portion is part of "
                "the amount, not on top of it: to pay only the GST, set both the Amount and the "
                "GST portion to the GST figure."))
        pos = approval._payment_position()
        others = pos['paid']
        if self.id and self.state == 'posted':
            return
        self._check_payment_buckets(approval)
        self._check_payment_not_above_billed(approval)  # BILLED-VS-PAID
        self._check_advance_not_beyond_bill_reserved(approval)  # ADVANCE-VS-BILL-RESERVED
        self._check_grid_matches_amount(approval)  # GRID-MATCHES-AMOUNT
        if float_compare(others + self.amount, pos['cap'], precision_rounding=0.01) > 0:
            self._raise_payment_limit_error(pos['cap'], others)

    def _check_no_redundant_payment_on_create(self, approval, new_vals):
        """Blocks creating a brand-new payment outright once existing
        payment(s) already linked to this approval -- draft or posted --
        already cover the outstanding balance on its posted bill(s).

        This is safe from the "Update Amount" false-block issue (see
        _check_payment_limit above) because it only ever looks at OTHER,
        already-existing payment records' amounts -- never at the amount
        of the record currently being created. The reconciliation-grid
        flow's transient wrong-then-corrected value only ever affects a
        record's OWN amount at its OWN first save, so checking against
        already-settled prior records never trips on that.

        If there are no posted bills yet at all, there's nothing to be
        "already covered" against, so creation is allowed through (e.g.
        advance payments made before any bill exists).
        """
        bills = self.env['account.move'].search([
            ('approval_id', '=', approval.id),
            ('move_type', '!=', 'entry'),
            ('state', '=', 'posted'),
        ])
        if not bills:
            return

        outstanding = sum(bills.mapped('amount_residual'))
        if outstanding <= 0:
            raise UserError(_(
                "This approval is already fully settled -- the linked "
                "bill(s) have no outstanding balance. No further payment "
                "entries can be created against it."
            ))

        # NOTE: deliberately NOT also comparing against other existing
        # DRAFT payments' amounts here. That was tried and reverted --
        # draft account.payment records can appear (and even transiently
        # duplicate) purely as a side effect of normal UI interaction
        # (Odoo auto-saves an in-progress record the moment any button is
        # clicked, e.g. ticking a checkbox in the Invoices reconciliation
        # grid), well before the user has actually finished or intended to
        # finalize anything. A check based on draft-state data is
        # therefore unreliable and produces false positives ("a payment
        # has already been recorded" when nothing was ever really
        # recorded/finished). The `outstanding <= 0` check above is safe
        # because it only reacts to genuinely POSTED bill state.
        # Preventing a duplicate PAYMENT specifically is instead handled
        # at action_post() time by _check_payment_limit, which correctly
        # counts only posted payments (+ self) -- coexisting drafts are
        # harmless until one is actually posted.

    @api.model_create_multi
    def create(self, vals_list):
        # Auto-fill the GST/Taxable split BEFORE create(), not just via
        # the client-side onchange -- the onchange only fires on an
        # actual UI field-change event, but Amount is often just a
        # pre-filled context default (e.g. action_open_payment's
        # default_amount) that the user never manually edits. In that
        # case the onchange never runs, gst_paid_amount/taxable_paid_amount
        # stay at 0, and _check_gst_taxable_split then rejects the very
        # first save. Computing the split here guarantees it's correct
        # regardless of what happened (or didn't) in the browser.
        for vals in vals_list:
            if vals.get('approval_id') and vals.get('amount') and not (
                vals.get('gst_paid_amount') or vals.get('taxable_paid_amount')
            ):
                # No bill can be ticked yet at create() time, and a payment has
                # no GST field, so the whole amount counts as taxable. If a
                # bill is ticked later, the onchange / write() resync assigns
                # the bill's GST portion.
                vals['taxable_paid_amount'] = vals['amount']
                vals['gst_paid_amount'] = 0.0
        for vals in vals_list:
            if vals.get('other_charges_lines'):
                self._check_charge_line_accounts(vals['other_charges_lines'])
        # OTHER-CHARGES-AMOUNT: with Other Charges the payment Amount is the base amount plus the
        # charge lines (TDS is negative). The form does not always update the Amount when a line is
        # added, and a mismatch makes the journal entry get rebuilt twice (two bank lines, which
        # Odoo refuses). So take the charge amounts the form sends and set the Amount from them.
        for vals in vals_list:
            if vals.get('other_charge_applicable') and vals.get('payment_base_amount') and vals.get('other_charges_lines'):
                charges = []
                for cmd in vals['other_charges_lines']:
                    if (isinstance(cmd, (list, tuple)) and len(cmd) == 3 and cmd[0] == 0
                            and isinstance(cmd[2], dict) and 'other_charge' in cmd[2]):
                        charges.append(cmd[2]['other_charge'] or 0.0)
                    else:
                        charges = None
                        break
                if charges is not None:
                    expected = vals['payment_base_amount'] + sum(charges)
                    if float_compare(vals.get('amount') or 0.0, expected, precision_rounding=0.01) != 0:
                        vals['amount'] = expected
        # GST-FIX: when a GST portion is given, the stored taxable portion is always
        # amount - GST, using the real amount, whatever the screen sent.
        for vals in vals_list:
            if vals.get('approval_id') and vals.get('gst_paid_amount'):  # ZERO-AMOUNT-CHECK
                if float_compare(vals['gst_paid_amount'], vals.get('amount') or 0.0, precision_rounding=0.01) > 0:
                    raise UserError(_("The GST portion cannot be more than the payment amount. The GST portion is part of the "
                      "amount, not on top of it: to pay only the GST, set both the Amount and the GST "
                      "portion to the GST figure."))
                vals['taxable_paid_amount'] = (vals.get('amount') or 0.0) - vals['gst_paid_amount']

        records = super().create(vals_list)

        for rec, vals in zip(records, vals_list):
            if vals.get('approval_id'):
                approval = self.env['bill.approval'].browse(vals['approval_id'])
                rec._check_no_redundant_payment_on_create(approval, vals)
                rec._copy_approval_attachments(vals['approval_id'])
                rec._sync_budget_from_bill(approval)
                rec._check_payment_limit(approval)

        return records

    def write(self, vals):
        # If 'amount' is changing here but the caller did NOT also
        # explicitly set gst_paid_amount/taxable_paid_amount in this same
        # write, re-derive the split automatically afterwards. This is
        # necessary because `amount` can legitimately be changed by code
        # we don't control at all -- e.g. partial_payment_adjustment's
        # "Update Amount" button, which recalculates `amount` from
        # multiple ticked invoices with no knowledge that our split
        # fields exist. Without this, the split silently goes stale and
        # trips _check_gst_taxable_split's constraint on save, even
        # though the user did nothing wrong.
        resync_split = 'amount' in vals and not (
            'gst_paid_amount' in vals or 'taxable_paid_amount' in vals
        )

        res = super().write(vals)

        for rec in self:
            if rec.approval_id:
                rec._copy_approval_attachments(rec.approval_id.id)
                rec._sync_budget_from_bill(rec.approval_id)
                if resync_split:
                    taxable_paid, gst_paid = rec._derive_split()
                    super(AccountPayment, rec).write({
                        'taxable_paid_amount': taxable_paid,
                        'gst_paid_amount': gst_paid,
                    })
                if 'other_charges_lines' in vals:
                    rec._check_charge_line_accounts(vals['other_charges_lines'])
                if 'gst_paid_amount' in vals and not resync_split:
                    # GST-FIX: stored taxable = real amount - GST typed.
                    if float_compare(rec.gst_paid_amount, rec.amount, precision_rounding=0.01) > 0:
                        raise UserError(_("The GST portion cannot be more than the payment amount. The GST portion is part of the "
                      "amount, not on top of it: to pay only the GST, set both the Amount and the GST "
                      "portion to the GST figure."))
                    super(AccountPayment, rec).write({
                        'taxable_paid_amount': rec.amount - rec.gst_paid_amount,
                    })
                rec._check_payment_limit(rec.approval_id)

        return res

    def action_post(self):
        # This is the authoritative enforcement point: by the time a
        # payment is posted, any in-progress reconciliation-grid editing
        # (ticking invoices, "Update Amount", etc.) is finished and
        # rec.amount reflects the user's final intent. Block posting here
        # rather than relying on draft-time writes, which can fire mid-edit
        # with a transient amount (see _check_payment_limit above).
        self._resync_gst_taxable_split(force=True)
        for rec in self:
            if rec.approval_id:
                rec._check_payment_limit(rec.approval_id)
        return super().action_post()

    # VENDOR-LOCKED-TO-APPROVAL: same guarantee as on account.move -- a
    # payment linked to an approval must pay the SAME vendor the approval
    # was raised for.
    @api.constrains('partner_id', 'approval_id')
    def _check_partner_matches_approval(self):
        for rec in self:
            if rec.approval_id and rec.partner_id != rec.approval_id.supplier_name:
                raise UserError(_(
                    "Vendor mismatch: this payment is linked to approval "
                    "%(ref)s, which was raised for %(approval_vendor)s -- it "
                    "cannot pay %(payment_vendor)s instead. Create a separate "
                    "payment (with no approval) for a different vendor.",
                    ref=rec.approval_id.name,
                    approval_vendor=rec.approval_id.supplier_name.name,
                    payment_vendor=rec.partner_id.name or _('(no vendor selected)'),
                ))

    # VENDOR-FIELD-FROZEN-TO-APPROVAL: same freeze as AccountMove above,
    # applied to the payment's own Vendor field.
    def get_view(self, view_id=None, view_type='form', **options):
        res = super().get_view(view_id=view_id, view_type=view_type, **options)
        if view_type == 'form':
            doc = etree.fromstring(res['arch'])
            # TOP-LEVEL-PARTNER-ID-ONLY: restrict to field nodes that are
            # not nested inside another field's embedded sub-view (a
            # one2many's list/form, e.g. Invoice Lines, Journal Items, or a
            # linked payment's own partner_id column) -- those belong to a
            # different record/model whose evaluation context has no
            # `approval_id` field at all, and stamping this readonly
            # condition onto them crashed with "Name 'approval_id' is not
            # defined" the moment a new invoice line was added (confirmed
            # via a live arch dump: 7 partner_id nodes existed total, only
            # 2 were genuine top-level fields).
            for node in doc.xpath("//field[@name='partner_id'][not(ancestor::field)]"):
                existing = node.get('readonly')
                node.set('readonly', "(%s) or (approval_id)" % existing if existing else "approval_id")
            # TAXABLE-GST-PORTION-INJECT: injects the Taxable/GST Portion
            # fields at request time instead of via a stored ir.ui.view --
            # see this patch's module docstring for why (a new ir.ui.view
            # here forces a module-load-time revalidation that crashes on
            # accounts_extended's approval_state field, confirmed twice).
            amount_labels = doc.xpath("//label[@for='amount']")
            if amount_labels:
                label_node = amount_labels[0]
                injected_field_names = []
                for fname, fattrs in (
                    # VISIBLE-NOT-HIDDEN (payment side): this was shipped
                    # invisible (a bug carried over from the v17 source
                    # itself, not introduced by the v18 migration) -- v17's
                    # live production server showed a visible "Bill
                    # Approval: BA-xxxxx" reference on this same form, but
                    # that came from elsewhere (not this injected field),
                    # so it was never caught. Made visible here, read-only,
                    # using the string the v17 server displayed.
                    ('approval_id', {'string': 'Bill Approval', 'readonly': '1'}),
                    ('taxable_paid_amount', {
                        'string': 'Taxable Portion',
                        'readonly': "state != 'draft'",
                        'invisible': "not approval_id or payment_type != 'outbound'",
                        # ONCHANGE-ATTR-ADDED: Odoo normally writes this
                        # onto a field node during its own view
                        # post-processing (_postprocess_on_change), which
                        # runs BEFORE we inject this node -- without it,
                        # the client never calls onchange() when the user
                        # types here, so Amount never updates.
                        'on_change': '1',
                    }),
                    ('gst_paid_amount', {
                        'string': 'GST Portion',
                        'readonly': "state != 'draft'",
                        'invisible': "not approval_id or payment_type != 'outbound'",
                        'on_change': '1',
                    }),
                ):
                    new_field = etree.Element('field')
                    new_field.set('name', fname)
                    for attr_name, attr_value in fattrs.items():
                        new_field.set(attr_name, attr_value)
                    label_node.addprevious(new_field)
                    injected_field_names.append(fname)
                # FIELDS-METADATA-MERGE-V2: the web client checks BOTH
                # res['models'][model] (which field names are known/
                # loadable for this model -- confirmed via an Odoo shell
                # probe to be a frozendict of {model: tuple(field_names)},
                # NOT including our injected fields by default -- this is
                # exactly why the client threw '"account.payment".
                # "taxable_paid_amount" field is undefined') and
                # res['fields'] (the per-field type/label metadata). Both
                # were computed by super().get_view() BEFORE we injected
                # these new <field> nodes, so both need our field names
                # added now, without overwriting anything already present.
                # 'models' is a frozendict, so it must be rebuilt as a
                # plain dict before its account.payment entry can be
                # updated.
                missing = [n for n in injected_field_names if n not in (res.get('fields') or {})]
                if missing:
                    res['fields'] = dict(res.get('fields') or {})
                    res['fields'].update(self.fields_get(missing))
                models_map = dict(res.get('models') or {})
                existing_names = set(models_map.get(self._name, ()))
                existing_names.update(injected_field_names)
                models_map[self._name] = tuple(existing_names)
                res['models'] = models_map
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res


# NO-PAYMENT-OUTSIDE-APPROVAL
# A vendor bill that belongs to an approval is paid ONLY from that approval (its Payment
# button). The standard "Register Payment" wizard creates a payment with no approval on it, so
# none of the approval's limits would see it, and an advance that has not been matched to the
# bill yet leaves the bill open to be paid a second time. Refuse it, and say where to pay.
class AccountPaymentRegister(models.TransientModel):
    _inherit = 'account.payment.register'

    def action_create_payments(self):
        for wizard in self:
            bills = wizard.line_ids.move_id.filtered(lambda m: m.move_type == 'in_invoice' and m.approval_id)
            if bills:
                raise UserError(_(
                    "Bill %(bills)s belongs to approval %(approvals)s, so it cannot be paid from here.\n"
                    "Open the approval and use its Payment button. Every payment must be made from the "
                    "approval, so that it is checked against the approved taxable and GST amounts.",
                    bills=', '.join(bills.mapped('name')),
                    approvals=', '.join(bills.mapped('approval_id.name'))))
        return super().action_create_payments()
