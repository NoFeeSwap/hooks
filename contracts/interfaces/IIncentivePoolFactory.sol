// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {IERC721} from "@openzeppelin/interfaces/IERC721.sol";
import {INofee} from "@governance/interfaces/INofee.sol";
import {IXNofee} from "@vault/interfaces/IXNofee.sol";
import {IUnlockCallback} from "@core/callback/IUnlockCallback.sol";
import {INofeeswap} from "@core/interfaces/INofeeswap.sol";
import {IHook} from "@core/interfaces/IHook.sol";
import {Tag} from "@core/utilities/Tag.sol";
import {X47} from "@core/utilities/X47.sol";

/// @notice Interface for the IncentivePoolFactory contract.
interface IIncentivePoolFactory is IUnlockCallback, IHook, IERC721 {
  /// @notice Thrown when any account other than admin attempts to access a
  /// functionality which is reserved for the admin.
  error OnlyByAdmin(address attemptingAddress, address adminAddress);
  
  /// @notice Thrown when attempting to access functionalities that are only
  /// available to Nofeeswap contract.
  error OnlyByNofeeswap(address attemptingAddress);

  /// @notice Thrown when the length of two input arrays that are supposed to
  /// be equal differ from each other.
  error UnequalLengths(uint256 length0, uint256 length1);

  /// @notice Thrown when the given tags are not in the correct order, i.e.,
  /// 'tag0 < tag1'.
  error TagsOutOfOrder(Tag tag0, Tag tag1);

  /// @notice Thrown when a given growth portion is greater than one.
  error InvalidGrowthPortion(X47 poolGrowthPortion);

  /// @notice Thrown when any caller other than 'address(this)' attempts to use
  /// this contract as locker.
  error CallerMustBeIncentivePoolFactory(address attemptingAddress);

  /// @notice Thrown when attempting set a conversion pool in 
  /// 'IncentivePoolFactory' whose tags are not nofeeToken.
  error InvalidTags(Tag tag0, Tag tag1);

  /// @notice Thrown when attempting to initialize a pool with incompatible
  /// flags.
  error IncompatibleFlags();

  /// @notice Thrown when attempting set a conversion pool which is not
  /// subscribed to the 'IncentivePoolFactory' hook.
  error InvalidConversionPool(uint256 poolId);

  /// @notice Thrown when attempting to disburse prior to the next disbursement
  /// block.
  error TooEarlyToDisburse(
    uint256 nextDisbursementBlock,
    uint256 currentBlockNumber
  );

  /// @notice Thrown when attempting to sell nofee in a pool which is closed by
  /// incentivePoolFactory.
  error PoolIsClosedForThisDirection(
    uint256 nextDisbursementBlock,
    uint256 nextBlockNumber,
    uint256 currentBlockNumber
  );

  /// @notice Emitted when a new admin is assigned.
  event NewAdmin(
    address indexed oldAdmin,
    address indexed newAdmin
  );

  /// @notice Emitted when a new pool growth portion is set by incentive pool
  /// factory.
  event NewPoolGrowthPortions(
    Tag indexed tag0,
    Tag indexed tag1,
    X47 newPoolGrowthPortion
  );

  /// @notice Emitted when a new conversion pool is set by incentive pool
  /// factory.
  event NewConversionPool(
    Tag indexed tag,
    uint256 indexed poolId
  );

  /// @notice Emitted when a new value for disburseGap is set
  /// incentivePoolFactory.
  event NewDisburseGap(
    uint256 oldDisburseGap,
    uint256 newDisburseGap
  );

  /// @notice Emitted when a new value for delay is set in
  /// incentivePoolFactory.
  event NewDelay(
    uint256 oldDelay,
    uint256 newDelay
  );
  
  /// @notice Nofeeswap's contract.
  function nofeeswap() external returns (INofeeswap);

  /// @notice ERC-20 address of the reward token to be distributed.
  function nofee() external returns (INofee);

  /// @notice The address of xNofee staking contract.
  function xNofee() external returns (IXNofee);

  /// @notice The admin of this contract who can change admin, modify pool 
  /// growth portion or switch conversion pools.
  function admin() external returns (address);

  /// @notice The number of blocks in between twe disbursements.
  function disburseGap() external returns (uint256);

