{
    'name': 'Gestor Avanzado de Colecciones (Headless)',
    'version': '19.0.1.0.0',
    'category': 'Inventory/Creative',
    'summary': 'Gestión de Colecciones Artísticas sobre Categorías Internas',
    'description': """
        Módulo Backend para gestión de contenido Headless (Next.js).
        
        Características:
        - Extiende product.category (Categorías Internas).
        - Permite marcar categorías como 'Colecciones Públicas'.
        - Gestión de Descripción Larga y Slugs (Keys para JSON).
        - API Endpoint para sincronización con Frontend.
    """,
    'author': 'Tu Empresa',
    'website': 'https://tudominio.com',
    'depends': ['product', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/product_category_views.xml',
    ],
    'installable': True,
    'application': True,
    'license': 'OPL-1',
}
