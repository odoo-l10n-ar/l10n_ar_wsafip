# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import logging

_logger = logging.getLogger(__name__)


class l10n_ar_wsafip_fex_config(models.TransientModel):
    @api.multi
    def _default_company(self):
        import pdb; pdb.set_trace()
        users_obj = self.env['res.users']
        return users_obj.browse(cr, uid, uid, context).company_id.id

    def execute(self, cr, uid, ids, context=None):
        """
        """
        conn_obj = self.pool.get('wsafip.connection')
        journal_obj = self.pool.get('account.journal')
        afipserver_obj = self.pool.get('wsafip.server')
        sequence_obj = self.pool.get('ir.sequence')

        import pdb; pdb.set_trace()

        for ws in self.browse(cr, uid, ids):
            # Tomamos la compania
            company = ws.company_id
            conn_category = 'homologation' \
                if ws.wsfex_for_homologation else 'production'

            # Hay que crear la autorizacion para el servicio si no existe.
            conn_ids = conn_obj.search(
                cr, uid, [('partner_id', '=', company.partner_id.id)])

            if len(conn_ids) == 0:
                # Hay que crear la secuencia de proceso en batch si no existe.
                seq_ids = sequence_obj.search(
                    cr, uid, [('code', '=', 'ws_afip_sequence')])
                if seq_ids:
                    seq_id = seq_ids[0]
                else:
                    seq_id = sequence_obj.create(
                        cr, uid, {
                            'name': 'Web Service AFIP Sequence',
                            'code': 'ws_afip_sequence'})

                # Crear el conector al AFIP
                conn_id = conn_obj.create(cr, uid, {
                    'name':
                    'AFIP Sequence Authorization Invoice: %s' % company.name,
                    'partner_id': company.partner_id.id,
                    'logging_id':
                    afipserver_obj.search(
                        cr, uid,
                        [('code', '=', 'wsaa'),
                         ('category', '=', conn_category)])[0],
                    'server_id':
                    afipserver_obj.search(
                        cr, uid,
                        [('code', '=', 'wsfex'),
                         ('category', '=', conn_category)])[0],
                    'certificate': ws.wsfex_certificate_id.id,
                    'batch_sequence_id': seq_id,
                })
            else:
                conn_id = conn_ids[0]

            # Asigno el conector al AFIP
            jou_ids = journal_obj.search(cr, uid,
                                         [('company_id', '=', company.id),
                                          ('point_of_sale', '=',
                                           ws.wsfex_point_of_sale),
                                          ('type', '=', 'sale')])

            journal_obj.write(cr, uid, jou_ids, {'afip_connection_id': conn_id})

            # Actualizo el código de impuestos de la AFIP
            # en los impuestos locales
            conn = conn_obj.browse(cr, uid, conn_id)
            conn.server_id.wsfex_update(conn_id)

        return True

    _name = 'l10n_ar_wsafip_fex.config'
    _inherit = 'res.config'

    company_id = fields.Many2one('res.company',
                                 string='Company',
                                 required=True,
                                 default=_default_company)
    wsfex_certificate_id = fields.Many2one('crypto.certificate',
                                           string='Certificate',
                                           required=True)
    wsfex_for_homologation = fields.Boolean('Is for homologation',
                                            default=False)

l10n_ar_wsafip_fex_config()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
