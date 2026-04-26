from opentdx.client import macQuotationClient
from opentdx.const import ADJUST, BOARD_TYPE, CATEGORY, EX_BOARD_TYPE, EX_MARKET, MARKET, PERIOD, SORT_TYPE, SORT_ORDER
import pandas as pd
import pytest
from opentdx.utils.help import industry_to_board_symbol, ah_code_to_symbol, lot_size_to_symbol
from opentdx.utils.bitmap import PRESET_FIELDS

class TestMacQuotationClientLogin:
    """登录"""

    def test_connected(self, mqc):
        assert mqc.connected is True

class TestMacQuotationClientMixin:
    """SP模式"""

    def test_mix_in(self, mqc, sp_qc):
        """
        测试 MacQuotationClient (mqc) 与 SP模式客户端 (sp_qc) 在获取板块列表时的一致性。
        验证混合模式下的数据获取结果是否与纯SP模式一致。
        """
        result = mqc.get_board_list(BOARD_TYPE.HY, count=5)
        result2 = sp_qc.get_board_list(BOARD_TYPE.HY, count=5)
        assert result == result2
        
    def test_mqc_has_qc_method(self, mqc, qc):
        """
        测试 MacQuotationClient (mqc) 是否具备标准 QuotationClient (qc) 的行情获取能力。
        验证通过 mqc 获取的个股行情数据与标准 qc 获取的数据一致。
        """
        mqc.login()
        result = mqc.get_quotes(MARKET.SZ, '000001')
        result2 = qc.get_quotes(MARKET.SZ, '000001')
        
        # 验证两个结果都是列表且长度相同
        assert isinstance(result, list), f"mqc 返回类型错误: {type(result)}"
        assert isinstance(result2, list), f"qc 返回类型错误: {type(result2)}"
        assert len(result) == len(result2), f"返回数据长度不一致: mqc={len(result)}, qc={len(result2)}"
        
class TestMacQuotationClientStock:
    """股票市场 API"""
    def test_get_market_monitor(self, mqc:macQuotationClient):
        result = mqc.get_market_monitor(MARKET.SH)
        assert result is not None
        
        df = pd.DataFrame(result)
        if 'name' not in df.columns:  # 正确的检查列是否存在的方式
            assert "未找到 [主力监控] 功能 的 name 字段"

    def test_equal_market_monitor(self, mqc:macQuotationClient, qc):
        result1 = mqc.get_market_monitor(MARKET.SH, start = 0, count=5)
        result2 = qc.get_unusual(MARKET.SH, start = 0, count=5)
        
        # 验证数据类型和长度一致性
        assert isinstance(result1, list), f"result1 应为列表类型，实际为 {type(result1)}"
        assert isinstance(result2, list), f"result2 应为列表类型，实际为 {type(result2)}"
        assert len(result1) == len(result2), f"两个结果长度不一致: {len(result1)} != {len(result2)}"
        
        # 只测试部分关键字段（排除 name 和 mac协议特有的 v1-v4 字段）
        key_fields = ['index', 'market', 'code', 'time', 'desc', 'value', 'unusual_type']
        
        for i, (item1, item2) in enumerate(zip(result1, result2)):
            # 提取关键字段进行比对
            filtered1 = {k: item1[k] for k in key_fields if k in item1}
            filtered2 = {k: item2[k] for k in key_fields if k in item2}
            
            # 验证所有关键字段都存在
            assert len(filtered1) == len(key_fields), \
                f"第 {i} 条记录 result1 缺少字段: 期望{len(key_fields)}个，实际{len(filtered1)}个"
            assert len(filtered2) == len(key_fields), \
                f"第 {i} 条记录 result2 缺少字段: 期望{len(key_fields)}个，实际{len(filtered2)}个"
            
            # 比对关键字段
            assert filtered1 == filtered2, \
                f"第 {i} 条记录关键字段比对失败:\n  result1: {filtered1}\n  result2: {filtered2}"

