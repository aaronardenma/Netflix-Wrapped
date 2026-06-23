import { useMemo, useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useDispatch, useSelector } from "react-redux";
import { authAPI } from "@/services/api";
import { authExpired, selectAuth } from "@/store/authSlice";
import { Input } from "@/components/ui/input";
import { MdLockOutline, MdOutlineDeleteForever, MdStorage } from "react-icons/md";

const SECTIONS = [
  { key: "password", label: "Password management", icon: MdLockOutline },
  { key: "data", label: "Data management", icon: MdStorage },
  { key: "delete", label: "Delete account", icon: MdOutlineDeleteForever },
];

function getErrorMessage(error) {
  const detail = error?.response?.data?.error || error;
  if (Array.isArray(detail)) {
    return detail.join(" ");
  }
  return typeof detail === "string" ? detail : "Request failed.";
}

export default function Profile() {
  const { isAuthenticated, user, loading } = useSelector(selectAuth);
  const [activeSection, setActiveSection] = useState("password");
  const [message, setMessage] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [passwordForm, setPasswordForm] = useState({
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  });
  const [dataForm, setDataForm] = useState({
    currentPassword: "",
    confirmation: "",
  });
  const [deleteForm, setDeleteForm] = useState({
    currentPassword: "",
    confirmation: "",
  });
  const dispatch = useDispatch();
  const nav = useNavigate();

  const activeLabel = useMemo(
    () => SECTIONS.find((section) => section.key === activeSection)?.label,
    [activeSection]
  );

  if (loading) {
    return <div className="p-8 text-sm text-gray-500">Loading account...</div>;
  }

  if (!isAuthenticated) {
    return <Navigate to="/auth/login" replace />;
  }

  const handlePasswordSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");

    try {
      if (passwordForm.newPassword !== passwordForm.confirmPassword) {
        setMessage("Passwords do not match.");
        return;
      }

      await authAPI.changePassword({
        currentPassword: passwordForm.currentPassword,
        newPassword: passwordForm.newPassword,
      });
      dispatch(authExpired());
      setMessage("Password updated. Please sign in again.");
      nav("/auth/login");
    } catch (error) {
      setMessage(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  const handleWipeSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");

    try {
      if (dataForm.confirmation !== "WIPE MY DATA") {
        setMessage('Type "WIPE MY DATA" to confirm.');
        return;
      }

      const response = await authAPI.wipeAccountData({
        currentPassword: dataForm.currentPassword,
      });
      setMessage(response.data?.message || "Your saved data has been removed.");
      setDataForm({ currentPassword: "", confirmation: "" });
    } catch (error) {
      setMessage(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  const handleDeleteSubmit = async (event) => {
    event.preventDefault();
    setSubmitting(true);
    setMessage("");

    try {
      if (deleteForm.confirmation !== "DELETE MY ACCOUNT") {
        setMessage('Type "DELETE MY ACCOUNT" to confirm.');
        return;
      }

      await authAPI.deleteAccount({
        currentPassword: deleteForm.currentPassword,
      });
      dispatch(authExpired());
      nav("/auth/login");
    } catch (error) {
      setMessage(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="mx-auto max-w-6xl px-6 py-8">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-neutral-950">Account</h1>
        <p className="mt-1 text-sm text-neutral-600">
          Manage password changes, saved data, and account deletion from one place.
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="border border-neutral-200 bg-white p-3">
          <div className="mb-3 px-2 py-1 text-xs font-semibold uppercase tracking-wide text-neutral-500">
            Settings
          </div>
          <div className="flex flex-col gap-1">
            {SECTIONS.map((section) => {
              const Icon = section.icon;
              const isActive = activeSection === section.key;
              return (
                <button
                  key={section.key}
                  type="button"
                  onClick={() => {
                    setActiveSection(section.key);
                    setMessage("");
                  }}
                  className={`flex cursor-pointer items-center gap-2 px-3 py-2 text-left text-sm font-medium transition-colors ${
                    isActive
                      ? "bg-black text-white"
                      : "text-neutral-700 hover:bg-neutral-100"
                  }`}
                >
                  <Icon className="text-lg" />
                  <span>{section.label}</span>
                </button>
              );
            })}
          </div>
        </aside>

        <main className="border border-neutral-200 bg-white p-6">
          <div className="mb-6">
            <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
              {activeLabel}
            </p>
            <h2 className="mt-1 text-xl font-semibold text-neutral-950">
              {activeSection === "password"
                ? "Update your password"
                : activeSection === "data"
                ? "Remove saved Netflix data"
                : "Delete your account"}
            </h2>
            <p className="mt-1 text-sm text-neutral-600">
              {activeSection === "password"
                ? "Change your password and sign in again with the new credentials."
                : activeSection === "data"
                ? "This clears your saved viewing history, profiles, and recap results."
                : "This permanently removes your account and all account-owned data."}
            </p>
          </div>

          {activeSection === "password" && (
            <form className="space-y-4" onSubmit={handlePasswordSubmit}>
              <div>
                <p className="mb-2 text-xs ml-1 text-gray-500">Current password</p>
                <Input
                  type="password"
                  value={passwordForm.currentPassword}
                  onChange={(e) =>
                    setPasswordForm((current) => ({
                      ...current,
                      currentPassword: e.target.value,
                    }))
                  }
                  required
                  disabled={submitting}
                />
              </div>
              <div>
                <p className="mb-2 text-xs ml-1 text-gray-500">New password</p>
                <Input
                  type="password"
                  value={passwordForm.newPassword}
                  onChange={(e) =>
                    setPasswordForm((current) => ({
                      ...current,
                      newPassword: e.target.value,
                    }))
                  }
                  required
                  disabled={submitting}
                />
              </div>
              <div>
                <p className="mb-2 text-xs ml-1 text-gray-500">Confirm new password</p>
                <Input
                  type="password"
                  value={passwordForm.confirmPassword}
                  onChange={(e) =>
                    setPasswordForm((current) => ({
                      ...current,
                      confirmPassword: e.target.value,
                    }))
                  }
                  required
                  disabled={submitting}
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="rounded cursor-pointer bg-black px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Saving..." : "Change password"}
              </button>
            </form>
          )}

          {activeSection === "data" && (
            <form className="space-y-4" onSubmit={handleWipeSubmit}>
              <div>
                <p className="mb-2 text-xs ml-1 text-gray-500">Current password</p>
                <Input
                  type="password"
                  value={dataForm.currentPassword}
                  onChange={(e) =>
                    setDataForm((current) => ({
                      ...current,
                      currentPassword: e.target.value,
                    }))
                  }
                  required
                  disabled={submitting}
                />
              </div>
              <div>
                <p className="mb-2 text-xs ml-1 text-gray-500">Type WIPE MY DATA to confirm</p>
                <Input
                  type="text"
                  value={dataForm.confirmation}
                  onChange={(e) =>
                    setDataForm((current) => ({
                      ...current,
                      confirmation: e.target.value,
                    }))
                  }
                  required
                  disabled={submitting}
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="rounded cursor-pointer bg-black px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Removing..." : "Wipe saved data"}
              </button>
            </form>
          )}

          {activeSection === "delete" && (
            <form className="space-y-4" onSubmit={handleDeleteSubmit}>
              <div>
                <p className="mb-2 text-xs ml-1 text-gray-500">Current password</p>
                <Input
                  type="password"
                  value={deleteForm.currentPassword}
                  onChange={(e) =>
                    setDeleteForm((current) => ({
                      ...current,
                      currentPassword: e.target.value,
                    }))
                  }
                  required
                  disabled={submitting}
                />
              </div>
              <div>
                <p className="mb-2 text-xs ml-1 text-gray-500">Type DELETE MY ACCOUNT to confirm</p>
                <Input
                  type="text"
                  value={deleteForm.confirmation}
                  onChange={(e) =>
                    setDeleteForm((current) => ({
                      ...current,
                      confirmation: e.target.value,
                    }))
                  }
                  required
                  disabled={submitting}
                />
              </div>
              <button
                type="submit"
                disabled={submitting}
                className="rounded bg-red-600 cursor-pointer px-4 py-2 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-50"
              >
                {submitting ? "Deleting..." : "Delete account"}
              </button>
            </form>
          )}

          {message && (
            <p
              className={`mt-4 text-sm ${
                message.toLowerCase().includes("success") ||
                message.toLowerCase().includes("removed") ||
                message.toLowerCase().includes("updated")
                  ? "text-green-600"
                  : "text-red-600"
              }`}
            >
              {message}
            </p>
          )}

          <div className="mt-6 border-t border-neutral-200 pt-4 text-sm text-neutral-600">
            Signed in as <span className="font-semibold text-neutral-900">{user?.email}</span>
          </div>
        </main>
      </div>
    </div>
  );
}
