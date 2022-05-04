from gm.api import *

import pandas as pd

from simple import KdrawGrid
from simple import KdrawRealtimeMultiPeriod
from simple import LoggerFactory
logger = LoggerFactory.getLogger(__name__)

from czsc_demo.conf.conf import conf

def _draw_kline(context, html_path=conf['path.output.html'], extends_name2='', all: bool = False, draw_long_short_area=True, slice_len=1000):
    '''
    画单个k线图
    '''
    (
        hebing_df,
        fenxing_df,
        fenbi_df,
        xianduan_df,
        zhongshu_df,
        realtime_fenbi_df,
        realtime_xianduan_df,
        realtime_zhongshu_df,
    ) = context._engine.get_containers()
    klines = context._engine.get_klines()

    factor_result = context._engine.get_factor_result()
    if 'macd' in factor_result:  # macd数据
        macd_dic = factor_result['macd']
        klines_copy = pd.concat([klines, macd_dic['macd_df']], axis=1)
        macd_normalized_df = macd_dic['normalized_df']
    else:
        klines_copy = klines.copy(deep=True)
        macd_normalized_df = None

    if all:
        start_idx1 = None
    else:
        if klines_copy.shape[0] > slice_len:
            start_idx1 = klines_copy.iloc[-slice_len:,].index[0]  # 只画进1000根k线
        else:
            start_idx1 = None
    if hasattr(context, '_rsch_reverse_points'):
        rsch_reverse_points = context._rsch_reverse_points
    else:
        rsch_reverse_points = []

    factor_result = context._engine.get_factor_result()
    if 'ma' in factor_result:  # macd数据
        ma_dic = factor_result['ma']
        ma_df = ma_dic['ma_df']
    else:
        ma_df = None
    if hasattr(context, '_draw_target_point'):
        draw_target_point = context._draw_target_point
    else:
        draw_target_point = []
    if not hasattr(context, '_draw_points'):
        context._draw_points = []

    grid1 = KdrawGrid(
        title='%s-%s' % (context._symbol, context._frequency),
        data_df=klines_copy,
        fb_df=realtime_fenbi_df,
        xd_df=realtime_xianduan_df,
        zs_df=realtime_zhongshu_df,
        macd_or_natr='macd',
        grid_width='2400px',
        grid_height='1200px',
        points=context._draw_points,
        start_idx=start_idx1,
        long_short_range={},
        xd_reverse_points=rsch_reverse_points,
        xd_forward_points=[],
        macd_normalized_df=macd_normalized_df,
        target_point=draw_target_point,
        ma_df=ma_df,
    ).get_grid()

    extends_name = '%s-%s-%s' % (context._frequency, klines_copy.index[-1], extends_name2,)
    KdrawRealtimeMultiPeriod(base_name=context._symbol, html_path=html_path, extends_name=extends_name, grids=[grid1],).gen_html()


def _open_short_forward_4_bar_backtest(context, target_price, dynamic_volumes=False):
    '''
    顺开空
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')

    # 取最新价格
    last_data = _get_last_data(context)
    last_low = last_data['last_low']
    if last_low <= target_price:
        logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        logger.info('【顺开空】【委托】 %s >>>' % context.now)
        last_open = last_data['last_open']
        limit_price = max(last_low, min(last_open, target_price)) - context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('bar回测【顺开空】【限价】【下单】， 限价：%s' % (limit_price))
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Sell,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Open,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【顺开空】报单信息：%s' % order)


def _open_long_forward_4_bar_backtest(context, target_price, dynamic_volumes=False):
    '''
    顺开多
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')

    # 取最新价格
    last_data = _get_last_data(context)
    last_high = last_data['last_high']
    if last_high >= target_price:
        logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        logger.info('【顺开多】【委托】 %s >>>' % context.now)
        last_open = last_data['last_open']
        limit_price = min(last_high, max(last_open, target_price)) + context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('bar回测【顺开多】【限价】【下单】，限价：%s' % limit_price)
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Buy,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Open,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【顺开多】报单信息：%s' % order)