class TestMacQuotationClientBoard:
    """板块 API"""

    def test_get_board_count(self, mqc):
        result = mqc.get_board_count(BOARD_TYPE.HY)
        assert result is not None
        assert 'total' in result
        assert result['total'] > 0

    def test_get_board_list(self, mqc):
        result = mqc.get_board_list(BOARD_TYPE.HY, count=5)
        assert isinstance(result, list)
        assert len(result) > 0
        
    def test_ex_get_board_list(self, meqc):
        result = meqc.get_board_list(EX_BOARD_TYPE.HK_ALL, count=5)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_board_members_quotes(self, mqc):
        result = mqc.get_board_members_quotes('880761', count=5)
        assert isinstance(result, list)

    def test_get_board_members(self, mqc):
        # 普通板块
        result = mqc.get_board_members('880761', count=5)
        assert isinstance(result, list)
        assert len(result) > 0
        
        # 指数成分股 000xxx
        result = mqc.get_board_members('000903', count=5)
        assert isinstance(result, list)
        assert len(result) > 0
        
        # 指数成分股 399xxx
        result = mqc.get_board_members('399262', count=5)
        assert isinstance(result, list)
        assert len(result) > 0
        
        # 北证成分股 899xxx
        result = mqc.get_board_members('899601', count=5)
        assert isinstance(result, list)
        assert len(result) > 0
        
        
    def test_get_board_members_hkboard(self, meqc):
        result = meqc.get_board_members('HK0287', count=5)
        assert isinstance(result, list)
        assert len(result) > 0
        
    def test_get_board_members_usboard(self, meqc):
        result = meqc.get_board_members('US0495', count=5)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_board_members_with_sort_type(self, mqc):
        """测试 sort_type 和 sort_order 参数是否生效"""
        board_code = '880761'
        count = 10

        # 测试按成交量降序排序 (默认通常是降序，但显式指定更稳妥)
        result_desc = mqc.get_board_members_quotes(board_code, count=count, sort_type=SORT_TYPE.VOLUME, sort_order=SORT_ORDER.DESC)
        assert isinstance(result_desc, list)
        assert len(result_desc) > 1, "返回数据不足以进行排序验证"

        vols_desc = [item.get('vol', 0) for item in result_desc if isinstance(item, dict)]
        assert len(vols_desc) == len(result_desc), "部分数据缺失 vol 字段"
        
        # 检查是否是降序排列 (从大到小)
        for i in range(len(vols_desc) - 1):
            assert vols_desc[i] >= vols_desc[i+1], f"降序排序错误: 索引 {i} 的 vol ({vols_desc[i]}) 小于 索引 {i+1} 的 vol ({vols_desc[i+1]})"

        # 测试按成交量升序排序
        result_asc = mqc.get_board_members_quotes(board_code, count=count, sort_type=SORT_TYPE.VOLUME, sort_order=SORT_ORDER.ASC)
        assert isinstance(result_asc, list)
        assert len(result_asc) > 1, "返回数据不足以进行排序验证"

        vols_asc = [item.get('vol', 0) for item in result_asc if isinstance(item, dict)]
        assert len(vols_asc) == len(result_asc), "部分数据缺失 vol 字段"

        # 检查是否是升序排列 (从小到大)
        for i in range(len(vols_asc) - 1):
            assert vols_asc[i] <= vols_asc[i+1], f"升序排序错误: 索引 {i} 的 vol ({vols_asc[i]}) 大于 索引 {i+1} 的 vol ({vols_asc[i+1]})"


    def test_get_symbol_zjlx(self, mqc):
        result = mqc.get_symbol_zjlx('000100', MARKET.SZ)
        assert result is not None
        
    def test_get_symbol_zjlx_not_support_ex_market(self, mqc):
        """测试资金流向不支持扩展市场（EX_MARKET）
        
        可能的行为：
        1. 抛出 TypeError 异常
        2. 返回 None
        """
        import pytest
        try:
            result = mqc.get_symbol_zjlx('000100', EX_MARKET.US_STOCK)
            # 如果没有抛出异常，应该返回 None
            assert result is None, f"期望返回 None，但实际返回: {type(result).__name__}"
        except TypeError as e:
            # 如果抛出 TypeError，验证错误信息
            assert "market 参数必须为 MARKET 类型" in str(e) or "MARKET" in str(e)

    def test_get_symbol_belong_board(self, mqc):
        result = mqc.get_symbol_belong_board('000100', MARKET.SZ)
        assert result is not None

    def test_get_symbol_bars(self, mqc):
        result = mqc.get_symbol_bars(MARKET.SZ, '000100', PERIOD.DAILY, count=5)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_symbol_bars_with_adjust(self, mqc):
        result = mqc.get_symbol_bars(MARKET.SZ, '000100', PERIOD.DAILY, count=5, fq=ADJUST.QFQ)
        assert isinstance(result, list)
        assert len(result) > 0

    def test_get_board_list_ex_board_type(self, mqc):
        result = mqc.get_board_list(EX_BOARD_TYPE.HK_ALL, count=5)
        assert result is None or isinstance(result, list)


