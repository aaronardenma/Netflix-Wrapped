import { useRef, useEffect } from "react";
import * as d3 from "d3";

export function BarGraphD3({
  data,
  x_axis_key,
  y_axis_key,
  y_axis_label,
  title,
}) {
  const svgRef = useRef();
  const tooltipRef = useRef();

  useEffect(() => {
    if (!data) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Tooltip setup
    let tooltip = d3.select(tooltipRef.current);
    if (tooltip.empty()) {
      tooltip = d3
        .select("body")
        .append("div")
        .attr("class", "tooltip")
        .style("position", "absolute")
        .style("pointer-events", "none")
        .style("opacity", 0)
        .style("background", "rgba(0,0,0,0.7)")
        .style("color", "#fff")
        .style("padding", "6px 10px")
        .style("border-radius", "4px")
        .style("font-family", "Montserrat, sans-serif")
        .style("font-size", "12px");
      tooltipRef.current = tooltip.node();
    }

    const width = 600;
    const height = 600;
    const margin = { top: 40, right: 30, bottom: 50, left: 100 }; // wider left margin for y-axis labels

    const color = d3
      .scaleOrdinal(d3.schemePaired)
      .domain(data.map((d) => d[x_axis_key]));

    svg
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("preserveAspectRatio", "xMidYMid meet")
      .style("font-family", "Montserrat, sans-serif");

    // Scales
    const tempText = svg.append("text").attr("font-size", "12px").attr("visibility", "hidden");
let maxLabelWidth = 0;
data.forEach(d => {
  tempText.text(d[x_axis_key]);
  const bbox = tempText.node().getBBox();
  if (bbox.width > maxLabelWidth) maxLabelWidth = bbox.width;
});
tempText.remove();

// Adjust left margin
margin.left = Math.max(margin.left, maxLabelWidth + 10);

// Y scale
const y = d3.scaleBand()
  .domain(data.map(d => d[x_axis_key]))
  .range([margin.top, height - margin.bottom])
  .padding(0.2);

// X scale
const x = d3.scaleLinear()
  .domain([0, d3.max(data, d => +d[y_axis_key])])
  .nice()
  .range([margin.left, width - margin.right]);


    // Y-axis
    const yAxisG = svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y))
      .selectAll("text")
      .attr("font-size", "12px");

    // X-axis
    const xAxisG = svg
      .append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x).ticks(5));

    // Bars
    svg
      .selectAll("rect")
      .data(data)
      .join("rect")
      .attr("y", (d) => y(d[x_axis_key]))
      .attr("x", margin.left)
      .attr("height", y.bandwidth())
      .attr("width", (d) => x(d[y_axis_key]) - margin.left)
      .attr("fill", (d) => color(d[x_axis_key]))
      .on("mouseover", (event, d) => {
        d3.select(event.currentTarget).attr("fill", d3.color(color(d[x_axis_key])).brighter(0.8));
        tooltip.transition().duration(200).style("opacity", 1);
        tooltip
          .html(`<strong>${x_axis_key}:</strong> ${d[x_axis_key]}<br><strong>${y_axis_key}:</strong> ${d[y_axis_key]}`)
          .style("left", `${event.pageX + 10}px`)
          .style("top", `${event.pageY - 28}px`);
      })
      .on("mousemove", (event) => {
        tooltip.style("left", `${event.pageX + 10}px`).style("top", `${event.pageY - 28}px`);
      })
      .on("mouseout", (event, d) => {
        d3.select(event.currentTarget).attr("fill", color(d[x_axis_key]));
        tooltip.transition().duration(500).style("opacity", 0);
      });

    // Centered x-axis label (numerical)
    svg
      .append("text")
      .attr("x", margin.left + (width - margin.left - margin.right) / 2)
      .attr("y", height - 10)
      .attr("text-anchor", "middle")
      .style("font-family", "Montserrat, sans-serif")
      .style("font-size", "14px")
      .text(y_axis_label);

    // Title
    svg
      .append("text")
      .attr("x", width / 2)
      .attr("y", margin.top / 2)
      .attr("text-anchor", "middle")
      .attr("font-size", "16px")
      .attr("font-weight", "bold")
      .text(title);
  }, [data, x_axis_key, y_axis_key, y_axis_label, title]);

  return <svg ref={svgRef} style={{ width: "100%", height: "auto" }} />;
}
