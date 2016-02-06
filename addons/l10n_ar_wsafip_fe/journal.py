# -*- coding: utf-8 -*-
from openerp import models, fields, api
import logging
import urllib2

_logger = logging.getLogger(__name__)


class account_journal(models.Model):
    _inherit = "account.journal"

    wsafip_connection_id = fields.Many2one(
        'wsafip.connection', 'Web Service connection',
        help="Which connection must be used to use AFIP services.")
    wsafip_state = fields.Selection(
        compute='_get_wsafip_state', string='Connection state',
        readonly=True,
        selection=[
            ('not_implemented', 'Not implemented'),
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
    wsafip_items_generated = fields.Integer(
        compute='_get_wsafip_items_generated',
        string='Number of Invoices Generated',
        help="Connect to the AFIP and check how many invoices"
        " was generated.",
        readonly=True)

    @api.depends("wsafip_connection_id")
    @api.multi
    def _get_wsafip_state(self):
        for jou in self:
            jou.ensure_one()
            jou.wsafip_state = jou.get_wsafip_state()

    @api.multi
    def get_wsafip_state(self):
        """
        Compute connection and journal state with the afip.
        """
        self.ensure_one()
        journal = self

        conn = journal.wsafip_connection_id
        if not conn:
            wsafip_state = 'not_available'
        elif conn.server_id.code != 'wsfe':
            return 'not_implemented'

        # Try to login just one time.
        try:
            conn.login()
        except urllib2.URLError as e:
            wsafip_state = __URLError.get(e[0][0], 'err:%i' % e[0][0])
        except Exception as e:
            wsafip_state = 'something_wrong'

        if conn.state not in ['connected', 'clockshifted']:
            return 'connection_error'

        authserver, appserver, dbserver \
            = \
            conn.server_id.wsfe_get_status(conn.id)

        if authserver == 'OK':
            syncronized = (journal.wsafip_items_generated + 1 ==
                            journal.sequence_id.number_next)

        wsafip_state = (
            'connected' if authserver == 'OK' and syncronized else
            'unsync' if authserver == 'OK' and not syncronized else
            'connected_but_appserver_error' if appserver != 'OK' else
            'connected_but_dbserver_error' if dbserver != 'OK' else
            'connected_but_servers_error')

        return wsafip_state

    @api.depends("wsafip_connection_id")
    def _get_wsafip_items_generated(self):
        for jou in self:
            jou.wsafip_items_generated = jou.get_wsafip_items_generated()

    @api.multi
    def get_wsafip_items_generated(self):
        """
        Compute invoice numbers stored in afip.
        """
        self.ensure_one()
        journal = self

        conn = journal.wsafip_connection_id
        if conn and conn.server_id.code == 'wsfe':
            r = conn.server_id.wsfe_get_last_invoice_number(
                conn,
                journal.point_of_sale,
                journal.journal_class_id.afip_code)
            _logger.debug("AFIP number of invoices in %s is %s" %
                            (journal.name, r))
            return r
        else:
            return False


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
