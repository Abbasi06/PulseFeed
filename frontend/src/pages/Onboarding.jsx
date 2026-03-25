import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { useAuth } from "../context/AuthContext";
import InterestPicker from "../components/InterestPicker";
import AtmosphericBackground from "../components/AtmosphericBackground";
import { MIN_SUBFIELDS } from "../constants/taxonomy";
import { API_URL } from "../config";

const MAX_NAME = 100;
const MAX_OCC = 150;

// ---------------------------------------------------------------------------
// Step indicator
// ---------------------------------------------------------------------------

const STEP_LABELS = ["Identity", "Expertise"];

function StepIndicator({ current }) {
  return (
    <div className="flex items-center gap-0 mb-8">
      {STEP_LABELS.map((label, i) => {
        const n = i + 1;
        const done = n < current;
        const active = n === current;
        return (
          <div key={label} className="flex items-center flex-1 last:flex-none">
            <div className="flex flex-col items-center gap-1">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold transition-all ${
                  done
                    ? "bg-fuchsia-600 text-white"
                    : active
                      ? "bg-violet-600 text-white ring-4 ring-violet-600/20"
                      : "bg-slate-800 text-slate-500 border border-slate-700"
                }`}
              >
                {done ? <Check className="w-4 h-4" /> : n}
              </div>
              <span
                className={`text-[10px] font-medium tracking-wide ${active ? "text-violet-400" : done ? "text-fuchsia-400" : "text-slate-600"}`}
              >
                {label}
              </span>
            </div>
            {i < STEP_LABELS.length - 1 && (
              <div
                className={`flex-1 h-px mx-2 mb-4 transition-colors ${done ? "bg-fuchsia-600/40" : "bg-slate-800"}`}
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function Onboarding() {
  const navigate = useNavigate();
  const { login } = useAuth();

  const [step, setStep] = useState(1);
  const [name, setName] = useState("");
  const [occupation, setOccupation] = useState("");
  const [field, setField] = useState("");
  const [subFields, setSubFields] = useState([]);
  const [errors, setErrors] = useState({});
  const [apiError, setApiError] = useState("");
  const [loading, setLoading] = useState(false);

  function validateStep1() {
    const e = {};
    if (!name.trim()) e.name = "Name is required";
    if (!occupation.trim()) e.occupation = "Occupation is required";
    return e;
  }

  function validateStep2() {
    const e = {};
    if (!field) e.field = "Select a domain first";
    else if (subFields.length < MIN_SUBFIELDS)
      e.subFields = `Select at least ${MIN_SUBFIELDS} focus areas`;
    return e;
  }

  function handleNext() {
    const e = validateStep1();
    if (Object.keys(e).length) {
      setErrors(e);
      return;
    }
    setErrors({});
    setStep(2);
  }

  function handleBack() {
    setErrors({});
    setStep(1);
  }

  async function handleSubmit(e) {
    e.preventDefault();
    const e2 = validateStep2();
    if (Object.keys(e2).length) {
      setErrors(e2);
      setStep(2);
      return;
    }
    setErrors({});
    setApiError("");
    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/users`, {
        method: "POST",
        credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          name: name.trim(),
          occupation: occupation.trim(),
          selected_chips: subFields.slice(0, 5),
          field,
          sub_fields: subFields,
        }),
      });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail ?? `Error ${res.status}`);
      }
      const user = await res.json();
      login(user);
      navigate("/dashboard");
    } catch (err) {
      setApiError(err.message || "Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const canSubmit = field && subFields.length >= MIN_SUBFIELDS && !loading;

  return (
    <div className="min-h-screen flex items-center justify-center px-4 py-12">
      <AtmosphericBackground />
      <div className="relative z-10 w-full max-w-lg">
        {/* Brand */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Pulse<span className="text-violet-400">Board</span>
          </h1>
          <p className="mt-2 text-slate-400 text-sm">
            Build your personalized AI knowledge feed in 2 steps.
          </p>
        </div>

        <div className="bg-slate-900/80 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-8 shadow-2xl shadow-black/50 ring-1 ring-white/5">
          <StepIndicator current={step} />

          {/* API error banner */}
          {apiError && (
            <div className="flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-lg px-4 py-3 mb-6">
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

          <form onSubmit={handleSubmit} noValidate>
            {/* ── Step 1: Identity ── */}
            {step === 1 && (
              <div className="space-y-5">
                <div>
                  <div className="flex justify-between mb-1.5">
                    <label className="text-sm font-medium text-slate-200">
                      Name
                    </label>
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
                    placeholder="Ada Lovelace"
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

                <div>
                  <div className="flex justify-between mb-1.5">
                    <label className="text-sm font-medium text-slate-200">
                      Job Title / Role
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
                    onChange={(e) =>
                      setOccupation(e.target.value.slice(0, MAX_OCC))
                    }
                    placeholder="e.g. Senior AI Engineer, Security Researcher…"
                    className={`w-full px-3.5 py-2.5 bg-slate-800 border rounded-lg text-sm text-slate-200 placeholder-slate-500 outline-none transition-colors ${
                      errors.occupation
                        ? "border-red-500"
                        : "border-slate-700 focus:border-violet-500 focus:ring-1 focus:ring-violet-500/30"
                    }`}
                  />
                  {errors.occupation && (
                    <p className="mt-1.5 text-xs text-red-400">
                      {errors.occupation}
                    </p>
                  )}
                </div>

                <button
                  type="button"
                  onClick={handleNext}
                  className="w-full py-3 px-4 btn-primary rounded-lg transition-all mt-2"
                >
                  Next: Expertise →
                </button>
              </div>
            )}

            {/* ── Step 2: Expertise ── */}
            {step === 2 && (
              <div className="space-y-5">
                <InterestPicker
                  field={field}
                  subFields={subFields}
                  onFieldChange={(f) => {
                    setField(f);
                    setErrors((prev) => ({
                      ...prev,
                      field: undefined,
                      subFields: undefined,
                    }));
                  }}
                  onSubFieldsChange={(sf) => {
                    setSubFields(sf);
                    setErrors((prev) => ({ ...prev, subFields: undefined }));
                  }}
                />

                {(errors.field || errors.subFields) && (
                  <p className="text-xs text-red-400 text-center">
                    {errors.field || errors.subFields}
                  </p>
                )}

                <div className="flex gap-3 mt-6">
                  <button
                    type="button"
                    onClick={handleBack}
                    className="px-4 py-3 bg-slate-800 hover:bg-slate-700 border border-slate-700 text-slate-300 text-sm font-medium rounded-lg transition-colors"
                  >
                    ← Back
                  </button>
                  <button
                    type="submit"
                    disabled={!canSubmit}
                    className="flex-1 py-3 px-4 btn-primary disabled:opacity-40 disabled:cursor-not-allowed rounded-lg transition-all flex items-center justify-center gap-2"
                  >
                    {loading ? (
                      <>
                        <svg
                          className="animate-spin w-4 h-4"
                          fill="none"
                          viewBox="0 0 24 24"
                        >
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Building your feed…
                      </>
                    ) : (
                      "Launch My Feed →"
                    )}
                  </button>
                </div>
              </div>
            )}
          </form>
        </div>
      </div>
    </div>
  );
}
