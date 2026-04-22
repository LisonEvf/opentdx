from .baseStockClient import BaseStockClient, _paginate, update_last_ack_time
from .quotationClient import QuotationClient
from .exQuotationClient import exQuotationClient
from .commonClientMixin import CommonClientMixin
from opentdx.parser.mac_quotation import MarketMonitor
from opentdx.const import MARKET, mac_hosts, mac_ex_hosts

# class macQuotationClient(BaseStockClient, CommonClientMixin):
class macQuotationClient(QuotationClient, CommonClientMixin):
    def __init__(self, multithread=False, heartbeat=False, auto_retry=False, raise_exception=False):
        super().__init__(multithread, heartbeat, auto_retry, raise_exception)
        self.hosts = mac_hosts
        # CommonClientMixin 需识别到配置 _sp_mode_enabled
        self._sp_mode_enabled = True
        
    @update_last_ack_time
    def get_market_monitor(self, market: MARKET, start: int = 0, count: int = 10) -> list[dict]:
        """
        获取市场监控 - 与get_unusual的区别在于，不需要Login() 也能访问,且返回结果中包含了股票名称（name字段）
        :param market:
        :param start:
        :param count:
        :return:
        """
        return _paginate(
            lambda s, c: self.call(MarketMonitor(market, s, c)),
            600, count, start,
        )
        

# class macExQuotationClient(BaseStockClient, CommonClientMixin):
class macExQuotationClient(exQuotationClient, CommonClientMixin):
    def __init__(self, multithread=False, heartbeat=False, auto_retry=False, raise_exception=False):
        super().__init__(multithread, heartbeat, auto_retry, raise_exception)
        self.hosts = mac_ex_hosts
        # CommonClientMixin 需识别到配置 _sp_mode_enabled
        self._sp_mode_enabled = True