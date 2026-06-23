/* eslint-disable react/prop-types */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Clapperboard,
  Film,
  ImageOff,
  RefreshCw,
  Sparkles,
  Tv,
} from "lucide-react";
import { netflixAPI } from "@/services/api";

function formatPeriod(start, end) {
  const options = { month: "short", day: "numeric", year: "numeric" };
  return `${new Date(`${start}T00:00:00`).toLocaleDateString([], options)} - ${new Date(
    `${end}T00:00:00`,
  ).toLocaleDateString([], options)}`;
}

function RecommendationPoster({ recommendation }) {
  const [failed, setFailed] = useState(false);

  if (!recommendation.poster_url || failed) {
    return (
      <div className="flex h-full w-full flex-col items-center justify-center gap-2 bg-neutral-100 px-3 text-center text-neutral-500">
        <ImageOff className="h-6 w-6" aria-hidden="true" />
        <span className="text-xs font-bold">Poster unavailable</span>
      </div>
    );
  }

  return (
    <img
      src={recommendation.poster_url}
      alt={`${recommendation.title} poster`}
      className="h-full w-full object-cover"
      loading="lazy"
      onError={() => setFailed(true)}
    />
  );
}

function RecommendationCard({ recommendation }) {
  const TypeIcon = recommendation.media_type === "tv" ? Tv : Film;
  const matchStrength =
    recommendation.rank <= 3
      ? "Best match"
      : recommendation.rank <= 8
        ? "Strong match"
        : recommendation.rank <= 15
          ? "Good match"
          : "Exploratory pick";

  return (
    <article className="grid w-full grid-cols-[7rem_minmax(0,1fr)] overflow-hidden border border-neutral-200 bg-white shadow-sm sm:grid-cols-[9rem_minmax(0,1fr)] lg:grid-cols-[10rem_minmax(0,1fr)_10rem]">
      <div className="aspect-[2/3] w-full bg-neutral-100">
        <RecommendationPoster recommendation={recommendation} />
      </div>

      <div className="flex min-w-0 flex-col p-4 sm:p-5">
        <p className="text-xs font-black uppercase text-red-600">
          Pick {recommendation.rank}
        </p>
        <h4 className="mt-1 break-words text-xl font-black text-neutral-950 sm:text-2xl">
          {recommendation.title}
        </h4>

        <div className="mt-3 flex flex-wrap gap-x-3 gap-y-1 text-xs font-bold text-neutral-500">
          {recommendation.release_year && (
            <span>{recommendation.release_year}</span>
          )}
          {recommendation.genres?.slice(0, 3).map((genre) => (
            <span key={genre}>{genre}</span>
          ))}
          {recommendation.original_language && (
            <span>{recommendation.original_language.toUpperCase()}</span>
          )}
        </div>

        {recommendation.overview && (
          <p className="mt-4 line-clamp-3 text-sm font-medium leading-6 text-neutral-600">
            {recommendation.overview}
          </p>
        )}

        <p className="mt-auto pt-4 text-sm font-bold leading-6 text-neutral-800">
          {recommendation.explanation}
        </p>

        <div className="mt-4 flex items-center gap-2 border-t border-neutral-200 pt-4 text-xs font-black uppercase text-neutral-600 lg:hidden">
          <Sparkles className="h-4 w-4 text-red-600" aria-hidden="true" />
          <span>{matchStrength}</span>
        </div>
      </div>

      <div className="hidden border-l border-neutral-200 bg-neutral-50 p-5 lg:flex lg:flex-col lg:items-center lg:justify-center lg:text-center">
        <div
          className="flex h-11 w-11 items-center justify-center border border-neutral-200 bg-white text-neutral-700"
          title={recommendation.media_type === "tv" ? "TV show" : "Movie"}
        >
          <TypeIcon className="h-5 w-5" aria-hidden="true" />
        </div>
        <p className="mt-3 text-xs font-black uppercase text-neutral-500">
          {recommendation.media_type === "tv" ? "TV show" : "Movie"}
        </p>
        <Sparkles className="mt-7 h-5 w-5 text-red-600" aria-hidden="true" />
        <p className="mt-2 text-sm font-black text-neutral-900">
          {matchStrength}
        </p>
      </div>
    </article>
  );
}

