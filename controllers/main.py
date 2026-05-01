from odoo import http
from odoo.http import request


class CollectionsApiController(http.Controller):

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _json_response(self, data, status=200):
        return request.make_response(
            data=http.json.dumps(data),
            headers=[
                ('Content-Type', 'application/json'),
                ('Access-Control-Allow-Origin', '*'),
                ('Access-Control-Allow-Methods', 'GET, OPTIONS'),
                ('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept'),
            ],
            status=status
        )

    def _get_product_image_url(self, base_url, product_template, field_name):
        if getattr(product_template, field_name):
            return f"{base_url}/web/image/product.template/{product_template.id}/{field_name}"
        return None

    def _get_sold_map_by_template(self, product_templates):
        """
        Devuelve un diccionario:
            {
                product_template_id: True / False
            }

        Un producto se considera vendido únicamente si alguna de sus variantes
        aparece en una línea de venta cuya orden esté confirmada o cerrada.

        Estados considerados:
            - sale: pedido confirmado
            - done: pedido bloqueado/cerrado

        Estados ignorados:
            - draft: cotización
            - sent: cotización enviada
            - cancel: cancelado
        """
        sold_map = {product.id: False for product in product_templates}

        if not product_templates:
            return sold_map

        variants = product_templates.mapped('product_variant_ids')
        if not variants:
            return sold_map

        variant_to_template = {
            variant.id: variant.product_tmpl_id.id
            for variant in variants
        }

        SaleOrderLine = request.env['sale.order.line'].sudo()

        grouped_lines = SaleOrderLine.read_group(
            domain=[
                ('product_id', 'in', variants.ids),
                ('order_id.state', 'in', ['sale', 'done']),
            ],
            fields=['product_id'],
            groupby=['product_id'],
        )

        for group in grouped_lines:
            product_data = group.get('product_id')
            if not product_data:
                continue

            variant_id = product_data[0]
            template_id = variant_to_template.get(variant_id)

            if template_id:
                sold_map[template_id] = True

        return sold_map

    def _get_availability_payload(self, is_sold):
        return {
            'is_sold': bool(is_sold),
            'availability_status': 'sold' if is_sold else 'available',
            'sold_source': 'confirmed_sale_order' if is_sold else None,
        }

    # -------------------------------------------------------------------------
    # ENDPOINT 1: LISTADO GENERAL DE COLECCIONES
    # -------------------------------------------------------------------------

    @http.route(
        '/api/collections_data',
        type='http',
        auth='public',
        methods=['GET', 'OPTIONS'],
        csrf=False,
        cors='*'
    )
    def get_collections_json(self):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({}, status=200)

        Category = request.env['product.category'].sudo()
        ProductTemplate = request.env['product.template'].sudo()

        categories = Category.search([
            ('is_collection', '=', True)
        ])

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

        data = {}

        for cat in categories:
            key = cat.collection_key or cat.name.lower().replace(" ", "-")

            parent_key = None
            if cat.parent_id and cat.parent_id.is_collection:
                parent_key = cat.parent_id.collection_key or cat.parent_id.name.lower().replace(" ", "-")

            products = ProductTemplate.search([
                ('categ_id', 'child_of', cat.id),
                ('sale_ok', '=', True),
            ], limit=10)

            sold_map = self._get_sold_map_by_template(products)

            product_preview = []

            for product in products:
                slug = product.headless_slug or str(product.id)
                img_url = f"{base_url}/web/image/product.template/{product.id}/image_1920"
                is_sold = sold_map.get(product.id, False)

                product_preview.append({
                    'id': product.id,
                    'name': product.name,
                    'slug': slug,
                    'image': img_url,
                    **self._get_availability_payload(is_sold),
                })

            data[key] = {
                "id": cat.id,
                "title": cat.collection_title_display or cat.name,
                "description": cat.collection_description or "",
                "parent": parent_key,
                "products_preview": product_preview,
            }

        return self._json_response(data)

    # -------------------------------------------------------------------------
    # ENDPOINT 2: DETALLE COMPLETO DE COLECCIÓN
    # -------------------------------------------------------------------------

    @http.route(
        '/api/collection/<string:collection_key>',
        type='http',
        auth='public',
        methods=['GET', 'OPTIONS'],
        csrf=False,
        cors='*'
    )
    def get_collection_details(self, collection_key):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({}, status=200)

        Category = request.env['product.category'].sudo()
        ProductTemplate = request.env['product.template'].sudo()

        base_url = request.env['ir.config_parameter'].sudo().get_param('web.base.url')

        category = Category.search([
            ('collection_key', '=', collection_key),
            ('is_collection', '=', True),
        ], limit=1)

        if not category:
            return self._json_response(
                {'error': 'Collection not found'},
                status=404
            )

        products = ProductTemplate.search([
            ('categ_id', 'child_of', category.id),
            ('sale_ok', '=', True),
        ])

        sold_map = self._get_sold_map_by_template(products)

        products_data = []

        for product in products:
            main_image = f"{base_url}/web/image/product.template/{product.id}/image_1920"

            gallery_urls = {
                'image_1': self._get_product_image_url(base_url, product, 'headless_image_1'),
                'image_2': self._get_product_image_url(base_url, product, 'headless_image_2'),
                'image_3': self._get_product_image_url(base_url, product, 'headless_image_3'),
                'image_4': self._get_product_image_url(base_url, product, 'headless_image_4'),
            }

            is_sold = sold_map.get(product.id, False)

            product_obj = {
                'id': product.id,
                'name': product.name,
                'slug': product.headless_slug or str(product.id),
                'price': product.list_price,
                'currency': product.currency_id.symbol,

                **self._get_availability_payload(is_sold),

                'short_description': product.headless_short_description or "",
                'long_description': product.headless_long_description or "",

                'material': product.headless_material or "",
                'specs': {
                    'weight_kg': product.weight,
                    'volume_m3': product.volume,
                    'dimensions': {
                        'length': product.dim_length,
                        'width': product.dim_width,
                        'height': product.dim_height,
                        'display': f"{product.dim_length}x{product.dim_width}x{product.dim_height} cm",
                    },
                },

                'images': {
                    'main': main_image,
                    **gallery_urls,
                },

                'seo': {
                    'keyword': product.headless_seo_keyword or "",
                    'meta_title': product.headless_meta_title or product.name,
                    'meta_description': product.headless_meta_description or product.headless_short_description or "",
                },
            }

            products_data.append(product_obj)

        response_data = {
            "collection_info": {
                "title": category.collection_title_display or category.name,
                "description": category.collection_description,
                "subtitle": category.collection_subtitle or "",
                "key": category.collection_key,
            },
            "products": products_data,
        }

        return self._json_response(response_data)