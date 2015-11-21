# -*- coding: utf-8 -*-
from openerp import models, fields
import logging


_logger = logging.getLogger(__name__)


class account_invoice(models.Model):
    _inherit = "account.invoice"

    afip_batch_number = fields.Integer('AFIP Batch number', readonly=True)
    afip_error_id = fields.Many2one('wsafip.error', 'AFIP Status',
                                    readonly=True)
    state = fields.Selection(selection_add=[('batch_validation',
                                             'Batch Validation')])

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
