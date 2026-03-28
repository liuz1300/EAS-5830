// SPDX-License-Identifier: MIT
pragma solidity ^0.8.17;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/access/AccessControl.sol";
import "./BridgeToken.sol";

contract Destination is AccessControl {
    bytes32 public constant WARDEN_ROLE = keccak256("BRIDGE_WARDEN_ROLE");
    bytes32 public constant CREATOR_ROLE = keccak256("CREATOR_ROLE");
	mapping( address => address) public underlying_tokens;
	mapping( address => address) public wrapped_tokens;
	address[] public tokens;

	event Creation( address indexed underlying_token, address indexed wrapped_token );
	event Wrap( address indexed underlying_token, address indexed wrapped_token, address indexed to, uint256 amount );
	event Unwrap( address indexed underlying_token, address indexed wrapped_token, address frm, address indexed to, uint256 amount );

    constructor( address admin ) {
        _grantRole(DEFAULT_ADMIN_ROLE, admin);
        _grantRole(CREATOR_ROLE, admin);
        _grantRole(WARDEN_ROLE, admin);
    }
 /// @notice Create a new BridgeToken for an underlying asset
    function createToken(
        address _underlying_token,
        string memory name,
        string memory symbol
    ) public onlyRole(CREATOR_ROLE) returns(address) {
        require(_underlying_token != address(0), "Underlying token required");
        require(wrapped_tokens[_underlying_token] == address(0), "Token already registered");

        // Deploy a new BridgeToken
        BridgeToken token = new BridgeToken(_underlying_token, name, symbol, address(this));

        // Register in mappings
        wrapped_tokens[_underlying_token] = address(token);
        underlying_tokens[address(token)] = _underlying_token;

        // Add to token list
        tokens.push(address(token));

        emit Creation(_underlying_token, address(token));
        return address(token);
    }

    /// @notice Mint wrapped tokens on destination chain
    function wrap(
        address _underlying_token,
        address _recipient,
        uint256 _amount
    ) public onlyRole(WARDEN_ROLE) {
        address tokenAddr = wrapped_tokens[_underlying_token];
        require(tokenAddr != address(0), "Token not registered");

        BridgeToken(tokenAddr).mint(_recipient, _amount);
        emit Wrap(_underlying_token, _recipient, _amount);
    }

    /// @notice Burn wrapped tokens to return to source chain
    function unwrap(
        address _wrapped_token,
        address _recipient,
        uint256 _amount
    ) public {
        address underlying = underlying_tokens[_wrapped_token];
        require(underlying != address(0), "Wrapped token not registered");

        BridgeToken(_wrapped_token).burnFrom(msg.sender, _amount);
        emit Unwrap(_wrapped_token, _recipient, _amount);
    }

    /// @notice Helper to get number of wrapped tokens created
    function totalTokens() public view returns (uint256) {
        return tokens.length;
    }
}
