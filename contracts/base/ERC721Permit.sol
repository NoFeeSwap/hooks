// SPDX-License-Identifier: MIT
//
// This contract is modified from
//
// https://github.com/Uniswap/v4-periphery/blob/
// ea2bf2e1ba6863bb809fc2ff791744f308c4a26d/src/base/ERC721Permit_v4.sol
//
// under MIT license. The following changes are made:
//
//    - OpenZeppelin's 'ERC721' contract is inherited.
//
//    - The OpenZeppelin's public method 'ERC721.ownerOf(uint256 tokenId)' is
//      used in 'permit' as opposed direct access to solmate's
//      '_ownerOf[uint256 tokenId]' mapping.
//
//    - The OpenZeppelin's internal method
//      '_approve(address to, uint256 tokenId, address auth)' is used in 
//      'permit' as opposed solmate's internal method
//      '_approve(address owner, address spender, uint256 id)' mapping.
//
//    - The OpenZeppelin's internal method
//      '_setApprovalForAll(address owner, address operator, bool approved)' is
//      used in 'permitForAll' as opposed the internal method
//      '_approveForAll(address owner, address operator, bool approved)'.
//
//    - The following overrides
//      'approve(address spender, uint256 id)', and
//      'setApprovalForAll(address operator, bool approved)' are removed in
//      favor of OpenZeppelin's implementation.
//
pragma solidity ^0.8.0;

import {ERC721} from "@openzeppelin/token/ERC721/ERC721.sol";
import {IERC721Permit_v4} from "@uniswap/interfaces/IERC721Permit_v4.sol";
import {EIP712_v4} from "@uniswap/base/EIP712_v4.sol";
import {ERC721PermitHash} from "@uniswap/libraries/ERC721PermitHash.sol";
import {UnorderedNonce} from "@uniswap/base/UnorderedNonce.sol";
import {SignatureVerification} from "@permit2/libraries/SignatureVerification.sol";

/// @title ERC721 with permit
/// @notice Nonfungible tokens that support an approve via signature, i.e. permit
abstract contract ERC721Permit is ERC721, IERC721Permit_v4, EIP712_v4, UnorderedNonce {
    using SignatureVerification for bytes;

    /// @notice Computes the nameHash and versionHash
    constructor(string memory name_, string memory symbol_) ERC721(name_, symbol_) EIP712_v4(name_) {}

    /// @notice Checks if the block's timestamp is before a signature's deadline
    modifier checkSignatureDeadline(uint256 deadline) {
        if (block.timestamp > deadline) revert SignatureDeadlineExpired();
        _;
    }

    /// @inheritdoc IERC721Permit_v4
    function permit(address spender, uint256 tokenId, uint256 deadline, uint256 nonce, bytes calldata signature)
        external
        payable
        checkSignatureDeadline(deadline)
    {
        // the .verify function checks the owner is non-0
        address owner = ownerOf(tokenId);

        bytes32 digest = ERC721PermitHash.hashPermit(spender, tokenId, nonce, deadline);
        signature.verify(_hashTypedData(digest), owner);

        _useUnorderedNonce(owner, nonce);
        _approve(spender, tokenId, address(0));
    }

    /// @inheritdoc IERC721Permit_v4
    function permitForAll(
        address owner,
        address operator,
        bool approved,
        uint256 deadline,
        uint256 nonce,
        bytes calldata signature
    ) external payable checkSignatureDeadline(deadline) {
        bytes32 digest = ERC721PermitHash.hashPermitForAll(operator, approved, nonce, deadline);
        signature.verify(_hashTypedData(digest), owner);

        _useUnorderedNonce(owner, nonce);
        _setApprovalForAll(owner, operator, approved);
    }
}
