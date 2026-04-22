import React, { useState, useEffect, useRef } from 'react'
import { User, Briefcase, FileText, Mail, CheckCircle, AlertCircle, Upload, Trash2, Plus, Minus, Loader2 } from 'lucide-react'
import clsx from 'clsx'
import { getProfile, updateProfile, getResumes, uploadResume, deleteResume } from '../api/client.js'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function Toggle({ checked, onChange, label, sublabel }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <div
        className={clsx(
          'relative mt-0.5 w-10 h-5.5 rounded-full transition-colors duration-200 shrink-0',
          checked ? 'bg-indigo-600' : 'bg-gray-700'
        )}
        style={{ height: '22px', width: '40px' }}
        onClick={() => onChange(!checked)}
      >
        <span
          className={clsx(
            'absolute top-0.5 w-4 h-4 rounded-full bg-white shadow transition-transform duration-200',
            checked ? 'translate-x-5' : 'translate-x-0.5'
          )}
        />
      </div>
      <div>
        <p className={clsx('text-sm font-medium', checked ? 'text-white' : 'text-gray-400')}>{label}</p>
        {sublabel && <p className="text-xs text-gray-600 mt-0.5">{sublabel}</p>}
      </div>
    </label>
  )
}

function Field({ label, children, className = '' }) {
  return (
    <div className={className}>
      <label className="block text-xs font-semibold text-gray-500 uppercase tracking-wider mb-1.5">{label}</label>
      {children}
    </div>
  )
}

function Input({ value, onChange, placeholder, type = 'text', className = '' }) {
  return (
    <input
      type={type}
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      className={clsx(
        'w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 outline-none transition-colors',
        className
      )}
    />
  )
}

function Select({ value, onChange, options, className = '' }) {
  return (
    <select
      value={value || ''}
      onChange={e => onChange(e.target.value)}
      className={clsx(
        'w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white outline-none transition-colors appearance-none',
        className
      )}
    >
      <option value="">— Select —</option>
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  )
}

// ─── Toast ────────────────────────────────────────────────────────────────────

function Toast({ type, message, onDismiss }) {
  useEffect(() => {
    const t = setTimeout(onDismiss, 3500)
    return () => clearTimeout(t)
  }, [onDismiss])

  return (
    <div className={clsx(
      'fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl text-sm font-medium fade-in-up',
      type === 'success'
        ? 'bg-green-500/15 border-green-500/30 text-green-400'
        : 'bg-red-500/15 border-red-500/30 text-red-400'
    )}>
      {type === 'success' ? <CheckCircle size={15} /> : <AlertCircle size={15} />}
      {message}
    </div>
  )
}

// ─── Tab definitions ──────────────────────────────────────────────────────────

const TABS = [
  { id: 'personal', label: 'Personal Info', icon: User },
  { id: 'experience', label: 'Experience & Skills', icon: Briefcase },
  { id: 'resumes', label: 'Resumes', icon: FileText },
  { id: 'coverletter', label: 'Cover Letter & Defaults', icon: Mail },
]

const RACE_OPTIONS = [
  { value: 'prefer_not', label: 'Prefer not to say' },
  { value: 'asian', label: 'Asian' },
  { value: 'black', label: 'Black or African American' },
  { value: 'hispanic', label: 'Hispanic or Latino' },
  { value: 'native_american', label: 'Native American or Alaska Native' },
  { value: 'pacific_islander', label: 'Native Hawaiian or Pacific Islander' },
  { value: 'white', label: 'White' },
  { value: 'two_or_more', label: 'Two or more races' },
]

const GENDER_OPTIONS = [
  { value: 'prefer_not', label: 'Prefer not to say' },
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'nonbinary', label: 'Non-binary' },
  { value: 'other', label: 'Other' },
]

const VETERAN_OPTIONS = [
  { value: 'prefer_not', label: 'Prefer not to say' },
  { value: 'not_veteran', label: 'I am not a veteran' },
  { value: 'veteran', label: 'I am a veteran' },
  { value: 'active', label: 'Active duty' },
]

const DISABILITY_OPTIONS = [
  { value: 'prefer_not', label: 'Prefer not to say' },
  { value: 'no', label: 'No disability' },
  { value: 'yes', label: 'Yes, I have a disability' },
]

const DEFAULT_SKILLS = [
  'Python', 'SQL', 'Apache Airflow', 'DBT', 'Power BI',
  'Tableau', 'AWS', 'GCP', 'Azure', 'Snowflake', 'BigQuery', 'Spark', 'Kafka',
]

const RESUME_LABELS = ['Data Engineer', 'Data Analyst', 'Data Science']

// ─── Personal Info Tab ────────────────────────────────────────────────────────

