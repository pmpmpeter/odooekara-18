from odoo import http
from odoo.http import request
from odoo.exceptions import UserError, ValidationError
import base64

class DocumentController(http.Controller):
    @http.route('/document/download/pdf/<int:record_id>', type='http', auth='user')
    def document_download_pdf(self, record_id):
        record = request.env['document.request'].sudo().browse(record_id)
        if not record or not record.pdf_document:
            raise UserError("The requested file does not exist.")
        record.multi_download = True
        pdf_content = base64.b64decode(record.pdf_document)
        return request.make_response(
            pdf_content,
            headers=[
                ('Content-Type', 'application/pdf'),
                ('Content-Disposition', f'attachment; filename={record.pdf_filename}'),
            ]
        )

