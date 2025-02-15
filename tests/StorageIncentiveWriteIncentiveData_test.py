# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
from brownie import accounts, StorageIncentiveWrapper
from Nofee import logTest, toInt

value0 = 0x0000000000000000000000000000000000000000000000000000000000000000
value1 = 0x0000000000000000000000000000000000000000000000000000000000000001
value2 = 0xF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00F
value3 = 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
value4 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

balance0 = 0x00000000000000000000000000000000
balance1 = 0x00000000000000000000000000000001
balance2 = 0xF00FF00FF00FF00FF00FF00FF00FF00F
balance3 = 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
balance4 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
balance5 = 0 - 0x00000000000000000000000000000001
balance6 = 0 - 0xF00FF00FF00FF00FF00FF00FF00FF00F
balance7 = 0 - 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
balance8 = 0 - 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

storageSlot0 = 0x0000000000000000000000000000000000000000000000000000000000000000
storageSlot1 = 0x0000000000000000000000000000000000000000000000000000000000000001
storageSlot2 = 0xF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00FF00F
storageSlot3 = 0x8FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
storageSlot4 = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF

logPrice0 = 0x0000000000000000
logPrice1 = 0x0000000000000001
logPrice2 = 0xF00FF00FF00FF00F
logPrice3 = 0x8FFFFFFFFFFFFFFF
logPrice4 = 0xFFFFFFFFFFFFFFFF

block0 = 0x00000000
block1 = 0x40000000
block2 = 0x80000000
block3 = 0xFFFFFFFF

points0 = 0x000000000000000000000000
points1 = 0x000000000000000000000001
points2 = 0xF00FF00FF00FF00FF00FF00F
points3 = 0x8FFFFFFFFFFFFFFFFFFFFFFF
points4 = 0xFFFFFFFFFFFFFFFFFFFFFFFF

@pytest.fixture(autouse=True)
def wrapper(fn_isolation):
    return StorageIncentiveWrapper.deploy({'from': accounts[0]})

@pytest.mark.parametrize('storageSlot', [storageSlot0, storageSlot2, storageSlot4])
@pytest.mark.parametrize('content0', [value0, value2, value4])
@pytest.mark.parametrize('content1', [value0, value2, value4])
@pytest.mark.parametrize('content2', [value0, value2, value4])
def test_writeIncentiveData(wrapper, storageSlot, content0, content1, content2, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the incentive data are written correctly.
    poolId = ((content0 >> 160) << 160) + toInt(wrapper.address)
    evanescentPointsPerShareSubtrahend = content0 % (1 << 96)
    qMin = (content1 >> 192)
    qMax = (content1 >> 128) % (1 << 64)
    shares = content1 % (1 << 128)
    evanescentPointsOwed = content2

    tx = wrapper._writeIncentiveData(storageSlot, poolId, qMin, qMax, shares, evanescentPointsPerShareSubtrahend, evanescentPointsOwed)
    content0New, content1New, content2New = tx.return_value

    assert content0New == content0 & 0xFFFFFFFFFFFFFFFFFFFFFFFF0000000000000000FFFFFFFFFFFFFFFFFFFFFFFF
    assert content1New == content1
    assert content2New == content2