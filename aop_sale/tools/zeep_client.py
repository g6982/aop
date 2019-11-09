from requests import Session
from zeep.transports import Transport
from zeep import Client


session = Session()
session.verify = False
transport = Transport(session=session)

# 客户供应商
zeep_supplier_client = Client('https://222.66.94.66:9081/zjwms/ws/supplierInfo?wsdl', transport=transport)

# 任务
zeep_task_client = Client('https://222.66.94.66:9081/zjwms/ws/generationTask?wsdl', transport=transport)

# 库存检查
zeep_check_stock_client = Client('https://222.66.94.66:9081/zjwms/ws/searchInventory?wsdl', transport=transport)

SUPPLIER_FIELD_DICT = {
    'name': 'name',
    'ref': 'code',
    'country_id': 'country_name',
    'state_id': 'state_name',
    'city_id': 'city_name',
    'district_id': 'district_name',
    'street': 'street_name'
}