function PersonalInfoTab({ form, setForm }) {
  function f(key) {
    return v => setForm(p => ({ ...p, [key]: v }))
  }

  return (
    <div className="space-y-8">
      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Contact Information</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="Full Name"><Input value={form.name} onChange={f('name')} placeholder="Jane Smith" /></Field>
          <Field label="Email"><Input value={form.email} onChange={f('email')} placeholder="jane@example.com" type="email" /></Field>
          <Field label="Phone"><Input value={form.phone} onChange={f('phone')} placeholder="+1 (555) 000-0000" /></Field>
          <Field label="Location — City"><Input value={form.city} onChange={f('city')} placeholder="San Francisco" /></Field>
          <Field label="State"><Input value={form.state} onChange={f('state')} placeholder="CA" /></Field>
          <Field label="ZIP Code"><Input value={form.zip_code} onChange={f('zip_code')} placeholder="94105" /></Field>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Online Profiles</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="LinkedIn URL"><Input value={form.linkedin_url} onChange={f('linkedin_url')} placeholder="https://linkedin.com/in/…" /></Field>
          <Field label="GitHub URL"><Input value={form.github_url} onChange={f('github_url')} placeholder="https://github.com/…" /></Field>
          <Field label="Portfolio URL" className="col-span-2"><Input value={form.portfolio_url} onChange={f('portfolio_url')} placeholder="https://yoursite.com" /></Field>
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Work Authorization</h3>
        <div className="space-y-4">
          <Toggle
            checked={!!form.work_authorized}
            onChange={v => setForm(p => ({ ...p, work_authorized: v }))}
            label="Authorized to work in the US"
            sublabel="US citizen, permanent resident, or valid work visa"
          />
          <Toggle
            checked={!!form.sponsorship_needed}
            onChange={v => setForm(p => ({ ...p, sponsorship_needed: v }))}
            label="Require visa sponsorship"
            sublabel="Now or in the future"
          />
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-1">Demographics <span className="text-xs text-gray-600 font-normal">(Optional — used for EEO questions)</span></h3>
        <div className="grid grid-cols-2 gap-4 mt-4">
          <Field label="Race / Ethnicity">
            <Select value={form.race_ethnicity} onChange={f('race_ethnicity')} options={RACE_OPTIONS} />
          </Field>
          <Field label="Gender">
            <Select value={form.gender} onChange={f('gender')} options={GENDER_OPTIONS} />
          </Field>
          <Field label="Veteran Status">
            <Select value={form.veteran_status} onChange={f('veteran_status')} options={VETERAN_OPTIONS} />
          </Field>
          <Field label="Disability Status">
            <Select value={form.disability_status} onChange={f('disability_status')} options={DISABILITY_OPTIONS} />
          </Field>
        </div>
      </div>
    </div>
  )
}

// ─── Experience & Skills Tab ──────────────────────────────────────────────────

function ExperienceTab({ form, setForm }) {
  function f(key) {
    return v => setForm(p => ({ ...p, [key]: v }))
  }

  function addSkill() {
    setForm(p => ({ ...p, skills: [...(p.skills || []), { name: '', years: '' }] }))
  }

  function updateSkill(idx, field, val) {
    setForm(p => {
      const skills = [...(p.skills || [])]
      skills[idx] = { ...skills[idx], [field]: val }
      return { ...p, skills }
    })
  }

  function removeSkill(idx) {
    setForm(p => ({ ...p, skills: (p.skills || []).filter((_, i) => i !== idx) }))
  }

  const skills = form.skills || []

  return (
    <div className="space-y-8">
      <div>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-sm font-semibold text-gray-300">Technology Skills</h3>
          <button
            onClick={addSkill}
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            <Plus size={13} /> Add skill
          </button>
        </div>
        <div className="space-y-2.5">
          {skills.map((skill, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <input
                value={skill.name}
                onChange={e => updateSkill(idx, 'name', e.target.value)}
                placeholder="Technology (e.g., Python)"
                className="flex-1 bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 outline-none transition-colors"
              />
              <input
                value={skill.years}
                onChange={e => updateSkill(idx, 'years', e.target.value)}
                placeholder="Experience (e.g., 5 years)"
                className="w-44 bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 outline-none transition-colors"
              />
              <button
                onClick={() => removeSkill(idx)}
                className="text-gray-600 hover:text-red-400 transition-colors shrink-0"
              >
                <Minus size={15} />
              </button>
            </div>
          ))}
          {skills.length === 0 && (
            <p className="text-xs text-gray-600 py-2">No skills added yet. Click "Add skill" above.</p>
          )}
        </div>
      </div>

      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-4">Education</h3>
        <div className="grid grid-cols-2 gap-4">
          <Field label="School / University" className="col-span-2">
            <Input value={form.school} onChange={f('school')} placeholder="University of California, Berkeley" />
          </Field>
          <Field label="Degree">
            <Input value={form.degree} onChange={f('degree')} placeholder="Bachelor of Science" />
          </Field>
          <Field label="Major">
            <Input value={form.major} onChange={f('major')} placeholder="Computer Science" />
          </Field>
          <Field label="Minor">
            <Input value={form.minor} onChange={f('minor')} placeholder="Statistics (optional)" />
          </Field>
          <Field label="GPA">
            <Input value={form.gpa} onChange={f('gpa')} placeholder="3.8" />
          </Field>
          <Field label="Graduation Date">
            <Input value={form.graduation_date} onChange={f('graduation_date')} placeholder="May 2022" />
          </Field>
        </div>
      </div>
    </div>
  )
}

