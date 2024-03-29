
'Use <m> or <message> to retrieve the data transmitted by the scanner.'
'Use <t> or <terminal> to retrieve the running terminal browse record.'
'Put the returned action code in <act>, as a single character.'
'Put the returned result or message in <res>, as a list of strings.'
'Put the returned value in <val>, as an integer'

#保存步骤名称
if not terminal.get_tmp_value('picking_type_name', False):
  terminal.update_tmp_values({'picking_type_name': message})

# lst = [
#         ('brand_name', '车型'),
#         ('from_location', '车辆来自'),
#         ('vin_scan', 'VIN码扫描'),
#         ('submit', '提交'),
#       ]

# 车型
product_name = terminal.get_tmp_value('product_name', False)
product_model = terminal.get_tmp_value('product_model', False)

# 车辆来自
from_location_name = terminal.get_tmp_value('from_location_name', False)

# vin扫描数量
vin_scan_count = terminal.get_tmp_value('vin_scan_count', 0)

lst = []

if product_name:
  lst.append(('brand_name', '车型' + '({0}/{1})'.format(product_name, product_model)))
else:
  lst.append(('brand_name', '车型'))
  
  
if from_location_name:
  lst.append(('from_location', '车辆来自' + '({0})'.format(from_location_name)))
else:
  lst.append(('from_location', '车辆来自'))
  
  
if vin_scan_count>0:
  lst.append(('vin_scan', 'VIN码扫描' + '({0})'.format(vin_scan_count))) 
else:
  lst.append(('vin_scan', 'VIN码扫描'))
  
  
lst.append(('submit', '提交'))

act = 'L'

res = [
    ('|', _('入库'))
]

for line in lst: 
  res.append((line[0], line[1]))