from datetime import time
import struct
from opentdx._typing import override


from opentdx.const import  MARKET
from opentdx.parser.quotation import Unusual
from opentdx.parser.baseParser import register_parser

@register_parser(0x1237)
class MarketMonitor(Unusual): # 主力监控
    """
    主力监控
    和Unusual的区别在于，不需要Login() 也能访问
    """
    def __init__(self, market: MARKET, start: int, count: int = 600):
        # pkg = bytearray.fromhex('0200 8301 0000 1e00 0000 0100 0000 0000 0000 0000 0000')
        # self.body = pkg
        self.body = struct.pack('<H H 2x H 2x H 10x', market.value, start,  count, 1)
        
    @override
    def deserialize(self, data):
        count,  = struct.unpack('<H', data[:2])
        results = []
        for i in range(count):
            market, code, _, unusual_type, _, index, z = struct.unpack('<H6sBBBHH', data[32 * i + 2: 32 * i + 17])
            desc, value = self.unpack_by_type(unusual_type, data[32 * i + 17: 32 * i + 30])
            hour, minute_sec = struct.unpack('<BH', data[32 * i + 31: 32 * i + 34])

            results.append({
                'index': index,
                'market': MARKET(market),
                'code': code.decode('gbk').replace('\x00', ''),
                'time': time(hour, minute_sec // 100, minute_sec % 100),
                'desc': desc,
                'value': value,
                'unusual_type': unusual_type,
            })
            
        # ===================== 关键：动态计算文本位置，不写死 =====================
        # 头部 2 字节 + 每条 32 字节 = 二进制数据总长度
        binary_length = 2 + count * 32
        # 剩下的全部是文本
        text_bytes = data[binary_length:]
        # ========================================================================

        # 解析文本（GBK 中文）
        text_str = text_bytes.decode('gbk', errors='ignore')
        text_list = text_str.strip(',').split(',')

        # 把名称匹配到对应股票
        for i in range(len(results)):
            if i < len(text_list):
                results[i]['name'] = text_list[i]
                
        return results