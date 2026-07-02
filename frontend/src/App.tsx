import { useMemo, useState, type ReactNode } from "react";
import {
  Apple,
  Bell,
  BrainCircuit,
  CalendarDays,
  CheckCircle2,
  ChevronDown,
  Code2,
  Database,
  Download,
  Gauge,
  Grid2X2,
  Layers3,
  LineChart,
  LockKeyhole,
  Medal,
  MessageSquareText,
  MonitorSmartphone,
  Search,
  Send,
  Settings,
  Share2,
  ShieldCheck,
  Sparkles,
  Star,
  TerminalSquare,
  Upload,
  UserCircle,
  UsersRound,
  X,
} from "lucide-react";

type Page = "dashboard" | "interviews" | "reports" | "profile";

const navItems = [
  { id: "dashboard", label: "Dashboard", icon: Grid2X2 },
  { id: "interviews", label: "Interviews", icon: MessageSquareText },
  { id: "reports", label: "Reports", icon: LineChart },
  { id: "profile", label: "Profile", icon: UserCircle },
] satisfies Array<{ id: Page; label: string; icon: typeof Grid2X2 }>;

const jobs = [
  { initials: "SE", title: "SEO Expert", created: "Created 2 days ago", status: "Active", difficulty: "Intermediate", candidates: "14 Candidates", color: "lilac" },
  { initials: "UX", title: "Product Designer", created: "Created 3 days ago", status: "Active", difficulty: "Mid", candidates: "12 Candidates", color: "mint" },
  { initials: "QA", title: "QA Automation Engineer", created: "Created 4 days ago", status: "Paused", difficulty: "Intermediate", candidates: "8 Candidates", color: "rose" },
  { initials: "ND", title: "Senior Node.js Developer", created: "Created 5 days ago", status: "Draft", difficulty: "Expert", candidates: "0 Candidates", color: "blue" },
];

const scheduledInterviews = [
  { time: "10:30", name: "Maya Chen", role: "Frontend Engineer", score: "8.4", status: "Ready" },
  { time: "12:00", name: "Omar Saleh", role: "Backend Engineer", score: "7.8", status: "Pending" },
  { time: "14:15", name: "Nina Patel", role: "Product Designer", score: "8.1", status: "Ready" },
];

const activity = [
  "AI scored 4 new candidate answers",
  "SEO Expert job moved to Active",
  "2 candidates need manual review",
  "Node.js draft is missing 3 questions",
];

const seniorityOptions = [
  { title: "Junior", icon: Medal, description: "Foundational knowledge, syntax proficiency, and problem-solving fundamentals." },
  { title: "Mid-level", icon: Gauge, description: "System design basics, optimized algorithms, and autonomous delivery skills." },
  { title: "Senior", icon: ShieldCheck, description: "Scalability, leadership, complex architecture, and strategic engineering." },
];

const roleCategories = [
  { title: "Frontend", icon: Code2 },
  { title: "Backend", icon: Database },
  { title: "Fullstack", icon: Layers3 },
  { title: "Mobile", icon: MonitorSmartphone },
  { title: "DevOps", icon: TerminalSquare },
];

const reportScores = [
  { label: "Answer Accuracy", value: 80 },
  { label: "Detail Level", value: 90 },
  { label: "Technical Terminology", value: 65 },
  { label: "Explanation Quality", value: 85 },
];

const reportQuestions = [
  {
    id: "01",
    question: "How do you handle race conditions in high-concurrency systems?",
    score: 92,
    response:
      "I typically employ optimistic locking at the database level for most CRUD operations. For complex distributed systems, I lean toward Redis-based distributed locks or message queuing to linearize state changes.",
    insight:
      "The candidate correctly identified multiple concurrency strategies and explained tradeoffs with strong practical experience.",
  },
  { id: "02", question: "Can you explain the differences between gRPC and REST?", score: 78 },
  { id: "03", question: "Describe your approach to API versioning in a public-facing service.", score: 88 },
];

