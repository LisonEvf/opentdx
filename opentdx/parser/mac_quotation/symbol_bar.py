import struct
from datetime import datetime, timedelta
from typing import Union
from opentdx._typing import override

from opentdx.const import EX_MARKET, MARKET, PERIOD, ADJUST
from opentdx.parser.baseParser import BaseParser, register_parser



# TODO 转移到公共类
def combine_to_datetime(ymd, date_num, format_tdx_time=False):
    # 解析日期
    date_str = str(ymd)
    year = int(date_str[:4])
    month = int(date_str[4:6])
    day = int(date_str[6:8])

    # date_num 是从午夜开始的秒数
    seconds = date_num
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60

    dt = datetime(year, month, day, hours, minutes)
    if format_tdx_time:
        if 0 <= dt.hour <= 5:
            dt = dt + timedelta(days=1)  # 或者 timedelta(hours=24)
        else:
            dt = dt
    return dt


@register_parser(0x122E, 1)
class SymbolBar(BaseParser):
    def __init__(self, market: MARKET | EX_MARKET, code: str, period: PERIOD, times: int = 1, start: int = 0, count: int = 700, fq: ADJUST = ADJUST.NONE):
        self.body = struct.pack("<H22sHH I HH bbb bH4s", market.value, code.encode("gbk"), period.value, times, start, count, fq.value, 1, 1, 0, 1, 0, b"")
        self.period = period
        # print("16进制: " + " ".join(f"{b:02x}" for b in self.body))
        # #debug 31 00700
        # pkg = bytearray.fromhex(f"1f00 3030 3730 3000 0000 0000 0000 0000 \

    #     0000 0000 0000 0000 0400 0100 0000 0000 \
    #     0300 0100 0101 0001 0000 0000 0000")
    # #debug 0 000100
    # pkg = bytearray.fromhex(f"0000 3030 3031 3030 0000 0000 0000 0000  \
    #     0000 0000 0000 0000 0400 0100 0000 0000  \
    #     bc02 0200 0101 0001 0000 0000 0000 ")

    @override
    def deserialize(self, data):
        row_length = 36
        header_length = 33

        header = data[:header_length]
        header_fmt = "<H12s10xBHHI"
        header_fmt_length = struct.calcsize(header_fmt)
        market, symbol, period, unknow, count, start = struct.unpack(header_fmt, header[:header_fmt_length])
        #  4a 00 54 53 4c 41 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 03 00 01 0f 00 00 00 00 00

        # 判断是否是分钟K线
        format_tdx_time = period < 4 or period == 7 or period == 8

        bars = []
        # print(f"总行数 {row_count}")
        for i in range(count):
            row_data = data[header_length + row_length * i : header_length + row_length * (i + 1)]

            fmt = "II7f"
            # fmt_length = struct.calcsize(fmt)
            # ymd 是 20201201. time_num是从当天 00:00:00 开始的秒数
            ymd, time_num, open, high, low, close, amount, vol, float_shares = struct.unpack(fmt, row_data)

            # 如果是美股或者期货, time_num是中国时间, 但ymd是美国日期. 例如 2026-03-26 22:30:00 的k线, TDX数据返回的是 2026-03-25 22:30:00 

            datetime = combine_to_datetime(ymd, time_num, format_tdx_time)
            bar = {
                "datetime": datetime,
                "open": open,
                "high": high,
                "low": low,
                "close": close,
                "vol": vol,
                "amount": amount,
                "float_shares": float_shares,  # 流通股
            }
            bars.append(bar)

        return bars
