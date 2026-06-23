/* eslint-disable react/prop-types */
import Plot from "react-plotly.js";

// Keep the Sankey, bubble chart, and treemap available for later iteration.
const SHOW_DEFERRED_VISUALIZATIONS = false;

const monthOrder = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];
const dayOrder = [
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
  "Sunday",
];
const netflixRed = "#e50914";
const ink = "#171717";
const grid = "#e5e5e5";

function hours(value) {
  return Number(value || 0);
}

function chartLayout(title, extra = {}) {
  return {
    title: {
      text: title ? `<b>${title}</b>` : "",
      x: 0,
      xanchor: "left",
      font: { size: 16, color: ink },
    },
    margin: { t: 52, r: 24, b: 48, l: 56 },
    paper_bgcolor: "white",
    plot_bgcolor: "white",
    font: { family: "Montserrat, Arial, sans-serif", color: ink },
    hoverlabel: { bgcolor: ink, bordercolor: ink, font: { color: "white" } },
    xaxis: { gridcolor: grid, zerolinecolor: grid, automargin: true },
    yaxis: { gridcolor: grid, zerolinecolor: grid, automargin: true },
    ...extra,
  };
}

function ChartCard({ children, wide = false, allowOverflow = false }) {
  return (
    <div
      className={`min-w-0 rounded-lg border border-neutral-200 bg-white p-3 shadow-sm sm:p-4 ${
        allowOverflow ? "overflow-visible" : "overflow-hidden"
      } ${wide ? "lg:col-span-2" : ""}`}
    >
      {children}
    </div>
  );
}

function EmptyChart({ title }) {
  return (
    <ChartCard>
      <div className="flex h-80 flex-col justify-center">
        <h3 className="text-base font-black text-neutral-950">{title}</h3>
        <p className="mt-2 text-sm text-neutral-500">
          Not enough data for this view.
        </p>
      </div>
    </ChartCard>
  );
}

function toCalendarMatrix(rows = []) {
  if (!rows.length) return null;

  const dates = rows.map((row) => new Date(`${row.date}T00:00:00`));
  const min = new Date(Math.min(...dates));
  const max = new Date(Math.max(...dates));
  const start = new Date(min);
  start.setDate(start.getDate() - start.getDay());
  const end = new Date(max);
  end.setDate(end.getDate() + (6 - end.getDay()));

  const byDate = new Map(rows.map((row) => [row.date, hours(row.hrs)]));
  const weeks = [];
  const labels = [];
  const hover = [];
  const dateGrid = [];
  const values = Array.from({ length: 7 }, () => []);
  let cursor = new Date(start);

  while (cursor <= end) {
    const weekLabel = cursor.toISOString().slice(0, 10);
    labels.push(weekLabel);
    weeks.push(values[0].length);
    for (let day = 0; day < 7; day += 1) {
      const iso = cursor.toISOString().slice(0, 10);
      const value = byDate.get(iso) || 0;
      values[day].push(value);
      hover[day] ||= [];
      dateGrid[day] ||= [];
      hover[day].push(`${iso}<br>${value.toFixed(2)} hrs`);
      dateGrid[day].push(iso);
      cursor.setDate(cursor.getDate() + 1);
    }
  }

  return { labels, weeks, values, hover, dateGrid };
}

function monthlyChartData(rows = []) {
  const byMonth = new Map(rows.map((row) => [row.month, hours(row.hrs)]));
  return monthOrder.map((month) => ({
    month,
    hrs: byMonth.get(month.toUpperCase()) ?? byMonth.get(month) ?? 0,
  }));
}

function movieShowRows(rows = []) {
  const types = [
    ...new Set(
      rows
        .map((row) => row.type || "Unknown")
        .filter((type) => type !== "Unknown"),
    ),
  ];
  return types.map((type) => ({
    type,
    x: monthOrder,
    y: monthOrder.map((month) => {
      const match = rows.find(
        (row) =>
          (row.month || "").toLowerCase() === month.toLowerCase() &&
          (row.type || "Unknown") === type,
      );
      return hours(match?.hrs);
    }),
  }));
}

