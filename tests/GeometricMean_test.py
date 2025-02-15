# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
from Nofee import logTest
from brownie import accounts, GeometricMeanWrapper
from sympy import Integer, floor, sqrt

list0X216 = [((1 << k) - 1) // 5 for k in range(1, 216, 10)]
list1X216 = [((1 << 216) - 1) // 3, ((1 << 216) - 1)]

@pytest.fixture(autouse=True)
def wrapper(fn_isolation):
    return GeometricMeanWrapper.deploy({'from': accounts[0]})

@pytest.mark.parametrize('value0', list0X216 + list1X216 + [0])
@pytest.mark.parametrize('value1', list0X216 + list1X216 + [0])
def test_geometricMean(wrapper, value0, value1, request, worker_id):
    logTest(request, worker_id)
    
    tx = wrapper.geometricMeanWrapper(value0, value1)
    result = tx.return_value
    assert (result % (2 ** 256)) == (floor(sqrt(Integer(value0 * value1))) >> 104)