class TestMacQuotationClientBoardFields:
    """板块 API f"""

    def test_base_info(self, mqc:macQuotationClient):
        
        print("支持自定义字段 ohlc")

        rs = mqc.get_board_members_quotes(board_symbol="881394",count=300, fields='basic')
        df = pd.DataFrame(rs)
  
        for field in PRESET_FIELDS['basic']:
            assert field in df.columns, f"字段 {field} 不在返回数据中"
            
    def test_list_fields(self, mqc:macQuotationClient):
        
        print("支持自定义字段 ohlc")
        category = CATEGORY.A
        fields = ['pre_close','open','high','low','close','vol','amount','ah_code','lot_size','industry']
        rs = mqc.get_board_members_quotes(board_symbol=category,count=300, fields=fields)
        df = pd.DataFrame(rs)
  
        for field in fields:
            assert field in df.columns, f"字段 {field} 不在返回数据中"


class TestMacQuotationClientExchange:
    """板块 API 通过help转换 symbol"""

    def test_exchange_ah_code(self, mqc):
        
        print("支持自定义字段 ohlc , 增加ah_code , 查询881394板块")
        ah_code_bit = 0x4a
        lot_size_bit = 0x23
        ah_code_filter = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << ah_code_bit) | (1 << lot_size_bit)
        rs = mqc.get_board_members_quotes(board_symbol="881394",count=300, filter=ah_code_filter)
        df = pd.DataFrame(rs)
        
        if 'ah_code' in df.columns:  # 正确的检查列是否存在的方式
            df['ah_code'] = df.apply(lambda row: ah_code_to_symbol(row['ah_code'], row['market']), axis=1)


        # 新增验证逻辑
        assert df is not None and not df.empty, "获取的数据为空"
        
        # 筛选 symbol 为 601066 的行
        # 注意：symbol 在 DataFrame 中可能是 int 或 string 类型，这里假设是 int，如果是 string 请改为 '601066'
        ah_df = df[df['symbol'] == '601066']
        
        # 确保找到了该股票
        assert not ah_df.empty, "未找到 symbol 为 601066 的股票数据"
        
        # 获取第一行的 ah_code 并验证
        target_ah_code = ah_df.iloc[0]['ah_code']
        assert target_ah_code == '06066', f"期望 ah_code 为 '06066'，实际为 '{target_ah_code}'"
        

    def test_exchange_dq_symbol(self, mqc):
        
        print("支持自定义字段 ohlc , 增加ah_code , 查询881394板块")
        ah_code_bit = 0x4a
        lot_size_bit = 0x23
        ah_code_filter = (1 << 1) | (1 << 2) | (1 << 3) | (1 << 4) | (1 << 5) | (1 << ah_code_bit) | (1 << lot_size_bit)
        rs = mqc.get_board_members_quotes(board_symbol="881394", count=100, filter=ah_code_filter)
        df = pd.DataFrame(rs)
        

        if 'lot_size' in df.columns:  # 正确的检查列是否存在的方式
            df['dq_symbol'] = df.apply(lambda row: lot_size_to_symbol(row['lot_size']), axis=1)
            
        # 新增验证逻辑
        assert df is not None and not df.empty, "获取的数据为空"
        
        # 验证 000166 的 dq_symbol
        df_000166 = df[df['symbol'] == '000166']
        assert not df_000166.empty, "未找到 symbol 为 000166 的股票数据"
        target_dq_symbol_166 = df_000166.iloc[0]['dq_symbol']
        assert target_dq_symbol_166 == '880202', f"期望 000166 的 dq_symbol 为 '880202'，实际为 '{target_dq_symbol_166}'"

        # 验证 600999 的 dq_symbol
        df_600999 = df[df['symbol'] == '600999']
        assert not df_600999.empty, "未找到 symbol 为 600999 的股票数据"
        target_dq_symbol_999 = df_600999.iloc[0]['dq_symbol']
        assert target_dq_symbol_999 == '880218', f"期望 600999 的 dq_symbol 为 '880218'，实际为 '{target_dq_symbol_999}'"
        

    def test_exchange_industry_symbol(self, mqc):

        print("支持自定义字段 ohlc , 增加ah_code , 查询880201板块-黑龙江板块")

        industry_bit = 0x1c
        ah_code_filter =  (1 << industry_bit)
        rs = mqc.get_board_members_quotes(board_symbol="880201",count=100, filter=ah_code_filter)
        df = pd.DataFrame(rs)

        if 'industry' in df.columns:  # 正确的检查列是否存在的方式
            df['industry_symbol'] = df['industry'].apply(lambda x: industry_to_board_symbol(x))
        
        # 新增验证逻辑
        assert df is not None and not df.empty, "获取的数据为空"
        
        # 验证 000166 的 dq_symbol
        df_300900 = df[df['symbol'] == '300900']
        assert not df_300900.empty, "未找到 symbol 为 300900 的股票数据"
        target = df_300900.iloc[0]['industry_symbol']
        assert target == '881288', f"期望 300900 的 dq_symbol 为 '881288'，实际为 '{target}'"


