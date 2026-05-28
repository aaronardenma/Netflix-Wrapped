/* eslint-disable react/prop-types */
import {
  CalendarDays,
  Clock,
  Clapperboard,
  Flame,
  History,
  PlayCircle,
  Repeat2,
  Timer,
  Trophy,
} from "lucide-react";

const fallback = "None";

function StatCard({ icon: Icon, label, value, detail }) {
  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
      <div className="mb-3 flex items-center justify-between gap-3">
        <p className="text-sm font-semibold text-neutral-500">{label}</p>
        <div className="flex size-9 items-center justify-center rounded-md bg-red-50 text-red-600">
          <Icon className="size-4" />
        </div>
      </div>
      <p className="text-2xl font-black tracking-normal text-neutral-950">
        {value ?? fallback}
      </p>
      {detail && <p className="mt-2 text-sm text-neutral-500">{detail}</p>}
    </div>
  );
}

export default function CoreStatsGrid({ stats }) {
  if (!stats) return null;

  const cards = [
    {
      icon: Timer,
      label: "Total Watch Time",
      value: `${stats.total_watchtime_hours} hrs`,
      detail: `${stats.total_viewing_events} viewing events`,
    },
    {
      icon: Clapperboard,
      label: "Unique Titles",
      value: stats.unique_titles,
      detail: `${stats.unique_movies} movies, ${stats.unique_shows} shows`,
    },
    {
      icon: Clock,
      label: "Average Session",
      value: `${stats.average_session_minutes} min`,
      detail: "Average time per viewing event",
    },
    {
      icon: Trophy,
      label: "Longest Session",
      value: `${stats.longest_session?.minutes ?? 0} min`,
      detail: stats.longest_session?.title,
    },
    {
      icon: Flame,
      label: "Longest Streak",
      value: `${stats.longest_watch_streak_days} days`,
      detail: "Consecutive watch days",
    },
    {
      icon: CalendarDays,
      label: "Peak Day",
      value: stats.most_active_day?.day,
      detail: `${stats.most_active_day?.hours ?? 0} hrs watched`,
    },
    {
      icon: PlayCircle,
      label: "Peak Hour",
      value: stats.most_active_hour?.label,
      detail: `${stats.most_active_hour?.hours ?? 0} hrs watched`,
    },
    {
      icon: Repeat2,
      label: "Rewatched Titles",
      value: stats.rewatched_titles,
      detail: "Titles watched more than once",
    },
    {
      icon: History,
      label: "First / Last",
      value: stats.first_watched_title?.title,
      detail: `Last: ${stats.last_watched_title?.title ?? fallback}`,
    },
  ];

  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <StatCard key={card.label} {...card} />
      ))}
    </div>
  );
}
