# -*- coding: utf-8 -*-

import base64
import json
import mimetypes
import re

from odoo import http
from odoo.http import request


class CollectionsApiController(http.Controller):

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    def _json_response(self, data, status=200):
        """
        Respuesta JSON estándar.

        IMPORTANTE:
        No agregamos manualmente Access-Control-Allow-Origin porque las rutas
        ya usan cors='*'. Si se agrega también aquí, Odoo/proxy/Nginx puede
        terminar enviando Access-Control-Allow-Origin duplicado y el navegador
        bloqueará la respuesta.
        """
        return request.make_response(
            data=json.dumps(data, default=str, ensure_ascii=False),
            headers=[
                ('Content-Type', 'application/json; charset=utf-8'),
            ],
            status=status,
        )

    def _get_product_image_url(self, base_url, product_template, field_name):
        if getattr(product_template, field_name):
            return f"{base_url}/web/image/product.template/{product_template.id}/{field_name}"
        return None

    def _get_product_video_payload(self, base_url, product_template, fallback_poster=None):
        """
        Devuelve un payload estable para el frontend.

        Mantiene compatibilidad:
        - Si no hay video, devuelve has_video=False.
        - Si hay archivo subido, devuelve URL interna de streaming.
        - Si no hay archivo, pero hay URL manual, devuelve esa URL.
        """
        if hasattr(product_template, 'get_headless_video_payload'):
            return product_template.get_headless_video_payload(
                base_url=base_url,
                fallback_poster=fallback_poster,
            )

        return {
            'has_video': False,
            'url': '',
            'poster': fallback_poster or '',
            'source': None,
            'filename': '',
            'mimetype': '',
        }

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

    def _safe_header_filename(self, filename):
        filename = (filename or 'product-video.mp4').strip()
        filename = filename.replace('"', '').replace("'", '')
        filename = filename.replace('\n', '').replace('\r', '')
        return filename or 'product-video.mp4'

    def _get_video_mimetype(self, filename):
        mimetype, _encoding = mimetypes.guess_type(filename or 'product-video.mp4')
        return mimetype or 'video/mp4'

    def _build_video_response(self, file_content, filename):
        """
        Respuesta de video con soporte básico para Range requests.

        Esto ayuda especialmente a navegadores como Safari y a reproductores HTML5
        que piden fragmentos del video en vez de descargarlo completo.
        """
        total_size = len(file_content)
        filename = self._safe_header_filename(filename)
        mimetype = self._get_video_mimetype(filename)

        request_method = request.httprequest.method
        range_header = request.httprequest.headers.get('Range')

        common_headers = [
            ('Content-Type', mimetype),
            ('Content-Disposition', f'inline; filename="{filename}"'),
            ('Accept-Ranges', 'bytes'),
            ('Cache-Control', 'public, max-age=86400'),
            ('Access-Control-Expose-Headers', 'Content-Length, Content-Range, Accept-Ranges'),
        ]

        if range_header:
            match = re.match(r'bytes=(\d*)-(\d*)', range_header)

            if match:
                start_str, end_str = match.groups()

                try:
                    if start_str == '' and end_str:
                        suffix_length = int(end_str)
                        start = max(total_size - suffix_length, 0)
                        end = total_size - 1
                    else:
                        start = int(start_str or 0)
                        end = int(end_str) if end_str else total_size - 1

                    end = min(end, total_size - 1)

                    if start >= total_size or start > end:
                        return request.make_response(
                            b'',
                            headers=[
                                ('Content-Range', f'bytes */{total_size}'),
                                *common_headers,
                            ],
                            status=416,
                        )

                    chunk = file_content[start:end + 1]
                    body = b'' if request_method == 'HEAD' else chunk

                    headers = [
                        *common_headers,
                        ('Content-Range', f'bytes {start}-{end}/{total_size}'),
                        ('Content-Length', str(len(chunk))),
                    ]

                    return request.make_response(
                        body,
                        headers=headers,
                        status=206,
                    )

                except Exception:
                    pass

        body = b'' if request_method == 'HEAD' else file_content

        headers = [
            *common_headers,
            ('Content-Length', str(total_size)),
        ]

        return request.make_response(
            body,
            headers=headers,
            status=200,
        )

    # -------------------------------------------------------------------------
    # ENDPOINT VIDEO: STREAMING DE VIDEO DEL PRODUCTO
    # -------------------------------------------------------------------------

    @http.route(
        [
            '/api/collections/product-video/<int:product_template_id>',
            '/api/collections/product-video/<int:product_template_id>/<string:filename>',
        ],
        type='http',
        auth='public',
        methods=['GET', 'HEAD', 'OPTIONS'],
        csrf=False,
        cors='*',
    )
    def stream_product_video(self, product_template_id, filename=None, **kw):
        """
        Sirve el video subido en product.template.headless_video_file.

        La URL con filename es decorativa, pero ayuda al navegador a detectar
        mejor el tipo de archivo:
            /api/collections/product-video/123/video.mp4
        """
        if request.httprequest.method == 'OPTIONS':
            return request.make_response(
                b'',
                headers=[
                    ('Access-Control-Allow-Methods', 'GET, HEAD, OPTIONS'),
                    ('Access-Control-Allow-Headers', 'Range, Content-Type'),
                    ('Access-Control-Expose-Headers', 'Content-Length, Content-Range, Accept-Ranges'),
                ],
                status=200,
            )

        product = request.env['product.template'].sudo().browse(product_template_id)

        if not product.exists() or not product.headless_video_file:
            return request.make_response(
                'Video not found',
                headers=[('Content-Type', 'text/plain; charset=utf-8')],
                status=404,
            )

        try:
            file_content = base64.b64decode(product.headless_video_file)
            real_filename = filename or product.headless_video_filename or 'product-video.mp4'

            return self._build_video_response(
                file_content=file_content,
                filename=real_filename,
            )

        except Exception as error:
            return request.make_response(
                f"Error streaming video: {str(error)}",
                headers=[('Content-Type', 'text/plain; charset=utf-8')],
                status=500,
            )

    # -------------------------------------------------------------------------
    # ENDPOINT 1: LISTADO GENERAL DE COLECCIONES
    # -------------------------------------------------------------------------

    @http.route(
        '/api/collections_data',
        type='http',
        auth='public',
        methods=['GET', 'OPTIONS'],
        csrf=False,
        cors='*',
    )
    def get_collections_json(self):
        if request.httprequest.method == 'OPTIONS':
            return self._json_response({}, status=200)

        Category = request.env['product.category'].sudo()
        ProductTemplate = request.env['product.template'].sudo()

        categories = Category.search([
            ('is_collection', '=', True),
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
                video_payload = self._get_product_video_payload(
                    base_url=base_url,
                    product_template=product,
                    fallback_poster=img_url,
                )

                product_preview.append({
                    'id': product.id,
                    'name': product.name,
                    'slug': slug,

                    # Compatibilidad anterior
                    'image': img_url,

                    # Nuevo soporte multimedia
                    'media_type': 'video' if video_payload.get('has_video') else 'image',
                    'has_video': video_payload.get('has_video'),
                    'video_url': video_payload.get('url'),
                    'video': video_payload,

                    **self._get_availability_payload(is_sold),
                })

            data[key] = {
                'id': cat.id,
                'title': cat.collection_title_display or cat.name,
                'description': cat.collection_description or '',
                'parent': parent_key,
                'products_preview': product_preview,
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
        cors='*',
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
                status=404,
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

            video_payload = self._get_product_video_payload(
                base_url=base_url,
                product_template=product,
                fallback_poster=main_image,
            )

            is_sold = sold_map.get(product.id, False)

            product_obj = {
                'id': product.id,
                'name': product.name,
                'slug': product.headless_slug or str(product.id),
                'price': product.list_price,
                'currency': product.currency_id.symbol,

                **self._get_availability_payload(is_sold),

                'short_description': product.headless_short_description or '',
                'long_description': product.headless_long_description or '',

                'material': product.headless_material or '',
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

                # Compatibilidad anterior
                'images': {
                    'main': main_image,
                    **gallery_urls,
                },

                # Nuevo soporte multimedia
                'media_type': 'video' if video_payload.get('has_video') else 'image',
                'has_video': video_payload.get('has_video'),
                'video_url': video_payload.get('url'),
                'video': video_payload,
                'media': {
                    'type': 'video' if video_payload.get('has_video') else 'image',
                    'image': main_image,
                    'video': video_payload,
                },

                'seo': {
                    'keyword': product.headless_seo_keyword or '',
                    'meta_title': product.headless_meta_title or product.name,
                    'meta_description': product.headless_meta_description or product.headless_short_description or '',
                },
            }

            products_data.append(product_obj)

        response_data = {
            'collection_info': {
                'title': category.collection_title_display or category.name,
                'description': category.collection_description or '',
                'subtitle': category.collection_subtitle or '',
                'key': category.collection_key,
            },
            'products': products_data,
        }

        return self._json_response(response_data)