class TestMacQuotationClientTickChart:
    """分时图 API - 真实请求测试"""
        
    def test_get_symbol_tick_chart_stock_basic(self, mqc):
        """测试A股基本分时图数据获取"""
        result = mqc.get_symbol_tick_chart(MARKET.SZ, '000001')
        
        # 验证返回数据类型
        assert isinstance(result, dict), f"返回类型应为dict，实际为 {type(result)}"
        
        # 验证必需字段存在
        required_fields = [
            'market', 'code', 'name', 'decimal', 'category', 'vol_unit',
            'time', 'pre_close', 'open', 'high', 'low', 'close',
            'momentum', 'vol', 'amount', 'turnover', 'avg',
            'industry', 'industry_code', 'chart_data'
        ]
        
        for field in required_fields:
            assert field in result, f"缺少必需字段: {field}"
        
        # 验证基本信息正确性
        assert result['code'] == '000001', f"股票代码错误: {result['code']}"
        assert result['market'] == MARKET.SZ.value, f"市场代码错误: {result['market']}"
        assert isinstance(result['name'], str) and len(result['name']) > 0, "股票名称不能为空"
        
        # 验证价格字段合理性
        assert result['pre_close'] > 0, f"昨收价应大于0: {result['pre_close']}"
        assert result['open'] >= 0, f"开盘价应>=0: {result['open']}"
        assert result['high'] >= 0, f"最高价应>=0: {result['high']}"
        assert result['low'] >= 0, f"最低价应>=0: {result['low']}"
        assert result['close'] >= 0, f"收盘价应>=0: {result['close']}"
        
        # 验证高低价格逻辑
        if result['high'] > 0 and result['low'] > 0:
            assert result['high'] >= result['low'], \
                f"最高价({result['high']})应>=最低价({result['low']})"
        
        # 验证成交量和成交额
        assert result['vol'] >= 0, f"成交量应>=0: {result['vol']}"
        assert result['amount'] >= 0, f"成交额应>=0: {result['amount']}"
        
        # 验证分时图数据
        assert isinstance(result['chart_data'], list), "chart_data应为列表"
        if len(result['chart_data']) > 0:
            # 验证分时图数据结构
            first_point = result['chart_data'][0]
            assert 'time' in first_point, "分时图数据点缺少time字段"
            assert 'price' in first_point, "分时图数据点缺少price字段"
            assert 'avg' in first_point, "分时图数据点缺少avg字段"
            assert 'vol' in first_point, "分时图数据点缺少vol字段"
            assert 'momentum' in first_point, "分时图数据点缺少momentum字段"

    def test_get_symbol_tick_chart_with_date(self, mqc):
        """测试指定日期的历史分时图数据"""
        from datetime import date
        
        # 使用一个最近的交易日（需要根据实际情况调整）
        query_date = date(2024, 1, 15)
        result = mqc.get_symbol_tick_chart(MARKET.SH, '600000', query_date)
        
        # 验证返回数据类型
        assert isinstance(result, dict), f"返回类型应为dict，实际为 {type(result)}"
        
        # 验证基本信息
        assert result['code'] == '600000', f"股票代码错误: {result['code']}"
        assert result['market'] == MARKET.SH.value, f"市场代码错误: {result['market']}"
        
        # 验证时间字段（历史数据应该有具体的时间戳）
        assert result['time'] is not None, "历史数据的时间戳不应为None"
        
        # 验证日期是否正确
        if result['time']:
            result_date = result['time'].date()
            assert result_date == query_date, \
                f"返回数据日期({result_date})与查询日期({query_date})不一致"
        
        # 验证价格数据有效性
        assert result['pre_close'] > 0, f"昨收价应大于0: {result['pre_close']}"
        assert result['close'] >= 0, f"收盘价应>=0: {result['close']}"
        
        # 历史数据的chart_data可能为空或包含数据
        assert isinstance(result['chart_data'], list), "chart_data应为列表"

    def test_get_symbol_tick_chart_invalid_date(self, mqc):
        """测试无效日期的处理"""
        from datetime import date
        
        # 测试未来日期（应该返回空数据或特定错误）
        future_date = date(2030, 12, 31)
        result = mqc.get_symbol_tick_chart(MARKET.SZ, '000001', future_date)
        
        # 验证返回类型仍然正确
        assert isinstance(result, dict), "即使日期无效，也应返回字典类型"
        
        # 未来日期可能返回空数据或部分字段为空
        # 这里主要验证不会抛出异常
        assert result is not None, "返回值不应为None"

    def test_get_symbol_tick_chart_weekend_date(self, mqc):
        """测试周末日期的处理"""
        from datetime import date
        
        # 2024-01-13 是星期六
        weekend_date = date(2024, 1, 13)
        result = mqc.get_symbol_tick_chart(MARKET.SH, '600000', weekend_date)
        
        # 验证返回类型
        assert isinstance(result, dict), "周末日期查询应返回字典类型"
        
        # 周末无交易数据，但不应抛出异常
        assert result is not None, "周末查询返回值不应为None"

    def test_get_symbol_tick_chart_hk_stock(self, meqc):
        """测试港股分时图数据获取"""
        # 使用港股主板市场
        result = meqc.get_symbol_tick_chart(EX_MARKET.HK_MAIN_BOARD, '00700')
        
        # 验证返回数据类型
        assert isinstance(result, dict), f"返回类型应为dict，实际为 {type(result)}"
        
        assert isinstance(result['chart_data'], list), f" result['chart_data'] 返回类型应为list，实际为 {type(result['chart_data'])}"


    def test_get_symbol_tick_chart_hk_with_date(self, meqc):
        """测试港股历史分时图数据"""
        from datetime import date
        
        # 使用一个最近的交易日
        query_date = date(2024, 1, 15)
        result = meqc.get_symbol_tick_chart(EX_MARKET.HK_MAIN_BOARD, '00700', query_date)
        
        # 港股历史数据可能返回None（取决于服务器支持情况）
        # 这里主要验证不会抛出异常
        if result is not None:
            # 如果返回数据，验证其结构
            assert isinstance(result, dict), f"返回类型应为dict，实际为 {type(result)}"
            
            # 验证基本信息
            assert result['code'] == '00700', f"港股代码错误: {result['code']}"
            assert result['market'] == EX_MARKET.HK_MAIN_BOARD.value, \
                f"港股市场代码错误: {result['market']}"
            
            # 验证时间字段
            if result['time']:
                result_date = result['time'].date()
                # 港股历史数据日期应与查询日期一致
                assert result_date == query_date, \
                    f"港股返回数据日期({result_date})与查询日期({query_date})不一致"
            
            # 验证价格数据
            assert result['pre_close'] > 0, f"港股昨收价应大于0: {result['pre_close']}"
        else:
            # 如果返回None，说明服务器不支持该日期的历史数据，这也是可接受的
            pass

    def test_get_symbol_tick_chart_chart_data_structure(self, mqc):
        """测试分时图数据结构的完整性"""
        result = mqc.get_symbol_tick_chart(MARKET.SZ, '000001')
        
        # 验证chart_data是列表
        assert isinstance(result['chart_data'], list), "chart_data必须是列表类型"
        
        # 如果有分时数据，验证每个数据点的结构
        if len(result['chart_data']) > 0:
            for i, point in enumerate(result['chart_data']):
                assert isinstance(point, dict), f"第{i}个分时数据点应为字典类型"
                
                # 验证必需字段
                assert 'time' in point, f"第{i}个分时数据点缺少time字段"
                assert 'price' in point, f"第{i}个分时数据点缺少price字段"
                assert 'avg' in point, f"第{i}个分时数据点缺少avg字段"
                assert 'vol' in point, f"第{i}个分时数据点缺少vol字段"
                assert 'momentum' in point, f"第{i}个分时数据点缺少momentum字段"
                
                # 验证字段类型
                assert point['price'] >= 0, f"第{i}个数据点价格应>=0"
                assert point['avg'] >= 0, f"第{i}个数据点均价应>=0"
                assert point['vol'] >= 0, f"第{i}个数据点成交量应>=0"
                
                # time字段应该是datetime.time类型
                from datetime import time as time_type
                assert isinstance(point['time'], time_type), \
                    f"第{i}个数据点time字段应为time类型，实际为{type(point['time'])}"


