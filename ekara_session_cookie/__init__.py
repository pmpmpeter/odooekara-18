import odoo.http as odoo_http

ODOO_NAME = 'session_id'
OWN_NAME = 'session_id_o18'

_orig_call = odoo_http.Application.__call__


def _patched_call(self, environ, start_response):
    # Incoming: ignore Odoo 17's session_id, and present ours to Odoo as session_id
    cookie = environ.get('HTTP_COOKIE')
    if cookie:
        parts = []
        for part in cookie.split(';'):
            name, sep, value = part.strip().partition('=')
            if name == ODOO_NAME:
                continue
            if name == OWN_NAME:
                name = ODOO_NAME
            if name:
                parts.append(f'{name}{sep}{value}')
        environ['HTTP_COOKIE'] = '; '.join(parts)

    # Outgoing: rename Set-Cookie session_id -> session_id_o18
    def _start_response(status, headers, exc_info=None):
        new_headers = []
        for key, value in headers:
            if key.lower() == 'set-cookie' and value.startswith(ODOO_NAME + '='):
                value = OWN_NAME + value[len(ODOO_NAME):]
            new_headers.append((key, value))
        return start_response(status, new_headers, exc_info)

    return _orig_call(self, environ, _start_response)


odoo_http.Application.__call__ = _patched_call