export default function ProfileRecommendations({ profile, isAuthenticated }) {
  const queryClient = useQueryClient();
  const queryKey = ["profileRecommendations", profile];
  const {
    data,
    error,
    isLoading,
  } = useQuery({
    queryKey,
    queryFn: async () => {
      const response = await netflixAPI.getRecommendations(profile);
      return response.data.data;
    },
    enabled: Boolean(profile && isAuthenticated),
    retry: false,
  });
  const refreshMutation = useMutation({
    mutationFn: async () => {
      const response = await netflixAPI.getRecommendations(profile, true);
      return response.data.data;
    },
    onSuccess: (nextData) => {
      queryClient.setQueryData(queryKey, nextData);
    },
  });

  if (!isAuthenticated) {
    return (
      <section className="border border-neutral-200 bg-white p-8 shadow-sm">
        <Sparkles className="h-7 w-7 text-red-600" />
        <h3 className="mt-4 text-2xl font-black text-neutral-950">
          Save your history to get personalized picks
        </h3>
        <p className="mt-3 max-w-2xl text-sm font-semibold leading-6 text-neutral-600">
          Recommendations require a saved profile so watched titles can be excluded
          and your playlist can be refreshed over time.
        </p>
      </section>
    );
  }

  if (isLoading) {
    return (
      <section className="border border-neutral-200 bg-white p-8 shadow-sm">
        <div className="flex items-center gap-3">
          <RefreshCw className="h-5 w-5 animate-spin text-red-600" />
          <p className="font-black text-neutral-900">
            Finding unseen titles for {profile}...
          </p>
        </div>
        <p className="mt-3 text-sm font-semibold text-neutral-600">
          Comparing recent watch patterns with the available catalog.
        </p>
      </section>
    );
  }

  const currentError = refreshMutation.error || error;
  if (currentError && !data) {
    return (
      <section className="border border-red-200 bg-red-50 p-8">
        <h3 className="text-xl font-black text-neutral-950">
          Picks are not available yet
        </h3>
        <p className="mt-3 max-w-2xl text-sm font-semibold leading-6 text-red-800">
          {currentError.response?.data?.error ||
            "The recommendation catalog could not be prepared."}
        </p>
      </section>
    );
  }

  return (
    <section>
      <div className="flex flex-col gap-5 border border-neutral-200 bg-white p-5 shadow-sm md:flex-row md:items-end md:justify-between">
        <div>
          <div className="flex items-center gap-2 text-red-600">
            <Sparkles className="h-5 w-5" />
            <p className="text-sm font-black uppercase">What to watch next</p>
          </div>
          <h3 className="mt-2 text-2xl font-black text-neutral-950">
            Made for {profile}
          </h3>
          <p className="mt-2 max-w-3xl text-sm font-semibold leading-6 text-neutral-600">
            Personalized recommendations based on your recent viewing patterns.
          </p>
          {data && (
            <p className="mt-2 text-xs font-bold text-neutral-500">
              Viewing period: {formatPeriod(data.period_start, data.period_end)}
            </p>
          )}
        </div>
        <button
          type="button"
          onClick={() => refreshMutation.mutate()}
          disabled={refreshMutation.isPending}
          className="inline-flex h-10 shrink-0 items-center justify-center gap-2 bg-neutral-950 px-4 text-sm font-black text-white transition hover:bg-red-600 disabled:cursor-not-allowed disabled:opacity-50"
        >
          <RefreshCw
            className={`h-4 w-4 ${refreshMutation.isPending ? "animate-spin" : ""}`}
          />
          Refresh picks
        </button>
      </div>

      {refreshMutation.error && data && (
        <div className="mt-4 border border-red-200 bg-red-50 p-3 text-sm font-bold text-red-800">
          The current playlist is still available, but it could not be refreshed.
        </div>
      )}

      {data?.recommendations?.length ? (
        <div className="mt-5 flex flex-col gap-4">
          {data.recommendations.map((recommendation) => (
            <RecommendationCard
              key={`${recommendation.media_type}-${recommendation.tmdb_id}`}
              recommendation={recommendation}
            />
          ))}
        </div>
      ) : (
        <div className="mt-5 border border-neutral-200 bg-white p-8 text-center">
          <Clapperboard className="mx-auto h-7 w-7 text-neutral-500" />
          <p className="mt-3 font-black text-neutral-900">
            No unseen matches were found.
          </p>
        </div>
      )}
      <p className="mt-5 border-t border-neutral-200 pt-4 text-xs font-bold leading-5 text-neutral-500">
        Recommendations use an external title catalog. Availability varies by
        region, and some titles may not currently be on Netflix.
      </p>
    </section>
  );
}
