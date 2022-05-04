# coding=utf-8
from __future__ import print_function, absolute_import
from gm.api import *
from gm.model.storage import context
import pandas as pd
import numpy as np
import talib as ta
from datetime import datetime
import time

from simple import CzscModelEngine
from simple.czsc import Utils as czsc_utils
from simple.logger.logger import LoggerFactory
logger = LoggerFactory.getLogger(__name__)
from simple import wx_push

from czsc_demo.conf.conf import conf
import czsc_demo.strategy.myquant.code.myquant_base_strategy_stock_demo as base


token = conf['myquant']['token']
serv_addr = conf['myquant']['serv_addr']

_conf = conf['myquant']['stock_selector']

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


'''
常量定义
'''


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


def init(ctx):
    algo(ctx)


def algo(ctx):
    # 获取当前时间
    # now = ctx.now
    now = time.strftime('%Y-%m-%d')
    # 获取上一个交易日
    last_day = get_previous_trading_date(exchange='SHSE', date=now)
    logger.info('开始筛选结构 交易日 %s' % last_day)
    ctx.stock1 = get_history_constituents(index='SHSE.000001', start_date=last_day, end_date=last_day)[0]['constituents'].keys()
    ctx.stock2 = get_history_constituents(index='SZSE.399001', start_date=last_day, end_date=last_day)[0]['constituents'].keys()
    ctx.stock3 = get_history_constituents(index='SZSE.399006', start_date=last_day, end_date=last_day)[0]['constituents'].keys()
    ctx.stock = list(ctx.stock1)
    ctx.stock.extend(list(ctx.stock2))
    ctx.stock.extend(list(ctx.stock3))


    # 获取当天有交易的股票
    not_suspended_info = get_history_instruments(symbols=ctx.stock, start_date=last_day, end_date=last_day)
    not_suspended_symbols = [item['symbol'] for item in not_suspended_info if not item['is_suspended']]

    if not not_suspended_symbols:
        logger.info('没有当日交易的待选股票')
        return

    stocks = get_fundamentals(
        table='trading_derivative_indicator',
        start_date=last_day,
        end_date=last_day,
        filter='TURNRATE >= 1.5 and NEGOTIABLEMV > 10000000000',  # 换手率 流通市值
        symbols=not_suspended_symbols,
        fields='TCLOSE,TURNRATE,NEGOTIABLEMV',
        df=True,
    )

    selected_symbols = []
    for stock in stocks['symbol'].values:
        ctx._symbol = stock
        ctx._frequency = '1d'
        history_pd = history_n(
            symbol=stock, frequency=frequency, count=600, fields='bob,eob,open,close,high,low', fill_missing=None, adjust=ADJUST_PREV, end_time=now, df=True,
        )
        # 设置k线起始时间为索引
        history_pd = history_pd.set_index('bob')
        # 初始化模型
        ctx._engine = CzscModelEngine(
            stock_code=stock,
            frequency=frequency,
            is_debug=False,
            realtime_drive_time='',
            subscribe_factors=['macd', 'xianduansanmai'],
        )
        for idx in range(history_pd.shape[0]):
            ctx._engine.k_receive(history_pd.iloc[idx : idx + 1], is_realtime=False)

        if __is_sanmai_up(ctx):  # 三买
            logger.info('%s 满足形态条件' % stock)
            base._draw_kline(context=ctx, draw_long_short_area=False, all=True, extends_name2='三买选股')
            selected_symbols.append(stock)
         
    logger.info('三买结构：%s' % selected_symbols)
    content = '# selected symbols \n\n %s' % (selected_symbols)
    wx_push('三买结构', desp=content)


def __is_sanmai_up(ctx) -> bool:
    '''
    判断当前为三买
    '''
    realtime_xianduan_df = ctx._engine.get_realtime_xianduan_df()
    last_xd = realtime_xianduan_df.iloc[-1]
    zhongshu = ctx._engine.get_realtime_zhongshu_df()
    is_zhongshusanmai = zhongshu.shape[0] > 0 and last_xd['end_point'][1] > zhongshu.iloc[-1]['top_point'][1]
    is_xianduansanmai = False
    factor_result = ctx._engine.get_factor_result()
    if 'xianduansanmai' in factor_result:  # xianduansanmai数据
        xianduansanmai_factor = factor_result['xianduansanmai']
        if len(xianduansanmai_factor) > 0 and xianduansanmai_factor[0] == 1:
            is_xianduansanmai = True
    if is_zhongshusanmai or is_xianduansanmai:  # 三买
        return True
    return False


def on_bar(ctx, bars):
    pass
