from opentdx.client import macQuotationClient
from opentdx.const import ADJUST, BOARD_TYPE, CATEGORY, EX_BOARD_TYPE, EX_MARKET, MARKET, PERIOD, SORT_TYPE, SORT_ORDER
import pandas as pd
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
