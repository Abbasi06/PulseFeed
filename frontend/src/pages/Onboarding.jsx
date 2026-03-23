import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import TagInput from '../components/TagInput'
import { API_URL } from '../config'

const MAX_NAME = 100
const MAX_OCC = 150

export default function Onboarding() {
  const navigate = useNavigate()
  const { login } = useAuth()
  const [name, setName] = useState('')
  const [occupation, setOccupation] = useState('')
  const [interests, setInterests] = useState([])
  const [hobbies, setHobbies] = useState([])
  const [errors, setErrors] = useState({})
  const [apiError, setApiError] = useState('')
  const [loading, setLoading] = useState(false)

  function validate() {
    const e = {}
    if (!name.trim()) e.name = 'Name is required'
    if (!occupation.trim()) e.occupation = 'Occupation is required'
    if (interests.length === 0) e.interests = 'Add at least one interest'
    return e
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const e2 = validate()
    if (Object.keys(e2).length) { setErrors(e2); return }
    setErrors({})
    setApiError('')
    setLoading(true)
    try {
      const res = await fetch(`${API_URL}/users`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name.trim(), occupation: occupation.trim(), interests, hobbies }),
      })
      if (!res.ok) {
        const data = await res.json().catch(() => ({}))
        throw new Error(data.detail ?? `Error ${res.status}`)
      }
      const user = await res.json()
      login(user)
      navigate('/dashboard')
    } catch (err) {
      setApiError(err.message || 'Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-950 flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-lg">
        {/* Brand */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Pulse<span className="text-violet-400">Board</span>
          </h1>
          <p className="mt-2 text-slate-400 text-sm">
            Your personalized AI knowledge feed — set up your profile to get started.
          </p>
        </div>

        <form
          onSubmit={handleSubmit}
          noValidate
          className="bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl shadow-black/30 space-y-6"
        >
          {/* API error banner */}
          {apiError && (
            <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
              <svg className="w-5 h-5 text-red-400 shrink-0 mt-0.5" fill="none" stroke="currentColor" strokeWidth={2} viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
              </svg>
              <p className="text-sm text-red-300">{apiError}</p>
            </div>
          )}

          {/* Name */}
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-sm font-medium text-slate-200">Name</label>
              <span className={`text-xs ${name.length > MAX_NAME * 0.9 ? 'text-amber-400' : 'text-slate-500'}`}>
                {name.length}/{MAX_NAME}
              </span>
            </div>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value.slice(0, MAX_NAME))}
              placeholder="Ada Lovelace"
              className={`w-full px-3.5 py-2.5 bg-slate-800 border rounded-lg text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors ${
                errors.name
                  ? 'border-red-500 focus:border-red-400'
                  : 'border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30'
              }`}
            />
            {errors.name && <p className="mt-1.5 text-xs text-red-400">{errors.name}</p>}
          </div>

          {/* Occupation */}
          <div>
            <div className="flex justify-between mb-1.5">
              <label className="text-sm font-medium text-slate-200">Occupation</label>
              <span className={`text-xs ${occupation.length > MAX_OCC * 0.9 ? 'text-amber-400' : 'text-slate-500'}`}>
                {occupation.length}/{MAX_OCC}
              </span>
            </div>
            <input
              type="text"
              value={occupation}
              onChange={(e) => setOccupation(e.target.value.slice(0, MAX_OCC))}
              placeholder="Software Engineer"
              className={`w-full px-3.5 py-2.5 bg-slate-800 border rounded-lg text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors ${
                errors.occupation
                  ? 'border-red-500 focus:border-red-400'
                  : 'border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30'
              }`}
            />
            {errors.occupation && <p className="mt-1.5 text-xs text-red-400">{errors.occupation}</p>}
          </div>

          {/* Interests */}
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1.5">
              Interests <span className="text-slate-500 font-normal">(required)</span>
            </label>
            <TagInput
              tags={interests}
              onChange={setInterests}
              placeholder="e.g. AI, Python, climate… press Enter"
            />
            {errors.interests && <p className="mt-1.5 text-xs text-red-400">{errors.interests}</p>}
            <p className="mt-1.5 text-xs text-slate-500">Press Enter or comma to add · up to 10 tags</p>
          </div>

          {/* Hobbies */}
          <div>
            <label className="block text-sm font-medium text-slate-200 mb-1.5">
              Hobbies <span className="text-slate-500 font-normal">(optional)</span>
            </label>
            <TagInput
              tags={hobbies}
              onChange={setHobbies}
              placeholder="e.g. hiking, chess, cooking…"
            />
            <p className="mt-1.5 text-xs text-slate-500">Helps personalise your feed further</p>
          </div>

          {/* Submit */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-3 px-4 bg-violet-600 hover:bg-violet-500 disabled:bg-violet-800 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg className="animate-spin w-4 h-4" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
                Creating your feed…
              </>
            ) : (
              'Start My Feed →'
            )}
          </button>
        </form>
      </div>
    </div>
  )
}
