import { useMemo, useRef, useState } from "react";
import { useSelector } from "react-redux";
import { useNavigate } from "react-router-dom";
import {
  Dropzone,
  DropZoneArea,
  DropzoneDescription,
  DropzoneFileList,
  DropzoneFileListItem,
  DropzoneMessage,
  DropzoneRemoveFile,
  DropzoneTrigger,
  useDropzone,
} from "./ui/dropzone";
import {
  ArrowRightIcon,
  CheckCircle2Icon,
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
    title: "Request your file",
    description: "Open Netflix account data and request the viewing history CSV.",
  },
  {
    title: "Upload the CSV",
    description: "Drop the file here so the app can read profiles and years.",
  },
  {
    title: "Generate insights",
    description: "Go to Statistics, pick a profile, and the latest year starts first.",
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
    description: "Authenticated uploads are stored for faster profile comparisons.",
  },
  {
    icon: FileSpreadsheetIcon,
    title: "Netflix CSV only",
    description: "Upload the ViewingActivity.csv file from Netflix.",
  },
];

const SESSION_UPLOAD_KEY = "netflixWrapped:lastAnonymousUpload";

const formatDuration = (startTime) => {
  const elapsedMs = performance.now() - startTime;
  return `${(elapsedMs / 1000).toFixed(2)}s (${Math.round(elapsedMs)}ms)`;
};

