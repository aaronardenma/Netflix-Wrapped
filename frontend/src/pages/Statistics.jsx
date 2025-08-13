import React, { useState } from "react";
import { useSearchParams, useNavigate, useLocation } from "react-router-dom";
import Profiles from "@/components/Profiles";
import { useQuery } from "@tanstack/react-query";
import VizCarousel from "@/components/VizCarousel";
import { netflixAPI } from "@/services/api";

const BACKEND_URL = "http://127.0.0.1:8000";

export default function Statistics() {
  const [searchParams] = useSearchParams();
  const profile = searchParams.get("profile") || null;
  const year = searchParams.get("year") || null;
  // const [graphs, setGraphs] = useState(null);

  const navigate = useNavigate();

  const {
    data: graphs,
    error,
    isLoading,
  } = useQuery({
    queryFn: () => fetchGraphs(),
    queryKey: ["graphs", profile, year],
    enabled: !!profile && !!year,
  });

  const fetchGraphs = async () => {
    try {
      // const res = await fetch(`http://127.0.0.1:8000/api/get-stored-data/`, {
      //   method: "POST",
      //   headers: {
      //     "Content-Type": "application/json",
      //   },
      //   body: JSON.stringify({ profile_name: profile, year: parseInt(year) }),
      //   credentials: "include",
      // });
      const res = await netflixAPI.getStoredDataByProfile(profile, parseInt(year))

      const data = await res.data;
      return data.data;
    } catch (err) {
      console.error(err);
    }
  };

  // const monthlyWatchtimeData = graphs.monthly_watchtime || [];
  // const titleWatchtimeData = graphs.total_title_watchtime || [];
  // const typeWatchtimeData = graphs.total_type_watchtime || [];
  // const ratingWatchtimeData = graphs.ratings_watchtime || [];
  // console.log(fetchGraphs());
  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      {!graphs ? (
        <div className="flex flex-col">
          {/* <div className="text-center mb-4"> */}
          <p className="text-xl font-semibold ml-4 mb-4">
            Check out your previous stats!
          </p>
          <Profiles />
        </div>
      ) : (
        <div className="flex flex-col">
          <h2 className="text-2xl font-bold mb-4 ml-4">
            <span>{profile}</span>{" "}<span className="text-red-500">({year})</span>
          </h2>
          <VizCarousel graphs={graphs} profile={profile} year={year} />
        </div>
      )}
    </div>
  );
}
