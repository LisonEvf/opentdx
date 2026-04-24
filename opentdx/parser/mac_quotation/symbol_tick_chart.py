
from datetime import date, datetime, time
import struct
from typing import Union

from opentdx.const import EX_MARKET, MARKET
from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import industry_to_board_symbol


@register_parser(0x122D, 1)
class SymbolTickChart(BaseParser):
    
    def __init__(self, market: Union[MARKET, EX_MARKET], code: str, query_date: date = None ):
        # ymd = 20260101
        if query_date is not None:
            ymd = int(query_date.strftime("%Y%m%d"))
        else:
            ymd = 0
        self.body = struct.pack("<H22sI5H", market.value, code.encode("gbk"), ymd, 1,0,0,0,0)

    def deserialize(self, data):
        market, code, date_raw, u, price, count = struct.unpack("<H22sIBfH", data[:35])

        chart_data = []
        for i in range(count):
            minutes, price, avg, vol, momentum = struct.unpack("<HffIf", data[35 + i * 18: 35 + (i + 1) * 18])
            chart_data.append({
                'time': time(minutes // 60 % 24, minutes % 60),
                "price": price,
                "avg": avg,
                "vol": vol,
                "momentum": momentum
            })
        
        name, decimal, category, vol_unit, date_raw, time_raw,\
        pre_close, open, high, low, close, momentum, vol, amount, turnover, avg, industry = struct.unpack("<44sBHf5x2I5ffIf12x2fI", data[35 + count * 18:])
        
        return {
            "market": market,
            "code": code.decode("gbk").rstrip(chr(0)),
            "name": name.decode("gbk").rstrip(chr(0)),
            "decimal": decimal,
            "category": category,
            "vol_unit": vol_unit,
            "time": datetime(date_raw//10000, (date_raw%10000)//100, date_raw%100, time_raw//10000, (time_raw%10000)//100, time_raw%100),
            "pre_close": pre_close,
            "open": open,
            "high": high,
            "low": low,
            "close": close,
            "momentum": momentum,
            "vol": vol,
            "amount": amount,
            "turnover": turnover,
            "avg": avg,
            "industry": industry,
            "industry_code": industry_to_board_symbol(industry),
            "chart_data": chart_data
        }