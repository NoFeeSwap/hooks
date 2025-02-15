// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {readStorage, writeStorage} from "@core/utilities/Storage.sol";
import {X59} from "@core/utilities/X59.sol";
import {IIncentive} from "../interfaces/IIncentive.sol";
import {
  getPoolIdFromCalldata,
  getLogPriceMinOffsettedFromCalldata,
  getLogPriceMaxOffsettedFromCalldata
} from "@core/hooks/HookCalldata.sol";

////////////////////////////////////////////////////////////////// tokenId slot

// uint256(keccak256("tokenId")) - 1
uint256 constant tokenIdSlot = 
  0x53DC9BF46BEBDCA9BE947EE80674B58899973AAC1948A8396714431DA6D4F166;

/// @notice Increments 'tokenId' by '1'.
/// @return tokenId The value prior to being incremented.
function incrementTokenId() returns (
  uint256 tokenId
) {
  assembly {
    tokenId := sload(tokenIdSlot)
    sstore(tokenIdSlot, add(tokenId, 1))
  }
}

//////////////////////////////////////////// total evanescent points owed slots

// uint256(keccak256("totalEvanescentPointsOwed")) - 1
uint256 constant totalEvanescentPointsOwedSlot = 
  0x15DDCE81810DC72EA0A787EE057ABA4C00DC9587828A137DDB1AF46D6B42C9B6;

/// @notice Increments 'totalEvanescentPointsOwed' for all subscribing pools.
/// @param increment The increment to be added.
function updateTotalEvanescentPointsOwed(
  uint256 increment
) {
  writeStorage(
    totalEvanescentPointsOwedSlot,
    readStorage(totalEvanescentPointsOwedSlot) + increment
  );
}

/////////////////////////////////////////////////////////////// pool data slots

// uint128(uint256(keccak256("poolData"))) - 1
uint128 constant poolDataSlot = 0x739010B57B0DE36D3FD2252EB66D6A12;

/// @notice Calculates 'poolDataSlot'.
/// @param poolId The poolId whose corresponding slot to be calculated.
/// @return storageSlot The resulting slot in storage.
function getPoolDataSlot(
  uint256 poolId
) pure returns (
  uint256 storageSlot
) {
  assembly {
    // We populate the first two memory slots from right to left:
    //
    //    0                             32             48
    //    |                             |              |
    //    +-----------------------------+--------------+
    //    |            poolId           | poolDataSlot |
    //    +-----------------------------+--------------+
    //

    // Populates the most signifacnt 16 bytes of the memory slot 1.
    mstore(16, poolDataSlot) // 16 = 32 - 16

    // Populates the entire memory slot 0.
    mstore(0, poolId) // 0 = 32 - 32

    // Caculates the resulting hash.
    storageSlot := keccak256(0, 48)
  }
}

/// @notice Decodes pool data from the content of 'storageSlot'.
/// @param value Output of 'readStorage(getPoolDataSlot(poolId))'.
/// @return blockNumber Last block number where pool is touched.
/// @return qLower Most recent 'qLower' boundary of the active interval.
/// @return qUpper Most recent 'qUpper' boundary of the active interval.
/// @return activeEvanescentPointsPerShare Evanescent points per share for the
/// active interval.
function readPoolData(
  uint256 value
) pure returns (
  uint32 blockNumber,
  X59 qLower,
  X59 qUpper,
  uint256 activeEvanescentPointsPerShare
) {
  //
  //      4 bytes      8 bytes     8 bytes               12 bytes
  //  +-------------+-----------+-----------+--------------------------------+
  //  | blockNumber |  qLower   |  qUpper   | activeEvanescentPointsPerShare |
  //  +-------------+-----------+-----------+--------------------------------+
  //
  assembly {
    blockNumber := shr(224, value)
    qLower := and(shr(160, value), 0xFFFFFFFFFFFFFFFF)
    qUpper := and(shr(96, value), 0xFFFFFFFFFFFFFFFF)
    activeEvanescentPointsPerShare := and(value, 0xFFFFFFFFFFFFFFFFFFFFFFFF)
  }
}

