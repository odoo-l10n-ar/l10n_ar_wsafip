# -*- coding: utf-8 -*-
from openerp import models, api
import logging
import urllib2

_logger = logging.getLogger(__name__)

__URLError = {
    101: 'network_down',
    104: 'connection_rejected',
    -2: 'unknown_service'
}


class account_journal(models.Model):
    _inherit = "account.journal"

    @api.depends('wsafip_items_generated', 'journal.sequence_id.number_next')
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
        elif conn.server_id.code != 'wsfex':
            return super(account_journal, self).get_wsafip_state()

        # Try to login just one time.
        try:
            conn.login()
        except urllib2.URLError as e:
            wsafip_state = __URLError.get(e[0][0], 'err:%i' % e[0][0])
        except Exception as e:
            wsafip_state = 'something_wrong'

        if conn.state not in ['connected', 'clockshifted']:
            wsafip_state = 'connection_error'

        authserver, appserver, dbserver \
            = \
            conn.server_id.wsfex_get_status(conn.id)

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

    @api.multi
    def get_wsafip_items_generated(self):
        """
        Compute invoice numbers stored in afip.
        """
        self.ensure_one()
        journal = self

        conn = journal.wsafip_connection_id
        if conn and conn.server_id.code == 'wsfex':
            r = conn.server_id.wsfex_get_last_invoice_number(
                conn,
                journal.point_of_sale,
                journal.journal_class_id.afip_code)
            _logger.debug("AFIP number of invoices in %s is %s" %
                            (journal.name, r))
            return r
        else:
            return super(account_journal, self).get_wsafip_items_generated()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
