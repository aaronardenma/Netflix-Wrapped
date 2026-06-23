import { Link } from "react-router-dom";
import {
  ArrowRight,
  BarChart3,
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
    label: "Request your Netflix history",
    detail:
      "Ask Netflix for a copy of your account history so your recap can be created.",
    action: "Request history",
    href: "https://www.netflix.com/account/getmyinfo",
    external: true,
  },
  {
    icon: FileUp,
    label: "Bring in your history",
    detail:
      "Choose the viewing history file Netflix sends you and we’ll prepare your recap.",
    action: "Create recap",
    href: "/create",
  },
  {
    icon: BarChart3,
    label: "Choose a profile and year",
    detail:
      "Pick the profile and year you want to explore, then see your personalized results.",
    action: "View results",
    href: "/recap",
  },
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
            Bring in your Netflix viewing history and turn it into a personalized
            recap. Create an account when you want to save your results, or
            continue without one for a one-time experience.
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
                Request my history
              </a>
            </Button>
            <Button
              asChild
              variant="outline"
              className="h-11 border-white/20 bg-white/5 px-5 text-white hover:bg-white/10 hover:text-white"
            >
              <Link to="/create">
                <FileUp className="size-4" />
                Create my recap
              </Link>
            </Button>
          </div>

          <div className="mt-8 grid max-w-4xl gap-3 text-left text-sm text-neutral-300 sm:grid-cols-2">
            <div className="flex items-start gap-3 rounded-lg border border-white/10 bg-white/[0.04] p-4">
              <LockKeyhole className="mt-0.5 size-5 text-red-400" />
              <div>
                <p className="font-semibold text-white">No account required</p>
                <p className="mt-1">Create and explore a recap in one session.</p>
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
                    ? "Your viewing history and recaps can be saved to your profile."
                    : "Create one before starting when you want to keep your results."}
                </p>
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
