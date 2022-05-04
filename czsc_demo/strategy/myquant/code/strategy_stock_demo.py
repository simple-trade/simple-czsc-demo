# coding=utf-8
from __future__ import print_function, absolute_import
from gm.api import *
import pandas as pd
import numpy as np
from datetime import datetime

from simple import CzscModelEngine
from simple.czsc import Utils
from simple import LoggerFactory
logger = LoggerFactory.getLogger(__name__)

from czsc_demo.conf.conf import conf
import czsc_demo.strategy.myquant.code.myquant_base_strategy_stock_demo as base




token = conf['myquant']['token']
serv_addr = conf['myquant']['serv_addr']

_conf = conf['myquant']['strategy_demo']

mode = _conf['mode']
market = _conf['market']
volume = _conf['volume']
backtest_slippage = _conf['backtest_slippage']
backtest_account_id = _conf['backtest_account_id']
strategy_id = _conf['strategy_id']
frequency = _conf['frequency']
symbols = _conf['symbols']
frequency = _conf['frequency']
backtest_start_time = _conf['backtest_start_time']
backtest_end_time = _conf['backtest_end_time']
backtest_initial_cash = _conf['backtest_initial_cash']
backtest_transaction_ratio = _conf['backtest_transaction_ratio']
backtest_slippage_ratio = _conf['backtest_slippage_ratio']
backtest_commission_ratio = _conf['backtest_commission_ratio']

def _run():
    '''
    封装启动入口
    '''
    logger.info('启动策略, 加载配置\n %s' % _conf)
    run(
        strategy_id=strategy_id,
        filename=__name__,
        mode=mode,  # 2：回测模式，1：实时模式
        token=token,
        backtest_start_time=backtest_start_time,
        backtest_end_time=backtest_end_time,
        backtest_transaction_ratio=backtest_transaction_ratio,
        backtest_initial_cash=backtest_initial_cash,
        backtest_slippage_ratio=backtest_slippage_ratio,
        backtest_commission_ratio=backtest_commission_ratio,
        serv_addr=serv_addr,
    )


def init(context):
    context._market = market
    context._symbol = symbols[0]
    context._backtest_start_time = backtest_start_time
    context._backtest_end_time = backtest_end_time
    if context._market == 2:  # 期货
        context._base_symbol = context._symbol  # 设置基础合约 用于期货
        # 获取当时的主力合约
        startDate = datetime.strptime(context._backtest_start_time, '%Y-%m-%d %H:%M:%S').date()
        continuous_contract = get_continuous_contracts(context._symbol, startDate, startDate)
        context._symbol = continuous_contract[0]['symbol']
        logger.info('初始化期货主力合约【%s】' % context._symbol)
        # 定时检查主力合约
        schedule(schedule_func=__sche_switch_main_symbol, date_rule='1d', time_rule='9:00:00')
    __init(context)


def __init(context):
    '''
    初始化，用于init和切换合约
    '''
    context._frequency = frequency
    context._mode = mode
    context._backtest_slippage = backtest_slippage
    context._backtest_account_id = backtest_account_id
    # 交易手数
    context._volume = volume
    # 合约信息
    context._instrumentinfos_dic = get_instruments(symbols=context._symbol, exchanges=None, sec_types=None, names=None, fields=None, df=False)
    # 获取历史数据
    history_pd = history_n(
        symbol=context._symbol,
        frequency=frequency,
        count=500,
        fields='bob,eob,open,close,high,low',
        fill_missing=None,
        end_time=context._backtest_start_time,
        df=True,
    )
    # 精度转换
    history_pd[['open', 'close', 'high', 'low']] = history_pd[['open', 'close', 'high', 'low']].apply(lambda x: round(x, 2))
    # 设置k线起始时间为索引
    history_pd = history_pd.set_index('bob')
    # 初始化模型
    context._engine = CzscModelEngine(context._symbol, frequency, False, '', ['macd', 'xianduansanmai'])
    for idx in range(history_pd.shape[0]):
        context._engine.k_receive(history_pd.iloc[idx : idx + 1], is_realtime=False)

    # 订阅
    subscribe(symbols=context._symbol, frequency=frequency, count=100)

    # 研究变量
    context._rsch_macd_deviation = None  # macd背驰、背离
    # 绘图变量
    context._draw = True  # 绘图开关
    context._draw_points = []  # 买卖点标记
    logger.info('初始化完成')


def on_bar(context, bars):
    '''
    bar在本周期结束时间后才会推送
    '''
    positions = context.account(account_id=context._backtest_account_id).positions(symbol=context._symbol, side=None)
    if len(positions) == 0:  # 空仓
        __try_open(context=context)
    bar_df = pd.DataFrame(data=[[bars[0].open, bars[0].close, bars[0].high, bars[0].low,]], index=[bars[0].eob], columns=['open', 'close', 'high', 'low'])
    # 精度转换
    bar_df[['open', 'close', 'high', 'low']] = bar_df[['open', 'close', 'high', 'low']].apply(lambda x: round(x, 2))
    # 推入模型
    context._engine.k_receive(bar_df, is_realtime=False)
    positions = context.account(account_id=context._backtest_account_id).positions(symbol=context._symbol, side=None)
    if len(positions) == 1:  # 持仓
        __try_close(context=context, positions=positions)

