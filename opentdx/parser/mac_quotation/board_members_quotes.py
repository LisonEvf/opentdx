import struct
from typing import override

from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import exchange_board_code
from opentdx.const import MARKET,EX_MARKET, CATEGORY , EX_CATEGORY, SORT_TYPE, SORT_ORDER
from opentdx.utils.log import log
from opentdx.utils.bitmap import FIELD_BITMAP_MAP, get_active_fields_from_bitmap


@register_parser(0x122C, 1)
class BoardMembersQuotes(BaseParser):
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

        # 无法全传0, 只查板块的成员,通过 board_members 查询
        if filter == 0:
            # 默认位图：常用字段组合
            pkg = bytearray.fromhex('ff fce1 cc3f 0803 01 00 00 00 00 00 00 00 0000 0000 00')
        elif filter == -1:
            # 全字段模式（测试用）
            pkg = bytearray.fromhex('ff ffff ffff ffff ff 00 00 00 00 00 00 00 0000 0000 00')
        elif filter == -99:
            # 全字段模式（验证新字段使用）
            pkg = bytearray.fromhex("ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff ff")
        else:
            # 根据 filter 整数值生成位图
            pkg = bytearray(filter.to_bytes(20, 'little'))
                    
        self.body = self.body + params + pkg
        # print(len(self.body), self.body)

    @override
    def deserialize(self, data):
        pos = 0
        header_length = 26

        # 解析头部：20字节位图 + 4字节总数 + 2字节本页数量
        field_bitmap, total, row_count = struct.unpack("<20sIH", data[:header_length])
        pos += header_length

        base_row_length = 68  # 固定头部68字节

        # ========== 预编译字段解析器列表 ==========
        active_bits = get_active_fields_from_bitmap(field_bitmap)
        new_fields_detected = [bit for bit in active_bits if bit not in FIELD_BITMAP_MAP]

        if new_fields_detected:
            log.debug(f"\n[WARNING] 检测到 {len(new_fields_detected)} 个请求的字段位不在已知映射中:")
            for bit_pos in new_fields_detected:
                log.debug(f"  位{bit_pos}: 未知字段，需要进一步分析")
        
        field_parsers = []  # 每个元素: (field_name, fmt, is_unknown, offset)
        
        data_offset = base_row_length
        for bit_pos in active_bits:
            info = FIELD_BITMAP_MAP.get(bit_pos)
            if info is None:
                field_name = f"unknown_field_{bit_pos}"
                fmt = '<f'
                is_unknown = True
            else:
                field_name, fmt, _ = info
                is_unknown = False
            field_parsers.append((field_name, fmt, is_unknown, data_offset))
            data_offset += 4

        row_length = base_row_length + 4 * len(active_bits)

        # ========== 逐行解析 ==========
        stocks = []
        for i in range(row_count):
            row_data = data[pos + i * row_length : pos + (i + 1) * row_length]

            # 1. 解析固定头部（68字节）
            base_info = parse_row_header(row_data)  # 保持不变

            # 2. 解析动态字段（使用预编译的 field_parsers）
            dynamic_info = {}
            for field_name, fmt, is_unknown, offset in field_parsers:
                if offset + 4 > len(row_data):
                    dynamic_info[field_name] = None
                    continue
                # 使用 unpack_from 避免切片
                value = struct.unpack_from(fmt, row_data, offset)[0]
                # 对未知字段的整数误解析修复
                if is_unknown and fmt == '<f' and value != 0.0 and abs(value) < 1e-6:
                    try:
                        value = struct.unpack_from('<i', row_data, offset)[0]
                    except Exception:
                        pass
                dynamic_info[field_name] = value

            stocks.append({**base_info, **dynamic_info})

        return {
            "field_bitmap": field_bitmap,
            "count": row_count,
            "total": total,
            "stocks": stocks,
        }


def parse_row_header(row_data: bytes) -> dict:
    """
    解析行数据的头部信息（前68字节）
    """
    header_format = "<H22s44s"
    market_code, code_bytes, name_bytes = struct.unpack(header_format, row_data[:68])
    code = code_bytes.decode("gbk", errors="ignore").replace("\x00", "")
    name = name_bytes.decode("gbk", errors="ignore").replace("\x00", "")
    try:
        if market_code <= 3:
            market = MARKET(market_code)
        else:
            market = EX_MARKET(market_code)
    except Exception as e:
        log.error(f"解析市场信息出错: {e}")
        market = EX_MARKET.TEMP_STOCK
    return {"name": name, "market": market, "symbol": code}
