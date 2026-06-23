/* eslint-disable react/prop-types */
import { Download, Flame, Gauge, Moon, Sparkles, Tv, Zap } from "lucide-react";

const cardDefinitions = [
  ["watching_personality", "Watching Personality", Sparkles],
  ["comfort_show", "Comfort Show", Tv],
  ["peak_couch_hour", "Peak Couch Hour", Moon],
  ["most_chaotic_month", "Most Chaotic Month", Zap],
  ["top_genre_era", "Top Genre Era", Flame],
  ["binge_watcher_percentile", "Binge-Watcher Percentile", Gauge],
];

function wrapCanvasText(ctx, text, x, y, maxWidth, lineHeight, maxLines = 2) {
  const words = String(text || "").split(" ");
  const lines = [];
  let current = "";

  words.forEach((word) => {
    const test = current ? `${current} ${word}` : word;
    if (ctx.measureText(test).width <= maxWidth) {
      current = test;
    } else {
      if (current) lines.push(current);
      current = word;
    }
  });
  if (current) lines.push(current);

  lines.slice(0, maxLines).forEach((line, index) => {
    ctx.fillText(
      index === maxLines - 1 && lines.length > maxLines ? `${line}...` : line,
      x,
      y + index * lineHeight,
    );
  });
}

function exportRecapImage(cards, profile, year) {
  const canvas = document.createElement("canvas");
  canvas.width = 1080;
  canvas.height = 1350;
  const ctx = canvas.getContext("2d");

  ctx.fillStyle = "#121212";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = "#e50914";
  ctx.fillRect(0, 0, canvas.width, 22);
  ctx.fillRect(0, canvas.height - 22, canvas.width, 22);

  ctx.fillStyle = "#ffffff";
  ctx.font = "900 58px Montserrat, Arial, sans-serif";
  ctx.fillText(`${profile || "Netflix"} Wrapped`, 72, 120);
  ctx.font = "700 28px Montserrat, Arial, sans-serif";
  ctx.fillStyle = "#d4d4d4";
  ctx.fillText(year === "all" ? "All years recap" : `${year} recap`, 72, 165);

  const share = cards.shareable_recap || {};
  ctx.fillStyle = "#e50914";
  ctx.fillRect(72, 205, 936, 130);
  ctx.fillStyle = "#ffffff";
  ctx.font = "900 42px Montserrat, Arial, sans-serif";
  ctx.fillText(`${share.total_watchtime_hours || 0} hours`, 104, 260);
  ctx.font = "700 25px Montserrat, Arial, sans-serif";
  ctx.fillText(`${share.unique_titles || 0} unique titles watched`, 104, 302);

  cardDefinitions.forEach(([key, label], index) => {
    const card = cards[key] || {};
    const col = index % 2;
    const row = Math.floor(index / 2);
    const x = 72 + col * 488;
    const y = 390 + row * 270;

    ctx.fillStyle = "#ffffff";
    ctx.fillRect(x, y, 448, 220);
    ctx.fillStyle = "#e50914";
    ctx.fillRect(x, y, 10, 220);

    ctx.fillStyle = "#737373";
    ctx.font = "800 21px Montserrat, Arial, sans-serif";
    ctx.fillText(label.toUpperCase(), x + 32, y + 48);
    ctx.fillStyle = "#111111";
    ctx.font = "900 34px Montserrat, Arial, sans-serif";
    wrapCanvasText(
      ctx,
      card.value || "Not enough data",
      x + 32,
      y + 100,
      372,
      39,
      2,
    );
    ctx.fillStyle = "#525252";
    ctx.font = "600 21px Montserrat, Arial, sans-serif";
    wrapCanvasText(ctx, card.description || "", x + 32, y + 178, 372, 27, 2);
  });

  ctx.fillStyle = "#a3a3a3";
  ctx.font = "700 22px Montserrat, Arial, sans-serif";
  ctx.fillText("Created with Netflix Wrapped", 72, 1280);

  const link = document.createElement("a");
  link.download = `netflix-wrapped-${profile || "recap"}-${year || "all"}.png`;
  link.href = canvas.toDataURL("image/png");
  link.click();
}

function WrappedCard({ icon: Icon, label, card }) {
  if (!card) return null;

  return (
    <div className="rounded-lg border border-neutral-200 bg-white p-5 shadow-sm">
      <div className="mb-5 flex items-center justify-between gap-3">
        <div className="flex size-10 items-center justify-center rounded-md bg-red-50 text-red-600">
          <Icon className="size-5" />
        </div>
        <p className="text-xs font-black uppercase text-neutral-400">{label}</p>
      </div>
      <h3 className="break-words text-xl font-black leading-tight text-neutral-950 sm:text-2xl">
        {card.value}
      </h3>
      <p className="mt-3 text-sm leading-6 text-neutral-600">
        {card.description}
      </p>
    </div>
  );
}

export default function WrappedCards({ cards, profile, year }) {
  if (!cards) return null;

  return (
    <section className="space-y-4">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-sm font-bold uppercase text-red-600">
            Wrapped Cards
          </p>
          <h2 className="mt-1 text-xl font-black tracking-normal text-neutral-950 sm:text-2xl">
            Your shareable recap highlights
          </h2>
        </div>
        <button
          type="button"
          onClick={() => exportRecapImage(cards, profile, year)}
          className="inline-flex w-full cursor-pointer items-center justify-center gap-2 rounded-md bg-neutral-950 px-4 py-3 text-sm font-bold text-white transition hover:bg-neutral-800 sm:w-auto"
        >
          <Download className="size-4" />
          Export recap PNG
        </button>
      </div>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
        {cardDefinitions.map(([key, label, Icon]) => (
          <WrappedCard key={key} icon={Icon} label={label} card={cards[key]} />
        ))}
      </div>
    </section>
  );
}
