// Copyright 2025, NoFeeSwap LLC - All rights reserved.
pragma solidity ^0.8.28;

import {X216} from "@core/utilities/X216.sol";
import {FullMathLibrary} from "@core/utilities/FullMath.sol";

// Modified from OpenZeppelin 
// <https://github.com/OpenZeppelin/openzeppelin-contracts/blob/
//  master/contracts/utils/math/Math.sol>

/// @notice Calculates 'floor(sqrt(x * y) // (2 ** 104))'.
/// Both inputs should be less than 'oneX216'.
function geometricMean(X216 x, X216 y) pure returns (uint256 result) {
  // First, 'x * y / (2 ** 208)' is calculated which does not overflow because:
  // 'x * y / (2 ** 208) < (2 ** 216) * (2 ** 216) / (2 ** 208) == 2 ** 224'
  uint256 a;

  // Let 's := x * y - (2 ** 256 - 1) * p'
  // Let 'r := x * y - (2 ** 208) * q'
  // Then 's - r == (2 ** 208) * q' [modulo '2 ** 256 - 1']
  // And 'q == (2 ** 48) * (s - r)' [modulo '2 ** 256 - 1']
  assembly {
    a := mulmod(
      // '(s - r) % (2 ** 256 - 1)'
      addmod(
        // 's'
        mulmod(x, y, not(0)),
        // '(0 - r) % (2 ** 256 - 1)'
        // The subtraction is safe because the output of 'mulmod' is less than
        // '1 << 208'.
        sub(not(0), mulmod(x, y, shl(208, 1))),
        not(0)
      ),
      // modular inverse of '1 << 208' modulo '2 ** 256 - 1'
      shl(48, 1),
      not(0)
    )
  }
  
  unchecked {
    // Take care of easy edge cases when a == 0 or a == 1
    if (a <= 1) return a;

    uint256 aa = a;
    uint256 xn = 1;

    if (aa >= 0x100000000000000000000000000000000) {
      aa >>= 128;
      xn <<= 64;
    }
    if (aa >= 0x10000000000000000) {
      aa >>= 64;
      xn <<= 32;
    }
    if (aa >= 0x100000000) {
      aa >>= 32;
      xn <<= 16;
    }
    if (aa >= 0x10000) {
      aa >>= 16;
      xn <<= 8;
    }
    if (aa >= 0x100) {
      aa >>= 8;
      xn <<= 4;
    }
    if (aa >= 0x10) {
      aa >>= 4;
      xn <<= 2;
    }
    if (aa >= 0x4) {
      xn <<= 1;
    }

    xn = (3 * xn) >> 1;
    xn = (xn + a / xn) >> 1;
    xn = (xn + a / xn) >> 1;
    xn = (xn + a / xn) >> 1;
    xn = (xn + a / xn) >> 1;
    xn = (xn + a / xn) >> 1;
    xn = (xn + a / xn) >> 1;

    return xn - (xn > a / xn ? 1 : 0);
  }
}