#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import asyncio
import telnetlib3
import requests
import json
import os

rows, columns = os.popen('stty size', 'r').read().split()

HOST_IP = '172.16.107.109'
HOST_RANGE = range(6023, 7023)
HOST_PORT = 6023
WAREHOUSE_ID = -1

BASE_URL = 'http://127.0.0.1:8069'
BARCODE_URL = BASE_URL + '/api/barcode/'
WAREHOUSE_URL = BASE_URL + '/api/warehouse/list'
PICKING_TYPE_URL = BASE_URL + '/api/stock_picking_type/list/'
PICKING_ID_URL = BASE_URL + '/api/stock_picking/list'
HEADERS = {
    'Content-Type': 'application/json',
    'charset': 'utf-8',
}


class BarcodeWMS:
    def __init__(self, host_ip, host_port):
        '''
        :param host_ip: telnet IP
        :param host_port: telnet 端口
        '''
        self.warehouse_data = False
        self.picking_type_data = False
        self.picking_data = False
        self._host = host_ip
        self._port = host_port
        self._warehouse_id = False
        self._picking_type_id = False
        self._picking_id = False
        self._reader = False
        self._writer = False

        self.run()

    @property
    def warehouse_id(self):
        return self._warehouse_id

    @warehouse_id.setter
    def warehouse_id(self, value):
        self._warehouse_id = value

    # 仓库数据
    @staticmethod
    def _get_warehouse_data():
        res = requests.post(WAREHOUSE_URL, headers=HEADERS)
        warehouse_data = json.loads(res.content)
        warehouse_data = warehouse_data.get('result')
        warehouse_data = json.loads(warehouse_data)
        return warehouse_data

    # 仓库界面
    def _warehouse_ui(self, writer, option=False, reader=False):
        if not option:
            data = {
                'params': {
                    'code': 'warehouse'
                }
            }
            res = requests.post(WAREHOUSE_URL, json.dumps(data), headers=HEADERS)

            try:
                warehouse_data = json.loads(res.content)
            except Exception as e:
                return
            warehouse_data = warehouse_data.get('result')
            warehouse_data = json.loads(warehouse_data)
            self.warehouse_data = warehouse_data
            print('warehouse_data: ', warehouse_data)
            writer.write(u'仓库信息\r\n'.center(80))
            for w_key in warehouse_data.keys():
                writer.write(u'{}: {}\r\n'.format(int(w_key) + 1, warehouse_data.get(w_key)))
        else:
            self._warehouse_id = option
            self._stock_picking_type_ui(writer, option=option, reader=reader)

    # 步骤的数据
    def _get_picking_type_data(self, option, writer):
        data = {
            'params': {
                'warehouse_name': self.warehouse_data.get(option)
            }
        }
        print('data: ', data)

        res = requests.post(PICKING_TYPE_URL + str(option), json.dumps(data), headers=HEADERS)
        if res.status_code != 200:
            return self._warehouse_ui(writer)

        picking_type_data = json.loads(res.content)
        picking_type_data = picking_type_data.get('result')
        picking_type_data = json.loads(picking_type_data)
        return picking_type_data

    # 步骤界面
    def _stock_picking_type_ui(self, writer, option=False, reader=False):
        if not option:
            return
        data = {
            'params': {
                'warehouse_name': self.warehouse_data.get(option)
            }
        }
        print('data: ', data)

        res = requests.post(PICKING_TYPE_URL + str(option), json.dumps(data), headers=HEADERS)
        if res.status_code != 200:
            return self._warehouse_ui(writer)

        picking_type_data = json.loads(res.content)
        picking_type_data = picking_type_data.get('result')
        picking_type_data = json.loads(picking_type_data)

        self.picking_type_data = picking_type_data
        print('picking_type_data: ', picking_type_data)
        writer.write(u'步骤信息\r\n'.center(80))
        for p_key in picking_type_data.keys():
            writer.write(u'{}: {}\r\n'.format(int(p_key) + 1, picking_type_data.get(p_key)))

        self._stock_picking_ui(writer, option=option)

    # 任务的数据
    def _get_picking_data(self, option, writer):
        data = {
            'params': {
                'warehouse_name': self.warehouse_data.get(option)
            }
        }
        print('data: ', data)

        res = requests.post(PICKING_ID_URL + str(option), json.dumps(data), headers=HEADERS)
        if res.status_code != 200:
            return self._warehouse_ui(writer)

        picking_data = json.loads(res.content)
        picking_data = picking_data.get('result')
        picking_data = json.loads(picking_data)
        return picking_data

    # 任务界面
    def _stock_picking_ui(self, writer, option=False):
        if not option:
            return
        data = {
            'params': {
                'warehouse_name': self.warehouse_data.get(option)
            }
        }
        print('data: ', data)

        res = requests.post(PICKING_ID_URL + str(option), json.dumps(data), headers=HEADERS)
        if res.status_code != 200:
            return self._warehouse_ui(writer)

        picking_data = json.loads(res.content)
        picking_data = picking_data.get('result')
        picking_data = json.loads(picking_data)

        self.picking_data = picking_data
        print('picking_type_data: ', picking_data)
        writer.write(u'任务信息\r\n'.center(80))
        for p_key in picking_data.keys():
            writer.write(u'{}: {}\r\n'.format(int(p_key) + 1, picking_data.get(p_key)))

    # 接收输入
    # writer._transport._sock_fd 可以获取到 客户端的ID
    @asyncio.coroutine
    def shell(self, reader, writer):

        # FIXME: 初始化界面，显示仓库？
        self._warehouse_ui(writer)

        barcode_value = ''
        while True:
            # read stream until '?' mark is found
            outp = yield from reader.read(4096)

            if not outp:
                # End of File
                break
            elif '?' in outp:
                # reply all questions with 'y'.
                writer.write('y')
            if '\r' != outp:
                barcode_value += outp

            else:
                data = {
                    'barcode_value': barcode_value
                }
                # print('data: ', data)
                # res = requests.post(BARCODE_URL + barcode_value, data)
                # writer.write('barcode_value: {}, return: {}\r\n'.format(barcode_value, res.content))

                # 没有选择仓库
                if not self._warehouse_id:
                    self._warehouse_ui(writer, option=barcode_value, reader=reader)

                # 已经指定了仓库, 没有指定作业类型
                if self._warehouse_id and not self._picking_type_id:
                    self._stock_picking_type_ui(writer, option=barcode_value, reader=reader)

                # 已经指定了仓库, 指定了作业类型，没有指定任务
                if self._warehouse_id and self._picking_type_id and not self._picking_id:
                    self._stock_picking_ui(writer, option=barcode_value, reader=reader)

                # 已经指定了仓库, 指定了作业类型，指定任务，完成任务
                if self._warehouse_id and self._picking_type_id and self._picking_id:
                    pass

                barcode_value = ''
            # display all server output
        # EOF
        print()

    def run(self):
        loop = asyncio.get_event_loop()
        coro = telnetlib3.create_server(host=self._host, port=self._port, shell=self.shell)
        server = loop.run_until_complete(coro)
        loop.run_until_complete(server.wait_closed())


if __name__ == '__main__':
    barcode_wms = BarcodeWMS(HOST_IP, HOST_PORT)
