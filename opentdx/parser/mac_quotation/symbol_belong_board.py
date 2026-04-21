import json
import struct
from opentdx._typing import override

import pandas as pd
from opentdx.const import  MARKET

from opentdx.parser.baseParser import BaseParser, register_parser


@register_parser(0x1218,1)
class SymbolBelongBoard(BaseParser):
    '''股票关联行情'''
    def __init__(self, symbol: str, market: MARKET):


        query_info_str = "Stock_GLHQ".encode("ascii")
        # self.body = struct.pack('<I9x', board_code)
        self.body = struct.pack("<H8s16x21s", market.value, symbol.encode("gbk"), query_info_str)
        #TODO 另外还有 Stock_ZJLX 资金流向, 内容为主力流入流出,散户流入流出
        # query_info_str = "Stock_ZJLX".encode('ascii')

        # pkg = bytearray.fromhex('0000 0000 0000 0000 \
        # 0000 0000 0000 0000 0000 5374 6f63 6b5f \
        # 474c 4851 0000 0000 0000 0000 0000 00   ')

 
        # 基础参数

    @override
    def deserialize(self, data):

        header_length = 27
        market, query_info_str, ext = struct.unpack("<H12s5x8s", data[0:header_length])

        # 步骤1：解析出字符串（同方法1）
        header_length = 27
        remaining_length = len(data) - header_length
        (unpacked_bytes,) = struct.unpack(f"{header_length}x{remaining_length}s", data)
        list_str = unpacked_bytes.decode("gbk")

        python_list = json.loads(list_str)

        df = pd.DataFrame()
        if len(python_list) > 0:
            # 2. 第二步：List 转 Pandas DataFrame（核心操作）
            # 定义列名（根据数据含义命名，更易理解）
            columns = [
                "板块类型",
                "状态码",
                "板块代码",
                "板块名称",
                "现价",
                "昨收",
                "指标1",
                "指标2",
                "指标3",
            ]

            # 转换为DataFrame
            df = pd.DataFrame(python_list, columns=columns)

            # 3. 第三步：数据类型转换（字符串转数值）
            # 把数值型列从字符串转为浮点数/整数
            numeric_columns = ["现价", "昨收", "指标1", "指标2", "指标3", "状态码"]
            for col in numeric_columns:
                df[col] = pd.to_numeric(
                    df[col], errors="coerce"
                )  # errors='coerce' 把无法转换的转为NaN

        return df