  /// @notice The number of blocks for which conversion pools should be closed
  /// after each disburse.
  function delay() external returns (uint256);

  /// @notice The mapping of poolGrowthPortions for every pair of incentive
  /// tags.
  /// @param tag0 The arithmetically smaller Tag.
  /// @param tag1 The arithmetically larger Tag.
  /// @return growthPortion The resulting poolGrowthPortion.
  function poolGrowthPortion(
    Tag tag0,
    Tag tag1
  ) external returns (X47 growthPortion);

  /// @notice The mapping of pools that are used to convert tokens to nofee
  /// tokens.
  /// @param tag The tag whose conversion pool to be determined.
  /// @return poolId The arithmetically larger Tag.
  function conversionPools(Tag tag) external returns (uint256 poolId);

  /// @notice The mapping of last block number where a tag is converted and
  /// disbursed.
  /// @param tag The tag whose last disbursement block to be determined.
  /// @return blockNumber The resulting block number.
  function lastDisbursed(Tag tag) external returns (uint256 blockNumber);

  /// @notice Sets a new admin for this contract.
  /// @param admin Address of the new admin.
  function setAdmin(address admin) external;

  /// @notice Sets a new value for 'disburseGap'.
  /// @param disburseGap The new value for 'disburseGap'.
  function setDisburseGap(uint256 disburseGap) external;

  /// @notice Sets a new value for 'delay'.
  /// @param delay The new value for 'delay'.
  function setDelay(uint256 delay) external;

  /// @notice Sets new value for 'poolGrowthPortion' for each of the given pair
  /// of tags.
  /// @param tag0 An array of arithmetically smaller tags.
  /// @param tag1 An array of arithmetically larger tags.
  /// @param newPoolGrowthPortion The given values for 'poolGrowthPortion'.
  function modifyPoolGrowthPortion(
    Tag[] calldata tag0,
    Tag[] calldata tag1,
    X47[] calldata newPoolGrowthPortion
  ) external;

  /// @notice Modifies or adds conversion pools.
  /// @param poolIds The given conversion pools.
  function modifyConversionPools(uint256[] memory poolIds) external;

  /// @notice Syncs pool growth portion for previously initialized pools with
  /// the current pool growth portion of this contract.
  /// @param poolIds The pools whose poolGrowthPortion to by synced.
  function updatePoolGrowthPortion(uint256[] memory poolIds) external;

