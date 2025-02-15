# Copyright 2025, NoFeeSwap LLC - All rights reserved.
import pytest
from brownie import chain, accounts, Access, Nofeeswap, NofeeswapDelegatee, ERC20FixedSupply, Oracle, Operator, Deployer
from eth_abi import encode
from eth_abi.packed import encode_packed
from Nofee import logTest, ADD, REVERT, PUSH32, SWAP, JUMP, JUMPDEST, LT, NEG, TAKE_TOKEN, ISZERO, SYNC_TOKEN, TRANSFER_FROM_PAYER_ERC20, SETTLE, address0, mintSequence, keccak, toInt, twosComplementInt8, encodeKernelCompact, encodeCurve, getPoolId

@pytest.fixture(autouse=True)
def deployment(fn_isolation):
    root = accounts[0]
    owner = accounts[1]
    other = accounts[2]
    deployer = Deployer.deploy(root, {'from': root})
    delegatee = deployer.addressOf(1)
    nofeeswap = deployer.addressOf(2)
    deployer.create3(
        1,
        NofeeswapDelegatee.bytecode + encode(
            ['address'],
            [nofeeswap]
        ).hex(), 
        {'from': root}
    )
    deployer.create3(
        2,
        Nofeeswap.bytecode + encode(
            ['address', 'address'],
            [delegatee, root.address]
        ).hex(), 
        {'from': root}
    )
    delegatee = NofeeswapDelegatee.at(delegatee)
    nofeeswap = Nofeeswap.at(nofeeswap)
    access = Access.deploy({'from': root})
    oracle = Oracle.deploy(nofeeswap, {'from': root})
    operator = Operator.deploy(nofeeswap, address0, address0, address0, {'from': root})

    protocolGrowthPortion = (2 * (1 << 47)) // 100
    poolGrowthPortion = (1 << 47) // 100

    nofeeswap.dispatch(delegatee.modifyProtocol.encode_input(
        (poolGrowthPortion << 208) + (protocolGrowthPortion << 160) + int(root.address, 16)
    ), {'from': root})

    return root, owner, other, nofeeswap, delegatee, access, oracle, operator, poolGrowthPortion, protocolGrowthPortion

