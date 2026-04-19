from typing import Union

import pandas as pd

from .baseStockClient import update_last_ack_time
from opentdx.const import ADJUST, BOARD_TYPE, CATEGORY, EX_CATEGORY, MARKET, PERIOD, EX_BOARD_TYPE, SORT_TYPE, SORT_ORDER, mac_hosts, mac_ex_hosts
from opentdx.parser.mac_quotation import BoardCount, BoardList, BoardMembers, BoardMembersQuotes, SymbolBar, SymbolBelongBoard
from opentdx.utils.log import log
from functools import wraps


def require_sp_mode(func):
    """装饰器：要求必须先调用 sp() 方法"""
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if hasattr(self, '_check_sp_mode'):
            self._check_sp_mode()
        return func(self, *args, **kwargs)
    return wrapper


# ---------------------- 公共接口  ----------------------
class CommonClientMixin:
    _sp_mode_enabled = False
    
    def sp(self, hosts=None):
        """启动sp模式,支持mac协议调用.

        Args:
            hosts (list of str): List of hosts to use. 如果为None，则根据子类类型自动选择

        Returns:
            self
        """
        # 如果未传入 hosts，根据子类类型自动选择默认值
        if hosts is None:
            # 获取调用者的类名
            class_name = self.__class__.__name__
            
            # 根据类名判断使用哪个默认 hosts
            if class_name == "QuotationClient":
                hosts = mac_hosts
            elif class_name == "exQuotationClient":
                hosts = mac_ex_hosts
            else:
                # 默认使用 mac_hosts
                hosts = mac_hosts
        
        self.hosts = hosts
        self._sp_mode_enabled = True
        return self

    def _check_sp_mode(self):
        """检查是否已启用sp模式"""
        if not self._sp_mode_enabled:
            raise RuntimeError(
                "必须先调用 sp() 方法启用sp模式后才能使用此方法。\n"
                "示例: client.sp().get_board_members_quotes(...)"
            )
            
    @require_sp_mode
    @update_last_ack_time
    def get_board_count(self, market: Union[BOARD_TYPE, EX_BOARD_TYPE]):
        return self.call(BoardCount(market))

    @require_sp_mode
    @update_last_ack_time
    def get_board_list(self, market: Union[BOARD_TYPE, EX_BOARD_TYPE], count=10000):
        MAX_LIST_COUNT = 150
        security_list = []
        page_size = min(count, MAX_LIST_COUNT)
        
        msg = f"TDX 板块列表：{market} 查询总量{count}"
        log.debug(msg)
        
        for start in range(0, count, page_size):
            current_count = min(page_size, count - start)
            part = self.call(BoardList(board_type=market, start=start, page_size=current_count))
            
            if len(part) > 0:
                security_list.extend(part)
            
            if len(part) < current_count:
                log.debug(f"{msg} 数据量不足，获取结束")
                break
                
        return security_list

    @require_sp_mode
    @update_last_ack_time
    def get_board_members_quotes(self, board_symbol: str | CATEGORY | EX_CATEGORY = "881001", count=100000, sort_type: SORT_TYPE = SORT_TYPE.CHANGE_PCT, sort_order=SORT_ORDER.DESC, filter=0):
        MAX_LIST_COUNT = 80
        security_list = []
        
        msg = f"TDX 板块成分报价：{board_symbol} 查询总量{count}"
        log.debug(msg)
        
        for start in range(0, count, MAX_LIST_COUNT):
            current_count = min(MAX_LIST_COUNT, count - start)
            rs = self.call(BoardMembersQuotes(board_symbol=board_symbol, start=start, page_size=current_count, sort_type=sort_type, sort_order=sort_order, filter=filter))
            part = rs["stocks"]
            
            if len(part) > 0:
                security_list.extend(part)
            
            if len(part) < current_count:
                log.debug(f"{msg} 数据量不足，获取结束")
                break
                
        return security_list

    @require_sp_mode
    # @update_last_ack_time
    def get_board_members(self, board_symbol: str, count=100000):
        MAX_LIST_COUNT = 80
        security_list = []
        
        msg = f"TDX 板块成员：{board_symbol} 查询总量{count}"
        log.debug(msg)
        
        for start in range(0, count, MAX_LIST_COUNT):
            current_count = min(MAX_LIST_COUNT, count - start)
            rs = self.call(BoardMembers(board_symbol=board_symbol, start=start, page_size=current_count))
            part = rs["stocks"]
            
            if len(part) > 0:
                security_list.extend(part)
            
            if len(part) < current_count:
                log.debug(f"{msg} 数据量不足，获取结束")
                break
                
        return security_list
    
    @require_sp_mode
    @update_last_ack_time
    def get_symbol_belong_board(self, symbol: str, market: MARKET) -> pd.DataFrame:
        parser = SymbolBelongBoard(symbol=symbol, market=market)
        df = self.call(parser)
        return df
    
    @require_sp_mode    
    @update_last_ack_time
    def get_symbol_bars(
        self, market: MARKET, code: str, period: PERIOD, times: int = 1, start: int = 0, count: int = 800, fq: ADJUST = ADJUST.NONE
    ):
        MAX_LIST_COUNT = 700
        page_size = min(count, MAX_LIST_COUNT)
        security_list = []
        start = 0

        msg = f"TDX bar :{market} {code} {period} 查询总量{count} {start}  "
        log.debug(msg)

        for start in range(0, count, page_size):
            # 计算本次请求的实际数量，最后一次根据剩余数据减少
            current_count = min(page_size, count - start)

            parser = SymbolBar(market=market, code=code, period=period, times=times, start=start, count=current_count, fq=fq)
            part = self.call(parser)

            if len(part) > 0:
                security_list.extend(part)

            if len(part) < current_count:
                log.debug(f"{msg} 数据量不足,获取结束")
                break

        return security_list