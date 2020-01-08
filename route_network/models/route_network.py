#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, api, fields
from ..tools import dijkstras
import logging

_logger = logging.getLogger(__name__)


class RouteNetwork(models.Model):
    _name = 'route.network'

    name = fields.Char('Name')
    partner_id = fields.Many2one('res.partner', 'Partner')
    step_ids = fields.One2many(
        comodel_name='route.network.step',
        inverse_name='network_id',
        string='Network',
        ondelete='cascade',
        help='Network.')

    shortest_note = fields.Text('Shortest')

    def find_out_shortest_path(self):
        all_location_ids = self.step_ids.mapped('location_id')
        all_location_ids = list(set(all_location_ids.ids))
        
        # 获取所有的箭头
        all_rule_ids = self.env['route.network.rule'].search([
            ('from_id', 'in', self.step_ids.ids),
            ('to_id', 'in', self.step_ids.ids)
        ])

        # 找到最开始的节点和最后的节点
        start_rule_id = self.step_ids.filtered(lambda x: not x.out_transition_ids)
        end_rule_id = self.step_ids.filtered(lambda x: not x.in_transition_ids)

        # 注册所有的节点
        all_node = []
        location_node = {}
        for location_id in all_location_ids:
            node_id = dijkstras.Node(location_id)
            location_node[location_id] = node_id
            all_node.append(node_id)

        _logger.info({
            'all node': all_node,
            'all_location_ids': all_location_ids
        })
        # 初始化
        node_graph = dijkstras.Graph(all_node)

        _logger.info({
            'node_graph': node_graph
        })
        # 添加节点信息
        for location_id in all_location_ids:
            # 找到该节点的所有开始
            from_rules = all_rule_ids.filtered(lambda x: x.from_id.location_id.id == location_id)
            for from_rule_id in from_rules:
                # 找到节点
                from_node = location_node.get(from_rule_id.from_id.location_id.id)
                to_node = location_node.get(from_rule_id.to_id.location_id.id)

                # 连接
                node_graph.connect(from_node, to_node, from_rule_id.quantity_weight)

        end_node = location_node.get(end_rule_id.location_id.id)

        res = [(weight, [n.data for n in node]) for (weight, node) in node_graph.dijkstra(end_node)]
        res = res[-1][-1]

        all_location_ids = self.env['stock.location'].browse(res)
        shortest_note = ' -> '.join(x.display_name for x in all_location_ids)

        self.shortest_note = shortest_note
        _logger.info({
            'path': [(weight, [n.data for n in node]) for (weight, node) in node_graph.dijkstra(end_node)]
        })


class RouteNetwork(models.Model):
    _name = 'route.network.step'

    network_id = fields.Many2one('route.network')
    name = fields.Char('Name')
    location_id = fields.Many2one('stock.location', string='Location')

    out_transition_ids = fields.One2many(
        comodel_name='route.network.rule',
        inverse_name='from_id',
        string='From',
        ondelete='cascade')
    in_transition_ids = fields.One2many(
        comodel_name='route.network.rule',
        inverse_name='to_id',
        string='To',
        ondelete='cascade')


class RouteNetworkRule(models.Model):
    _name = 'route.network.rule'
    _order = 'sequence'

    name = fields.Char('Name', compute='_compute_name')

    sequence = fields.Integer(
        string='Sequence',
        default=0,
        required=False,
        help='Sequence order.')

    from_id = fields.Many2one('route.network.step')
    to_id = fields.Many2one('route.network.step')

    quantity_weight = fields.Integer('Weight')

    @api.multi
    @api.depends('from_id', 'to_id')
    def _compute_name(self):
        for line_id in self:
            if line_id.from_id and line_id.to_id:
                line_id.name = line_id.from_id.name + ' -> ' + line_id.to_id.name