function buildRadarData(rows = []) {
  if (!rows.length) return [];
  const metrics = [
    ["watchtime_hours", "Watch time"],
    ["unique_titles", "Titles"],
    ["viewing_events", "Events"],
    ["movie_hours", "Movies"],
    ["show_hours", "Shows"],
    ["active_days", "Active days"],
  ];
  const maxByMetric = Object.fromEntries(
    metrics.map(([key]) => [
      key,
      Math.max(...rows.map((row) => hours(row[key])), 1),
    ]),
  );

  return rows.map((row) => ({
    type: "scatterpolar",
    r: metrics.map(([key]) => (hours(row[key]) / maxByMetric[key]) * 100),
    theta: metrics.map(([, label]) => label),
    fill: "toself",
    name: row.profile,
  }));
}

function buildSankeyData(rows = []) {
  if (!rows.length) return null;

  const labels = [];
  const indexOf = (label) => {
    const index = labels.indexOf(label);
    if (index >= 0) return index;
    labels.push(label);
    return labels.length - 1;
  };

  const linkMap = new Map();
  rows.forEach((row) => {
    const profile = `Profile: ${row.profile}`;
    const genre = `Genre: ${row.genre}`;
    const type = `Type: ${row.type}`;
    [
      [profile, genre],
      [genre, type],
    ].forEach(([source, target]) => {
      const key = `${source}|${target}`;
      linkMap.set(key, (linkMap.get(key) || 0) + hours(row.hrs));
    });
    indexOf(profile);
    indexOf(genre);
    indexOf(type);
  });

  const source = [];
  const target = [];
  const value = [];
  linkMap.forEach((linkValue, key) => {
    const [from, to] = key.split("|");
    source.push(indexOf(from));
    target.push(indexOf(to));
    value.push(linkValue);
  });

  return { labels, source, target, value };
}

function buildTreemapData(rows = []) {
  const genres = [...new Set(rows.map((row) => row.genre || "Unknown"))];
  const genreTotals = genres.map((genre) =>
    rows
      .filter((row) => (row.genre || "Unknown") === genre)
      .reduce((total, row) => total + hours(row.hrs), 0),
  );

  return {
    labels: ["All watch time", ...genres, ...rows.map((row) => row.title)],
    parents: [
      "",
      ...genres.map(() => "All watch time"),
      ...rows.map((row) => row.genre || "Unknown"),
    ],
    values: [
      genreTotals.reduce((total, value) => total + value, 0),
      ...genreTotals,
      ...rows.map((row) => hours(row.hrs)),
    ],
  };
}

