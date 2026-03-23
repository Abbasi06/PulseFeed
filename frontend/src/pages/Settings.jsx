import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import TagInput from "../components/TagInput";
import { API_URL } from "../config";

const MAX_NAME = 100;
const MAX_OCC = 150;

export default function Settings() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const userId = user?.id;

  const [name, setName] = useState("");
  const [occupation, setOccupation] = useState("");
  const [interests, setInterests] = useState([]);
  const [hobbies, setHobbies] = useState([]);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);
  const [saved, setSaved] = useState(false);
  const [fetching, setFetching] = useState(true);

  useEffect(() => {
    if (!userId) return;
    fetch(`${API_URL}/users/${userId}`, { credentials: "include" })
      .then((r) => r.json())
      .then((u) => {
        setName(u.name ?? "");
        setOccupation(u.occupation ?? "");
        setInterests(u.interests ?? []);
        setHobbies(u.hobbies ?? []);
      })
      .catch(() => setApiError("Could not load your profile."))
      .finally(() => setFetching(false));
  }, [userId]);

  function validate() {
    const e = {};
    if (!name.trim()) e.name = "Name is required";
    if (!occupation.trim()) e.occupation = "Occupation is required";
    if (interests.length === 0) e.interests = "Add at least one interest";
    return e;
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const e2 = validate();
    if (Object.keys(e2).length) {
      setErrors(e2);
      return;
    }
    setErrors({});
    setApiError("");
    setSaved(false);
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/users/${userId}`, {
        method: "PUT",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          occupation: occupation.trim(),
          interests,
          hobbies,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Error ${res.status}`);
      }
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
    } catch (err) {
      setApiError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleLogout() {
    await logout();
    navigate("/");
  }

  if (fetching) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-6 h-6 border-2 border-violet-500 border-t-transparent rounded-full animate-spin" />
      </div>
    );
  }

  return (
    <div className="max-w-xl mx-auto px-4 sm:px-6 py-8">
      <h2 className="text-xl font-bold text-white mb-1">Settings</h2>
      <p className="text-sm text-slate-400 mb-8">
        Update your profile to re-tune your feed.
      </p>

      <form onSubmit={handleSubmit} noValidate className="space-y-6">
        {apiError && (
          <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3">
            <svg
              className="w-5 h-5 text-red-400 shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              strokeWidth={2}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"
              />
            </svg>
            <p className="text-sm text-red-300">{apiError}</p>
          </div>
        )}

        {saved && (
          <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 rounded-lg px-4 py-3">
            <svg
              className="w-4 h-4 text-green-400"
              fill="none"
              stroke="currentColor"
              strokeWidth={2.5}
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M5 13l4 4L19 7"
              />
            </svg>
            <p className="text-sm text-green-300">
              Profile saved successfully.
            </p>
          </div>
        )}

        {/* Name */}
        <div>
          <div className="flex justify-between mb-1.5">
            <label className="text-sm font-medium text-slate-200">Name</label>
            <span
              className={`text-xs ${name.length > MAX_NAME * 0.9 ? "text-amber-400" : "text-slate-500"}`}
            >
              {name.length}/{MAX_NAME}
            </span>
          </div>
          <input
            type="text"
            value={name}
            onChange={(e) => setName(e.target.value.slice(0, MAX_NAME))}
            className={`w-full px-3.5 py-2.5 bg-slate-800 border rounded-lg text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors ${
              errors.name
                ? "border-red-500"
                : "border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30"
            }`}
          />
          {errors.name && (
            <p className="mt-1.5 text-xs text-red-400">{errors.name}</p>
          )}
        </div>

        {/* Occupation */}
        <div>
          <div className="flex justify-between mb-1.5">
            <label className="text-sm font-medium text-slate-200">
              Occupation
            </label>
            <span
              className={`text-xs ${occupation.length > MAX_OCC * 0.9 ? "text-amber-400" : "text-slate-500"}`}
            >
              {occupation.length}/{MAX_OCC}
            </span>
          </div>
          <input
            type="text"
            value={occupation}
            onChange={(e) => setOccupation(e.target.value.slice(0, MAX_OCC))}
            className={`w-full px-3.5 py-2.5 bg-slate-800 border rounded-lg text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors ${
              errors.occupation
                ? "border-red-500"
                : "border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30"
            }`}
          />
          {errors.occupation && (
            <p className="mt-1.5 text-xs text-red-400">{errors.occupation}</p>
          )}
        </div>

        {/* Interests */}
        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1.5">
            Interests
          </label>
          <TagInput
            tags={interests}
            onChange={setInterests}
            placeholder="Add interest…"
          />
          {errors.interests && (
            <p className="mt-1.5 text-xs text-red-400">{errors.interests}</p>
          )}
        </div>

        {/* Hobbies */}
        <div>
          <label className="block text-sm font-medium text-slate-200 mb-1.5">
            Hobbies{" "}
            <span className="text-slate-500 font-normal">(optional)</span>
          </label>
          <TagInput
            tags={hobbies}
            onChange={setHobbies}
            placeholder="Add hobby…"
          />
        </div>

        <div className="flex items-center gap-3 pt-2">
          <button
            type="submit"
            disabled={loading}
            className="flex-1 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:bg-violet-800 disabled:cursor-not-allowed text-white text-sm font-semibold rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <svg
                  className="animate-spin w-4 h-4"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Saving…
              </>
            ) : (
              "Save Changes"
            )}
          </button>
          <button
            type="button"
            onClick={handleLogout}
            className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors"
          >
            Sign out
          </button>
        </div>
      </form>
    </div>
  );
}
