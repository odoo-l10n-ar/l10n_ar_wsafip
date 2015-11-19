# -*- coding: utf-8 -*-
from openerp import models, fields


class wsafip_error(models.Model):
    _name = 'afip.wsafip_error'

    name = fields.Char('Name', size=64),
    service = fields.Char('Service', size=6),
    code = fields.Char('Code', size=4),
    description = fields.Text('Description'),

wsafip_error()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
