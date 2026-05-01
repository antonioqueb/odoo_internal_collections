{
    'name': 'Gestor Avanzado de Colecciones (Headless)',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Creative',
    'summary': 'Gestión de Colecciones Artísticas sobre Categorías Internas',
    'description': """
        Módulo Backend para gestión de contenido Headless (Next.js).
        Sincroniza categorías y subcategorías como colecciones anidadas.
        Expone productos para catálogo web y calcula si un producto ya fue vendido
        con base en órdenes de venta confirmadas.
    """,
    'author': 'Alphaqueb Consulting S.A.S.',
    'website': 'https://www.alphaqueb.com',
    'depends': [
        'product',
        'stock',
        'sale_management',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/product_category_views.xml',
        'views/product_template_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}