# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
from brownie import accounts, StorageIncentiveWrapper
from Nofee import logTest, toInt, keccak256, keccakPacked

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

@pytest.mark.parametrize('tokenId', [value0, value2, value4])
@pytest.mark.parametrize('content0', [value0, value1, value2, value3, value4])
@pytest.mark.parametrize('content1', [value0, value1, value2, value3, value4])
@pytest.mark.parametrize('content2', [value0, value1, value2, value3, value4])
@pytest.mark.parametrize('value', [value0, value1, value2, value3, value4])
def test_collectEvanescentPoints(wrapper, tokenId, content0, content1, content2, value, request, worker_id):
    logTest(request, worker_id)
    
    # Check if the incentive points are collected correctly.
    poolId = ((content0 >> 160) << 160) + toInt(wrapper.address)
    evanescentPointsPerShareSubtrahend = content0 % (1 << 96)
    qMin = (content1 >> 192)
    qMax = (content1 >> 128) % (1 << 64)
    shares = content1 % (1 << 128)
    
    blockNumber = value >> 224
    qLower = (value >> 160) % (1 << 64)
    qUpper = (value >> 96) % (1 << 64)
    activeEvanescentPointsPerShare = value % (1 << 96)
    if qLower != qUpper:
        pointsMinSlot = keccakPacked(['uint256', 'uint64', 'uint64'], [poolId, qMin, (keccak256('evanescentPointsPerShareMapping') - 1) % (1 << 64)])
        pointsMaxSlot = keccakPacked(['uint256', 'uint64', 'uint64'], [poolId, qMax, (keccak256('evanescentPointsPerShareMapping') - 1) % (1 << 64)])
        pointsLowerSlot = keccakPacked(['uint256', 'uint64', 'uint64'], [poolId, qLower, (keccak256('evanescentPointsPerShareMapping') - 1) % (1 << 64)])
        pointsUpperSlot = keccakPacked(['uint256', 'uint64', 'uint64'], [poolId, qUpper, (keccak256('evanescentPointsPerShareMapping') - 1) % (1 << 64)])

        points0 = (value >> 160) >> 1
        points1 = (value % (1 << 96)) >> 1
        points2 = (content0 >> 160) >> 1
        points3 = (content0 % (1 << 96)) >> 1

        if (qUpper <= qMin):
            contents = [max(points0, points1), min(points0, points1), 0, 0]
            evanescentPointsPerShare = max(points0, points1) - min(points0, points1)
        elif (qMax <= qLower):
            contents = [min(points0, points1), max(points0, points1), 0, 0]
            evanescentPointsPerShare = max(points0, points1) - min(points0, points1)
        else:
            contents = [min(points0, points1), min(points2, points3), max(points0, points1), max(points2, points3)]
            evanescentPointsPerShare = activeEvanescentPointsPerShare + max(points0, points1) + max(points2, points3) - min(points0, points1) - min(points2, points3)

        tx = wrapper._collectEvanescentPoints(
            tokenId,
            content0,
            content1,
            content2,
            value,
            [pointsMinSlot, pointsMaxSlot, pointsLowerSlot, pointsUpperSlot],
            contents
        )
        evanescentPointsOwed, content0New, content1New, content2New = tx.return_value

        assert content0New == ((content0 >> 96) << 96) + evanescentPointsPerShare
        assert content1New == content1
        assert content2New == 0
        if (content2 + shares * (evanescentPointsPerShare - evanescentPointsPerShareSubtrahend) >= 0):
            assert evanescentPointsOwed == content2 + shares * (evanescentPointsPerShare - evanescentPointsPerShareSubtrahend)