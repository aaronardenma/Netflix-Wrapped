import { useMemo, useRef, useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Dropzone,
  DropZoneArea,
  DropzoneFileList,
  DropzoneFileListItem,
  DropzoneRemoveFile,
  DropzoneTrigger,
  useDropzone,
} from "./ui/dropzone";
import {
  ArrowRightIcon,
  CloudUploadIcon,
  DatabaseIcon,
  ExternalLinkIcon,
  FileSpreadsheetIcon,
  Loader2Icon,
  ShieldCheckIcon,
  SparklesIcon,
  Trash2Icon,
} from "lucide-react";
import { toast, ToastContainer } from "react-toastify";
import { netflixAPI } from "@/services/api/";
import { selectAuth } from "@/store/authSlice";

const workflowSteps = [
  {
    title: "Request your history",
    description: "Ask Netflix for a copy of your account and viewing history.",
  },
  {
    title: "Bring it into your recap",
    description: "Choose the viewing history file Netflix sends you.",
  },
  {
    title: "Explore your results",
    description: "Pick a profile and year to see your personalized recap.",
  },
];

const supportItems = [
  {
    icon: ShieldCheckIcon,
    title: "Private by default",
    description: "Use the app without an account for a temporary session.",
  },
  {
    icon: DatabaseIcon,
    title: "Saved when signed in",
    description: "Your history is saved so you can revisit and compare recaps.",
  },
  {
    icon: FileSpreadsheetIcon,
    title: "Netflix viewing history",
    description: "Choose the ViewingActivity file included in your Netflix data.",
  },
];

const SESSION_UPLOAD_KEY = "netflixWrapped:lastAnonymousUpload";

const formatDuration = (startTime) => {
  const elapsedMs = performance.now() - startTime;
  return `${(elapsedMs / 1000).toFixed(2)}s (${Math.round(elapsedMs)}ms)`;
};

