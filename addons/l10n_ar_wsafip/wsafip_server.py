# -*- coding: utf-8 -*-
from openerp import fields, models, api
from suds.client import Client
from sslhttps import HttpsTransport


class wsafip_server(models.Model):
    _name = "wsafip.server"

    def name_get(self, cr, uid, ids, context=None):
        if isinstance(ids, (list, tuple)) and not len(ids):
            return []
        if isinstance(ids, (long, int)):
            ids = [ids]
        reads = self.read(cr, uid, ids, ['name', 'category'], context=context)
        res = []
        for record in reads:
            res.append((record['id'], u"{name} [{category}]".format(**record)))
        return res

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
    auth_conn_id = fields.One2many('wsafip.connection', 'logging_id',
                                   string='Authentication Connections')
    conn_id = fields.One2many('wsafip.connection', 'server_id',
                              string='Service Connections')

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
