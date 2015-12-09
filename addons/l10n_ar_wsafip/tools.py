# -*- coding: utf-8 -*-
from openerp.exceptions import Warning
from suds import WebFault
from suds.transport import TransportError
from ssl import SSLError
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
            except TransportError as e:
                msg = 'Connection error!: %s' % (e[0])
                _logger.error(msg)
                raise Warning(msg)
            except WebFault as e:
                msg = 'AFIP Web service error!: %s' % (e[0])
                _logger.error(msg)
                raise Warning(msg)
            except SSLError as e:
                msg = 'Connection error!: %s' % (e[0])
                _logger.error(msg)
                raise Warning(msg)
            except Exception as e:
                msg = 'Unexpected error in WebService!: %s' % str(e)
                _logger.error(msg)
                raise Warning(msg)

            return False
        return _deco_client_
    return _deco_service_


def update_afip_code(pool, cr, uid, model_name, remote_list, can_create=True,
                     domain=[]):
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

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
