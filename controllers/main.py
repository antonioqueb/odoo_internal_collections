from odoo import http
from odoo.http import request

class CollectionsApiController(http.Controller):

    # --- Endpoint 1: Listado General de Colecciones (Estructura de Árbol) ---
    @http.route('/api/collections_data', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_collections_json(self):
        domain = [('is_collection', '=', True)]
        categories = request.env['product.category'].sudo().search(domain)
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        data = {}
        for cat in categories:
            key = cat.collection_key or cat.name.lower().replace(" ", "-")
            parent_key = None
            if cat.parent_id and cat.parent_id.is_collection:
                parent_key = cat.parent_id.collection_key or cat.parent_id.name.lower().replace(" ", "-")

            # Lista simple para vista rápida
            products = request.env['product.template'].sudo().search([
                ('categ_id', 'child_of', cat.id),
                ('sale_ok', '=', True), 
            ], limit=10) # Limitamos vista previa

            product_preview = []
            for p in products:
                slug = p.headless_slug or str(p.id)
                img_url = f"{base_url}/web/image/product.template/{p.id}/image_1920"
                product_preview.append({
                    'id': p.id,
                    'name': p.name,
                    'slug': slug,
                    'image': img_url,
                })

            data[key] = {
                "id": cat.id,
                "title": cat.collection_title_display or cat.name,
                "description": cat.collection_description or "",
                "parent": parent_key,
                "products_preview": product_preview
            }
            
        return request.make_response(
            data=http.json.dumps(data),
            headers=[('Content-Type', 'application/json')]
        )

    # --- Endpoint 2: Detalle de Productos por Colección (FULL DATA) ---
    @http.route('/api/collection/<string:collection_key>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_collection_details(self, collection_key):
        """
        Retorna todos los productos de una colección específica con:
        - Descripción corta/larga
        - SEO, Slug
        - 5 Imágenes (Principal + 4 extras)
        - Dimensiones, Peso, Material
        """
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
        # 1. Buscar la categoría por el key
        category = request.env['product.category'].sudo().search([
            ('collection_key', '=', collection_key),
            ('is_collection', '=', True)
        ], limit=1)

        if not category:
            return request.make_response(
                data=http.json.dumps({'error': 'Collection not found'}),
                headers=[('Content-Type', 'application/json')],
                status=404
            )

        # 2. Buscar productos
        products = request.env['product.template'].sudo().search([
            ('categ_id', 'child_of', category.id),
            ('sale_ok', '=', True)
        ])

        products_data = []

        for p in products:
            # --- Gestión de Imágenes ---
            # Imagen Principal
            main_image = f"{base_url}/web/image/product.template/{p.id}/image_1920"
            
            # Imágenes Extra (Galería estándar de Odoo)
            # Tomamos las primeras 4 imágenes extra
            extra_images = p.product_template_image_ids[:4]
            gallery_urls = {}
            
            # Rellenar slots image_1 a image_4
            for i in range(4):
                key_name = f"image_{i+1}"
                if i < len(extra_images):
                    img_obj = extra_images[i]
                    gallery_urls[key_name] = f"{base_url}/web/image/product.image/{img_obj.id}/image_1920"
                else:
                    gallery_urls[key_name] = None # O null si prefieres

            # --- Construcción del Objeto Producto ---
            product_obj = {
                'id': p.id,
                'name': p.name,
                'slug': p.headless_slug or str(p.id),
                'price': p.list_price,
                'currency': p.currency_id.symbol,
                
                # Contenido
                'short_description': p.headless_short_description or "",
                'long_description': p.headless_long_description or "", # Ojo: esto retorna HTML
                
                # Especificaciones
                'material': p.headless_material or "",
                'specs': {
                    'weight_kg': p.weight,
                    'dimensions': {
                        'length': p.dim_length,
                        'width': p.dim_width,
                        'height': p.dim_height,
                        'display': f"{p.dim_length}x{p.dim_width}x{p.dim_height} cm"
                    }
                },

                # Imágenes (Total 5)
                'images': {
                    'main': main_image,
                    **gallery_urls # Expande image_1, image_2, etc.
                },

                # SEO & Meta
                'seo': {
                    'keyword': p.headless_seo_keyword or "",
                    'meta_title': p.headless_meta_title or p.name,
                    'meta_description': p.headless_meta_description or p.headless_short_description or ""
                }
            }
            products_data.append(product_obj)

        # Respuesta final
        response_data = {
            "collection_info": {
                "title": category.collection_title_display or category.name,
                "description": category.collection_description,
                "key": category.collection_key
            },
            "products": products_data
        }

        return request.make_response(
            data=http.json.dumps(response_data),
            headers=[('Content-Type', 'application/json')]
        )