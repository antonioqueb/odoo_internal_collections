# -*- coding: utf-8 -*-

import mimetypes
import re

from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    # CONTENIDO CMS / HEADLESS
    # -------------------------------------------------------------------------

    headless_short_description = fields.Text(
        string="Descripción Corta",
        help="Breve resumen para tarjetas de producto."
    )

    headless_long_description = fields.Html(
        string="Descripción Larga (Rich Text)",
        help="Contenido completo del producto."
    )

    headless_material = fields.Char(
        string="Material / Composición"
    )

    # -------------------------------------------------------------------------
    # IMÁGENES EXTRA
    # -------------------------------------------------------------------------

    headless_image_1 = fields.Image(
        string="Imagen Extra 1",
        max_width=1920,
        max_height=1920,
    )
    headless_image_2 = fields.Image(
        string="Imagen Extra 2",
        max_width=1920,
        max_height=1920,
    )
    headless_image_3 = fields.Image(
        string="Imagen Extra 3",
        max_width=1920,
        max_height=1920,
    )
    headless_image_4 = fields.Image(
        string="Imagen Extra 4",
        max_width=1920,
        max_height=1920,
    )

    # -------------------------------------------------------------------------
    # VIDEO DEL PRODUCTO
    # -------------------------------------------------------------------------

    headless_video_file = fields.Binary(
        string="Archivo de Video",
        attachment=True,
        help="Video local del producto para mostrar en la web. Formatos recomendados: MP4 o WebM."
    )

    headless_video_filename = fields.Char(
        string="Nombre archivo video"
    )

    headless_video_url_manual = fields.Char(
        string="URL Externa de Video",
        help="Opcional. Usa este campo si el video está alojado fuera de Odoo."
    )

    headless_video_poster = fields.Image(
        string="Poster / Portada del Video",
        max_width=1920,
        max_height=1920,
        help="Imagen de portada para mostrar antes de reproducir el video."
    )

    # -------------------------------------------------------------------------
    # DIMENSIONES ESPECÍFICAS
    # -------------------------------------------------------------------------

    dim_length = fields.Float(string="Largo (cm)")
    dim_width = fields.Float(string="Ancho (cm)")
    dim_height = fields.Float(string="Alto (cm)")

    # -------------------------------------------------------------------------
    # SEO & URLS
    # -------------------------------------------------------------------------

    headless_slug = fields.Char(
        string="Slug URL",
        copy=False,
        help="Identificador único para la URL del frontend."
    )

    headless_seo_keyword = fields.Char(
        string="Palabra Clave SEO"
    )

    headless_meta_title = fields.Char(
        string="Meta Título"
    )

    headless_meta_description = fields.Text(
        string="Meta Descripción"
    )

    # -------------------------------------------------------------------------
    # HELPERS VIDEO
    # -------------------------------------------------------------------------

    def _headless_absolute_url(self, url, base_url=None):
        self.ensure_one()

        if not url:
            return ''

        url = url.strip()

        if url.startswith('http://') or url.startswith('https://') or url.startswith('//'):
            return url

        if base_url:
            return f"{base_url.rstrip('/')}/{url.lstrip('/')}"

        return url

    def _get_headless_safe_video_filename(self):
        self.ensure_one()

        filename = self.headless_video_filename or 'product-video.mp4'
        filename = filename.strip().replace(' ', '_')
        filename = re.sub(r'[^A-Za-z0-9._-]', '', filename)

        return filename or 'product-video.mp4'

    def _get_headless_video_mimetype(self):
        self.ensure_one()

        filename = self.headless_video_filename or 'product-video.mp4'
        mimetype, _encoding = mimetypes.guess_type(filename)

        return mimetype or 'video/mp4'

    def get_headless_video_src(self, base_url=None):
        """
        Prioridad:
        1. Archivo de video subido en Odoo.
        2. URL externa manual.

        Devuelve URL absoluta si se pasa base_url.
        """
        self.ensure_one()

        if self.headless_video_file:
            safe_filename = self._get_headless_safe_video_filename()
            relative_url = f"/api/collections/product-video/{self.id}/{safe_filename}"
            return self._headless_absolute_url(relative_url, base_url=base_url)

        if self.headless_video_url_manual:
            return self._headless_absolute_url(
                self.headless_video_url_manual,
                base_url=base_url,
            )

        return ''

    def get_headless_video_poster_src(self, base_url=None):
        self.ensure_one()

        if self.headless_video_poster:
            relative_url = f"/web/image/product.template/{self.id}/headless_video_poster"
            return self._headless_absolute_url(relative_url, base_url=base_url)

        return ''

    def get_headless_video_payload(self, base_url=None, fallback_poster=None):
        """
        Payload listo para el frontend.

        Ejemplo:
        {
            "has_video": true,
            "url": "https://erp.../api/collections/product-video/10/video.mp4",
            "poster": "https://erp.../web/image/...",
            "source": "uploaded",
            "filename": "video.mp4",
            "mimetype": "video/mp4"
        }
        """
        self.ensure_one()

        video_url = self.get_headless_video_src(base_url=base_url)
        has_video = bool(video_url)

        source = None
        if self.headless_video_file:
            source = 'uploaded'
        elif self.headless_video_url_manual:
            source = 'external'

        poster = ''
        if has_video:
            poster = self.get_headless_video_poster_src(base_url=base_url) or fallback_poster or ''

        return {
            'has_video': has_video,
            'url': video_url,
            'poster': poster,
            'source': source,
            'filename': self.headless_video_filename or '',
            'mimetype': self._get_headless_video_mimetype() if self.headless_video_file else '',
        }

    # -------------------------------------------------------------------------
    # GENERACIÓN AUTOMÁTICA DE SLUG
    # -------------------------------------------------------------------------

    @api.onchange('name')
    def _onchange_name_slug(self):
        if not self.headless_slug and self.name:
            s = self.name.lower().strip()
            s = re.sub(r'[^a-z0-9\s-]', '', s)
            self.headless_slug = re.sub(r'\s+', '-', s)

    _sql_constraints = [
        ('headless_slug_unique', 'unique(headless_slug)', 'El Slug del producto debe ser único.')
    ]