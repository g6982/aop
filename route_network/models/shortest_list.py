#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, api, fields


class RouteNetworkShortestPath(models.Model):
    _name = 'route.network.shortest.path'

    name = fields.Char('Location name')
