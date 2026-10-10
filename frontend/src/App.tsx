import { useEffect, useMemo, useRef, useState } from "react";
import {
  AlertCircle,
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileImage,
  FileText,
  Flame,
  ImagePlus,
  Inbox,
  LoaderCircle,
  Mail,
  MapPin,
  MessageCircle,
  Search,
  Send,
  Settings2,
  Sparkles,
  Trash2,
  Type,
  Upload,
  X,
} from "lucide-react";

type Notice = {
  id: string;
  title: string;
  deadline: string | null;
  venue: string | null;
  eligibility: string | null;
  actions: string[];
  created_at: string;
};

type Task = {
  id: string;
  notice_id: string;
  text: string;
  completed: boolean;
  created_at: string;
  notice: Notice;
};

type Summary = {
  notices: number;
  open_tasks: number;
  completed_tasks: number;
};

type DashboardData = {
  summary: Summary;
  notices: Notice[];
  upcoming_tasks: Task[];
};

type EmailSummary = {
  id: string;
  subject: string;
  sender: string;
  priority: "Urgent" | "High" | "Medium" | "Low";
  priority_reason: string;
  summary: string;
  deadlines: string[];
  actions: string[];
  created_at: string;
};

type View = "overview" | "analyze" | "emails" | "tasks" | "notices";
type NoticeDraft = Omit<Notice, "id" | "created_at">;
type NoticeAnalysis = {
  notice: NoticeDraft;
};
type AssistantMessage = {
  role: "user" | "assistant";
  content: string;
};

const EMPTY_SUMMARY: Summary = { notices: 0, open_tasks: 0, completed_tasks: 0 };
const NAV_ITEMS: { id: View; label: string; icon: typeof BookOpen }[] = [
  { id: "overview", label: "Overview", icon: BookOpen },
  { id: "analyze", label: "Scan a notice", icon: ImagePlus },
  { id: "emails", label: "Mail Summarizer", icon: Mail },
  { id: "tasks", label: "My tasks", icon: CheckCheck },
  { id: "notices", label: "Notice library", icon: FileText },
];

const SAMPLE_EMAILS = [
  {
    label: "🚨 Late Fee Penalty (Urgent)",
    text: "URGENT NOTICE FROM ACADEMIC OFFICE:\nAll students with pending semester dues must clear payments on the ERP portal before 11:59 PM tomorrow, October 11. Failure to comply will result in an immediate late fine of Rs. 2,500 and deregistration from mid-semester examinations. Please download the payment receipt after completing the transaction.",
  },
  {
    label: "📅 Mid-Term Hall Ticket (High)",
    text: "OFFICE OF ACADEMIC AFFAIRS:\nMid-term examination schedule has been finalized. Hall tickets are now available on the portal. All students must download and print their admit cards before Friday, October 16, and obtain physical verification signature from their respective faculty advisor. Entry into exam halls without signed hall tickets is strictly prohibited.",
  },
  {
    label: "💡 Robotics Hackathon (Medium)",
    text: "INVITATION FOR TECH FEST:\nThe Robotics and IoT Club is hosting the 2026 Annual Hackathon on October 24 at CC-302. Teams of up to 4 can register through the club portal before October 20. Exciting cash prizes, certificates, and mentorship from industry leaders will be provided.",
  },
  {
    label: "ℹ️ Library Maintenance (Low)",
    text: "CENTRAL LIBRARY CIRCULAR:\nThe 2nd floor reading hall will remain closed for air conditioning maintenance this Sunday from 9 AM to 1 PM. The digital catalog and ground floor lending counter will operate normally. Thank you for your cooperation.",
  },
];



async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, init);
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const payload = (await response.json()) as { detail?: string };
      if (payload.detail) message = payload.detail;
    } catch {
      // Keep the HTTP status message if the server didn't return JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

function getDateGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return "Good morning";
  if (hour < 17) return "Good afternoon";
  return "Good evening";
}

function formatDate(value?: string | null) {
  if (!value) return "Date not listed";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return new Intl.DateTimeFormat("en", {
    month: "short",
    day: "numeric",
    year: parsed.getFullYear() === new Date().getFullYear() ? undefined : "numeric",
  }).format(parsed);
}

function parseTaskDate(value?: string | null) {
  if (!value || !/\d/.test(value)) return null;
  const text = value.trim();
  const monthNames = "jan feb mar apr may jun jul aug sep oct nov dec".split(" ");
  const monthPattern = "Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?";
  const yearFirst = text.match(/\b(\d{4})-(\d{2})-(\d{2})\b/);
  const dayFirst = text.match(new RegExp(`\\b(\\d{1,2})\\s+(${monthPattern})\\s+(\\d{4})\\b`, "i"));
  const monthFirst = text.match(new RegExp(`\\b(${monthPattern})\\s+(\\d{1,2})(?:st|nd|rd|th)?[,]?\\s+(\\d{4})\\b`, "i"));
  let year: number;
  let month: number;
  let day: number;
  if (yearFirst) {
    year = Number(yearFirst[1]);
    month = Number(yearFirst[2]) - 1;
    day = Number(yearFirst[3]);
  } else if (dayFirst) {
    day = Number(dayFirst[1]);
    month = monthNames.indexOf(dayFirst[2].slice(0, 3).toLowerCase());
    year = Number(dayFirst[3]);
  } else if (monthFirst) {
    month = monthNames.indexOf(monthFirst[1].slice(0, 3).toLowerCase());
    day = Number(monthFirst[2]);
    year = Number(monthFirst[3]);
  } else {
    return null;
  }
  const parsed = new Date(year, month, day);
  if (parsed.getFullYear() !== year || parsed.getMonth() !== month || parsed.getDate() !== day) return null;
  return parsed;
}

function dateKey(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function startOfDay(value: Date) {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate());
}

