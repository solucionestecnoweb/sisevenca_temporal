# -*- coding: utf-8 -*-
{
        'name': ' Venezuela - IVA Retention',
        'version': '14.0.1.0',
        'author': 'INM & LDR Soluciones Tecnológicas y Empresariales C.A',
        'contribuitors': "Bryan Gómez <bryan.gomez1311@gmail.com>",
        'summary': '',
        'description': """""",
        'category': 'Accounting/Accounting',
        'website': 'http://soluciones-tecno.com/',
        'depends': [
                'account',
                'l10n_ve_account_sequence_number',
                'l10n_ve_res_config_settings_retentions',
                'l10n_ve_base',
                'l10n_ve_currency_rate',
        ],
        'data': [
                'security/ir.model.access.csv',
                'data/ir_sequence.xml',
                'data/account_journal.xml',
                'report/paperformat.xml',
                'report/ir_action_report.xml',
                'data/email_template.xml',
                'views/res_partner_views.xml',
                'views/iva_retention_views.xml',
                'views/account_move_views.xml',
                'views/res_config_settings_views.xml',
                'views/report_iva.xml',
                'views/report_iva_resume.xml',
                'wizard/retention_iva_txt_views.xml',
                'views/retention_txt_summary_views.xml',
                'wizard/retention_iva_resume_views.xml',
                'views/iva_menuitem.xml',
        ],
        'license': 'LGPL-3',
        'installable': True,
        'application': True,
        'auto_install': False,
                      
}