function App() {
  const [isSignedIn, setIsSignedIn] = useState(false);
  const [page, setPage] = useState<Page>("dashboard");
  const [seniority, setSeniority] = useState("Mid-level");
  const [role, setRole] = useState("Frontend");

  const pageTitle = useMemo(() => {
    if (page === "dashboard") return "System Overview";
    if (page === "interviews") return "Choose Your Interview Path";
    if (page === "reports") return "Candidate AI Assessment";
    return "Account Settings";
  }, [page]);

  if (!isSignedIn) {
    return <LoginPage onSignIn={() => setIsSignedIn(true)} />;
  }

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <BrainCircuit size={24} strokeWidth={2.4} />
          </div>
          <div>
            <strong>InterviewAI</strong>
            <span>AI-DRIVEN INSIGHTS</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <button className={page === item.id ? "nav-item active" : "nav-item"} key={item.id} onClick={() => setPage(item.id)}>
                <Icon size={21} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-user">
          <div className="mini-avatar">AS</div>
          <div>
            <strong>Alex Sterling</strong>
            <span>HR Director</span>
          </div>
        </div>

        <button className="new-interview" onClick={() => setPage("interviews")}>
          <Send size={18} />
          <span>New Interview</span>
        </button>
      </aside>

      <section className="workspace">
        <header className="topbar">
          <label className="search-box">
            <Search size={20} />
            <input placeholder={page === "profile" ? "Search settings..." : page === "interviews" ? "Search paths, candidates..." : "Search candidates..."} />
          </label>
          <div className="topbar-actions">
            <button className="icon-button alert" aria-label="Notifications">
              <Bell size={21} />
            </button>
            <button className="icon-button" aria-label="Settings" onClick={() => setPage("profile")}>
              <Settings size={22} />
            </button>
            <button className="avatar-button" aria-label="Profile" onClick={() => setPage("profile")}>
              AS
            </button>
          </div>
        </header>

        <div className="content">
          {page === "dashboard" && <DashboardPage />}
          {page === "interviews" && (
            <InterviewPathPage
              pageTitle={pageTitle}
              role={role}
              seniority={seniority}
              setRole={setRole}
              setSeniority={setSeniority}
            />
          )}
          {page === "reports" && <ReportsPage />}
          {page === "profile" && <ProfilePage />}
        </div>
      </section>
    </main>
  );
}

function LoginPage({ onSignIn }: { onSignIn: () => void }) {
  return (
    <main className="login-shell">
      <section className="login-hero">
        <div className="brand login-brand">
          <div className="brand-mark">
            <BrainCircuit size={24} />
          </div>
          <div>
            <strong>InterviewAI</strong>
            <span>AI-DRIVEN INSIGHTS</span>
          </div>
        </div>
        <div className="login-copy">
          <p>Hiring intelligence platform</p>
          <h1>Assess technical talent with consistent AI-backed evidence.</h1>
          <div className="login-proof">
            <span>32 active jobs</span>
            <span>148 candidate assessments</span>
            <span>91% reviewer agreement</span>
          </div>
        </div>
      </section>
      <section className="login-panel">
        <div>
          <h2>Welcome back</h2>
          <p>Sign in to manage interviews, reports, and hiring decisions.</p>
        </div>
        <div className="oauth-grid">
          <button onClick={onSignIn}><GoogleMark /> Google</button>
          <button onClick={onSignIn}><Apple size={19} /> Apple</button>
          <button onClick={onSignIn}><X size={18} /> X</button>
        </div>
        <div className="divider">or continue with email</div>
        <form className="login-form" onSubmit={(event) => { event.preventDefault(); onSignIn(); }}>
          <label>
            Email address
            <input type="email" defaultValue="alex.sterling@corporate.ai" />
          </label>
          <label>
            Password
            <input type="password" defaultValue="interviewai" />
          </label>
          <button className="primary-action full" type="submit">Sign In</button>
        </form>
      </section>
    </main>
  );
}

