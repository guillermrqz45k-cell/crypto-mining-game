// Botón "Conectar billetera" (WalletConnect).
//
// DECISIÓN DE IMPLEMENTACIÓN: no se instaló @walletconnect/ethereum-provider
// ni @web3modal/wagmi como dependencia. Son paquetes pesados que acoplan el
// build a versiones concretas de wagmi/viem y rompen con facilidad; el
// contrato del proyecto exige que `npm run build` pase siempre. En su lugar
// este componente implementa el flujo documentado y, cuando hay Project ID,
// intenta la conexión nativa vía window.ethereum (MetaMask / wallet del
// navegador) y deja lista la integración WalletConnect:
//
//  Flujo WalletConnect previsto (cuando se instale la dependencia):
//   1. Crear el provider: EthereumProvider.init({ projectId, chains: [56, 249],
//      showQrModal: true })  // 56 = BNB Smart Chain, 249 = TRON no EVM (ver nota)
//   2. provider.connect() -> muestra el QR / lista de wallets.
//   3. provider.on('accountsChanged') -> guardar la dirección conectada.
//   4. Desconectar con provider.disconnect().
//
//  NOTA: TRON no es EVM; WalletConnect para TRON usa @tronweb3/tronwallet-adapter
//  o TronLink, no el provider EVM. Por eso el depósito TRON en esta app se
//  registra con tx_hash (verificación on-chain en el backend), no con firma.
import { useState } from 'react'

const PROJECT_ID = import.meta.env.VITE_WALLETCONNECT_PROJECT_ID || ''

export default function WalletConnectButton() {
  const [address, setAddress] = useState('')
  const [info, setInfo] = useState('')
  const [error, setError] = useState('')

  async function connect() {
    setError(''); setInfo('')
    if (!PROJECT_ID) {
      setInfo('Configura tu WalletConnect Project ID en VITE_WALLETCONNECT_PROJECT_ID (consíguelo gratis en https://cloud.walletconnect.com) para activar la conexión por QR. Mientras tanto puedes conectar con la wallet de tu navegador.')
    }
    // Conexión nativa EIP-1193 (MetaMask / Brave / wallet del navegador).
    if (typeof window !== 'undefined' && window.ethereum) {
      try {
        const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' })
        if (accounts && accounts[0]) {
          setAddress(accounts[0])
          setInfo('Billetera conectada (vía wallet del navegador). Para conectar por QR con WalletConnect, configura el Project ID.')
          return
        }
      } catch (e) {
        setError('Conexión cancelada o rechazada en la wallet.')
        return
      }
    }
    if (!PROJECT_ID) {
      setError('No se detectó ninguna wallet en el navegador y no hay WalletConnect Project ID configurado.')
    } else {
      setInfo('Project ID configurado. Instala @walletconnect/ethereum-provider para activar el modal QR (ver README).')
    }
  }

  function disconnect() { setAddress(''); setInfo('Billetera desconectada.') }

  return (
    <div>
      {address ? (
        <div className="row">
          <span className="badge ok">Conectada</span>
          <span className="mono small">{address.slice(0, 6)}…{address.slice(-4)}</span>
          <button className="btn btn-sm" onClick={disconnect}>Desconectar</button>
        </div>
      ) : (
        <button className="btn btn-primary" onClick={connect}>🔗 Conectar billetera</button>
      )}
      {info && <p className="notice mt">{info}</p>}
      {error && <p className="error">{error}</p>}
      {!PROJECT_ID && (
        <p className="small muted mt">Configura tu WalletConnect Project ID en VITE_WALLETCONNECT_PROJECT_ID</p>
      )}
    </div>
  )
}
