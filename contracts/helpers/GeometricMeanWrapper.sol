// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import "../utilities/GeometricMean.sol";

/// @title This contract exposes the functions of 'GeometricMean.sol' for
/// testing purposes.
contract GeometricMeanWrapper {
  function geometricMeanWrapper(
    X216 x,
    X216 y
  ) public returns (
    uint256 result
  ) {
    return geometricMean(x, y);
  }
}