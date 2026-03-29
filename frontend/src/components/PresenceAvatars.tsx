import { useEffect, useState } from 'react'
import { getProvider } from '../lib/collaboration'

export default function PresenceAvatars() {
  const [states, setStates] = useState([] as any[])

  useEffect(() => {
    const provider = getProvider()
    if (!provider) return

    const update = () => {
      const all = Array.from(provider.awareness.getStates().values())
      setStates(all.filter(s => s.user))
    }

    provider.awareness.on('change', update)
    update()

    return () => provider.awareness.off('change', update)
  }, [])

  if (states.length === 0) return null

  return (
    <div className="absolute top-4 right-32 z-10 flex gap-1">
      {states.map((s, i) => (
        <div
          key={i}
          title={s.user.name}
          className="w-7 h-7 rounded-full flex items-center justify-center text-xs text-white font-medium"
          style={{ backgroundColor: s.user.color }}
        >
          {s.user.name?.[0]?.toUpperCase()}
        </div>
      ))}
    </div>
  )
}
