import struct
from typing import override

from opentdx.parser.baseParser import BaseParser, register_parser
from opentdx.utils.help import exchange_board_code
from opentdx.const import MARKET,EX_MARKET, CATEGORY , EX_CATEGORY, SORT_TYPE, SORT_ORDER
from opentdx.utils.log import log

# 定义字段位图映射 (根据 TDX 协议定义)
# 每一位代表一个4字节的字段是否存在
# 通过对比静态解析和动态解析验证得出（基于实测数据）
# 
# 注意：所有字段（包括基础字段）都受位图控制
# 位0-5: 基础字段 (pre_close, open, high, low, close, vol)
# 位6+: 扩展字段
#
# 格式: {位位置: (字段名, 格式字符串, "说明")}
# 格式字符串: '<f' = float (4字节浮点数), '<I' = uint32 (4字节无符号整数)
FIELD_BITMAP_MAP = {
    # 基础字段（位0x0-0x5）- ✅ 100% 确认
    0x0: ("pre_close", '<f', "昨收"),
    0x1: ("open", '<f', "开盘价"),
    0x2: ("high", '<f', "最高价"),
    0x3: ("low", '<f', "最低价"),
    0x4: ("close", '<f', "收盘价"),
    0x5: ("vol", '<I', "成交量"),
    0x6: ("vol_ratio", '<f', "量比"),
    0x7: ("amount", '<f', "总金额（单位：元，注意：港股单位不同）"),
    
    # 扩展字段（位0x8-0xF）
    0x8: ("inside_volume", '<I', "内盘"),  # ✅ 920627验证：CSV内盘=20999, bitmap=20999
    0x9: ("outside_volume", '<I', "外盘"),  # ✅ 920627验证：CSV外盘=24576, bitmap=24576 
    0xa: ("total_shares", '<f', "总股数(单位万)"),
    0xb: ("float_shares", '<f', "流通股(单位万)"), # 港股为H股数,也是流通股
    0xc: ("EPS", '<f', "每股收益"), 
    0xd: ("net_assets", '<f', "净资产"),  # 
    0xe: ("unkonw_action_price", '<f', "未知价"),# （国内通常为3, 9,12） 美股港股与close相等
    0xf: ("total_market_cap_ab", '<f', "AB股总市值"),  # 港股代表H市值
    
    # 位0x10-0x17
    0x10: ("pe_dynamic", '<f', "市盈率(动)"),
    0x11: ("bid", '<f', "买价"),  
    0x12: ("ask", '<f', "卖价"), 
    0x13: ("server_update_date", '<I', "服务器更新日期 YYYYMMDD"),
    0x14: ("server_update_time", '<I', "服务器更新时间 HHMMSS"),
    0x15: ("lot_size_info", '<I', "未确定"), # 港股 格式为 240000500 ,美股味 550000001  , 24/55不确定 500和1代表lot_size
    0x16: ("unknown_23", '<f', "未确定"),
    0x17: ("DIVIDEND_YIELD", '<f', "股息"), 
    
    0x18: ("bid_volume", '<I', "买量"),
    0x19: ("ask_volume", '<I', "卖量"),
    0x1a: ("last_volume", '<I', "现量"), 
    0x1b: ("turnover", '<f', "换手"),
    0x1c: ("industry", '<I', "行业"),#行业分类代码（5位数字）- 行业板块内固定，地域/概念板块内多样
    0x1d: ("industry_change_up", '<f', "行业涨跌幅"), 
    0x1e: ("some_bitmap", '<I', "位图"),
    0x1f: ("decimal_point", '<I', "数据精度"),
    
    0x20: ("buy_price_limit", '<f', "涨停价"),  
    0x21: ("sell_price_limit", '<f', "跌停价"), 
    0x22: ("unknown_34", '<I', "（港股通常为15）"),
    0x23: ("lot_size", '<I', "每手股数(港股)"),
    0x24: ("pre_ipov", '<f', "昨IPOV)"), #ETF-昨日IPOV
    0x25: ("speed_pct", '<f', "涨速"), 
    0x26: ("avg_price", '<f', "均价"),  
    0x27: ("ipov", '<f', "IPOV"),  #ETF-IPOV
    
    0x28: ("pe_ttm_vol_related", '<f', "市盈率TTM（与vol相关0.96，可能不是真正的PE TTM）"),  # ✅ 高相关
    0x29: ("ex_price_placeholder", '<f', "收盘价占位（与amount相关0.89，需验证）"),  # ⚠️ 中等相关
    0x2a: ("unknown_36_amount_related", '<f', "未知字段36（与amount相关0.90，需验证）"),  # ⚠️ 中等相关
    0x2b: ("KCB_FLAG", '<I', "科创板标志 "), #688开头30101 #300开头50101
    0x2c: ("BJ_FLAG", '<I', "北交所标志"),
    0x2d: ("unknown_field_39_vol_related", '<f', "未知字段39（与vol相关0.99，高度相关）"),  # ✅ 高相关
    0x2e: ("unknown_field_40", '<f', "未知字段40"),
    0x2f: ("unknown_field_41", '<f', "未知字段41"),
    
    0x30: ("pe_ttm", '<f', "市盈率TTM"),
    0x31: ("pe_static", '<f', "市盈率静"),
    0x32: ("unknown_field_44", '<f', "未知字段44（"),
    0x33: ("unknown_field_45", '<f', "未知字段45"),
    0x34: ("unknown_field_46", '<f', "未知字段46"),
    0x35: ("unknown_field_47", '<f', "未知字段47"),
    0x36: ("unknown_field_48", '<f', "未知字段48"),
    0x37: ("unknown_field_49", '<f', "未知字段49"),
    
    0x38: ("unknown_close_price", '<f', "美股字段"), 
    0x39: ("unknown_field_51", '<f', "未知字段51"),
    0x3a: ("unknown_field_52", '<I', "未知字段52"),
    0x3b: ("change_20d_pct", '<f', "20日涨幅%"),  # ✅ 920627验证：CSV=-12.55, bitmap=-12.55
    0x3c: ("ytd_pct", '<f', "年初至今%"),  # ✅ 920627验证：CSV=-3.8, bitmap=-3.8
    0x3d: ("unknown_field_55", '<f', "未知字段55"),
    0x3e: ("unknown_field_56", '<f', "未知字段56"),
    0x3f: ("unknown_field_63", '<I', "未知字段63"),
    
    0x40: ("mtd_pct", '<f', "月初至今%"),  # ✅ 920627验证：CSV=6.11, bitmap=6.11
    0x41: ("change_1y_pct", '<f', "一年涨幅%"),  # ✅ 920627验证：CSV=-17.29, bitmap=-17.29
    0x42: ("prev_change_pct", '<f', "昨涨幅%"),  # ✅ 920627验证：CSV=-1.14, bitmap=-1.14
    0x43: ("change_3d_pct", '<f', "3日涨幅%"),  # ✅ 920627验证：CSV=12.1, bitmap=12.10 (注：CSV振幅%=12.19是不同的字段)
    0x44: ("change_60d_pct", '<f', "60日涨幅%"),  # ✅ 920627验证：CSV=-15.37, bitmap=-15.37
    0x45: ("change_5d_pct", '<f', "5日涨幅%"),  # ✅ 920627验证：CSV=6.44, bitmap=6.44
    0x46: ("change_10d_pct", '<f', "10日涨幅%"),  # ✅ 920627验证：CSV=1.64, bitmap=1.64
    0x47: ("unknown_71", '<f', "未知字段71（待分析）"),
    
    0x48: ("low_copy", '<f', "最低价(备份)"),  
    0x49: ("low_copy2", '<f', "最低价(备份)"), 
    0x4a: ("ah_code", '<I', "对应A/H股code,不足位数前面补0"), # 600876 对应 1108 /  06881 对应 601881
    0x4b: ("unknown_code", '<I', "少部分有数据,6位数字 123247"),
    0x4c: ("unknown_field_76", '<f', "未知字段76（全部为0，未启用）"),
    0x4d: ("unknown_field_77", '<f', "未知字段77（全部为0，未启用）"),
    0x4e: ("unknown_field_78", '<f', "未知字段78（全部为0，未启用）"),
    0x4f: ("unknown_field_79", '<f', "未知字段79（全部为0，未启用）"),
    
    # 新发现的扩展字段（位0x50-0x57）- 通过 000100 数据发现
    0x50: ("unknown_field_80", '<f', "未知字段80（待分析）"),
    0x51: ("unknown_field_81", '<f', "未知字段81（待分析）"),
    0x52: ("unknown_field_82", '<f', "未知字段82（待分析）"),
    0x53: ("unknown_field_83", '<f', "未知字段83（待分析）"),
    0x54: ("unknown_field_84", '<f', "未知字段84（待分析）"),
    0x55: ("unknown_field_85", '<f', "未知字段85（待分析）"),
    0x56: ("unknown_field_86", '<f', "未知字段86（待分析）"),
    0x57: ("open_amount", '<f', "开盘金额（元）"),  # ✅ 000100验证：CSV=1322.18万, bitmap=13221810元

    0x59: ("active", '<I', "活跃度"), 
    0x5c: ("CONSECUTIVE_UP_DAYS", '<i', "连涨天"), # 正数代表连涨，负数代表连跌 
    
    0x6a: ("SHORT_ACMOUNT", '<f', "2分钟金额"), 

}