function DashboardPage() {
  return (
    <>
      <section className="page-heading">
        <div>
          <h1>System Overview</h1>
          <p>Track interviews, jobs, candidates, and AI assessment quality from one workspace.</p>
        </div>
        <button className="primary-action">
          <Sparkles size={20} />
          <span>New AI Job</span>
        </button>
      </section>

      <section className="metrics-grid" aria-label="Interview metrics">
        <MetricCard icon={<UsersRound size={23} />} label="TOTAL INTERVIEWS" value="6" tone="soft" trend="+12% from last month" />
        <MetricCard icon={<ShieldCheck size={23} />} label="SUCCESS RATE" value="25%" tone="green" trend="-4% needs review" bad />
        <article className="metric-card dark">
          <div className="metric-icon dark-icon"><LineChart size={24} /></div>
          <p>AVG AI SCORE</p>
          <strong>1.9<span>/10</span></strong>
        </article>
      </section>

      <section className="analysis-grid">
        <article className="trend-panel">
          <div className="panel-title">
            <h2>Interview Completion Trend</h2>
            <div className="segmented"><button>7 Days</button><button className="selected">30 Days</button></div>
          </div>
          <div className="chart-canvas" aria-label="Interview completion trend chart">
            <svg viewBox="0 0 760 360" role="img">
              <defs>
                <linearGradient id="areaFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#08784e" stopOpacity="0.26" />
                  <stop offset="74%" stopColor="#08784e" stopOpacity="0.04" />
                  <stop offset="100%" stopColor="#08784e" stopOpacity="0" />
                </linearGradient>
              </defs>
              <path className="area" d="M28 328 C180 330 300 324 412 320 C510 316 548 252 590 178 C635 92 674 36 712 70 C733 89 728 144 728 206 L728 340 L28 340 Z" />
              <path className="line" d="M28 328 C180 330 300 324 412 320 C510 316 548 252 590 178 C635 92 674 36 712 70 C733 89 728 144 728 206" />
            </svg>
          </div>
        </article>
        <DifficultyPanel />
      </section>

      <section className="operations-grid">
        <TodayInterviews />
        <ActivityPanel />
      </section>
      <JobsTable />
    </>
  );
}

function InterviewPathPage({
  pageTitle,
  seniority,
  role,
  setSeniority,
  setRole,
}: {
  pageTitle: string;
  seniority: string;
  role: string;
  setSeniority: (value: string) => void;
  setRole: (value: string) => void;
}) {
  return (
    <>
      <section className="page-heading interview-heading">
        <div>
          <h1>{pageTitle}</h1>
          <p>Configure the AI assessment engine by selecting the technical seniority and domain focus required for your candidate.</p>
        </div>
      </section>

      <section className="path-layout">
        <div>
          <div className="section-eyebrow"><LineChart size={18} /> SELECT SENIORITY</div>
          <div className="seniority-grid">
            {seniorityOptions.map((option) => {
              const Icon = option.icon;
              return (
                <button className={seniority === option.title ? "seniority-card selected" : "seniority-card"} key={option.title} onClick={() => setSeniority(option.title)}>
                  <span><Icon size={24} /></span>
                  <strong>{option.title}</strong>
                  <p>{option.description}</p>
                </button>
              );
            })}
          </div>
        </div>

        <aside>
          <div className="section-eyebrow"><Layers3 size={18} /> ROLE CATEGORIES</div>
          <div className="role-card">
            {roleCategories.map((category) => {
              const Icon = category.icon;
              return (
                <button className={role === category.title ? "role-option active" : "role-option"} key={category.title} onClick={() => setRole(category.title)}>
                  <Icon size={21} />
                  <span>{category.title}</span>
                </button>
              );
            })}
          </div>
        </aside>
      </section>

      <section className="path-summary">
        <div className="summary-icons"><BrainCircuit size={24} /><Sparkles size={24} /></div>
        <div>
          <p>PATH OPTIMIZED</p>
          <h2>{seniority} {role} Specialist</h2>
          <span>45 mins</span>
          <span>12 Tasks</span>
          <span>AI Proctoring</span>
        </div>
        <button className="primary-action dark-action">Begin Assessment <Send size={18} /></button>
      </section>
    </>
  );
}

