# -*- coding: utf-8 -*-
{'active': False,
 'author': 'OpenERP - Team de Localizaci\xc3\xb3n Argentina',
 'category': 'Localization/Argentina',
 'demo_xml': [],
 'depends': ['crypto'],
 'description': '''
 Configuración y API para acceder a las Web Services de la AFIP

 Incluye:
 - Wizard para instalar los claves para acceder a las Web Services.
 - API para realizar consultas en la Web Services desde OpenERP.

 El módulo l10n_ar_wsafip permite a OpenERP acceder a los servicios del AFIP a
 través de Web Services. Este módulo es un servicio para administradores y
 programadores, donde podrán configurar el servidor, la autentificación y además
 tendrán acceso a una API genérica en Python para utilizar los servicios AFIP.

 Para poder ejecutar los tests es necesario cargar la clave privada y el
 certificado al archivo test_key.yml.

 Tenga en cuenta que estas claves son personales y pueden traer conflicto
 publicarlas en los repositorios públicos.''',
 'external_dependencies': {
     'python': ['suds']
 },
 'installable': True,
 'license': 'AGPL-3',
 'name': 'Argentina - Base para los Web Services del AFIP',
 'test': ['test/test_key.yml',
          'test/test_mime_signer.yml',
          'test/test_wsafip_service.yml'],
 'data': ['data/wsafip_sequence.xml',
          'data/wsafip_server.xml',
          'data/wsafip_menuitem.xml',
          'data/wsafip_connection_view.xml',
          'data/wsafip_server_view.xml',
          'data/wsafip_config.xml',
          'security/wsafip_security.xml',
          'security/ir.model.access.csv'],
 'version': '8.0.1.1',
 'website': 'https://launchpad.net/~openerp-l10n-ar-localization'}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
