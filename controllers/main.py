from odoo import http
from odoo.http import request

class CollectionsApiController(http.Controller):

    @http.route('/api/collections_data', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_collections_json(self):
        """
        Retorna JSON mapeado por 'key' incluyendo referencia al padre.
        """
        # Buscar categorías marcadas como colección
        domain = [('is_collection', '=', True)]
        categories = request.env['product.category'].sudo().search(domain)
        
        # Obtenemos base url para imágenes
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        data = {}
        
        for cat in categories:
            # 1. Definir Key (Slug)
            key = cat.collection_key or cat.name.lower().replace(" ", "-")
            
            # 2. LÓGICA DE ANIDAMIENTO (PADRE / HIJO)
            parent_key = None
            if cat.parent_id and cat.parent_id.is_collection:
                parent_key = cat.parent_id.collection_key or cat.parent_id.name.lower().replace(" ", "-")

            # 3. Obtener productos
            # CORRECCIÓN AQUÍ: Eliminado 'is_published' porque requiere website_sale
            products = request.env['product.template'].sudo().search([
                ('categ_id', 'child_of', cat.id),
                ('sale_ok', '=', True), 
                # ('is_published', '=', True)  <-- ELIMINADO para evitar error
            ], limit=100)

            product_list = []
            for p in products:
                # URL de imagen del producto
                img_url = f"{base_url}/web/image/product.template/{p.id}/image_1920"
                
                product_list.append({
                    'id': p.id,
                    'name': p.name,
                    'price': p.list_price,
                    'image': img_url,
                    'currency': p.currency_id.symbol
                })

            # 4. Construir respuesta
            data[key] = {
                "title": cat.collection_title_display or cat.name,
                "description": cat.collection_description or "",
                "parent": parent_key,
                "products": product_list
            }
            
        return request.make_response(
            data=http.json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )