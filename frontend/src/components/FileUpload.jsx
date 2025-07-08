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
import { CloudUploadIcon, Trash2Icon } from "lucide-react";
import { toast, ToastContainer } from "react-toastify";
import axios from "axios";

export default function FileUpload() {
  const [file, setFile] = useState(null);
  const [availableUsers, setAvailableUsers] = useState([]);
  const [userYearsMap, setUserYearsMap] = useState({});
  const [availableYears, setAvailableYears] = useState([]);
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedYear, setSelectedYear] = useState("");
  const [loading, setLoading] = useState(false);
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
      const res = await axios.post("http://127.0.0.1:8000/api/extract/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        withCredentials: true,
      });
      const userYears = res.data;
      setUserYearsMap(userYears);
      setAvailableUsers(Object.keys(userYears).sort());
    } catch (err) {
      const backendError = err.response?.data?.error || "Failed to extract data.";
      toast.error(`Upload failed: ${backendError}`, {
        autoClose: 10000,
        theme: "colored",
      });
    }
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
    if (!file || !selectedUser || !selectedYear) {
      toast.error("Please select a file, user, and year.", { theme: "colored" });
      return;
    }

    const formData = new FormData();
    formData.append("file", file);
    formData.append("user", selectedUser);
    formData.append("year", selectedYear);

    try {
      setLoading(true);
      const response = await axios.post("http://127.0.0.1:8000/api/upload/", formData, {
        headers: { "Content-Type": "multipart/form-data" },
        withCredentials: true,
      });

      navigate(`/statistics?user=${encodeURIComponent(selectedUser)}&year=${encodeURIComponent(selectedYear)}`, {
        state: response.data,
      });
    } catch (err) {
      const message = err.response?.data?.error || err.message;
      toast.error(`Upload failed: ${message}`, { autoClose: 10000, theme: "colored" });
    } finally {
      setLoading(false);
    }
  };

  return (
  <div className="min-h-screen bg-gradient-to-br from-black via-zinc-900 to-neutral-800 text-white py-16 px-4">
    <div className="mx-auto max-w-2xl bg-white/5 backdrop-blur-sm border border-white/10 rounded-xl p-8 shadow-lg space-y-8">
      <h2 className="text-3xl font-bold text-center mb-4">
        Upload Your <span className="text-red-500">Netflix</span> History
      </h2>

      <Dropzone {...dropzone}>
        <div>
          <div className="flex justify-between items-center mb-2 text-sm text-zinc-300">
            <DropzoneDescription>Upload your Netflix viewing history CSV</DropzoneDescription>
            <DropzoneMessage />
          </div>
          <DropZoneArea className="bg-zinc-600">
            <DropzoneTrigger className="flex flex-col w-full items-center gap-4 bg-zinc-800 p-10 rounded-lg border-2 border-dashed border-zinc-600 text-center text-sm hover:bg-zinc-700 transition-colors duration-200">
              <CloudUploadIcon className="size-8 text-zinc-400" />
              <div>
                <p className="font-semibold text-white">Upload CSV</p>
                <p className="text-sm text-zinc-400">Click or drag to upload</p>
              </div>
            </DropzoneTrigger>
          </DropZoneArea>
        </div>

        <DropzoneFileList className="pt-4">
          {dropzone.fileStatuses.map((file) => (
            <DropzoneFileListItem
              key={file.id}
              file={file}
              className="rounded bg-zinc-700 px-3 py-2 mb-2"
            >
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm font-medium text-white">{file.fileName}</p>
                  <p className="text-xs text-zinc-400">{(file.file.size / (1024 * 1024)).toFixed(2)} MB</p>
                </div>
                <DropzoneRemoveFile>
                  <Trash2Icon className="text-red-400 hover:text-red-500 transition" />
                </DropzoneRemoveFile>
              </div>
            </DropzoneFileListItem>
          ))}
        </DropzoneFileList>
      </Dropzone>

      {availableUsers.length > 0 && (
        <div>
          <label className="block mb-1 text-sm font-medium text-zinc-200">User</label>
          <select
            value={selectedUser}
            onChange={(e) => setSelectedUser(e.target.value)}
            className="w-full p-2 rounded bg-zinc-800 text-white border border-zinc-600 focus:outline-none focus:ring-2 focus:ring-red-500"
          >
            <option value="">Select user</option>
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
          <label className="block mb-1 text-sm font-medium text-zinc-200">Year</label>
          <select
            value={selectedYear}
            onChange={(e) => setSelectedYear(e.target.value)}
            className="w-full p-2 rounded bg-zinc-800 text-white border border-zinc-600 focus:outline-none focus:ring-2 focus:ring-red-500"
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
        className="w-full bg-red-500 hover:bg-red-600 transition text-white font-semibold py-2 px-4 rounded disabled:opacity-50"
      >
        {loading ? "Processing..." : "Get Graphs"}
      </button>

      <ToastContainer />
    </div>
  </div>
);

}