  /// @notice Initializes a pool and mints an NFT.
  ///
  /// @param unpepperedPoolId The least significant 160 bits refer to the
  /// address of the corresponding incentive hook. The next 20 bits should be
  /// compliant with the requirements of the corresponding incentive hook. The
  /// next 8 bits represent the natural logarithm of 'pOffset' which must be
  /// greater than or equal to '-89' and less than or equal to '89' in 'int8'
  /// representation (two's complement). Hence, 'pOffset' is greater than or
  /// equal to 'exp(-89)' and less than or equal to 'exp(+89)'. As will be
  /// discussed later, the price of the pool is always greater than or equal to
  ///
  ///  'pOffset * exp(- 16 + 1 / (2 ** 59))'
  ///
  /// and less than or equal to
  ///
  ///  'pOffset * exp(+ 16 - 1 / (2 ** 59))'.
  ///
  /// One candidate for 'pOffset' is the current market price at the time of
  /// initialization. Alternatively, one may input 0 as the logarithm of
  /// 'pOffset' in which case, the price range of the pool would be limited to
  /// '(exp(-16), exp(+16))'.
  /// The remaining 68 bits are derived according to the following rule:
  ///
  /// 'unchecked {
  ///     poolId = unsaltedPoolId + (
  ///        keccak256(
  ///           abi.encodePacked(
  ///              address(IncentivePoolFactory),
  ///              unsaltedPoolId
  ///           )
  ///        ) << 188
  ///     )
  ///  }'
  ///
  /// where
  ///
  /// 'unchecked {
  ///     unsaltedPoolId = unpepperedPoolId + (
  ///        keccak256(abi.encodePacked(msg.sender, unpepperedPoolId)) << 188
  ///     )
  ///  }'.
  ///
  /// @param kernelCompactArray For every pool, the kernel function
  /// 'k : [0, qSpacing] -> [0, 1]' represents a monotonically non-decreasing
  /// piece-wise linear function. Let 'm + 1' denote the number of these
  /// breakpoints. For every integer '0 <= i <= m' the i-th breakpoint of the
  /// kernel represents the pair '(b[i], c[i])' where
  ///
  ///  '0 == b[0] <  b[1] <= b[2] <= ... <= b[m - 1] <  b[m] == qSpacing',
  ///  '0 == c[0] <= c[1] <= c[2] <= ... <= c[m - 1] <= c[m] == 1'.
  /// 
  /// In its compact form, each breakpoint occupies 10 bytes, in which:
  ///
  ///  - the 'X15' representation of '(2 ** 15) * c[i]' occupies 2 bytes,
  ///
  ///  - the 'X59' representation of '(2 ** 59) * b[i]' occupies 8 bytes,
  ///
  /// The above-mentioned layout is illustrated as follows:
  ///
  ///          A 80 bit kernel breakpoint
  ///  +--------+--------------------------------+
  ///  | 2 byte |             8 byte             |
  ///  +--------+--------------------------------+
  ///  |        |
  ///  |         \
  ///  |          (2 ** 59) * b[i]
  ///   \
  ///    (2 ** 15) * c[i]
  ///
  /// These 80 bit breakpoints are compactly encoded in a 'uint256[]' array and
  /// given as input to 'initialize' or 'modifyKernel' methods.
  ///
  /// Consider the following examples:
  ///
  ///   - The sequence of breakpoints
  ///
  ///       '(0, 0), (qSpacing, 1)'
  ///
  ///     implies that the diagram of 'k' is a single segment connecting the
  ///     point '(0, 0)' to the point '(qSpacing, 1)'. This leads to the kernel
  ///     function:
  ///
  ///       'k(h) := h / qSpacing'.
  ///
  ///   - The sequence of breakpoints
  ///
  ///       '(0, 0), (qSpacing / 2, 1), (qSpacing, 1)'
  ///
  ///     implies that the diagram of 'k' is composed of two segments:
  ///
  ///       - The first segment connects the point '(0, 0)' to the point
  ///         '(qSpacing / 2, 1)'.
  ///
  ///       - The second segment connects the point '(qSpacing / 2, 1)' to the
  ///         point '(qSpacing, 1)'.
  ///
  ///     The combination of the two segments leads to the kernel function:
  ///
  ///                 /
  ///                |  2 * h / qSpacing    if 0 < q < qSpacing / 2
  ///       'k(h) := |                                                      '.
  ///                |  1                   if qSpacing / 2 < q < qSpacing
  ///                 \
  ///
  ///   - The sequence of breakpoints
  ///
  ///       '(0, 0), (qSpacing / 2, 0), (qSpacing / 2, 1 / 2), (qSpacing, 1)'
  ///
  ///     implies that the diagram of 'k' is composed of three segments:
  ///
  ///       - The first segment belongs to the horizontal axis connecting the
  ///         point '(0, 0)' to the point '(qSpacing / 2, 0)'.
  ///
  ///       - The second segment is vertical, connecting the point
  ///         '(qSpacing / 2, 0)' to the point '(qSpacing / 2, 1 / 2)'. A
  ///         vertical segment (i.e., two consecutive breakpoints with equal
  ///         horizontal coordinates) indicates that the kernel function is
  ///         discontinuous which is permitted by the protocol. In this case,
  ///         we have a discontinuity at point 'qSpacing / 2' because:
  ///            
  ///           '0 == k(qSpacing / 2 - epsilon) != 
  ///                 k(qSpacing / 2 + epsilon) == 1 / 2 + epsilon / qSpacing'
  ///            
  ///         where 'epsilon > 0' is an arbitrarily small value approaching 0.
  ///
  ///       - The third segment connects the point '(qSpacing / 2, 1 / 2)' to
  ///         the point '(qSpacing, 1)'.
  ///
  ///     The combination of the three segments leads to the kernel function:
  ///
  ///                 /
  ///                |  0               if 0 < q < qSpacing / 2
  ///       'k(h) := |                                                  '.
  ///                |  h / qSpacing    if qSpacing / 2 < q < qSpacing
  ///                 \
  ///
  /// A wide variety of other functions can be constructed and provided as
  /// input. The break-points are provided to protocol as 'kernelCompactArray'
  /// upon initialization of a pool or when changing a pool's kernel. A pool 
  /// owner can provide a new kernel in the compact form through the function 
  /// 'modifyKernel'. For each break-point a 64-bit horizontal coordinate 
  /// is given in 'X59' representation, and a 16-bit vertical coordinate
  /// corresponding to kernel's intensity is provided in 'X15' representation.
  /// Hence, each break-point takes 80 bits in the compact form. The
  /// break-points should be tightly packed within a 'uint256[]' array with
  /// their height appears first.
  ///
  /// @param curveArray The curve sequence contains historical prices in 'X59'
  /// representation. It should have at least two members. In other words,
  /// every member of the curve sequence represents a historical price
  /// 'pHistorical' which is stored in the form:
  ///
  ///   '(2 ** 59) * (16 + qHistorical)'
  ///
  /// where
  ///
  ///   'qHistorical := log(pHistorical / pOffset)'.
  ///
  /// Hence, each member of the curve occupies exactly '64' bits as explained
  /// in 'Curve.sol'. And each slot of 'curveArray' comprises four members of
  /// the curve sequence.
  ///
  /// The first and the second members of the curve sequence correspond to the
  /// boundaries of the current active liquidity interval (i.e., 'qLower' and
  /// 'qUpper') with the order depending on the desired history. The last
  /// member of the curve represents the current price of the pool, i.e.,
  /// 'qCurrent'.
  ///    
  /// For every integer '0 <= i < l', denote the (i + 1)-th historical price
  /// recorded by the curve sequence as 'p[i]'. Additionally, to simplify the
  /// notations, the out-of-range price 'p[l]' is assigned the same value as
  /// 'p[l - 1]'. Now, for every integer '0 <= i <= l', define also 
  ///    
  ///   'q[i] := log(p[i] / pOffset)'.
  ///
  /// The curve sequence is constructed in such a way that for every
  /// '2 <= i < l', we have:
  ///
  ///   'min(q[i - 1], q[i - 2]) < q[i] < max(q[i - 1], q[i - 2])'.
  ///
  /// This ordering rule is verified upon initialization of any pool and it is
  /// preserved by every amendment to the curve sequence.
  ///
  /// One candidate for the initial curve sequence is
  ///
  ///   'q[0] := log(p[0] / pOffset)',
  ///   'q[1] := log(p[1] / pOffset)',
  ///   'q[2] := log(p[2] / pOffset)'.
  ///
  /// where
  ///
  ///   - 'p[2]' is the market log price at the time of initialization.
  ///
  ///   - '|q[1] - q[0]| = qSpacing' which is selected based on tokens'
  ///     economic characteristics such as price volatility.
  ///
  ///   - 'q[0] < q[2] < q[1]' if the historical price has reached 'q[2]' from
  ///     above.
  ///
  ///   - 'q[1] < q[2] < q[0]' if the historical price has reached 'q[2]' from
  ///     below.
  ///
  /// More intuitively, members of the curve can be viewed as historical peaks
  /// of the price with later members representing more recent peaks. The
  /// initial curve is supplied by the pool creator and it determines
  /// 'qSpacing' which should not be less than 'minLogSpacing'.
  function initialize(
    uint256 unpepperedPoolId,
    uint256[] calldata kernelCompactArray,
    uint256[] calldata curveArray
  ) external;

  /// @notice This function provides a new pending 'kernel' for pools that are
  /// initialized by this contract. Can be called by the NFT owner or their
  /// operator only.
  /// @param poolId The target pool identifier.
  /// @param kernelCompactArray The new kernel array in its compact form.
  function modifyKernel(
    uint256 poolId,
    uint256[] calldata kernelCompactArray
  ) external;

  /// @notice Can be called by any address to convert this contract's collected
  /// pool growth portions of any tag to nofee tokens and transfer them to
  /// 'xNofeeToken'.
  /// @param tag The tag value to be converted to nofee and disbursed.
  /// @return amount The current balance of 'this' with respect to 'tag'.
  /// @return nofeeAmount The resulting amount of nofees.
  function disburse(
    Tag tag
  ) external returns (
    uint256 amount,
    uint256 nofeeAmount
  );
}