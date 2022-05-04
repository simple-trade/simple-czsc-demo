#!/bin/zsh
cd `dirname $0`
bin_dir=`pwd`

labpid=`sed -n '1p' $bin_dir/lab.pid`

kill -9 $labpid
echo "killed $labpid"
