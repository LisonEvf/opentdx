import json
import struct
from opentdx._typing import override

import pandas as pd
from opentdx.const import MARKET

from opentdx.parser.baseParser import BaseParser, register_parser


@register_parser(0x1218, 2)
class SymbolZJLX(BaseParser):

    """
    资金流向解析器
    解析 Stock_ZJLX 查询返回的资金流向数据
    包含主力流入流出、散户流入流出等信息
    """
    
    def __init__(self, symbol: str, market: MARKET):
        # 使用 Stock_ZJLX 作为查询标识
        query_info_str = "Stock_ZJLX".encode("ascii")
        # 构建请求体：市场代码(2字节) + 股票代码(8字节GBK) + 填充(16字节) + 查询类型(21字节ASCII)
        self.body = struct.pack("<H8s16x21s", market.value, symbol.encode("gbk"), query_info_str)

    @override
    def deserialize(self, data):
        """
        解析资金流向数据
        
        Args:
            data: 二进制响应数据，格式如：
                  bytearray(b'\x00\x00Stock_ZJLX\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x9b\x00\x00\x00[["241204384.00","433446784.00","556449984.00","364207616.00"],["1327623680.00","1792538112.00","-186592736.00","47775920.00","91628976.00","47187888.00"]]')
            
        Returns:
            DataFrame: 包含资金流向信息的DataFrame，包含今日和5日资金流向数据
        """
        header_length = 27
        market, query_info_str, ext = struct.unpack("<H12s5x8s", data[0:header_length])

        # 解析剩余数据为GBK编码的JSON字符串
        remaining_length = len(data) - header_length
        (unpacked_bytes,) = struct.unpack(f"{header_length}x{remaining_length}s", data)
        list_str = unpacked_bytes.decode("gbk")
        
        # 解析JSON字符串为Python对象
        # 数据结构: [["今日资金流向..."], ["5日资金流向..."]]
        python_list = json.loads(list_str)
        
        df = pd.DataFrame()
        if len(python_list) > 0 and len(python_list) >= 2:

            # python_list[0]: 今日资金流向（4个字段）
            # python_list[1]: 5日资金流向（6个字段）
            today_data = python_list[0]    # ["主力流入", "主力流出", "散户流入", "散户流出"]
            five_days_data = python_list[1]  # 根据实际数据修正顺序
            
            # 定义列名（根据截图和实际数据对比修正）
            columns = [
                # 今日资金流向
                "今日主力流入",
                "今日主力流出",
                "今日散户流入",
                "今日散户流出",
                # 5日资金流向（修正后的顺序）
                "5日主买",          # 索引0: 276,671.8万
                "5日主卖",          # 索引1: 348,667万
                "5日超大单净额",    # 索引2: -17,784.2万
                "5日大单净额",      # 索引3: -6,786.7万
                "5日中单净额",      # 索引4: 8,398.3万
                "5日小单净额",      # 索引5: 16,172.5万
            ]
            
            # 合并今日和5日数据
            merged_data = today_data + five_days_data
            
            # 创建DataFrame
            df = pd.DataFrame([merged_data], columns=columns)
            
            # 数据类型转换：将所有列从字符串转为浮点数
            for col in columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
            
            # 计算一些衍生指标
            if "今日主力流入" in df.columns and "今日主力流出" in df.columns:
                df["今日主力净流入"] = df["今日主力流入"] - df["今日主力流出"]
            
            if "今日散户流入" in df.columns and "今日散户流出" in df.columns:
                df["今日散户净流入"] = df["今日散户流入"] - df["今日散户流出"]
            
            if "5日主买" in df.columns and "5日主卖" in df.columns:
                df["5日主力净流入"] = df["5日主买"] - df["5日主卖"]
        
        return df
