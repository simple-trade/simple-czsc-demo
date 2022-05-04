#!/bin/zsh

cd `dirname $0`
bin_dir=`pwd`
cd ..
$bin_dir/clear_html_tradelog.sh
nohup python -W ignore czsc_demo/tests/test_myquant_strategy_stock_demo.py >$bin_dir/simple.log 2>&1 & echo $! > $bin_dir/lab.pid
