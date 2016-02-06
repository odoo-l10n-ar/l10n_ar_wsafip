# -*- coding: utf-8 -*-
from openerp import fields, models, api
from suds.client import Client
from sslhttps import HttpsTransport

__URLError = {
    101: 'network_down',
    104: 'connection_rejected',
    -2: 'unknown_service'
}

class wsafip_server(models.Model):
    _name = "wsafip.server"

    @api.multi
    def get_state(self, conn):
        self.ensure_one()

        try:
            conn.login()
        except urllib2.URLError as e:
            return __URLError.get(e[0][0], 'err:%i' % e[0][0])
        except Exception as e:
            return 'something_wrong'

        return conn.state

    @api.multi
    def client(self):
        self.ensure_one()
        return Client(self.url+'?WSDL', transport=HttpsTransport())

    name = fields.Char('Name', size=64, select=1)
    code = fields.Char('Code', size=16, select=1)
    category = fields.Selection(selection=[('production', 'Production'),
                                           ('homologation', 'Homologation')],
                                string='Class')
    url = fields.Char('URL', size=512)
    auth_conn_ids = fields.One2many('wsafip.connection', 'logging_id',
                                    string='Authentication Connections')
    conn_ids = fields.One2many('wsafip.connection', 'server_id',
                               string='Service Connections')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
