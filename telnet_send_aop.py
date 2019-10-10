#!/usr/bin/env python3
import asyncio
import telnetlib3
import requests
import json

HOST_IP = '172.16.107.109'
HOST_PORT = 6023
WAREHOUSE_ID = -1

BASE_URL = 'http://127.0.0.1:8069'
BARCODE_URL = BASE_URL + '/api/barcode/'
WAREHOUSE_URL = BASE_URL + '/api/warehouse/list'


def _warehouse_ui(writer, option=False):
    if not option:
        data = {
            'code': 'warehouse'
        }
        res = requests.post(WAREHOUSE_URL, data)
        warehouse_data = json.loads(res.content)
        for w_key in warehouse_data.keys():
            writer.write(u'{}: {}\r\n'.format(int(w_key) + 1, warehouse_data.get(w_key)))
    else:
        _stock_picking_type_ui(writer)


def _stock_picking_type_ui(writer, option=False):
    pass


def stock_picking_ui(writer, option=False):
    pass


@asyncio.coroutine
def shell(reader, writer):

    _warehouse_ui(writer)
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
            res = requests.post(BARCODE_URL + barcode_value, data)
            writer.write('barcode_value: {}, return: {}\r\n'.format(barcode_value, res.content))
            _warehouse_ui(writer, option=barcode_value)
            barcode_value = ''
        # display all server output
    # EOF
    print()

loop = asyncio.get_event_loop()
coro = telnetlib3.create_server(host=HOST_IP, port=HOST_PORT, shell=shell)
server = loop.run_until_complete(coro)
loop.run_until_complete(server.wait_closed())