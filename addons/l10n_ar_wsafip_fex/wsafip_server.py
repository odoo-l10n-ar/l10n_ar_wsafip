# -*- coding: utf-8 -*-
from openerp import models, api
from openerp.exceptions import Warning
import logging
from openerp.addons.l10n_ar_wsafip.tools import service
# from suds.client import Client
# from suds import WebFault
# from datetime import date

_logger = logging.getLogger(__name__)

logging.getLogger('suds.transport').setLevel(logging.DEBUG)

fex_service = service('wsfex')


def _update(pool, cr, uid, model_name, remote_list, can_create=True, domain=[]):
    model_pool = pool.get(model_name)

    # Build set of AFIP codes
    rem_afip_code_set = set([i['afip_code'] for i in remote_list])

    # Take exists instances
    sto_ids = model_pool.search(cr, uid, [('active', 'in', ['f', 't'])] +
                                domain)
    sto_list = model_pool.read(cr, uid, sto_ids, ['afip_code'])
    sto_afip_code_set = set([i['afip_code'] for i in sto_list])

    # Append new afip_code
    to_append = rem_afip_code_set - sto_afip_code_set
    if to_append and can_create:
        for item in [i for i in remote_list if i['afip_code'] in to_append]:
            model_pool.create(cr, uid, item)
    elif to_append and not can_create:
        _logger.warning('New items of type %s in WS. I will not create them.'
                        % model_name)

    # Update active document types
    to_update = rem_afip_code_set & sto_afip_code_set
    update_dict = dict([(i['afip_code'], i['active']) for i in remote_list
                        if i['afip_code'] in to_update])
    to_active = [k for k, v in update_dict.items() if v]
    if to_active:
        model_ids = model_pool.search(cr, uid, [
            ('afip_code', 'in', to_active), ('active', 'in', ['f', False])])
        model_pool.write(cr, uid, model_ids, {'active': True})

    to_deactive = [k for k, v in update_dict.items() if not v]
    if to_deactive:
        model_ids = model_pool.search(cr, uid,
                                      [('afip_code', 'in', to_deactive),
                                       ('active', 'in', ['t', True])])
        model_pool.write(cr, uid, model_ids, {'active': False})

    # To disable exists local afip_code but not in remote
    to_inactive = sto_afip_code_set - rem_afip_code_set
    if to_inactive:
        model_ids = model_pool.search(cr, uid,
                                      [('afip_code', 'in', list(to_inactive))])
        model_pool.write(cr, uid, model_ids, {'active': False})

    _logger.info('Updated %s items' % model_name)

    return True