/// @notice Encodes pool data and writes it in the given 'storageSlot'.
/// @param storageSlot Output of 'getPoolDataSlot'.
/// @param blockNumber Last block number where pool is touched.
/// @param qLower Most recent 'qLower' boundary of the active interval.
/// @param qUpper Most recent 'qUpper' boundary of the active interval.
/// @param activeEvanescentPointsPerShare Evanescent points per share for the
/// active interval.
function writePoolData(
  uint256 storageSlot,
  uint32 blockNumber,
  X59 qLower,
  X59 qUpper,
  uint256 activeEvanescentPointsPerShare
) {
  //
  //      4 bytes      8 bytes     8 bytes               12 bytes
  //  +-------------+-----------+-----------+--------------------------------+
  //  | blockNumber |  qLower   |  qUpper   | activeEvanescentPointsPerShare |
  //  +-------------+-----------+-----------+--------------------------------+
  //
  uint256 value;
  assembly {
    value := or(
      or(shl(224, blockNumber), shl(160, qLower)),
      or(shl(96, qUpper), activeEvanescentPointsPerShare)
    )
  }
  writeStorage(storageSlot, value);
}

////////////////////////////////////////////////////////// incentive data slots

// uint128(uint256(keccak256("incentiveData"))) - 1;
uint128 constant incentiveDataSlot = 0x8CC275057B673C0282CE82CEE41466B9;

/// @notice Calculates 'incentiveDataSlot' for a given 'tokenId'.
/// @param tokenId The tokenId whose corresponding slot to be calculated.
/// @return storageSlot The resulting slot in storage.
function getIncentiveDataSlot(
  uint256 tokenId
) pure returns (
  uint256 storageSlot
) {
  assembly {
    // We populate the first two memory slots from right to left:
    //
    //    0                              32                  48
    //    |                              |                   |
    //    +------------------------------+-------------------+
    //    |            tokenId           | incentiveDataSlot |
    //    +------------------------------+-------------------+
    //

    // Populates the most signifacnt 16 bytes of the memory slot 1.
    mstore(16, incentiveDataSlot) // 16 = 32 - 16

    // Populates the entire memory slot 0.
    mstore(0, tokenId) // 0 = 32 - 32

    // Caculates the resulting hash.
    storageSlot := keccak256(0, 48)
  }
}

