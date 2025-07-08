import React from "react";
import { useSearchParams, useNavigate, useLocation } from "react-router-dom";
import LineGraph from "../components/LineGraph";
import BarGraph from "../components/BarGraph";
import PieGraph from "../components/PieGraph";

export default function Statistics() {
  const [searchParams] = useSearchParams();
  const user = searchParams.get("user") || "Unknown";
  const year = searchParams.get("year") || "Unknown";

  const location = useLocation();
  const graphs = location.state || {};

  const navigate = useNavigate();

  if (!graphs || Object.keys(graphs).length === 0) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen text-center space-y-4">
        <p className="text-lg font-medium text-muted-foreground">
          No graph data available for <span className="font-semibold text-primary">{user}</span> in{" "}
          <span className="font-semibold text-primary">{year}</span>.
        </p>
        <button
          onClick={() => navigate("/upload")}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition"
        >
          Go Back to Upload
        </button>
      </div>
    );
  }

  const monthlyWatchtimeData = graphs.monthly_watchtime || [];
  const titleWatchtimeData = graphs.total_title_watchtime || [];
  const typeWatchtimeData = graphs.total_type_watchtime || [];
  const ratingWatchtimeData = graphs.ratings_watchtime || [];

  return (
    <div className="max-w-6xl mx-auto px-4 py-8 space-y-6">
      <div className="flex justify-between items-center mb-6">
        <h2 className="text-2xl font-bold">
          Statistics for{" "}
          <span className="text-primary">{user}</span> ({year})
        </h2>
        <button
          onClick={() => navigate("/upload")}
          className="px-4 py-2 bg-muted text-foreground border border-border rounded hover:bg-muted/80 transition"
        >
          Choose New User
        </button>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="bg-card shadow-sm rounded-lg p-4">
          <LineGraph
            data={monthlyWatchtimeData}
            x_axis_key="month"
            x_axis_label="Months"
            y_axis_label="Watchtime (hrs)"
            title="Monthly Watchtime"
          />
        </div>

        <div className="bg-card shadow-sm rounded-lg p-4">
          <BarGraph
            data={titleWatchtimeData}
            x_axis_key="title"
            x_axis_label="Title"
            y_axis_key="hrs"
            y_axis_label="Watchtime (hrs)"
            title="Top 10 Watched Content"
          />
        </div>

        <div className="bg-card shadow-sm rounded-lg p-4 md:col-span-2">
          <PieGraph
            data={typeWatchtimeData}
            metric="hrs"
            category_key="type"
            title="Content Type Breakdown"
          />
        </div>
      </div>

      <div className="text-center mt-10">
        <button
          onClick={() => navigate("/upload")}
          className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600 transition"
        >
          Back
        </button>
      </div>
    </div>
  );
}