def __sche_switch_main_symbol(context):
    '''
    切换主力合约，用于定时
    '''
    # 获取当时的主力合约
    continuous_contract = get_continuous_contracts(context._base_symbol, context.now.date(), context.now.date())
    if context._symbol != continuous_contract[0]['symbol']:
        prve_symbol = context._symbol
        current_symbol = continuous_contract[0]['symbol']
        # 清仓前主力合约
        __clear_all_position(context)
        # 绘图控制
        if context._draw:
            base._draw_kline(context=context, extends_name2='all', all=True)
        # 取消订阅原合约
        unsubscribe(symbols=prve_symbol, frequency=frequency)
        # 赋值当前主力合约
        context._symbol = current_symbol
        # 重新设置回测起始时间
        context._backtest_start_time = context.now.strftime('%Y-%m-%d %H:%M:%S')
        # 重新初始化
        __init(context)
        logger.info('----------------------------------------------------------------------------------------------------------------')
        logger.info('定时任务 - 更换主力合约完成 【%s】->【%s】回测起始时间：%s' % (prve_symbol, current_symbol, context._backtest_start_time))
        logger.info('----------------------------------------------------------------------------------------------------------------')




def __entry_struct_condition(context) -> bool:
    '''
    进场结构条件
    '''
    realtime_xianduan_df = context._engine.get_realtime_xianduan_df()
    if realtime_xianduan_df.shape[0] < 2:
        return False  # 线段数量至少要2个
    return True

def __open_long_condition(context) -> bool:
    '''
    开多进场条件
    '''
    return __is_sanmai_up(context)



def __is_sanmai_up(context):
    '''
    判断当前为三买
    '''
    realtime_xianduan_df = context._engine.get_realtime_xianduan_df()
    last_xd = realtime_xianduan_df.iloc[-1]
    zhongshu = context._engine.get_realtime_zhongshu_df()
    # 中枢三买
    is_zhongshusanmai = zhongshu.shape[0] > 0 and last_xd['end_point'][1] > zhongshu.iloc[-1]['top_point'][1]
    # 线段三买
    is_xianduansanmai = False
    factor_result = context._engine.get_factor_result()
    if 'xianduansanmai' in factor_result:  # xianduansanmai数据
        xianduansanmai_factor = factor_result['xianduansanmai']
        if len(xianduansanmai_factor) > 0 and xianduansanmai_factor[0] == 1:
            is_xianduansanmai = True
    # 其中一种三买结构即成立
    if is_zhongshusanmai or is_xianduansanmai:  # 三买
        return True
    return False


def __is_sanmai_down(context):
    '''
    判断当前为三卖
    '''
    realtime_xianduan_df = context._engine.get_realtime_xianduan_df()
    last_xd = realtime_xianduan_df.iloc[-1]
    zhongshu = context._engine.get_realtime_zhongshu_df()
    is_zhongshusanmai = zhongshu.shape[0] > 0 and last_xd['end_point'][1] < zhongshu.iloc[-1]['bottom_point'][1]
    is_xianduansanmai = False
    factor_result = context._engine.get_factor_result()
    if 'xianduansanmai' in factor_result:  # xianduansanmai数据
        xianduansanmai_factor = factor_result['xianduansanmai']
        if len(xianduansanmai_factor) > 0 and xianduansanmai_factor[0] == -1:
            is_xianduansanmai = True
    if is_zhongshusanmai or is_xianduansanmai:  # 三买
        return True
    return False


def __open_short_condition(context) -> bool:
    '''
    开空进场条件
    '''
    return __is_sanmai_down(context)


def __try_open(context):
    '''
    尝试开仓
    '''
    if not __entry_struct_condition(context):
        return  # 不满足结构条件

    realtime_xianduan_df = context._engine.get_realtime_xianduan_df()
    realtime_fenbi_df = context._engine.get_realtime_fenbi_df()
    klines = context._engine.get_klines()
    last_xd_series = realtime_xianduan_df.iloc[-1]

    fb_indices = realtime_fenbi_df.loc[last_xd_series['start_point'][0] : last_xd_series['end_point'][0]].index  # 线段内的分笔序列
    entry_price2_fb_idx = fb_indices[-2]  # 最后一段的倒数第二个分笔
    entry_price2 = realtime_fenbi_df.loc[entry_price2_fb_idx]['price']


    last_xd_type = last_xd_series['type']  # 最后一个线段类型
    if -1 == last_xd_type:  # 最后一段下跌，只尝试开多
        if not __open_long_condition(context):  # 不满足开多进场条件
            return
        entry_price = entry_price2 # 进场价格
        base._open_long_forward_4_bar_backtest(context=context, target_price=entry_price) #尝试开多

    else:  # 最后一段上涨，只尝试开空
        if not __open_short_condition(context):  # 不满足开空进场条件
            return
        entry_price =  entry_price2 # 进场价格
        base._open_short_forward_4_bar_backtest(context=context, target_price=entry_price) #尝试开空


