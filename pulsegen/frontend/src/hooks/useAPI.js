import { useState, useEffect, useRef, useCallback } from 'react'
import { ADMIN_API_URL, ADMIN_API_KEY } from '../config'

export function useAPI(endpoint, interval = null) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [isRefreshing, setIsRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const isFirstLoad = useRef(true)

  const fetchData = useCallback(
    async (signal) => {
      setIsRefreshing(true)
      if (isFirstLoad.current) {
        setLoading(true)
      }
      try {
        const response = await fetch(`${ADMIN_API_URL}/admin${endpoint}`, {
          signal,
          headers: { 'X-Admin-Key': ADMIN_API_KEY },
        })
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const json = await response.json()
        setData(json)
        setError(null)
        isFirstLoad.current = false
      } catch (err) {
        if (err.name === 'AbortError') return
        setError(err.message)
        setData(null)
      } finally {
        setLoading(false)
        setIsRefreshing(false)
      }
    },
    [endpoint],
  )

  useEffect(() => {
    const controller = new AbortController()
    fetchData(controller.signal)
    if (interval) {
      const timer = setInterval(() => fetchData(controller.signal), interval)
      return () => {
        clearInterval(timer)
        controller.abort()
      }
    }
    return () => controller.abort()
  }, [endpoint, interval, fetchData])

  const refetch = useCallback(() => {
    isFirstLoad.current = true
    const controller = new AbortController()
    fetchData(controller.signal)
  }, [fetchData])

  return { data, loading, isRefreshing, error, refetch }
}
