// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {IERC721} from "@openzeppelin/interfaces/IERC721.sol";
import {IERC721Permit_v4} from "@uniswap/interfaces/IERC721Permit_v4.sol";
import {IEIP712_v4} from "@uniswap/interfaces/IEIP712_v4.sol";
import {IMulticall_v4} from "@uniswap/interfaces/IMulticall_v4.sol";
import {IUnorderedNonce} from "@uniswap/interfaces/IUnorderedNonce.sol";
import {INofee} from "@governance/interfaces/INofee.sol";
import {IHook} from "@core/interfaces/IHook.sol";
import {IOperator} from "@operator/interfaces/IOperator.sol";
import {Tag} from "@core/utilities/Tag.sol";
import {X59} from "@core/utilities/X59.sol";
import {X111} from "@core/utilities/X111.sol";
import {IIncentivePoolFactory} from "./IIncentivePoolFactory.sol";

/// @notice Interface for the Incentive hook contract.
interface IIncentive is
  IHook,
  IOperator,
  IERC721Permit_v4,
  IEIP712_v4,
  IMulticall_v4,
  IUnorderedNonce
{
  /// @notice Thrown when the number shares to be burned exceed the existing 
  /// number of shares.
  error InsufficientShares(uint256 tokenId);

  /// @notice Thrown when attempting to modify the number of shares for an
  /// incentive position with a wrong 'poolId'.
  error InvalidPoolId(uint256 poolId, uint256 poolIdFromCalldata);

  /// @notice Thrown when attempting to modify the number of shares for an
  /// incentive position with a wrong 'qMin'.
  error InvalidLogPriceMin(X59 qMin, X59 qMinFromCalldata);

  /// @notice Thrown when attempting to modify the number of shares for an
  /// incentive position with a wrong 'qMax'.
  error InvalidLogPriceMax(X59 qMax, X59 qMaxFromCalldata);

  /// @notice Thrown when the given tags are not in the correct order, i.e.,
  /// 'tag0 < tag1'.
  error TagsOutOfOrder(Tag tag0, Tag tag1);

  /// @notice Thrown when the start block is not in the future.
  error InvalidStartBlock(uint32 startBlock, uint32 currentBlock);

  /// @notice Thrown when the end block is not ahead of the start block.
  error InvalidEndBlock(uint32 endBlock, uint32 startBlock);

  /// @notice Thrown when attempting to initialize a pool with incompatible
  /// flags.
  error IncompatibleFlags();

  /// @notice Thrown when any address other than 'incentivePoolFactory'
  /// attempts to create a pool.
  error InvalidFactory(address invalidFactory);

  /// @notice Thrown when 'tag0' of a subscribing pool is not in agreement with
  /// incentive's 'tag0'.
  error InvalidTag0(Tag invalidTag0);

  /// @notice Thrown when 'tag1' of a subscribing pool is not in agreement with
  /// incentive's 'tag1'.
  error InvalidTag1(Tag invalidTag1);

  /// @notice Thrown when the recipient passed by hook data is not the token 
  /// owner.
  error NotTokenOwner(address recipient);

  /// @notice IncentivePoolFactory's contract address.
  function incentivePoolFactory() external returns (IIncentivePoolFactory);

  /// @notice 'tag0' of this incentive contact.
  function tag0() external returns (Tag);

  /// @notice 'tag1' of this incentive contact.
  function tag1() external returns (Tag);

  /// @notice Holder of the reward tokens to be distributed.
  function payMaster() external returns (address);

  /// @notice ERC-20 address of the reward token to be distributed.
  function rewardToken() external returns (INofee);

  /// @notice The start block of the incentive program.
  function startBlock() external returns (uint32);

  /// @notice The end block of the incentive program.
  function endBlock() external returns (uint32);

  /// @notice No interval with growth above this value is rewarded.
  function maxIncentiveGrowth() external returns (X111);

  /// @notice Collects incentive rewards for LPs. It should be run by the NFT
  /// holder of the LP position.
  /// @param tokenId The corresponding tokenId of the incentive position.
  /// @return amount The amount of rewards collected.
  function collect(uint256 tokenId) external returns (uint256 amount);
}