def __try_close(context, positions):
    '''
    模型计算之后尝试平仓
    '''
    realtime_xianduan_df = context._engine.get_realtime_xianduan_df()
    last_xd_series = realtime_xianduan_df.iloc[-1]
    last_xd_type = last_xd_series['type']  # 线段类型
    position = positions[0]
    if position.side == PositionSide_Long:  # 持有多头
        if last_xd_type == -1:  # 下降线段
            last_price = base._get_last_data(context)['last_price']
            base._close_long_forward_4_bar_backtest(context, last_price)  # 按最新价报单
    elif position.side == PositionSide_Short:  # 持有空头
        if last_xd_type == 1 :
            last_price = base._get_last_data(context)['last_price']
            base._close_short_forward_4_bar_backtest(context, last_price)  # 按最新价报单
    else:
        raise Exception('Mars Area 出现未知的持仓方向 【%s】' % position.side)



def __on_execution_report_trade_open(context, execrpt):
    '''
    开仓成交
    '''
    logger.info('【开仓】【成交】>>>')
    context._fund_cost_price = execrpt.price  # 持仓成本
    data_now = base._get_last_data(context)['data_now']
    if execrpt.side == OrderSide_Buy:  # 买入
        logger.info('【顺开多】成交，成交价格：%s，时间：%s' % (execrpt.price, data_now))
        if context._draw:  # 画图
            open_type_str = '顺开多'
            context._draw_points.append(
                [data_now, open_type_str, data_now, execrpt.price, 'bl',]
            )
            base._draw_kline(context=context, extends_name2=open_type_str)
    elif execrpt.side == OrderSide_Sell:  # 卖出
        logger.info('【顺开空】成交，成交价格：%s，时间：%s' % (execrpt.price, data_now))
        if context._draw:  # 画图
            open_type_str = '顺开空'
            context._draw_points.append(
                [data_now, open_type_str, data_now, execrpt.price, 'bs',]
            )
            base._draw_kline(context=context, extends_name2=open_type_str)
    else:
        raise Exception('Mars Area 【开仓成交】')
    logger.info('【开仓】【完成】>>>')


def __on_execution_report_trade_close(context, execrpt):
    '''
    平仓成交
    '''
    logger.info('【平仓】【成交】<<<')
    context._fund_cost_price = np.nan
    data_now = base._get_last_data(context)['data_now']
    if execrpt.side == OrderSide_Buy:  # 买入(平空)
        if context._draw:  # 画图
            context._draw_points.append(
                [data_now, '平空', data_now, execrpt.price, 'ss',]
            )
            base._draw_kline(context=context, extends_name2='sell_short')
    elif execrpt.side == OrderSide_Sell:  # 卖出(平多)
        if context._draw:  # 画图
            context._draw_points.append(
                [data_now, '平多', data_now, execrpt.price, 'sl',]
            )
            base._draw_kline(context=context, extends_name2='sell long')
    else:
        raise Exception('Mars Area 【平仓成交】')

    logger.info('【平仓】【完成】<<<')
    logger.info('<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


def __clear_all_position(context):
    '''
    清仓
    '''
    pass


def on_execution_report(context, execrpt):
    '''
    委托执行回报事件
    - 响应委托被执行事件，委托成交后被触发。
    '''
    base._on_execution_report_pre(context=context, execrpt=execrpt)
    if execrpt.exec_type == ExecType_Trade:  # 成交
        if execrpt.position_effect == PositionEffect_Open:  # 开仓
            __on_execution_report_trade_open(context, execrpt)
        elif execrpt.position_effect == PositionEffect_Close:  # 平仓
            __on_execution_report_trade_close(context, execrpt)
        else:
            logger.error('回报事件检测出【其他平仓类型】 %s' % execrpt)
    else:
        logger.error('回报事件检测出【未成交】回报 %s' % execrpt)
    base._on_execution_report_post(context=context, execrpt=execrpt)


def on_order_status(context, order):
    '''
    委托状态更新事件
    - 响应委托状态更新事件，下单后及委托状态更新时被触发。
    '''
    base._on_order_status_pre(context=context, order=order)
    #
    # 策略处理
    #
    base._on_order_status_post(context=context, order=order)


def on_account_status(context, account):
    '''
    交易账户状态更新事件
    '''
    base._on_account_status_pre(context=context, account=account)
    #
    # 策略处理
    #
    base._on_account_status_post(context=context, account=account)


def on_backtest_finished(context, indicator):
    '''
    在回测模式下，回测结束后会触发该事件，并返回回测得到的绩效指标对象
    '''
    base._on_backtest_finished(context=context, indicator=indicator)
