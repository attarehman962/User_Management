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

const emptyStatus = {
  message: "",
  kind: "",
};

const defaultListStatus = {
  message: "Sign in to load protected user records.",
  kind: "",
};

const tokenStorageKey = "user_management_token";

function roleLabel(role) {
  return role === "admin" ? "Admin" : "Local User";
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem(tokenStorageKey) || "");
  const [authView, setAuthView] = useState("signin");
  const [currentUser, setCurrentUser] = useState(null);
  const [users, setUsers] = useState([]);
  const [registerForm, setRegisterForm] = useState(emptyRegisterForm);
  const [loginForm, setLoginForm] = useState(emptyLoginForm);
  const [editorForm, setEditorForm] = useState(emptyEditorForm);
  const [registerStatus, setRegisterStatus] = useState(emptyStatus);
  const [authStatus, setAuthStatus] = useState(emptyStatus);
  const [listStatus, setListStatus] = useState(defaultListStatus);
  const [isLoadingUsers, setIsLoadingUsers] = useState(false);
  const [isSavingUser, setIsSavingUser] = useState(false);

  const isAuthenticated = Boolean(token);
  const isAdmin = currentUser?.role === "admin";

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
    setListStatus(defaultListStatus);
    setEditorForm(emptyEditorForm);
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

  async function hydrateSession(message = "Loading dashboard...") {
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
        message: isAdminMessage(me.role, userList.length),
        kind: "success",
      });
    } catch (error) {
      if (error.message === "Invalid or expired token" || error.message === "Not authenticated") {
        localStorage.removeItem(tokenStorageKey);
        setToken("");
        setAuthStatus({ message: "Session expired. Please sign in again.", kind: "error" });
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
      const createdUser = await apiRequest("/users", {
        method: "POST",
        body: JSON.stringify(registerForm),
      });

      setRegisterForm(emptyRegisterForm);
      if (token) {
        setRegisterStatus({
          message: `${createdUser.name} created successfully as ${roleLabel(createdUser.role)}.`,
          kind: "success",
        });
        await hydrateSession("Refreshing directory...");
      } else {
        setAuthView("signin");
        setRegisterStatus({
          message: "Account created successfully. You can sign in now.",
          kind: "success",
        });
      }
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
      setAuthStatus({ message: "Signed in successfully.", kind: "success" });
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
      await hydrateSession(`Refreshing records after updating user ${editorForm.id}...`);
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
      await hydrateSession(`Refreshing records after deleting user ${userId}...`);
    } catch (error) {
      setListStatus({ message: error.message, kind: "error" });
    }
  }

  function handleLogout() {
    setToken("");
    setAuthStatus({ message: "Signed out.", kind: "" });
    setRegisterStatus(emptyStatus);
    closeEditor();
  }

  function canManageUser(user) {
    if (!currentUser) {
      return false;
    }

    return isAdmin || currentUser.id === user.id;
  }

  return (
    <div className={`app-shell ${isAuthenticated ? "dashboard-mode" : "auth-mode"}`}>
      <nav className="topbar reveal rise-1">
        <div className="brand-block">
          <p className="brand-kicker">Backend-first dashboard</p>
          <h1>User Management Control Center</h1>
        </div>

        <div className="topbar-actions">
          {!isAuthenticated ? (
            <>
              <button
                className={authView === "signin" ? "secondary active-button" : "secondary"}
                type="button"
                onClick={() => setAuthView("signin")}
              >
                Sign In
              </button>
              <button
                className={authView === "signup" ? "primary active-button" : "primary"}
                type="button"
                onClick={() => setAuthView("signup")}
              >
                Sign Up
              </button>
            </>
          ) : (
            <>
              <RolePill role={currentUser?.role} />
              <button
                className="secondary"
                type="button"
                onClick={() => hydrateSession("Refreshing dashboard...")}
                disabled={isLoadingUsers}
              >
                {isLoadingUsers ? "Refreshing..." : "Refresh"}
              </button>
              <button className="primary" type="button" onClick={handleLogout}>
                Logout
              </button>
            </>
          )}
        </div>
      </nav>

      {!isAuthenticated ? (
        <>
          <section className="auth-layout">
            <section className="panel auth-panel auth-card reveal rise-3">
              {authView === "signin" ? (
                <>
                  <div className="section-heading">
                    <h3>Sign In</h3>
                    <p>Authenticate with the existing JWT flow and load your role-based dashboard.</p>
                  </div>

                  <form className="form-stack" onSubmit={handleLogin}>
                    <label>
                      Email
                      <input
                        name="email"
                        type="email"
                        placeholder="admin@example.com"
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
                    <button className="primary" type="submit">
                      Sign In
                    </button>
                  </form>

                  <StatusLine status={authStatus} />
                </>
              ) : (
                <>
                  <div className="section-heading">
                    <h3>Sign Up</h3>
                    <p>Create a new local user account. A default admin account is seeded automatically when the system starts with an empty database.</p>
                  </div>

                  <form className="form-stack" onSubmit={handleRegister}>
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
                    <button className="primary" type="submit">
                      Create Account
                    </button>
                  </form>

                  <StatusLine status={registerStatus} />
                </>
              )}
            </section>
          </section>
        </>
      ) : (
        <>
          <section className="dashboard-grid">
            <aside className="dashboard-sidebar">
              <section className="panel profile-panel reveal rise-2">
                <div className="section-heading">
                  <h3>Session Profile</h3>
                  <p>Authenticated identity and access context from the backend.</p>
                </div>

                <div className="profile-card">
                  <p className="profile-name">{currentUser?.name}</p>
                  <p className="profile-email">{currentUser?.email}</p>
                  <div className="profile-meta">
                    <RolePill role={currentUser?.role} />
                    <span className="muted-label">User ID {currentUser?.id}</span>
                  </div>
                </div>
              </section>

              {isAdmin ? (
                <section className="panel create-panel reveal rise-4">
                  <div className="section-heading">
                    <h3>Create User Account</h3>
                    <p>Provision a new account without leaving the dashboard.</p>
                  </div>

                  <form className="form-stack" onSubmit={handleRegister}>
                    <label>
                      Name
                      <input
                        name="name"
                        type="text"
                        placeholder="New team member"
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
                        placeholder="member@example.com"
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
                        placeholder="Temporary password"
                        minLength="8"
                        value={registerForm.password}
                        onChange={handleFieldChange(setRegisterForm)}
                        required
                      />
                    </label>
                    <button className="primary" type="submit">
                      Add User
                    </button>
                  </form>

                  <StatusLine status={registerStatus} />
                </section>
              ) : null}
            </aside>

            <section className="panel directory-panel reveal rise-3">
              <div className="toolbar">
                <div>
                  <h3>{isAdmin ? "User Directory" : "User Directory"}</h3>
                  <p className="muted-copy">
                    {isAdmin
                      ? "Full backend-backed user listing with management controls."
                      : "Directory visibility for all authenticated users, with self-only account actions."}
                  </p>
                </div>
                <div className="toolbar-copy">
                  <span className="muted-label">
                    {isAdmin ? "Directory scope: all users" : "Directory scope: all users, actions limited to self"}
                  </span>
                </div>
              </div>

              <StatusLine status={listStatus} />

              {users.length ? (
                <div className="table-shell">
                  <table>
                    <thead>
                      <tr>
                        <th>Name</th>
                        <th>Email</th>
                        {isAdmin ? <th>Role</th> : null}
                        <th>ID</th>
                        <th>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {users.map((user) => (
                        <tr key={user.id}>
                          <td>
                            <div className="cell-stack">
                              <strong>{user.name}</strong>
                              {currentUser?.id === user.id ? <span className="row-caption">Current session</span> : null}
                            </div>
                          </td>
                          <td>{user.email}</td>
                          {isAdmin ? (
                            <td>
                              <RolePill role={user.role} />
                            </td>
                          ) : null}
                          <td>{user.id}</td>
                          <td>
                            <div className="table-actions">
                              <button
                                className="secondary"
                                type="button"
                                onClick={() => openEditor(user)}
                                disabled={!canManageUser(user)}
                              >
                                Edit
                              </button>
                              <button
                                className="danger"
                                type="button"
                                onClick={() => handleDeleteUser(user.id)}
                                disabled={!canManageUser(user)}
                              >
                                Delete
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="empty-state">
                  <p>No user records are available yet.</p>
                </div>
              )}
            </section>
          </section>
        </>
      )}

      {editorForm.id ? (
        <div className="modal-backdrop" role="presentation" onClick={closeEditor}>
          <section
            className="modal-panel panel reveal-pop"
            role="dialog"
            aria-modal="true"
            aria-labelledby="edit-user-heading"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="toolbar">
              <div>
                <h3 id="edit-user-heading">Edit User</h3>
                <p className="muted-copy">Update profile details while preserving the existing backend API contract.</p>
              </div>
              <button className="secondary" type="button" onClick={closeEditor}>
                Close
              </button>
            </div>

            <form className="form-stack" onSubmit={handleUpdateUser}>
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
              <div className="table-actions">
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
    </div>
  );
}

function StatusLine({ status }) {
  const className = status.kind ? `status ${status.kind}` : "status";
  return <p className={className}>{status.message}</p>;
}

function MetricCard({ label, value, meta }) {
  return (
    <article className="metric-card panel">
      <p className="metric-label">{label}</p>
      <h3>{value}</h3>
      <p className="metric-meta">{meta}</p>
    </article>
  );
}

function RolePill({ role }) {
  return <span className={`role-pill ${role || "user"}`}>{roleLabel(role)}</span>;
}

function isAdminMessage(role, count) {
  if (role === "admin") {
    return `Loaded ${count} user record${count === 1 ? "" : "s"} with admin access.`;
  }

  return `Loaded ${count} user record${count === 1 ? "" : "s"} with user-level directory access.`;
}

export default App;
