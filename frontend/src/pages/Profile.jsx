import React, { useState, useEffect, useRef } from 'react'
import {
  User, Briefcase, Target, Mail, CheckCircle, AlertCircle,
  Upload, Trash2, Plus, Minus, Loader2, ChevronDown, ChevronRight,
  FileText, X,
} from 'lucide-react'
import clsx from 'clsx'
import { getProfile, updateProfile, getResumes, uploadResume, deleteResume } from '../api/client.js'

// ─── Helpers ─────────────────────────────────────────────────────────────────

function Toggle({ checked, onChange, label, sublabel }) {
  return (
    <label className="flex items-start gap-3 cursor-pointer group">
      <div
        className={clsx(
          'relative mt-0.5 rounded-full transition-colors duration-200 shrink-0',
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
      'fixed bottom-6 right-6 z-50 flex items-center gap-2.5 px-4 py-3 rounded-xl border shadow-xl text-sm font-medium',
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
  { id: 'personal',     label: 'Personal Info',     icon: User },
  { id: 'experience',   label: 'Education & Skills', icon: Briefcase },
  { id: 'roles',        label: 'Roles',              icon: Target },
  { id: 'coverletter',  label: 'Defaults',           icon: Mail },
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
          <Field label="City"><Input value={form.city} onChange={f('city')} placeholder="San Francisco" /></Field>
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
        <h3 className="text-sm font-semibold text-gray-300 mb-1">
          Demographics <span className="text-xs text-gray-600 font-normal">(Optional — EEO questions)</span>
        </h3>
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

// ─── Education & Skills Tab ───────────────────────────────────────────────────

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
          <button onClick={addSkill} className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
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
                placeholder="Years (e.g., 5)"
                className="w-36 bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 outline-none transition-colors"
              />
              <button onClick={() => removeSkill(idx)} className="text-gray-600 hover:text-red-400 transition-colors shrink-0">
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

// ─── Work Experience Entry ────────────────────────────────────────────────────

function WorkExpEntry({ entry, index, onChange, onRemove }) {
  const [open, setOpen] = useState(index === 0)

  return (
    <div className="bg-gray-800/60 border border-gray-700/50 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-gray-800 transition-colors"
      >
        {open ? <ChevronDown size={13} className="text-gray-500 shrink-0" /> : <ChevronRight size={13} className="text-gray-500 shrink-0" />}
        <span className="text-sm font-medium text-white flex-1 truncate">
          {entry.title || entry.company
            ? `${entry.title || '(no title)'}${entry.company ? ' · ' + entry.company : ''}`
            : `Job ${index + 1}`}
        </span>
        {index === 0 && <span className="text-xs text-indigo-400 font-medium shrink-0">Most Recent</span>}
        <button
          onClick={e => { e.stopPropagation(); onRemove() }}
          className="text-gray-600 hover:text-red-400 transition-colors shrink-0 ml-1"
        >
          <Trash2 size={13} />
        </button>
      </button>

      {open && (
        <div className="px-4 pb-4 space-y-3 border-t border-gray-700/50 pt-3">
          <div className="grid grid-cols-2 gap-3">
            <Field label="Company">
              <Input value={entry.company} onChange={v => onChange('company', v)} placeholder="Acme Corp" />
            </Field>
            <Field label="Job Title">
              <Input value={entry.title} onChange={v => onChange('title', v)} placeholder="Senior Data Engineer" />
            </Field>
            <Field label="Start Date">
              <Input value={entry.start_date} onChange={v => onChange('start_date', v)} placeholder="Jan 2022" />
            </Field>
            <Field label="End Date">
              <Input value={entry.end_date} onChange={v => onChange('end_date', v)} placeholder="Present" />
            </Field>
          </div>
          <Field label="Description / Responsibilities">
            <textarea
              value={entry.description || ''}
              onChange={e => onChange('description', e.target.value)}
              rows={4}
              placeholder="Describe your responsibilities and key achievements. This text is used to fill 'job description' fields on application forms."
              className="w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-600 outline-none transition-colors resize-y leading-relaxed"
            />
          </Field>
        </div>
      )}
    </div>
  )
}

// ─── Role Editor ─────────────────────────────────────────────────────────────

function RoleEditor({ roleName, config, resume, onConfigChange, onUpload, onDeleteResume, onDeleteRole }) {
  const fileRef = useRef(null)
  const wx = config.work_experience || []

  function addEntry() {
    onConfigChange({ ...config, work_experience: [...wx, { company: '', title: '', start_date: '', end_date: '', description: '' }] })
  }

  function updateEntry(idx, field, val) {
    const entries = wx.map((e, i) => i === idx ? { ...e, [field]: val } : e)
    onConfigChange({ ...config, work_experience: entries })
  }

  function removeEntry(idx) {
    onConfigChange({ ...config, work_experience: wx.filter((_, i) => i !== idx) })
  }

  function handleFileChange(file) {
    if (!file) return
    if (file.type !== 'application/pdf') { alert('Only PDF files are accepted.'); return }
    onUpload(file)
  }

  return (
    <div className="space-y-6">
      {/* Resume */}
      <div className="bg-gray-800/40 border border-gray-700/50 rounded-xl p-4">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gray-700/60 border border-gray-700 flex items-center justify-center shrink-0">
              <FileText size={16} className={resume ? 'text-indigo-400' : 'text-gray-600'} />
            </div>
            <div>
              <p className="text-sm font-medium text-white">Resume PDF</p>
              {resume ? (
                <p className="text-xs text-gray-400 mt-0.5">
                  {resume.file_name || resume.label}
                  {resume.uploaded_at && <span className="text-gray-600 ml-1.5">· {new Date(resume.uploaded_at).toLocaleDateString()}</span>}
                </p>
              ) : (
                <p className="text-xs text-gray-600 mt-0.5">No PDF uploaded</p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <input ref={fileRef} type="file" accept=".pdf" className="hidden" onChange={e => handleFileChange(e.target.files?.[0])} />
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-indigo-600/20 hover:bg-indigo-600/30 border border-indigo-500/30 text-indigo-400 rounded-lg transition-colors"
            >
              <Upload size={12} /> {resume ? 'Replace' : 'Upload PDF'}
            </button>
            {resume && (
              <button
                onClick={onDeleteResume}
                className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 text-red-400 rounded-lg transition-colors"
              >
                <Trash2 size={12} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Work Experience */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-sm font-semibold text-gray-300">Work Experience</h3>
            <p className="text-xs text-gray-600 mt-0.5">
              Entries fill employer/title/description fields on application forms. First entry = most recent job.
            </p>
          </div>
          <button
            onClick={addEntry}
            className="flex items-center gap-1.5 text-xs text-indigo-400 hover:text-indigo-300 transition-colors shrink-0"
          >
            <Plus size={13} /> Add job
          </button>
        </div>
        <div className="space-y-2">
          {wx.map((entry, idx) => (
            <WorkExpEntry
              key={idx}
              entry={entry}
              index={idx}
              onChange={(field, val) => updateEntry(idx, field, val)}
              onRemove={() => removeEntry(idx)}
            />
          ))}
          {wx.length === 0 && (
            <div className="text-center py-6 border border-dashed border-gray-700/50 rounded-xl">
              <p className="text-xs text-gray-600">No work experience added yet.</p>
              <button onClick={addEntry} className="mt-2 text-xs text-indigo-400 hover:text-indigo-300 transition-colors">
                + Add first job
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Role-specific cover letter */}
      <div>
        <h3 className="text-sm font-semibold text-gray-300 mb-1">Cover Letter Override</h3>
        <p className="text-xs text-gray-600 mb-2">
          Used instead of the base cover letter when applying for <span className="text-gray-400">{roleName}</span> roles. Leave blank to use the default.
        </p>
        <textarea
          value={config.cover_letter_template || ''}
          onChange={e => onConfigChange({ ...config, cover_letter_template: e.target.value })}
          rows={6}
          placeholder="Write a cover letter specific to this role. Use {{job_title}}, {{company}}, {{your_name}} as placeholders…"
          className="w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-4 py-3 text-sm text-white placeholder-gray-600 outline-none transition-colors resize-y leading-relaxed"
        />
      </div>

      {/* Delete role */}
      <div className="pt-2 border-t border-gray-800">
        <button
          onClick={onDeleteRole}
          className="flex items-center gap-1.5 text-xs text-red-500/70 hover:text-red-400 transition-colors"
        >
          <Trash2 size={12} /> Delete "{roleName}" role
        </button>
      </div>
    </div>
  )
}

// ─── Roles Tab ────────────────────────────────────────────────────────────────

function RolesTab({ form, setForm, resumes, onUpload, onDelete }) {
  const [activeRole, setActiveRole] = useState(null)
  const [addingRole, setAddingRole] = useState(false)
  const [newRoleName, setNewRoleName] = useState('')

  const roles = form.roles || {}
  const allRoleNames = [...new Set([...Object.keys(roles), ...Object.keys(resumes)])]

  // Auto-select first role
  useEffect(() => {
    if (!activeRole && allRoleNames.length > 0) setActiveRole(allRoleNames[0])
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  function addRole() {
    const name = newRoleName.trim()
    if (!name) return
    setForm(p => ({
      ...p,
      roles: { ...(p.roles || {}), [name]: { work_experience: [], cover_letter_template: '' } },
    }))
    setActiveRole(name)
    setNewRoleName('')
    setAddingRole(false)
  }

  function deleteRole(name) {
    setForm(p => {
      const next = { ...(p.roles || {}) }
      delete next[name]
      return { ...p, roles: next }
    })
    if (activeRole === name) setActiveRole(allRoleNames.find(r => r !== name) || null)
  }

  function updateRoleConfig(name, config) {
    setForm(p => ({
      ...p,
      roles: { ...(p.roles || {}), [name]: config },
    }))
  }

  const config = roles[activeRole] || { work_experience: [], cover_letter_template: '' }

  return (
    <div>
      {/* Role selector */}
      <div className="flex items-center gap-2 flex-wrap mb-6">
        {allRoleNames.map(name => (
          <button
            key={name}
            onClick={() => setActiveRole(name)}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-all',
              activeRole === name
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-white hover:bg-gray-700 border border-gray-700'
            )}
          >
            {name}
            {resumes[name] && <span className="w-1.5 h-1.5 rounded-full bg-green-400 shrink-0" title="Resume uploaded" />}
          </button>
        ))}

        {addingRole ? (
          <div className="flex items-center gap-1.5">
            <input
              autoFocus
              value={newRoleName}
              onChange={e => setNewRoleName(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') addRole(); if (e.key === 'Escape') { setAddingRole(false); setNewRoleName('') } }}
              placeholder="Role name (e.g., Backend Engineer)"
              className="bg-gray-800 border border-indigo-500 rounded-lg px-3 py-1.5 text-sm text-white placeholder-gray-600 outline-none w-56"
            />
            <button onClick={addRole} className="text-green-400 hover:text-green-300 text-xs px-2 py-1.5">Add</button>
            <button onClick={() => { setAddingRole(false); setNewRoleName('') }} className="text-gray-500 hover:text-gray-300 text-xs px-1 py-1.5"><X size={13} /></button>
          </div>
        ) : (
          <button
            onClick={() => setAddingRole(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-gray-500 hover:text-indigo-400 border border-dashed border-gray-700 hover:border-indigo-500/50 transition-all"
          >
            <Plus size={12} /> Add Role
          </button>
        )}
      </div>

      {allRoleNames.length === 0 && (
        <div className="text-center py-12 border border-dashed border-gray-700/50 rounded-xl">
          <Target size={28} className="text-gray-700 mx-auto mb-3" />
          <p className="text-sm text-gray-500 font-medium">No roles yet</p>
          <p className="text-xs text-gray-600 mt-1 mb-4">Add a role for each type of job you're applying to.</p>
          <button
            onClick={() => setAddingRole(true)}
            className="text-xs text-indigo-400 hover:text-indigo-300 transition-colors"
          >
            + Add your first role
          </button>
        </div>
      )}

      {activeRole && (
        <RoleEditor
          key={activeRole}
          roleName={activeRole}
          config={config}
          resume={resumes[activeRole]}
          onConfigChange={cfg => updateRoleConfig(activeRole, cfg)}
          onUpload={file => onUpload(activeRole, file)}
          onDeleteResume={() => onDelete(activeRole)}
          onDeleteRole={() => deleteRole(activeRole)}
        />
      )}
    </div>
  )
}

// ─── Defaults Tab ─────────────────────────────────────────────────────────────

function DefaultsTab({ form, setForm }) {
  function f(key) {
    return v => setForm(p => ({ ...p, [key]: v }))
  }

  return (
    <div className="space-y-6">
      <div>
        <Field label="Base Cover Letter Template">
          <textarea
            value={form.cover_letter_template || ''}
            onChange={e => setForm(p => ({ ...p, cover_letter_template: e.target.value }))}
            rows={10}
            placeholder="Write a base cover letter. Use {{job_title}}, {{company}}, {{your_name}} as placeholders…"
            className="w-full bg-gray-800 border border-gray-700 focus:border-indigo-500 rounded-lg px-4 py-3 text-sm text-white placeholder-gray-600 outline-none transition-colors resize-y leading-relaxed"
          />
        </Field>
        <p className="text-xs text-gray-600 mt-1.5">
          Fallback used when no role-specific cover letter is set. Placeholders: {'{{job_title}}'}, {'{{company}}'}, {'{{your_name}}'}, {'{{today_date}}'}
        </p>
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
        let skills = data.skills || data.technology_skills || []
        if (!Array.isArray(skills)) {
          skills = Object.entries(skills).map(([name, years]) => ({ name, years }))
        }
        if (skills.length === 0) {
          skills = DEFAULT_SKILLS.map(name => ({ name, years: '' }))
        }
        setForm({ ...data, skills, roles: data.roles || {} })
      } else {
        setForm({ skills: DEFAULT_SKILLS.map(name => ({ name, years: '' })), roles: {} })
      }
    } catch {
      setForm({ skills: DEFAULT_SKILLS.map(name => ({ name, years: '' })), roles: {} })
    }
  }

  async function loadResumes() {
    try {
      const data = await getResumes()
      const map = {}
      if (Array.isArray(data)) {
        data.forEach(r => { map[r.label || r.filename] = r })
      }
      setResumes(map)
    } catch { /* ignore */ }
  }

  async function handleSave() {
    setSaving(true)
    try {
      const skillsObj = {}
      ;(form.skills || []).forEach(s => { if (s.name) skillsObj[s.name] = s.years })
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
      // Ensure a role config entry exists for this label
      setForm(prev => ({
        ...prev,
        roles: {
          [label]: { work_experience: [], cover_letter_template: '' },
          ...(prev.roles || {}),
        },
      }))
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

  const showSaveButton = activeTab !== 'roles'

  return (
    <div className="min-h-screen p-6 max-w-3xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-white tracking-tight">Profile</h1>
        <p className="text-gray-500 text-sm mt-1">Your information, roles, and resumes used during auto-apply.</p>
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
        {activeTab === 'roles' && (
          <RolesTab
            form={form}
            setForm={setForm}
            resumes={resumes}
            onUpload={handleUpload}
            onDelete={handleDelete}
          />
        )}
        {activeTab === 'coverletter' && <DefaultsTab form={form} setForm={setForm} />}
      </div>

      {/* Save button — Roles tab auto-saves changes to form state; explicit save commits to DB */}
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

      {toast && <Toast type={toast.type} message={toast.message} onDismiss={() => setToast(null)} />}
    </div>
  )
}
