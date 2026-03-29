import * as Y from 'yjs'
import { WebsocketProvider } from 'y-websocket'
import { getUser } from './auth'

const WS_URL = import.meta.env.VITE_WS_URL

export const ydoc = new Y.Doc()

export const edgeAnnotations = ydoc.getMap('edge_annotations')
export const comments = ydoc.getArray('comments')
export const nodePositions = ydoc.getMap('node_positions')

let provider: WebsocketProvider | null = null

export function connectWorkspace(workspaceId) {
  const token = localStorage.getItem('access_token')
  provider = new WebsocketProvider(
    `${WS_URL}/ws`,
    `${workspaceId}?token=${token}`,
    ydoc
  )

  const user = getUser()
  if (user) {
    const color = '#' + Math.floor(Math.random() * 0xffffff).toString(16).padStart(6, '0')
    provider.awareness.setLocalStateField('user', { name: user.email, color })
  }

  return provider
}

export function getProvider() {
  return provider
}
