# HCKCOIN (HCK) — Contrato de referencia

## Qué es

`HCKCOIN.sol` es un token ERC-20 mínimo y autocontenido (sin imports
externos, sin dependencia de OpenZeppelin) que representa el token de
recompensa **HCKCOIN (HCK)** de CRYPTO MINING GAME.

> ⚠️ **ADVERTENCIA IMPORTANTE — LEER ANTES DE DESPLEGAR**
>
> Este contrato es **solo una referencia y NO está desplegado** en ninguna
> red. Hoy la economía del juego corre **100% off-chain** en el servidor
> (FastAPI + PostgreSQL): los saldos de HCK, la minería, las máquinas, las
> misiones, los bonos y los retiros se gestionan en la base de datos.
> No existe ningún token HCK en circulación on-chain, y el sistema nunca
> guarda claves privadas: los retiros USDT los paga el admin manualmente
> desde su propia wallet.
>
> El token solo se acuñaría si **AMO decide lanzar el token on-chain**
> en el futuro. Desplegarlo sin esa decisión crearía un token real con
> valor potencial y responsabilidades legales/fiscales.

## Características

| Propiedad | Valor |
|---|---|
| Nombre | HCKCOIN |
| Símbolo | HCK |
| Decimales | 18 |
| Suministro inicial | 0 |
| Suministro máximo (`MAX_SUPPLY`) | 1.000.000.000 HCK |
| Estándar | ERC-20 mínimo |

Funciones:

- `totalSupply()`, `balanceOf(account)`, `allowance(owner, spender)`
- `transfer(to, amount)`, `approve(spender, amount)`, `transferFrom(from, to, amount)`
- `mint(to, amount)` — **solo `owner`**, revierte si supera `MAX_SUPPLY`
- `burn(amount)` — cualquier titular quema sus propios tokens
- `owner()` — dirección del owner (quien despliega)
- Eventos `Transfer`, `Approval`, `Mint`

## Cómo compilarlo

### Opción A — solc (línea de comandos)

```bash
# Instalar el compilador (una vez). En Debian/Ubuntu:
#   sudo add-apt-repository ppa:ethereum/ethereum && sudo apt update && sudo apt install solc
# O usarlo vía npx (sin instalar nada):
npx solc --bin --abi contracts/HCKCOIN.sol
```

El compilado genera el bytecode (`--bin`) y la ABI (`--abi`). Con
`--bin --abi` se obtienen los artefactos necesarios para desplegar con
cualquier herramienta.

### Opción B — Remix (navegador, sin instalar nada)

1. Abrir https://remix.ethereum.org
2. Crear un archivo `HCKCOIN.sol` y pegar el contenido de
   `contracts/HCKCOIN.sol`.
3. En "Solidity Compiler", elegir versión **0.8.20 o superior** y pulsar
   **Compile**.
4. No hace falta instalar librerías: el contrato no tiene imports.

## Cómo desplegarlo en BSC testnet (solo si AMO lo decide)

1. **Red:** BNB Smart Chain Testnet (chain ID 97).
   Obtener tBNB de prueba en el faucet oficial de BNB Chain.
2. **Wallet:** usar MetaMask (o similar) con una wallet del admin.
   **Nunca** pegar la clave privada en el repositorio ni en variables
   compartidas.
3. **Despliegue en Remix:**
   - Compilar como arriba.
   - En "Deploy & Run Transactions", elegir "Injected Provider - MetaMask"
     y la red BSC Testnet.
   - Desplegar `HCKCOIN`. El desplegador queda como `owner`.
4. **Verificación:** verificar el contrato en
   https://testnet.bscscan.com con el código fuente, para que cualquiera
   pueda auditarlo.
5. **Antes de mainnet:** auditar el contrato, decidir el plan de
   acuñación (quién y cuánto `mint`), y definir la relación entre el
   HCK off-chain del juego y el token on-chain (por ejemplo, canje
   1:1 con tope diario). **No desplegar en mainnet sin esa decisión.**

## Estado actual

- Contrato escrito y compilado (ver reporte del agente de contratos).
- **No desplegado** en ninguna red (ni testnet ni mainnet).
- Economía del juego: off-chain, en PostgreSQL (`db/schema.sql`).