function CalendarHeatmap({
  rows,
  title,
  description,
  mode = "watchtime",
  streakDates = [],
  longestStreakDays = 0,
}) {
  const matrix = toCalendarMatrix(rows);
  if (!matrix) return <EmptyChart title={title} />;
  const streakDateSet = new Set(streakDates);
  const isStreakMode = mode === "streak";
  const values = isStreakMode
    ? matrix.dateGrid.map((dates, dayIndex) =>
        dates.map((date, weekIndex) => {
          if (streakDateSet.has(date)) return 2;
          return matrix.values[dayIndex][weekIndex] > 0 ? 1 : 0;
        }),
      )
    : matrix.values;
  const hover = isStreakMode
    ? matrix.dateGrid.map((dates, dayIndex) =>
        dates.map((date, weekIndex) => {
          const watched = matrix.values[dayIndex][weekIndex] > 0;
          const status = streakDateSet.has(date)
            ? "Part of a consecutive watching streak"
            : watched
              ? "Watched, but not connected to another active day"
              : "No watch time";
          return `${date}<br>${status}`;
        }),
      )
    : matrix.hover;

  return (
    <ChartCard wide allowOverflow>
      <div className="mb-1">
        <h3 className="text-base font-black text-neutral-950">{title}</h3>
        <p className="mt-1 max-w-3xl text-sm leading-6 text-neutral-500">
          {description}
        </p>
        <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs font-semibold text-neutral-600">
          {isStreakMode ? (
            <>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-neutral-100 align-middle" />No viewing</span>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-red-200 align-middle" />Watched</span>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-red-700 align-middle" />Streak day</span>
              <span className="text-red-700">Best streak: {longestStreakDays} days</span>
            </>
          ) : (
            <>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-red-50 align-middle" />Little or no watch time</span>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-red-600 align-middle" />More watch time</span>
            </>
          )}
        </div>
      </div>
      <Plot
        data={[
          {
            z: values,
            x: matrix.weeks,
            y: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
            text: hover,
            hovertemplate: "%{text}<extra></extra>",
            type: "heatmap",
            colorscale: isStreakMode
              ? [
                  [0, "#f5f5f5"],
                  [0.49, "#f5f5f5"],
                  [0.5, "#fecaca"],
                  [0.74, "#fecaca"],
                  [0.75, "#b91c1c"],
                  [1, "#b91c1c"],
                ]
              : [
                  [0, "#fff5f5"],
                  [0.35, "#fca5a5"],
                  [1, netflixRed],
                ],
            zmin: 0,
            zmax: isStreakMode ? 2 : undefined,
            showscale: !isStreakMode,
            colorbar: isStreakMode ? undefined : { title: { text: "Hours" } },
          },
        ]}
        layout={chartLayout("", {
          height: 340,
          margin: { t: 20, r: isStreakMode ? 24 : 72, b: 44, l: 64 },
          xaxis: { showgrid: false, zeroline: false, showticklabels: false },
          yaxis: {
            autorange: "reversed",
            showgrid: false,
            zeroline: false,
            automargin: true,
          },
        })}
        config={{ displayModeBar: false, responsive: true }}
        useResizeHandler
        style={{ width: "100%", height: "340px" }}
      />
    </ChartCard>
  );
}

