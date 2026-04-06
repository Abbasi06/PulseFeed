import { useState, useEffect } from 'react'
import { ADMIN_API_URL } from '../config'

export function useHealthCheck(intervalMs = 15000) {
  const [online, setOnline] = useState(true)
  const [lastChecked, setLastChecked] = useState(null)

  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${ADMIN_API_URL}/health`, {
          signal: AbortSignal.timeout(3000),
        })
        setOnline(res.ok)
      } catch {
        setOnline(false)
      } finally {
        setLastChecked(new Date())
      }
    }
    check()
    const id = setInterval(check, intervalMs)
    return () => clearInterval(id)
  }, [intervalMs])

  return { online, lastChecked }
}
