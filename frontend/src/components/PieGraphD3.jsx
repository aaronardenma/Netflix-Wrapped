import { useRef, useEffect, useState } from "react";
import * as d3 from "d3";

export function PieGraphD3({ data, metric, category_key, title }) {
  const svgRef = useRef();
  const tooltipRef = useRef();

  const [selectedIndex, setSelectedIndex] = useState(null);

  useEffect(() => {
    if (!data) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    // Create tooltip div if it doesn't exist
    let tooltip = d3.select(tooltipRef.current);
    if (tooltip.empty()) {
      tooltip = d3
        .select("body")
        .append("div")
        .attr("class", "pie-tooltip")
        .style("position", "absolute")
        .style("pointer-events", "none")
        .style("opacity", 0)
        .style("background", "rgba(0,0,0,0.7)")
        .style("color", "#fff")
        .style("padding", "6px 10px")
        .style("font-family", "Montserrat, sans-serif")
        .style("border-radius", "4px")
        .style("font-size", "12px");
      tooltipRef.current = tooltip.node();
    }

    const width = 600;
    const height = 300;
    const titleHeight = 30;
    const legendWidth = 150;
    const radius = Math.min(width - legendWidth, height - titleHeight * 2) / 2;
    const gap = 20;
const combinedWidth = radius * 2 + gap + legendWidth;

// Center combined block horizontally inside SVG width
const offsetX = (width - combinedWidth) / 2;

const pieCenterX = offsetX + radius;
const pieCenterY = height / 2 + titleHeight / 2;

const legendX = pieCenterX + radius + gap;
const legendY = titleHeight + 20;

const g = svg
  .append("g")
  .attr("transform", `translate(${pieCenterX},${pieCenterY})`);


    svg.attr("width", width).attr("height", height);


    const color = d3.scaleOrdinal(d3.schemePaired);

    const pie = d3
      .pie()
      .value((d) => d[metric])
      .sort(null);

    const path = d3
      .arc()
      .outerRadius(radius - 10)
      .innerRadius(0);

    const labelArc = d3
      .arc()
      .outerRadius(radius * 0.6)
      .innerRadius(radius * 0.5);

    const arcs = g
      .selectAll(".arc")
      .data(pie(data))
      .join("g")
      .attr("class", "arc");

    const total = d3.sum(data, (d) => d[metric]);

    arcs
      .append("path")
      .attr("d", path)
      .attr("fill", (d, i) =>
        selectedIndex === i ? d3.color(color(i)).brighter(0.7) : color(i)
      )
      .style("cursor", "pointer")
      .on("mouseover", function (event, d) {
        const index = arcs.nodes().indexOf(this.parentNode);
        d3.select(this).attr("fill", d3.color(color(index)).brighter(0.7));

        tooltip
          .style("opacity", 1)
          .html(`<strong>${d.data[category_key]}</strong>`);
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", event.pageX + 10 + "px")
          .style("top", event.pageY - 28 + "px");
      })
      .on("mouseout", function (event, d) {
        const index = arcs.nodes().indexOf(this.parentNode);
        d3.select(this).attr(
          "fill",
          selectedIndex === index ? d3.color(color(index)).brighter(0.7) : color(index)
        );
        tooltip.style("opacity", 0);
      })
      .on("click", function (event, d) {
        const index = arcs.nodes().indexOf(this.parentNode);
        setSelectedIndex(selectedIndex === index ? null : index);
      });

    arcs.attr("transform", (d, i) => {
      if (selectedIndex === i) {
        const midAngle = (d.startAngle + d.endAngle) / 2;
        const x = 10 * Math.cos(midAngle);
        const y = 10 * Math.sin(midAngle);
        return `translate(${x},${y})`;
      }
      return "translate(0,0)";
    });

    // Percentage labels on slices
    arcs
      .append("text")
      .attr("transform", (d) => `translate(${labelArc.centroid(d)})`)
      .attr("dy", "0.35em")
      .style("font-family", "Montserrat, sans-serif")
      .attr("font-size", "12px")
      .attr("font-weight", "bold")
      .attr("text-anchor", "middle")
      .style("pointer-events", "none")
      .text((d) => {
        const percent = ((d.data[metric] / total) * 100).toFixed(1);
        return `${percent}%`;
      });

    // Title
    svg
      .append("text")
      .attr("x", width / 2)
      .attr("y", titleHeight / 1.5)
      .style("font-family", "Montserrat, sans-serif")
      .attr("font-size", "20px")
      .attr("font-weight", "bold")
      .attr("text-anchor", "middle")
      .text(title);

    // Legend on right side
    const legend = svg
  .append("g")
  .attr("transform", `translate(${legendX}, ${legendY})`);

    const legendItemHeight = 25;

    const legendItems = legend
      .selectAll(".legend-item")
      .data(data)
      .join("g")
      .attr("class", "legend-item")
      .attr("transform", (_, i) => `translate(0, ${i * legendItemHeight})`);

    legendItems
      .append("rect")
      .attr("width", 18)
      .attr("height", 18)
      .attr("fill", (_, i) => color(i));

    legendItems
      .append("text")
      .attr("x", 24)
      .attr("y", 9)
      .attr("dy", "0.35em")
      .style("font-family", "Montserrat, sans-serif")
      .attr("font-size", "14px")
      .text((d) => {
        return `${d[category_key]}`;
      });
  }, [data, metric, category_key, title, selectedIndex]);

  return <svg ref={svgRef} />;
}
