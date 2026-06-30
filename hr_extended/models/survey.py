from odoo import fields, models, _

class SurveySurvey(models.Model):
    _inherit = 'survey.survey'

    start_date = fields.Date(string='Start Date', required=True)
    end_date = fields.Date(string='End Date', required=True)