def get_active_fields_from_bitmap(bitmap_bytes: bytes) -> list[int]:
    """
    从位图中获取所有激活的位位置
    
    Args:
        bitmap_bytes: 20字节的位图数据
        
    Returns:
        激活的位位置列表，如 [0, 1, 2, 5, 10]
    """
    bitmap_int = int.from_bytes(bitmap_bytes, 'little')
    active_bits = []
    
    bit_pos = 0
    while bitmap_int:
        if bitmap_int & 1:
            active_bits.append(bit_pos)
        bitmap_int >>= 1
        bit_pos += 1
    
    return active_bits


def parse_row_header(row_data: bytes) -> dict:
    """
    解析行数据的头部信息（前68字节）
    
    Args:
        row_data: 原始行数据
        
    Returns:
        包含 name, market, symbol 的字典
    """
    # 格式: <H6s16s24s20s
    # H: market (2字节)
    # 6s: code (6字节)
    # 24s: name_raw (24字节)
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
        
    return {
        "name": name,
        "market": market,
        "symbol": code
    }


def parse_dynamic_fields(row_data: bytes, field_bitmap: bytes) -> dict:
    """
    根据位图动态解析字段数据（从第68字节开始）
    
    Args:
        row_data: 原始行数据
        field_bitmap: 字段位图（20字节）
        
    Returns:
        包含所有动态字段的字典
    """
    header_size = 68  # 固定头部大小
    data_start = header_size
    data_dict = {}
    
    # 动态解析：根据位图确定有哪些字段
    active_bits = get_active_fields_from_bitmap(field_bitmap)
    
    pos = data_start
    
    # 所有字段都受位图控制，按位图顺序解析
    for bit_pos in active_bits:
        field_info = FIELD_BITMAP_MAP.get(bit_pos)
        
        if field_info is None:
            field_name = f"unknown_field_{bit_pos}"
            field_format = '<f'  # 默认uint32
            # print(f"[INFO] 发现未知字段 位{bit_pos}，暂按uint32解析")
        else:
            field_name, field_format, _ = field_info
        
        if pos + 4 <= len(row_data):
            raw_bytes = row_data[pos:pos+4]
            
            # 直接使用定义的格式字符串解析
            value = struct.unpack(field_format, raw_bytes)[0]
            
            # 如果是 unknown_field 且按 float 解析后数值较小，尝试按 uint32 重新解析
            if field_name.startswith("unknown_field") and field_format == '<f':
                # 需求变更：不是要小于某个值，而是它的数值有比较多指数（即极小浮点数，通常是整数误解析为float的结果）
                # 判断条件：绝对值极小（非正规数范围）或者科学计数法指数部分很小
                # 检查是否为非零且绝对值极小（例如 < 1e-5），这通常意味着它是被误解析的整数
                # 或者检查其科学计数法表示
                if value != 0.0 and abs(value) < 1e-6:
                    try:
                        int_value = struct.unpack('<i', raw_bytes)[0]
                        print(f"[DEBUG] 发现未知字段 {field_name} 位{bit_pos} : {value} (疑似误解析)， 重新解析为整数: {int_value}")
                        value = int_value
                    except Exception:
                        pass
                # 也可以保留一部分之前对于较小整数的判断，如果业务上认为某些正常浮点数不会落在 1e-5 到 1000 之间且为未知字段
                # 但根据需求描述“比较多指数”，主要针对的是极小值（如 1.4e-45 这种）
                # 如果还需要覆盖之前的小整数情况（比如 100 被解析成 1.4e-43 这种极端情况其实也被上面覆盖了）
                # 如果指的是像 1.23456789 这种有很多小数位的，那通常不应该重解析。
                # “比较多指数”通常指科学计数法 e-xx 很大。
                
            data_dict[field_name] = value
            pos += 4
        else:
            data_dict[field_name] = None
            break
    
    return data_dict