export default function FileUpload() {
  const { isAuthenticated } = useSelector(selectAuth);
  const [userYearsMap, setUserYearsMap] = useState({});
  const [backgroundProcessing, setBackgroundProcessing] = useState(false);
  const [processingError, setProcessingError] = useState(false);
  const [processingStatus, setProcessingStatus] = useState("");
  const uploadStartTimeRef = useRef(null);
  const pendingFilesRef = useRef([]);
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { data: storedData } = useQuery({
    queryKey: ["storedData"],
    queryFn: async () => {
      const response = await netflixAPI.getStoredData();
      return response.data;
    },
    enabled: isAuthenticated,
  });

  const historySummary = useMemo(
    () =>
      Object.keys(userYearsMap).length > 0
        ? userYearsMap
        : isAuthenticated
          ? storedData || {}
          : {},
    [isAuthenticated, storedData, userYearsMap],
  );
  const profileCount = Object.keys(historySummary).length;
  const yearCount = useMemo(() => {
    const uniqueYears = new Set(Object.values(historySummary).flat());
    return uniqueYears.size;
  }, [historySummary]);

  const dropzone = useDropzone({
    onDropFile: async (file) => {
      setBackgroundProcessing(true);
      setProcessingError(false);
      setProcessingStatus(
        isAuthenticated
          ? "Saving your viewing history and preparing your recap..."
          : "Reading your viewing history and preparing your recap..."
      );
      pendingFilesRef.current.push(file.file || file);
      return {
        status: "success",
        result: file.name,
      };
    },
    onAllUploaded: async () => {
      const files = pendingFilesRef.current;
      pendingFilesRef.current = [];
      if (files.length > 0) {
        await extractUserYearMap(files);
      }
    },
    validation: {
      accept: { "text/csv": [".csv"] },
      maxSize: 5 * 1024 * 1024,
      maxFiles: 5,
    },
  });

  const extractUserYearMap = async (files) => {
    try {
      const uploadFiles = Array.isArray(files) ? files : [files];
      uploadStartTimeRef.current = performance.now();
      console.info(`[CSV processing] Started processing ${uploadFiles.length} file(s)`);
      setBackgroundProcessing(true);
      setProcessingError(false);
      setProcessingStatus(
        isAuthenticated
          ? "Saving your viewing history and finding profiles and years..."
          : "Finding profiles and years in your viewing history..."
      );

      const res = await netflixAPI.quickExtractCSV(uploadFiles);

      const response = res.data;

      setUserYearsMap(response.profile_years || {});

      if (isAuthenticated) {
        sessionStorage.removeItem(SESSION_UPLOAD_KEY);
        await queryClient.invalidateQueries({ queryKey: ["storedData"] });
      } else {
        sessionStorage.setItem(
          SESSION_UPLOAD_KEY,
          JSON.stringify({
            jobId: response.job_id,
            profileYears: response.profile_years,
            readyProfileYears: response.ready_profile_years || {},
            expiresAt: response.expires_at || null,
          })
        );
      }

      const mergeStats = response.merge_stats;
      setProcessingStatus(
        response.status === "completed"
          ? `Your recap is ready. ${mergeStats?.duplicates_skipped || 0} duplicate rows were ignored.`
          : `Your recap is being prepared. ${mergeStats?.duplicates_skipped || 0} duplicate rows were ignored.`
      );

      if (response.status === "completed") {
        setBackgroundProcessing(false);
        console.info(
          `[CSV processing] Completed full CSV processing in ${formatDuration(uploadStartTimeRef.current)}`
        );
      } else {
        console.info(
          `[CSV processing] Initial CSV upload/extraction completed in ${formatDuration(uploadStartTimeRef.current)}. Background processing is still running.`
        );
      }

      toast.success(
        "Your history is ready. Choose a profile and year to view your recap.",
        {
          autoClose: 5000,
          theme: "colored",
        }
      );

      const params = new URLSearchParams();
      if (!isAuthenticated) {
        params.set("job_id", response.job_id);
      }
      navigate(`/recap${params.toString() ? `?${params.toString()}` : ""}`);
    } catch (err) {
      console.error("Extract error:", err);
      toast.error(`Failed to extract data: ${err.message}`, {
        autoClose: 10000,
        theme: "colored",
      });
      setBackgroundProcessing(false);
      setProcessingError(true);
      setProcessingStatus(
        "We could not prepare this recap. Check the file and try again."
      );
    }
  };

  return (
    <main className="min-h-screen bg-[#f4f1ec] px-4 py-10 text-gray-950 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        <section className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-end">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-red-200 bg-white/80 px-3 py-1 text-sm font-semibold text-red-700 shadow-sm">
              <SparklesIcon className="h-4 w-4" />
              Create your Netflix Wrapped
            </div>
            <div className="max-w-3xl space-y-4">
              <h1 className="text-4xl font-bold leading-tight text-gray-950 sm:text-5xl">
                See what your Netflix history says about you.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-gray-700 sm:text-lg">
                Request your viewing history from Netflix, bring it here, and explore a personalized recap for every profile and year.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <a
                href="https://www.netflix.com/account/getmyinfo"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-gray-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-gray-800"
              >
                Request my history
                <ExternalLinkIcon className="h-4 w-4" />
              </a>
              <a
                href="#upload-panel"
                className="inline-flex items-center justify-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 transition hover:border-red-300 hover:text-red-700"
              >
                Start my recap
                <ArrowRightIcon className="h-4 w-4" />
              </a>
            </div>
          </div>

          <div className="grid gap-3 rounded-lg border border-gray-200 bg-white/80 p-4 shadow-sm">
            {workflowSteps.map((step, index) => (
              <div key={step.title} className="flex gap-4">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-red-600 text-sm font-bold text-white">
                  {index + 1}
                </div>
                <div>
                  <h2 className="text-sm font-bold text-gray-950">{step.title}</h2>
                  <p className="mt-1 text-sm leading-6 text-gray-600">{step.description}</p>
                </div>
              </div>
            ))}
          </div>
        </section>

        <section className="grid gap-6 lg:grid-cols-[minmax(0,1.25fr)_minmax(320px,0.75fr)]">
          <div
            id="upload-panel"
            className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm sm:p-6 lg:p-8"
          >
            <div className="flex flex-col gap-4 pb-6 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-red-700">
                  Create recap
                </p>
                <h2 className="mt-2 text-2xl font-bold text-gray-950">
                  Add your Netflix history
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                  We’ll find the profiles and years in your history, then let you choose the recap you want to explore.
                </p>
              </div>
              <div className="inline-flex w-fit items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-semibold text-gray-700">
                {isAuthenticated ? (
                  <>
                    <DatabaseIcon className="size-5 shrink-0 stroke-[2.25] text-red-600" />
                    Saving enabled
                  </>
                ) : (
                  <>
                    <ShieldCheckIcon className="size-5 shrink-0 stroke-[2.25] text-red-600" />
                    Temporary session
                  </>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <Dropzone {...dropzone}>
                <div>
                  <DropZoneArea
                    aria-busy={backgroundProcessing}
                    className={backgroundProcessing ? "pointer-events-none" : ""}
                  >
                    <DropzoneTrigger
                      aria-disabled={backgroundProcessing}
                      className={`flex min-h-64 w-full flex-col items-center justify-center gap-5 rounded-lg border-2 border-dashed p-8 text-center text-sm transition ${
                        backgroundProcessing
                          ? "cursor-wait border-red-300 bg-red-50/50"
                          : "border-gray-300 bg-[#faf8f5] hover:border-red-300 hover:bg-red-50/40"
                      }`}
                    >
                      {backgroundProcessing ? (
                        <>
                          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-sm">
                            <Loader2Icon className="h-8 w-8 animate-spin text-red-600" />
                          </span>
                          <div role="status" aria-live="polite">
                            <p className="text-lg font-bold text-gray-950">
                              Preparing your recap
                            </p>
                            <p className="mt-2 max-w-md text-sm leading-6 text-gray-600">
                              {processingStatus}
                            </p>
                          </div>
                          <div className="h-1.5 w-full max-w-sm overflow-hidden rounded-full bg-red-100">
                            <div className="h-full w-1/2 animate-pulse rounded-full bg-red-600" />
                          </div>
                          <p className="text-xs font-semibold text-gray-500">
                            Results will open automatically when this step is complete.
                          </p>
                        </>
                      ) : processingError ? (
                        <>
                          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-red-100 text-2xl font-black text-red-700">
                            !
                          </span>
                          <div role="alert" aria-live="assertive">
                            <p className="text-lg font-bold text-gray-950">
                              Recap could not be prepared
                            </p>
                            <p className="mt-2 max-w-md text-sm leading-6 text-red-700">
                              {processingStatus}
                            </p>
                          </div>
                          <p className="text-xs font-semibold text-gray-500">
                            Click here or drop another file to try again.
                          </p>
                        </>
                      ) : (
                        <>
                          <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-sm">
                            <CloudUploadIcon className="h-8 w-8 text-red-600" />
                          </span>
                          <div>
                            <p className="text-lg font-bold text-gray-950">
                              Drop your Netflix viewing history here
                            </p>
                            <p className="mt-2 text-sm text-gray-600">
                              Or click to choose it. Look for ViewingActivity in the files Netflix sent you.
                            </p>
                          </div>
                        </>
                      )}
                    </DropzoneTrigger>
                  </DropZoneArea>
                </div>
                {dropzone.fileStatuses.length > 0 && (
                  <DropzoneFileList className="mt-4">
                    {dropzone.fileStatuses.map((file) => (
                      <DropzoneFileListItem
                        key={file.id}
                        file={file}
                        className="mb-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-3"
                      >
                        <div className="flex items-center justify-between gap-4">
                          <div className="flex min-w-0 items-center gap-3">
                            <FileSpreadsheetIcon className="h-5 w-5 shrink-0 text-red-600" />
                            <div className="min-w-0">
                              <p className="truncate text-sm font-semibold text-gray-800">
                                {file.fileName}
                              </p>
                              <p className="text-xs text-gray-500">
                                {(file.file.size / (1024 * 1024)).toFixed(2)} MB
                              </p>
                            </div>
                          </div>
                          <DropzoneRemoveFile
                            aria-disabled={backgroundProcessing}
                            disabled={backgroundProcessing}
                            className="rounded-md bg-white p-2"
                          >
                            <Trash2Icon className="h-4 w-4 text-red-500 transition hover:text-red-700" />
                          </DropzoneRemoveFile>
                        </div>
                      </DropzoneFileListItem>
                    ))}
                  </DropzoneFileList>
                )}
              </Dropzone>

              <div className="rounded-md border border-gray-200 bg-gray-50 p-4 text-sm leading-6 text-gray-600">
                When your history is ready, Results opens automatically so you can choose a profile and year.
              </div>
            </div>
          </div>

          <aside className="space-y-6">
            {isAuthenticated && (
              <div className="rounded-lg border border-gray-200 bg-gray-950 p-5 text-white shadow-sm sm:p-6">
                <p className="text-sm font-semibold text-red-300">Found in your history</p>
                <div className="mt-5 grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-3xl font-bold">{profileCount}</p>
                    <p className="mt-1 text-sm text-gray-300">Profiles</p>
                  </div>
                  <div>
                    <p className="text-3xl font-bold">{yearCount}</p>
                    <p className="mt-1 text-sm text-gray-300">Years</p>
                  </div>
                </div>
                <p className="mt-5 text-sm leading-6 text-gray-300">
                  Choose a profile and year in Results as soon as your recap is ready.
                </p>
              </div>
            )}

            <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm sm:p-6">
              <h2 className="text-lg font-bold text-gray-950">What this page does</h2>
              <div className="mt-5 space-y-5">
                {supportItems.map((item) => {
                  const Icon = item.icon;
                  return (
                    <div key={item.title} className="flex gap-3">
                      <Icon className="mt-0.5 h-5 w-5 shrink-0 text-red-600" />
                      <div>
                        <p className="text-sm font-bold text-gray-900">{item.title}</p>
                        <p className="mt-1 text-sm leading-6 text-gray-600">
                          {item.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </aside>
        </section>
      </div>
      <ToastContainer />
    </main>
  );
}
