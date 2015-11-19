# -*- coding: utf-8 -*-
from openerp.osv import fields, osv


class wsfe_error(osv.osv):
    _name = 'afip.wsfe_error'
    _columns = {
        'name': fields.char('Name', size=64),
        'code': fields.char('Code', size=2),
        'description': fields.text('Description'),
    }
wsfe_error()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