def parse_row_data(row_data: bytes, field_bitmap: bytes = None) -> dict:
    """
    解析单条股票数据（组合函数）
    
    Args:
        row_data: 原始行数据
        field_bitmap: 字段位图（20字节），如果提供则动态解析字段
        
    Returns:
        包含 base_info 和 data_dict 的完整字典
    """
    # ========== 1. 解析头部 (68字节) ==========
    base_info = parse_row_header(row_data)
    
    # ========== 2. 解析动态字段 ==========
    if field_bitmap:
        data_dict = parse_dynamic_fields(row_data, field_bitmap)
    else:
        data_dict = {}
    
    # ========== 3. 合并返回 ==========
    return {**base_info, **data_dict}


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
            # filter 的每一位对应 FIELD_BITMAP_MAP 中的一个位位置
            pkg = self._generate_bitmap_from_filter(filter)
        
        self.body = self.body + params + pkg
        # print(len(self.body), self.body)

    def _generate_bitmap_from_filter(self, filter: int) -> bytearray:
        """
        根据 filter 参数生成20字节的位图
        
        Args:
            filter: 整数，每一位代表是否启用对应的字段
                   例如: filter = (1 << 0) | (1 << 4) | (1 << 5) 
                   表示启用 pre_close(位0), close(位4), volume(位5)
        
        Returns:
            20字节的位图数据
        """
        # 初始化20字节的全0位图
        bitmap_bytes = bytearray(20)
        
        # 将 filter 转换为位图
        # filter 的第 n 位对应 FIELD_BITMAP_MAP 中的位位置 n
        for bit_pos in range(160):  # 20字节 = 160位
            if filter & (1 << bit_pos):
                # 计算该位在哪个字节中
                byte_index = bit_pos // 8
                bit_index = bit_pos % 8
                # 设置对应的位
                bitmap_bytes[byte_index] |= (1 << bit_index)
        
        return bitmap_bytes


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

        # print(magic_num.hex())

        # print(f"16进制: {header.hex()} totol: {total} count:{row_count}")
        pos += header_length
        
        # 基础信息,name market code 
        base_row_lenght = 68
        # 字段,根据field_bitmap 动态解析
        count_ones = int.from_bytes(field_bitmap, 'little').bit_count()
        # 计算每行总长度
        row_lenght = base_row_lenght + 4 * count_ones 
        
        # print(f"16进制!!!!:{len(data)}   {data.hex()} ")
        # print(f"位图激活字段数: {count_ones}")
        # print(f"每行长度: {row_lenght} 字节")
        
        # 检测新字段：对比请求位图和已知字段映射
        request_bitmap_int = int.from_bytes(field_bitmap, 'little')
        known_max_bit = max(FIELD_BITMAP_MAP.keys()) if FIELD_BITMAP_MAP else -1
        new_fields_detected = []
        
        for bit_pos in range(known_max_bit + 1, 160):  # 20字节=160位
            if request_bitmap_int & (1 << bit_pos):
                new_fields_detected.append(bit_pos)
        
        if new_fields_detected:
            log.debug(f"\n[WARNING] 检测到 {len(new_fields_detected)} 个新字段（超出已知字段范围）:")
            for bit_pos in new_fields_detected:
                log.debug(f"  位{bit_pos}: 未知字段，需要进一步分析")
        
        stocks = []
        
        for i in range(row_count):
            row_data = data[pos + i * row_lenght : pos + (i + 1) * row_lenght]
            # print(f"16进制 >>> :{len(row_data)}   {row_data.hex()} ")
            # 传入位图，进行动态解析
            stock_dict = parse_row_data(row_data, field_bitmap=field_bitmap)
            
            # 特殊字段处理：格式化 ah_code
            if stock_dict.get("ah_code"):
                market = stock_dict.get("market")
                ah_code_raw = stock_dict.get("ah_code")
                
                # 判断当前股票的市场类型
                if market in [MARKET.SZ, MARKET.SH, MARKET.BJ]:
                    # 国内市场（A股）：ah_code 对应的是港股，需要格式化为5位，不足前面补0
                    stock_dict["ah_code"] = str(ah_code_raw).zfill(5)
                else:
                    # 港股市场：ah_code 对应的是A股，需要格式化为6位，不足前面补0
                    stock_dict["ah_code"] = str(ah_code_raw).zfill(6)
            
            
            stocks.append(stock_dict)
            
        result = {
            "field_bitmap": field_bitmap,
            "count": row_count,
            "total": total,
            "stocks": stocks,
        }
        return result