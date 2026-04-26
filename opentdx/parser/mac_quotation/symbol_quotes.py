import struct
from typing import List, Tuple

from opentdx.parser.baseParser import register_parser
from opentdx.parser.mac_quotation import BoardMembersQuotes
from opentdx.const import MARKET, EX_MARKET
from opentdx.utils.bitmap import SYMBOL_QUOTES_DEFAULT_HEX, QUOTES_DEBUG_HEX, QUOTES_DEBUG_ALL_HEX

# 正常应该是 BoardMembersQuotes extent SymbolQuotes. 但BoardMembersQuotes先解析了
@register_parser(0x122B)
class SymbolQuotes(BoardMembersQuotes):
    """
    股票行情查询解析器 (命令字: 0x122B)
    
    ⚠️  **重要说明**: 
    - 支持批量查询多只股票，服务器会返回所有股票的完整行情数据
    - **支持自定义bitmap**：通过filter参数控制返回哪些字段，减少数据传输
    
    请求包结构:
    - 命令字: 0x122B (由 serialize 自动添加)
    - 字段位图: 20字节 (控制返回字段，与FIELD_BITMAP_MAP对应)
    - 股票数量: 2字节 (uint16 LE) ← **入参count**
    - 股票列表: 每个股票 = market(2字节) + code(22字节GBK编码，不足补0)
    
    响应数据结构:
    - 字段位图: 20字节 ([0-19]) - 服务器回显的位图配置
    - 查询总量 total: 2字节 ([20-21], uint16 LE) ← **入参回显** 
    - 未知字段: 2字节 ([22-23], 通常为0)
    - 返回总量: 2字节 ([24]: count低字节副本, [25]: 填充0)
    - 股票数据列表: 每条记录180字节
      * market: 2字节 (0=SZ, 1=SH, 2=BJ, >=3为EX_MARKET)
      * code: 6字节 (GBK编码)
      * 行情数据: 172字节（根据bitmap动态包含不同字段）
        - 偏移60-79: 价格字段 (5个float): pre_close, open, high, low, close
        - 偏移88-91: amount (成交金额，元)
        - 偏移92-95: volume (成交量，手)
        - 更多字段参考 FIELD_BITMAP_MAP
    
    
    返回值结构 (dict):
    ```python
    {
        "field_bitmap": "ffbc81cc...",  # 字段位图（hex字符串）
        "count": 2,                      # 请求的股票数量
        "stocks": [                      # 股票行情数据列表
            {
                "market": MARKET.SZ,
                "code": "300385",
                "pre_close": 15.0,
                "open": 14.6,
                "high": 14.8,
                "low": 14.03,
                "close": 14.21,
                "change": -0.79,
                "change_pct": -5.27,
                "volume": 33314,
                "amount": 260138928.0,
                ...
            },
            ...
        ]
    }
    ```
    
    示例:
    ```python
    from opentdx.parser.mac_quotation import SymbolQuotes
    from opentdx.const import MARKET, EX_MARKET
    from opentdx.utils.bitmap import fields_to_filter
    
    # 方式1: 默认bitmap（常用字段）
    parser = SymbolQuotes(code_list=[
        (MARKET.SZ, "300385"),
        (MARKET.SH, "600519"),
    ])
    
    # 方式2: 自定义字段组合
    custom_filter = fields_to_filter('basic+volume')  # 基础行情+成交量
    parser = SymbolQuotes(code_list=[(MARKET.SZ, "300385")], filter=custom_filter)
    
    # 方式3: 全字段模式（测试用）
    parser = SymbolQuotes(code_list=[(MARKET.SZ, "300385")], filter=-1)
    
    # 获取结果
    result = client.call(parser)
    print(f"位图: {result['field_bitmap']}")
    print(f"查询数量: {result['total']}")
    print(f"数量: {result['count']}")
    for stock in result['stocks']:
        print(f"{stock['code']}: {stock['close']}")
    ```
    """
    
    def __init__(
        self,
        symbol_list: List[Tuple[MARKET | EX_MARKET, str]],
        filter: int = 0
    ):
        """
        初始化多股票行情查询
        
        Args:
            code_list: 股票/标识列表，每个元素为 (市场, 标识符) 的元组
                    例如: 
                    - [(EX_MARKET.US_STOCK, "BOIL"), (EX_MARKET.HK_MAIN_BOARD, "00700")]
                    - 标识符可以是股票代码或特殊标识如"BOIL"
            filter: 字段过滤器（位图），控制返回哪些字段
                   - 0: 使用默认bitmap（常用字段组合）
                   - -1: 全字段模式（测试用）
                   - 其他值: 自定义位图，可通过 fields_to_filter() 生成
                     例如: filter = fields_to_filter('basic+volume')
        """
        

        # 构建固定参数部分 (20字节) - 支持自定义bitmap
        # SymbolQuotes 默认bitmap: ffbc81cc3f080300000000000000000000000000
        # BoardMembersQuotes 默认bitmap: fffce1cc3f080301000000000000000000000000

        if filter == 0:
            # 默认位图：常用字段组合
            pkg = bytearray.fromhex(SYMBOL_QUOTES_DEFAULT_HEX)
        elif filter == -1:
            # 全字段模式（测试用）
            pkg = bytearray.fromhex(QUOTES_DEBUG_HEX)
        elif filter == -99:
            # 全字段模式（验证新字段使用）
            pkg = bytearray.fromhex(QUOTES_DEBUG_ALL_HEX)
        else:
            # 根据 filter 整数值生成位图
            pkg = bytearray(filter.to_bytes(20, 'little'))

        self.body = pkg + struct.pack('H', len(symbol_list))
        
        for market, code in symbol_list:
            self.body.extend(struct.pack('<H22s', market.value, code.encode('gbk')))


