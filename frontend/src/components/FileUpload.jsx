import { useEffect, useState } from "react";
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
import { CloudUploadIcon, Trash2Icon, Loader2Icon, ZapIcon } from "lucide-react";
import { toast, ToastContainer } from "react-toastify";
import {netflixAPI} from "@/services/api/"

export default function FileUpload() {
  const [file, setFile] = useState(null);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [userYearsMap, setUserYearsMap] = useState({});
  const [availableYears, setAvailableYears] = useState([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedYear, setSelectedYear] = useState("");
  const [loading, setLoading] = useState(false);
  const [backgroundProcessing, setBackgroundProcessing] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [processingStatus, setProcessingStatus] = useState("");
  const [priorityProcessing, setPriorityProcessing] = useState(false);
  const navigate = useNavigate(); 

  const dropzone = useDropzone({
    onDropFile: async (file) => {
      setFile(file);
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
    const formData = new FormData();
    formData.append("file", file);

    try {
      setBackgroundProcessing(true);

      // const res = await fetch("http://127.0.0.1:8000/api/csv/quick-extract/", {
      //   method: "POST",
      //   body: formData,
      //   credentials: "include",
      // });
      const res = await netflixAPI.quickExtractCSV(file)
      console.log(res)

      const response = res.data;

      setUserYearsMap(response.profile_years);
      setAvailableUsers(Object.keys(response.profile_years).sort());
      setJobId(response.job_id);
      setProcessingStatus("Processing all combinations in background...");

      startPollingStatus(response.job_id);

      toast.success("CSV uploaded! Select a profile/year and we'll prioritize processing it.", {
        autoClose: 5000,
        theme: "colored",
      });

    } catch (err) {
      console.error("Extract error:", err);
      toast.error(`Failed to extract data: ${err.message}`, {
        autoClose: 10000,
        theme: "colored",
      });
      setBackgroundProcessing(false);
    }
  };

  const startPollingStatus = (jobId) => {
    const pollInterval = setInterval(async () => {
      try {
        // const res = await fetch(`http://127.0.0.1:8000/api/processing-status/${jobId}/`, {
        //   credentials: "include",
        // });

        const res = await netflixAPI.getProcessingStatus(jobId)
        console.log(res)

        if (res.ok) {
          const status = res.data.status;

          if (status.status === "completed") {
            setBackgroundProcessing(false);
            setProcessingStatus("All data processed!");
            clearInterval(pollInterval);
            toast.success("Background processing completed!", {
              theme: "colored",
            });
          } else if (status.status === "error") {
            setBackgroundProcessing(false);
            setProcessingStatus(`Processing error: ${status.message}`);
            clearInterval(pollInterval);
          } else {
            setProcessingStatus("Processing remaining combinations in background...");
          }
        }
      } catch (error) {
        console.error("Status polling error:", error);
      }
    }, 5000); // Poll every 5 seconds

    setTimeout(() => clearInterval(pollInterval), 600000); // Clean up after 10 minutes
  };

  const pollForPriorityResult = async (maxAttempts = 10) => {
    let attempts = 0;

    const checkResult = async () => {
      try {
        // const response = await fetch("http://127.0.0.1:8000/api/get-data/", {
        //   method: "POST",
        //   headers: {
        //     "Content-Type": "application/json",
        //   },
        //   body: JSON.stringify({
        //     user: selectedUser,
        //     year: selectedYear,
        //     job_id: jobId,
        //   }),
        //   credentials: "include",
        // });

        const response = await netflixAPI.getData(selectedUser, selectedYear, jobId)

        if (response.ok) {
          const responseData = response.data;

          if (responseData.status === "ready") {
            setPriorityProcessing(false);
            setLoading(false);

            // Navigate to /statistics with query params only (no state)
            navigate(
              `/statistics?profile=${encodeURIComponent(selectedUser)}&year=${encodeURIComponent(selectedYear)}`
            );
            return true;
          }
        }

        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(checkResult, 1000);
        } else {
          setPriorityProcessing(false);
          setLoading(false);
          toast.error("Priority processing is taking longer than expected. Please try again.", {
            theme: "colored",
          });
        }
      } catch (error) {
        console.error("Priority polling error:", error);
        attempts++;
        if (attempts < maxAttempts) {
          setTimeout(checkResult, 2000);
        } else {
          setPriorityProcessing(false);
          setLoading(false);
          toast.error("Error checking priority processing status.", {
            theme: "colored",
          });
        }
      }
    };

    checkResult();
  };

  useEffect(() => {
    if (selectedUser && userYearsMap[selectedUser]) {
      setAvailableYears(userYearsMap[selectedUser]);
      setSelectedYear("");
    } else {
      setAvailableYears([]);
      setSelectedYear("");
    }
  }, [selectedUser, userYearsMap]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!selectedUser || !selectedYear) {
      toast.error("Please select a profile and year.", {
        theme: "colored",
      });
      return;
    }

    try {
      setLoading(true);

      // Check if data is already available
      // const response = await fetch("http://127.0.0.1:8000/api/get-data/", {
      //   method: "POST",
      //   headers: {
      //     "Content-Type": "application/json",
      //   },
      //   body: JSON.stringify({
      //     user: selectedUser,
      //     year: selectedYear,
      //     job_id: jobId,
      //   }),
      //   credentials: "include",
      // });

      const response = await netflixAPI.getData(selectedUser, selectedYear, jobId)

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const responseData = response.data;

      if (responseData.status === "ready") {
        // Navigate to statistics page with URL params only
        navigate(
          `/statistics?profile=${encodeURIComponent(selectedUser)}&year=${encodeURIComponent(selectedYear)}`
        );
      } else if (responseData.status === "priority_processing") {
        setPriorityProcessing(true);
        toast.info(
          `⚡ Processing ${selectedUser} - ${selectedYear} with priority!`,
          {
            autoClose: 3000,
            theme: "colored",
          }
        );

        // Start polling for priority result
        pollForPriorityResult();
      } else {
        toast.info(
          "Your selection is being processed. Please wait a moment...",
          {
            autoClose: 5000,
            theme: "colored",
          }
        );
        setLoading(false);
      }
    } catch (err) {
      console.error("Submit error:", err);
      toast.error(`Failed to get data: ${err.message}`, {
        autoClose: 10000,
        theme: "colored",
      });
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 py-16 px-4">
      <div className="mx-auto max-w-2xl bg-white border border-gray-200 rounded-xl p-8 shadow-lg space-y-8">
        <h2 className="text-3xl font-bold text-center mb-4">
          Upload Your <span className="text-red-600">Netflix</span> History
        </h2>

        <Dropzone {...dropzone}>
          <div>
            <div className="flex justify-between items-center mb-2 text-sm text-gray-600">
              <DropzoneDescription>
                Upload your Netflix viewing history CSV
              </DropzoneDescription>
              <DropzoneMessage />
            </div>
            <DropZoneArea>
              <DropzoneTrigger className="flex flex-col w-full items-center gap-4 p-10 rounded-lg border-2 border-dashed border-gray-300 text-center text-sm hover:bg-gray-100 transition-colors duration-200">
                <CloudUploadIcon className="size-8 text-gray-400" />
                <div>
                  <p className="font-semibold text-gray-700">Upload CSV</p>
                  <p className="text-sm text-gray-500">
                    Click or drag to upload
                  </p>
                </div>
              </DropzoneTrigger>
            </DropZoneArea>
          </div>
          {dropzone.fileStatuses.length > 0 && (
            <DropzoneFileList>
              {dropzone.fileStatuses.map((file) => (
                <DropzoneFileListItem
                  key={file.id}
                  file={file}
                  className="rounded px-3 py-2 mb-2 bg-gray-50 border border-gray-200"
                >
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="text-sm font-medium text-gray-700">
                        {file.fileName}
                      </p>
                      <p className="text-xs text-gray-500">
                        {(file.file.size / (1024 * 1024)).toFixed(2)} MB
                      </p>
                    </div>
                    <DropzoneRemoveFile className="bg-white">
                      <Trash2Icon className="text-red-500 hover:text-red-600 transition" />
                    </DropzoneRemoveFile>
                  </div>
                </DropzoneFileListItem>
              ))}
            </DropzoneFileList>
          )}
        </Dropzone>

        {/* Processing Status */}
        {/* {backgroundProcessing && (
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div className="flex items-center">
              <Loader2Icon className="animate-spin h-5 w-5 text-blue-500 mr-2" />
              <div>
                <p className="text-sm font-medium text-blue-800">
                  Background Processing
                </p>
                <p className="text-xs text-blue-600">{processingStatus}</p>
              </div>
            </div>
          </div>
        )} */}

        {/* Priority Processing Status */}
        {priorityProcessing && (
          <div className="bg-orange-50 border border-orange-200 rounded-lg p-4">
            <div className="flex items-center">
              <ZapIcon className="h-5 w-5 text-orange-500 mr-2" />
              <div>
                <p className="text-sm font-medium text-orange-800">
                  ⚡ Priority Processing
                </p>
                <p className="text-xs text-orange-600">
                  Processing...
                </p>
              </div>
            </div>
          </div>
        )}

        {availableUsers.length > 0 && (
          <div>
            <label className="block mb-1 text-sm font-medium text-gray-700">
              Profile
            </label>
            <select
              value={selectedUser}
              onChange={(e) => setSelectedUser(e.target.value)}
              className="w-full p-2 rounded text-gray-900 border border-gray-300 focus:outline-none focus:ring-2 focus:ring-red-600"
            >
              <option value="">Select profile</option>
              {availableUsers.map((user) => (
                <option key={user} value={user}>
                  {user}
                </option>
              ))}
            </select>
          </div>
        )}

        {availableYears.length > 0 && (
          <div>
            <label className="block mb-1 text-sm font-medium text-gray-700">
              Year
            </label>
            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(e.target.value)}
              className="w-full p-2 rounded text-gray-900 border border-gray-300 focus:outline-none focus:ring-2 focus:ring-red-600"
            >
              <option value="">Select year</option>
              {availableYears.map((year) => (
                <option key={year} value={year}>
                  {year}
                </option>
              ))}
            </select>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading || !selectedUser || !selectedYear}
          className="w-full bg-red-600 hover:bg-red-700 transition text-white font-semibold py-2 px-4 rounded disabled:opacity-50 flex items-center justify-center"
        >
          {loading ? (
            priorityProcessing ? (
              <>
                <ZapIcon className="h-4 w-4 mr-2" />
                Priority Processing...
              </>
            ) : (
              <>
                <Loader2Icon className="animate-spin h-4 w-4 mr-2" />
                Getting Data...
              </>
            )
          ) : (
            <>
              <ZapIcon className="h-4 w-4 mr-2" />
              Get Started
            </>
          )}
        </button>
      </div>
      <ToastContainer />
    </div>
  );
}
