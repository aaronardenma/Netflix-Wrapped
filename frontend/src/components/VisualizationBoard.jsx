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
const daypartOrder = ["Late night", "Morning", "Afternoon", "Evening"];
const daypartLabels = {
  "Late night": "Late night<br>12 AM-5 AM",
  Morning: "Morning<br>6 AM-11 AM",
  Afternoon: "Afternoon<br>12 PM-5 PM",
  Evening: "Evening<br>6 PM-11 PM",
};
const netflixRed = "#e50914";
const ink = "#171717";
const grid = "#e5e5e5";
const slate = "#334155";
const teal = "#0f766e";
const amber = "#d97706";
const indigo = "#4f46e5";
const rose = "#be123c";
const sky = "#0284c7";
const categoricalPalette = [
  netflixRed,
  teal,
  amber,
  indigo,
  rose,
  sky,
  "#65a30d",
  "#7c3aed",
  "#c2410c",
  "#0891b2",
];
const calendarScale = [
  [0, "#fffbeb"],
  [0.35, "#fcd34d"],
  [1, amber],
];
const timeWindowScale = [
  [0, "#ecfeff"],
  [0.35, "#67e8f9"],
  [1, teal],
];
const streakScale = [
  [0, "#f5f5f5"],
  [0.49, "#f5f5f5"],
  [0.5, "#c7d2fe"],
  [0.74, "#c7d2fe"],
  [0.75, indigo],
  [1, indigo],
];

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

function movieShowSummaryRows(rows = []) {
  const totals = new Map();
  rows.forEach((row) => {
    const type = row.type || "Unknown";
    if (type === "Unknown") return;
    totals.set(type, (totals.get(type) || 0) + hours(row.hrs));
  });

  return [...totals.entries()]
    .map(([type, hrs]) => ({ type, hrs }))
    .sort((a, b) => a.hrs - b.hrs);
}

function daypartForHour(hour) {
  const numericHour = Number(hour);
  if (numericHour < 6) return "Late night";
  if (numericHour < 12) return "Morning";
  if (numericHour < 18) return "Afternoon";
  return "Evening";
}

