# -*- coding: utf-8 -*-
from openerp import models
from openerp.exceptions import Warning
from suds import WebFault
from suds.transport import TransportError
from ssl import SSLError
import logging

_logger = logging.getLogger(__name__)

def service(code, without_auth=False):
    def _deco_service_(func):
        def _deco_client_(self, conn, *args, **kargs):
            self.ensure_one()
            if self.code != code:
                return False

            if not isinstance(conn, models.Model):
                conn = self.env['wsafip.connection'].browse(conn)
            conn.login()

            try:
                if (without_auth):
                    return func(self,
                                self.client().service,
                                *args,
                                **kargs)
                else:
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
                _logger.error(msg, exc_info=1)
                raise Warning(msg)

            return False
        return _deco_client_
    return _deco_service_


def check_afip_errors(response, no_raise=[]):
    if hasattr(response, 'Errors'):
        no_raise = all(e.Code in no_raise for e in response.Errors[0])
        errors = '\n'.join(u"%s (%s)" % (e.Msg, unicode(e.Code))
                           for e in response.Errors[0])
        if not no_raise:
            raise Warning("Errors:\n%s", errors)
        else:
            return errors
    return False


def update_afip_code(model_obj, remote_list, can_create=True, domain=[]):
    # Build set of AFIP codes
    rem_afip_code_set = set([i['afip_code'] for i in remote_list])

    # Take exists instances
    sto_afip_code_set = set(model_obj.search(
        [('active', 'in', ['f', 't'])] + domain
    ).mapped('afip_code'))

    # Append new afip_code
    to_append = rem_afip_code_set - sto_afip_code_set
    if to_append and can_create:
        for item in [i for i in remote_list if i['afip_code'] in to_append]:
            model_obj.create(item)
    elif to_append and not can_create:
        _logger.warning('New items of type %s in WS. I will not create them.'
                        % model_obj._name)

    # Update active document types
    to_update = rem_afip_code_set & sto_afip_code_set
    update_dict = dict([(i['afip_code'], i['active']) for i in remote_list
                        if i['afip_code'] in to_update])
    to_active = [k for k, v in update_dict.items() if v]
    if to_active:
        model_obj.search([
            ('afip_code', 'in', to_active), ('active', 'in', ['f', False])]
        ).write({'active': True})

    to_deactive = [k for k, v in update_dict.items() if not v]
    if to_deactive:
        model_obj.search([
            ('afip_code', 'in', to_deactive),
            ('active', 'in', ['t', True])]).write({'active': False})

    # To disable exists local afip_code but not in remote
    to_inactive = sto_afip_code_set - rem_afip_code_set
    if to_inactive:
        model_obj.search(
            [('afip_code', 'in', list(to_inactive))]
        ).write({'active': False})

    _logger.info('Updated %s items' % model_obj._name)

    return True

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
