# -*- coding: utf-8 -*-
from openerp import models, api
from openerp.exceptions import Warning
import logging
from openerp.addons.l10n_ar_wsafip.tools import service

from openerp.osv import osv
from openerp.tools.translate import _
from openerp.addons.l10n_ar_wsafip.sslhttps import HttpsTransport
from datetime import date

_logger = logging.getLogger(__name__)

logging.getLogger('suds.transport').setLevel(logging.DEBUG)

fe_service = service('wsfe')


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
    @fe_service
    def wsfe_get_status(self, service, auth):
        """
        AFIP Description: Método Dummy para verificación de funcionamiento
        de infraestructura (FEDummy)
        """
        response = service.FEDummy()
        return (response.AuthServer,
                response.AppServer,
                response.DbServer)

    @api.multi
    @fe_service
    def wsfe_update_afip_concept_type(self, service, auth,
                                      context=None):
        """
        Update concepts class.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Conceptos (FEParamGetTiposConcepto)
        """
        response = service.FEParamGetTiposConcepto(Auth=auth)

        concepttype_list = [
            {'afip_code': ct.Id,
             'name': ct.Desc,
             'active': ct.FchHasta in [None, 'NULL']}
            for ct in response.ResultGet.ConceptoTipo]

        import pdb; pdb.set_trace()
        #self.env['afip.concept_type'].import()

        _update(self.pool, cr, uid,
                'afip.concept_type',
                concepttype_list,
                can_create=True,
                domain=[('afip_code', '!=', 0)])
        return

    def wsfe_update_journal_class(self, cr, uid, ids, conn_id, context=None):
        """
        Update journal class.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de comprobante (FEParamGetTiposCbte)
        """
        conn_obj = self.pool.get('wsafip.connection')

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection, continue if connected or clockshifted
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                continue

            try:
                _logger.info('Updating journal class from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEParamGetTiposCbte(
                    Auth=conn.get_auth())

                # Take list of journal class
                journalclass_list = [
                    {'afip_code': c.Id,
                     'name': c.Desc,
                     'active': c.FchHasta in [None, 'NULL']}
                    for c in response.ResultGet.CbteTipo
                ]
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' %
                              (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') %
                                     (e[0], e[1]))

            _update(self.pool, cr, uid,
                    'afip.journal_class',
                    journalclass_list,
                    can_create=False,
                    domain=[('afip_code', '!=', 0)])

        return

    def wsfe_update_document_type(self, cr, uid, ids, conn_id, context=None):
        """
        Update document type.
        This function must be called from connection model.

        Recuperador de valores referenciales de códigos de Tipos de Documentos
        (FEParamGetTiposDoc)
        """
        conn_obj = self.pool.get('wsafip.connection')

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection, continue if connected or clockshifted
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                continue

            try:
                _logger.info('Updating document types from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEParamGetTiposDoc(
                    Auth=conn.get_auth())

                # Take list of document types
                doctype_list = [
                    {'afip_code': c.Id,
                     'name': c.Desc,
                     'code': c.Desc,
                     'active': c.FchHasta in [None, 'NULL']}
                    for c in response.ResultGet.DocTipo
                ]
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' %
                              (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') %
                                     (e[0], e[1]))

            _update(self.pool, cr, uid,
                    'afip.document_type',
                    doctype_list,
                    can_create=True,
                    domain=[])

        return True

    def wsfe_update_optional_types(self, cr, uid, ids, conn_id, context=None):
        """
        Update optional types. This function must be called from
        connection model.

        Recuperador de valores referenciales de códigos de Tipos de datos
        Opcionales (FEParamGetTiposOpcional)
        """
        conn_obj = self.pool.get('wsafip.connection')

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection, continue if connected or clockshifted
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                continue

            try:
                _logger.info('Updating currency from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEParamGetTiposOpcional(
                    Auth=conn.get_auth())

                # Take list of currency
                currency_list = [
                    {'afip_code': c.Id,
                     'name': c.Desc,
                     'active': c.FchHasta in [None, 'NULL']}
                    for c in response.ResultGet.OpcionalTipo
                ]
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' %
                              (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') %
                                     (e[0], e[1]))

            _update(self.pool, cr, uid,
                    'afip.optional_type',
                    currency_list,
                    can_create=True,
                    domain=[])
        return True

    def wsfe_update_currency(self, cr, uid, ids, conn_id, context=None):
        """
        Update currency. This function must be called from connection model.

        AFIP Description: Recuperador de valores referenciales de códigos de
        Tipos de Monedas (FEParamGetTiposMonedas)
        """
        conn_obj = self.pool.get('wsafip.connection')

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection, continue if connected or clockshifted
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                continue

            try:
                _logger.info('Updating currency from AFIP Web service')
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FEParamGetTiposMonedas(
                    Auth=conn.get_auth())

                # Take list of currency
                currency_list = [
                    {'afip_code': c.Id,
                     'name': c.Desc,
                     'active': c.FchHasta in [None, 'NULL']}
                    for c in response.ResultGet.Moneda
                ]
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' %
                              (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') %
                                     (e[0], e[1]))

            _update(self.pool, cr, uid,
                    'res.currency',
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

        tax_list = [
            {'afip_code': c.Id,
             'name': c.Desc}
            for c in response.ResultGet.TributoTipo
        ]

        response = service.FEParamGetTiposIva(Auth=auth)

        def _escape_(s):
            return s.replace('%', '%%')

        tax_list.extend([
            {'afip_code': c.Id,
             'name': "%s" % _escape_(c.Desc)}
            for c in response.ResultGet.IvaTipo
        ])

        tax_code_pool = self.env['account.tax.code']

        for tc in tax_list:
            tax_codes = tax_code_pool.search([('name', 'ilike', tc['name'])])
            if len(tax_codes) == 1:
                _logger.debug("Tax '%s' match with %s" %
                              (tc['name'], tax_codes.name))
                tax_codes.afip_code = tc['afip_code']
            elif len(tax_codes) > 1:
                _logger.debug("Tax '%s' match with some %s" %
                              (tc['name'], ','.join(tax_codes.mapped("name"))))
            else:
                _logger.debug("Tax '%s' match with nobody." % tc['name'])
        return True

    def wsfe_get_last_invoice_number(self, cr, uid, ids, conn_id, ptoVta,
                                     cbteTipo, context=None):
        """
        Get last ID number from AFIP

        AFIP Description: Recuperador de ultimo valor de comprobante registrado
        (FECompUltimoAutorizado)
        """
        conn_obj = self.pool.get('wsafip.connection')

        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                r[srv.id] = False
                continue

            try:
                _logger.info('Take last invoice number from AFIP Web service '
                             '(pto vta: %s, cbte tipo: %s)' %
                             (ptoVta, cbteTipo))
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                response = srvclient.service.FECompUltimoAutorizado(
                    Auth=conn.get_auth(), PtoVta=ptoVta, CbteTipo=cbteTipo)

            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s\n'
                                       u'Pueda que esté intente realizar esta '
                                       u'operación desde el servidor de '
                                       u'homologación. Intente desde el '
                                       u'servidor de producción.') %
                                     (e[0], e[1]))

            if hasattr(response, 'Errors'):
                for e in response.Errors.Err:
                    _logger.error('AFIP Web service error!: (%i) %s' %
                                  (e.Code, e.Msg))
                r[srv.id] = False
            else:
                r[srv.id] = int(response.CbteNro)
        return r

    def wsfe_get_cae(self, cr, uid, ids, conn_id, invoice_request,
                     context=None):
        """
        Get CAE.

        AFIP Description: Método de autorización de comprobantes electrónicos
        por CAE (FECAESolicitar)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                continue

            _logger.info('Get CAE from AFIP Web service')
            _logger.debug('Request: %s' % invoice_request)

            auth = conn.get_auth()
            try:
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                first = 0
                response = srvclient.service.FECAESolicitar(
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
            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise Warning(_(u'AFIP Web service error\n'
                                u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise Warning(_(u'AFIP Web service error\n'
                                u'System return error %i: %s') % (e[0], e[1]))

            soapRequest = [{'FeCabReq': {
                'CantReg': len(invoice_request),
                'PtoVta': invoice_request[first]['PtoVta'],
                'CbteTipo': invoice_request[first]['CbteTipo'], },
                'FeDetReq': [
                    {'FECAEDetRequest': dict(
                        [(k, v) for k, v in req.iteritems()
                         if k not in ['CantReg', 'PtoVta', 'CbteTipo']])}
                    for req in invoice_request], }]

            common_error = [
                (err.Code, unicode(err.Msg)) for err in response.Errors[0]
            ] if hasattr(response, 'Errors') else []
            if (common_error):
                _logger.error('Request error: %s' % (common_error,))

            if not hasattr(response, 'FeDetResp'):
                raise osv.except_osv(_(u'AFIP error'),
                                     _(u'Stupid error:\n%s') %
                                     ('\n'.join(
                                         ["%i:%s" % err for err in common_error]
                                     )))

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
                        'Errores': common_error +
                        [(err.Code, unicode(err.Msg))
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

    def wsfe_get_caea(self, cr, uid, ids, conn_id, date=date.today(),
                      context=None):
        """
        Get CAEA.

        AFIP Description: Método de obtención de CAEA (FECAEASolicitar)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        raise NotImplemented

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                continue

            _logger.info('Get CAEA from AFIP Web service')

            auth = conn.get_auth()
            try:
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                first = 0
                response = srvclient.service.FECAESolicitar(
                    Auth=auth,
                    FeCAEAReq=[{
                        'Periodo': date,
                        'Orden': "",
                    }]
                )
            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') %
                                     (e[0], e[1]))

            soapRequest = [{'FeCabReq': {
                'CantReg': len(invoice_request),
                'PtoVta': invoice_request[first]['PtoVta'],
                'CbteTipo': invoice_request[first]['CbteTipo'], },
                'FeDetReq': [
                    {'FECAEDetRequest': dict(
                        [(k, v) for k, v in req.iteritems()
                         if k not in ['CantReg', 'PtoVta', 'CbteTipo']])}
                    for req in invoice_request], }]

            common_error = [
                (err.Code, unicode(err.Msg)) for err in response.Errors[0]
            ] if hasattr(response, 'Errors') else []
            if (common_error):
                _logger.error('Request error: %s' % (common_error,))

            if not hasattr(response, 'FeDetResp'):
                raise osv.except_osv(_(u'AFIP error'),
                                     _(u'Stupid error:\n%s') %
                                     ('\n'.join(
                                         ["%i:%s" % err for err in common_error]
                                     )))

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
                        'Errores': common_error +
                        [(err.Code, unicode(err.Msg))
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

    def wsfe_get_caea_declaration(self, cr, uid, ids, conn_id,
                                  invoicese, context=None):
        """
        Get CAEA.

        AFIP Description: método para informar comprobantes emitidos con CAEA
        (FECAEARegInformativo)
        """
        conn_obj = self.pool.get('wsafip.connection')
        r = {}

        raise NotImplemented

        for srv in self.browse(cr, uid, ids, context=context):
            # Ignore servers without code WSFE.
            if srv.code != 'wsfe':
                continue

            # Take the connection
            conn = conn_obj.browse(cr, uid, conn_id, context=context)
            conn.login()
            if conn.state not in ['connected', 'clockshifted']:
                continue

            _logger.info('Get CAE from AFIP Web service')
            _logger.debug('Request: %s' % invoice_request)

            auth = conn.get_auth()
            try:
                srvclient = Client(srv.url+'?WSDL', transport=HttpsTransport())
                first = 0
                response = srvclient.service.FECAESolicitar(
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
            except WebFault as e:
                _logger.error('AFIP Web service error!: %s' % (e[0]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error: %s') % e[0])
            except Exception as e:
                _logger.error('AFIP Web service error!: (%i) %s' % (e[0], e[1]))
                raise osv.except_osv(_(u'AFIP Web service error'),
                                     _(u'System return error %i: %s') %
                                     (e[0], e[1]))

            soapRequest = [{'FeCabReq': {
                'CantReg': len(invoice_request),
                'PtoVta': invoice_request[first]['PtoVta'],
                'CbteTipo': invoice_request[first]['CbteTipo'], },
                'FeDetReq': [
                    {'FECAEDetRequest': dict(
                        [(k, v) for k, v in req.iteritems()
                         if k not in ['CantReg', 'PtoVta', 'CbteTipo']])}
                    for req in invoice_request], }]

            common_error = [
                (err.Code, unicode(err.Msg)) for err in response.Errors[0]
            ] if hasattr(response, 'Errors') else []
            if (common_error):
                _logger.error('Request error: %s' % (common_error,))

            if not hasattr(response, 'FeDetResp'):
                raise osv.except_osv(_(u'AFIP error'),
                                     _(u'Stupid error:\n%s') %
                                     ('\n'.join(
                                         ["%i:%s" % err for err in common_error]
                                     )))

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
                        'Errores': common_error +
                        [(err.Code, unicode(err.Msg))
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