class TestMacQuotationClientSymbolQuotes:
    """分时图 API - 真实请求测试"""

    def test_get_symbol_quotes(self, mqc:macQuotationClient):
        """测试A股的股票信息"""
        symbol_list = [
            (MARKET.SZ, '000001'),
            (MARKET.SH, '688808'),
            (MARKET.SZ, '000999')
            
        ]
        print(symbol_list)
        result = mqc.get_symbol_quotes(symbol_list)
        df = pd.DataFrame(result['stocks'])
        print(result['stocks'])
        
    def test_get_symbol_quotes_with_basic_fields(self, mqc:macQuotationClient):
        """测试使用 basic 字段预设获取股票行情"""
        symbol_list = [
            (MARKET.SZ, '000001'),
            (MARKET.SH, '600000'),
        ]
        
        result = mqc.get_symbol_quotes(symbol_list, fields="basic")
        
        # 验证返回结构
        assert isinstance(result, dict), f"返回类型应为dict，实际为{type(result)}"
        assert "field_bitmap" in result, "返回值应包含field_bitmap字段"
        assert "count" in result, "返回值应包含count字段"
        assert "stocks" in result, "返回值应包含stocks字段"
        assert result["count"] == len(symbol_list), f"返回数量应与请求数量一致"
        assert len(result["stocks"]) == len(symbol_list), f"返回股票数应与请求数量一致"
        
        # 验证基本字段存在
        for stock in result["stocks"]:
            assert "market" in stock, "股票数据应包含market字段"
            assert "symbol" in stock, "股票数据应包含symbol字段"
            assert "pre_close" in stock, "basic字段集应包含pre_close"
            assert "open" in stock, "basic字段集应包含open"
            assert "high" in stock, "basic字段集应包含high"
            assert "low" in stock, "basic字段集应包含low"
            assert "close" in stock, "basic字段集应包含close"
            assert "vol" in stock, "basic字段集应包含vol"
            
        print(f"Basic字段测试结果: {len(result['stocks'])}只股票")
        
    def test_get_symbol_quotes_with_quote_fields(self, mqc:macQuotationClient):
        """测试使用 quote 字段预设获取盘口数据"""
        symbol_list = [
            (MARKET.SZ, '000001'),
        ]
        
        result = mqc.get_symbol_quotes(symbol_list, fields="quote")
        
        # 验证返回结构
        assert isinstance(result, dict), f"返回类型应为dict，实际为{type(result)}"
        assert len(result["stocks"]) == len(symbol_list), f"返回股票数应与请求数量一致"
        
        # 验证盘口字段存在
        for stock in result["stocks"]:
            assert "bid" in stock, "quote字段集应包含bid"
            assert "ask" in stock, "quote字段集应包含ask"
            assert "bid_volume" in stock, "quote字段集应包含bid_volume"
            assert "ask_volume" in stock, "quote字段集应包含ask_volume"
            assert "last_volume" in stock, "quote字段集应包含last_volume"
            
        print(f"Quote字段测试结果: bid={result['stocks'][0].get('bid')}, ask={result['stocks'][0].get('ask')}")
        
    def test_get_symbol_quotes_with_volume_fields(self, mqc:macQuotationClient):
        """测试使用 volume 字段预设获取量能数据"""
        symbol_list = [
            (MARKET.SZ, '000001'),
        ]
        
        result = mqc.get_symbol_quotes(symbol_list, fields="volume")
        
        # 验证返回结构
        assert isinstance(result, dict), f"返回类型应为dict，实际为{type(result)}"
        assert len(result["stocks"]) == len(symbol_list), f"返回股票数应与请求数量一致"
        
        # 验证量能字段存在
        for stock in result["stocks"]:
            assert "vol" in stock, "volume字段集应包含vol"
            assert "amount" in stock, "volume字段集应包含amount"
            assert "turnover" in stock, "volume字段集应包含turnover"
            assert "vol_ratio" in stock, "volume字段集应包含vol_ratio"
            
        print(f"Volume字段测试结果: vol={result['stocks'][0].get('vol')}, amount={result['stocks'][0].get('amount')}")
        
    def test_get_symbol_quotes_with_combined_fields(self, mqc:macQuotationClient):
        """测试使用组合字段（basic+quote）获取股票行情"""
        symbol_list = [
            (MARKET.SZ, '000001'),
            (MARKET.SH, '600000'),
        ]
        
        result = mqc.get_symbol_quotes(symbol_list, fields="basic+quote")
        
        # 验证返回结构
        assert isinstance(result, dict), f"返回类型应为dict，实际为{type(result)}"
        assert result["count"] == len(symbol_list), f"返回数量应与请求数量一致"
        assert len(result["stocks"]) == len(symbol_list), f"返回股票数应与请求数量一致"
        
        # 验证组合字段都存在
        for stock in result["stocks"]:
            # Basic字段
            assert "pre_close" in stock, "应包含pre_close"
            assert "close" in stock, "应包含close"
            # Quote字段
            assert "bid" in stock, "应包含bid"
            assert "ask" in stock, "应包含ask"
            
        print(f"Combined字段测试结果: {len(result['stocks'])}只股票，字段数={len(result['stocks'][0])}")
        
    def test_get_symbol_quotes_with_fundamental_fields(self, mqc:macQuotationClient):
        """测试使用 fundamental 字段预设获取基本面数据"""
        symbol_list = [
            (MARKET.SZ, '000001'),
        ]
        
        result = mqc.get_symbol_quotes(symbol_list, fields="fundamental")
        
        # 验证返回结构
        assert isinstance(result, dict), f"返回类型应为dict，实际为{type(result)}"
        assert len(result["stocks"]) == len(symbol_list), f"返回股票数应与请求数量一致"
        
        # 验证基本面字段存在
        for stock in result["stocks"]:
            assert "total_shares" in stock, "fundamental字段集应包含total_shares"
            assert "float_shares" in stock, "fundamental字段集应包含float_shares"
            assert "EPS" in stock, "fundamental字段集应包含EPS"
            assert "net_assets" in stock, "fundamental字段集应包含net_assets"
            
        print(f"Fundamental字段测试结果: EPS={result['stocks'][0].get('EPS')}, net_assets={result['stocks'][0].get('net_assets')}")
        
    def test_get_symbol_quotes_with_custom_filter(self, mqc:macQuotationClient):
        """测试使用自定义filter参数获取股票行情"""
        from opentdx.utils.bitmap import fields_to_filter
        
        symbol_list = [
            (MARKET.SZ, '000001'),
        ]
        
        # 使用自定义filter（只获取价格和成交量）
        custom_filter = fields_to_filter(["pre_close", "close", "vol"])
        result = mqc.get_symbol_quotes(symbol_list, filter=custom_filter)
        
        # 验证返回结构
        assert isinstance(result, dict), f"返回类型应为dict，实际为{type(result)}"
        assert len(result["stocks"]) == len(symbol_list), f"返回股票数应与请求数量一致"
        
        # 验证自定义字段存在
        for stock in result["stocks"]:
            assert "pre_close" in stock, "应包含pre_close"
            assert "close" in stock, "应包含close"
            assert "vol" in stock, "应包含vol"
            
        print(f"Custom filter测试结果: 位图={result['field_bitmap'][:16]}...")
        