export default function VisualizationBoard({ graphs }) {
  const visualizations = graphs?.visualizations || {};
  const genreWatchtime = graphs?.genre_content_insights?.genre_watchtime || [];
  const topTitles = graphs?.total_title_watchtime || [];
  const monthly = monthlyChartData(graphs?.monthly_watchtime || []);
  const hourlyRows = visualizations.hour_of_day_heatmap || [];
  const peakHourValue = Math.max(
    ...hourlyRows.map((row) => hours(row.hrs)),
    0,
  );
  const typeRows = movieShowRows(visualizations.movie_show_by_month || []);
  const radarData = buildRadarData(
    graphs?.profile_comparisons?.radar_metrics || [],
  );
  const sankeyData = buildSankeyData(
    graphs?.profile_comparisons?.sankey_profile_genre_type || [],
  );
  const treemapData = buildTreemapData(visualizations.treemap || []);

  return (
    <section className="grid min-w-0 gap-4 lg:grid-cols-2">
      <ChartCard wide>
        <Plot
          data={[
            {
              type: "bar",
              x: monthly.map((row) => row.month),
              y: monthly.map((row) => row.hrs),
              marker: { color: "#262626" },
              name: "Hours",
            },
            {
              type: "scatter",
              mode: "lines+markers",
              x: monthly.map((row) => row.month),
              y: monthly.map((row) => row.hrs),
              line: { color: netflixRed, width: 3 },
              marker: { color: netflixRed, size: 7 },
              name: "Trend",
            },
          ]}
          layout={chartLayout("Monthly Viewing Rhythm", {
            height: 360,
            barmode: "overlay",
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </ChartCard>

      <ChartCard>
        <Plot
          data={[
            {
              type: "bar",
              x: dayOrder.map((day) => day.slice(0, 3)),
              y: dayOrder.map((day) => {
                const match = (visualizations.day_of_week_heatmap || []).find(
                  (row) => row.day === day,
                );
                return hours(match?.hrs);
              }),
              marker: { color: netflixRed },
              hovertemplate: "%{x}<br>%{y:.2f} hrs<extra></extra>",
            },
          ]}
          layout={chartLayout("Watch Time by Day of Week", {
            height: 340,
            margin: { t: 52, r: 24, b: 48, l: 64 },
            xaxis: {
              showgrid: false,
              zeroline: false,
              tickangle: 0,
              automargin: true,
            },
            yaxis: {
              title: { text: "Hours" },
              gridcolor: grid,
              zeroline: false,
              rangemode: "tozero",
              automargin: true,
            },
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "340px" }}
        />
      </ChartCard>

      <ChartCard>
        <Plot
          data={[
            {
              type: "bar",
              orientation: "h",
              x: hourlyRows.map((row) => hours(row.hrs)),
              y: hourlyRows.map((row) => row.label),
              marker: {
                color: hourlyRows.map((row) =>
                  hours(row.hrs) === peakHourValue ? netflixRed : "#404040",
                ),
              },
              hovertemplate: "%{y}<br>%{x:.2f} hrs<extra></extra>",
            },
          ]}
          layout={chartLayout("Your Peak Viewing Hours", {
            height: 620,
            margin: { t: 52, r: 48, b: 48, l: 88 },
            xaxis: {
              title: { text: "Hours watched" },
              gridcolor: grid,
              zeroline: false,
              rangemode: "tozero",
              automargin: true,
            },
            yaxis: {
              autorange: "reversed",
              tickangle: 0,
              showgrid: false,
              zeroline: false,
              automargin: true,
            },
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "620px" }}
        />
      </ChartCard>

      <CalendarHeatmap
        rows={visualizations.calendar_heatmap || []}
        title="Your Daily Watch Time"
        description="Each square is one calendar day. Darker red means you watched more hours on that date; blank or pale squares indicate little or no viewing."
      />

      <ChartCard>
        <Plot
          data={[
            {
              type: "pie",
              labels: genreWatchtime.map((row) => row.genre),
              values: genreWatchtime.map((row) => hours(row.hrs)),
              hole: 0.58,
              marker: {
                colors: [
                  "#e50914",
                  "#262626",
                  "#f97316",
                  "#14b8a6",
                  "#6366f1",
                  "#84cc16",
                  "#f43f5e",
                  "#0ea5e9",
                ],
              },
              textinfo: "percent",
              textposition: "inside",
              insidetextorientation: "horizontal",
              hovertemplate: "%{label}<br>%{value:.2f} hrs<br>%{percent}<extra></extra>",
            },
          ]}
          layout={chartLayout("Your Genre Mix", {
            height: 460,
            showlegend: true,
            margin: { t: 56, r: 20, b: 120, l: 20 },
            legend: {
              orientation: "h",
              x: 0,
              xanchor: "left",
              y: -0.18,
              yanchor: "top",
              font: { size: 11 },
              itemwidth: 30,
            },
            uniformtext: { minsize: 9, mode: "hide" },
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </ChartCard>

      <ChartCard>
        <Plot
          data={typeRows.map((row) => ({
            type: "bar",
            x: row.x,
            y: row.y,
            name: row.type,
          }))}
          layout={chartLayout("Movies vs TV by Month", {
            height: 380,
            barmode: "stack",
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </ChartCard>

      <ChartCard wide>
        <Plot
          data={[
            {
              type: "scatter",
              mode: "lines",
              x: (visualizations.watchtime_timeline || []).map(
                (row) => row.date,
              ),
              y: (visualizations.watchtime_timeline || []).map((row) =>
                hours(row.hrs),
              ),
              line: { color: netflixRed, width: 2 },
              fill: "tozeroy",
              fillcolor: "rgba(229, 9, 20, 0.12)",
            },
          ]}
          layout={chartLayout("Your Viewing Timeline", { height: 340 })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </ChartCard>

      <ChartCard>
        <Plot
          data={[
            {
              type: "bar",
              orientation: "h",
              x: [...topTitles].reverse().map((row) => hours(row.hrs)),
              y: [...topTitles].reverse().map((row) => row.title),
              marker: { color: netflixRed },
              hovertemplate: "%{y}<br>%{x:.2f} hrs<extra></extra>",
            },
          ]}
          layout={chartLayout("Your Most-Watched Titles", {
            height: 430,
            margin: { t: 52, r: 18, b: 48, l: 110 },
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </ChartCard>

      {radarData.length ? (
        <ChartCard>
          <Plot
            data={radarData}
            layout={chartLayout("How Profiles Watch", {
              height: 430,
              polar: {
                radialaxis: { visible: true, range: [0, 100], ticksuffix: "%" },
              },
              showlegend: true,
            })}
            config={{ displayModeBar: false, responsive: true }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </ChartCard>
      ) : (
        <EmptyChart title="How Profiles Watch" />
      )}

      {SHOW_DEFERRED_VISUALIZATIONS && (
        <>
      {sankeyData ? (
        <ChartCard wide>
          <Plot
            data={[
              {
                type: "sankey",
                node: { label: sankeyData.labels, pad: 14, thickness: 16 },
                link: {
                  source: sankeyData.source,
                  target: sankeyData.target,
                  value: sankeyData.value,
                },
              },
            ]}
            layout={chartLayout("From Profiles to Genres and Formats", {
              height: 500,
              margin: { t: 52, r: 20, b: 20, l: 20 },
            })}
            config={{ displayModeBar: false, responsive: true }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </ChartCard>
      ) : (
        <EmptyChart title="From Profiles to Genres and Formats" />
      )}

      <ChartCard>
        <Plot
          data={[
            {
              type: "scatter",
              mode: "markers",
              x: (visualizations.title_bubbles || []).map((row) => row.genre),
              y: (visualizations.title_bubbles || []).map((row) => row.type),
              text: (visualizations.title_bubbles || []).map(
                (row) => `${row.title}<br>${hours(row.hrs).toFixed(2)} hrs`,
              ),
              marker: {
                color: (visualizations.title_bubbles || []).map(
                  (_, index) => index,
                ),
                colorscale: "Portland",
                size: (visualizations.title_bubbles || []).map((row) =>
                  Math.max(8, Math.sqrt(hours(row.hrs)) * 12),
                ),
                sizemode: "diameter",
                opacity: 0.78,
                line: { color: "white", width: 1 },
              },
              hovertemplate: "%{text}<extra></extra>",
            },
          ]}
          layout={chartLayout("Titles by Genre, Format, and Watch Time", {
            height: 430,
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </ChartCard>

      <ChartCard>
        <Plot
          data={[
            {
              type: "treemap",
              labels: treemapData.labels,
              parents: treemapData.parents,
              values: treemapData.values,
              branchvalues: "total",
              marker: { colorscale: "Reds" },
              hovertemplate: "%{label}<br>%{value:.2f} hrs<extra></extra>",
            },
          ]}
          layout={chartLayout("Where Your Watch Time Went", {
            height: 430,
            margin: { t: 52, r: 8, b: 8, l: 8 },
          })}
          config={{ displayModeBar: false, responsive: true }}
          useResizeHandler
          style={{ width: "100%", height: "100%" }}
        />
      </ChartCard>
        </>
      )}

      <CalendarHeatmap
        rows={visualizations.streak_calendar?.days || []}
        streakDates={visualizations.streak_calendar?.streak_dates || []}
        longestStreakDays={visualizations.streak_calendar?.longest_streak_days || 0}
        mode="streak"
        title="Your Watching Streaks"
        description="This view ignores hours and focuses on consistency. Dark red marks days connected to another active viewing day; light red marks isolated viewing days."
      />
    </section>
  );
}
