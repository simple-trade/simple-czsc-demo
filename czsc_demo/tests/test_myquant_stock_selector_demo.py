# -*- encoding: utf-8 -*-

import sys
import os

filepath = os.path.dirname(__file__)
root = os.path.abspath(os.path.join(filepath, '../..'))
sys.path.append(root)
import unittest
from czsc_demo.strategy.myquant.selector.stock_selector_demo import _run


class Tester(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def testDriver(self):
        _run()


if __name__ == '__main__':
    # verbosity=*：默认是1；设为0，则不输出每一个用例的执行结果；2-输出详细的执行结果
    unittest.main(verbosity=1)
