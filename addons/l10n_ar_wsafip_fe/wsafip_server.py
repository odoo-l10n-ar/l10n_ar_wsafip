# -*- coding: utf-8 -*-
from openerp import models, api
import logging
from openerp.addons.l10n_ar_wsafip.tools import service
from openerp.addons.l10n_ar_wsafip.tools import check_afip_errors
from openerp.addons.l10n_ar_wsafip.tools import update_afip_code

from openerp.osv import osv
from openerp.tools.translate import _
from datetime import date

_logger = logging.getLogger(__name__)

logging.getLogger('suds.transport').setLevel(logging.DEBUG)

fe_service = service('wsfe')
fe_service_without_auth = service('wsfe', without_auth=True)


class wsafip_server(models.Model):
    _inherit = "wsafip.server"

    """
    Implementación de la Factura Electrónica.

    Ref: https://www.afip.gob.ar/fe/documentos/manual_desarrollador_COMPG_v2.pdf
    TODO:
    Método de consulta de CAEA (FECAEAConsultar)
    Método para informar CAEA sin movimiento (FECAEASinMovimientoInformar)
    Método para informar comprobantes emitidos con CAEA (FECAEARegInformativo)
    Método para consultar CAEA sin movimiento (FECAEASinMovimientoConsultar)
    Recuperador de valores referenciales de códigos de Tipos de Alícuotas
    (FEParamGetTiposIva)
    Recuperador de los puntos de venta asignados a
    Facturación Electrónica que soporten CAE y CAEA vía Web Services
    (FEParamGetPtosVenta)
    Recuperador de cotización de moneda (FEParamGetCotizacion)
    Recuperador de cantidad máxima de registros FECAESolicitar /
    FECAEARegInformativo (FECompTotXRequest)
    """

    @api.multi
    @fe_service_without_auth
    def wsfe_get_status(self, service):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento
        de infraestructura (FEDummy)
        """
        _logger.info('Get status from AFIP Web service')

        response = service.FEDummy()

        return (response.AuthServer,
                response.AppServer,
                response.DbServer)

    @api.multi
    @fe_service
    def wsfe_update_afip_concept_type(self, service, auth):
        """
        Update concepts class.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Conceptos (FEParamGetTiposConcepto)
        """
        _logger.info('Updating concepts class from AFIP Web service')

        response = service.FEParamGetTiposConcepto(Auth=auth)

        concepttype_list = [
            {'afip_code': ct.Id,
             'name': ct.Desc,
             'active': ct.FchHasta in [None, 'NULL']}
            for ct in response.ResultGet.ConceptoTipo]

        # self.env['afip.concept_type'].import()

        update_afip_code(
            self.env['afip.concept_type'],
            concepttype_list,
            can_create=True,
            domain=[('afip_code', '!=', 0)])

        return True

    @api.multi
    @fe_service
    def wsfe_update_journal_class(self, service, auth):
        """
        Update journal class.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de comprobante (FEParamGetTiposCbte)
        """
        _logger.info('Updating journal class from AFIP Web service')

        response = service.FEParamGetTiposCbte(Auth=auth)

        # Take list of journal class
        journalclass_list = [
            {'afip_code': c.Id,
                'name': c.Desc,
                'active': c.FchHasta in [None, 'NULL']}
            for c in response.ResultGet.CbteTipo
        ]

        update_afip_code(
            self.env['afip.journal_class'],
            journalclass_list,
            can_create=False,
            can_deactivate=False,
            domain=[('afip_code', '!=', 0)])

        return True

    @api.multi
    @fe_service
    def wsfe_update_document_type(self, service, auth):
        """
        Update document type.
        This function must be called from connection model.

        Recuperador de valores referenciales de códigos de Tipos de Documentos
        (FEParamGetTiposDoc)
        """
        _logger.info('Updating document types from AFIP Web service')

        response = service.FEParamGetTiposDoc(Auth=auth)

        # Take list of document types
        doctype_list = [
            {'afip_code': c.Id,
                'name': c.Desc,
                'code': c.Desc,
                'active': c.FchHasta in [None, 'NULL']}
            for c in response.ResultGet.DocTipo
        ]

        update_afip_code(
            self.env['afip.document_type'],
            doctype_list,
            can_create=True,
            can_deactivate=False,
            domain=[])

        return True

    @api.multi
    @fe_service
    def wsfe_update_optional_types(self, service, auth):
        """
        Update optional types. This function must be called from
        connection model.

        Recuperador de valores referenciales de códigos de Tipos de datos
        Opcionales (FEParamGetTiposOpcional)
        """
        _logger.info('Updating optional types from AFIP Web service')

        response = service.FEParamGetTiposOpcional(Auth=auth)

        # Take list of currency
        currency_list = [
            {'afip_code': c.Id,
                'name': c.Desc,
                'active': c.FchHasta in [None, 'NULL']}
            for c in response.ResultGet.OpcionalTipo
        ]

        update_afip_code(
            self.env['afip.optional_type'],
            currency_list,
            can_create=True,
            can_deactivate=False,
            domain=[])

        return True

    @api.multi
    @fe_service
    def wsfe_update_currency(self, service, auth):
        """
        Update currency. This function must be called from connection model.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Monedas (FEParamGetTiposMonedas)
        """
        response = service.FEParamGetTiposMonedas(Auth=auth)
        check_afip_errors(response)

        # Take list of currency
        currency_list = [
            {'afip_code': c.Id,
             'name': c.Desc,
             'active': c.FchHasta in [None, 'NULL']}
            for c in response.ResultGet.Moneda
        ]

        update_afip_code(
            self.env['res.currency'],
            currency_list,
            can_create=False,
            domain=[])

        return True

    @api.multi
    @fe_service
    def wsfe_update_tax(self, service, auth):
        """
        Update taxes. This function must be called from connection model.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Tributos (FEParamGetTiposTributos)
        """
        response = service.FEParamGetTiposTributos(Auth=auth)
        check_afip_errors(response)

        tax_list = [
            {'afip_code': c.Id,
             'name': c.Desc}
            for c in response.ResultGet.TributoTipo
        ]

        response = service.FEParamGetTiposIva(Auth=auth)
        check_afip_errors(response)

        def _escape_(s):
            return s.replace('%', '\%')

        tax_list.extend([
            {'afip_code': c.Id,
             'name': "IVA Ventas %s" % _escape_(c.Desc)}
            for c in response.ResultGet.IvaTipo
        ])

        tax_list.extend([
            {'afip_code': c.Id,
             'name': "IVA Compras %s" % _escape_(c.Desc)}
            for c in response.ResultGet.IvaTipo
        ])

        tax_code_pool = self.env['account.tax.code']

        for tc in tax_list:
            tax_codes = tax_code_pool.search([('name', 'ilike', tc['name'])])
            if len(tax_codes) > 0:
                _logger.debug("Tax '%s' match with %s" %
                              (tc['name'], ','.join(tax_codes.mapped('name'))))
                tax_codes.write({'afip_code': tc['afip_code']})
            else:
                _logger.debug("Tax '%s' match with nobody." % tc['name'])

        return True

    @api.multi
    @fe_service
    def wsfe_get_last_invoice_number(self, service, auth, ptoVta, cbteTipo):
        """
        Get last ID number from AFIP

        AFIP Description: Recuperador de ultimo valor de comprobante registrado
        (FECompUltimoAutorizado)
        """
        response = service.FECompUltimoAutorizado(Auth=auth,
                                                  PtoVta=ptoVta,
                                                  CbteTipo=cbteTipo)
        check_afip_errors(response)

        return int(response.CbteNro)

    @api.multi
    @fe_service
    def wsfe_get_cae(self, service, auth, invoice_request):
        """
        Get CAE.

        AFIP Description: Método de autorización de comprobantes electrónicos
        por CAE (FECAESolicitar)
        """
        r = {}
        first = 0

        response = service.FECAESolicitar(
            Auth=auth,
            FeCAEReq=[{
                'FeCabReq': {
                    'CantReg': len(invoice_request),
                    'PtoVta': invoice_request[first]['PtoVta'],
                    'CbteTipo': invoice_request[first]['CbteTipo'],
                },
                'FeDetReq': [
                    {'FECAEDetRequest': dict(
                        [(k, v) for k, v in req.iteritems()
                         if k not in ['CantReg', 'PtoVta', 'CbteTipo']
                         ])}
                    for req in invoice_request
                ],
            }]
        )
        errors = check_afip_errors(response, True)

        soapRequest = [{'FeCabReq': {
            'CantReg': len(invoice_request),
            'PtoVta': invoice_request[first]['PtoVta'],
            'CbteTipo': invoice_request[first]['CbteTipo'], },
            'FeDetReq': [
                {'FECAEDetRequest': dict(
                    [(k, v) for k, v in req.iteritems()
                     if k not in ['CantReg', 'PtoVta', 'CbteTipo']])}
                for req in invoice_request], }]

        if not hasattr(response, 'FeDetResp'):
            raise osv.except_osv(_(u'AFIP error'),
                                 _(u'Stupid error:\n%s') % errors)

        for resp in response.FeDetResp.FECAEDetResponse:
            if resp.Resultado == 'R':
                # Existe Error!
                _logger.error('Invoice error: %s' % (resp,))
                r[int(resp.CbteDesde)] = {
                    'CbteDesde': resp.CbteDesde,
                    'CbteHasta': resp.CbteHasta,
                    'Observaciones':
                    [(o.Code, unicode(o.Msg))
                     for o in resp.Observaciones.Obs]
                    if hasattr(resp, 'Observaciones') else [],
                    'Errores': [(err.Code, unicode(err.Msg))
                                for err in response.Errors.Err]
                    if hasattr(response, 'Errors') else [],
                }
            else:
                # Todo bien!
                r[int(resp.CbteDesde)] = {
                    'CbteDesde': resp.CbteDesde,
                    'CbteHasta': resp.CbteHasta,
                    'CAE': resp.CAE,
                    'CAEFchVto': resp.CAEFchVto,
                    'Request': soapRequest,
                    'Response': response,
                }
        return r

    @api.multi
    @fe_service
    def wsfe_query_invoice(self, service, auth, cbteTipo, cbteNro, ptoVta):
        """
        Query for invoice stored by AFIP Web service.

        AFIP Description: Método para consultar Comprobantes Emitidos
        y su código (FECompConsultar)
        """
        response = service.FECompConsultar(
            Auth=auth,
            FeCompConsReq={
                'CbteTipo': cbteTipo,
                'CbteNro': cbteNro,
                'PtoVta': ptoVta,
            })
        if check_afip_errors(response, no_raise=[602]):
            return {}

        return {
            'Concepto': response.ResultGet.Concepto,
            'DocTipo': response.ResultGet.DocTipo,
            'DocNro': response.ResultGet.DocNro,
            'CbteDesde': response.ResultGet.CbteDesde,
            'CbteHasta': response.ResultGet.CbteHasta,
            'CbteFch': response.ResultGet.CbteFch,
            'ImpTotal': response.ResultGet.ImpTotal,
            'ImpTotConc': response.ResultGet.ImpTotConc,
            'ImpNeto': response.ResultGet.ImpNeto,
            'ImpOpEx': response.ResultGet.ImpOpEx,
            'ImpTrib': response.ResultGet.ImpTrib,
            'ImpIVA': response.ResultGet.ImpIVA,
            'FchServDesde': response.ResultGet.FchServDesde,
            'FchServHasta': response.ResultGet.FchServHasta,
            'FchVtoPago': response.ResultGet.FchVtoPago,
            'MonId': response.ResultGet.MonId,
            'MonCotiz': response.ResultGet.MonCotiz,
            'Resultado': response.ResultGet.Resultado,
            'CodAutorizacion': response.ResultGet.CodAutorizacion,
            'EmisionTipo': response.ResultGet.EmisionTipo,
            'FchVto': response.ResultGet.FchVto,
            'FchProceso': response.ResultGet.FchProceso,
            'PtoVta': response.ResultGet.PtoVta,
            'CbteTipo': response.ResultGet.CbteTipo,
            'Iva': [
                {'Id': item.Id,
                 'BaseImp': item.BaseImp,
                 'Importe': item.Importe}
                for tag, iva in response.ResultGet.Iva
                for item in iva
            ]
        }

    @api.multi
    @fe_service
    def wsfe_get_caea(self, service, auth, date=date.today()):
        """
        Get CAEA.

        AFIP Description: Método de obtención de CAEA (FECAEASolicitar)
        """
        raise NotImplemented

    @api.multi
    @fe_service
    def wsfe_get_caea_declaration(self, service, auth, invoicese):
        """
        Get CAEA.

        AFIP Description: método para informar comprobantes emitidos con CAEA
        (FECAEARegInformativo)
        """
        raise NotImplemented

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
