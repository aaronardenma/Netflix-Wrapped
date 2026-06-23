/* eslint-disable react/prop-types */
import { UsersRound } from "lucide-react";

export default function ProfileComparisons({ comparisons }) {
  if (!comparisons?.profile_watchtime?.length) return null;

  return (
    <section className="space-y-4">
      <div>
        <p className="text-sm font-bold uppercase text-red-600">Profile Comparisons</p>
        <h2 className="mt-1 text-xl font-black tracking-normal text-neutral-950 sm:text-2xl">
          Household viewing patterns
        </h2>
      </div>

      <div className="grid gap-4 md:grid-cols-[1.2fr_0.8fr]">
        <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <div className="mb-4 flex items-center gap-2">
            <div className="flex size-9 items-center justify-center rounded-md bg-red-50 text-red-600">
              <UsersRound className="size-4" />
            </div>
            <h3 className="text-base font-black text-neutral-950">Watch Time By Profile</h3>
          </div>
          <div className="space-y-3">
            {comparisons.profile_watchtime.map((item) => (
              <div key={item.profile}>
                <div className="mb-1 flex items-center justify-between text-sm">
                  <span className="break-words font-bold text-neutral-900">{item.profile}</span>
                  <span className="font-bold text-neutral-950">{item.hrs} hrs</span>
                </div>
                <div className="h-2 rounded-full bg-neutral-100">
                  <div
                    className="h-2 rounded-full bg-red-600"
                    style={{
                      width: `${Math.min(
                        100,
                        (item.hrs / Math.max(...comparisons.profile_watchtime.map((profile) => profile.hrs))) * 100
                      )}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-base font-black text-neutral-950">Most Unique Profile</h3>
          <p className="text-3xl font-black text-neutral-950">
            {comparisons.most_unique_profile?.profile}
          </p>
          <p className="mt-2 text-sm text-neutral-500">
            {comparisons.most_unique_profile?.unique_titles ?? 0} titles no other profile watched.
          </p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 break-words text-base font-black text-neutral-950">Overlap With {comparisons.selected_profile}</h3>
          <div className="space-y-3">
            {comparisons.overlap_scores?.length ? (
              comparisons.overlap_scores.map((item) => (
                <div key={item.profile} className="flex items-center justify-between gap-4">
                  <span className="break-words text-sm font-bold leading-5 text-neutral-900">{item.profile}</span>
                  <span className="text-sm font-bold text-neutral-950">
                    {item.overlap_score}% overlap
                  </span>
                </div>
              ))
            ) : (
              <p className="text-sm text-neutral-500">No other profiles to compare yet.</p>
            )}
          </div>
        </div>

        <div className="rounded-lg border border-neutral-200 bg-white p-4 shadow-sm">
          <h3 className="mb-4 text-base font-black text-neutral-950">Shared Titles</h3>
          <div className="space-y-3">
            {comparisons.shared_titles?.length ? (
              comparisons.shared_titles.slice(0, 8).map((item) => (
                <div key={item.title}>
                  <p className="break-words text-sm font-bold leading-5 text-neutral-900">{item.title}</p>
                  <p className="text-xs text-neutral-500">{item.profiles.join(", ")}</p>
                </div>
              ))
            ) : (
              <p className="text-sm text-neutral-500">No shared titles found.</p>
            )}
          </div>
        </div>
      </div>
    </section>
  );
}
