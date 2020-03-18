#-*- coding: utf-8 -*-

from pyecharts import options as opts
from pyecharts.charts import Geo
from pyecharts.globals import ChartType, SymbolType
import json
import requests


# 获取所有经纬度
def get_all_lat_long(all_location_dict):
    all_location_lat_lang = {}
    geo_obj = Geo()
    cd_lat_lang = geo_obj.get_coordinate(name='成都')
    for location_id in all_location_dict.keys():
        tmp = geo_obj.get_coordinate(name=all_location_dict.get(location_id))
        if not tmp:
            tmp = cd_lat_lang

        all_location_lat_lang[location_id] = tmp
    return all_location_lat_lang


# 添加所有存在经纬度的位置记录
def add_new_location_records(all_location_lat_lang, all_location_dict):
    res = {}
    for location_id in all_location_lat_lang.keys():
        res[all_location_dict.get(location_id)] = all_location_lat_lang.get(location_id)
    return res


def get_all_line(all_location_lat_lang, all_line, all_location_dict):
    res = []

    for line_id in all_line:
        # 所有线段节点，都必须要有经纬度才行
        if str(line_id[0]) and str(line_id[1]) in all_location_lat_lang.keys():
            # print(line_id)
            res.append(
                (all_location_dict.get(str(line_id[0])), all_location_dict.get(str(line_id[1])))
            )

    return res


# 获取 odoo 所有 位置信息
def get_all_location_line():
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36'
    }
    url = 'http://127.0.0.1:8069/api/location/all_location_line'
    res = requests.get(url, headers=headers)
    data = json.loads(res.content)

    all_location_dict = data.get('all_location_dict', False)

    # 所有经纬度
    all_location_lat_lang = get_all_lat_long(all_location_dict)

    # 获取所有存在经纬度的位置，作为连接
    new_location_dict = {location_id: all_location_dict.get(location_id) for location_id in all_location_lat_lang}

    all_line = data.get('all_line')

    all_location_display_name = data.get('all_location_display_name')

    new_location_records = add_new_location_records(all_location_lat_lang, all_location_dict)
    new_location_line = get_all_line(all_location_lat_lang, all_line, all_location_dict)

    with open('location.json', 'w') as f:
        f.write(json.dumps(new_location_records))
    f.close()

    return new_location_line


def geo_lines() -> Geo:
    new_location_line = get_all_location_line()
    c = (
        Geo()
        .add_schema(maptype="china")
        .add_coordinate_json(json_file='location.json')
        .add(
            "geo",
            new_location_line,
            type_=ChartType.LINES,
            effect_opts=opts.EffectOpts(symbol=SymbolType.ARROW, symbol_size=6, color="purple"),
            linestyle_opts=opts.LineStyleOpts(curve=0.2),
        )
        .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
        .set_global_opts(title_opts=opts.TitleOpts(title="Geo-Map-Lines"))
    )
    # c = (
    #     Geo()
    #     .add_schema(maptype="china")
    #     .add_coordinate_json(json_file=new_location_records)
    #     .add(
    #         "",
    #         [("广州", 55), ("北京", 66), ("杭州", 77), ("重庆", 88)],
    #         type_=ChartType.EFFECT_SCATTER,
    #         color="white",
    #     )
    #     .add(
    #         "geo",
    #         [("广州", "上海"), ("广州", "北京"), ("广州", "杭州"), ("广州", "重庆"), ("重庆", "北京")],
    #         type_=ChartType.LINES,
    #         effect_opts=opts.EffectOpts(
    #             symbol=SymbolType.ARROW, symbol_size=6, color="purple"
    #         ),
    #         linestyle_opts=opts.LineStyleOpts(curve=0.2),
    #     )
    #     .set_series_opts(label_opts=opts.LabelOpts(is_show=False))
    #     .set_global_opts(title_opts=opts.TitleOpts(title="Geo-Map-Lines"))
    # )

    # 返回 html
    # return c.render_embed()

    # 返回 json
    # return c.dump_options()
    # 但是无法加载

    return c.dump_options_with_quotes()