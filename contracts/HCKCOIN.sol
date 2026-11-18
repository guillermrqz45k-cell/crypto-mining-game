// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title HCKCOIN (HCK)
/// @notice CONTRATO DE REFERENCIA — NO DESPLEGADO.
/// @dev La economía del juego "CRYPTO MINING GAME" corre OFF-CHAIN en el
///      servidor (FastAPI + PostgreSQL): los saldos de HCK, las máquinas,
///      las misiones y los retiros se gestionan en la base de datos.
///      Este contrato existe solo como referencia, por si AMO decide en el
///      futuro lanzar el token HCKCOIN on-chain (por ejemplo en BSC).
///      Hoy NO hay ningún token HCK en circulación on-chain, no se ha
///      desplegado en ninguna red y el sistema NUNCA guarda claves privadas.
///
///      Contrato ERC-20 mínimo y AUTOCONTENIDO: no usa imports externos
///      (nada de OpenZeppelin) para poder compilarse con un solo archivo
///      en Remix o con `solc` sin dependencias.
///
///      Reglas del token:
///      - Nombre: "HCKCOIN", símbolo: "HCK", decimales: 18.
///      - Suministro máximo: 1.000.000.000 HCK (MAX_SUPPLY).
///      - Solo el owner puede acuñar (mint), y nunca por encima del tope.
///      - Cualquier titular puede quemar (burn) sus propios tokens.
///      - El suministro inicial es 0: todo HCK se acuña bajo demanda.
contract HCKCOIN {
    // ------------------------------------------------------------------
    // Metadatos del token
    // ------------------------------------------------------------------
    string public constant name = "HCKCOIN";
    string public constant symbol = "HCK";
    uint8 public constant decimals = 18;

    /// @notice Suministro máximo: 1.000.000.000 HCK (con 18 decimales).
    uint256 public constant MAX_SUPPLY = 1_000_000_000 * 10 ** 18;

    // ------------------------------------------------------------------
    // Estado
    // ------------------------------------------------------------------
    uint256 private _totalSupply;
    mapping(address => uint256) private _balances;
    mapping(address => mapping(address => uint256)) private _allowances;

    /// @notice Dirección del owner (quien despliega el contrato).
    address public owner;

    // ------------------------------------------------------------------
    // Eventos
    // ------------------------------------------------------------------
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    event Mint(address indexed to, uint256 value);

    // ------------------------------------------------------------------
    // Modificadores
    // ------------------------------------------------------------------
    modifier onlyOwner() {
        require(msg.sender == owner, "HCKCOIN: solo el owner");
        _;
    }

    // ------------------------------------------------------------------
    // Constructor
    // ------------------------------------------------------------------
    /// @notice El desplegador queda como owner. Suministro inicial: 0.
    constructor() {
        owner = msg.sender;
    }

    // ------------------------------------------------------------------
    // Lecturas ERC-20
    // ------------------------------------------------------------------
    /// @notice Suministro total en circulación.
    function totalSupply() public view returns (uint256) {
        return _totalSupply;
    }

    /// @notice Saldo de HCK de una cuenta.
    function balanceOf(address account) public view returns (uint256) {
        return _balances[account];
    }

    /// @notice Cantidad que `spender` puede gastar en nombre de `account`.
    function allowance(address account, address spender) public view returns (uint256) {
        return _allowances[account][spender];
    }

    // ------------------------------------------------------------------
    // Transferencias ERC-20
    // ------------------------------------------------------------------
    /// @notice Transfiere `amount` HCK del llamante a `to`.
    function transfer(address to, uint256 amount) public returns (bool) {
        _transfer(msg.sender, to, amount);
        return true;
    }

    /// @notice Aprueba a `spender` para gastar hasta `amount` HCK del llamante.
    function approve(address spender, uint256 amount) public returns (bool) {
        _allowances[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }

    /// @notice Transfiere `amount` HCK de `from` a `to` usando el allowance.
    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        uint256 current = _allowances[from][msg.sender];
        require(current >= amount, "HCKCOIN: allowance insuficiente");
        unchecked {
            _allowances[from][msg.sender] = current - amount;
        }
        _transfer(from, to, amount);
        return true;
    }

    // ------------------------------------------------------------------
    // Mint / Burn
    // ------------------------------------------------------------------
    /// @notice Acuña `amount` HCK para `to`. Solo el owner.
    /// @dev Revierte si el nuevo suministro total superaría MAX_SUPPLY.
    function mint(address to, uint256 amount) public onlyOwner {
        require(to != address(0), "HCKCOIN: destino cero");
        require(_totalSupply + amount <= MAX_SUPPLY, "HCKCOIN: supera MAX_SUPPLY");
        _totalSupply += amount;
        _balances[to] += amount;
        emit Mint(to, amount);
        emit Transfer(address(0), to, amount);
    }

    /// @notice Quema `amount` HCK del saldo del llamante.
    function burn(uint256 amount) public {
        require(_balances[msg.sender] >= amount, "HCKCOIN: saldo insuficiente");
        unchecked {
            _balances[msg.sender] -= amount;
            _totalSupply -= amount;
        }
        emit Transfer(msg.sender, address(0), amount);
    }

    // ------------------------------------------------------------------
    // Lógica interna
    // ------------------------------------------------------------------
    function _transfer(address from, address to, uint256 amount) internal {
        require(from != address(0), "HCKCOIN: origen cero");
        require(to != address(0), "HCKCOIN: destino cero");
        require(_balances[from] >= amount, "HCKCOIN: saldo insuficiente");
        unchecked {
            _balances[from] -= amount;
            _balances[to] += amount;
        }
        emit Transfer(from, to, amount);
    }
}
