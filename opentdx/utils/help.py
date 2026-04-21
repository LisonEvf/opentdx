# coding=utf-8

from datetime import date, datetime
import struct

from opentdx.const import EX_MARKET, MARKET
from opentdx.enums import IndustryCode
from opentdx.utils.log import log

def query_market(code) -> MARKET | None:
    """
    0 - 深圳， 1 - 上海
    """
    if code.startswith(("50", "51", "60", "68", "90", "110", "113", "132", "204")):
        return MARKET.SH
    elif code.startswith(("00", "12", "13", "15", "16", "18", "20", "30", "39", "115", "1318")):
        return MARKET.SZ
    elif code.startswith(("5", "6", "7", "9")):
        return MARKET.SH
    elif code.startswith(("4", "8")):
        return MARKET.BJ
    else:
        log.error("unknown market code: {}".format(code))
        return None


# 根据可视化的板块id获取到系统需要的真实板块code
def exchange_board_code(board_symbol):
    if board_symbol.startswith("US"):
        # US0401 => 30401
        board_code = 30000 + int(board_symbol.replace("US", ""))
    elif board_symbol.startswith("HK"):
        # HK0283 => 20283
        board_code = 20000 + int(board_symbol.replace("HK", ""))
    elif board_symbol.startswith("000"):
        # 000686 => 31686
        board_code = 31000 + int(board_symbol)
    elif board_symbol.startswith("399") and len(board_symbol) == 6:
        # 399372 => 30399
        board_code = int(board_symbol) - 399000 + 30000
    elif board_symbol.startswith("899") and len(board_symbol) == 6:
        # 899050 => 32050
        board_code = int(board_symbol) - 899000 + 32000
    elif board_symbol.startswith("88") and len(board_symbol) == 6:
        # 880686 => 20686
        board_code = int(board_symbol) - 880000 + 20000
    else:
        # 由于数字过大,可能查询到其他的板块
        board_code = int(board_symbol)

    return board_code

def industry_to_board_symbol(industry_value:str) -> str:
    # 从83005提取出3005，然后拼接为X3005
    industry_str = str(industry_value)
    suffix = industry_str[-4:]  # 获取后3位，如"005"
    key = f"X{suffix}"  # 拼接为"X3005"
    
    try:
        return str(IndustryCode[key].value)
    except KeyError:
        return ""  # 如果找不到对应的枚举项
    
def ah_code_to_symbol(ah_code:str, market:str) -> str:
    """
        将ah_code转换为symbol, 补齐0
                        
        Example:
            >>> ah_code_filter = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << 0x4a)
                rs = client.get_board_members_quotes(board_symbol="881394",count=100, filter=ah_code_filter)
                df = pd.DataFrame(rs)
                df['ah_symbol'] = df.apply(lambda row: ah_code_to_symbol(row['ah_code'], row['market']), axis=1)
    """
    
    if ah_code == 0:
        return ""
    
    if market in [MARKET.SZ, MARKET.SH, MARKET.BJ]:
        # 国内市场（A股）：ah_code 对应的是港股，需要格式化为5位，不足前面补0
        ah_symbol = str(ah_code).zfill(5)
    else:
        # 港股市场：ah_code 对应的是A股，需要格式化为6位，不足前面补0
        ah_symbol = str(ah_code).zfill(6)
    
    return ah_symbol
    
def lot_size_to_symbol(lotsize:str) -> str:
    """
        将lotsize转换为symbol, 补齐前缀
                        
    """
    if lotsize == 0:
        return ""
    
    dq_symbol = 880200 + int(lotsize)
    
    return str(dq_symbol)

#### XXX: 分析了一下，貌似是类似utf-8的编码方式保存有符号数字
def get_price(data, pos):
    pos_byte = 6
    bdata = data[pos]
    int_data = bdata & 0x3f
    if bdata & 0x40:
        sign = True
    else:
        sign = False

    if bdata & 0x80:
        while True:
            pos += 1
            bdata = data[pos]
            int_data += (bdata & 0x7f) << pos_byte
            pos_byte += 7

            if bdata & 0x80:
                pass
            else:
                break

    pos += 1

    if sign:
        int_data = -int_data

    return int_data, pos