class wsafip_server(models.Model):
    _inherit = "wsafip.server"
    """
    Imprementación de Factura electrónica de exportación.

    Ref:
  https://www.afip.gob.ar/fe/documentos/WSFEX-Manualparaeldesarrollador_V1_1.pdf
    """

    @api.multi
    @fex_service
    def wsfex_autorize(self, service, auth, invoice):
        """
        2.1 Autorizador (FEXAuthorize)
        """
        response = service.FEXAuthorize(Auth=auth,
                                        Cmp=invoice)
        return response

    @api.multi
    @fex_service
    def wsfex_query_invoice(self, service, auth,
                            cbte_tipo, punto_vta, cbte_nro):
        """
        2.2 Recuperador de Comprobante (FEXGetCMP)
        """
        response = service.FEXGetCMP(Auth=auth,
                                     Cmp={'Cbte_Tipo': cbte_tipo,
                                          'Punto_vta': punto_vta,
                                          'Cbte_nro': cbte_nro})
        return response

    @api.multi
    @fex_service
    def wsfex_get_last_request_id(self, service, auth):
        """
        2.3 Recuperador de último valor de Id de requerimiento (FEXGetLast_ID)
        """
        response = service.FEXGetLast_ID(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_last_invoice_number(self, service, auth):
        """
        2.4 Recuperador delúltimo Cbte_nroautorizado(FEXGetLast_CMP)
        """
        response = service.FEXGetLast_CMP(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_currency_codes(self, service, auth):
        """
        2.5 Recuperador de valores referenciales de códigosde Moneda
        (FEXGetPARAM_MON)
        """
        response = service.FEXGetPARAM_MON(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_invoice_type_codes(self, service, auth):
        """
        2.6 Recuperador de valores referenciales de códigos de
        Tipos de comprobante (FEXGetPARAM_Cbte_Tipo)
        """
        response = service.FEXGetPARAM_Cbte_Tipo(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_export_type_codes(self, service, auth):
        """
        2.7 Recuperador de valores referenciales de códigos de
        Tipo de exportación (FEXGetPARAM_Tipo_Expo)
        """
        response = service.FEXGetPARAM_Tipo_Expo(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_unity_type_codes(self, service, auth):
        """
        2.8 Recuperador de valores referenciales de códigos de
        Unidades de Medida (FEXGetPARAM_Umed)
        """
        response = service.FEXGetPARAM_Umed(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_lang_codes(self, service, auth):
        """
        2.9 Recuperador de valores referenciales de códigos de
        Idiomas (FEXGetPARAM_Idiomas)
        """
        response = service.FEXGetPARAM_Idiomas(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_country_codes(self, service, auth):
        """
        2.10 Recuperador de valores referenciales de códigos de
        Países (FEXGetPARAM_DST_pais)
        """
        response = service.FEXGetPARAM_DST_pais(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_incoterms_codes(self, service, auth):
        """
        2.11 Recuperador de valores referenciales de
        Incoterms (FEXGetPARAM_Incoterms)
        """
        response = service.FEXGetPARAM_Incoterms(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_get_country_cuit_codes(self, service, auth):
        """
        2.12 Recuperador de valores referenciales de CUITs de
        Países (FEXGetPARAM_DST_CUIT)
        """
        response = service.FEXGetPARAM_DST_CUIT(Auth=auth)
        if response.FEXErr.ErrCode != 0:
            raise Warning(response.FEXErr.ErrMsg)

        country = {}
        for result in response.FEXResultGet[0]:
            _c, _t = result.DST_Ds.split(' - ')
            if _c not in country:
                country[_c] = {}
            if _t not in country[_c]:
                country[_c][_t] = result.DST_CUIT
        return country

    @api.multi
    @fex_service
    def wsfex_get_currency_value(self, service, auth, mon_id):
        """
        2.13 Recuperador de cotizaciónde moneda (FEXGetPARAM_Ctz)
        """
        response = service.FEXGetPARAM_Ctz(Auth=auth, Mon_id=str(mon_id))
        return response

    @api.multi
    @fex_service
    def wsfex_get_web_points_of_sale(self, service, auth):
        """
        2.14 Recuperador de los puntos de venta asignados a
        Facturación Electrónica de comprobantes de Exportación vía
        Web Services (FEXGetPARAM_PtoVenta)
        """
        response = service.FEXGetPARAM_PtoVenta(Auth=auth)
        return response

    @api.multi
    @fex_service
    def wsfex_check_permissions(self, service, auth, id_permiso, dst_merc):
        """
        2.15 Verificador  de existencia de Permiso/País de destinación en
        bases de datos aduaneras (FEXCheck_Permiso)
        """
        response = service.FEXCheck_Permiso(Auth=auth,
                                            ID_Permiso=str(id_permiso),
                                            Dst_merc=int(dst_merc))
        return response

    @api.multi
    @fex_service
    def wsfex_dummy(self, service, auth):
        """
        2.16 MétodoDummy para verificación de funcionamiento de
        infraestructura (FEXDummy)
        """
        response = service.FEXDummy()

        if response.AuthServer != 'OK':
            raise Warning('Authentication is offline')
        if response.AppServer != 'OK':
            raise Warning('Webservice is offline')
        if response.DbServer != 'OK':
            raise Warning('Database is offline')

        return True

    @api.one
    def wsfex_update(self, conn_id):
        self.wsfex_dummy(conn_id)
        self.wsfex_get_web_points_of_sale(conn_id)
        country_cuit = self.wsfex_get_country_cuit_codes(conn_id)
        import pdb; pdb.set_trace()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