export default function FileUpload() {
  const { isAuthenticated } = useSelector(selectAuth);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [userYearsMap, setUserYearsMap] = useState({});
  const [backgroundProcessing, setBackgroundProcessing] = useState(false);
  const [processingStatus, setProcessingStatus] = useState("");
  const uploadStartTimeRef = useRef(null);
  const navigate = useNavigate();

  const profileCount = availableUsers.length;
  const yearCount = useMemo(() => {
    const uniqueYears = new Set(Object.values(userYearsMap).flat());
    return uniqueYears.size;
  }, [userYearsMap]);

  const dropzone = useDropzone({
    onDropFile: async (file) => {
      await extractUserYearMap(file);
      return {
        status: "success",
        result: file.name,
      };
    },
    validation: {
      accept: { "text/csv": [".csv"] },
      maxSize: 5 * 1024 * 1024,
      maxFiles: 1,
    },
  });

  const extractUserYearMap = async (file) => {
    try {
      uploadStartTimeRef.current = performance.now();
      console.info(`[CSV processing] Started processing ${file.name}`);
      setBackgroundProcessing(true);

      const res = await netflixAPI.quickExtractCSV(file);

      const response = res.data;

      setUserYearsMap(response.profile_years);
      setAvailableUsers(Object.keys(response.profile_years).sort());

      sessionStorage.setItem(
        SESSION_UPLOAD_KEY,
        JSON.stringify({
          jobId: response.job_id,
          profileYears: response.profile_years,
          readyProfileYears: response.ready_profile_years || {},
        })
      );

      setProcessingStatus(
        response.status === "completed"
          ? "Upload processed and ready."
          : "Processing all combinations in background..."
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
        "CSV uploaded. Choose a profile on the Statistics page to generate insights.",
        {
          autoClose: 5000,
          theme: "colored",
        }
      );

      const params = new URLSearchParams();
      if (!isAuthenticated) {
        params.set("job_id", response.job_id);
      }
      navigate(`/statistics${params.toString() ? `?${params.toString()}` : ""}`);
    } catch (err) {
      console.error("Extract error:", err);
      toast.error(`Failed to extract data: ${err.message}`, {
        autoClose: 10000,
        theme: "colored",
      });
      setBackgroundProcessing(false);
    }
  };

  return (
    <main className="min-h-screen bg-[#f4f1ec] px-4 py-10 text-gray-950 sm:px-6 lg:px-8">
      <div className="mx-auto flex max-w-7xl flex-col gap-8">
        <section className="grid gap-8 lg:grid-cols-[1.05fr_0.95fr] lg:items-end">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 rounded-full border border-red-200 bg-white/80 px-3 py-1 text-sm font-semibold text-red-700 shadow-sm">
              <SparklesIcon className="h-4 w-4" />
              Netflix Wrapped upload workflow
            </div>
            <div className="max-w-3xl space-y-4">
              <h1 className="text-4xl font-bold leading-tight text-gray-950 sm:text-5xl">
                Turn Netflix viewing history into profile-level insights.
              </h1>
              <p className="max-w-2xl text-base leading-7 text-gray-700 sm:text-lg">
                Start by downloading your Netflix account data, then upload the viewing activity CSV here. You can save uploads with an account or generate insights for a one-time session.
              </p>
            </div>
            <div className="flex flex-col gap-3 sm:flex-row">
              <a
                href="https://www.netflix.com/account/getmyinfo"
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center justify-center gap-2 rounded-md bg-gray-950 px-4 py-3 text-sm font-semibold text-white transition hover:bg-gray-800"
              >
                Get Netflix data
                <ExternalLinkIcon className="h-4 w-4" />
              </a>
              <a
                href="#upload-panel"
                className="inline-flex items-center justify-center gap-2 rounded-md border border-gray-300 bg-white px-4 py-3 text-sm font-semibold text-gray-900 transition hover:border-red-300 hover:text-red-700"
              >
                Upload CSV
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
            <div className="mb-6 flex flex-col gap-4 border-b border-gray-200 pb-6 sm:flex-row sm:items-start sm:justify-between">
              <div>
                <p className="text-sm font-semibold uppercase tracking-wide text-red-700">
                  Upload
                </p>
                <h2 className="mt-2 text-2xl font-bold text-gray-950">
                  Add your viewing activity file
                </h2>
                <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-600">
                  The app reads profile names and available years first, then lets you pick the exact recap to generate.
                </p>
              </div>
              <div className="inline-flex w-fit items-center gap-2 rounded-full border border-gray-200 bg-gray-50 px-3 py-1.5 text-xs font-semibold text-gray-700">
                {isAuthenticated ? (
                  <>
                    <DatabaseIcon className="h-4 w-4 text-red-600" />
                    Saving enabled
                  </>
                ) : (
                  <>
                    <ShieldCheckIcon className="h-4 w-4 text-red-600" />
                    Temporary session
                  </>
                )}
              </div>
            </div>

            <div className="space-y-6">
              <Dropzone {...dropzone}>
                <div>
                  <div className="mb-3 flex flex-col gap-2 text-sm text-gray-600 sm:flex-row sm:items-center sm:justify-between">
                    <DropzoneDescription>
                      Upload your Netflix viewing history CSV
                    </DropzoneDescription>
                    <DropzoneMessage />
                  </div>
                  <DropZoneArea>
                    <DropzoneTrigger className="flex min-h-64 w-full flex-col items-center justify-center gap-5 rounded-lg border-2 border-dashed border-gray-300 bg-[#faf8f5] p-8 text-center text-sm transition hover:border-red-300 hover:bg-red-50/40">
                      <span className="flex h-16 w-16 items-center justify-center rounded-full bg-white shadow-sm">
                        <CloudUploadIcon className="h-8 w-8 text-red-600" />
                      </span>
                      <div>
                        <p className="text-lg font-bold text-gray-950">
                          Drop ViewingActivity.csv here
                        </p>
                        <p className="mt-2 text-sm text-gray-600">
                          Or click to browse. CSV only, up to 5 MB.
                        </p>
                      </div>
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
                          <DropzoneRemoveFile className="rounded-md bg-white p-2">
                            <Trash2Icon className="h-4 w-4 text-red-500 transition hover:text-red-700" />
                          </DropzoneRemoveFile>
                        </div>
                      </DropzoneFileListItem>
                    ))}
                  </DropzoneFileList>
                )}
              </Dropzone>

              {(backgroundProcessing || processingStatus) && (
                <div className="grid gap-3">
                  {processingStatus && (
                    <div className="rounded-md border border-blue-200 bg-blue-50 p-4">
                      <div className="flex gap-3">
                        {backgroundProcessing ? (
                          <Loader2Icon className="mt-0.5 h-5 w-5 animate-spin text-blue-600" />
                        ) : (
                          <CheckCircle2Icon className="mt-0.5 h-5 w-5 text-blue-600" />
                        )}
                        <div>
                          <p className="text-sm font-bold text-blue-950">
                            Upload status
                          </p>
                          <p className="mt-1 text-xs leading-5 text-blue-700">
                            {processingStatus}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="rounded-md border border-gray-200 bg-gray-50 p-4 text-sm leading-6 text-gray-600">
                After upload, Statistics opens automatically. Choose a profile there and the latest available year will generate first.
              </div>
            </div>
          </div>

          <aside className="space-y-6">
            <div className="rounded-lg border border-gray-200 bg-gray-950 p-5 text-white shadow-sm sm:p-6">
              <p className="text-sm font-semibold text-red-300">Detected after upload</p>
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
                Upload a CSV here, then choose a profile in Statistics. Years become available as processing finishes.
              </p>
            </div>

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