// ─── Resumes Tab ──────────────────────────────────────────────────────────────

function ResumesTab({ resumes, onUpload, onDelete }) {
  const fileRefs = useRef({})

  function handleFileChange(label, file) {
    if (!file) return
    if (file.type !== 'application/pdf') {
      alert('Only PDF files are accepted.')
      return
    }
    onUpload(label, file)
  }

  return (
    <div className="space-y-4">
      <p className="text-xs text-gray-500 mb-6">
        Upload a tailored PDF resume for each role type. The AI will pick the best one based on the job description.
      </p>
      {RESUME_LABELS.map(label => {
        const resume = resumes[label]
        return (
          <div key={label} className="bg-gray-800/60 border border-gray-700/60 rounded-xl p-5">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-gray-700/60 border border-gray-700 flex items-center justify-center shrink-0">
                  <FileText size={18} className="text-indigo-400" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-white">{label}</p>
                  {resume ? (
                    <>
                      <p className="text-xs text-gray-400 mt-0.5">{resume.filename || resume.label}</p>
                      {resume.uploaded_at && (
                        <p className="text-xs text-gray-600 mt-0.5">
                          Uploaded {new Date(resume.uploaded_at).toLocaleDateString()}
                        </p>
                      )}
                    </>
                  ) : (
                    <p className="text-xs text-gray-600 mt-0.5">No resume uploaded</p>
                  )}
                </div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <input
                  ref={el => fileRefs.current[label] = el}
                  type="file"
                  accept=".pdf"
                  className="hidden"
                  onChange={e => handleFileChange(label, e.target.files?.[0])}
                />
                <button
                  onClick={() => fileRefs.current[label]?.click()}
                  className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-400 rounded-lg transition-colors"
                >
                  <Upload size={12} />
                  {resume ? 'Replace' : 'Upload PDF'}
                </button>
                {resume && (
                  <button
                    onClick={() => onDelete(label)}
                    className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 rounded-lg transition-colors"
                  >
                    <Trash2 size={12} />
                    Delete
                  </button>
                )}
              </div>
            </div>

            {/* Text preview */}
            {resume?.text_preview && (
              <div className="mt-4 border-t border-gray-700/50 pt-3">
                <p className="text-xs text-gray-600 uppercase tracking-wider font-semibold mb-1.5">Content preview</p>
                <p className="text-xs text-gray-500 leading-relaxed font-mono line-clamp-3">
                  {resume.text_preview.slice(0, 200)}…
                </p>
              </div>
            )}
          </div>
        )
      })}
    </div>
  )
}

// ─── Cover Letter Tab ─────────────────────────────────────────────────────────

function CoverLetterTab({ form, setForm }) {
  function f(key) {
    return v => setForm(p => ({ ...p, [key]: v }))
  }

  return (
    <div className="space-y-6">
      <div>
        <Field label="Cover Letter Template">
          <textarea
            value={form.cover_letter_template || ''}
            onChange={e => setForm(p => ({ ...p, cover_letter_template: e.target.value }))}
            rows={10}
            placeholder="Write a cover letter template. Use {{job_title}}, {{company}}, {{your_name}} as placeholders…"
            className="w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-4 py-3 text-sm text-white placeholder-gray-600 outline-none transition-colors resize-y leading-relaxed"
          />
        </Field>
        <p className="text-xs text-gray-600 mt-1.5">Use placeholders: {'{{job_title}}'}, {'{{company}}'}, {'{{your_name}}'}, {'{{today_date}}'}</p>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Field label="Salary Expectation">
          <Input value={form.salary_expectation} onChange={f('salary_expectation')} placeholder="e.g., $120,000 – $150,000" />
        </Field>
        <Field label="Available Start Date">
          <Input value={form.start_date} onChange={f('start_date')} placeholder="e.g., Immediately, 2 weeks notice" />
        </Field>
      </div>

      <Toggle
        checked={!!form.willing_to_relocate}
        onChange={v => setForm(p => ({ ...p, willing_to_relocate: v }))}
        label="Willing to relocate"
        sublabel="Shown when applications ask about relocation"
      />
    </div>
  )
}

