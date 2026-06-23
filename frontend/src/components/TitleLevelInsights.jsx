/* eslint-disable react/prop-types */
import { Clapperboard, Film, Flame, ListVideo, Repeat2, Star, Tv, Video } from "lucide-react";

function MetricList({ icon: Icon, title, items, labelKey, valueKey = "hrs", valueSuffix = "hrs", secondary }) {
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
          <div key={`${title}-${item[labelKey]}`} className="flex min-w-0 items-start justify-between gap-3">
            <div className="min-w-0">
              <p className="break-words text-sm font-bold leading-5 text-neutral-900">{item[labelKey]}</p>
              {secondary && (
                <p className="mt-0.5 text-xs text-neutral-500">{secondary(item)}</p>
              )}
            </div>
            <span className="shrink-0 text-sm font-bold text-neutral-950">
              {item[valueKey]} {valueSuffix}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

export default function TitleLevelInsights({ insights }) {
  if (!insights) return null;

  const hiddenObsession = insights.hidden_obsession;
  const mostActiveSeasons = [...(insights.season_watchtime || [])]
    .sort((a, b) => (b.active_days || 0) - (a.active_days || 0))
    .slice(0, 6);

  return (
    <section className="space-y-4">
      <div>
        <p className="text-sm font-bold uppercase text-red-600">Title Insights</p>
        <h2 className="mt-1 text-xl font-black tracking-normal text-neutral-950 sm:text-2xl">
          Shows, movies, binges, and rewatches
        </h2>
      </div>

      {hiddenObsession && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-5 shadow-sm">
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3">
              <div className="flex size-10 shrink-0 items-center justify-center rounded-md bg-red-600 text-white">
                <Star className="size-5" />
              </div>
              <div>
                <p className="text-sm font-bold uppercase text-red-700">Hidden obsession</p>
                <h3 className="mt-1 break-words text-xl font-black text-neutral-950">{hiddenObsession.title}</h3>
                <p className="mt-1 text-sm text-neutral-700">
                  {hiddenObsession.repeat_watches} repeat watches across {hiddenObsession.active_days} active days.
                </p>
              </div>
            </div>
            <p className="text-2xl font-black text-red-700">{hiddenObsession.hrs} hrs</p>
          </div>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        <MetricList
          icon={Clapperboard}
          title="Top Titles"
          items={insights.top_titles}
          labelKey="title"
          secondary={(item) => `${item.type} • ${item.watch_count} watches`}
        />
        <MetricList
          icon={Tv}
          title="Top Shows"
          items={insights.top_shows}
          labelKey="show"
          secondary={(item) => `${item.watch_count} watches`}
        />
        <MetricList
          icon={Film}
          title="Top Movies"
          items={insights.top_movies}
          labelKey="movie"
          secondary={(item) => `${item.watch_count} watches`}
        />
        <MetricList
          icon={Flame}
          title="Most Binged Series"
          items={insights.most_binged_series}
          labelKey="show"
          valueKey="episode_watches"
          valueSuffix="episodes"
          secondary={(item) => `${item.date} • ${item.hrs} hrs`}
        />
        <MetricList
          icon={ListVideo}
          title="Episodes Watched"
          items={insights.episodes_per_show}
          labelKey="show"
          valueKey="episodes"
          valueSuffix="episodes"
          secondary={(item) => `${item.watches} total watches • ${item.hrs} hrs`}
        />
        <MetricList
          icon={Video}
          title="Time Per Season"
          items={insights.season_watchtime}
          labelKey="label"
          secondary={(item) => `${item.watch_count} watches • ${item.active_days} active days`}
        />
        <MetricList
          icon={Repeat2}
          title="Rewatched Favorites"
          items={insights.rewatched_favorites}
          labelKey="title"
          valueKey="repeat_watches"
          valueSuffix="rewatches"
          secondary={(item) => `${item.hrs} hrs • ${item.type}`}
        />
        <MetricList
          icon={Video}
          title="Season Streaks"
          items={mostActiveSeasons}
          labelKey="label"
          valueKey="active_days"
          valueSuffix="days"
          secondary={(item) => `${item.watch_count} watches • ${item.hrs} hrs`}
        />
      </div>
    </section>
  );
}