def to_datetime(num, with_time=False) -> datetime:
    year = 0
    month = 0
    day = 0
    hour = 15
    minute = 0
    if with_time:
        zip_data = num & 0xFFFF
        year = (zip_data >> 11) + 2004
        month = int((zip_data & 0x7FF) / 100)
        day = (zip_data & 0x7FF) % 100

        minutes = num >> 16
        hour = int(minutes / 60)
        minute = minutes % 60
    else:
        year = num // 10000
        month = num % 10000 // 100
        day = num % 100
    if year > datetime.now().year:
        raise ValueError("year is too large")

    return datetime(year, month, day, hour, minute)

def format_time(time_stamp):
    if time_stamp == 0 or time_stamp == 100:
        return '00:00:00.000'
    else:
        time_stamp = str(time_stamp)
    """
    format time from reversed_bytes0
    by using method from https://github.com/rainx/pytdx/issues/187
    """
    time_str = time_stamp[:-6] + ':'
    if int(time_stamp[-6:-4]) < 60:
        time_str += '%s:' % time_stamp[-6:-4]
        time_str += '%06.3f' % (
            int(time_stamp[-4:]) * 60 / 10000.0
        )
    else:
        time_str += '%02d:' % (
            int(time_stamp[-6:]) * 60 / 1000000
        )
        time_str += '%06.3f' % (
            (int(time_stamp[-6:]) * 60 % 1000000) * 60 / 1000000.0
        )
    return time_str

def unpack_futures(data, code_len: int = 23):
    if len(data) == 292 + code_len:
        raise Exception('')
    
    market, code = struct.unpack(f'<B{code_len}s', data[:1 + code_len])
    active, pre_close, open, high, low, close, open_position, add_position, vol, curr_vol, amount, in_vol, out_vol, u14, hold_position = struct.unpack(f'<I5f4If4I', data[1 + code_len: 61 + code_len])
    handicap_list = struct.unpack('<5f5I5f5I', data[61 + code_len: 141 + code_len])
    handicap = {
        'bids': [{'price': handicap_list[i], 'vol': handicap_list[i + 5]} for i in range(5)],
        'asks': [{'price': handicap_list[i], 'vol': handicap_list[i + 5]} for i in range(10, 15)]
    }
    u1, settlement, u2, avg, pre_settlement, u3, u4, u5, u6, pre_close  = struct.unpack('<HfIffIIIIf', data[141 + code_len: 179 + code_len])
    s1, pre_vol, u7, s2, u8, day3_raise, s3, settlement2, date_raw, u9, raise_speed, u10, s4, u11, u12 = struct.unpack('<12sff12sff25sfIIff24sHB', data[179 + code_len: 291 + code_len])

    # 当没有 date_raw 数据时,会报错
    # goods.Futures_QuotesList(ExtMarketCategory.港股.value, 1895, 2)  02632没有date_raw数据
    if date_raw // 10000 == 0:
        date_obj = date(1900, 1, 1)
    else:
        date_obj = date(date_raw // 10000, date_raw % 10000 // 100, date_raw % 100)

    return {
            'market': EX_MARKET(market), 
            'code': code.decode('gbk').replace('\x00', ''), 
            'active': active, 
            'pre_close': pre_close, 
            'open': open, 
            'high': high, 
            'low': low, 
            'close': close, 
            'open_position': open_position, 
            'add_position': add_position, 
            'vol': vol, 
            'curr_vol': curr_vol, 
            'amount': amount, 
            'in_vol': in_vol, 
            'out_vol': out_vol, 
            'u14': u14, 
            'hold_position': hold_position,
            'handicap': handicap,
            'settlement': settlement,
            'avg': avg,
            'pre_settlement': pre_settlement,
            'pre_close': pre_close,
            'pre_vol': pre_vol,
            'day3_raise': day3_raise,
            'settlement2': settlement2,
            'date': date_obj,
            'raise_speed': raise_speed,
            'u1': u1,
            'u2': u2,
            'u3': [u3, u4, u5, u6],
        }