import { useState, useEffect } from 'react'
import { ADMIN_API_URL } from '../config'

export function useAPI(endpoint, interval = null) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const fetchData = async () => {
    try {
      setLoading(true)
      const response = await fetch(`${ADMIN_API_URL}/admin${endpoint}`)
      if (!response.ok) throw new Error(`HTTP ${response.status}`)
      const json = await response.json()
      setData(json)
      setError(null)
    } catch (err) {
      setError(err.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    if (interval) {
      const timer = setInterval(fetchData, interval)
      return () => clearInterval(timer)
    }
  }, [endpoint, interval])

  return { data, loading, error, refetch: fetchData }
}
