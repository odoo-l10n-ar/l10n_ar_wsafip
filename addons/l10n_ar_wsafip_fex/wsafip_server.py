# -*- coding: utf-8 -*-
from openerp import models
from openerp.tools.translate import _
from suds.client import Client
from suds import WebFault
import logging
from openerp.addons.l10n_ar_wsafip.sslhttps import HttpsTransport
from datetime import date

_logger = logging.getLogger(__name__)

logging.getLogger('suds.transport').setLevel(logging.DEBUG)


def _update(pool, cr, uid, model_name, remote_list, can_create=True, domain=[]):
    model_obj = pool.get(model_name)

    # Build set of AFIP codes
    rem_afip_code_set = set([i['afip_code'] for i in remote_list])

    # Take exists instances
    sto_ids = model_obj.search(cr, uid, [('active', 'in', ['f', 't'])] + domain)
    sto_list = model_obj.read(cr, uid, sto_ids, ['afip_code'])
    sto_afip_code_set = set([i['afip_code'] for i in sto_list])

    # Append new afip_code
    to_append = rem_afip_code_set - sto_afip_code_set
    if to_append and can_create:
        for item in [i for i in remote_list if i['afip_code'] in to_append]:
            model_obj.create(cr, uid, item)
    elif to_append and not can_create:
        _logger.warning('New items of type %s in WS. I will not create them.'
                        % model_name)

    # Update active document types
    to_update = rem_afip_code_set & sto_afip_code_set
    update_dict = dict([(i['afip_code'], i['active']) for i in remote_list
                        if i['afip_code'] in to_update])
    to_active = [k for k, v in update_dict.items() if v]
    if to_active:
        model_ids = model_obj.search(cr, uid, [
            ('afip_code', 'in', to_active), ('active', 'in', ['f', False])])
        model_obj.write(cr, uid, model_ids, {'active': True})

    to_deactive = [k for k, v in update_dict.items() if not v]
    if to_deactive:
        model_ids = model_obj.search(cr, uid,
                                     [('afip_code', 'in', to_deactive),
                                      ('active', 'in', ['t', True])])
        model_obj.write(cr, uid, model_ids, {'active': False})

    # To disable exists local afip_code but not in remote
    to_inactive = sto_afip_code_set - rem_afip_code_set
    if to_inactive:
        model_ids = model_obj.search(cr, uid,
                                     [('afip_code', 'in', list(to_inactive))])
        model_obj.write(cr, uid, model_ids, {'active': False})

    _logger.info('Updated %s items' % model_name)

    return True


class wsafip_server(osv.osv):
    _inherit = "wsafip.server"
    """
    Imprementación de Factura electrónica de exportación.

    Ref: https://www.afip.gob.ar/fe/documentos/WSFEX-Manualparaeldesarrollador_V1_1.pdf
    """

    def wsfex_autorize(self, cr, uid, ids, conn_id,
                       invoicese, context=None):
        """
        2.1 Autorizador (FEXAuthorize)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_query_invoice(self, cr, uid, ids, conn_id,
                            invoicese, context=None):
        """
        2.2 Recuperador de Comprobante (FEXGetCMP)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_last_request_id(self, cr, uid, ids, conn_id, context=None):
        """
        2.3 Recuperador de último valor de Id de requerimiento (FEXGetLast_ID)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_last_invoice_number(self, cr, uid, ids, conn_id, context=None):
        """
        2.4 Recuperador delúltimo Cbte_nroautorizado(FEXGetLast_CMP)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_currency_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.5 Recuperador de valores referenciales de códigosde Moneda
        (FEXGetPARAM_MON)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_invoice_type_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.6 Recuperador de valores referenciales de códigos de
        Tipos de comprobante (FEXGetPARAM_Cbte_Tipo)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_export_type_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.7 Recuperador de valores referenciales de códigos de
        Tipo de exportación (FEXGetPARAM_Tipo_Expo)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_unity_type_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.8 Recuperador de valores referenciales de códigos de
        Unidades de Medida (FEXGetPARAM_Umed)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_lang_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.9 Recuperador de valores referenciales de códigos de
        Idiomas (FEXGetPARAM_Idiomas)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_country_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.10 Recuperador de valores referenciales de códigos de
        Países (FEXGetPARAM_DST_pais)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_incoterms_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.11 Recuperador de valores referenciales de
        Incoterms (FEXGetPARAM_Incoterms)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_country_cuit_codes(self, cr, uid, ids, conn_id, context=None):
        """
        2.12 Recuperador de valores referenciales de CUITs de
        Países (FEXGetPARAM_DST_CUIT)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_currency_value(self, cr, uid, ids, conn_id, context=None):
        """
        2.13 Recuperador de cotizaciónde moneda (FEXGetPARAM_Ctz)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_get_web_points_of_sale(self, cr, uid, ids, conn_id, context=None):
        """
        2.14 Recuperador de los puntos de venta asignados a
        Facturación Electrónica de comprobantes de Exportación vía
        Web Services (FEXGetPARAM_PtoVenta)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_check_permissions(self, cr, uid, ids, conn_id, context=None):
        """
        2.15 Verificador  de existencia de Permiso/Paísde destinación en
        bases de datos aduaneras (FEXCheck_Permiso)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

    def wsfex_dummy(self, cr, uid, ids, conn_id, context=None):
        """
        2.16 MétodoDummy para verificación de funcionamiento de
        infraestructura (FEXDummy)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFEX.
            if srv.code != 'wsfex':
                continue

        return r

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
