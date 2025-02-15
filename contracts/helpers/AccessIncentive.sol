// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {Access} from "@core/helpers/Access.sol";
import {IStorageAccess} from "@core/interfaces/IStorageAccess.sol";
import {X59} from "@core/utilities/X59.sol";
import {
  tokenIdSlot,
  getPoolDataSlot,
  readPoolData,
  getIncentiveDataSlot,
  totalEvanescentPointsOwedSlot
} from "../utilities/StorageIncentive.sol";

contract AccessIncentive is Access {
  function _readIncentiveTokenId(
    IStorageAccess incentive
  ) external view returns (
    uint256 tokenId
  ) {
    bytes32 slot = incentive.storageAccess(
      bytes32(tokenIdSlot)
    );
    assembly {
      tokenId := slot
    }
  }

  function _readPoolData(
    IStorageAccess incentive,
    uint256 poolId
  ) external view returns (
    uint32 blockNumber,
    X59 qLower,
    X59 qUpper,
    uint256 activeEvanescentPointsPerShare
  ) {
    bytes32 slot = incentive.storageAccess(
      bytes32(getPoolDataSlot(poolId))
    );
    (
      blockNumber,
      qLower,
      qUpper,
      activeEvanescentPointsPerShare
    ) = readPoolData(uint256(slot));
  }

  function _readIncentiveData(
    IStorageAccess incentive,
    uint256 tokenId
  ) external view returns (
    uint256 poolId,
    X59 qMin,
    X59 qMax,
    uint256 shares,
    uint256 evanescentPointsPerShareSubtrahend,
    uint256 evanescentPointsOwed
  ) {
    uint256 storageSlot = getIncentiveDataSlot(tokenId);
    uint256 value0 = uint256(incentive.storageAccess(bytes32(storageSlot)));
    unchecked {
      ++storageSlot;
    }
    uint256 value1 = uint256(incentive.storageAccess(bytes32(storageSlot)));
    unchecked {
      ++storageSlot;
    }
    evanescentPointsOwed = uint256(
      incentive.storageAccess(bytes32(storageSlot))
    );
    assembly {
      poolId := or(
        and(value0, shl(160, 0xFFFFFFFFFFFFFFFFFFFFFFFF)),
        incentive
      )
      evanescentPointsPerShareSubtrahend := and(
        value0,
        0xFFFFFFFFFFFFFFFFFFFFFFFF
      )

      qMin := and(shr(192, value1), 0xFFFFFFFFFFFFFFFF)
      qMax := and(shr(128, value1), 0xFFFFFFFFFFFFFFFF)
      shares := and(value1, 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF)
    }
  }

  function _readTotalEvanescentPointsOwedSlot(
    IStorageAccess incentive
  ) external view returns (
    uint256 value
  ) {
    bytes32 storageSlot = incentive.storageAccess(
      bytes32(totalEvanescentPointsOwedSlot)
    );
    assembly {
      value := storageSlot
    }
  }
}