def test_oracle(deployment, request, worker_id):
    logTest(request, worker_id)
    
    root, owner, other, nofeeswap, delegatee, access, oracle, operator, poolGrowthPortion, protocolGrowthPortion = deployment

    token0 = ERC20FixedSupply.deploy("ERC20_0", "ERC20_0", 2**128, root, {'from': root})
    token1 = ERC20FixedSupply.deploy("ERC20_1", "ERC20_1", 2**128, root, {'from': root})
    token0.approve(operator, 2**128, {'from': root})
    token1.approve(operator, 2**128, {'from': root})
    if toInt(token0.address) > toInt(token1.address):
        token0, token1 = token1, token0
    tag0 = toInt(token0.address)
    tag1 = toInt(token1.address)

    qLower = 2 ** 40 + 1
    qUpper = 2 ** 40 + 1 + 2 ** 40
    qSpacing = qUpper - qLower

    kernel = [
      [0, 0],
      [2 ** 40, 2 ** 15]
    ]
    curve = [qLower, qUpper]

    logOffset = -5

    # initialization
    unsaltedPoolId = (twosComplementInt8(logOffset) << 180) + (0b00000000001000000010 << 160) + toInt(oracle.address)
    poolId = getPoolId(owner.address, unsaltedPoolId)

    deadline = 2 ** 32 - 1

    tx = nofeeswap.dispatch(
      delegatee.initialize.encode_input(
        unsaltedPoolId,
        tag0,
        tag1,
        0,
        encodeKernelCompact(kernel),
        encodeCurve(curve),
        b"HookData"
      ),
      {'from': owner}
    )

    index, length, timestamp, logPriceCumulative = oracle.lastObservation(poolId)
    assert index == 0
    assert length == 2
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == 0

    timestamp, logPriceCumulative = oracle.observation(poolId, index)
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == 0

    ##############################

    qMin = qLower - (1 << 63) + (logOffset * (1 << 59))
    qMax = qUpper - (1 << 63) + (logOffset * (1 << 59))
    shares = 1000000000000000000000000000
    tagShares = keccak(['uint256', 'int256', 'int256'], [poolId, qMin, qMax])

    amountSpecified = - (1 << 120)
    zeroForOne = 2
    hookData = b"HookData"

    successSlot = 2

    amount0Slot = 3
    amount1Slot = 4

    amount0Slot0 = 30
    amount1Slot0 = 40

    amount0Slot1 = 31
    amount1Slot1 = 41

    amount0Slot2 = 32
    amount1Slot2 = 42

    amount0Slot3 = 33
    amount1Slot3 = 43

    successSlotSync0 = 5
    successSlotSync1 = 6

    successSlotTransfer0 = 7
    successSlotTransfer1 = 8

    valueSlotSettle0 = 9
    successSlotSettle0 = 10
    resultSlotSettle0 = 11

    valueSlotSettle1 = 12
    successSlotSettle1 = 13
    resultSlotSettle1 = 14

    amountSpecifiedSlot = 15
    zeroSlot = 100
    logicSlot = 200

    limit0 = qLower + ((1 * qSpacing) // 8)
    limit1 = qLower + ((3 * qSpacing) // 8)
    limit2 = qLower + ((2 * qSpacing) // 8)
    limit3 = qLower + ((5 * qSpacing) // 8)

    sequence = [0] * 5
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, amountSpecified, amountSpecifiedSlot]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit0, zeroForOne, zeroSlot, successSlot, amount0Slot0, amount1Slot0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit1, zeroForOne, zeroSlot, successSlot, amount0Slot1, amount1Slot1, len(hookData), hookData]
    )
    sequence[3] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit2, zeroForOne, zeroSlot, successSlot, amount0Slot2, amount1Slot2, len(hookData), hookData]
    )
    sequence[4] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit3, zeroForOne, zeroSlot, successSlot, amount0Slot3, amount1Slot3, len(hookData), hookData]
    )

    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)

    tx = nofeeswap.unlock(operator, data, {'from': root})

    index, length, timestamp, logPriceCumulative = oracle.lastObservation(poolId)
    assert index == 1
    assert length == 2
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper

    timestamp, logPriceCumulative = oracle.observation(poolId, index)
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper

    ##############################

    _limit0 = qUpper - ((1 * qSpacing) // 8)
    _limit1 = qUpper - ((3 * qSpacing) // 8)
    _limit2 = qUpper - ((2 * qSpacing) // 8)
    _limit3 = qUpper - ((5 * qSpacing) // 8)

    sequence = [0] * 5
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, amountSpecified, amountSpecifiedSlot]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit0, zeroForOne, zeroSlot, successSlot, amount0Slot0, amount1Slot0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit1, zeroForOne, zeroSlot, successSlot, amount0Slot1, amount1Slot1, len(hookData), hookData]
    )
    sequence[3] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit2, zeroForOne, zeroSlot, successSlot, amount0Slot2, amount1Slot2, len(hookData), hookData]
    )
    sequence[4] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit3, zeroForOne, zeroSlot, successSlot, amount0Slot3, amount1Slot3, len(hookData), hookData]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)

    tx = nofeeswap.unlock(operator, data, {'from': root})

    index, length, timestamp, logPriceCumulative = oracle.lastObservation(poolId)
    assert index == 0
    assert length == 2
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper + limit3

    timestamp, logPriceCumulative = oracle.observation(poolId, index)
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper + limit3

    ##############################

    chain.mine()
    chain.mine()
    chain.mine()

    # grow
    tx = oracle.grow(poolId, 4)

    ##############################

    data = mintSequence(nofeeswap, token0, token1, tagShares, poolId, qMin, qMax, shares, hookData, deadline)
    tx = nofeeswap.unlock(operator, data, {'from': root})

    ##############################

    limit0_ = qLower + ((1 * qSpacing) // 16)
    limit1_ = qLower + ((3 * qSpacing) // 16)
    limit2_ = qLower + ((2 * qSpacing) // 16)
    limit3_ = qLower + ((5 * qSpacing) // 16)

    sequence = [0] * 36
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, amountSpecified, amountSpecifiedSlot]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit0_, zeroForOne, zeroSlot, successSlot, amount0Slot0, amount1Slot0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit1_, zeroForOne, zeroSlot, successSlot, amount0Slot1, amount1Slot1, len(hookData), hookData]
    )
    sequence[3] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit2_, zeroForOne, zeroSlot, successSlot, amount0Slot2, amount1Slot2, len(hookData), hookData]
    )
    sequence[4] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, limit3_, zeroForOne, zeroSlot, successSlot, amount0Slot3, amount1Slot3, len(hookData), hookData]
    )
    sequence[5] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount0Slot0, amount0Slot1, amount0Slot]
    )
    sequence[6] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount0Slot, amount0Slot2, amount0Slot]
    )
    sequence[7] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount0Slot, amount0Slot3, amount0Slot]
    )
    sequence[8] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount1Slot0, amount1Slot1, amount1Slot]
    )
    sequence[9] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount1Slot, amount1Slot2, amount1Slot]
    )
    sequence[10] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount1Slot, amount1Slot3, amount1Slot]
    )
    sequence[11] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[12] = encode_packed(
      ['uint8'],
      [REVERT]
    )
    sequence[13] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[11] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:13]]), successSlot]
    )
    sequence[14] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [LT, zeroSlot, amount0Slot, logicSlot]
    )
    sequence[15] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[16] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [NEG, amount0Slot, amount0Slot]
    )
    sequence[17] = encode_packed(
      ['uint8', 'address', 'address', 'uint8', 'uint8'],
      [TAKE_TOKEN, token0.address, root.address, amount0Slot, successSlotSettle0]
    )
    sequence[18] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[15] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:18]]), logicSlot]
    )
    sequence[19] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [ISZERO, logicSlot, logicSlot]
    )
    sequence[20] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[21] = encode_packed(
      ['uint8', 'address'],
      [SYNC_TOKEN, token0.address]
    )
    sequence[22] = encode_packed(
      ['uint8', 'address', 'uint8', 'address', 'uint8', 'uint8'],
      [TRANSFER_FROM_PAYER_ERC20, token0.address, amount0Slot, nofeeswap.address, successSlotTransfer0, 0]
    )
    sequence[23] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [SETTLE, valueSlotSettle0, successSlotSettle0, resultSlotSettle0]
    )
    sequence[24] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[20] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:24]]), logicSlot]
    )
    sequence[25] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [LT, zeroSlot, amount1Slot, logicSlot]
    )
    sequence[26] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[27] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [NEG, amount1Slot, amount1Slot]
    )
    sequence[28] = encode_packed(
      ['uint8', 'address', 'address', 'uint8', 'uint8'],
      [TAKE_TOKEN, token1.address, root.address, amount1Slot, successSlotSettle1]
    )
    sequence[29] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[26] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:29]]), logicSlot]
    )
    sequence[30] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [ISZERO, logicSlot, logicSlot]
    )
    sequence[31] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[32] = encode_packed(
      ['uint8', 'address'],
      [SYNC_TOKEN, token1.address]
    )
    sequence[33] = encode_packed(
      ['uint8', 'address', 'uint8', 'address', 'uint8', 'uint8'],
      [TRANSFER_FROM_PAYER_ERC20, token1.address, amount1Slot, nofeeswap.address, successSlotTransfer1, 0]
    )
    sequence[34] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [SETTLE, valueSlotSettle1, successSlotSettle1, resultSlotSettle1]
    )
    sequence[35] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[31] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:35]]), logicSlot]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)

    tx = nofeeswap.unlock(operator, data, {'from': root})

    index, length, timestamp, logPriceCumulative = oracle.lastObservation(poolId)
    assert index == 1
    assert length == 2
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper + limit3 + 6 * _limit3

    timestamp, logPriceCumulative = oracle.observation(poolId, index)
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper + limit3 + 6 * _limit3

    ##############################

    chain.mine()
    chain.mine()
    chain.mine()
    chain.mine()

    ##############################

    _limit0_ = qUpper - ((1 * qSpacing) // 16)
    _limit1_ = qUpper - ((3 * qSpacing) // 16)
    _limit2_ = qUpper - ((2 * qSpacing) // 16)
    _limit3_ = qUpper - ((5 * qSpacing) // 16)

    sequence = [0] * 36
    sequence[0] = encode_packed(
      ['uint8', 'int256', 'uint8'],
      [PUSH32, amountSpecified, amountSpecifiedSlot]
    )
    sequence[1] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit0_, zeroForOne, zeroSlot, successSlot, amount0Slot0, amount1Slot0, len(hookData), hookData]
    )
    sequence[2] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit1_, zeroForOne, zeroSlot, successSlot, amount0Slot1, amount1Slot1, len(hookData), hookData]
    )
    sequence[3] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit2_, zeroForOne, zeroSlot, successSlot, amount0Slot2, amount1Slot2, len(hookData), hookData]
    )
    sequence[4] = encode_packed(
      ['uint8', 'uint256', 'uint8', 'uint64', 'uint8', 'uint8', 'uint8', 'uint8', 'uint8', 'uint16', 'bytes'],
      [SWAP, poolId, amountSpecifiedSlot, _limit3_, zeroForOne, zeroSlot, successSlot, amount0Slot3, amount1Slot3, len(hookData), hookData]
    )
    sequence[5] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount0Slot0, amount0Slot1, amount0Slot]
    )
    sequence[6] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount0Slot, amount0Slot2, amount0Slot]
    )
    sequence[7] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount0Slot, amount0Slot3, amount0Slot]
    )
    sequence[8] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount1Slot0, amount1Slot1, amount1Slot]
    )
    sequence[9] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount1Slot, amount1Slot2, amount1Slot]
    )
    sequence[10] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [ADD, amount1Slot, amount1Slot3, amount1Slot]
    )
    sequence[11] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[12] = encode_packed(
      ['uint8'],
      [REVERT]
    )
    sequence[13] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[11] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:13]]), successSlot]
    )
    sequence[14] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [LT, zeroSlot, amount0Slot, logicSlot]
    )
    sequence[15] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[16] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [NEG, amount0Slot, amount0Slot]
    )
    sequence[17] = encode_packed(
      ['uint8', 'address', 'address', 'uint8', 'uint8'],
      [TAKE_TOKEN, token0.address, root.address, amount0Slot, successSlotSettle0]
    )
    sequence[18] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[15] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:18]]), logicSlot]
    )
    sequence[19] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [ISZERO, logicSlot, logicSlot]
    )
    sequence[20] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[21] = encode_packed(
      ['uint8', 'address'],
      [SYNC_TOKEN, token0.address]
    )
    sequence[22] = encode_packed(
      ['uint8', 'address', 'uint8', 'address', 'uint8', 'uint8'],
      [TRANSFER_FROM_PAYER_ERC20, token0.address, amount0Slot, nofeeswap.address, successSlotTransfer0, 0]
    )
    sequence[23] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [SETTLE, valueSlotSettle0, successSlotSettle0, resultSlotSettle0]
    )
    sequence[24] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[20] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:24]]), logicSlot]
    )
    sequence[25] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [LT, zeroSlot, amount1Slot, logicSlot]
    )
    sequence[26] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[27] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [NEG, amount1Slot, amount1Slot]
    )
    sequence[28] = encode_packed(
      ['uint8', 'address', 'address', 'uint8', 'uint8'],
      [TAKE_TOKEN, token1.address, root.address, amount1Slot, successSlotSettle1]
    )
    sequence[29] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[26] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:29]]), logicSlot]
    )
    sequence[30] = encode_packed(
      ['uint8', 'uint8', 'uint8'],
      [ISZERO, logicSlot, logicSlot]
    )
    sequence[31] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [0, 0, 0]
    )
    sequence[32] = encode_packed(
      ['uint8', 'address'],
      [SYNC_TOKEN, token1.address]
    )
    sequence[33] = encode_packed(
      ['uint8', 'address', 'uint8', 'address', 'uint8', 'uint8'],
      [TRANSFER_FROM_PAYER_ERC20, token1.address, amount1Slot, nofeeswap.address, successSlotTransfer1, 0]
    )
    sequence[34] = encode_packed(
      ['uint8', 'uint8', 'uint8', 'uint8'],
      [SETTLE, valueSlotSettle1, successSlotSettle1, resultSlotSettle1]
    )
    sequence[35] = encode_packed(
      ['uint8'],
      [JUMPDEST]
    )
    sequence[31] = encode_packed(
      ['uint8', 'uint16', 'uint8'],
      [JUMP, sum([len(action) for action in sequence[0:35]]), logicSlot]
    )
    data = encode_packed(['uint32'] + ['bytes'] * len(sequence), [deadline] + sequence)

    tx = nofeeswap.unlock(operator, data, {'from': root})

    index, length, timestamp, logPriceCumulative = oracle.lastObservation(poolId)
    assert index == 2
    assert length == 3
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper + limit3 + 6 * _limit3 + 5 * limit3_

    timestamp, logPriceCumulative = oracle.observation(poolId, index)
    assert timestamp == chain[-1].timestamp
    assert logPriceCumulative == qUpper + limit3 + 6 * _limit3 + 5 * limit3_