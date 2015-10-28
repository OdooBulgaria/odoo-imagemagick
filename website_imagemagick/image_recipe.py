# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution, third party addon
#    Copyright (C) 2004-2015 Vertel AB (<http://vertel.se>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64
from cStringIO import StringIO
from openerp import models, fields, api, _
from openerp.exceptions import except_orm, Warning, RedirectWarning
from openerp import http
from openerp.http import request
from openerp import SUPERUSER_ID
from datetime import datetime
from openerp.modules import get_module_resource, get_module_path
import werkzeug
import pytz
import re

from openerp.tools.safe_eval import safe_eval as eval

from wand.image import Image
from wand.display import display
from wand.drawing import Drawing
import subprocess

import logging
_logger = logging.getLogger(__name__)

class website_imagemagic(http.Controller):

    # this controller will control url: /image/image_id/magic/recipe_id
    @http.route(['/image/<model("ir.attachment"):image>/magic/<model("image.recipe"):recipe>'], type='http', auth="public", website=True)
    def view_attachment(self, image=None, recipe=None, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        return recipe.send_file(http, attachment=image)

    # this controller will control url: /image/image_url/magic/recipe_id
    @http.route(['/imageurl/<string:url>/magic/<model("image.recipe"):recipe>'], type='http', auth="public", website=True)
    def view_url(self, url=None, recipe=None, **post):
        cr, uid, context, pool = request.cr, request.uid, request.context, request.registry
        return recipe.send_file(http, url=url)


class image_recipe(models.Model):
    _name = "image.recipe"

    name = fields.Char(string='Name')
    recipe = fields.Text(string='Recipe')
    param_ids = fields.One2many(comodel_name='image.recipe.param', inverse_name='recipe_id', string='Recipes')

  # http://docs.wand-py.org/en/0.4.1/index.html

    def attachment_to_img(self, attachment):  # return an image object while filename is an attachment
        if attachment.url:  # make image url as /module_path/attachment_url and use it as filename
            path = '/'.join(get_module_path(attachment.url.split('/')[1]).split('/')[0:-1])
            return Image(filename=path + attachment.url)
        return Image(StringIO(attachment.datas).decode('base64'))

    def url_to_img(self, url):  # return an image object while filename is an url
        return Image(filename=url)

    def get_mtime(self, attachment):    # return a last modified time of an image
        if attachment.write_date > self.write_date:
            return attachment.write_date
        return self.write_date

    def send_file(self, http, attachment=None, url=None):   # return a image while given an attachment or an url
        img_watermark = Image(filename='/usr/share/odoo-addons/addons/web/static/src/img/nologo.png')
        if attachment:
            return http.send_file(StringIO(self.run(self.attachment_to_img(attachment), img_watermark=img_watermark).make_blob(format='jpg')), filename=attachment.datas_fname, mtime=self.get_mtime(attachment))
        return http.send_file(self.run(self.url_to_img(url)), filename=url)


    def run(self, image, **kwargs):   # return a image with specified recipe

        kwargs.update({p.name: p.value for p in self.param_ids})
        kwargs.update({
            'image': image,
            'user': self.env['res.users'].browse(self._uid),
            })
        eval(self.recipe, kwargs, mode='exec', nocopy=True)
        return image


class image_recipe_param(models.Model):
    _name = "image.recipe.param"

    name = fields.Char(string='Name')
    value = fields.Char(string='Value')
    recipe_id = fields.Many2one(comodel_name='image.recipe', string='Recipe')
