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
        获取市场监控数据（主力监控）。
        
        与get_unusual的区别在于，不需要Login()也能访问，且返回结果中包含了股票名称（name字段）。
        
        Args:
            market: 市场类型，指定要查询的市场（如上海、深圳等）
            start: 起始位置，用于分页查询，默认为0
            count: 获取数量，指定返回的记录条数，默认为10
        
        Returns:
            包含市场监控信息的字典列表，每个字典包含以下字段：
            - index (int): 记录索引位置
            - market (MARKET): 市场类型枚举值
            - code (str): 股票代码
            - name (str): 股票名称
            - time (datetime.time): 监控时间
            - desc (str): 监控描述，表示异动类型（见下方示例）
            - value (str): 数值描述，具体的数值信息
            - unusual_type (int): 异动类型代码
            - v1-v4 (float): 原始数值字段
            
            desc 字段常见示例：
            - "主力买入" / "主力卖出": 主力资金动向
            - "加速拉升" / "加速下跌": 价格快速变动
            - "低位反弹" / "高位回落": 价格反转信号
            - "撑杆跳高" / "平台跳水": 剧烈价格波动
            - "单笔冲涨" / "单笔冲跌": 单笔交易冲击
            - "区间放量涨" / "区间放量跌" / "区间放量平": 成交量异常
            - "区间缩量": 成交量萎缩
            - "大单托盘" / "大单压盘" / "大单锁盘": 大单行为
            - "竞价试买": 集合竞价阶段行为
            - "逼近涨停" / "封涨停板" / "打开涨停": 涨停相关
            - "逼近跌停" / "封跌停板" / "打开跌停": 跌停相关
            - "尾盘拉升" / "尾盘打压" / "尾盘对倒": 尾盘异动
            - "盘中强势" / "盘中弱势": 盘中强弱状态
            - "急速拉升" / "急速下跌": 极速价格变动
            
            返回数据示例：
            [
                {
                    "index": 0,                      # 记录索引
                    "market": <MARKET.SH: 1>,       # 市场类型
                    "code": "600519",               # 股票代码
                    "name": "贵州茅台",              # 股票名称
                    "time": datetime.time(14, 30, 0), # 监控时间
                    "desc": "区间放量涨",            # 异动描述
                    "value": "2.5倍3.20%",          # 数值描述
                    "unusual_type": 11,             # 异动类型代码 (0x0b)
                    "v1": 1,                        # 原始数值1
                    "v2": 2.5,                      # 原始数值2（倍数）
                    "v3": 0.032,                    # 原始数值3（涨跌幅）
                    "v4": 0.0                       # 原始数值4
                },
                ...
            ]
        
        Example:
            >>> from opentdx.const import MARKET
            >>> client = macQuotationClient()
            >>> 
            >>> # 【推荐】增量获取模式 - 维护 last_index 避免重复拉取
            >>> last_index = 0  # 在客户端持久化存储此值（如 Redis/数据库）
            >>> new_data = client.get_market_monitor(MARKET.SH, start=last_index, count=100)
            >>> if new_data:
            ...     last_index += len(new_data)  # 更新索引供下次使用
            ...     print(f"新增 {len(new_data)} 条记录，当前索引: {last_index}")
            >>> 
            >>> # 基础用法 - 获取上海市场前10条监控数据
            >>> data = client.get_market_monitor(MARKET.SH, start=0, count=10)
            >>> print(f"获取到 {len(data)} 条记录")
            >>> for item in data:
            ...     print(f"{item['code']} - {item['name']}: {item['desc']} ({item['value']})")
            600519 - 贵州茅台: 区间放量涨 (2.5倍3.20%)
            000858 - 五粮液: 主力买入 (1800.50/1795.00)
            600036 - 招商银行: 加速拉升 (1.25%)
            >>> 
            >>> # 筛选特定类型的监控数据
            >>> volume_spike = [item for item in data if '放量' in item['desc']]
            >>> print(f"发现 {len(volume_spike)} 条放量信号")
            >>> 
            >>> # 分页查询 - 获取深圳市场第20-30条监控数据
            >>> data = client.get_market_monitor(MARKET.SZ, start=20, count=10)
            >>> for stock in data:
            ...     print(f"{stock['code']} - {stock['name']}: {stock['desc']}")
            >>> 
            >>> # 批量获取所有市场的监控数据
            >>> all_data = []
            >>> for market in [MARKET.SH, MARKET.SZ]:
            ...     page_data = client.get_market_monitor(market, count=100)
            ...     all_data.extend(page_data)
            >>> print(f"共获取 {len(all_data)} 条监控数据")
        
        Note:
            - **性能优化建议**: 建议在客户端维护 last_index（最后获取的位置索引），每次调用时传入该值作为 start 参数，实现增量数据获取，避免每次都从0开始全量拉取。
            - 该接口无需登录即可调用，适合快速获取市场概况
            - 最大单次请求数量限制为600条（内部通过_paginate自动处理分页）
            - 返回的数据已按时间倒序排列，最新的数据在前
            - last_index 应持久化存储（如 Redis、数据库或本地文件），服务重启后可恢复
            - desc 字段描述了具体的异动类型，可用于分类统计和策略触发
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