# -*- coding: utf-8 -*-

from odoo import models, fields, api, _


class PerformanceReviewPopup(models.TransientModel):
    _name = "performance.review.refuse.popup"
    _description = "Performance ReviewPopup Refuse Popup"

    refuse_reason = fields.Char(string='Reason', track_visibility=True)
    employee_rating_id = fields.Many2one('self.rating', string='Self Rating #')

    def refuse_process(self):
        if self.employee_rating_id:
            self.employee_rating_id.state = 'preparation'
            self.employee_rating_id.refuse_reason = self.refuse_reason

