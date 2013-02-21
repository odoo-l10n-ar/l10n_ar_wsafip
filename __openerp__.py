# -*- coding: utf-8 -*-
##############################################################################
#
# Copyright (C) 2012 OpenERP - Team de Localización Argentina.
# https://launchpad.net/~openerp-l10n-ar-localization
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
{
    'name':     'Argentina - Base para los Web Services del AFIP',
    'version':  '2.7.155',
    'author':   'OpenERP - Team de Localización Argentina',
    'category': 'Localization/Argentina',
    'website':  'https://launchpad.net/~openerp-l10n-ar-localization',
    'license':  'AGPL-3',
    'description': """
Configuración y API para acceder a las Web Services de la AFIP

Incluye:
 - Wizard para instalar los claves para acceder a las Web Services.
 - API para realizar consultas en la Web Services desde OpenERP.

El módulo l10n_ar_wsafip permite a OpenERP acceder a los servicios del AFIP a través de Web Services. Este módulo es un servicio para administradores y programadores, donde podrán configurar el servidor, la autentificación y además tendrán acceso a una API genérica en Python para utilizar los servicios AFIP.

Para poder ejecutar los tests es necesario cargar la clave privada y el certificado al archivo test_key.yml. Tenga en cuenta que estas claves son personales y pueden traer conflicto publicarlas en los repositorios públicos.
""",
    'depends': [
        'crypto',
    ],
    'init_xml': [],
    'demo_xml': [],
    'test': [
        'test/test_key.yml',
        'test/test_mime_signer.yml',
        'test/test_wsafip_service.yml',
    ],
    'update_xml': [
        'data/wsafip_sequence.xml',
        'data/wsafip_server.xml',
        'data/wsafip_menuitem.xml',
        'data/wsafip_authorization_view.xml',
        'data/wsafip_server_view.xml',
        'data/wsafip_config.xml',
        'security/wsafip_security.xml',
        'security/ir.model.access.csv',
    ],
    'external_dependencies': {
        'python': [ 'ZSI' ],
    },
    'active': False,
    'installable': True,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
