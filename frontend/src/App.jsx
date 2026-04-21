import { startTransition, useEffect, useState } from "react";

const emptyRegisterForm = {
  name: "",
  email: "",
  password: "",
};

const emptyLoginForm = {
  email: "",
  password: "",
};

const emptyEditorForm = {
  id: null,
  name: "",
  email: "",
  password: "",
};

const tokenStorageKey = "user_management_token";

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(tokenStorageKey) || "");
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [registerForm, setRegisterForm] = useState(emptyRegisterForm);
  const [loginForm, setLoginForm] = useState(emptyLoginForm);
  const [editorForm, setEditorForm] = useState(emptyEditorForm);
  const [registerStatus, setRegisterStatus] = useState({ message: "", kind: "" });
  const [authStatus, setAuthStatus] = useState({ message: "", kind: "" });
  const [listStatus, setListStatus] = useState({ message: "Login required to load users.", kind: "" });
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [isSavingUser, setIsSavingUser] = useState(false);

  useEffect(() => {
    if (token) {
      localStorage.setItem(tokenStorageKey, token);
      hydrateSession();
      return;
    }

    localStorage.removeItem(tokenStorageKey);
    startTransition(() => {
      setCurrentUser(null);
      setUsers([]);
    });
    setListStatus({ message: "Login required to load users.", kind: "" });
  }, [token]);

  async function apiRequest(path, options = {}) {
    const headers = {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    };

    if (token && !headers.Authorization) {
      headers.Authorization = `Bearer ${token}`;
    }

    const response = await fetch(path, { ...options, headers });
    const contentType = response.headers.get("content-type") || "";
    const payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();

    if (!response.ok) {
      const detail = typeof payload === "object" && payload?.detail
        ? payload.detail
        : "Request failed";
      throw new Error(detail);
    }

    return payload;
  }

  async function hydrateSession(message = "Loading users...") {
    if (!token) {
      return;
    }

    setIsLoadingUsers(true);
    setListStatus({ message, kind: "" });

    try {
      const [me, userList] = await Promise.all([
        apiRequest("/auth/me", { method: "GET" }),
        apiRequest("/users", { method: "GET" }),
      ]);

      startTransition(() => {
        setCurrentUser(me);
        setUsers(userList);
      });
      setListStatus({
        message: `Loaded ${userList.length} user(s).`,
        kind: "success",
      });
    } catch (error) {
      if (error.message === "Invalid or expired token" || error.message === "Not authenticated") {
        localStorage.removeItem(tokenStorageKey);
        setToken("");
        setAuthStatus({ message: "Session expired. Please log in again.", kind: "error" });
      }
      setListStatus({ message: error.message, kind: "error" });
    } finally {
      setIsLoadingUsers(false);
    }
  }

  function handleFieldChange(setter) {
    return (event) => {
      const { name, value } = event.target;
      setter((current) => ({ ...current, [name]: value }));
    };
  }

  async function handleRegister(event) {
    event.preventDefault();
    setRegisterStatus({ message: "Creating account...", kind: "" });

    try {
      await apiRequest("/users", {
        method: "POST",
        body: JSON.stringify(registerForm),
      });
      setRegisterForm(emptyRegisterForm);
      setRegisterStatus({
        message: "Account created. You can log in now.",
        kind: "success",
      });
    } catch (error) {
      setRegisterStatus({ message: error.message, kind: "error" });
    }
  }

  async function handleLogin(event) {
    event.preventDefault();
    setAuthStatus({ message: "Requesting token...", kind: "" });

    try {
      const data = await apiRequest("/auth/login", {
        method: "POST",
        body: JSON.stringify(loginForm),
      });
      setToken(data.access_token);
      setLoginForm(emptyLoginForm);
      setAuthStatus({ message: "Logged in successfully.", kind: "success" });
    } catch (error) {
      setAuthStatus({ message: error.message, kind: "error" });
    }
  }

  function openEditor(user) {
    setEditorForm({
      id: user.id,
      name: user.name,
      email: user.email,
      password: "",
    });
  }

  function closeEditor() {
    setEditorForm(emptyEditorForm);
  }

  async function handleUpdateUser(event) {
    event.preventDefault();
    if (!editorForm.id) {
      return;
    }

    const payload = {
      name: editorForm.name,
      email: editorForm.email,
    };
    if (editorForm.password.trim()) {
      payload.password = editorForm.password;
    }

    setIsSavingUser(true);
    setListStatus({ message: `Updating user ${editorForm.id}...`, kind: "" });

    try {
      await apiRequest(`/users/${editorForm.id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      closeEditor();
      await hydrateSession(`Refreshing after updating user ${editorForm.id}...`);
    } catch (error) {
      setListStatus({ message: error.message, kind: "error" });
    } finally {
      setIsSavingUser(false);
    }
  }

  async function handleDeleteUser(userId) {
    const confirmed = window.confirm(`Delete user ${userId}?`);
    if (!confirmed) {
      return;
    }

    setListStatus({ message: `Deleting user ${userId}...`, kind: "" });

    try {
      await apiRequest(`/users/${userId}`, { method: "DELETE" });
      await hydrateSession(`Refreshing after deleting user ${userId}...`);
    } catch (error) {
      setListStatus({ message: error.message, kind: "error" });
    }
  }

  function handleLogout() {
    setToken("");
    setAuthStatus({ message: "Logged out.", kind: "" });
    closeEditor();
  }

  return (
    <main className="shell">
      <section className="hero">
        <p className="eyebrow">React Frontend</p>
        <h1>User Dashboard</h1>
        <p>
          This React app talks to the FastAPI backend for registration, JWT login,
          protected CRUD, and user session checks.
        </p>
      </section>

      <section className="grid">
        <aside className="panel stack">
          <section className="stack">
            <div className="section-heading">
              <h2>Register</h2>
              <p>Create a new account with a hashed password.</p>
            </div>
            <form className="stack" onSubmit={handleRegister}>
              <label>
                Name
                <input
                  name="name"
                  type="text"
                  placeholder="Ayesha Khan"
                  value={registerForm.name}
                  onChange={handleFieldChange(setRegisterForm)}
                  required
                />
              </label>
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  placeholder="ayesha@example.com"
                  value={registerForm.email}
                  onChange={handleFieldChange(setRegisterForm)}
                  required
                />
              </label>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  placeholder="At least 8 characters"
                  minLength="8"
                  value={registerForm.password}
                  onChange={handleFieldChange(setRegisterForm)}
                  required
                />
              </label>
              <button className="primary" type="submit">Create Account</button>
            </form>
            <StatusLine status={registerStatus} />
          </section>

          <section className="stack auth-panel">
            <div className="section-heading">
              <h2>Login</h2>
              <p>Exchange email and password for a JWT bearer token.</p>
            </div>
            <form className="stack" onSubmit={handleLogin}>
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  placeholder="ayesha@example.com"
                  value={loginForm.email}
                  onChange={handleFieldChange(setLoginForm)}
                  required
                />
              </label>
              <label>
                Password
                <input
                  name="password"
                  type="password"
                  placeholder="Your password"
                  minLength="8"
                  value={loginForm.password}
                  onChange={handleFieldChange(setLoginForm)}
                  required
                />
              </label>
              <button className="primary" type="submit">Get Token</button>
            </form>

            <div className="toolbar compact">
              <div>
                <h3>JWT Token</h3>
                <p className="muted-copy">Stored in localStorage for this browser.</p>
              </div>
              <button className="secondary" type="button" onClick={handleLogout}>
                Logout
              </button>
            </div>
            <div className="token-box">{token || "No token yet. Log in to unlock protected routes."}</div>
            <StatusLine status={authStatus} />
          </section>
        </aside>

        <section className="panel results-panel">
          <div className="toolbar">
            <div>
              <h2>Protected Users List</h2>
              <p className="muted-copy">
                Load users, inspect the authenticated session, and edit data through the API.
              </p>
            </div>
            <button
              className="secondary"
              type="button"
              onClick={() => hydrateSession("Refreshing users...")}
              disabled={!token || isLoadingUsers}
            >
              {isLoadingUsers ? "Loading..." : "Refresh"}
            </button>
          </div>

          <div className="session-card">
            <p className="session-label">Authenticated User</p>
            {currentUser ? (
              <div>
                <strong>{currentUser.name}</strong>
                <p className="session-meta">{currentUser.email}</p>
              </div>
            ) : (
              <p className="session-meta">Log in to load your current user session.</p>
            )}
          </div>

          <StatusLine status={listStatus} />

          <div className="users">
            {!users.length ? (
              <div className="empty">
                {token
                  ? "No users found yet. Create one and refresh."
                  : "Log in to load protected user data."}
              </div>
            ) : (
              users.map((user) => (
                <article key={user.id} className="user-card">
                  <div className="user-top">
                    <div>
                      <h3 className="user-title">{user.name}</h3>
                      <p className="user-meta">{user.email}</p>
                    </div>
                    <span className="badge">ID {user.id}</span>
                  </div>
                  <div className="user-actions">
                    <button className="secondary" type="button" onClick={() => openEditor(user)}>
                      Edit
                    </button>
                    <button className="danger" type="button" onClick={() => handleDeleteUser(user.id)}>
                      Delete
                    </button>
                  </div>
                </article>
              ))
            )}
          </div>
        </section>
      </section>

      {editorForm.id ? (
        <div className="modal-backdrop" role="presentation" onClick={closeEditor}>
          <section
            className="modal panel"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-user-heading"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="toolbar compact">
              <div>
                <h2 id="edit-user-heading">Edit User</h2>
                <p className="muted-copy">Update the selected user and optionally rotate the password.</p>
              </div>
              <button className="secondary" type="button" onClick={closeEditor}>
                Close
              </button>
            </div>

            <form className="stack" onSubmit={handleUpdateUser}>
              <label>
                Name
                <input
                  name="name"
                  type="text"
                  value={editorForm.name}
                  onChange={handleFieldChange(setEditorForm)}
                  required
                />
              </label>
              <label>
                Email
                <input
                  name="email"
                  type="email"
                  value={editorForm.email}
                  onChange={handleFieldChange(setEditorForm)}
                  required
                />
              </label>
              <label>
                New Password
                <input
                  name="password"
                  type="password"
                  minLength="8"
                  placeholder="Leave blank to keep the current password"
                  value={editorForm.password}
                  onChange={handleFieldChange(setEditorForm)}
                />
              </label>
              <div className="user-actions">
                <button className="primary" type="submit" disabled={isSavingUser}>
                  {isSavingUser ? "Saving..." : "Save Changes"}
                </button>
                <button className="secondary" type="button" onClick={closeEditor}>
                  Cancel
                </button>
              </div>
            </form>
          </section>
        </div>
      ) : null}
    </main>
  );
}

function StatusLine({ status }) {
  const className = status.kind ? `status ${status.kind}` : "status";
  return <p className={className}>{status.message}</p>;
}

export default App;
