/* eslint-disable react/prop-types */
import { Film, Globe2, Tags, Timer, TrendingUp } from "lucide-react";

const fullMonthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

function formatHours(value) {
  const number = Number(value || 0);
  return number.toFixed(2).replace(/\.?0+$/, "");
}

function monthName(item) {
  const monthNumber = Number(item.month);
  return fullMonthNames[monthNumber - 1] || item.month_label || `Month ${item.month}`;
}

function InsightList({
  icon: Icon,
  title,
  items,
  labelKey,
  valueSuffix = "hrs",
  formatValue = (value) => value,
}) {
  if (!items?.length) return null;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex size-9 items-center justify-center rounded-md bg-red-50 text-red-600">
          <Icon className="size-4" />
        </div>
        <h3 className="text-base font-black text-neutral-950">{title}</h3>
      </div>
      <div className="space-y-3">
        {items.slice(0, 6).map((item) => (
          <div key={`${title}-${item[labelKey]}`} className="flex min-w-0 items-center justify-between gap-3">
            <span className="break-words text-sm font-bold leading-5 text-neutral-900">{item[labelKey]}</span>
            <span className="text-sm font-bold text-neutral-950">
              {formatValue(item.hrs)} {valueSuffix}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function GenreContentInsights({ insights }) {
  if (!insights) return null;

  return (
    <section className="space-y-4">
      <div>
        <p className="text-sm font-bold uppercase text-red-600">Content Insights</p>
        <h2 className="mt-1 text-xl font-black tracking-normal text-neutral-950 sm:text-2xl">
          Genres, eras, and watching preferences
        </h2>
      </div>
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <InsightList
          icon={Tags}
          title="Top Genres"
          items={insights.genre_watchtime}
          labelKey="genre"
        />
        <InsightList
          icon={TrendingUp}
          title="Release Periods"
          items={insights.release_period_watchtime || insights.release_decade_watchtime}
          labelKey={insights.release_period_watchtime ? "period" : "decade"}
        />
        <InsightList
          icon={Globe2}
          title="Content Countries"
          items={insights.country_watchtime}
          labelKey="country"
        />
        <InsightList
          icon={Timer}
          title="Runtime Preference"
          items={insights.runtime_preference}
          labelKey="bucket"
        />
        <InsightList
          icon={Film}
          title="Ratings"
          items={insights.rating_watchtime}
          labelKey="rating"
          formatValue={formatHours}
        />
        <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-base font-black text-neutral-950">Top Genre By Month</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {insights.top_genre_by_month?.slice(0, 12).map((item) => (
              <div key={item.month} className="rounded-md bg-neutral-50 p-3">
                <p className="text-xs font-bold uppercase text-neutral-400">
                  {monthName(item)}
                </p>
                <p className="break-words text-sm font-bold leading-5 text-neutral-900">{item.genre}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
