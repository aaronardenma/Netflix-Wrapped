import { useEffect, useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import VisualizationBoard from "@/components/VisualizationBoard";
import { netflixAPI } from "@/services/api";
import CoreStatsGrid from "@/components/CoreStatsGrid";
import GenreContentInsights from "@/components/GenreContentInsights";
import ProfileComparisons from "@/components/ProfileComparisons";
import TitleLevelInsights from "@/components/TitleLevelInsights";
import WrappedCards from "@/components/WrappedCards";
import ProfileRecommendations from "@/components/ProfileRecommendations";
import { selectAuth } from "@/store/authSlice";
import {
  ChartNoAxesCombinedIcon,
  CalendarDaysIcon,
  CheckIcon,
  ClapperboardIcon,
  GitCompareArrowsIcon,
  LayoutDashboardIcon,
  LogInIcon,
  SparklesIcon,
  TagsIcon,
  UploadIcon,
  UserRoundIcon,
  UsersRoundIcon,
} from "lucide-react";
import { toast, ToastContainer } from "react-toastify";

const SESSION_UPLOAD_KEY = "netflixWrapped:lastAnonymousUpload";
const ALL_YEARS_VALUE = "all";
const STAT_TABS = [
  { value: "overview", label: "Overview", icon: LayoutDashboardIcon },
  { value: "compare", label: "Compare", icon: GitCompareArrowsIcon },
  { value: "titles", label: "Titles", icon: ClapperboardIcon },
  { value: "content", label: "Content", icon: TagsIcon },
  { value: "profiles", label: "Profiles", icon: UsersRoundIcon },
  { value: "visualizations", label: "Visualizations", icon: ChartNoAxesCombinedIcon },
  { value: "for-you", label: "For You", icon: SparklesIcon },
];
const PARTIAL_PENDING_TABS = new Set(["compare", "content", "profiles", "visualizations"]);

async function fetchStoredData() {
  const res = await netflixAPI.getStoredData();
  return res.data;
}

const sortYearsDesc = (years = []) =>
  [
    ...new Set(
      years
        .filter((year) => year !== ALL_YEARS_VALUE)
        .map(Number)
        .filter((year) => !Number.isNaN(year))
    ),
  ].sort((a, b) => b - a);

export default function Statistics() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [compareYearA, setCompareYearA] = useState("");
  const [compareYearB, setCompareYearB] = useState("");
  const { isAuthenticated, loading: authLoading } = useSelector(selectAuth);
  const profile = searchParams.get("profile") || null;
  const year = searchParams.get("year") || null;
  const jobId = searchParams.get("job_id") || null;
  const requestedView = searchParams.get("view") || "overview";
  const activeView = STAT_TABS.some((tab) => tab.value === requestedView)
    ? requestedView
    : "overview";
  const [anonymousUpload, setAnonymousUpload] = useState(() => {
    try {
      const rawUpload = sessionStorage.getItem(SESSION_UPLOAD_KEY);
      return rawUpload ? JSON.parse(rawUpload) : null;
    } catch {
      return null;
    }
  });

  const {
    data: storedData,
    error: storedDataError,
    isLoading: isStoredDataLoading,
  } = useQuery({
    queryFn: fetchStoredData,
    queryKey: ["storedData"],
    enabled: !authLoading && isAuthenticated,
  });

  const {
    data: processingStatus,
    error: processingStatusError,
    isLoading: isProcessingStatusLoading,
  } = useQuery({
    queryFn: async () => {
      const res = await netflixAPI.getProcessingStatus(jobId);
      return res.data;
    },
    queryKey: ["processingStatus", jobId],
    enabled: !!jobId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status && status !== "completed" && status !== "error" ? 2500 : false;
    },
  });

  const fetchGraphs = async () => {
    try {
      const res = jobId
        ? await netflixAPI.getData(profile, year, jobId)
        : await netflixAPI.getStoredDataByProfile(
            profile,
            year === ALL_YEARS_VALUE ? ALL_YEARS_VALUE : parseInt(year, 10)
          );

      const data = res.data;
      if (data.status && data.status !== "ready") {
        if (data.status === "processing" || data.status === "priority_processing") {
          return null;
        }
        if (data.status === "expired") {
          throw new Error("Your temporary recap expired. Create it again to continue.");
        }
        throw new Error(data.message || "Cached statistics are not ready yet.");
      }
      return data.data;
    } catch (err) {
      console.error(err);
      throw err;
    }
  };

  const {
    data: graphs,
    error,
    isLoading,
  } = useQuery({
    queryFn: () => fetchGraphs(),
    queryKey: ["graphs", profile, year, jobId],
    enabled: !!profile && !!year && (!!jobId || isAuthenticated),
    refetchInterval: (query) => {
      if (!profile || !year || !jobId) return false;
      if (query.state.data?._partial) return 2500;
      if (query.state.data) return false;
      return 2500;
    },
  });
  const authenticationExpired =
    !jobId &&
    [error, storedDataError].some(
      (queryError) => queryError?.message === "Authentication expired"
    );

  useEffect(() => {
    if (!isAuthenticated) return;

    sessionStorage.removeItem(SESSION_UPLOAD_KEY);
    setAnonymousUpload(null);
    queryClient.removeQueries({
      predicate: (query) =>
        query.queryKey[0] === "processingStatus" ||
        (query.queryKey[0] === "graphs" && Boolean(query.queryKey[3])),
    });

    if (jobId) {
      setSearchParams((currentParams) => {
        const nextParams = new URLSearchParams(currentParams);
        nextParams.delete("job_id");
        return nextParams;
      }, { replace: true });
    }
  }, [
    isAuthenticated,
    jobId,
    queryClient,
    setSearchParams,
  ]);

  useEffect(() => {
    if (jobId) return;

    if (!authenticationExpired) return;

    sessionStorage.removeItem(SESSION_UPLOAD_KEY);
    toast.error("Your session expired. Redirecting you to sign in again.", {
      autoClose: 5000,
      theme: "colored",
    });

    const timer = setTimeout(() => {
      navigate("/auth/login", { replace: true });
    }, 1400);

    return () => clearTimeout(timer);
  }, [authenticationExpired, navigate, jobId]);

  useEffect(() => {
    if (isAuthenticated || !jobId || !processingStatus?.profile_years) return;

    sessionStorage.setItem(
      SESSION_UPLOAD_KEY,
      JSON.stringify({
        jobId,
        profileYears: processingStatus.profile_years,
        readyProfileYears: processingStatus.ready_profile_years || {},
        expiresAt: processingStatus.expires_at || null,
      })
    );
    setAnonymousUpload({
      jobId,
      profileYears: processingStatus.profile_years,
      readyProfileYears: processingStatus.ready_profile_years || {},
      expiresAt: processingStatus.expires_at || null,
    });
  }, [isAuthenticated, jobId, processingStatus]);

  useEffect(() => {
    if (isAuthenticated || !jobId || processingStatus?.status !== "expired") return;
    sessionStorage.removeItem(SESSION_UPLOAD_KEY);
    setAnonymousUpload(null);
  }, [isAuthenticated, jobId, processingStatus]);

  const sessionProfileYears = anonymousUpload?.profileYears || {};
  const statusProfileYears = processingStatus?.profile_years || {};
  const readyProfileYears =
    processingStatus?.ready_profile_years ||
    anonymousUpload?.readyProfileYears ||
    {};
  const anonymousSessionExpired = anonymousUpload?.expiresAt
    ? new Date(anonymousUpload.expiresAt).getTime() <= Date.now()
    : false;
  const hasAnonymousSession =
    !authenticationExpired &&
    !anonymousSessionExpired &&
    Boolean(jobId || anonymousUpload?.jobId) &&
    (Object.keys(statusProfileYears).length > 0 ||
      Object.keys(sessionProfileYears).length > 0);
  const visibleData = authenticationExpired
    ? {}
    : isAuthenticated
    ? Object.keys(statusProfileYears).length > 0
      ? statusProfileYears
      : storedData
    : Object.keys(statusProfileYears).length > 0
    ? statusProfileYears
    : sessionProfileYears;
  const profileNames = visibleData ? Object.keys(visibleData).sort() : [];
  const hasCurrentSessionUpload = !isAuthenticated && profileNames.length > 0;
  const allYearsForProfile = profile ? sortYearsDesc(visibleData?.[profile]) : [];
  const readyYearsForProfile = profile
    ? sortYearsDesc(isAuthenticated ? visibleData?.[profile] : readyProfileYears?.[profile])
    : [];
  const availableYears = isAuthenticated
    ? [ALL_YEARS_VALUE, ...allYearsForProfile]
    : [ALL_YEARS_VALUE, ...sortYearsDesc(
        Array.from(new Set([...readyYearsForProfile, ...(year ? [year] : [])]))
      )];
  const selectedYearIsReady =
    year === ALL_YEARS_VALUE ||
    isAuthenticated ||
    (year && readyYearsForProfile.includes(Number(year)));
  const comparableYears = isAuthenticated ? allYearsForProfile : readyYearsForProfile;
  const anonymousExpiresAt = processingStatus?.expires_at || anonymousUpload?.expiresAt || null;
  const progressPercent = Math.max(0, Math.min(100, Number(processingStatus?.percent || 0)));
  const formattedAnonymousExpiry = anonymousExpiresAt
    ? new Date(anonymousExpiresAt).toLocaleString([], {
        month: "short",
        day: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })
    : null;

  const {
    data: yearComparison,
    error: yearComparisonError,
    isFetching: isYearComparisonLoading,
    refetch: refetchYearComparison,
  } = useQuery({
    queryFn: async () => {
      const res = await netflixAPI.compareYears({
        profileName: profile,
        yearA: compareYearA,
        yearB: compareYearB,
        jobId,
      });
      return res.data.data;
    },
    queryKey: ["compareYears", profile, compareYearA, compareYearB, jobId],
    enabled: false,
    retry: false,
  });

  const canCompareYears =
    !!profile &&
    !!compareYearA &&
    !!compareYearB &&
    compareYearA !== compareYearB &&
    comparableYears.includes(Number(compareYearA)) &&
    comparableYears.includes(Number(compareYearB));

  const selectProfile = (nextProfile) => {
    if (!nextProfile) {
      setSearchParams({});
      return;
    }

    const years = sortYearsDesc(visibleData?.[nextProfile]);
    const nextParams = { profile: nextProfile };
    if (years.length > 0) {
      nextParams.year = String(years[0]);
    }
    if (activeView !== "overview") {
      nextParams.view = activeView;
    }
    if (!isAuthenticated && anonymousUpload?.jobId) {
      nextParams.job_id = anonymousUpload.jobId;
    } else if (jobId) {
      nextParams.job_id = jobId;
    }
    setSearchParams(nextParams);
  };

  const handleYearChange = (event) => {
    const nextYear = event.target.value;

    if (!nextYear) {
      setSearchParams(profile ? { profile } : {});
      return;
    }

    const nextParams = { profile, year: nextYear };
    if (activeView !== "overview") {
      nextParams.view = activeView;
    }
    if (jobId) {
      nextParams.job_id = jobId;
    } else if (!isAuthenticated && anonymousUpload?.jobId) {
      nextParams.job_id = anonymousUpload.jobId;
    }
    setSearchParams(nextParams);
  };

  const selectView = (nextView) => {
    if (graphs?._partial && PARTIAL_PENDING_TABS.has(nextView)) return;

    const nextParams = new URLSearchParams(searchParams);
    if (nextView === "overview") {
      nextParams.delete("view");
    } else {
      nextParams.set("view", nextView);
    }
    setSearchParams(nextParams);
  };

  const canFetchSelectedStats = !!profile && !!year && (!!jobId || isAuthenticated);
  const isPartialRecap = Boolean(graphs?._partial);
  const isGeneratingSelectedStats =
    canFetchSelectedStats && !graphs && !error && (!selectedYearIsReady || isLoading);
  const showRecapSelector =
    !authLoading &&
    !authenticationExpired &&
    (isAuthenticated || hasAnonymousSession);

  return (
    <main className="min-h-screen bg-[#f4f1ec] px-4 py-8 md:px-8">
      <div
        className={`mx-auto grid max-w-7xl gap-6 ${
          showRecapSelector
            ? "lg:grid-cols-[280px_minmax(0,1fr)]"
            : "grid-cols-1"
        }`}
      >
        {showRecapSelector && (
          <aside className="h-fit rounded-lg border border-neutral-200 bg-white p-5 shadow-sm lg:sticky lg:top-6">
            <p className="text-sm font-bold uppercase tracking-wide text-red-600">
              View stats
            </p>
            <h1 className="mt-2 text-2xl font-black text-neutral-950">
              Choose a recap
            </h1>
            <p className="mt-2 text-sm leading-6 text-neutral-600">
              Pick a visible profile first. The year select updates based on saved data for that profile.
            </p>

          <div className="mt-6 space-y-4">
            <div>
              <label className="mb-2 flex items-center gap-2 text-sm font-semibold text-neutral-800">
                <UserRoundIcon className="h-4 w-4 text-red-600" />
                Profile
              </label>
              <div className="max-h-72 space-y-2 overflow-y-auto pr-1">
                {isStoredDataLoading || isProcessingStatusLoading ? (
                  <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-600">
                    Loading profiles...
                  </div>
                ) : profileNames.length > 0 ? (
                  profileNames.map((name) => {
                    const isSelected = profile === name;

                    return (
                      <button
                        key={name}
                        type="button"
                        onClick={() => selectProfile(name)}
                        disabled={!!storedDataError || !!processingStatusError}
                        className={`flex w-full items-center justify-between gap-3 cursor-pointer rounded-md border px-3 py-2.5 text-left text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
                          isSelected
                            ? "border-red-200 bg-red-50 text-red-700"
                            : "border-neutral-200 bg-white text-neutral-800 hover:border-red-200 hover:bg-red-50/50"
                        }`}
                      >
                        <span className="truncate">{name}</span>
                        {isSelected && <CheckIcon className="h-4 w-4 shrink-0" />}
                      </button>
                    );
                  })
                ) : (
                  <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3 text-sm text-neutral-600">
                    {isAuthenticated
                      ? "No saved profiles found."
                      : "No current recap found."}
                  </div>
                )}
              </div>
            </div>

            {profile && (
              <div>
                <label className="mb-2 flex items-center gap-2 text-sm font-semibold text-neutral-800">
                  <CalendarDaysIcon className="h-4 w-4 text-red-600" />
                  Year
                </label>
                <select
                  value={year || ""}
                  onChange={handleYearChange}
                  disabled={availableYears.length === 0}
                  className="w-full rounded-md border cursor-pointer border-neutral-300 bg-white p-3 text-sm font-medium text-neutral-950 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100 disabled:bg-neutral-100 disabled:text-neutral-500"
                >
                  <option value="" className="cursor-pointer">
                    {availableYears.length === 0 ? "No years found" : "Select year"}
                  </option>
                  {availableYears.map((availableYear) => (
                    <option key={availableYear} value={availableYear}>
                      {availableYear === ALL_YEARS_VALUE
                        ? "All years"
                        : !isAuthenticated &&
                      !readyYearsForProfile.includes(Number(availableYear))
                        ? `${availableYear} (preparing)`
                        : availableYear}
                    </option>
                  ))}
                </select>
              </div>
            )}

            {storedDataError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                Failed to load saved profiles.
              </div>
            )}
            {processingStatusError && (
              <div className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                Failed to refresh session processing status.
              </div>
            )}
            {!isAuthenticated && formattedAnonymousExpiry && (
              <div className="rounded-md border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-800">
                Temporary recap expires {formattedAnonymousExpiry}.
              </div>
            )}
            {!isAuthenticated && jobId && processingStatus && processingStatus.status !== "completed" && (
              <div className="rounded-md border border-neutral-200 bg-neutral-50 p-3">
                <div className="flex items-center justify-between text-xs font-semibold text-neutral-700">
                  <span>Preparing your recap</span>
                  <span>{progressPercent}%</span>
                </div>
                <div className="mt-2 h-2 overflow-hidden rounded-full bg-neutral-200">
                  <div
                    className="h-full rounded-full bg-red-600 transition-all"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>
            )}
          </div>
          </aside>
        )}

        <section className="min-w-0">
          {isLoading && !graphs ? (
            <div className="rounded-lg border border-neutral-200 bg-white p-6 text-neutral-600">
              Loading results...
            </div>
          ) : error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
              {jobId
                ? error.message || "Failed to load cached insights. The temporary session may have expired."
                : "Failed to load insights."}
            </div>
          ) : !profile ? (
            <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
              <p className="text-sm font-bold uppercase tracking-wide text-red-600">
                {isAuthenticated ? "Saved results" : "Recap results"}
              </p>
              <h2 className="mt-2 text-2xl font-black text-neutral-950 sm:text-3xl">
                {profileNames.length > 0
                  ? "Select a profile to start."
                  : isAuthenticated
                  ? "No saved recaps yet."
                  : "No current recap yet."}
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
                {profileNames.length > 0
                  ? "Your available profiles appear on the left."
                  : isAuthenticated
                  ? "Create a recap to save profile and year results to your account."
                  : "Create a one-time recap in this browser, or make an account when you want to keep your results."}
              </p>
              {!hasCurrentSessionUpload && profileNames.length === 0 && (
                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => navigate("/create")}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-red-700"
                  >
                    <UploadIcon className="h-4 w-4" />
                    Create recap
                  </button>
                  {!isAuthenticated && (
                    <button
                      type="button"
                      onClick={() => navigate("/auth/create")}
                      className="inline-flex items-center justify-center gap-2 rounded-md border border-neutral-300 bg-white px-4 py-3 text-sm font-bold text-neutral-900 transition hover:border-red-300 hover:text-red-700"
                    >
                      <LogInIcon className="h-4 w-4" />
                      Create account
                    </button>
                  )}
                </div>
              )}
            </div>
          ) : !year ? (
            <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
              <p className="text-sm font-bold uppercase tracking-wide text-red-600">
                {profile}
              </p>
              <h2 className="mt-2 text-2xl font-black text-neutral-950 sm:text-3xl">
                Choose a year.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
                These are the years found in this profile’s viewing history.
              </p>
            </div>
          ) : !canFetchSelectedStats ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-8 shadow-sm">
              <p className="text-sm font-bold uppercase tracking-wide text-amber-700">
                Recap unavailable
              </p>
              <h2 className="mt-2 text-2xl font-black text-neutral-950 sm:text-3xl">
                Create the recap again or log in.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-700">
                One-time recaps expire after a limited period. Start again to recreate it, or log in to access results saved to your account.
              </p>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => navigate("/create")}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-red-700"
                >
                  <UploadIcon className="h-4 w-4" />
                  Create recap
                </button>
                <button
                  type="button"
                  onClick={() => navigate("/auth/login")}
                  className="inline-flex items-center justify-center gap-2 rounded-md border border-neutral-300 bg-white px-4 py-3 text-sm font-bold text-neutral-900 transition hover:border-red-300 hover:text-red-700"
                >
                  <LogInIcon className="h-4 w-4" />
                  Log back in
                </button>
              </div>
            </div>
          ) : isGeneratingSelectedStats ? (
            <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
              <p className="text-sm font-bold uppercase tracking-wide text-red-600">
                Generating insights
              </p>
              <h2 className="mt-2 text-2xl font-black text-neutral-950 sm:text-3xl">
                Preparing {profile} ({year === ALL_YEARS_VALUE ? "All years" : year})
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
                The selected year is being prepared first. More years will appear as their results become ready.
              </p>
              <div className="mt-5 flex items-center gap-3 text-sm font-semibold text-neutral-700">
                <span className="h-3 w-3 animate-pulse rounded-full bg-red-600" />
                Processing profile data...
              </div>
            </div>
          ) : !graphs ? (
            <div className="rounded-lg border border-neutral-200 bg-white p-6 text-neutral-600">
              Insights are not ready for this profile and year yet.
            </div>
          ) : (
            <div className="flex flex-col gap-8">
              <div>
                <p className="text-sm font-bold uppercase text-red-600">
                  Netflix Wrapped
                </p>
                <h2 className="mt-2 break-words text-2xl font-black tracking-normal text-neutral-950 sm:text-3xl">
                  {profile}{" "}
                  <span className="text-red-600">
                    ({year === ALL_YEARS_VALUE ? "All years" : year})
                  </span>
                </h2>
              </div>

              <nav
                aria-label="Statistics sections"
                className="overflow-x-auto rounded-lg border border-neutral-200 bg-white p-1.5 shadow-sm"
              >
                <div className="flex min-w-max gap-1">
                  {STAT_TABS.map(({ value, label, icon: Icon }) => {
                    const isSelected = activeView === value;
                    const isFinishing = isPartialRecap && PARTIAL_PENDING_TABS.has(value);
                    return (
                      <button
                        key={value}
                        type="button"
                        disabled={isFinishing}
                        onClick={() => selectView(value)}
                        aria-current={isSelected ? "page" : undefined}
                        className={`inline-flex min-h-11 cursor-pointer items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-black transition disabled:cursor-not-allowed disabled:opacity-55 sm:px-4 ${
                          isSelected
                            ? "bg-red-600 text-white"
                            : isFinishing
                            ? "text-neutral-400"
                            : "text-neutral-700 hover:bg-red-50 hover:text-red-700"
                        }`}
                      >
                        <Icon className="size-4 shrink-0" />
                        <span>{label}</span>
                        {isFinishing && (
                          <span className="rounded-full bg-neutral-100 px-2 py-0.5 text-[10px] uppercase text-neutral-500">
                            Finishing
                          </span>
                        )}
                      </button>
                    );
                  })}
                </div>
              </nav>

              {isPartialRecap && PARTIAL_PENDING_TABS.has(activeView) && (
                <section className="rounded-lg border border-amber-200 bg-amber-50 p-6 shadow-sm">
                  <p className="text-sm font-bold uppercase text-amber-700">
                    Finishing this section
                  </p>
                  <h3 className="mt-2 text-2xl font-black text-neutral-950">
                    The first recap is ready. This tab is still being filled in.
                  </h3>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-700">
                    Overview and title insights are available now. Profile comparisons,
                    content insights, and visualizations will appear automatically after
                    the worker completes the full recap.
                  </p>
                </section>
              )}

              {activeView === "overview" && (
                <>
                  <CoreStatsGrid stats={graphs.core_stats} />
                  <WrappedCards cards={graphs.wrapped_cards} profile={profile} year={year} />
                </>
              )}
              {!isPartialRecap && activeView === "compare" && (
                comparableYears.length >= 2 ? (
                <section className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
                  <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                      <p className="text-sm font-bold uppercase text-red-600">
                        Compare years
                      </p>
                      <h3 className="mt-1 text-xl font-black text-neutral-950">
                        Year-over-year recap
                      </h3>
                    </div>
                    <div className="grid w-full gap-3 sm:grid-cols-2 lg:w-auto lg:grid-cols-[1fr_1fr_auto]">
                      <select
                        value={compareYearA}
                        onChange={(event) => setCompareYearA(event.target.value)}
                        className="rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-semibold"
                      >
                        <option value="">Base year</option>
                        {comparableYears.map((availableYear) => (
                          <option key={availableYear} value={availableYear}>
                            {availableYear}
                          </option>
                        ))}
                      </select>
                      <select
                        value={compareYearB}
                        onChange={(event) => setCompareYearB(event.target.value)}
                        className="rounded-md border border-neutral-300 bg-white px-3 py-2 text-sm font-semibold"
                      >
                        <option value="">Compare year</option>
                        {comparableYears.map((availableYear) => (
                          <option key={availableYear} value={availableYear}>
                            {availableYear}
                          </option>
                        ))}
                      </select>
                      <button
                        type="button"
                        disabled={!canCompareYears || isYearComparisonLoading}
                        onClick={() => refetchYearComparison()}
                        className="rounded-md bg-neutral-950 px-4 py-2 text-sm font-bold text-white transition hover:bg-neutral-800 disabled:cursor-not-allowed disabled:opacity-50 sm:col-span-2 lg:col-span-1"
                      >
                        {isYearComparisonLoading ? "Comparing..." : "Compare"}
                      </button>
                    </div>
                  </div>
                  {yearComparisonError && (
                    <div className="mt-4 rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-700">
                      Could not compare those years.
                    </div>
                  )}
                  {yearComparison && (
                    <div className="mt-5 grid gap-3 md:grid-cols-3">
                      {[
                        ["Watch time", "total_watchtime_hours", "hrs"],
                        ["Viewing events", "total_viewing_events", ""],
                        ["Unique titles", "unique_titles", ""],
                      ].map(([label, key, suffix]) => {
                        const delta = yearComparison.deltas?.[key] || 0;
                        return (
                          <div key={key} className="rounded-md border border-neutral-200 bg-neutral-50 p-4">
                            <p className="text-xs font-bold uppercase text-neutral-500">{label}</p>
                            <p className={`mt-2 text-2xl font-black ${delta >= 0 ? "text-emerald-700" : "text-red-700"}`}>
                              {delta >= 0 ? "+" : ""}
                              {delta}
                              {suffix ? ` ${suffix}` : ""}
                            </p>
                            <p className="mt-1 text-xs text-neutral-500">
                              {yearComparison.year_b} vs {yearComparison.year_a}
                            </p>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </section>
                ) : (
                  <section className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
                    <p className="text-sm font-bold uppercase text-red-600">
                      Compare years
                    </p>
                    <h3 className="mt-2 text-2xl font-black text-neutral-950">
                      Two completed years are required
                    </h3>
                    <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
                      This profile needs viewing history from at least two completed years before a year-over-year comparison can be shown.
                    </p>
                  </section>
                )
              )}
              {activeView === "titles" && (
                <TitleLevelInsights insights={graphs.title_level_insights} />
              )}
              {!isPartialRecap && activeView === "content" && (
                <GenreContentInsights insights={graphs.genre_content_insights} />
              )}
              {!isPartialRecap && activeView === "profiles" && (
                <ProfileComparisons comparisons={graphs.profile_comparisons} />
              )}
              {!isPartialRecap && activeView === "visualizations" && (
                <VisualizationBoard graphs={graphs} />
              )}
              {activeView === "for-you" && (
                <ProfileRecommendations
                  profile={profile}
                  isAuthenticated={isAuthenticated}
                />
              )}
            </div>
          )}
        </section>
      </div>
      <ToastContainer />
    </main>
  );
}
