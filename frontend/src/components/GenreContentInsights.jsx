/* eslint-disable react/prop-types */
import { Film, Globe2, Tags, Timer, TrendingUp } from "lucide-react";

function InsightList({ icon: Icon, title, items, labelKey, valueSuffix = "hrs" }) {
  if (!items?.length) return null;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="mb-4 flex items-center gap-2">
        <div className="flex size-9 items-center justify-center rounded-md bg-red-50 text-red-600">
          <Icon className="size-4" />
        </div>
        <h3 className="font-bold text-neutral-950">{title}</h3>
      </div>
      <div className="space-y-3">
        {items.slice(0, 6).map((item) => (
          <div key={`${title}-${item[labelKey]}`} className="flex items-center justify-between gap-4">
            <span className="text-sm font-medium text-neutral-700">{item[labelKey]}</span>
            <span className="text-sm font-bold text-neutral-950">
              {item.hrs} {valueSuffix}
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
        <h2 className="mt-1 text-2xl font-black tracking-normal text-neutral-950">
          Genres, eras, and watching preferences
        </h2>
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <InsightList
          icon={Tags}
          title="Top Genres"
          items={insights.genre_watchtime}
          labelKey="genre"
        />
        <InsightList
          icon={TrendingUp}
          title="Release Decades"
          items={insights.release_decade_watchtime}
          labelKey="decade"
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
        />
        <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 font-bold text-neutral-950">Top Genre By Month</h3>
          <div className="grid grid-cols-2 gap-2">
            {insights.top_genre_by_month?.slice(0, 12).map((item) => (
              <div key={item.month} className="rounded-md bg-neutral-50 p-3">
                <p className="text-xs font-bold uppercase text-neutral-400">Month {item.month}</p>
                <p className="text-sm font-semibold text-neutral-900">{item.genre}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
