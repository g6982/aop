#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from odoo import models, api, fields
from odoo.exceptions import UserError
from ..tools import dijkstras
import logging
import matplotlib.pyplot as plt
import networkx as nx
import traceback

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

    start_location_id = fields.Many2one('stock.location', 'Start')
    end_location_id = fields.Many2one('stock.location', 'End')

    network_image = fields.Binary('Network', attachment=True)

    def find_out_shortest_path_with_networkx(self):
        # 初始化
        network_x_g = nx.DiGraph()

        if not self.step_ids:
            raise UserError('Empty >> _ << ')

        # 获取所有的箭头
        all_rule_ids = self.step_ids.mapped('out_transition_ids') + self.step_ids.mapped('in_transition_ids')

        all_rule_ids = [(x.from_id, x.to_id, x.quantity_weight) for x in all_rule_ids]

        # 去重
        all_rule_ids = list(set(all_rule_ids))

        # 所有节点的信息，包括权重
        tmp_node = [(x[0].display_name, x[1].display_name, x[2]) for x in all_rule_ids]

        tmp_node = list(set(tmp_node))

        network_x_g.add_weighted_edges_from(tmp_node)

        source_id = self.start_location_id.display_name
        target_id = self.end_location_id.display_name

        shortest_path = nx.shortest_path(network_x_g, source=source_id, target=target_id)
        # shortest_path = nx.shortest_path_length(network_x_g, source=source_id, target=target_id)
        # shortest_path = nx.shortest_path_length(network_x_g)

        _logger.info({
            'shortest_path': shortest_path,
            'source_id': source_id,
            'target_id': target_id,
        })
        shortest_note = ' -> '.join(x for x in shortest_path)
        self.shortest_note = shortest_note

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

    def generate_all_customer_contract_network(self):
        """
            根据所有的客户合同，生成一个大的网络
        """
        all_start_end_location = self.find_all_start_end_location(model_name='customer.aop.contract')

        self.create_all_location_steps(all_start_end_location)

        self.generate_route_by_location(all_start_end_location)

    def generate_all_supplier_contract_network(self):
        """
            根据所有的供应商合同，生成一个大的网络
        """
        all_start_end_location = self.find_all_start_end_location(model_name='supplier.aop.contract')
        # all_start_end_location = self.find_all_start_end_location_with_weight(model_name='supplier.aop.contract')

        self.create_all_location_steps(all_start_end_location)

        self.generate_route_by_location(all_start_end_location)
        # self.generate_route_by_location_with_weight(all_start_end_location)

    # 生成点
    def create_all_location_steps(self, all_start_end_location):
        all_location_ids = []
        for x in all_start_end_location:
            all_location_ids += list(x)[:2]

        # 所有位置
        all_location_ids = list(set(all_location_ids))
        all_location_ids = self.env['stock.location'].browse(all_location_ids)

        data = []
        for x in all_location_ids:
            data.append({
                'name': x.display_name,
                'location_id': x.id
            })

        # delete first
        self.step_ids.unlink()

        all_ids = self.env['route.network.step'].create(data)

        self.step_ids = [(6, 0, all_ids.ids)]

    def generate_route_by_location_with_weight(self, location_ids):
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
                'to_id': to_step.id,
                'quantity_weight': location_id[2]
            })
        # empty first
        self.step_ids.mapped('out_transition_ids').unlink()
        self.step_ids.mapped('in_transition_ids').unlink()

        res = self.env['route.network.rule'].create(data)

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
                'to_id': to_step.id,
            })

        # empty first
        self.step_ids.mapped('out_transition_ids').unlink()
        self.step_ids.mapped('in_transition_ids').unlink()

        res = self.env['route.network.rule'].create(data)

    def find_all_start_end_location_with_weight(self, model_name=False):
        all_supplier_contract = self.env[model_name].search([])
        all_carrier_ids = all_supplier_contract.mapped('delivery_carrier_ids')

        if model_name == 'supplier.aop.contract':
            all_location_ids = [
                (x.from_location_id, x.to_location_id, x.product_standard_price) for x in all_carrier_ids
                if x.from_location_id and x.to_location_id]
        elif model_name == 'customer.aop.contract':
            all_location_ids = [(x.from_location_id, x.to_location_id, x.fixed_price) for x in all_carrier_ids
                                if x.from_location_id and x.to_location_id]

        # 去重
        all_location_ids = list(set(all_location_ids))

        all_location_ids = [(x[0].id, x[1].id, x[2]) for x in all_location_ids if
                            not x[0].display_name.startswith('合作伙伴位置') and
                            not x[1].display_name.startswith('合作伙伴位置')]
        return all_location_ids

    def find_all_start_end_location(self, model_name=False):
        """
            查找所有的线段，去重
        """
        all_supplier_contract = self.env[model_name].search([])
        all_carrier_ids = all_supplier_contract.mapped('delivery_carrier_ids')

        all_location_ids = [(x.from_location_id, x.to_location_id) for x in all_carrier_ids
                            if x.from_location_id and x.to_location_id]

        # 去重
        all_location_ids = list(set(all_location_ids))

        all_location_ids = [(x[0].id, x[1].id) for x in all_location_ids if
                            not x[0].display_name.startswith('合作伙伴位置') and
                            not x[1].display_name.startswith('合作伙伴位置')]

        return all_location_ids


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

    quantity_weight = fields.Float('Weight')

    @api.multi
    @api.depends('from_id', 'to_id')
    def _compute_name(self):
        for line_id in self:
            if line_id.from_id and line_id.to_id:
                line_id.name = line_id.from_id.name + ' -> ' + line_id.to_id.name
