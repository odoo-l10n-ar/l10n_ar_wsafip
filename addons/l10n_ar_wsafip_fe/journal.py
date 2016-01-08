# -*- coding: utf-8 -*-
from openerp import models, fields, api
import logging
import urllib2

_logger = logging.getLogger(__name__)

__URLError = {
    101: 'network_down',
    104: 'connection_rejected',
    -2: 'unknown_service'
}


class account_journal(models.Model):

    @api.depends("afip_connection_id")
    def _get_afip_state(self):
        for journal in self:
            conn = journal.afip_connection_id
            if not conn:
                journal.afip_state = 'not_available'
                continue
            elif conn.server_id.code != 'wsfe':
                journal.afip_state = 'connection_service_error'
                continue

            # Try to login just one time.
            try:
                conn.login()
            except urllib2.URLError as e:
                journal.afip_state = __URLError.get(e[0][0], 'err:%i' % e[0][0])
                continue
            except Exception as e:
                journal.afip_state = 'something_wrong'
                continue

            if conn.state not in ['connected', 'clockshifted']:
                journal.afip_state = 'connection_error'
                continue

            authserver, appserver, dbserver \
                = \
                conn.server_id.wsfe_get_status(conn.id)

            if authserver == 'OK':
                syncronized = (journal.afip_items_generated + 1 ==
                               journal.sequence_id.number_next)

            journal.afip_state = (
                'connected' if authserver == 'OK' and syncronized else
                'unsync' if authserver == 'OK' and not syncronized else
                'connected_but_appserver_error' if appserver != 'OK' else
                'connected_but_dbserver_error' if dbserver != 'OK' else
                'connected_but_servers_error')

    @api.depends("afip_connection_id")
    def _get_afip_items_generated(self):
        for journal in self:
            conn = journal.afip_connection_id
            if conn and conn.server_id.code == 'wsfe':
                r = conn.server_id.wsfe_get_last_invoice_number(
                    conn,
                    journal.point_of_sale,
                    journal.journal_class_id.afip_code)
                _logger.debug("AFIP number of invoices in %s is %s" %
                              (journal.name, r))
                journal.afip_items_generated = r
            else:
                journal.afip_items_generated = False

    _inherit = "account.journal"

    afip_connection_id = fields.Many2one(
        'wsafip.connection', 'Web Service connection',
        help="Which connection must be used to use AFIP services.")
    afip_state = fields.Selection(
        compute=_get_afip_state, string='Connection state',
        readonly=True,
        selection=[
            ('not_available', 'Not available'),
            ('connected', 'Connected'),
            ('unsync', 'Unsyncronized'),
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
        help="Connect to the AFIP and check service status.")
    afip_items_generated = fields.Integer(
        compute=_get_afip_items_generated,
        string='Number of Invoices Generated',
        help="Connect to the AFIP and check how many invoices"
        " was generated.",
        readonly=True)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
