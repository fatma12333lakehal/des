{
    'name': 'Safety Culture ERP TOP',
    'version': '1.0',
    'category': 'Project/Engineering',
    'summary': 'Dynamic Inspection Report for Sales Engineers',
    'description': """
        Full dynamic report module for sales engineers.
        Supports Kitchen, Bathroom, Wardrobes, Doors, Flooring, Furniture.
        Includes BOQ integration and dynamic scope selection.
    """,
    'author': 'Lakehal Fatma Zahra',
    'images': ['static/description/icon.png'],
    'depends': ['base', 'project', 'sale','hr','crm'],
    'data': [
        'security/yallawrap_security.xml',  # security access rules
        'security/ir.model.access.csv',               # model access CSV

        'views/crm_lead.xml',
        'views/floor_view.xml',
        'views/yallawrap_tile_code.xml',
        'views/yallawrap_sale_order_views.xml',
        'reports/report_yallawrap_inspection.xml',






    ],
    "price": 1200.00,
    "currency": "EUR",
    'installable': True,
    'application': True,
}