function buildDaypartHeatmap(rows = [], hourlyRows = []) {
  if (rows.length) {
    return dayOrder.map((day) =>
      daypartOrder.map((daypart) => {
        const match = rows.find(
          (row) => row.day === day && row.daypart === daypart,
        );
        return hours(match?.hrs);
      }),
    );
  }

  const totals = Object.fromEntries(daypartOrder.map((daypart) => [daypart, 0]));
  hourlyRows.forEach((row) => {
    totals[daypartForHour(row.hour)] += hours(row.hrs);
  });
  return [daypartOrder.map((daypart) => totals[daypart])];
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

function buildProfileNetwork(comparisons = {}) {
  const profiles = (comparisons.profile_watchtime || []).map((row) => row.profile);
  if (profiles.length < 2) return null;

  const links = comparisons.profile_similarity_links || [];
  const radius = 1;
  const nodes = profiles.map((profile, index) => {
    const angle = (2 * Math.PI * index) / profiles.length - Math.PI / 2;
    return {
      profile,
      x: Math.cos(angle) * radius,
      y: Math.sin(angle) * radius,
      watchtime: hours(
        comparisons.profile_watchtime.find((row) => row.profile === profile)?.hrs,
      ),
      color: categoricalPalette[index % categoricalPalette.length],
    };
  });
  const nodeByProfile = new Map(nodes.map((node) => [node.profile, node]));
  const maxWatchtime = Math.max(...nodes.map((node) => node.watchtime), 1);
  const linkTraces = links
    .filter((link) => nodeByProfile.has(link.source) && nodeByProfile.has(link.target))
    .map((link) => {
      const source = nodeByProfile.get(link.source);
      const target = nodeByProfile.get(link.target);
      const similarity = hours(link.similarity);
      return {
        type: "scatter",
        mode: "lines",
        x: [source.x, target.x],
        y: [source.y, target.y],
        line: {
          color: similarity > 0 ? `rgba(23, 23, 23, ${Math.min(0.75, 0.18 + similarity / 140)})` : "rgba(23, 23, 23, 0.12)",
          width: Math.max(1, similarity / 18),
        },
        hoverinfo: "text",
        text: `${link.source} + ${link.target}<br>${similarity.toFixed(1)}% similar<br>${link.shared_titles || 0} shared titles`,
        showlegend: false,
      };
    });
  const labelTrace = {
    type: "scatter",
    mode: "text",
    x: links.map((link) => {
      const source = nodeByProfile.get(link.source);
      const target = nodeByProfile.get(link.target);
      return source && target ? (source.x + target.x) / 2 : null;
    }),
    y: links.map((link) => {
      const source = nodeByProfile.get(link.source);
      const target = nodeByProfile.get(link.target);
      return source && target ? (source.y + target.y) / 2 : null;
    }),
    text: links.map((link) => `${hours(link.similarity).toFixed(0)}%`),
    textfont: { size: 12, color: ink },
    hoverinfo: "skip",
    showlegend: false,
  };
  const nodeTrace = {
    type: "scatter",
    mode: "markers+text",
    x: nodes.map((node) => node.x),
    y: nodes.map((node) => node.y),
    text: nodes.map((node) => node.profile),
    textposition: "bottom center",
    marker: {
      color: nodes.map((node) => node.color),
      size: nodes.map((node) => Math.max(24, 24 + (node.watchtime / maxWatchtime) * 28)),
      line: { color: "white", width: 2 },
    },
    hovertemplate: "%{text}<br>%{customdata:.2f} hrs watched<extra></extra>",
    customdata: nodes.map((node) => node.watchtime),
    showlegend: false,
  };

  return [...linkTraces, labelTrace, nodeTrace];
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
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-indigo-200 align-middle" />Watched</span>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-indigo-600 align-middle" />Streak day</span>
              <span className="text-indigo-700">Best streak: {longestStreakDays} days</span>
            </>
          ) : (
            <>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-amber-50 align-middle" />Little or no watch time</span>
              <span><span className="mr-1.5 inline-block size-3 rounded-sm bg-amber-600 align-middle" />More watch time</span>
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
            colorscale: isStreakMode ? streakScale : calendarScale,
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
  const daypartRows = visualizations.daypart_by_day_heatmap || [];
  const daypartHeatmap = buildDaypartHeatmap(daypartRows, hourlyRows);
  const daypartYLabels = daypartRows.length
    ? dayOrder.map((day) => day.slice(0, 3))
    : ["All days"];
  const typeRows = movieShowSummaryRows(visualizations.movie_show_by_month || []);
  const profileNetworkData = buildProfileNetwork(graphs?.profile_comparisons);
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
              marker: { color: slate },
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
              marker: { color: teal },
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
              type: "heatmap",
              z: daypartHeatmap,
              x: daypartOrder.map((daypart) => daypartLabels[daypart]),
              y: daypartYLabels,
              colorscale: timeWindowScale,
              zmin: 0,
              colorbar: { title: { text: "Hours" } },
              hovertemplate:
                "%{y}<br>%{x}<br>%{z:.2f} hrs<extra></extra>",
            },
          ]}
          layout={chartLayout("Peak Viewing Windows", {
            height: 340,
            margin: { t: 52, r: 72, b: 76, l: 64 },
            xaxis: {
              showgrid: false,
              zeroline: false,
              automargin: true,
            },
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
                colors: categoricalPalette,
              },
              domain: { x: [0, 0.72], y: [0, 1] },
              textinfo: "percent",
              textposition: "inside",
              insidetextorientation: "horizontal",
              hovertemplate: "%{label}<br>%{value:.2f} hrs<br>%{percent}<extra></extra>",
            },
          ]}
          layout={chartLayout("Your Genre Mix", {
            height: 460,
            showlegend: true,
            margin: { t: 56, r: 118, b: 48, l: 12 },
            legend: {
              orientation: "v",
              x: 0.86,
              xanchor: "left",
              y: 0.98,
              yanchor: "top",
              font: { size: 10 },
              itemwidth: 24,
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
          data={[
            {
              type: "bar",
              orientation: "h",
              x: typeRows.map((row) => row.hrs),
              y: typeRows.map((row) => row.type),
              marker: {
                color: typeRows.map(
                  (_, index) => categoricalPalette[index % categoricalPalette.length],
                ),
              },
              text: typeRows.map((row) => `${row.hrs.toFixed(1)} hrs`),
              textposition: "auto",
              hovertemplate: "%{y}<br>%{x:.2f} hrs<extra></extra>",
            },
          ]}
          layout={chartLayout("Movies vs TV Split", {
            height: 340,
            margin: { t: 52, r: 28, b: 48, l: 92 },
            xaxis: {
              title: { text: "Hours watched" },
              gridcolor: grid,
              zeroline: false,
              rangemode: "tozero",
              automargin: true,
            },
            yaxis: {
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
              line: { color: indigo, width: 2 },
              fill: "tozeroy",
              fillcolor: "rgba(79, 70, 229, 0.14)",
            },
          ]}
          layout={chartLayout("Your Viewing Timeline", {
            height: 340,
            yaxis: {
              title: { text: "Hours watched" },
              gridcolor: grid,
              zeroline: false,
              rangemode: "tozero",
              automargin: true,
            },
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
              orientation: "h",
              x: [...topTitles].reverse().map((row) => hours(row.hrs)),
              y: [...topTitles].reverse().map((row) => row.title),
              marker: {
                color: [...topTitles].reverse().map(
                  (_, index) => categoricalPalette[index % categoricalPalette.length],
                ),
              },
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

      {profileNetworkData ? (
        <ChartCard>
          <Plot
            data={profileNetworkData}
            layout={chartLayout("Profile Similarity Map", {
              height: 430,
              margin: { t: 52, r: 20, b: 28, l: 20 },
              xaxis: {
                visible: false,
                range: [-1.35, 1.35],
                fixedrange: true,
              },
              yaxis: {
                visible: false,
                range: [-1.25, 1.35],
                scaleanchor: "x",
                scaleratio: 1,
                fixedrange: true,
              },
              showlegend: false,
            })}
            config={{ displayModeBar: false, responsive: true }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </ChartCard>
      ) : (
        <EmptyChart title="Profile Similarity Map" />
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