// ─── Main Profile page ────────────────────────────────────────────────────────

export default function Profile() {
  const [activeTab, setActiveTab] = useState('personal')
  const [form, setForm] = useState({})
  const [resumes, setResumes] = useState({})
  const [saving, setSaving] = useState(false)
  const [toast, setToast] = useState(null)

  useEffect(() => {
    loadProfile()
    loadResumes()
  }, [])

  async function loadProfile() {
    try {
      const data = await getProfile()
      if (data) {
        // Normalize skills from object to array if needed
        let skills = data.skills || data.technology_skills || []
        if (!Array.isArray(skills)) {
          skills = Object.entries(skills).map(([name, years]) => ({ name, years }))
        }
        if (skills.length === 0) {
          skills = DEFAULT_SKILLS.map(name => ({ name, years: '' }))
        }
        setForm({ ...data, skills })
      } else {
        setForm({ skills: DEFAULT_SKILLS.map(name => ({ name, years: '' })) })
      }
    } catch {
      setForm({ skills: DEFAULT_SKILLS.map(name => ({ name, years: '' })) })
    }
  }

  async function loadResumes() {
    try {
      const data = await getResumes()
      const map = {}
      if (Array.isArray(data)) {
        data.forEach(r => { map[r.label || r.filename] = r })
      } else if (data && typeof data === 'object') {
        Object.assign(map, data)
      }
      setResumes(map)
    } catch {
      // ignore
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      // Convert skills array to object for API
      const skillsObj = {}
      ;(form.skills || []).forEach(s => {
        if (s.name) skillsObj[s.name] = s.years
      })
      const payload = { ...form, skills: skillsObj, technology_skills: skillsObj }
      await updateProfile(payload)
      setToast({ type: 'success', message: 'Profile saved successfully.' })
    } catch (err) {
      setToast({ type: 'error', message: err.message || 'Failed to save profile.' })
    } finally {
      setSaving(false)
    }
  }

  async function handleUpload(label, file) {
    try {
      const result = await uploadResume(file, label)
      setResumes(prev => ({ ...prev, [label]: result }))
      setToast({ type: 'success', message: `${label} resume uploaded.` })
    } catch (err) {
      setToast({ type: 'error', message: err.message || 'Upload failed.' })
    }
  }

  async function handleDelete(label) {
    try {
      await deleteResume(label)
      setResumes(prev => {
        const next = { ...prev }
        delete next[label]
        return next
      })
      setToast({ type: 'success', message: `${label} resume deleted.` })
    } catch (err) {
      setToast({ type: 'error', message: err.message || 'Delete failed.' })
    }
  }

  return (
    <div className="min-h-screen p-6 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Profile</h1>
        <p className="text-gray-500 text-sm mt-1">Your information, skills, and resumes used during auto-apply.</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-900 border border-gray-700/60 rounded-xl p-1 mb-8 overflow-x-auto">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={clsx(
              'flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-150 whitespace-nowrap',
              activeTab === id
                ? 'bg-indigo-600 text-white shadow'
                : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
            )}
          >
            <Icon size={14} />
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="bg-gray-900 border border-gray-700/60 rounded-xl p-6 mb-6">
        {activeTab === 'personal' && <PersonalInfoTab form={form} setForm={setForm} />}
        {activeTab === 'experience' && <ExperienceTab form={form} setForm={setForm} />}
        {activeTab === 'resumes' && <ResumesTab resumes={resumes} onUpload={handleUpload} onDelete={handleDelete} />}
        {activeTab === 'coverletter' && <CoverLetterTab form={form} setForm={setForm} />}
      </div>

      {/* Save button (not shown on resumes tab — saved per upload) */}
      {activeTab !== 'resumes' && (
        <div className="flex justify-end">
          <button
            onClick={handleSave}
            disabled={saving}
            className="flex items-center gap-2 px-6 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-900 disabled:text-indigo-600 text-white text-sm font-semibold rounded-xl transition-all duration-150 shadow-lg shadow-indigo-900/40"
          >
            {saving ? <Loader2 size={15} className="animate-spin" /> : <CheckCircle size={15} />}
            {saving ? 'Saving…' : 'Save Profile'}
          </button>
        </div>
      )}

      {/* Toast */}
      {toast && <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />}
    </div>
  )
}
