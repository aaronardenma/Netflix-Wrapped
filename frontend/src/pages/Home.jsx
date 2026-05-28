import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
  CheckCircle2,
  Download,
  FileUp,
  LockKeyhole,
  Sparkles,
  UserPlus,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSelector } from "react-redux";
import { selectAuth } from "@/store/authSlice";

const workflowSteps = [
  {
    icon: Download,
    label: "Request your Netflix data",
    detail:
      "Open Netflix's data request page and ask for a copy of your account information.",
    action: "Open Netflix",
    href: "https://www.netflix.com/account/getmyinfo",
    external: true,
  },
  {
    icon: FileUp,
    label: "Upload viewing history",
    detail:
      "When Netflix sends your files, upload the viewing history CSV here.",
    action: "Upload CSV",
    href: "/upload",
  },
  {
    icon: BarChart3,
    label: "Choose a profile and year",
    detail:
      "Pick the Netflix profile and year you want analyzed, then generate your stats.",
    action: "View insights",
    href: "/statistics",
  },
];

const insightStats = [
  { label: "Top genre", value: "Drama" },
  { label: "Peak day", value: "Sunday" },
  { label: "Watch streak", value: "18 days" },
];

export default function Home() {
  const { isAuthenticated, user } = useSelector(selectAuth);

  return (
    <main className="min-h-[calc(100vh-80px)] bg-neutral-950 text-white">
      <section className="px-5 py-10 md:px-8 md:py-16">
        <div className="mx-auto flex max-w-7xl flex-col items-center text-center">
          <div className="mb-5 inline-flex w-fit items-center gap-2 rounded-full border border-red-500/30 bg-red-500/10 px-3 py-1 text-sm font-semibold text-red-100">
            <Sparkles className="size-4" />
            Netflix Wrapped starts with your viewing history
          </div>

          <h1 className="max-w-3xl text-4xl font-black leading-tight tracking-normal text-white md:text-6xl">
            Turn your Netflix history into a personal watch recap.
          </h1>

          <p className="mt-5 max-w-2xl text-base leading-7 text-neutral-300 md:text-lg">
            Request your data from Netflix, upload the viewing activity CSV, and
            generate profile-level insights. Create an account when you want to
            save results, or continue without one for a one-time recap.
          </p>

          <div className="mt-8 flex flex-col justify-center gap-3 sm:flex-row">
            <Button
              asChild
              className="h-11 bg-red-600 px-5 text-white hover:bg-red-700"
            >
              <a
                href="https://www.netflix.com/account/getmyinfo"
                target="_blank"
                rel="noreferrer"
              >
                <Download className="size-4" />
                Get Netflix data
              </a>
            </Button>
            <Button
              asChild
              variant="outline"
              className="h-11 border-white/20 bg-white/5 px-5 text-white hover:bg-white/10 hover:text-white"
            >
              <Link to="/upload">
                <FileUp className="size-4" />
                Upload CSV
              </Link>
            </Button>
          </div>

          <div className="mt-8 grid max-w-4xl gap-3 text-left text-sm text-neutral-300 sm:grid-cols-2">
            <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.04] p-4">
              <LockKeyhole className="mt-0.5 size-5 text-red-400" />
              <div>
                <p className="font-semibold text-white">No account required</p>
                <p className="mt-1">Upload a CSV and generate a recap in one session.</p>
              </div>
            </div>
            <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.04] p-4">
              <UserPlus className="mt-0.5 size-5 text-red-400" />
              <div>
                <p className="font-semibold text-white">
                  {isAuthenticated ? `Signed in as ${user?.firstName}` : "Save with an account"}
                </p>
                <p className="mt-1">
                  {isAuthenticated
                    ? "Your uploads can be tied to your saved profile."
                    : "Create one before uploading when you want to keep your data."}
                </p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-white/10 bg-neutral-100 px-5 py-10 text-neutral-950 md:px-8 md:py-14">
        <div className="mx-auto flex max-w-5xl items-center justify-center">
          <div className="w-full overflow-hidden rounded-lg border border-white/10 bg-neutral-900 shadow-2xl shadow-red-950/30">
            <div className="border-b border-white/10 bg-neutral-950/70 px-5 py-4">
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-semibold text-neutral-400">
                    Preview
                  </p>
                  <h2 className="text-xl font-bold text-white">
                    Your 2025 recap
                  </h2>
                </div>
                <div className="rounded-full bg-red-600 px-3 py-1 text-sm font-bold">
                  Ready
                </div>
              </div>
            </div>

            <div className="grid gap-4 p-5">
              <div className="grid grid-cols-3 gap-3">
                {insightStats.map((stat) => (
                  <div
                    key={stat.label}
                    className="rounded-md border border-white/10 bg-white/[0.04] p-3"
                  >
                    <p className="text-xs font-semibold uppercase text-neutral-500">
                      {stat.label}
                    </p>
                    <p className="mt-2 text-lg font-bold text-white">
                      {stat.value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="rounded-md border border-white/10 bg-black/30 p-4">
                <div className="mb-4 flex items-center justify-between">
                  <p className="font-semibold text-white">Watching by month</p>
                  <BarChart3 className="size-5 text-red-400" />
                </div>
                <div className="flex h-44 items-end gap-2">
                  {[42, 68, 54, 88, 73, 96, 61, 79, 52, 70, 91, 65].map(
                    (height, index) => (
                      <div
                        key={index}
                        className="flex flex-1 items-end rounded-t bg-red-600/20"
                      >
                        <div
                          className="w-full rounded-t bg-red-600"
                          style={{ height: `${height}%` }}
                        />
                      </div>
                    )
                  )}
                </div>
              </div>

              <div className="grid gap-2">
                {["ViewingActivity.csv uploaded", "Profile selected", "Insights generated"].map(
                  (item) => (
                    <div
                      key={item}
                      className="flex items-center gap-3 rounded-md border border-white/10 bg-white/[0.04] px-3 py-2 text-sm font-medium text-neutral-200"
                    >
                      <CheckCircle2 className="size-4 text-red-400" />
                      {item}
                    </div>
                  )
                )}
              </div>
            </div>
          </div>
        </div>
      </section>

      <section className="border-t border-neutral-300 bg-neutral-200 px-5 py-12 text-neutral-950 md:px-8 md:py-16">
        <div className="mx-auto max-w-7xl">
          <div className="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
            <div>
              <p className="text-sm font-bold uppercase text-red-700">
                Workflow
              </p>
              <h2 className="mt-2 text-3xl font-black tracking-normal">
                From Netflix export to insights
              </h2>
            </div>
            {!isAuthenticated && (
              <Button asChild variant="outline" className="w-fit">
                <Link to="/auth/create">
                  <UserPlus className="size-4" />
                  Create account
                </Link>
              </Button>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-3">
            {workflowSteps.map((step, index) => {
              const Icon = step.icon;
              const content = (
                <>
                  <div className="mb-5 flex items-center justify-between">
                    <div className="flex size-11 items-center justify-center rounded-md bg-red-600 text-white">
                      <Icon className="size-5" />
                    </div>
                    <span className="text-sm font-black text-neutral-300">
                      0{index + 1}
                    </span>
                  </div>
                  <h3 className="text-xl font-bold">{step.label}</h3>
                  <p className="mt-3 min-h-20 text-sm leading-6 text-neutral-600">
                    {step.detail}
                  </p>
                  <div className="mt-5 inline-flex items-center gap-2 text-sm font-bold text-red-600">
                    {step.action}
                    <ArrowRight className="size-4" />
                  </div>
                </>
              );

              return step.external ? (
                <a
                  key={step.label}
                  href={step.href}
                  target="_blank"
                  rel="noreferrer"
                  className="rounded-lg border border-neutral-300 bg-neutral-50 p-5 shadow-md shadow-neutral-300/60 transition hover:-translate-y-0.5 hover:border-red-300 hover:shadow-lg"
                >
                  {content}
                </a>
              ) : (
                <Link
                  key={step.label}
                  to={step.href}
                  className="rounded-lg border border-neutral-300 bg-neutral-50 p-5 shadow-md shadow-neutral-300/60 transition hover:-translate-y-0.5 hover:border-red-300 hover:shadow-lg"
                >
                  {content}
                </Link>
              );
            })}
          </div>
        </div>
      </section>
    </main>
  );
}
