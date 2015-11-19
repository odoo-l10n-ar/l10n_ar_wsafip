# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging
import urllib2

_logger = logging.getLogger(__name__)

__URLError = {
    101: 'network_down',
    104: 'connection_rejected',
    -2: 'unknown_service'
}


class account_journal(osv.osv):
    def _get_afip_state(self, cr, uid, ids, fields_name, arg, context=None):
        if context is None:
            context = {}
        r = {}
        for journal in self.browse(cr, uid, ids):
            conn = journal.afip_connection_id
            if not conn:
                r[journal.id] = 'not_available'
                continue
            elif conn.server_id.code != 'wsfe':
                r[journal.id] = 'connection_service_error'
                continue

            # Try to login just one time.
            try:
                conn.login()
            except urllib2.URLError as e:
                r[journal.id] = __URLError.get(e[0][0], 'err:%i' % e[0][0])
                continue
            except Exception as e:
                r[journal.id] = 'something_wrong'
                continue

            if conn.state not in ['connected', 'clockshifted']:
                r[journal.id] = 'connection_error'
                continue

            authserver, appserver, dbserver \
                = \
                conn.server_id.wsfe_get_status(conn.id)[conn.server_id.id]

            r[journal.id] = (
                'connected' if authserver == 'OK' else
                'connected_but_appserver_error' if appserver != 'OK' else
                'connected_but_dbserver_error' if dbserver != 'OK' else
                'connected_but_servers_error')

            _logger.debug("Connection return: %s" % r[journal.id])
        return r

    def _get_afip_items_generated(self, cr, uid, ids, fields_name, arg,
                                  context=None):
        if context is None:
            context = {}

        def glin(conn, ps, jc):
            r = conn.server_id.wsfe_get_last_invoice_number(conn.id, ps, jc)
            return r[conn.server_id.id]

        r = {}
        for journal in self.browse(cr, uid, ids):
            r[journal.id] = False
            conn = journal.afip_connection_id
            if conn and conn.server_id.code == 'wsfe':
                try:
                    r[journal.id] = glin(conn,
                                         journal.point_of_sale,
                                         journal.journal_class_id.afip_code)
                except:
                    r[journal.id] = False
            _logger.debug("AFIP number of invoices in %s is %s" %
                          (journal.name, r[journal.id]))
        return r

    _inherit = "account.journal"
    _columns = {
        'afip_connection_id': fields.many2one(
            'wsafip.connection', 'Web Service connection',
            help="Which connection must be used to use AFIP services."),
        'afip_state': fields.function(
            _get_afip_state, type='selection', string='Connection state',
            method=True, readonly=True,
            selection=[
                ('not_available', 'Not available'),
                ('connected', 'Connected'),
                ('connection_error', 'Connection Error'),
                ('connected_but_appserver_error',
                 'Application service has troubles'),
                ('connected_but_dbserver_error', 'Database service is down'),
                ('connected_but_authserver_error',
                 'Authentication service is down'),
                ('connected_but_servers_error', 'Services are down'),
                ('network_down', 'Network is down'),
                ('unknown_service', 'Unknown service'),
                ('connection_rejection', 'Connection reseted by host'),
                ('something_wrong', 'Not identified error')
            ],
            help="Connect to the AFIP and check service status."),
        'afip_items_generated': fields.function(
            _get_afip_items_generated, type='integer',
            string='Number of Invoices Generated', method=True,
            help="Connect to the AFIP and check how many invoices"
            " was generated.",
            readonly=True),
    }
account_journal()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