def _close_long_forward_4_bar_backtest(context, target_price):
    '''
    顺平多
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')
    # 取最新价格
    last_data = _get_last_data(context)
    last_low = last_data['last_low']
    if last_low <= target_price:
        last_open = last_data['last_open']
        limit_price = max(last_low, min(last_open, target_price)) - context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('【顺平多】【委托】 %s <<<' % context.now)
        logger.info('bar回测【顺平多】【限价】【下单】，限价：%s' % limit_price)
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Sell,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Close,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【顺平多】报单信息：%s' % order)


def _close_short_forward_4_bar_backtest(context, target_price):
    '''
    顺平空
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')

    # 取最新价格
    last_data = _get_last_data(context)
    last_high = last_data['last_high']
    if last_high >= target_price:
        last_open = last_data['last_open']
        limit_price = min(last_high, max(last_open, target_price)) + context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('【顺平空】【委托】 %s <<<' % context.now)
        logger.info('bar回测【顺平空】【限价】【下单】， 限价：%s' % limit_price)
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Buy,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Close,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【顺平空】报单信息：%s' % order)


def _open_short_reverse_4_bar_backtest(context, target_price, dynamic_volumes=False):
    '''
    逆开空
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')

    # 取最新价格
    last_data = _get_last_data(context)
    last_high = last_data['last_high']
    if last_high >= target_price:
        logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        logger.info('【逆开空】【委托】 %s >>>' % context.now)
        last_open = last_data['last_open']
        limit_price = min(last_high, max(last_open, target_price)) - context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('bar回测【逆开空】【限价】【下单】，限价：%s' % limit_price)
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Sell,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Open,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【逆开空】报单信息：%s' % order)


def _open_long_reverse_4_bar_backtest(context, target_price, dynamic_volumes=False):
    '''
    逆开多
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')

    # 取最新价格
    last_data = _get_last_data(context)
    last_low = last_data['last_low']
    if last_low <= target_price:
        logger.info('>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
        logger.info('【逆开多】【委托】 %s >>>' % context.now)
        last_open = last_data['last_open']
        limit_price = max(last_low, min(last_open, target_price)) + context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('bar回测【逆开多】【限价】【下单】， 限价：%s' % (limit_price))
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Buy,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Open,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【逆开多】报单信息：%s' % order)


def _close_long_reverse_4_bar_backtest(context, target_price):
    '''
    逆平多
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')

    # 取最新价格
    last_data = _get_last_data(context)
    last_high = last_data['last_high']
    if last_high >= target_price:
        logger.info('【逆平多】【委托】 %s <<<' % context.now)
        last_open = last_data['last_open']
        limit_price = min(last_high, max(last_open, target_price)) - context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('bar回测【逆平多】【限价】【下单】，限价：%s' % limit_price)
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Sell,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Close,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【逆平多】报单信息：%s' % order)


def _close_short_reverse_4_bar_backtest(context, target_price):
    '''
    逆平空
    - 适用范围：
        - bar回测
    '''
    if context._mode == MODE_LIVE:
        raise Exception('下单调用与运行模式不匹配')

    # 取最新价格
    last_data = _get_last_data(context)
    last_low = last_data['last_low']
    if last_low <= target_price:
        logger.info('【逆平空】【委托】 %s <<<' % context.now)
        last_open = last_data['last_open']
        limit_price = max(last_low, min(last_open, target_price)) + context._backtest_slippage * context._instrumentinfos_dic[0]['price_tick']  # 模拟滑点
        logger.info('bar回测【逆平空】【限价】【下单】，限价：%s' % limit_price)
        order = order_volume(
            symbol=context._symbol,
            volume=context._volume,
            side=OrderSide_Buy,
            order_type=OrderType_Limit,
            position_effect=PositionEffect_Close,
            price=limit_price,
            order_duration=OrderDuration_Unknown,
            order_qualifier=OrderQualifier_Unknown,
            account=context._backtest_account_id,
        )
        logger.debug('bar回测【逆平空】报单信息：%s' % order)


def _get_last_data(context):
    is_tick = context._frequency == 'tick'
    if is_tick:  # tick 数据
        datas = context.data(symbol=context._symbol, frequency=context._frequency, count=1, fields='open,high,low,created_at,price')
        data_type = 'tick'
        last_open = datas[-1].open
        last_high = datas[-1].high
        last_low = datas[-1].low
        last_price = datas[-1].price
        data_now = datas[-1].created_at
    else:
        datas = context.data(symbol=context._symbol, frequency=context._frequency, count=1, fields='open,high,low,close,eob')
        data_type = 'bar'
        last_open = datas.open.iloc[-1]
        last_high = datas.high.iloc[-1]
        last_low = datas.low.iloc[-1]
        last_price = datas.close.iloc[-1]  # bar数据把close当做最新价
        data_now = datas.eob.iloc[-1]

    return {'last_open': last_open, 'last_high': last_high, 'last_low': last_low, 'last_price': last_price, 'data_now': data_now, 'data_type': data_type}


def _on_backtest_finished(context, indicator):
    '''
    在回测模式下，回测结束后会触发该事件，并返回回测得到的绩效指标对象
    '''
    logger.info('回测完成 \n%s' % indicator)
    _draw_kline(context=context, extends_name2='all', all=True)


def _on_execution_report_pre(context, execrpt):
    '''
    委托执行回报事件
    - 响应委托被执行事件，委托成交后被触发。
    '''
    logger.debug('委托执行回报事件 -【通用前置】 %s' % execrpt)
    # TODO


def _on_execution_report_post(context, execrpt):
    '''
    委托执行回报事件
    - 响应委托被执行事件，委托成交后被触发。
    '''
    logger.debug('委托执行回报事件 -【通用后置】 %s' % execrpt)
    # TODO


def _on_order_status_pre(context, order):
    '''
    通用前置处理
    委托状态更新事件
    - 响应委托状态更新事件，下单后及委托状态更新时被触发。

    - OrderStatus_Unknown = 0
    - OrderStatus_New = 1                   # 已报
    - OrderStatus_PartiallyFilled = 2       # 部成
    - OrderStatus_Filled = 3                # 已成
    - OrderStatus_Canceled = 5              # 已撤
    - OrderStatus_PendingCancel = 6         # 待撤
    - OrderStatus_Rejected = 8              # 已拒绝
    - OrderStatus_Suspended = 9             # 挂起
    - OrderStatus_PendingNew = 10           # 待报
    - OrderStatus_Expired = 12              # 已过期

    '''
    logger.debug('委托状态更新事件-【通用前置】 %s' % order)
    if order.status == OrderStatus_Rejected:
        logger.error('订单被拒绝，策略停止 \n order: %s' % order)
        stop()
    if order.status == OrderStatus_Filled:
        pass
    else:
        raise Exception('出现未处理的委托状态 \n order: %s' % order)


def _on_order_status_post(context, order):
    '''
    通用后置处理
    委托状态更新事件
    - 响应委托状态更新事件，下单后及委托状态更新时被触发。

    - OrderStatus_Unknown = 0
    - OrderStatus_New = 1                   # 已报
    - OrderStatus_PartiallyFilled = 2       # 部成
    - OrderStatus_Filled = 3                # 已成
    - OrderStatus_Canceled = 5              # 已撤
    - OrderStatus_PendingCancel = 6         # 待撤
    - OrderStatus_Rejected = 8              # 已拒绝
    - OrderStatus_Suspended = 9             # 挂起
    - OrderStatus_PendingNew = 10           # 待报
    - OrderStatus_Expired = 12              # 已过期

    '''
    logger.debug('委托状态更新事件 -【通用后置】 %s' % order)


def _on_account_status_pre(context, account):
    '''
    前置
    交易账户状态更新事件
    '''
    logger.info('交易账户状态更新事件-【通用前置】 %s' % account)
    # TODO


def _on_account_status_post(context, account):
    '''
    后置
    交易账户状态更新事件
    '''
    logger.info('交易账户状态更新事件 -【通用后置】 %s' % account)
    # TODO
