# -*- coding: utf-8 -*-
from openerp import fields, models, api
from random import randint
import xml.etree.ElementTree as ET
from dateutil.parser import parse as dateparse
from dateutil.tz import tzlocal
from datetime import datetime, timedelta
from openerp.tools.translate import _
from suds.client import Client
import logging
from M2Crypto.X509 import X509Error

_logger = logging.getLogger(__name__)
_schema = logging.getLogger(__name__ + '.schema')

_login_message = """\
<?xml version="1.0" encoding="UTF-8"?>
<loginTicketRequest version="1.0">
<header>
    <uniqueId>{uniqueid}</uniqueId>
    <generationTime>{generationtime}</generationTime>
    <expirationTime>{expirationtime}</expirationTime>
</header>
<service>{service}</service>
</loginTicketRequest>"""

_intmin = -2147483648
_intmax = 2147483647


class wsafip_connection(models.Model):
    _name = "wsafip.connection"

    name = fields.Char('Name', size=64)
    partner_id = fields.Many2one(
        'res.partner',
        'Partner',
        default='_get_default_partner')
    server_id = fields.Many2one('wsafip.server', 'Service Server')
    logging_id = fields.Many2one('wsafip.server', 'Authorization Server')
    certificate = fields.Many2one('crypto.certificate', 'Certificate Signer')
    uniqueid = fields.Integer('Unique ID', readonly=True)
    token = fields.Text('Token', readonly=True)
    sign = fields.Text('Sign', readonly=True)
    generationtime = fields.Datetime('Generation Time', readonly=True)
    expirationtime = fields.Datetime('Expiration Time', readonly=True)
    state = fields.Selection(
        compute='_get_state',
        string='Status',
        selection=[
            ('clockshifted', 'Clock shifted'),
            ('connected', 'Connected'),
            ('disconnected', 'Disconnected'),
            ('invalid', 'Invalid'),
        ], readonly=True)
    batch_sequence_id = fields.Many2one(
        'ir.sequence',
        'Batch Sequence', readonly=False)

    @api.multi
    def _get_state(self):
        for conn in self:
            conn.state = self.get_state()

    @api.multi
    @api.model
    def get_state(self):
        self.ensure_one()

        conn = self
        if False in (conn.uniqueid, conn.generationtime,
                     conn.expirationtime, conn.token, conn.sign):
            _logger.info("Disconnected from AFIP.")
            return 'disconnected'
        elif not (dateparse(conn.generationtime) - timedelta(0, 5)
                  < datetime.now()):
            _logger.warning("clockshifted. Server: %s, Now: %s" % (
                str(dateparse(conn.generationtime)), str(datetime.now())))
            _logger.warning("clockshifted."
                            " Please syncronize your host to a NTP server.")
            return 'clockshifted'
        elif datetime.now() < dateparse(conn.expirationtime):
            return 'connected'
        else:
            _logger.info("Invalid Connection from AFIP.")
            return 'invalid'

    @api.model
    def _get_default_partner(self):
        user_mod = self.env['res.users']
        return user_mod.browse(self.env.uid).company_id.partner_id.id

    @api.multi
    def login(self):

        for conn in self:
            if conn.get_state() in ('connected', 'clockshifted'):
                continue

            aaclient = Client(conn.logging_id.url+'?WSDL')

            uniqueid = randint(_intmin, _intmax)
            msg = _login_message.format(
                uniqueid=uniqueid - _intmin,
                generationtime=(
                    datetime.now(tzlocal()) - timedelta(0, 60)).isoformat(),
                expirationtime=(
                    datetime.now(tzlocal()) + timedelta(0, 60)).isoformat(),
                service=conn.server_id.code
            )
            msg = conn.certificate.smime(msg)[conn.certificate.id]
            head, body, end = msg.split('\n\n')

            response = aaclient.service.loginCms(in0=body)

            T = ET.fromstring(response)

            auth_data = {
                'source': T.find('header/source').text,
                'destination': T.find('header/destination').text,
                'uniqueid': int(T.find('header/uniqueId').text)+_intmin,
                'generationtime': dateparse(
                    T.find('header/generationTime').text),
                'expirationtime': dateparse(
                    T.find('header/expirationTime').text),
                'token': T.find('credentials/token').text,
                'sign': T.find('credentials/sign').text,
            }

            del auth_data['source']
            del auth_data['destination']

            _logger.info("Successful Connection to AFIP.")
            conn.write(auth_data)

    @api.multi
    def get_auth(self):
        self.ensure_one()
        conn = self

        if conn.partner_id.document_type_id.name != 'CUIT':
            raise Warning(
                _('Selected partner has not CUIT. Need one to connect.'))
        return {
            'Token': conn.token.encode('ascii'),
            'Sign': conn.sign.encode('ascii'),
            'Cuit': conn.partner_id.document_number,
        }

    @api.multi
    def do_login(self):
        self.ensure_one()

        try:
            self.login()
        except X509Error, m:
            raise Warning(_('Certificate Error: %s') % m)
        except Exception, e:
            raise Warning(_('Unknown Error: %s') % e)

        return {}

wsafip_connection()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