function ReportsPage() {
  return (
    <>
      <section className="report-heading">
        <div>
          <p>Reports › Sarah Chen</p>
          <h1>Candidate AI Assessment</h1>
        </div>
        <div className="report-actions">
          <button><Share2 size={18} /> Share</button>
          <button className="dark-action"><Download size={18} /> Download PDF</button>
        </div>
      </section>

      <section className="report-overview">
        <article className="match-card">
          <div className="match-ring"><strong>85%</strong><span>Overall Match</span></div>
          <div className="recommend-pill"><CheckCircle2 size={17} /> Shortlist Recommended</div>
          <p>Exceptional technical knowledge and communication skills identified by InterviewAI.</p>
        </article>
        <article className="breakdown-card">
          <h2>Analysis Breakdown</h2>
          <div className="score-grid">
            {reportScores.map((score) => (
              <div className="score-line" key={score.label}>
                <div><span>{score.label}</span><b>{score.value}%</b></div>
                <div className="score-track"><i style={{ width: `${score.value}%` }} /></div>
              </div>
            ))}
          </div>
          <blockquote>
            <Sparkles size={19} />
            The candidate demonstrates a strong understanding of system design principles. Clarity and depth of explanations offset moderate terminology gaps.
          </blockquote>
        </article>
      </section>

      <section className="question-section">
        <h2>Question-by-Question Insights</h2>
        {reportQuestions.map((item, index) => (
          <article className={index === 0 ? "question-card open" : "question-card"} key={item.id}>
            <header>
              <span>{item.id}</span>
              <p>{item.question}</p>
              <b>Score: {item.score}%</b>
              <ChevronDown size={18} />
            </header>
            {index === 0 && (
              <div className="question-body">
                <div>
                  <h3>CANDIDATE RESPONSE</h3>
                  <p>{item.response}</p>
                </div>
                <div className="ai-insight">
                  <h3><BrainCircuit size={17} /> AI Insights</h3>
                  <p>{item.insight}</p>
                </div>
              </div>
            )}
          </article>
        ))}
      </section>

      <section className="recommendation-card">
        <div>
          <h2>Final Recommendation</h2>
          <p>Based on technical depth and structured communication, we recommend moving Sarah Chen to the final interview stage with the Engineering Lead.</p>
        </div>
        <div>
          <button className="reject"><X size={18} /> Reject</button>
          <button className="primary-action"><Star size={18} /> Shortlist</button>
        </div>
      </section>
    </>
  );
}

function ProfilePage() {
  return (
    <>
      <section className="settings-title"><h1>Account Settings</h1></section>
      <section className="profile-grid">
        <article className="profile-card">
          <div className="large-avatar">AS</div>
          <h2>Alex Sterling</h2>
          <p>Senior Talent Acquisition Director</p>
          <button className="dark-action"><Upload size={17} /> Update Photo</button>
          <button>Remove</button>
          <div className="completion">
            <div><span>Profile Completion</span><b>85%</b></div>
            <div><i /></div>
          </div>
        </article>

        <article className="settings-card">
          <div className="panel-title"><h2>Personal Information</h2><ShieldCheck size={24} /></div>
          <div className="form-grid">
            <label>FULL NAME<input defaultValue="Alex Sterling" /></label>
            <label>EMAIL ADDRESS<input defaultValue="alex.sterling@corporate.ai" /></label>
            <label>JOB TITLE<input defaultValue="Senior Talent Acquisition Director" /></label>
            <label>DEPARTMENT<select defaultValue="Human Resources"><option>Human Resources</option><option>Engineering</option></select></label>
            <label className="wide">BIO<textarea defaultValue="Over 12 years of experience in technical recruiting and talent strategy. Passionate about leveraging AI to create more equitable hiring processes." /></label>
          </div>
          <div className="form-actions"><button>Discard Changes</button><button className="dark-action">Save Details</button></div>
        </article>

        <article className="security-hero">
          <h2>Security & Integrity</h2>
          <p>Manage account protection, authentication methods, and active sessions to ensure your data remains secure.</p>
        </article>

        <article className="settings-card">
          <div className="panel-title"><h2><LockKeyhole size={23} /> Change Password</h2></div>
          <div className="form-grid">
            <label>CURRENT PASSWORD<input type="password" defaultValue="password" /></label>
            <span />
            <label>NEW PASSWORD<input type="password" defaultValue="password" /></label>
            <label>CONFIRM NEW PASSWORD<input type="password" defaultValue="password" /></label>
          </div>
          <div className="form-actions"><button className="primary-action">Update Password</button></div>
        </article>
      </section>
    </>
  );
}

