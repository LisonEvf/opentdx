import struct
from opentdx._typing import override

from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.const import CATEGORY, EX_CATEGORY, MARKET,EX_MARKET, SORT_ORDER, SORT_TYPE
from opentdx.utils.help import exchange_board_code


@register_parser(0x122C, 1)
class BoardMembers(BaseParser):
    def __init__(
        self,
        board_symbol: str | CATEGORY | EX_CATEGORY = "881001",
        sort_type: int | SORT_TYPE = 0xe,
        start: int = 0,
        page_size: int = 80,
        sort_order: SORT_ORDER = SORT_ORDER.NONE,
        filter: int = 0
    ):
        if isinstance(board_symbol, str):
            board_code = exchange_board_code(board_symbol)
        else:
            board_code = board_symbol.code
            
        if isinstance(sort_type, int):
            sort_type_code = sort_type
        else:
            sort_type_code = sort_type.value
              

        self.body = struct.pack("<I9x", board_code)
        # 基础参数
        params = struct.pack("<HIBBBB", sort_type_code, start, page_size, 0, sort_order.value, 0)
        # 额外参数, 会根据传入的值不同,返回值的数量不同. 例如只传0,则只会返回 symbol 和 symbol_name
        # 位图配置：20字节，每一位代表一个字段是否存在
        
        # filter = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4)

        # 全传0, 只查板块的成员,通过 board_members 查询

        pkg = bytearray.fromhex('00 0000 0000 0000 00 00 00 00 00 00 00 00 0000 0000 00')

        self.body = self.body + params + pkg

    @override
    def deserialize(self, data):
        pos = 0
        header_length = 26

        # 执行unpack解析
        (
            field_bitmap,
            total,  # 总行数标识 (4字节int)
            row_count,  # 数据类型标识 (2字节int)
        ) = struct.unpack("<20sIH", data[:header_length])

        pos += header_length
        row_lenght = 68

        stocks = []
        for i in range(row_count):
            price_pos = 0
            row_data = data[pos : pos + row_lenght]

            header_format = "<H22s44s"
            header_size = struct.calcsize(header_format)  # = 2+6+16+24+20 = 68
            (
                market_code,
                code_bytes,
                name_bytes,
            ) = struct.unpack(header_format, row_data[:header_size])
            
            # 解码字符串
            code = code_bytes.decode("gbk", errors="ignore").replace("\x00", "")
            name = name_bytes.decode("gbk", errors="ignore").replace("\x00", "")

            # 目前MARKET 为 0 , 1, 2 
            try:
                if market_code <= 3:
                    market = MARKET(market_code)
                else:    
                    market = EX_MARKET(market_code)
            except Exception as e:
                print(f"[ERROR] 解析市场信息出错: {e}")
                market = EX_MARKET.TEMP_STOCK

            if len(row_data) < 1:
                continue

            stocks.append(
                {
                    "name": name,
                    "market": market,
                    "symbol": code,
                }
            )

            pos += row_lenght

        result = {
            "field_bitmap": field_bitmap,
            "count": row_count,
            "total": total,
            "stocks": stocks,
        }
        return result
