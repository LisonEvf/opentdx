from datetime import time
import struct
from opentdx._typing import override


from opentdx.const import  MARKET
from opentdx.parser.baseParser import BaseParser,register_parser

@register_parser(0x1237)
class MarketMonitor(BaseParser): # 主力监控
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
            unpacked_data = self.unpack_by_type(unusual_type, data[32 * i + 17: 32 * i + 30])
            hour, minute_sec = struct.unpack('<BH', data[32 * i + 31: 32 * i + 34])

            results.append({
                'index': index,
                'market': MARKET(market),
                'code': code.decode('gbk').replace('\x00', ''),
                'time': time(hour, minute_sec // 100, minute_sec % 100),
                'desc': unpacked_data['desc'],
                'value': unpacked_data['value'],
                'unusual_type': unusual_type,
                'v1': unpacked_data['v1'],
                'v2': unpacked_data['v2'],
                'v3': unpacked_data['v3'],
                'v4': unpacked_data['v4'],
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
    
    def unpack_by_type(self, type: int, data: bytearray):
        v1, v2, v3, v4 = struct.unpack('<B3f', data)
        desc = ""
        val = ""
        if type == 0x03: 
            desc = f"主力{'买入' if v1 == 0x00 else '卖出'}" 
            val = f"{v2:.2f}/{v3:.2f}"
        elif type == 0x04: 
            desc = "加速拉升"
            val = f"{v2*100:.2f}%"
        elif type == 0x05: 
            desc = "加速下跌"
        elif type == 0x06:
            desc = "低位反弹"
            val = f"{v2*100:.2f}%"
        elif type == 0x07: 
            desc = "高位回落"
            val = f"{v2*100:.2f}%"
        elif type == 0x08: 
            desc = "撑杆跳高"
            val = f"{v2*100:.2f}%"
        elif type == 0x09: 
            desc = "平台跳水"
            val = f"{v2*100:.2f}%"
        elif type == 0x0a: 
            desc = f"单笔冲{'跌' if v2 < 0 else '涨'}"
            val = f"{v2*100:.2f}%"
        elif type == 0x0b:
            desc = f"区间放量{'平' if v3 == 0 else '跌' if v3 < 0 else '涨'}"
            val = f"{v2:.1f}倍{'' if v3 == 0 else f'{v3*100:.2f}%'}"
        elif type == 0x0c: 
            desc = "区间缩量"
        elif type == 0x10: 
            desc = "大单托盘"
            val = f"{v4:.2f}/{v3:.2f}"
        elif type == 0x11: 
            desc = "大单压盘"
            val = f"{v2:.2f}/{v3:.2f}"
        elif type == 0x12: 
            desc = "大单锁盘"
        elif type == 0x13: 
            desc = "竞价试买"
            val = f"{v2:.2f}/{v3:.2f}"
        elif type == 0x14: 
            sub_type, v2, v3 = struct.unpack('<Bff', data[1:10])
            direction = "涨" if v1 == 0x00 else "跌"
            if sub_type == 0x01:
                desc = f"逼近{direction}停"
            elif sub_type == 0x02:
                desc = f"封{direction}停板"
            elif sub_type == 0x04:
                desc = f"封{direction}大减"
            elif sub_type == 0x05:
                desc = f"打开{direction}停"
            val = f"{v2:.2f}/{v3:.2f}"
        elif type == 0x15:
            if v1 == 0x00:
                desc = "尾盘??"
            elif v1 == 0x01:
                desc = "尾盘对倒"
            elif v1 == 0x02:
                desc = "尾盘拉升"
            else:
                desc = "尾盘打压"
            val = f"{v2*100:.2f}%/{v3:.2f}"
        elif type == 0x16:
            desc = f"盘中{'弱' if v2 < 0x00 else '强'}势"
            val = f"{v2*100:.2f}%"
        elif type == 0x1d:
            desc = "急速拉升"
            val = f"{v2*100:.2f}%"
        elif type == 0x1e:
            desc = "急速下跌" 
            val = f"{v2*100:.2f}%"
        
        return {
            'desc': desc,
            'value': val,
            'v1': v1,
            'v2': v2,
            'v3': v3,
            'v4': v4,
        }
