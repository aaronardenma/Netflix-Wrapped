import { useQuery } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { LuScanFace } from "react-icons/lu";
import { useSearchParams } from "react-router-dom";
import { netflixAPI } from "@/services/api";

const BACKEND_URL = "http://127.0.0.1:8000";

async function fetchData() {
//   const res = await fetch(`${BACKEND_URL}/api/stored-data`, {
//     method: "GET",
//     credentials: "include",
//     headers: { "Content-Type": "application/json" },
//   });
  const res = await netflixAPI.getStoredData()
  return res.data;
}

export default function Profiles() {
  const [searchParams, setSearchParams] = useSearchParams();

  const [profileSelected, setProfileSelected] = useState(null);
  const [yearSelected, setYearSelected] = useState(null);
  const [click, setClick] = useState(false);

  // Sync local state with URL search params
  useEffect(() => {
    const profile = searchParams.get("profile");
    const year = searchParams.get("year");

    setProfileSelected(profile);
    setYearSelected(year);
    setClick(!!profile || !!year);
  }, [searchParams]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["storedData"],
    queryFn: fetchData,
  });

  const handleSetProfileSelected = (profile) => {
    setClick(true);
    // Update URL params, triggers useEffect sync
    setSearchParams({ profile });
  };

  const submit = (year) => {
    setClick(true);
    setSearchParams({
      ...Object.fromEntries(searchParams),
      year,
    });
  };

  const reset = () => {
    setClick(false);
    setSearchParams({});
  };

  const fetchUserYears = () => {
    if (!data || !profileSelected) return null;
    return data[profileSelected]?.map((year) => (
      <div
        key={year}
        className="flex flex-col items-center p-8 hover:bg-gray-200 cursor-pointer duration-300"
        onClick={() => submit(year)}
      >
        {year}
      </div>
    ));
  };

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error loading data</div>;

  return (
    <>
      {!click && !profileSelected && (
        <div className="grid grid-cols-3 gap-4">
          {data
            ? Object.keys(data).map((name) => (
                <div
                  key={name.toLowerCase()}
                  onClick={() => handleSetProfileSelected(name)}
                  className="flex flex-col items-center p-8 hover:bg-gray-200 cursor-pointer duration-300"
                >
                  <LuScanFace className="text-3xl" />
                  {name}
                </div>
              ))
            : "None"}
        </div>
      )}

      {click && profileSelected && (
        <div className="flex flex-col items-center">
          <div
            key={String(profileSelected)}
            className="flex flex-col items-center p-8 "
          >
            <LuScanFace className="text-5xl" />
            {profileSelected}
          </div>
          <div className="grid grid-cols-3 gap-8 mb-4">{fetchUserYears()}</div>
          <button
            className="text-sm cursor-pointer outline rounded-lg px-2 py-1 hover:bg-gray-100 duration-150"
            onClick={reset}
          >
            Back
          </button>
        </div>
      )}
    </>
  );
}
