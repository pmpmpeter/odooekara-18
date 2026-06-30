# -*- coding: utf-8 -*-
#############################################################################
#    A part of Open HRMS Project <https://www.openhrms.com>
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2023-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from markupsafe import Markup


class HrAnnouncement(models.Model):
    """ Model representing the HR Announcements"""
    _name = 'hr.announcement'
    _description = 'HR Announcement'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Code No:',
                       help="Sequence of Announcement")
    announcement_reason = fields.Text(string='Title', required=True,
                                      help="Announcement subject")
    state = fields.Selection(
        selection=[('draft', 'Draft'), ('to_approve', 'Waiting For Approval'),
                   ('approved', 'Approved'), ('rejected', 'Refused'),
                   ('expired', 'Expired')],
        string='Status', default='draft', help="State of announcement.",
        track_visibility='always')
    requested_date = fields.Date(string='Requested Date',
                                 default=fields.Datetime.now().
                                 strftime('%Y-%m-%d'),
                                 help="Create date of record")
    attachment_id = fields.Many2many(
        'ir.attachment', 'doc_warning_rel', 'doc_id', 'attach_id4',
        string="Attachment", help='Attach copy of your document')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.user.company_id,
                                 readonly=True, help="Login user Company")
    is_announcement = fields.Boolean(string='Is general Announcement?',
                                     help="Enable, if this is a "
                                          "General Announcement")
    announcement_type = fields.Selection(
        [('employee', 'By Employee'), ('department', 'By Department'),
         ('job_position', 'By Job Position')], string="Announcement Type",
        help="By Employee: Announcement intended for specific Employees.\n"
             "By Department: Announcement intended for Employees in "
             "specific Departments.\n"
             "By Job Position: Announcement intended for Employees "
             "who are having specific Job Positions")
    employee_ids = fields.Many2many('hr.employee', 'hr_employee_announcements',
                                    'announcement', 'employee',
                                    string='Employees',
                                    help="Employees who want to see "
                                         "this announcement")
    department_ids = fields.Many2many('hr.department',
                                      'hr_department_announcements',
                                      'announcement', 'department',
                                      string='Departments',
                                      help="Department which can see "
                                           "this announcement")
    position_ids = fields.Many2many('hr.job', 'hr_job_position_announcements',
                                    'announcement', 'job_position',
                                    string='Job Positions',
                                    help="Position of the employee "
                                         "who is authorized "
                                         "to view this announcements.")
    announcement = fields.Html(string='Letter', help="Announcement message")
    date_start = fields.Date(string='Start Date', default=fields.Date.today(),
                             required=True, help="Start date of announcement")
    date_end = fields.Date(string='End Date', default=fields.Date.today(),
                           required=True, help="End date of announcement")

    @api.constrains('date_start', 'date_end')
    def _check_date_start(self):
        """ Raise validation error when start date is greater than end date """
        if self.date_start > self.date_end:
            raise ValidationError(_("The Start Date must be earlier "
                                    "than the End Date"))

    @api.model
    def create(self, vals):
        """ Create method for HrAnnouncement model, adding sequence
        number to announcements. """
        if vals.get('is_announcement'):
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'hr.announcement.general')
        else:
            vals['name'] = self.env['ir.sequence'].next_by_code(
                'hr.announcement')

        announcements = super(HrAnnouncement, self).create(vals)

        employees = self.env['hr.employee'].search([])
        partners = employees.mapped('user_id.partner_id')

        for announcement in announcements:
            if announcement.attachment_id:
                announcement.attachment_id.write({
                    'res_model': self._name,
                    'res_id': announcement.id
                })

            if partners:
                base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
                announcement_url = f"{base_url}/web#id={announcement.id}&model=hr.announcement&view_type=form"

                message = Markup(
                    "Announcement Name: %s<br/>"
                    "Announcement Title: %s<br/>"
                    "<a href='%s' target='_blank'>Open Announcement</a>"
                ) % (
                              announcement.name,
                              announcement.announcement_reason,
                              announcement_url
                          )
                announcement.message_post(
                    body=message,
                    subject="New Announcement Created",
                    partner_ids=partners.ids,
                    message_type="notification"
                )

        return announcements

    def get_expiry_state(self):
        """
        Expire announcements based on their End date, triggered by a
        scheduled cron job.
        """
        announcements = self.search([('state', '!=', 'rejected')])
        for announcement in announcements:
            if announcement.date_end < fields.Date.today():
                announcement.write({
                    'state': 'expired'
                })

    def unlink(self):
        """
        Prevent deletion of records not in 'Draft' state unless performed by an admin.
        """
        if not self.env.is_admin():
            if any(record.state != 'draft' for record in self):
                raise ValidationError(
                    _("You can delete a record only in the 'Draft' state.")
                )
        return super(HrAnnouncement, self).unlink()
