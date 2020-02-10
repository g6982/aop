#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import UserError
from ..tools import dijkstras
import logging
import matplotlib.pyplot as plt
import networkx as nx

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

    network_image = fields.Binary('Network', attachment=True)

    def find_out_shortest_path(self):
        if not self.step_ids:
            raise UserError('Empty >> _ << ')
        all_location_ids = self.step_ids.mapped('location_id')
        all_location_name = {
            x.id: x.display_name for x in all_location_ids
        }
        all_location_ids = list(set(all_location_ids.ids))

        # 获取所有的箭头
        all_rule_ids = self.step_ids.mapped('out_transition_ids') + self.step_ids.mapped('in_transition_ids')

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

        # 初始化
        node_graph = dijkstras.Graph(all_node)

        # 添加节点信息
        for location_id in all_location_ids:
            # 找到该节点的所有开始
            from_rules = all_rule_ids.filtered(lambda x: x.from_id.location_id.id == location_id)
            if not from_rules:
                continue
            for from_rule_id in from_rules:
                # 找到节点
                from_node = location_node.get(from_rule_id.from_id.location_id.id)
                to_node = location_node.get(from_rule_id.to_id.location_id.id)

                # 连接 有方向的连接
                node_graph.directed_connect(from_node, to_node, from_rule_id.quantity_weight)

                # 无方向的连接
                # node_graph.connect(from_node, to_node, from_rule_id.quantity_weight)

        end_node = location_node.get(end_rule_id.location_id.id)

        res = [(weight, [n.data for n in node]) for (weight, node) in node_graph.dijkstra(end_node)]
        res = res[-1][-1]

        shortest_note = ' -> '.join(all_location_name.get(x) for x in res)

        self.shortest_note = shortest_note
        _logger.info({
            'path': [(weight, [n.data for n in node]) for (weight, node) in node_graph.dijkstra(end_node)]
        })

    def generate_all_supplier_contract_network(self):
        """
            根绝所有的供应商合同，生成一个大的网络
        """
        all_start_end_location = self.find_all_start_end_location()

        self.create_all_location_steps(all_start_end_location)

        self.generate_route_by_location(all_start_end_location)

    # 生成点
    def create_all_location_steps(self, all_start_end_location):
        all_location_ids = []
        for x in all_start_end_location:
            all_location_ids += list(x)
        all_location_ids = list(set(all_location_ids))
        all_location_ids = self.env['stock.location'].browse(all_location_ids)

        data = []
        for x in all_location_ids:
            data.append({
                'name': x.display_name,
                'location_id': x.id
            })
        all_ids = self.env['route.network.step'].create(data)
        self.step_ids = [(6, 0, all_ids.ids)]

    def generate_route_by_location(self, location_ids):
        """
            生成线段
        :param location_ids: 所有开始和结束节点
        :return:
        """
        all_steps = self.step_ids
        data = []
        for location_id in location_ids:
            from_step = all_steps.filtered(lambda x: x.location_id.id == location_id[0])
            to_step = all_steps.filtered(lambda x: x.location_id.id == location_id[1])

            if not from_step or not to_step:
                continue
            data.append({
                'from_id': from_step.id,
                'to_id': to_step.id
            })

        # empty first
        self.step_ids.mapped('out_transition_ids').unlink()
        self.step_ids.mapped('in_transition_ids').unlink()

        self.env['route.network.rule'].create(data)

    def find_all_start_end_location(self):
        """
            查找所有的线段，去重
        """
        all_supplier_contract = self.env['supplier.aop.contract'].search([])
        all_carrier_ids = all_supplier_contract.mapped('delivery_carrier_ids')

        all_location_ids = [(x.from_location_id.id, x.to_location_id.id) for x in all_carrier_ids
                            if x.from_location_id and x.to_location_id]

        # 去重
        all_start_end_location = set(all_location_ids)

        return list(all_start_end_location)


class RouteNetworkStep(models.Model):
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
