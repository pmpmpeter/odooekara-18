from odoo import http
from odoo.http import request


class HRDashboardController(http.Controller):


    @http.route(
        '/hr_dashboard',
        auth='user',
        website=False
    )
    def hr_dashboard(self):


        values=request.env[
        'hr.dashboard'
        ].dashboard_values()


        return request.render(

        'ekara_dashboard.dashboard_template',

        values

        )