function MetricCard({ icon, label, value, tone, trend, bad }: { icon: ReactNode; label: string; value: string; tone: string; trend: string; bad?: boolean }) {
  return (
    <article className="metric-card">
      <div className="metric-top">
        <div className={`metric-icon ${tone}`}>{icon}</div>
        <span className={bad ? "trend bad" : "trend good"}>{trend}</span>
      </div>
      <p>{label}</p>
      <strong>{value}</strong>
    </article>
  );
}

function DifficultyPanel() {
  return (
    <article className="difficulty-panel">
      <h2>Job Difficulty</h2>
      <div className="donut-wrap"><div className="donut"><div><strong>32</strong><span>JOBS</span></div></div></div>
      <div className="legend">
        <span className="dot black" /><p>Hard<br />(65%)</p>
        <span className="dot green-dot" /><p>Mid<br />(25%)</p>
        <span className="dot red-dot" /><p>Junior<br />(10%)</p>
      </div>
    </article>
  );
}

function TodayInterviews() {
  return (
    <article className="schedule-panel">
      <div className="section-title"><div><h2>Today's Interviews</h2><p>3 scheduled, 1 review pending</p></div><CalendarDays size={20} /></div>
      <div className="interview-list">
        {scheduledInterviews.map((interview) => (
          <div className="interview-item" key={interview.name}>
            <span className="time">{interview.time}</span>
            <div><strong>{interview.name}</strong><p>{interview.role}</p></div>
            <span className="score">{interview.score}</span>
            <span className={`mini-status ${interview.status.toLowerCase()}`}>{interview.status}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function ActivityPanel() {
  return (
    <article className="activity-panel">
      <div className="section-title"><div><h2>Live Activity</h2><p>Latest system events</p></div><Settings size={20} /></div>
      <div className="activity-list">
        {activity.map((item, index) => (
          <div className="activity-item" key={item}><CheckCircle2 size={18} /><span>{item}</span><small>{index + 2}m ago</small></div>
        ))}
      </div>
    </article>
  );
}

function JobsTable() {
  return (
    <section className="jobs-panel">
      <div className="jobs-header"><h2>Recent AI Jobs</h2><button>View All Jobs</button></div>
      <div className="jobs-table">
        <div className="table-head"><span>JOB TITLE</span><span>STATUS</span><span>DIFFICULTY</span><span>CANDIDATES</span></div>
        {jobs.map((job) => (
          <div className="job-row" key={job.title}>
            <div className="job-title"><span className={`initials ${job.color}`}>{job.initials}</span><div><strong>{job.title}</strong><p>{job.created}</p></div></div>
            <span className={`pill ${job.status.toLowerCase()}`}>{job.status}</span>
            <span className={`pill ${job.difficulty.toLowerCase()}`}>{job.difficulty}</span>
            <span className="empty-candidates">{job.candidates}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function GoogleMark() {
  return (
    <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true">
      <path fill="#4285F4" d="M21.6 12.23c0-.78-.07-1.53-.2-2.23H12v4.22h5.38a4.6 4.6 0 0 1-2 3.02v2.51h3.24c1.9-1.75 2.98-4.33 2.98-7.52Z" />
      <path fill="#34A853" d="M12 22c2.7 0 4.96-.9 6.62-2.43l-3.24-2.51c-.9.6-2.05.96-3.38.96-2.6 0-4.8-1.76-5.59-4.12H3.06v2.59A10 10 0 0 0 12 22Z" />
      <path fill="#FBBC05" d="M6.41 13.9A6.02 6.02 0 0 1 6.1 12c0-.66.11-1.3.31-1.9V7.51H3.06A10 10 0 0 0 2 12c0 1.61.39 3.14 1.06 4.49l3.35-2.59Z" />
      <path fill="#EA4335" d="M12 5.98c1.47 0 2.8.51 3.84 1.5l2.87-2.87C16.96 2.98 14.7 2 12 2a10 10 0 0 0-8.94 5.51l3.35 2.59C7.2 7.74 9.4 5.98 12 5.98Z" />
    </svg>
  );
}

export default App;