function App() {
  const [view, setView] = useState<View>("overview");
  const [dashboard, setDashboard] = useState<DashboardData>({
    summary: EMPTY_SUMMARY,
    notices: [],
    upcoming_tasks: [],
  });
  const [chartTasks, setChartTasks] = useState<Task[]>([]);
  const [calendarTasks, setCalendarTasks] = useState<Task[]>([]);
  const [notices, setNotices] = useState<Notice[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [query, setQuery] = useState("");
  const [taskStatus, setTaskStatus] = useState<"open" | "done" | "all">("open");
  const [taskView, setTaskView] = useState<"list" | "calendar">("list");
  const [calendarMonth, setCalendarMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [selectedCalendarDate, setSelectedCalendarDate] = useState(() => dateKey(new Date()));
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [inputMode, setInputMode] = useState<"file" | "text">("file");
  const [noticeText, setNoticeText] = useState("");
  const [previewUrl, setPreviewUrl] = useState("");
  const [draft, setDraft] = useState<NoticeDraft | null>(null);
  const [noticeSearch, setNoticeSearch] = useState("");
  const [loadingDashboard, setLoadingDashboard] = useState(true);
  const [loadingTasks, setLoadingTasks] = useState(false);
  const [analyzing, setAnalyzing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [noticeError, setNoticeError] = useState("");
  const [pageError, setPageError] = useState("");
  const [toast, setToast] = useState("");
  const [dragging, setDragging] = useState(false);
  const [dialog, setDialog] = useState<"help" | "settings" | "workspace" | "assistant" | "clear-completed" | null>(null);
  const [assistantMessages, setAssistantMessages] = useState<AssistantMessage[]>([]);
  const [assistantInput, setAssistantInput] = useState("");
  const [assistantBusy, setAssistantBusy] = useState(false);
  const [assistantError, setAssistantError] = useState("");
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);
  const [reducedMotion, setReducedMotion] = useState(
    () => window.localStorage.getItem("campuslens-reduced-motion") === "true",
  );
  const [apiStatus, setApiStatus] = useState<"unknown" | "checking" | "connected" | "unavailable">("unknown");
  const uploadRef = useRef<HTMLInputElement>(null);
  const assistantEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (dialog === "assistant") assistantEndRef.current?.scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth" });
  }, [assistantMessages, assistantBusy, dialog, reducedMotion]);

  // Mail Summarizer State
  const [emailText, setEmailText] = useState("");
  const [summarizingEmail, setSummarizingEmail] = useState(false);
  const [emailDraft, setEmailDraft] = useState<Omit<EmailSummary, "id" | "created_at"> | null>(null);
  const [emailsList, setEmailsList] = useState<EmailSummary[]>([]);
  const [emailPriorityFilter, setEmailPriorityFilter] = useState("all");
  const [savingEmail, setSavingEmail] = useState(false);
  const [emailError, setEmailError] = useState("");
  const [loadingEmails, setLoadingEmails] = useState(false);


  useEffect(() => {
    const url = selectedFile ? URL.createObjectURL(selectedFile) : "";
    setPreviewUrl(url);
    return () => {
      if (url) URL.revokeObjectURL(url);
    };
  }, [selectedFile]);

  useEffect(() => {
    void loadDashboard();
  }, []);

  useEffect(() => {
    if (view !== "tasks") return;
    const debounce = window.setTimeout(() => {
      if (taskView === "calendar") void loadCalendarTasks();
      else void loadTasks();
    }, 180);
    return () => window.clearTimeout(debounce);
  }, [view, query, taskStatus, taskView]);

  useEffect(() => {
    if (view === "emails") {
      void loadEmails(emailPriorityFilter);
    }
  }, [view, emailPriorityFilter]);

  useEffect(() => {
    if (!toast) return;
    const timeout = window.setTimeout(() => setToast(""), 3200);
    return () => window.clearTimeout(timeout);
  }, [toast]);

  useEffect(() => {
    window.localStorage.setItem("campuslens-reduced-motion", String(reducedMotion));
  }, [reducedMotion]);

  useEffect(() => {
    document.documentElement.classList.toggle("reduce-motion", reducedMotion);
    return () => document.documentElement.classList.remove("reduce-motion");
  }, [reducedMotion]);

  async function loadDashboard() {
    setLoadingDashboard(true);
    setPageError("");
    try {
      const [data, allNotices, allTasks] = await Promise.all([
        request<DashboardData>("/api/dashboard"),
        request<{ notices: Notice[] }>("/api/notices"),
        request<{ tasks: Task[] }>("/api/tasks?status=all"),
      ]);
      setDashboard(data);
      setNotices(allNotices.notices);
      setChartTasks(allTasks.tasks);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Could not load your dashboard.");
    } finally {
      setLoadingDashboard(false);
    }
  }

  async function loadTasks() {
    setLoadingTasks(true);
    try {
      const result = await request<{ tasks: Task[] }>(
        `/api/tasks?query=${encodeURIComponent(query)}&status=${taskStatus}`,
      );
      setTasks(result.tasks);
      setPageError("");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Could not load your tasks.");
    } finally {
      setLoadingTasks(false);
    }
  }

  async function loadCalendarTasks() {
    setLoadingTasks(true);
    try {
      const result = await request<{ tasks: Task[] }>("/api/tasks?status=open");
      setCalendarTasks(result.tasks);
      setPageError("");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Could not load calendar tasks.");
    } finally {
      setLoadingTasks(false);
    }
  }

  async function askAssistant(question = assistantInput) {
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion || assistantBusy) return;
    const history = assistantMessages.slice(-8);
    setAssistantMessages((current) => [...current, { role: "user", content: trimmedQuestion }]);
    if (!question.trim() || question === assistantInput) setAssistantInput("");
    setAssistantBusy(true);
    setAssistantError("");
    try {
      const result = await request<{ answer: string }>("/api/assistant", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: trimmedQuestion, history }),
      });
      setAssistantMessages((current) => [...current, { role: "assistant", content: result.answer }]);
    } catch (error) {
      setAssistantError(error instanceof Error ? error.message : "The assistant could not answer. Please try again.");
    } finally {
      setAssistantBusy(false);
    }
  }

  async function checkApiStatus() {
    setApiStatus("checking");
    try {
      await request<{ status: string }>("/api/health");
      setApiStatus("connected");
    } catch {
      setApiStatus("unavailable");
    }
  }

  function navigateToTasks(status: "open" | "done" | "all" = "open", search = "") {
    setTaskStatus(status);
    setQuery(search);
    setPageError("");
    setView("tasks");
    setSelectedNotice(null);
  }

  function acceptImage(file?: File) {
    if (!file) return;
    const isPdf = file.type === "application/pdf" || file.name.toLowerCase().endsWith(".pdf");
    if (!isPdf && !["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type)) {
      setNoticeError("Choose a PNG, JPEG, WebP, GIF, or PDF notice.");
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      setNoticeError("This file is larger than 12 MB. Choose a smaller file.");
      return;
    }
    setSelectedFile(file);
    setDraft(null);
    setNoticeError("");
  }

  function removeImage() {
    setSelectedFile(null);
    setDraft(null);
    setNoticeError("");
    if (uploadRef.current) uploadRef.current.value = "";
  }

  async function analyzeImage() {
    if (!selectedFile) {
      setNoticeError("Choose a notice image to get started.");
      return;
    }
    const form = new FormData();
    form.append("image", selectedFile);
    setAnalyzing(true);
    setNoticeError("");
    try {
      const result = await request<NoticeAnalysis>("/api/notices/analyze", {
        method: "POST",
        body: form,
      });
      setDraft(result.notice);
      setToast("Notice details are ready to review.");
    } catch (error) {
      setNoticeError(error instanceof Error ? error.message : "Could not analyze this image.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function analyzeText() {
    if (!noticeText.trim()) {
      setNoticeError("Paste or type the notice text before asking Gemma to extract it.");
      return;
    }
    setAnalyzing(true);
    setNoticeError("");
    try {
      const result = await request<NoticeAnalysis>("/api/notices/analyze-text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: noticeText.trim() }),
      });
      setDraft(result.notice);
      setToast("Notice details are ready to review.");
    } catch (error) {
      setNoticeError(error instanceof Error ? error.message : "Could not analyze this text.");
    } finally {
      setAnalyzing(false);
    }
  }

  async function saveNotice() {
    if (!draft?.title.trim()) {
      setNoticeError("Add a title before saving this notice.");
      return;
    }
    setSaving(true);
    setNoticeError("");
    try {
      await request<{ notice: Notice }>("/api/notices", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      await loadDashboard();
      setDraft(null);
      setSelectedFile(null);
      setNoticeText("");
      setView("overview");
      setToast("Saved. Its action items are now in your task list.");
    } catch (error) {
      setNoticeError(error instanceof Error ? error.message : "Could not save this notice.");
    } finally {
      setSaving(false);
    }
  }

  async function completeTask(taskId: string) {
    try {
      await request<{ task: Task }>(`/api/tasks/${encodeURIComponent(taskId)}/complete`, {
        method: "PATCH",
      });
      await Promise.all([
        loadDashboard(),
        taskView === "calendar" ? loadCalendarTasks() : loadTasks(),
      ]);
      setToast("Task marked complete.");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Could not update this task.");
    }
  }

  async function clearCompletedTasks() {
    try {
      const result = await request<{ deleted: number }>("/api/tasks/completed", { method: "DELETE" });
      setDialog(null);
      await Promise.all([loadDashboard(), loadTasks(), loadCalendarTasks()]);
      setToast(result.deleted ? `Removed ${result.deleted} completed ${result.deleted === 1 ? "task" : "tasks"}.` : "There are no completed tasks to remove.");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Could not remove completed tasks.");
      setDialog(null);
    }
  }

  async function loadEmails(priority = emailPriorityFilter) {
    setLoadingEmails(true);
    try {
      const data = await request<{ emails: EmailSummary[] }>(`/api/emails?priority=${priority}`);
      setEmailsList(data.emails || []);
    } catch {
      // Ignore
    } finally {
      setLoadingEmails(false);
    }
  }

  async function handleSummarizeEmail() {
    if (!emailText.trim()) return;
    setSummarizingEmail(true);
    setEmailError("");
    setEmailDraft(null);
    try {
      const res = await request<{ email: Omit<EmailSummary, "id" | "created_at"> }>("/api/emails/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email_text: emailText.trim() }),
      });
      setEmailDraft(res.email);
      setToast("Email summarized & prioritized with Gemma 4!");
    } catch (err) {
      setEmailError(err instanceof Error ? err.message : "Could not summarize email.");
    } finally {
      setSummarizingEmail(false);
    }
  }

  async function handleSaveEmail() {
    if (!emailDraft) return;
    setSavingEmail(true);
    try {
      await request<{ email: EmailSummary }>("/api/emails", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(emailDraft),
      });

      // Also convert actions into a campus notice so tasks appear in My Tasks
      if (emailDraft.actions && emailDraft.actions.length > 0) {
        await request<{ notice: Notice }>("/api/notices", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            title: `[Email] ${emailDraft.subject}`,
            deadline: emailDraft.deadlines[0] || null,
            venue: "Online / Email",
            eligibility: "All students",
            actions: emailDraft.actions,
          }),
        });
      }

      setToast("Saved to Email Library & Tasks added!");
      setEmailDraft(null);
      setEmailText("");
      await Promise.all([loadEmails(), loadDashboard()]);
    } catch (err) {
      setEmailError(err instanceof Error ? err.message : "Could not save email.");
    } finally {
      setSavingEmail(false);
    }
  }

  function updateDraft<K extends keyof NoticeDraft>(key: K, value: NoticeDraft[K]) {
    setDraft((current) => (current ? { ...current, [key]: value } : current));
  }

  const filteredNotices = useMemo(() => {
    const search = noticeSearch.trim().toLocaleLowerCase();
    if (!search) return notices;
    return notices.filter((notice) =>
      [notice.title, notice.deadline, notice.venue, notice.eligibility]
        .filter(Boolean)
        .some((value) => value!.toLocaleLowerCase().includes(search)),
    );
  }, [notices, noticeSearch]);

  const completionRate = chartTasks.length
    ? Math.round((chartTasks.filter((task) => task.completed).length / chartTasks.length) * 100)
    : 0;
  const weekWorkload = useMemo(() => Array.from({ length: 7 }, (_, index) => {
    const day = startOfDay(new Date());
    day.setDate(day.getDate() + index);
    const count = chartTasks.filter((task) => {
      const deadline = parseTaskDate(task.notice?.deadline);
      return !task.completed && deadline && dateKey(deadline) === dateKey(day);
    }).length;
    return {
      date: day,
      count,
      label: new Intl.DateTimeFormat("en", { weekday: "short" }).format(day),
    };
  }), [chartTasks]);
  const maxWeekWorkload = Math.max(1, ...weekWorkload.map((day) => day.count));

  const calendarCells = useMemo(() => {
    const first = new Date(calendarMonth.getFullYear(), calendarMonth.getMonth(), 1);
    const start = new Date(first);
    start.setDate(first.getDate() - ((first.getDay() + 6) % 7));
    return Array.from({ length: 42 }, (_, index) => {
      const day = new Date(start);
      day.setDate(start.getDate() + index);
      return day;
    });
  }, [calendarMonth]);
  const filteredCalendarTasks = useMemo(() => {
    const search = query.trim().toLocaleLowerCase();
    if (!search) return calendarTasks;
    return calendarTasks.filter((task) =>
      [task.text, task.notice?.title, task.notice?.venue]
        .filter(Boolean)
        .some((value) => value!.toLocaleLowerCase().includes(search)),
    );
  }, [calendarTasks, query]);
  const calendarTasksByDate = useMemo(() => {
    const grouped = new Map<string, Task[]>();
    for (const task of filteredCalendarTasks) {
      const deadline = parseTaskDate(task.notice?.deadline);
      if (!deadline) continue;
      const key = dateKey(deadline);
      grouped.set(key, [...(grouped.get(key) ?? []), task]);
    }
    return grouped;
  }, [filteredCalendarTasks]);
  const selectedDayTasks = calendarTasksByDate.get(selectedCalendarDate) ?? [];
  const undatedCalendarTasks = filteredCalendarTasks.filter((task) => !parseTaskDate(task.notice?.deadline));

  const viewTitle = {
    overview: "Overview",
    analyze: "Scan a notice",
    emails: "Mail Summarizer",
    tasks: "My tasks",
    notices: "Notice library",
  }[view];


  return (
    <div className="app-layout">
      <aside className="sidebar">
        <button className="brand" onClick={() => setView("overview")} aria-label="CampusLens home">
          <span className="brand-icon"><BookOpen size={19} strokeWidth={2.2} /></span>
          <span className="brand-word">campuslens<span>.</span></span>
        </button>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              className={`nav-item ${view === id ? "active" : ""}`}
              onClick={() => {
                setView(id);
                setPageError("");
              }}
            >
              <Icon size={17} strokeWidth={1.9} />
              <span>{label}</span>
              {id === "tasks" && dashboard.summary.open_tasks > 0 && (
                <span className="nav-count">{dashboard.summary.open_tasks}</span>
              )}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button
            className="sidebar-note"
            onClick={() => { setAssistantError(""); setDialog("assistant"); }}
            aria-label="Open CampusLens AI assistant"
            title="Ask the CampusLens assistant"
          >
            <span className="sidebar-note-icon"><Sparkles size={15} /></span>
            <span className="sidebar-note-copy"><strong>Campus assistant</strong><span>Ask about tasks, deadlines, or anything else.</span><span className="sidebar-assistant-cta">Ask Gemma <ArrowRight size={12} /></span></span>
          </button>
          <div className="sidebar-footer">
            <span className="avatar">CL</span>
            <span className="user-label">Campus workspace</span>
            <button className="sidebar-settings" onClick={() => setDialog("settings")} aria-label="Workspace settings" title="Workspace settings">
              <Settings2 size={16} />
            </button>
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs"><span>Workspace</span><span className="crumb-slash">/</span><strong>{viewTitle}</strong></div>
          <div className="topbar-actions">
            <span className="today-label"><CalendarDays size={15} /> {formatDate(new Date().toISOString())}</span>
            <button className="icon-button" aria-label="Help and app guide" title="Help" onClick={() => { setDialog("help"); void checkApiStatus(); }}><CircleHelp size={17} /></button>
            <button className="profile-dot" aria-label="Workspace information" title="Workspace information" onClick={() => setDialog("workspace")}>CL</button>
          </div>
        </header>

        {pageError && (
          <div className="inline-alert" role="alert">
            <span>{pageError}</span>
            <button className="alert-refresh" onClick={() => view === "tasks" ? void loadTasks() : void loadDashboard()}>Refresh</button>
            <button onClick={() => setPageError("")} aria-label="Dismiss"><X size={15} /></button>
          </div>
        )}

        {view === "overview" && (
          <section className="page-section page-enter">
            <div className="page-intro overview-intro">
              <div>
                <p className="eyebrow">{getDateGreeting()}, welcome back</p>
                <h1>Your campus, <em>made clear.</em></h1>
                <p className="intro-copy">A calmer way to keep up with what matters around campus.</p>
              </div>
              <button className="button button-primary scan-cta" onClick={() => setView("analyze")}>
                <ImagePlus size={17} /> Scan a notice <ArrowRight size={16} />
              </button>
            </div>

            <div className="stats-row">
              <StatCard
                icon={<FileText size={17} />}
                label="Notices saved"
                value={dashboard.summary.notices}
                caption="In your library"
                tone="sage"
                onClick={() => setView("notices")}
              />
              <StatCard
                icon={<Clock3 size={17} />}
                label="To do"
                value={dashboard.summary.open_tasks}
                caption="Actions to take"
                tone="butter"
                onClick={() => navigateToTasks("open")}
              />
              <StatCard
                icon={<Check size={17} />}
                label="Done"
                value={dashboard.summary.completed_tasks}
                caption="You’ve got this"
                tone="blue"
                onClick={() => navigateToTasks("done")}
              />
            </div>

            <section className="insights-grid" aria-label="Task insights">
              <article className="surface-card insight-card">
                <div className="card-heading">
                  <div><h3>Task completion</h3><p>Progress across all saved actions</p></div>
                  <span className="heading-icon green-icon"><CheckCheck size={16} /></span>
                </div>
                <div className="completion-chart">
                  <div
                    className="completion-ring"
                    role="img"
                    aria-label={`${completionRate}% of ${chartTasks.length} tasks completed`}
                    style={{ "--completion": `${completionRate}%` } as React.CSSProperties}
                  >
                    <div><strong>{completionRate}%</strong><span>complete</span></div>
                  </div>
                  <div className="chart-legend">
                    <span><i className="legend-dot done-dot" /> Completed <strong>{dashboard.summary.completed_tasks}</strong></span>
                    <span><i className="legend-dot open-dot" /> To do <strong>{dashboard.summary.open_tasks}</strong></span>
                  </div>
                </div>
              </article>
              <article className="surface-card insight-card workload-card">
                <div className="card-heading">
                  <div><h3>Next 7 days</h3><p>Open tasks with a readable due date</p></div>
                  <span className="heading-icon butter-icon"><CalendarDays size={16} /></span>
                </div>
                <div className="workload-chart" role="img" aria-label="Open tasks due on each of the next seven days">
                  {weekWorkload.map((day) => (
                    <div className="workload-day" key={dateKey(day.date)} title={`${day.count} ${day.count === 1 ? "task" : "tasks"} due ${formatDate(dateKey(day.date))}`}>
                      <span className="workload-count">{day.count || ""}</span>
                      <div className="workload-track"><i style={{ height: `${day.count ? Math.max(14, (day.count / maxWeekWorkload) * 100) : 3}%` }} /></div>
                      <span className="workload-label">{day.label}</span>
                    </div>
                  ))}
                </div>
              </article>
            </section>

            <div className="section-heading">
              <div>
                <h2>At a glance</h2>
                <p>The latest notices and what to do next.</p>
              </div>
              <button className="text-link" onClick={() => setView("notices")}>
                View all notices <ArrowRight size={15} />
              </button>
            </div>

            <div className="overview-grid">
              <section className="surface-card notice-preview">
                <div className="card-heading">
                  <div>
                    <h3>Recent notices</h3>
                    <p>Your campus bulletin, in one place</p>
                  </div>
                  <span className="heading-icon green-icon"><FileText size={16} /></span>
                </div>
                {loadingDashboard ? (
                  <LoadingRows />
                ) : dashboard.notices.length ? (
                  <div className="compact-notice-list">
                    {dashboard.notices.slice(0, 4).map((notice) => (
                      <NoticeRow key={notice.id} notice={notice} onClick={() => setSelectedNotice(notice)} />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<FileImage size={19} />}
                    title="Your notice board is ready"
                    text="Scan your first campus notice to see the important details here."
                    action={<button className="small-link" onClick={() => setView("analyze")}>Scan a notice <ArrowRight size={14} /></button>}
                  />
                )}
              </section>

              <section className="surface-card task-preview">
                <div className="card-heading">
                  <div>
                    <h3>Coming up</h3>
                    <p>Your next few action items</p>
                  </div>
                  <span className="heading-icon butter-icon"><Clock3 size={16} /></span>
                </div>
                {loadingDashboard ? (
                  <LoadingRows />
                ) : dashboard.upcoming_tasks.length ? (
                  <div className="compact-task-list">
                    {dashboard.upcoming_tasks.slice(0, 5).map((task) => (
                      <TaskRow key={task.id} task={task} onComplete={completeTask} compact />
                    ))}
                  </div>
                ) : (
                  <EmptyState
                    icon={<CheckCheck size={19} />}
                    title="Nothing urgent on your list"
                    text="Action items from saved notices will land here."
                    action={<button className="small-link" onClick={() => setView("tasks")}>Open task list <ArrowRight size={14} /></button>}
                  />
                )}
              </section>
            </div>

            <div className="bottom-prompt">
              <span className="prompt-mark"><Sparkles size={16} /></span>
              <div><strong>Have a notice in front of you?</strong><span>Turn it into a clear plan in a few seconds.</span></div>
              <button className="button button-outline" onClick={() => setView("analyze")}>Get started <ArrowRight size={15} /></button>
            </div>
          </section>
        )}

        {view === "analyze" && (
          <section className="page-section page-enter">
            <div className="page-intro compact-intro">
              <div>
                <p className="eyebrow">NOTICE SCANNER</p>
                <h1>Turn a notice into <em>a next step.</em></h1>
                <p className="intro-copy">Upload a photo or PDF, or paste the notice text. You stay in control.</p>
              </div>
              <span className="model-pill"><span className="status-dot" /> Gemma 4 · notice analysis</span>
            </div>

            <div className={`scanner-grid ${inputMode === "text" ? "text-scanner-grid" : ""}`}>
              <section className="surface-card upload-card">
                <div className="card-heading">
                  <div className="step-title"><span className="step-number">01</span><div><h3>Your notice</h3><p>Choose a source to analyze</p></div></div>
                  {inputMode === "file" && selectedFile && (
                    <button className="icon-button" onClick={removeImage} aria-label="Remove file"><X size={16} /></button>
                  )}
                </div>
                <div className="source-tabs" role="tablist" aria-label="Notice source">
                  <button role="tab" aria-selected={inputMode === "file"} className={inputMode === "file" ? "active" : ""} onClick={() => { setInputMode("file"); setNoticeError(""); }}>
                    <FileImage size={14} /> Image or PDF
                  </button>
                  <button role="tab" aria-selected={inputMode === "text"} className={inputMode === "text" ? "active" : ""} onClick={() => { setInputMode("text"); setNoticeError(""); }}>
                    <Type size={14} /> Paste text
                  </button>
                </div>
                {inputMode === "file" ? (
                  <>
                <input
                  ref={uploadRef}
                  className="visually-hidden"
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif,application/pdf,.pdf"
                  onChange={(event) => {
                    acceptImage(event.target.files?.[0]);
                    event.target.value = "";
                  }}
                />
                {previewUrl ? (
                  <div className="image-preview">
                    {selectedFile?.type === "application/pdf" || selectedFile?.name.toLowerCase().endsWith(".pdf")
                      ? <iframe className="pdf-preview" src={previewUrl} title={`Preview of ${selectedFile.name}`} />
                      : <img src={previewUrl} alt="Preview of uploaded campus notice" />}
                    <div className="image-filename"><FileImage size={14} />{selectedFile?.name}</div>
                  </div>
                ) : (
                  <button
                    className={`dropzone ${dragging ? "dragging" : ""}`}
                    onClick={() => uploadRef.current?.click()}
                    type="button"
                    onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(event) => { event.preventDefault(); setDragging(false); acceptImage(event.dataTransfer.files[0]); }}
                  >
                    <span className="upload-icon"><Upload size={19} /></span>
                    <strong>Drop your image or PDF here</strong>
                    <span>or <b>browse files</b> from your device</span>
                    <small>PNG, JPG, WEBP, PDF · up to 12 MB</small>
                  </button>
                )}
                {selectedFile && (
                  <button className="small-link change-file-button" onClick={() => uploadRef.current?.click()}>
                    <Upload size={13} /> Replace file
                  </button>
                )}
                <div className="scanner-tip"><Sparkles size={15} /><span>Use a clear, uncropped notice. Files are analyzed for this request and not retained.</span></div>
                <button className="button button-primary full-button" onClick={analyzeImage} disabled={analyzing || !selectedFile}>
                  {analyzing ? <><LoaderCircle className="spin" size={17} /> Reading notice…</> : <><Sparkles size={16} /> Extract from file</>}
                </button>
                  </>
                ) : (
                  <div className="text-input-panel">
                    <label htmlFor="notice-text" className="field-label">Notice text</label>
                    <textarea
                      id="notice-text"
                      className="notice-text-input"
                      rows={11}
                      maxLength={20000}
                      value={noticeText}
                      onChange={(event) => setNoticeText(event.target.value)}
                      placeholder={"Paste the notice or announcement here…\n\nInclude dates, locations, eligibility, and instructions when available."}
                    />
                    <div className="text-input-footer">
                      <span>{noticeText.length.toLocaleString()} / 20,000 characters</span>
                      {noticeText && <button className="small-link" onClick={() => setNoticeText("")}>Clear text <X size={13} /></button>}
                    </div>
                    <div className="scanner-tip"><Sparkles size={15} /><span>Gemma will extract the same details as it does from an image. Review before saving.</span></div>
                    <button className="button button-primary full-button" onClick={analyzeText} disabled={analyzing || !noticeText.trim()}>
                      {analyzing ? <><LoaderCircle className="spin" size={17} /> Reading notice…</> : <><Sparkles size={16} /> Extract from text</>}
                    </button>
                  </div>
                )}
              </section>

              <section className="surface-card extraction-card">
                <div className="card-heading">
                  <div className="step-title"><span className="step-number">02</span><div><h3>What matters</h3><p>Review and edit before saving</p></div></div>
                  {draft && <span className="review-pill"><Check size={13} /> Ready to review</span>}
                </div>
                {draft ? (
                  <div className="extracted-fields">
                    <label className="field full-field"><span>Notice title <b>*</b></span><input value={draft.title} onChange={(event) => updateDraft("title", event.target.value)} placeholder="Title" /></label>
                    <div className="field-row">
                      <label className="field"><span>Deadline</span><input value={draft.deadline ?? ""} onChange={(event) => updateDraft("deadline", event.target.value || null)} placeholder="Not specified" /></label>
                      <label className="field"><span>Venue</span><input value={draft.venue ?? ""} onChange={(event) => updateDraft("venue", event.target.value || null)} placeholder="Not specified" /></label>
                    </div>
                    <label className="field full-field"><span>Eligibility</span><input value={draft.eligibility ?? ""} onChange={(event) => updateDraft("eligibility", event.target.value || null)} placeholder="Not specified" /></label>
                    <label className="field full-field">
                      <span>Action items <small>One action per line</small></span>
                      <textarea
                        rows={4}
                        value={draft.actions.join("\n")}
                        onChange={(event) => updateDraft("actions", event.target.value.split("\n").map((action) => action.trim()).filter(Boolean))}
                        placeholder="No actions found"
                      />
                    </label>
                    <button className="button button-primary full-button" onClick={saveNotice} disabled={saving}>
                      {saving ? <><LoaderCircle className="spin" size={17} /> Saving notice…</> : <>Save notice & create tasks <ArrowRight size={16} /></>}
                    </button>
                  </div>
                ) : (
                  <div className="extraction-empty">
                    <span className="document-illustration"><FileText size={25} /></span>
                    <strong>Your details will appear here</strong>
                    <p>We’ll identify the title, date, place, eligibility, and what needs doing.</p>
                    <div className="extraction-keys"><span>Title</span><i /><span>Deadline</span><i /><span>Actions</span></div>
                  </div>
                )}
              </section>
            </div>
            {noticeError && <div className="inline-alert scanner-alert" role="alert"><span>{noticeError}</span><button onClick={() => setNoticeError("")} aria-label="Dismiss"><X size={15} /></button></div>}
            <p className="privacy-note"><Settings2 size={14} /> Uploaded files and pasted text are sent to Gemini only when you request analysis; neither is saved with the notice.</p>
          </section>
        )}

        {view === "tasks" && (
          <section className="page-section page-enter">
            <div className="page-intro compact-intro">
              <div><p className="eyebrow">YOUR ACTION CENTER</p><h1>One thing at <em>a time.</em></h1><p className="intro-copy">Small next steps make busy campus weeks easier.</p></div>
              <div className="task-summary-chip"><CheckCheck size={16} /> {dashboard.summary.open_tasks} open</div>
            </div>
            <section className="surface-card task-manager-card">
              <div className="task-manager-toolbar">
                <label className="search-box"><Search size={17} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search tasks, notices, or venues" /></label>
                <div className="task-toolbar-actions">
                  <div className="view-switch" role="group" aria-label="Task display">
                    <button className={taskView === "list" ? "active" : ""} onClick={() => setTaskView("list")}><CheckCheck size={14} /> List</button>
                    <button className={taskView === "calendar" ? "active" : ""} onClick={() => setTaskView("calendar")}><CalendarDays size={14} /> Calendar</button>
                  </div>
                  {taskView === "list" && (
                    <label className="select-wrap"><span className="visually-hidden">Filter tasks</span><select value={taskStatus} onChange={(event) => setTaskStatus(event.target.value as typeof taskStatus)}><option value="open">To do</option><option value="done">Completed</option><option value="all">All tasks</option></select><ChevronDown size={15} /></label>
                  )}
                  {dashboard.summary.completed_tasks > 0 && (
                    <button className="clear-completed-button" onClick={() => setDialog("clear-completed")}>
                      <Trash2 size={14} /> Clear completed
                    </button>
                  )}
                </div>
              </div>
              {taskView === "calendar" ? (
                loadingTasks ? <LoadingRows /> : (
                  <div className="calendar-layout">
                    <div className="calendar-panel">
                      <div className="calendar-toolbar">
                        <button className="icon-button" aria-label="Previous month" onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() - 1, 1))}><ChevronLeft size={17} /></button>
                        <h2>{new Intl.DateTimeFormat("en", { month: "long", year: "numeric" }).format(calendarMonth)}</h2>
                        <button className="icon-button" aria-label="Next month" onClick={() => setCalendarMonth(new Date(calendarMonth.getFullYear(), calendarMonth.getMonth() + 1, 1))}><ChevronRight size={17} /></button>
                        <button className="calendar-today" onClick={() => {
                          const today = new Date();
                          setCalendarMonth(new Date(today.getFullYear(), today.getMonth(), 1));
                          setSelectedCalendarDate(dateKey(today));
                        }}>Today</button>
                      </div>
                      <div className="calendar-grid" role="grid" aria-label="Tasks by deadline">
                        {["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].map((day) => <span className="calendar-weekday" role="columnheader" key={day}>{day}</span>)}
                        {calendarCells.map((day) => {
                          const key = dateKey(day);
                          const count = calendarTasksByDate.get(key)?.length ?? 0;
                          const today = key === dateKey(new Date());
                          return (
                            <button
                              className={`calendar-day ${day.getMonth() !== calendarMonth.getMonth() ? "outside-month" : ""} ${key === selectedCalendarDate ? "selected" : ""} ${today ? "today" : ""} ${count ? "has-tasks" : ""}`}
                              key={key}
                              role="gridcell"
                              aria-label={`${formatDate(key)}${count ? `, ${count} open ${count === 1 ? "task" : "tasks"}` : ""}`}
                              aria-pressed={key === selectedCalendarDate}
                              onClick={() => {
                                setSelectedCalendarDate(key);
                                if (day.getMonth() !== calendarMonth.getMonth()) setCalendarMonth(new Date(day.getFullYear(), day.getMonth(), 1));
                              }}
                            >
                              <span>{day.getDate()}</span>
                              {count > 0 && <i>{count}</i>}
                            </button>
                          );
                        })}
                      </div>
                      <div className="calendar-legend"><span><i className="legend-dot open-dot" /> Open tasks by notice deadline</span><span>Dates that could not be read stay in “No deadline”.</span></div>
                    </div>
                    <div className="calendar-day-panel">
                      <div className="calendar-day-heading">
                        <div><p className="eyebrow">SELECTED DAY</p><h3>{formatDate(selectedCalendarDate)}</h3></div>
                        <span>{selectedDayTasks.length} due</span>
                      </div>
                      {selectedDayTasks.length
                        ? <div className="managed-task-list">{[...selectedDayTasks].sort((a, b) => a.text.localeCompare(b.text)).map((task) => <TaskRow key={task.id} task={task} onComplete={completeTask} />)}</div>
                        : <p className="calendar-empty">No tasks due this day. Pick another date or use the list view.</p>}
                      {undatedCalendarTasks.length > 0 && (
                        <div className="undated-tasks">
                          <div className="undated-heading"><h4>No deadline</h4><span>{undatedCalendarTasks.length}</span></div>
                          <div className="managed-task-list">{undatedCalendarTasks.slice(0, 5).map((task) => <TaskRow key={task.id} task={task} onComplete={completeTask} />)}</div>
                          {undatedCalendarTasks.length > 5 && <p className="undated-more">{undatedCalendarTasks.length - 5} more undated tasks. Use the list view to see all.</p>}
                        </div>
                      )}
                    </div>
                  </div>
                )
              ) : loadingTasks ? (
                <LoadingRows />
              ) : tasks.length ? (
                <div className="managed-task-list">{[...tasks].sort((a, b) => {
                  const left = parseTaskDate(a.notice?.deadline)?.getTime() ?? Number.MAX_SAFE_INTEGER;
                  const right = parseTaskDate(b.notice?.deadline)?.getTime() ?? Number.MAX_SAFE_INTEGER;
                  return left - right;
                }).map((task) => <TaskRow key={task.id} task={task} onComplete={completeTask} />)}</div>
              ) : (
                <EmptyState
                  icon={<CheckCheck size={20} />}
                  title={query ? "No matching tasks" : taskStatus === "done" ? "No completed tasks yet" : taskStatus === "all" ? "Your task list is clear" : "A little breathing room"}
                  text={query ? "Try another search or clear it to see your tasks." : taskStatus === "done" ? "Completed tasks will be collected here." : taskStatus === "all" ? "Tasks from saved notices will appear here." : "Tasks from saved notices will appear here when there’s something to do."}
                  action={query
                    ? <button className="small-link" onClick={() => setQuery("")}>Clear search <X size={14} /></button>
                    : taskStatus === "open"
                      ? <button className="small-link" onClick={() => setView("analyze")}>Scan a notice <ArrowRight size={14} /></button>
                      : undefined}
                />
              )}
              <div className="list-footer">{taskView === "calendar" ? `${filteredCalendarTasks.length} open ${filteredCalendarTasks.length === 1 ? "task" : "tasks"} · ${calendarTasksByDate.size} days with deadlines` : `${tasks.length} ${tasks.length === 1 ? "task" : "tasks"} shown`}</div>
            </section>
          </section>
        )}

        {view === "notices" && (
          <section className="page-section page-enter">
            <div className="page-intro compact-intro">
              <div><p className="eyebrow">YOUR CAMPUS BULLETIN</p><h1>Notices worth <em>keeping.</em></h1><p className="intro-copy">The useful bits, saved in one searchable place.</p></div>
              <button className="button button-primary" onClick={() => setView("analyze")}><ImagePlus size={16} /> Scan a notice</button>
            </div>
            <section className="surface-card notice-library-card">
              <div className="library-toolbar">
                <label className="search-box"><Search size={17} /><input value={noticeSearch} onChange={(event) => setNoticeSearch(event.target.value)} placeholder="Search notices by title, date, or venue" /></label>
                <span className="result-count">{filteredNotices.length} saved</span>
              </div>
              {filteredNotices.length ? <div className="library-grid">{filteredNotices.map((notice) => <NoticeCard key={notice.id} notice={notice} onClick={() => setSelectedNotice(notice)} />)}</div> : <EmptyState icon={<FileText size={20} />} title={noticeSearch ? "No notices found" : "Your library starts here"} text={noticeSearch ? "Try a different title, date, or venue." : "Save a notice to keep its deadlines and action items close."} action={noticeSearch ? <button className="small-link" onClick={() => setNoticeSearch("")}>Clear search <X size={14} /></button> : <button className="small-link" onClick={() => setView("analyze")}>Scan your first notice <ArrowRight size={14} /></button>} />}
            </section>
          </section>
        )}

        {view === "emails" && (

          <section className="page-section page-enter">
            <div className="page-intro compact-intro">
              <div>
                <p className="eyebrow">MAIL & CIRCULAR SUMMARIZER</p>
                <h1>Cut through the noise. <em>Know what's urgent.</em></h1>
                <p className="intro-copy">Paste long college emails. Gemma 4 summarizes the key points and classifies urgency.</p>
              </div>
              <span className="model-pill"><span className="status-dot" /> Gemma 4 · Priority Ranking</span>
            </div>

            <div className="mail-grid">
              <section className="mail-input-card">
                <div className="card-heading">
                  <div className="step-title">
                    <span className="step-number">01</span>
                    <div>
                      <h3>Paste campus email or text</h3>
                      <p>Announcements, circulars, or circular emails</p>
                    </div>
                  </div>
                </div>

                <div className="sample-prompts">
                  <span style={{ fontSize: "11px", color: "var(--muted)", alignSelf: "center" }}>Try sample:</span>
                  {SAMPLE_EMAILS.map((s, idx) => (
                    <button
                      key={idx}
                      className="sample-chip"
                      onClick={() => {
                        setEmailText(s.text);
                        setEmailDraft(null);
                      }}
                    >
                      {s.label}
                    </button>
                  ))}
                </div>

                <textarea
                  className="mail-textarea"
                  placeholder="Paste email text here, e.g. 'Dear Students, Please be advised that registration for...'"
                  value={emailText}
                  onChange={(e) => setEmailText(e.target.value)}
                />

                {emailError && <p className="form-error" role="alert">{emailError}</p>}

                <button
                  style={{ marginTop: "14px" }}
                  className="button button-primary full-button"
                  onClick={handleSummarizeEmail}
                  disabled={summarizingEmail || !emailText.trim()}
                >
                  {summarizingEmail ? (
                    <><LoaderCircle className="spin" size={17} /> Summarizing with Gemma 4…</>
                  ) : (
                    <><Sparkles size={16} /> Summarize & Rank Urgency</>
                  )}
                </button>
              </section>

              <section className="mail-result-card">
                <div className="card-heading">
                  <div className="step-title">
                    <span className="step-number">02</span>
                    <div>
                      <h3>Extracted intelligence</h3>
                      <p>Priority, deadlines, and actions</p>
                    </div>
                  </div>
                  {emailDraft && (
                    <span className={`priority-pill priority-${emailDraft.priority.toLowerCase()}`}>
                      {emailDraft.priority === "Urgent" && <Flame size={12} />}
                      {emailDraft.priority === "High" && <Clock3 size={12} />}
                      {emailDraft.priority === "Medium" && <AlertCircle size={12} />}
                      {emailDraft.priority === "Low" && <Check size={12} />}
                      {emailDraft.priority}
                    </span>
                  )}
                </div>

                {emailDraft ? (
                  <div className="extraction-form">
                    <div className="mail-card-header">
                      <div>
                        <strong style={{ fontSize: "15px", display: "block" }}>{emailDraft.subject}</strong>
                        <span style={{ fontSize: "12px", color: "var(--muted)" }}>From: {emailDraft.sender}</span>
                      </div>
                    </div>

                    {emailDraft.priority_reason && (
                      <div className="priority-reason-box">
                        <strong>Why {emailDraft.priority}?</strong> {emailDraft.priority_reason}
                      </div>
                    )}

                    <div style={{ margin: "12px 0" }}>
                      <strong style={{ fontSize: "12px", color: "var(--soft-muted)", textTransform: "uppercase" }}>Summary</strong>
                      <p style={{ margin: "4px 0 0", fontSize: "13px", lineHeight: "1.5" }}>{emailDraft.summary}</p>
                    </div>

                    {emailDraft.deadlines && emailDraft.deadlines.length > 0 && (
                      <div>
                        <strong style={{ fontSize: "12px", color: "var(--soft-muted)", textTransform: "uppercase" }}>Key Dates / Deadlines</strong>
                        <div className="mail-deadlines-list">
                          {emailDraft.deadlines.map((d, i) => (
                            <span key={i} className="mail-deadline-badge">
                              <CalendarDays size={12} /> {d}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    <div>
                      <strong style={{ fontSize: "12px", color: "var(--soft-muted)", textTransform: "uppercase" }}>Action Items ({emailDraft.actions.length})</strong>
                      {emailDraft.actions.length ? (
                        <div style={{ marginTop: "6px" }}>
                          {emailDraft.actions.map((act, i) => (
                            <div key={i} className="mail-action-item">
                              <Check size={14} color="#38674e" /> <span>{act}</span>
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p style={{ fontSize: "12px", color: "var(--muted)" }}>No direct action items needed.</p>
                      )}
                    </div>

                    <button
                      style={{ marginTop: "16px" }}
                      className="button button-primary full-button"
                      onClick={handleSaveEmail}
                      disabled={savingEmail}
                    >
                      {savingEmail ? (
                        <><LoaderCircle className="spin" size={16} /> Saving…</>
                      ) : (
                        <><CheckCheck size={16} /> Save & Add Actions to My Tasks</>
                      )}
                    </button>
                  </div>
                ) : (
                  <div className="extraction-empty">
                    <span className="empty-sparkle"><Inbox size={26} /></span>
                    <strong>Ready to analyze</strong>
                    <p>Paste an email on the left and click "Summarize" to see priority ranking and action items.</p>
                  </div>
                )}
              </section>
            </div>

            <section className="surface-card">
              <div className="library-toolbar">
                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <Inbox size={18} color="#283b2d" />
                  <strong style={{ fontSize: "15px" }}>Prioritized Mail Feed</strong>
                </div>
                <div style={{ display: "flex", gap: "6px" }}>
                  {["all", "Urgent", "High", "Medium", "Low"].map((p) => (
                    <button
                      key={p}
                      className={`sample-chip ${emailPriorityFilter === p ? "active" : ""}`}
                      style={emailPriorityFilter === p ? { background: "#283b2d", color: "#fff", borderColor: "#283b2d" } : {}}
                      onClick={() => setEmailPriorityFilter(p)}
                    >
                      {p === "all" ? "All Priorities" : p}
                    </button>
                  ))}
                </div>
              </div>

              {loadingEmails ? (
                <LoadingRows />
              ) : emailsList.length ? (
                <div style={{ marginTop: "12px" }}>
                  {emailsList.map((em) => (
                    <article key={em.id} className="mail-feed-item">
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: "10px" }}>
                        <div>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                            <span className={`priority-pill priority-${em.priority.toLowerCase()}`}>
                              {em.priority}
                            </span>
                            <strong style={{ fontSize: "14px" }}>{em.subject}</strong>
                          </div>
                          <p style={{ margin: "6px 0 0", fontSize: "12px", color: "var(--muted)" }}>
                            From {em.sender} · {formatDate(em.created_at)}
                          </p>
                        </div>
                        {em.actions.length > 0 && (
                          <span className="notice-action-count">{em.actions.length} action(s)</span>
                        )}
                      </div>
                      <p style={{ margin: "8px 0 0", fontSize: "13px", lineHeight: "1.5" }}>{em.summary}</p>
                      {em.deadlines && em.deadlines.length > 0 && (
                        <div className="mail-deadlines-list">
                          {em.deadlines.map((d, idx) => (
                            <span key={idx} className="mail-deadline-badge"><CalendarDays size={12} /> {d}</span>
                          ))}
                        </div>
                      )}
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={<Mail size={22} />}
                  title="No emails categorized yet"
                  text="Paste and analyze an email above to rank and track campus announcements."
                />
              )}
            </section>
          </section>
        )}

        <footer className="app-footer"><span>CampusLens</span><span>Less searching. More doing.</span><span>Gemma 4 · {new Date().getFullYear()}</span></footer>

      </main>

      {toast && <div className="toast" role="status"><span className="toast-check"><Check size={14} /></span>{toast}<button onClick={() => setToast("")} aria-label="Dismiss"><X size={14} /></button></div>}
      {dialog === "help" && (
        <Dialog title="CampusLens quick guide" onClose={() => setDialog(null)}>
          <p className="dialog-copy">Turn a campus notice into a short, editable list of details and next steps.</p>
          <ol className="help-steps">
            <li><strong>Scan:</strong> Upload a clear PNG, JPG, WebP, or GIF (up to 12 MB).</li>
            <li><strong>Review:</strong> Check and edit the title, deadline, venue, eligibility, and actions.</li>
            <li><strong>Save:</strong> The notice goes to your library and each action becomes a task.</li>
          </ol>
          <div className={`connection-status ${apiStatus}`} role="status">
            <span className="status-dot" />
            {apiStatus === "checking" ? "Checking local API…" : apiStatus === "connected" ? "Local API is connected" : apiStatus === "unavailable" ? "Local API is unavailable" : "API status not checked"}
            <button className="small-link" onClick={() => void checkApiStatus()} disabled={apiStatus === "checking"}>
              {apiStatus === "checking" ? "Checking…" : "Check again"}
            </button>
          </div>
          <div className="dialog-actions">
            <button className="button button-outline" onClick={() => setDialog(null)}>Close</button>
            <button className="button button-primary" onClick={() => { setDialog(null); setView("analyze"); }}>Scan a notice <ArrowRight size={15} /></button>
          </div>
        </Dialog>
      )}
      {dialog === "settings" && (
        <Dialog title="Workspace settings" onClose={() => setDialog(null)}>
          <p className="dialog-copy">A few preferences for this browser and workspace.</p>
          <label className="preference-row">
            <span><strong>Reduce motion</strong><small>Limit animated transitions and loading effects.</small></span>
            <input type="checkbox" checked={reducedMotion} onChange={(event) => setReducedMotion(event.target.checked)} />
          </label>
          <div className="privacy-summary">
            <strong>Local workspace</strong>
            <p>Notices and tasks are stored by the local app. Notice files are sent to Gemini only when you analyze them. When you ask the assistant, your question and recent task/notice details are sent for an answer.</p>
          </div>
          <div className="dialog-actions"><button className="button button-primary" onClick={() => setDialog(null)}>Done</button></div>
        </Dialog>
      )}
      {dialog === "workspace" && (
        <Dialog title="Campus workspace" onClose={() => setDialog(null)}>
          <p className="dialog-copy">This is a local, single-user workspace. No account or campus profile is connected.</p>
          <div className="workspace-facts"><span>Application<strong>CampusLens</strong></span><span>Notice analysis<strong>Gemma 4 via Gemini API</strong></span><span>Data<strong>Stored locally on this device</strong></span></div>
          <div className="dialog-actions">
            <button className="button button-outline" onClick={() => { setDialog("settings"); }}>Settings</button>
            <button className="button button-primary" onClick={() => setDialog(null)}>Close</button>
          </div>
        </Dialog>
      )}
      {dialog === "assistant" && (
        <Dialog title="CampusLens assistant" className="assistant-dialog" onClose={() => setDialog(null)}>
          <div className="assistant-intro">
            <span className="assistant-intro-icon"><Sparkles size={16} /></span>
            <p>Ask about your saved tasks and notices, get help prioritizing, or ask a general question. Answers use Gemma 4.</p>
          </div>
          <div className="assistant-messages" aria-live="polite" aria-label="Assistant conversation">
            {!assistantMessages.length && (
              <div className="assistant-welcome">
                <span className="assistant-bot-icon"><MessageCircle size={17} /></span>
                <div><strong>What can I help with?</strong><p>I can summarize your open tasks, find upcoming deadlines, or help you plan your next steps.</p></div>
              </div>
            )}
            {assistantMessages.map((message, index) => (
              <article className={`assistant-message ${message.role}`} key={`${message.role}-${index}`}>
                <span className="assistant-message-icon">{message.role === "assistant" ? <Sparkles size={13} /> : "You"}</span>
                <p>{message.content}</p>
              </article>
            ))}
            {assistantBusy && <div className="assistant-thinking"><LoaderCircle className="spin" size={14} /> Thinking…</div>}
            <div ref={assistantEndRef} />
          </div>
          {!assistantMessages.length && (
            <div className="assistant-suggestions" aria-label="Suggested questions">
              {["Summarize my open tasks", "What deadlines are coming up?", "Help me prioritize this week"].map((suggestion) => (
                <button key={suggestion} onClick={() => void askAssistant(suggestion)} disabled={assistantBusy}>{suggestion}<ArrowRight size={12} /></button>
              ))}
            </div>
          )}
          {assistantError && <div className="assistant-error" role="alert">{assistantError}</div>}
          <form className="assistant-composer" onSubmit={(event) => { event.preventDefault(); void askAssistant(); }}>
            <textarea
              value={assistantInput}
              onChange={(event) => setAssistantInput(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  void askAssistant();
                }
              }}
              placeholder="Ask about your tasks or anything else…"
              aria-label="Ask the CampusLens assistant"
              maxLength={2000}
              rows={2}
              disabled={assistantBusy}
            />
            <button className="assistant-send" type="submit" disabled={assistantBusy || !assistantInput.trim()} aria-label="Send question">
              {assistantBusy ? <LoaderCircle className="spin" size={16} /> : <Send size={15} />}
            </button>
          </form>
          <p className="assistant-footnote">Workspace data is sent to Gemini only when you ask a question.</p>
        </Dialog>
      )}
      {dialog === "clear-completed" && (
        <Dialog title="Clear completed tasks?" onClose={() => setDialog(null)}>
          <p className="dialog-copy">
            This removes {dashboard.summary.completed_tasks} completed {dashboard.summary.completed_tasks === 1 ? "task" : "tasks"} from your task list. Saved notices are kept, and open tasks are not changed.
          </p>
          <div className="dialog-actions">
            <button className="button button-outline" onClick={() => setDialog(null)}>Keep tasks</button>
            <button className="button button-danger" onClick={() => void clearCompletedTasks()}><Trash2 size={14} /> Remove completed tasks</button>
          </div>
        </Dialog>
      )}
      {selectedNotice && (
        <Dialog title="Saved notice" onClose={() => setSelectedNotice(null)}>
          <NoticeDetails notice={selectedNotice} />
          <div className="dialog-actions">
            <button className="button button-outline" onClick={() => setSelectedNotice(null)}>Close</button>
            <button className="button button-primary" onClick={() => navigateToTasks("all", selectedNotice.title)}>View related tasks <ArrowRight size={15} /></button>
          </div>
        </Dialog>
      )}
    </div>
  );
}

function StatCard({ icon, label, value, caption, tone, onClick }: { icon: React.ReactNode; label: string; value: number; caption: string; tone: string; onClick: () => void }) {
  return <button className={`stat-card ${tone}`} onClick={onClick} aria-label={`${label}: ${value}. ${caption}. Open related items.`}><span className="stat-icon">{icon}</span><span className="stat-label">{label}</span><strong>{value}</strong><span className="stat-caption">{caption}</span><span className="stat-arrow"><ArrowUpRight size={15} /></span></button>;
}

function EmptyState({ icon, title, text, action }: { icon: React.ReactNode; title: string; text: string; action?: React.ReactNode }) {
  return <div className="empty-state"><span className="empty-state-icon">{icon}</span><strong>{title}</strong><p>{text}</p>{action}</div>;
}

function LoadingRows() {
  return <div className="loading-list" aria-label="Loading"><span /><span /><span /></div>;
}

function NoticeRow({ notice, onClick }: { notice: Notice; onClick: () => void }) {
  return <button className="notice-row" onClick={onClick} aria-label={`View notice: ${notice.title}`}>
    <span className="notice-row-icon"><FileText size={17} /></span>
    <div className="notice-row-copy"><strong>{notice.title}</strong><span>{notice.venue || "Campus notice"}{notice.deadline ? ` · Due ${formatDate(notice.deadline)}` : ""}</span></div>
    <span className="notice-action-count">{notice.actions.length} {notice.actions.length === 1 ? "action" : "actions"}</span>
    <ArrowRight className="row-arrow" size={15} />
  </button>;
}

function TaskRow({ task, onComplete, compact = false }: { task: Task; onComplete: (id: string) => void; compact?: boolean }) {
  const deadline = task.notice?.deadline;
  return <article className={`task-row ${task.completed ? "is-complete" : ""} ${compact ? "compact" : ""}`}>
    <button className="task-toggle" onClick={() => !task.completed && onComplete(task.id)} disabled={task.completed} aria-label={task.completed ? "Task completed" : `Complete ${task.text}`}>
      {task.completed ? <Check size={14} /> : null}
    </button>
    <div className="task-row-copy"><strong>{task.text}</strong><span>{task.notice?.title || "Campus notice"}</span></div>
    {deadline && <span className="task-deadline"><CalendarDays size={13} />{formatDate(deadline)}</span>}
    {compact && deadline && new Date(deadline) < new Date() && <span className="due-soon"><ArrowDownRight size={13} />Check date</span>}
    {!compact && <button className="task-done-button" onClick={() => onComplete(task.id)} disabled={task.completed}>{task.completed ? "Done" : "Mark done"}</button>}
  </article>;
}

function NoticeCard({ notice, onClick }: { notice: Notice; onClick: () => void }) {
  return <button className="library-notice" onClick={onClick} aria-label={`Open saved notice: ${notice.title}`}>
    <div className="library-notice-top"><span className="notice-type"><FileText size={13} /> NOTICE</span><span className="library-action-count">{notice.actions.length} actions</span></div>
    <h3>{notice.title}</h3>
    <div className="library-meta">
      {notice.deadline && <span><CalendarDays size={14} />{formatDate(notice.deadline)}</span>}
      {notice.venue && <span><MapPin size={14} />{notice.venue}</span>}
    </div>
    {notice.eligibility && <p className="eligibility-copy">For {notice.eligibility}</p>}
    {notice.actions.length > 0 && <div className="notice-action-list">{notice.actions.slice(0, 3).map((action, index) => <span key={`${notice.id}-${index}`}><Check size={13} />{action}</span>)}</div>}
    <span className="notice-card-cta">View notice <ArrowRight size={14} /></span>
  </button>;
}

function NoticeDetails({ notice }: { notice: Notice }) {
  return (
    <div className="notice-details">
      <h3>{notice.title}</h3>
      <dl>
        <div><dt>Deadline</dt><dd>{notice.deadline || "Not specified"}</dd></div>
        <div><dt>Venue</dt><dd>{notice.venue || "Not specified"}</dd></div>
        <div><dt>Eligibility</dt><dd>{notice.eligibility || "Not specified"}</dd></div>
        <div><dt>Saved</dt><dd>{formatDate(notice.created_at)}</dd></div>
      </dl>
      <strong className="details-actions-title">Action items</strong>
      {notice.actions.length
        ? <ul>{notice.actions.map((action, index) => <li key={`${notice.id}-detail-${index}`}><Check size={14} />{action}</li>)}</ul>
        : <p className="dialog-copy">No action items were identified in this notice.</p>}
    </div>
  );
}

function Dialog({ title, onClose, children, className = "" }: { title: string; onClose: () => void; children: React.ReactNode; className?: string }) {
  const dialogRef = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const element = dialogRef.current;
    if (element && !element.open) element.showModal();
    return () => {
      if (element?.open) element.close();
    };
  }, []);

  return (
    <dialog
      ref={dialogRef}
      className={`app-dialog ${className}`}
      aria-labelledby="dialog-title"
      onCancel={(event) => { event.preventDefault(); onClose(); }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <div className="dialog-heading">
        <h2 id="dialog-title">{title}</h2>
        <button className="icon-button" onClick={onClose} aria-label="Close dialog"><X size={17} /></button>
      </div>
      <div className="dialog-content">{children}</div>
    </dialog>
  );
}

export default App;
