// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {Index, zeroIndex, oneIndex, twoIndex} from "@core/utilities/Index.sol";
import {X59, zeroX59} from "@core/utilities/X59.sol";
import {INofeeswap} from "@core/interfaces/INofeeswap.sol";
import {IHook} from "@core/interfaces/IHook.sol";
import {BaseHook} from "@core/hooks/BaseHook.sol";
import {
  getPoolIdFromCalldata,
  getLogPriceCurrentFromCalldata
} from "@core/hooks/HookCalldata.sol";

/// @title The oracle hook gives access to the time weighted geometric mean of 
/// price (weighted arithmetic mean of logPrice) for any subscribing pool based
/// on the following formula:
/// 
///                 lastObservationBlock
///                        ---- 
///                        \
/// logPriceCumulative ==  /          (time(k) - time(k-1)) * logPrice(k)
///                        ---- 
///                   k = initialBlock
///
/// where for block 'k', 'time(k)' denotes the corresponding timestamp and
/// 'logPrice(k)' denotes the logPrice value at the end of block 'k'.
///
/// Observations are stored in an observation array. Each observation consists 
/// of the following information:
///
///  - An index
///  - The length of the observation array at the time of observation.
///  - Timestamp at the time of observation.
///  - 'logPriceCumulative' based on the above formula.
///
/// The very first slot of the observation array stores the last observation.
/// This includes the length of the array as well. Hence, one can access the
/// last observation by reading a single slot. The next slot stores observation
/// index zero and so on. Each observation is written both on the first slot and
/// the slot corresponding to its 'index' which is equal to 'index % length'.
/// 
/// Any address can pay the gas to expand the observation array for any pool.
/// The corresponding slots are then populated and the length of the observation 
/// array increases once per each observation until it reaches the end of the 
/// expanded array.
contract Oracle is BaseHook {
  /// @notice Thrown when attempting to access functionalities that are only
  /// available to Nofeeswap contract.
  error OnlyByNofeeswap(address attemptingAddress);

  /// @notice Thrown when attempting to initialize a pool with incompatible
  /// flags.
  error IncompatibleFlags();

  INofeeswap public immutable nofeeswap;

  constructor(INofeeswap _nofeeswap) {
    nofeeswap = _nofeeswap;
  }

  modifier onlyNofeeswap() {
    require(INofeeswap(msg.sender) == nofeeswap, OnlyByNofeeswap(msg.sender));
    _;
  }

  // uint128(uint256(keccak256("observationsSlot")));
  uint128 constant observationsSlot = 0x37991133182A66F5F9569C3640EF1A11;

  /// @notice Reads the most recent oracle observation from storage.
  /// @param poolId The corresponding poolId.
  /// @return index The index of the last observation.
  /// @return length The total length of the observation array.
  /// @return blockTimeStamp Timestamp associated with the last observation.
  /// @return logPriceCumulative The cumulative logPrice value.
  function lastObservation(
    uint256 poolId
  ) external view returns (
    Index index,
    Index length,
    uint32 blockTimeStamp,
    X59 logPriceCumulative
  ) {
    return _readLastObservation(_getLastObservationSlot(poolId));
  }

  /// @notice Reads the oracle observation corresponding to the given index.
  /// @param poolId The corresponding poolId.
  /// @param index The corresponding index.
  /// @return blockTimeStamp Timestamp associated with this observation.
  /// @return logPriceCumulative The cumulative logPrice value.
  function observation(
    uint256 poolId,
    Index index
  ) external view returns (
    uint32 blockTimeStamp,
    X59 logPriceCumulative
  ) {
    return _readObservation(_getLastObservationSlot(poolId), index);
  }

  /// @notice Expands the observation array.
  /// @param poolId The corresponding poolId.
  /// @param newLength The new length for the observation array.
  function grow(
    uint256 poolId,
    Index newLength
  ) external {
    uint256 lastObservationSlot = _getLastObservationSlot(poolId);
    ( , Index length, , ) = _readLastObservation(lastObservationSlot);
    if (length != zeroIndex) {
      while (length < newLength) {
        length = length + oneIndex;
        // A placeholder is used to populate all of the new slots.
        assembly ("memory-safe") {
          sstore(add(lastObservationSlot, length), not(0))
        }
      }
    }
  }

  /// @notice Called post initialization.
  function postInitialize(
    bytes calldata hookInput
  ) external override onlyNofeeswap returns (bytes4) {
    // Among the first 17 flags, subscribing pools may only have the
    // 'mid swap' and 'post initialize' flags activated.
    require(
      (getPoolIdFromCalldata() >> 160) & 0x1FFFF == 0x202,
      IncompatibleFlags()
    );
    
    // The very first observation is written.
    _writeObservation(
      _getLastObservationSlot(getPoolIdFromCalldata()),
      zeroIndex,
      twoIndex,
      uint32(block.timestamp),
      zeroX59
    );
    return IHook.postInitialize.selector;
  }

  /// @notice Called mid each swap.
  function midSwap(
    bytes calldata hookInput
  ) external override onlyNofeeswap returns (bytes4) {
    // A new observation is written if this is the first swap in this block.
    _update(getLogPriceCurrentFromCalldata());
    return IHook.midSwap.selector;
  }

  /// @notice Calculates the last observation storage pointer.
  function _getLastObservationSlot(
    uint256 poolId
  ) private pure returns (
    uint256 storageSlot
  ) {
    assembly ("memory-safe") {
      mstore(0, shl(128, observationsSlot))
      mstore(16, poolId)
      storageSlot := keccak256(0, 48)
    }
  }

  /// @notice Decodes the values stored in the last observation slot.
  function _readLastObservation(
    uint256 lastObservationSlot
  ) private view returns (
    Index index,
    Index length,
    uint32 blockTimeStamp,
    X59 logPriceCumulative
  ) {
    assembly ("memory-safe") {
      let observation := sload(lastObservationSlot)
      index := shr(240, observation)
      length := and(shr(224, observation), 0xFFFF)
      blockTimeStamp := and(shr(192, observation), 0xFFFFFFFF)
      logPriceCumulative := and(
        observation,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
      )
    }
  }

  /// @notice Decodes the values stored in the observation slot associated with
  /// the given index.
  function _readObservation(
    uint256 lastObservationSlot,
    Index index
  ) private view returns (
    uint32 blockTimeStamp,
    X59 logPriceCumulative
  ) {
    assembly ("memory-safe") {
      let observation := sload(add(lastObservationSlot, add(index, 1)))
      blockTimeStamp := and(shr(192, observation), 0xFFFFFFFF)
      logPriceCumulative := and(
        observation,
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF
      )
    }
  }

  /// @notice Writes a new observation in the 'lastObservationSlot' and stores
  /// a copy in the slot corresponding to the given index as well.
  function _writeObservation(
    uint256 lastObservationSlot,
    Index index,
    Index length,
    uint32 blockTimeStamp,
    X59 logPriceCumulative
  ) private {
    assembly ("memory-safe") {
      let content := or(
        shl(240, index),
        or(
          shl(224, length),
          or(shl(192, blockTimeStamp), logPriceCumulative)
        )
      )
      sstore(lastObservationSlot, content)
      sstore(add(lastObservationSlot, add(index, 1)), content)
    }
  }

  /// @notice Updates the last observation if necessary.
  function _update(
    X59 logPrice
  ) private {
    uint256 lastObservationSlot = _getLastObservationSlot(
      getPoolIdFromCalldata()
    );
    (
      Index index,
      Index length,
      uint32 blockTimeStamp,
      X59 logPriceCumulative
    ) = _readLastObservation(lastObservationSlot);

    uint32 timeDelta = uint32(block.timestamp) - blockTimeStamp;
    
    // If we are at the beginning of a new block, a new observation is needed.
    if (timeDelta != 0) {
      // 'logPriceCumulative' is incremented.
      assembly ("memory-safe") {
        logPriceCumulative := add(
          logPriceCumulative,
          mul(logPrice, timeDelta)
        )
      }
      index = index + oneIndex;

      // In this case, we have not reached the end of the observation array yet.
      if (index < length) {
        _writeObservation(
          lastObservationSlot,
          index,
          length,
          uint32(block.timestamp),
          logPriceCumulative
        );
      // In this case, we are at the end of the observation array.
      } else {
        (uint32 placeHolder, ) = _readObservation(
          lastObservationSlot,
          index
        );
        // In this case, the observation array is expanded.
        if (placeHolder != 0) {
          _writeObservation(
            lastObservationSlot,
            index,
            length + oneIndex,
            uint32(block.timestamp),
            logPriceCumulative
          );
        // In this case, we need to go back to the beginning of the array.
        } else {
          _writeObservation(
            lastObservationSlot,
            zeroIndex,
            length,
            uint32(block.timestamp),
            logPriceCumulative
          );
        }
      }
    }
  }
}