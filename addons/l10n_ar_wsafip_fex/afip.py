# -*- coding: utf-8 -*-
from openerp import models, fields


class afip_product_unit(models.Model):
    _inherit = 'product.uom'

    afip_code = fields.Integer('AFIP Code')


class afip_language(models.Model):
    _inherit = 'res.lang'

    afip_code = fields.Integer('AFIP Code')


class afip_incoterms(models.Model):
    _inherit = 'stock.incoterms'

    afip_code = fields.Integer('AFIP Code')


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
