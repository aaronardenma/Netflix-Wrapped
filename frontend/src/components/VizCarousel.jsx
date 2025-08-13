import { useState } from "react";
import { BarGraphD3 } from "../components/BarGraphD3";
import { LineGraphD3 } from "../components/LineGraphD3";
import { PieGraphD3 } from "../components/PieGraphD3";
import { MdOutlineArrowBackIos } from "react-icons/md";
import { MdOutlineArrowForwardIos } from "react-icons/md";


export default function VizCarousel({ graphs, profile, year }) {
  const [currentIndex, setCurrentIndex] = useState(0);
  const [fade, setFade] = useState(true);

  const graphComponents = [
    <LineGraphD3
      key="line"
      data={graphs.monthly_watchtime}
      x_axis_key="month"
      y_axis_key="hrs"
      x_axis_label="Months"
      y_axis_label="Watchtime (hrs)"
      title="Monthly Watchtime"
    />,
    <BarGraphD3
      key="bar"
      data={graphs.total_title_watchtime}
      x_axis_key="title"
      x_axis_label="Content"
      y_axis_key="hrs"
      y_axis_label="Watchtime (hrs)"
      title="Top 10 Watched Content"
    />,
    <PieGraphD3
      key="pie"
      data={graphs.total_type_watchtime}
      metric="hrs"
      category_key="type"
      title="Content Type Breakdown"
    />,
  ];

  const changeIndex = (newIndex) => {
    setFade(false);
    setTimeout(() => {
      setCurrentIndex(newIndex);
      setFade(true);
    }, 150);
  };

  const prev = () => {
    if (currentIndex > 0) {
      changeIndex(currentIndex - 1);
    }
  };

  const next = () => {
    if (currentIndex < graphComponents.length - 1) {
      changeIndex(currentIndex + 1);
    }
  };

  return (
    <div className="flex flex-col items-center">

      <div className="relative w-full max-w-4xl flex justify-center">
        {/* Graph container, flexible height */}
        <div
          className={`transition-opacity duration-150 ${fade ? "opacity-100" : "opacity-0"}`}
          style={{ width: "100%" }}
        >
          <div className="bg-card shadow-sm rounded-lg p-4 mx-auto max-w-3xl flex justify-center">
            {graphComponents[currentIndex]}
          </div>
        </div>

        {/* Fixed position buttons */}
        {currentIndex > 0 && (
          <button
            onClick={prev}
            aria-label="Previous graph"
            className="fixed left-4 -translate-y-1/2 rounded-full p-2 cursor-pointer bg-gray-200/90 shadow z-50 top-2/5"
          >
            <MdOutlineArrowBackIos />
          </button>
        )}

        {currentIndex < graphComponents.length - 1 && (
          <button
            onClick={next}
            aria-label="Next graph"
            className="fixed right-4 -translate-y-1/2 rounded-full p-2 cursor-pointer bg-gray-200/90 shadow z-50 top-2/5"
          >
            <MdOutlineArrowForwardIos />
          </button>
        )}
      </div>

      <div className="flex space-x-2 mt-4">
        {graphComponents.map((_, i) => (
          <button
            key={i}
            className={`w-3 h-3 rounded-full ${
              i === currentIndex ? "bg-primary" : "bg-gray-300"
            }`}
            onClick={() => changeIndex(i)}
            aria-label={`Select graph ${i + 1}`}
          />
        ))}
      </div>
    </div>
  );
}