/// @notice Decodes incentive data from the content of 'storageSlot'.
/// @param storageSlot Output of 'getIncentiveDataSlot'.
/// @return poolId The poolId for the corresponding position.
/// @return qMin Left boundary of the corresponding position.
/// @return qMax Right boundary of the corresponding position.
/// @return shares The number of shares per interval for the corresponding
/// position.
/// @return evanescentPointsPerShareSubtrahend evanescentPointsPerShare 
/// prior to the creation of this incentive position or the last time the
/// number of shares is modified or rewards are collected.
/// @return evanescentPointsOwed Evanescent points accrued since the creation
/// of this incentive position until the last time it is touched (collected
/// or modified).
function readIncentiveData(
  uint256 storageSlot
) view returns (
  uint256 poolId,
  X59 qMin,
  X59 qMax,
  uint256 shares,
  uint256 evanescentPointsPerShareSubtrahend,
  uint256 evanescentPointsOwed
) {
  //
  //          12 bytes        8 bytes              12 bytes
  //    +------------------+----------+------------------------------------+
  //    | poolId (96 msbs) |     -    | evanescentPointsPerShareSubtrahend |
  //    +------------------+----------+------------------------------------+
  //
  //       8 bytes    8 bytes                    16 bytes
  //    +----------+----------+--------------------------------------------+
  //    |   qMin   |   qMax   |                   shares                   |
  //    +----------+----------+--------------------------------------------+
  //
  //                                  32 bytes
  //    +------------------------------------------------------------------+
  //    |                       evanescentPointsOwed                       |
  //    +------------------------------------------------------------------+
  //
  uint256 value0 = readStorage(storageSlot);
  unchecked {
    ++storageSlot;
  }
  uint256 value1 = readStorage(storageSlot);
  unchecked {
    ++storageSlot;
  }
  evanescentPointsOwed = readStorage(storageSlot);
  assembly {
    poolId := or(and(value0, shl(160, 0xFFFFFFFFFFFFFFFFFFFFFFFF)), address())
    evanescentPointsPerShareSubtrahend := and(
      value0,
      0xFFFFFFFFFFFFFFFFFFFFFFFF
    )

    qMin := and(shr(192, value1), 0xFFFFFFFFFFFFFFFF)
    qMax := and(shr(128, value1), 0xFFFFFFFFFFFFFFFF)
    shares := and(value1, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
  }
}

/// @notice Increments or decrements shares for an incentive position.
/// @param tokenId The tokenId whose shares to be modified.
/// @param evanescentPointsPerShare The new value for 
/// 'evanescentPointsPerShare' which is used to update 'evanescentPointsOwed'.
/// @param sharesIncrement The number of shares to be added/subtracted.
function modifyIncentiveShares(
  uint256 tokenId,
  uint256 evanescentPointsPerShare,
  int256 sharesIncrement
) {
  unchecked {
    //          12 bytes        8 bytes              12 bytes
    //    +------------------+----------+------------------------------------+
    //    | poolId (96 msbs) |     -    | evanescentPointsPerShareSubtrahend |
    //    +------------------+----------+------------------------------------+
    //
    uint256 storageSlot = getIncentiveDataSlot(tokenId);
    uint256 evanescentPointsPerShareSubtrahend;
    {
      uint256 poolId;
      uint256 value = readStorage(storageSlot);
      assembly {
        poolId := or(
          and(value, shl(160, 0xFFFFFFFFFFFFFFFFFFFFFFFF)),
          address()
        )
        evanescentPointsPerShareSubtrahend := and(
          value,
          0xFFFFFFFFFFFFFFFFFFFFFFFF
        )
        value := or(
          and(value, not(0xFFFFFFFFFFFFFFFFFFFFFFFF)),
          evanescentPointsPerShare
        )
      }
      require(
        poolId == getPoolIdFromCalldata(),
        IIncentive.InvalidPoolId(poolId, getPoolIdFromCalldata())
      );
      writeStorage(storageSlot, value);
    }

    //       8 bytes    8 bytes                    16 bytes
    //    +----------+----------+--------------------------------------------+
    //    |   qMin   |   qMax   |                   shares                   |
    //    +----------+----------+--------------------------------------------+
    //
    ++storageSlot;
    int256 shares;
    {
      uint256 value = readStorage(storageSlot);
      X59 qMin;
      X59 qMax;
      assembly {
        qMin := and(shr(192, value), 0xFFFFFFFFFFFFFFFF)
        qMax := and(shr(128, value), 0xFFFFFFFFFFFFFFFF)
        shares := and(value, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
      }
      require(
        qMin == getLogPriceMinOffsettedFromCalldata(),
        IIncentive.InvalidLogPriceMin(
          qMin,
          getLogPriceMinOffsettedFromCalldata()
        )
      );
      require(
        qMax == getLogPriceMaxOffsettedFromCalldata(),
        IIncentive.InvalidLogPriceMax(
          qMax,
          getLogPriceMaxOffsettedFromCalldata()
        )
      );
      int256 sharesUpdated = shares + sharesIncrement;
      require(sharesUpdated >= 0, IIncentive.InsufficientShares(tokenId));
      assembly {
        value := or(
          and(value, not(0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)),
          sharesUpdated
        )
      }
      writeStorage(storageSlot, value);
    }

    //                                  32 bytes
    //    +------------------------------------------------------------------+
    //    |                       evanescentPointsOwed                       |
    //    +------------------------------------------------------------------+
    //
    ++storageSlot;
    writeStorage(
      storageSlot,
      readStorage(storageSlot) + uint256(shares) * 
        (evanescentPointsPerShare - evanescentPointsPerShareSubtrahend)
    );
  }
}

/// @notice Increments or decrements shares for an incentive position.
/// @param tokenId The tokenId whose evanescent points to be collected.
/// @return evanescentPointsOwed The amount of evanescent points to be granted.
function collectEvanescentPoints(
  uint256 tokenId
) returns (
  uint256 evanescentPointsOwed
) {
  uint256 storageSlot = getIncentiveDataSlot(tokenId);
  unchecked {
    //       8 bytes    8 bytes                    16 bytes
    //    +----------+----------+--------------------------------------------+
    //    |   qMin   |   qMax   |                   shares                   |
    //    +----------+----------+--------------------------------------------+
    //
    uint256 value = readStorage(storageSlot + 1);
    X59 qMin;
    X59 qMax;
    uint256 shares;
    assembly {
      qMin := shr(192, value)
      qMax := and(shr(128, value), 0xFFFFFFFFFFFFFFFF)
      shares := and(value, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
    }

    //          12 bytes        8 bytes              12 bytes
    //    +------------------+----------+------------------------------------+
    //    | poolId (96 msbs) |     -    | evanescentPointsPerShareSubtrahend |
    //    +------------------+----------+------------------------------------+
    //
    value = readStorage(storageSlot);
    uint256 poolId;
    uint256 evanescentPointsPerShareSubtrahend;
    assembly {
      poolId := or(
        and(value, shl(160, 0xFFFFFFFFFFFFFFFFFFFFFFFF)),
        address()
      )
      evanescentPointsPerShareSubtrahend := and(
        value,
        0xFFFFFFFFFFFFFFFFFFFFFFFF
      )
    }
    uint256 evanescentPointsPerShare = calculateEvanescentPointsPerShare(
      poolId,
      qMin,
      qMax
    );
    assembly {
      value := or(
        and(value, not(0xFFFFFFFFFFFFFFFFFFFFFFFF)),
        evanescentPointsPerShare
      )
    }
    writeStorage(storageSlot, value);

    //                                  32 bytes
    //    +------------------------------------------------------------------+
    //    |                       evanescentPointsOwed                       |
    //    +------------------------------------------------------------------+
    //
    // All operations are safe because 
    // 'evanescentPointsPerShareSubtrahend <= evanescentPointsPerShareNew <= 
    // 2 ** 96 - 1'
    storageSlot += 2;
    evanescentPointsOwed = readStorage(storageSlot) + shares * (
      evanescentPointsPerShare - evanescentPointsPerShareSubtrahend
    );
    writeStorage(storageSlot, 0);
  }
}

/// @notice Encodes incentive data and writes them in 'storageSlot'.
/// @param storageSlot Output of 'getIncentiveDataSlot'.
/// @param poolId THe poolId for the corresponding position.
/// @param qMin Left boundary of the corresponding position.
/// @param qMax Right boundary of the corresponding position.
/// @param shares The number of shares for the corresponding position.
/// @param evanescentPointsPerShareSubtrahend evanescent points per share at
/// the time when this position is created or the last time it is touched.
/// @param evanescentPointsOwed Evanescent points accrued since the creation of
/// this incentive position until the last time it is touched. Collect and 
/// modify position affect this value.
/// At any moment, the total number of evanescent points owed to this position
/// is equal to:
/// 'evanescentPointsOwed + shares * 
/// (positionEvanescentPointsPerShare - evanescentPointsPerShareSubtrahend)'
function writeIncentiveData(
  uint256 storageSlot,
  uint256 poolId,
  X59 qMin,
  X59 qMax,
  uint256 shares,
  uint256 evanescentPointsPerShareSubtrahend,
  uint256 evanescentPointsOwed
) {
  //
  //          12 bytes        8 bytes              12 bytes
  //    +------------------+----------+------------------------------------+
  //    | poolId (96 msbs) |     -    | evanescentPointsPerShareSubtrahend |
  //    +------------------+----------+------------------------------------+
  //
  //       8 bytes    8 bytes                    16 bytes
  //    +----------+----------+--------------------------------------------+
  //    |   qMin   |   qMax   |                   shares                   |
  //    +----------+----------+--------------------------------------------+
  //
  //                                  32 bytes
  //    +------------------------------------------------------------------+
  //    |                       evanescentPointsOwed                       |
  //    +------------------------------------------------------------------+
  //

  uint256 value0;
  uint256 value1;
  assembly {
    value0 := or(
      and(poolId, shl(160, 0xFFFFFFFFFFFFFFFFFFFFFFFF)),
      evanescentPointsPerShareSubtrahend
    )
    value1 := or(or(shl(192, qMin), shl(128, qMax)), shares)
  }
  writeStorage(storageSlot, value0);
  unchecked {
    ++storageSlot;
  }
  writeStorage(storageSlot, value1);
  unchecked {
    ++storageSlot;
  }
  writeStorage(storageSlot, evanescentPointsOwed);
}

///////////////////////////////////// Evanescent points per share mapping slots

// uint64(uint256(keccak256("evanescentPointsPerShareMapping"))) - 1;
uint64 constant evanescentPointsPerShareMappingSlot = 0x194AD8FB35443B37;

/// @notice Gives access to 'evanescentPointsPerShareMapping'. For every spaced 
/// 'logPrice <= qLower' the value of 
/// 'evanescentPointsPerShareMapping(logPrice)' is equal to total evanescent
/// points per a single share for a position from '-oo' to 
/// 'logPrice'. Similarly, for every spaced 'qUpper <= logPrice' the value of
/// 'evanescentPointsPerShareMapping(logPrice) is equal to total evanescent 
/// points per a single share for a position from 'logPrice' to '+oo'.
/// @param poolId The corresponding poolId.
/// @param logPrice The corresponding logPrice.
/// @return storageSlot The storage slot containing
/// 'getEvanescentPointsPerShareMapping(poolId, logPrice)'.
function getEvanescentPointsPerShareMappingSlot(
  uint256 poolId,
  X59 logPrice
) pure returns (
  uint256 storageSlot
) {
  assembly {
    // We populate the first two memory slots from right to left:
    //
    //    0        32         40                                    48
    //    |        |          |                                     |
    //    +--------+----------+-------------------------------------+
    //    | poolId | logPrice | evanescentPointsPerShareMappingSlot |
    //    +--------+----------+-------------------------------------+
    //

    // Populates bytes 40 to 48 of memory.
    mstore(16, evanescentPointsPerShareMappingSlot) // 16 = 48 - 32

    // Populates bytes 32 to 40 of memory.
    mstore(8, logPrice) // 8 = 40 - 32

    // Populates the entire memory slot 0.
    mstore(0, poolId) // 0 = 32 - 32

    // Caculates the resulting hash.
    storageSlot := keccak256(0, 48)
  }
}

/// @notice Given a liquidity range, this function calculates the amount of
/// evanescent points per a single share within the range.
function calculateEvanescentPointsPerShare(
  uint256 poolId,
  X59 qMin,
  X59 qMax
) view returns (
  uint256 evanescentPointsPerShare
) {
  uint256 storageSlot = getPoolDataSlot(poolId);
  (
    ,
    X59 lower,
    X59 upper,
    uint256 activeEvanescentPointsPerShare
  ) = readPoolData(readStorage(storageSlot));

  uint256 pointsMin = readStorage(
    getEvanescentPointsPerShareMappingSlot(poolId, qMin)
  );
  uint256 pointsMax = readStorage(
    getEvanescentPointsPerShareMappingSlot(poolId, qMax)
  );

  unchecked {
    // In this case, the active interval is behind the given range.
    if (upper <= qMin) {
      // The subtraction is safe because the number of points from
      // 'logPriceMinOffsetted' to '+infinity' is greater than or equal to
      // the number of points from 'logPriceMaxOffsetted' to '+infinity'.
      evanescentPointsPerShare = pointsMin - pointsMax;

    // In this case, the active interval is ahead of the given range.
    } else if (qMax <= lower) {
      // The subtraction is safe because the number of points from
      // '-infinity' to 'logPriceMaxOffsetted' is greater than or equal to
      // the number of points from '-infinity' to 'logPriceMinOffsetted'.
      evanescentPointsPerShare = pointsMax - pointsMin;

    // In this case, the active interval is within the given range.
    } else {
      // The subtractions are safe because: 
      // - the number of points from '-infinity' to 'lower' is greater than
      //   or equal to the number of points from '-infinity' to 
      //   'logPriceMinOffsetted'.
      // - the number of points from 'upper' to '+infinity' is greater than
      //   or equal to the number of points from 'logPriceMaxOffsetted' to 
      //   '+infinity'.
      // - Additionally, the total number of points per share is capped by
      //   'totalEvanescentPointsOwed'.
      evanescentPointsPerShare = 
        activeEvanescentPointsPerShare + readStorage(
          getEvanescentPointsPerShareMappingSlot(poolId, upper)
        ) - pointsMax + readStorage(
          getEvanescentPointsPerShareMappingSlot(poolId, lower)
        ) - pointsMin;
    }     
  }
}