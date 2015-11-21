# -*- coding: utf-8 -*-
from openerp.exceptions import Warning
from suds import WebFault
import logging

_logger = logging.getLogger(__name__)


def service(code):
    def _deco_service_(func):
        def _deco_client_(self, conn_id, *args, **kargs):
            self.ensure_one()
            if self.code != code:
                return False

            conn = self.env['wsafip.connection'].browse(conn_id)
            conn.login()

            try:
                return func(self,
                            self.client().service,
                            conn.get_auth(),
                            *args,
                            **kargs)
            except WebFault as e:
                msg = 'AFIP Web service error!: %s' % (e[0])
                _logger.error(msg)
                raise Warning(msg)
            except Exception as e:
                msg = 'AFIP Web service error!: (%i) %s' % (e[0], e[1])
                _logger.error(msg)
                raise Warning(msg)

            return False
        return _deco_client_
    return _deco_service_

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
