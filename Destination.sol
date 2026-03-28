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

 /// @notice Create a new wrapped token on the destination chain
    /// @notice Deploy a new wrapped token on the destination chain
    function createToken(
        address _underlying_token,
        string memory name,
        string memory symbol
    ) public onlyRole(CREATOR_ROLE) returns (address) {
        require(_underlying_token != address(0), "Underlying token required");

        // Deploy a new BridgeToken contract
        BridgeToken token = new BridgeToken(_underlying_token, name, symbol, address(this));

        // store mapping
        wrapped_tokens[_underlying_token] = address(token);
        underlying_tokens[address(token)] = _underlying_token;

        // Emit an event to announce the new token
        emit Creation(_underlying_token, address(token));

        // Return the address of the newly created token
        return address(token);
    }

    /// @notice Mint wrapped tokens on the destination chain
    function wrap(
        address _underlying_token, // source token
        address _recipient,
        uint256 _amount
    ) public onlyRole(WARDEN_ROLE) {
        address tokenAddr = wrapped_tokens[_underlying_token];
        require(tokenAddr != address(0), "Token not registered");

        BridgeToken(tokenAddr).mint(_recipient, _amount);
        emit Wrap(_underlying_token, _recipient, _amount);
    }

function unwrap(
    address _wrapped_token,
    address _recipient,  // source chain address
    uint256 _amount
) public {
    require(_wrapped_token != address(0), "Wrapped token required");
    require(_recipient != address(0), "Recipient required");
    require(_amount > 0, "Amount must be > 0");

    BridgeToken token = BridgeToken(_wrapped_token);

    // Burn tokens from the caller (msg.sender)
    token.burnFrom(_recipient, _amount);

    // Emit event so source chain knows who receives original tokens
    emit Unwrap(_wrapped_token, _recipient, _amount);
}

    /// @notice Return the number of wrapped tokens created
    function totalTokens() public view returns (uint256) {
        return tokens.length;
    }
}
