from odoo import http
from odoo.http import request

class CollectionsApiController(http.Controller):

    # --- Endpoint 1: Listado General ---
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

            # Preview simple
            products = request.env['product.template'].sudo().search([
                ('categ_id', 'child_of', cat.id),
                ('sale_ok', '=', True), 
            ], limit=10)

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

    # --- Endpoint 2: Detalle Completo ---
    @http.route('/api/collection/<string:collection_key>', type='http', auth='public', methods=['GET'], csrf=False, cors='*')
    def get_collection_details(self, collection_key):
        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')
        
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

        products = request.env['product.template'].sudo().search([
            ('categ_id', 'child_of', category.id),
            ('sale_ok', '=', True)
        ])

        products_data = []

        for p in products:
            # 1. Imagen Principal (Standard Odoo)
            main_image = f"{base_url}/web/image/product.template/{p.id}/image_1920"
            
            # 2. Imágenes Extra (Nuestros campos personalizados)
            # Construimos la URL solo si el campo tiene contenido (técnicamente Odoo lo sirve igual, pero ahorramos peticiones vacías en el front si validamos aquí)
            
            def get_img_url(field_name):
                # Helper simple para generar la URL si existe data
                if getattr(p, field_name):
                    return f"{base_url}/web/image/product.template/{p.id}/{field_name}"
                return None

            gallery_urls = {
                'image_1': get_img_url('headless_image_1'),
                'image_2': get_img_url('headless_image_2'),
                'image_3': get_img_url('headless_image_3'),
                'image_4': get_img_url('headless_image_4'),
            }

            product_obj = {
                'id': p.id,
                'name': p.name,
                'slug': p.headless_slug or str(p.id),
                'price': p.list_price,
                'currency': p.currency_id.symbol,
                
                'short_description': p.headless_short_description or "",
                'long_description': p.headless_long_description or "",
                
                'material': p.headless_material or "",
                'specs': {
                    'weight_kg': p.weight,
                    'volume_m3': p.volume,
                    'dimensions': {
                        'length': p.dim_length,
                        'width': p.dim_width,
                        'height': p.dim_height,
                        'display': f"{p.dim_length}x{p.dim_width}x{p.dim_height} cm"
                    }
                },

                'images': {
                    'main': main_image,
                    **gallery_urls
                },

                'seo': {
                    'keyword': p.headless_seo_keyword or "",
                    'meta_title': p.headless_meta_title or p.name,
                    'meta_description': p.headless_meta_description or p.headless_short_description or ""
                }
            }
            products_data.append(product_obj)

        response_data = {
            "collection_info": {
                "title": category.collection_title_display or category.name,
                "description": category.collection_description,
                "subtitle": category.collection_subtitle or "",
                "key": category.collection_key
            },
            "products": products_data
        }

        return request.make_response(
            data=http.json.dumps(response_data),
            headers=[('Content-Type', 'application/json')]
        )