# CRYPTO MINING GAME — Frontend

App React 18 + Vite de minería virtual de criptomonedas, estilo Notcoin / Hamster Kombat.
Tema oscuro futurista (neón cyan / violeta / dorado), CSS propio, gráficos SVG propios
(sin librerías pesadas de UI ni de gráficos). Todo el texto de la interfaz está en español.

## Requisitos

- Node.js 18+ y npm.

## Cómo correr

```bash
cd frontend
npm install
npm run dev        # desarrollo en http://localhost:5173
npm run build      # build de producción (salida en dist/)
npm run preview    # sirve el build en http://localhost:4173
```

## Variables de entorno

Copia `.env.example` a `.env` y ajusta:

| Variable | Por defecto | Descripción |
| --- | --- | --- |
| `VITE_API_URL` | `http://localhost:8000` | URL base del backend (FastAPI). |
| `VITE_WALLETCONNECT_PROJECT_ID` | _(vacío)_ | Project ID de WalletConnect (gratis en https://cloud.walletconnect.com). |

En producción, define `VITE_API_URL` con la URL pública del backend antes de
compilar (`npm run build`), porque Vite incrusta las variables `VITE_*` en el build.

## Estructura

```
index.html
vite.config.js
src/
  main.jsx            Entrada React
  App.jsx             Sesión (token en localStorage) y enrutado por estado
  api/client.js       Cliente fetch: base URL, token Bearer, todos los endpoints
  styles/main.css     Tema completo (móvil primero, sidebar en escritorio, bottom-nav en móvil)
  components/
    Layout.jsx            Sidebar (escritorio) + navegación inferior (móvil)
    ProductionChart.jsx   Gráfico SVG propio de producción (14 días)
    Confetti.jsx          Confeti CSS al subir de nivel
    WalletConnectButton.jsx  Conexión de billetera (ver abajo)
  pages/
    Auth.jsx          Login / registro (+ código de referido opcional)
    Dashboard.jsx     Centro de minería: saldos, hashrate, nivel/XP, minar, recolectar, almacén, gráfico
    Machines.jsx      Catálogo de 9 niveles + Mis máquinas (overclock)
    Missions.jsx      Misiones diarias + bono diario con racha de 7 días
    Wallet.jsx        Saldos, tasa HCK→USDT, depósito BSC/TRON, historiales
    Withdrawals.jsx   Retiros (mín. 10 USDT, comisión 2%, validación de dirección) + historial
    Referrals.jsx     Enlace de referido, copiar, contadores, lista de referidos
    Leaderboard.jsx   Top 20 por HCK y por hashrate
    Profile.jsx       Perfil y datos de sesión
    Admin.jsx         Panel admin: usuarios, depósitos, retiros, fondo, config, auditoría, fraude
```

## API

El cliente (`src/api/client.js`) cubre el contrato completo: auth, `/api/me`,
minería (status/start/stop/collect), máquinas, misiones, bono diario, billetera,
depósitos, transacciones, retiros, referidos, clasificación, stats y todos los
endpoints admin. Si un endpoint no existe aún en el backend, la UI muestra el
error con elegancia y sigue funcionando (el catálogo de máquinas tiene 9 niveles
de referencia como fallback).

## WalletConnect

No se instaló `@walletconnect/ethereum-provider` ni `@web3modal/wagmi` como
dependencia: son paquetes pesados que acoplan el build a versiones concretas de
wagmi/viem. El componente `WalletConnectButton.jsx` documenta el flujo previsto
(`EthereumProvider.init({ projectId, chains: [56], showQrModal: true })` +
`provider.connect()`), conecta hoy vía la wallet del navegador (`window.ethereum`)
y muestra el aviso **"Configura tu WalletConnect Project ID en
VITE_WALLETCONNECT_PROJECT_ID"** cuando no hay Project ID. Para activar el modal
QR, instala la dependencia y completa el flujo en ese componente (ver sus comentarios).
Nota: TRON no es EVM; para TRON se usa TronLink / adaptador TRON, no el provider EVM.

## Aviso legal

La app muestra en el pie: "Minería virtual. Las recompensas dependen del fondo
de recompensas disponible. Sin rentabilidad garantizada." El admin nunca ve ni
maneja claves privadas: paga desde su propia wallet y solo registra el tx_hash.

## Pendiente (no es código)

- `VITE_WALLETCONNECT_PROJECT_ID`: crear el proyecto en WalletConnect Cloud.
- `VITE_API_URL` en producción: URL pública del backend antes del build.
- Backend en marcha para que los datos sean reales (sin él, la UI muestra errores elegantes).
