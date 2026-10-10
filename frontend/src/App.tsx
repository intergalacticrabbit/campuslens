import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowDownRight,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CalendarDays,
  Check,
  CheckCheck,
  ChevronDown,
  CircleHelp,
  Clock3,
  FileImage,
  FileText,
  ImagePlus,
  LoaderCircle,
  MapPin,
  Search,
  Settings2,
  Sparkles,
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

type View = "overview" | "analyze" | "tasks" | "notices";
type NoticeDraft = Omit<Notice, "id" | "created_at">;
type NoticeAnalysis = {
  notice: NoticeDraft;
};

const EMPTY_SUMMARY: Summary = { notices: 0, open_tasks: 0, completed_tasks: 0 };
const NAV_ITEMS: { id: View; label: string; icon: typeof BookOpen }[] = [
  { id: "overview", label: "Overview", icon: BookOpen },
  { id: "analyze", label: "Scan a notice", icon: ImagePlus },
  { id: "tasks", label: "My tasks", icon: CheckCheck },
  { id: "notices", label: "Notice library", icon: FileText },
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

function App() {
  const [view, setView] = useState<View>("overview");
  const [dashboard, setDashboard] = useState<DashboardData>({
    summary: EMPTY_SUMMARY,
    notices: [],
    upcoming_tasks: [],
  });
  const [notices, setNotices] = useState<Notice[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [query, setQuery] = useState("");
  const [taskStatus, setTaskStatus] = useState<"open" | "done" | "all">("open");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
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
  const [dialog, setDialog] = useState<"help" | "settings" | "workspace" | null>(null);
  const [selectedNotice, setSelectedNotice] = useState<Notice | null>(null);
  const [reducedMotion, setReducedMotion] = useState(
    () => window.localStorage.getItem("campuslens-reduced-motion") === "true",
  );
  const [apiStatus, setApiStatus] = useState<"unknown" | "checking" | "connected" | "unavailable">("unknown");
  const uploadRef = useRef<HTMLInputElement>(null);

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
    const debounce = window.setTimeout(() => void loadTasks(), 180);
    return () => window.clearTimeout(debounce);
  }, [view, query, taskStatus]);

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
      const [data, allNotices] = await Promise.all([
        request<DashboardData>("/api/dashboard"),
        request<{ notices: Notice[] }>("/api/notices"),
      ]);
      setDashboard(data);
      setNotices(allNotices.notices);
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
    if (!["image/jpeg", "image/png", "image/webp", "image/gif"].includes(file.type)) {
      setNoticeError("Choose a PNG, JPEG, WebP, or GIF image.");
      return;
    }
    if (file.size > 12 * 1024 * 1024) {
      setNoticeError("This image is larger than 12 MB. Choose a smaller image.");
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
      await Promise.all([loadDashboard(), loadTasks()]);
      setToast("Task marked complete.");
    } catch (error) {
      setPageError(error instanceof Error ? error.message : "Could not update this task.");
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

  const viewTitle = {
    overview: "Overview",
    analyze: "Scan a notice",
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
          <div className="sidebar-note">
            <span className="sidebar-note-icon"><Sparkles size={15} /></span>
            <p>From notice board to <strong>next step.</strong></p>
          </div>
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
                <p className="intro-copy">Add a photo. We’ll pull out the details; you stay in control.</p>
              </div>
              <span className="model-pill"><span className="status-dot" /> Gemma 4 · image understanding</span>
            </div>

            <div className="scanner-grid">
              <section className="surface-card upload-card">
                <div className="card-heading">
                  <div className="step-title"><span className="step-number">01</span><div><h3>Your notice</h3><p>Choose a clear photo or screenshot</p></div></div>
                  {selectedFile && <button className="icon-button" onClick={removeImage} aria-label="Remove image"><X size={16} /></button>}
                </div>
                <input
                  ref={uploadRef}
                  className="visually-hidden"
                  type="file"
                  accept="image/png,image/jpeg,image/webp,image/gif"
                  onChange={(event) => {
                    acceptImage(event.target.files?.[0]);
                    event.target.value = "";
                  }}
                />
                {previewUrl ? (
                  <div className="image-preview">
                    <img src={previewUrl} alt="Preview of uploaded campus notice" />
                    <div className="image-filename"><FileImage size={14} />{selectedFile?.name}</div>
                  </div>
                ) : (
                  <button
                    className={`dropzone ${dragging ? "dragging" : ""}`}
                    onClick={() => uploadRef.current?.click()}
                    onDragOver={(event) => { event.preventDefault(); setDragging(true); }}
                    onDragLeave={() => setDragging(false)}
                    onDrop={(event) => { event.preventDefault(); setDragging(false); acceptImage(event.dataTransfer.files[0]); }}
                  >
                    <span className="upload-icon"><Upload size={19} /></span>
                    <strong>Drop your image here</strong>
                    <span>or <b>browse files</b> from your device</span>
                    <small>PNG, JPG, WEBP · up to 12 MB</small>
                  </button>
                )}
                <div className="scanner-tip"><Sparkles size={15} /><span>For best results, use a sharp image with the full notice in frame.</span></div>
                <button className="button button-primary full-button" onClick={analyzeImage} disabled={analyzing || !selectedFile}>
                  {analyzing ? <><LoaderCircle className="spin" size={17} /> Reading notice…</> : <><Sparkles size={16} /> Extract details</>}
                </button>
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
            <p className="privacy-note"><Settings2 size={14} /> Your image is analyzed for this request and isn't saved to the notice library unless you choose to save it.</p>
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
                <label className="select-wrap"><span className="visually-hidden">Filter tasks</span><select value={taskStatus} onChange={(event) => setTaskStatus(event.target.value as typeof taskStatus)}><option value="open">To do</option><option value="done">Completed</option><option value="all">All tasks</option></select><ChevronDown size={15} /></label>
              </div>
              {loadingTasks ? (
                <LoadingRows />
              ) : tasks.length ? (
                <div className="managed-task-list">{tasks.map((task) => <TaskRow key={task.id} task={task} onComplete={completeTask} />)}</div>
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
              <div className="list-footer">{tasks.length} {tasks.length === 1 ? "task" : "tasks"} shown</div>
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
            <p>Notices and tasks are stored by the local app. Notice images are sent to Gemini only when you choose to analyze them and are not kept in your library.</p>
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

function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: React.ReactNode }) {
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
      className="app-dialog"
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
