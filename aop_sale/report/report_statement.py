from odoo.http import request
from odoo import models, api
import logging
import time
from odoo import fields

_logger = logging.getLogger(__name__)


class ReportStatement(models.AbstractModel):
    _name = 'report.aop_sale.standard_statement_report_xlsx'
    _inherit = 'report.report_xlsx.abstract'

    def generate_xlsx_report(self, workbook, data, orde_ids):
        records = self.env['sale.order'].browse(data.get('record', []))
        sheet = workbook.add_worksheet('statement01')

        # 格式化
        merge_format = workbook.add_format({
            'bold': True,
            'border': 1,
            'align': 'center',
            'valign': 'center'
        })
        sheet.merge_range('A1:Q1', u'生产费用报销单', merge_format)
        sheet.merge_range('A2:Q2', u'报销单位：重庆中集-重庆中集汽车物流有限责任公司', merge_format)
        # sheet.write(0, 0, u'生产费用报销单')
        # sheet.write(1, 0, u'报销单位：重庆中集-重庆中集汽车物流有限责任公司')
        sheet.merge_range('A3:H3', fields.Datetime.now(), merge_format)
        sheet.merge_range('I3:Q3', u'报销单号： ' + str(time.time()), merge_format)
        sheet.merge_range('A4:B4', u'销售体系', merge_format)
        sheet.merge_range('C4:G4', u'长安福特', merge_format)
        sheet.merge_range('H4:J4', u'运输方式', merge_format)
        sheet.merge_range('K4:Q4', u'联运第二段GL', merge_format)

        # 交接单			数量	起始地-目的地			车型				单价	金额			扣款	过海费

        border = workbook.add_format({
            'border': 1
        })
        sheet.merge_range('A5:C5', u'交接单', merge_format)
        sheet.write(4, 3, u'数量', merge_format)
        # sheet.merge_range('D5:D5', u'数量', merge_format)
        sheet.merge_range('E5:G5', u'起始地-目的地', merge_format)
        sheet.merge_range('H5:K5', u'车型', merge_format)
        sheet.write(4, 11, u'单价', merge_format)
        sheet.merge_range('M5:O5', u'金额', merge_format)
        sheet.write(4, 15, u'扣款', merge_format)
        sheet.write(4, 16, u'过海费', merge_format)
        # sheet.merge_range('P5:P5', u'扣款', merge_format)
        # sheet.merge_range('Q5:Q5', u'过海费', merge_format)
        # sheet.merge_range('E5:G5', u'起始地-目的地', merge_format)
        # sheet.write(4, 7, u'过海费', bold)
        # for obj in records:
        #     report_name = obj.name
        #     # One sheet by order
        #     sheet = workbook.add_worksheet(report_name[:31])
        #     bold = workbook.add_format({'bold': True})
        #     sheet.write(0, 0, obj.name, bold)
