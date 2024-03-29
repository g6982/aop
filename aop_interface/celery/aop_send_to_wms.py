# /usr/bin/env python3
# -*- coding: utf-8 -*-
from celery import Celery
import logging
import json
try:
    from ..config import send_to_wms_config
    from ..config.wsdl_zeep_config import get_zeep_client_session
except:
    import send_to_wms_config
    from wsdl_zeep_config import get_zeep_client_session


_logger = logging.getLogger(__name__)


# 配置好celery的backend和broker
app = Celery('aop_send_to_wms')
app.config_from_object(send_to_wms_config)


# 使用celery 队列发送数据给WMS
@app.task(max_retries=5, retry_backoff=True, name='send_stock_picking_to_wms_task')
def send_stock_picking_to_wms(task_url, data):
    zeep_stock_picking_client = get_zeep_client_session(task_url)
    _logger.info({
        'data': data
    })
    # 发送任务的数据
    zeep_stock_picking_client.service.sendToTask(json.dumps(data, ensure_ascii=False))