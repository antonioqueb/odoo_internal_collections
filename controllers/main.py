from odoo import http
from odoo.http import request

class CollectionsApiController(http.Controller):

    @http.route('/api/collections_data', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_collections_json(self):
        """
        Retorna un JSON mapeado por 'key'.
        Formato:
        {
            "earth": {
                "description": "Texto...",
                "title": "Earth Collection",
                "products": [ ... array de productos simplificados ... ]
            },
            ...
        }
        """
        # Buscar todas las categorías marcadas como colección
        domain = [('is_collection', '=', True)]
        # sudo() es necesario para acceder si el usuario web no está logueado en Odoo
        categories = request.env['product.category'].sudo().search(domain)
        
        data = {}
        
        for cat in categories:
            # Usamos el campo collection_key si existe, si no, el nombre en minúsculas
            key = cat.collection_key or cat.name.lower()
            
            # Obtener productos de esta categoría (y subcategorías si Odoo está config así)
            # Buscamos product.template o product.product según tu necesidad.
            # Aquí busco product.template publicados (sale_ok=True)
            products = request.env['product.template'].sudo().search([
                ('categ_id', 'child_of', cat.id),
                ('sale_ok', '=', True)
            ], limit=50) # Limitamos a 50 por seguridad inicial

            product_list = []
            for p in products:
                # Mapeo simple para tu ProductGrid
                product_list.append({
                    'id': p.id,
                    'name': p.name,
                    'price': p.list_price,
                    # Añadir campos de imagen URL si es necesario
                })

            # Construimos el objeto
            # NOTA: Tu JSON original era string plano, pero tu TSX hace 'data.products'.
            # Por eso devolvemos un OBJETO con propiedad description.
            data[key] = {
                "title": cat.collection_title_display or cat.name,
                "description": cat.collection_description or "",
                "products": product_list
            }
            
        return request.make_response(
            data=http.json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )
