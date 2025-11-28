## ./__init__.py
```py
from . import controllers
from . import models
```

## ./__manifest__.py
```py
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
```

## ./controllers/__init__.py
```py
from . import main
```

## ./controllers/main.py
```py
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
```

## ./models/__init__.py
```py
from . import product_category
```

## ./models/product_category.py
```py
from odoo import models, fields, api
import re

class ProductCategory(models.Model):
    _inherit = 'product.category'

    # --- Campos de Configuración ---
    is_collection = fields.Boolean(
        string="Es una Colección Pública",
        default=False,
        help="Marca esta casilla si esta categoría representa una colección en el sitio web (Next.js)."
    )

    collection_key = fields.Char(
        string="Key / Slug (JSON)",
        help="La clave única que usa el JSON (ej: 'mineral specimens'). Si se deja vacío, se genera del nombre.",
        copy=False
    )

    # --- Contenido ---
    collection_title_display = fields.Char(
        string="Título Público",
        help="Si quieres que el título en la web sea diferente al nombre interno de la categoría."
    )
    
    collection_description = fields.Text(
        string="Descripción de la Colección",
        help="Texto completo descriptivo para la página de la colección.",
        translate=True
    )

    # --- Lógica de Slugs ---
    @api.onchange('name')
    def _onchange_name_generate_slug(self):
        if not self.collection_key and self.name:
            # Genera un slug simple: 'Earth Collection' -> 'earth-collection'
            self.collection_key = self.name.lower().strip()

    _sql_constraints = [
        ('collection_key_unique', 'unique(collection_key)', 'La Key (Slug) de la colección debe ser única.')
    ]
```

## ./views/product_category_views.xml
```xml
<?xml version="1.0" encoding="utf-8"?>
<odoo>
    <record id="view_category_form_collection_inherit" model="ir.ui.view">
        <field name="name">product.category.form.collection.inherit</field>
        <field name="model">product.category</field>
        <field name="inherit_id" ref="product.product_category_form_view"/>
        <field name="arch" type="xml">
            <xpath expr="//field[@name='parent_id']" position="after">
                <field name="is_collection" widget="boolean_toggle"/>
            </xpath>
            <xpath expr="//sheet" position="inside">
                <widget name="web_ribbon" title="Colección Pública" bg_color="bg-success" invisible="not is_collection"/>
            </xpath>
            <xpath expr="//sheet" position="inside">
                <notebook invisible="not is_collection">
                    <page string="Contenido CMS (Next.js)" name="cms_content">
                        <group>
                            <group string="Identificadores">
                                <field name="collection_key" placeholder="ej: earth" required="is_collection"/>
                                <field name="collection_title_display" placeholder="Dejar vacío para usar nombre de categoría"/>
                            </group>
                            <group string="Estadísticas">
                                <field name="product_count" string="Productos Totales" readonly="1"/>
                            </group>
                        </group>
                        <separator string="Narrativa de la Colección"/>
                        <field name="collection_description" 
                               placeholder="Escribe aquí la historia de la colección (soporta saltos de línea)..."
                               widget="text" 
                               options="{'rows': 10}"/>
                    </page>
                </notebook>
            </xpath>
        </field>
    </record>

    <record id="action_product_collections" model="ir.actions.act_window">
        <field name="name">Gestor de Colecciones</field>
        <field name="res_model">product.category</field>
        <field name="view_mode">list,form</field>
        <field name="domain">[('is_collection', '=', True)]</field>
        <field name="context">{'default_is_collection': True}</field>
        <field name="help" type="html">
            <p class="o_view_nocontent_smiling_face">
                Crea tu primera Colección Web
            </p>
            <p>
                Define las categorías que se enviarán a Next.js.
            </p>
        </field>
    </record>

    <menuitem id="menu_product_collections"
              name="Colecciones Web"
              parent="stock.menu_stock_config_settings"
              action="action_product_collections"
              sequence="15"/>
</odoo>```

