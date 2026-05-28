import { useEffect, useMemo } from "react";
import { useSelector } from "react-redux";
import { useNavigate, useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import VizCarousel from "@/components/VizCarousel";
import { netflixAPI } from "@/services/api";
import CoreStatsGrid from "@/components/CoreStatsGrid";
import GenreContentInsights from "@/components/GenreContentInsights";
import ProfileComparisons from "@/components/ProfileComparisons";
import { selectAuth } from "@/store/authSlice";
import {
  CalendarDaysIcon,
  CheckIcon,
  LogInIcon,
  UploadIcon,
  UserRoundIcon,
} from "lucide-react";
import { toast, ToastContainer } from "react-toastify";

const SESSION_UPLOAD_KEY = "netflixWrapped:lastAnonymousUpload";
const ALL_YEARS_VALUE = "all";

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
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated, loading: authLoading } = useSelector(selectAuth);
  const profile = searchParams.get("profile") || null;
  const year = searchParams.get("year") || null;
  const jobId = searchParams.get("job_id") || null;
  const anonymousUpload = useMemo(() => {
    try {
      const rawUpload = sessionStorage.getItem(SESSION_UPLOAD_KEY);
      return rawUpload ? JSON.parse(rawUpload) : null;
    } catch {
      return null;
    }
  }, []);

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
    enabled: !!jobId && !isAuthenticated,
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
      if (!profile || !year || !jobId || query.state.data) return false;
      return 2500;
    },
  });

  useEffect(() => {
    if (jobId) return;

    const authError = [error, storedDataError].find(
      (queryError) => queryError?.message === "Authentication expired"
    );

    if (!authError) return;

    toast.error("Your session expired. Redirecting you to sign in again.", {
      autoClose: 5000,
      theme: "colored",
    });

    const timer = setTimeout(() => {
      navigate("/auth/login", { replace: true });
    }, 1400);

    return () => clearTimeout(timer);
  }, [error, storedDataError, navigate, jobId]);

  useEffect(() => {
    if (!jobId || !processingStatus?.profile_years) return;

    sessionStorage.setItem(
      SESSION_UPLOAD_KEY,
      JSON.stringify({
        jobId,
        profileYears: processingStatus.profile_years,
        readyProfileYears: processingStatus.ready_profile_years || {},
      })
    );
  }, [jobId, processingStatus]);

  const sessionProfileYears = anonymousUpload?.profileYears || {};
  const statusProfileYears = processingStatus?.profile_years || {};
  const readyProfileYears = processingStatus?.ready_profile_years || {};
  const visibleData = isAuthenticated
    ? storedData
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
    if (jobId) {
      nextParams.job_id = jobId;
    } else if (!isAuthenticated && anonymousUpload?.jobId) {
      nextParams.job_id = anonymousUpload.jobId;
    }
    setSearchParams(nextParams);
  };

  const canFetchSelectedStats = !!profile && !!year && (!!jobId || isAuthenticated);
  const isGeneratingSelectedStats =
    canFetchSelectedStats && !graphs && !error && (!selectedYearIsReady || isLoading);

  return (
    <main className="min-h-screen bg-[#f4f1ec] px-4 py-8 md:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 lg:grid-cols-[280px_minmax(0,1fr)]">
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
                        className={`flex w-full items-center justify-between gap-3 rounded-md border px-3 py-2.5 text-left text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
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
                      : "No current upload found."}
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
                  className="w-full rounded-md border border-neutral-300 bg-white p-3 text-sm font-medium text-neutral-950 outline-none transition focus:border-red-500 focus:ring-2 focus:ring-red-100 disabled:bg-neutral-100 disabled:text-neutral-500"
                >
                  <option value="">
                    {availableYears.length === 0 ? "No years found" : "Select year"}
                  </option>
                  {availableYears.map((availableYear) => (
                    <option key={availableYear} value={availableYear}>
                      {availableYear === ALL_YEARS_VALUE
                        ? "All years"
                        : !isAuthenticated &&
                      !readyYearsForProfile.includes(Number(availableYear))
                        ? `${availableYear} (generating)`
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
          </div>
        </aside>

        <section className="min-w-0">
          {isLoading && !graphs ? (
            <div className="rounded-lg border border-neutral-200 bg-white p-6 text-neutral-600">
              Loading insights...
            </div>
          ) : error ? (
            <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-red-700">
              {jobId
                ? "Failed to load cached insights. The temporary session may have expired."
                : "Failed to load insights."}
            </div>
          ) : !profile ? (
            <div className="rounded-lg border border-neutral-200 bg-white p-8 shadow-sm">
              <p className="text-sm font-bold uppercase tracking-wide text-red-600">
                {isAuthenticated ? "Saved statistics" : "Session statistics"}
              </p>
              <h2 className="mt-2 text-3xl font-black text-neutral-950">
                {profileNames.length > 0
                  ? "Select a profile to start."
                  : isAuthenticated
                  ? "No saved statistics yet."
                  : "No current upload yet."}
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
                {profileNames.length > 0
                  ? "Your available profiles appear on the left."
                  : isAuthenticated
                  ? "Upload a Netflix viewing history CSV to save profiles and generate reusable statistics."
                  : "Upload a Netflix viewing history CSV to generate temporary statistics for this browser session. Create an account if you want to save them."}
              </p>
              {!hasCurrentSessionUpload && profileNames.length === 0 && (
                <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                  <button
                    type="button"
                    onClick={() => navigate("/upload")}
                    className="inline-flex items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-red-700"
                  >
                    <UploadIcon className="h-4 w-4" />
                    Generate stats
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
              <h2 className="mt-2 text-3xl font-black text-neutral-950">
                Choose a year.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
                The available years are based on the uploaded viewing history for this profile.
              </p>
            </div>
          ) : !canFetchSelectedStats ? (
            <div className="rounded-lg border border-amber-200 bg-amber-50 p-8 shadow-sm">
              <p className="text-sm font-bold uppercase tracking-wide text-amber-700">
                Session data unavailable
              </p>
              <h2 className="mt-2 text-3xl font-black text-neutral-950">
                Upload again or log in.
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-700">
                Anonymous statistics are loaded from a temporary cache. If the cache key is missing or expired, upload the CSV again. Saved statistics require signing in.
              </p>
              <div className="mt-5 flex flex-col gap-3 sm:flex-row">
                <button
                  type="button"
                  onClick={() => navigate("/upload")}
                  className="inline-flex items-center justify-center gap-2 rounded-md bg-red-600 px-4 py-3 text-sm font-bold text-white transition hover:bg-red-700"
                >
                  <UploadIcon className="h-4 w-4" />
                  Upload CSV
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
              <h2 className="mt-2 text-3xl font-black text-neutral-950">
                Preparing {profile} ({year === ALL_YEARS_VALUE ? "All years" : year})
              </h2>
              <p className="mt-3 max-w-2xl text-sm leading-6 text-neutral-600">
                The latest selected year is being generated first. More years will appear in the selector as they finish processing.
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
                <h2 className="mt-2 text-3xl font-black tracking-normal text-neutral-950">
                  {profile}{" "}
                  <span className="text-red-600">
                    ({year === ALL_YEARS_VALUE ? "All years" : year})
                  </span>
                </h2>
              </div>
              <CoreStatsGrid stats={graphs.core_stats} />
              <GenreContentInsights insights={graphs.genre_content_insights} />
              <ProfileComparisons comparisons={graphs.profile_comparisons} />
              <VizCarousel graphs={graphs} profile={profile} year={year} />
            </div>
          )}
        </section>
      </div>
      <ToastContainer />
    </main>
  );
}
