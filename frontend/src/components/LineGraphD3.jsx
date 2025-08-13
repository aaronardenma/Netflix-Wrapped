import { useRef, useEffect } from "react";
import * as d3 from "d3";

export function LineGraphD3({ data, x_axis_key, y_axis_key, x_axis_label, y_axis_label, title }) {
  const svgRef = useRef();

  useEffect(() => {
    if (!data || data.length === 0) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove();

    const width = 600;
    const height = 300;
    const margin = { top: 40, right: 30, bottom: 50, left: 60 };

    // Use viewBox for scalable SVG
    svg.attr("viewBox", `0 0 ${width} ${height}`).attr("preserveAspectRatio", "xMidYMid meet");

    const filteredData = data.filter(d => 
      d[x_axis_key] !== undefined && d[y_axis_key] !== undefined && !isNaN(+d[y_axis_key])
    );

    const x = d3
      .scalePoint()
      .domain(filteredData.map(d => d[x_axis_key]))
      .range([margin.left, width - margin.right]);

    const y = d3
      .scaleLinear()
      .domain([0, d3.max(filteredData, d => +d[y_axis_key])])
      .nice()
      .range([height - margin.bottom, margin.top]);

    const line = d3
      .line()
      .x(d => x(d[x_axis_key]))
      .y(d => y(+d[y_axis_key]))
      .curve(d3.curveMonotoneX);

    // Create tooltip div
    const tooltip = d3.select("body")
      .append("div")
      .attr("class", "tooltip")
      .style("position", "absolute")
      .style("visibility", "hidden")
      .style("background", "rgba(0, 0, 0, 0.8)")
      .style("color", "white")
      .style("padding", "8px")
      .style("border-radius", "4px")
      .style("font-size", "12px")
      .style("pointer-events", "none")
      .style("font-family", "Montserrat, sans-serif")
      .style("z-index", "1000");
      

    // X axis
    svg
      .append("g")
      .attr("transform", `translate(0,${height - margin.bottom})`)
      .call(d3.axisBottom(x))
      .append("text")
      .attr("x", width / 2)
      .attr("y", 35)
      .attr("fill", "black")
      .attr("text-anchor", "middle")
      .style("font-family", "Montserrat, sans-serif")
      .style("font-size", "16px");

    // Y axis
    svg
      .append("g")
      .attr("transform", `translate(${margin.left},0)`)
      .call(d3.axisLeft(y).ticks(5))
      .append("text")
      .attr("transform", "rotate(-90)")
      .attr("y", -45)
      .attr("x", -height / 2)
      .attr("fill", "black")
      .attr("text-anchor", "middle")
      .text(y_axis_label)
      .style("font-family", "Montserrat, sans-serif")
      .style("font-size", "16px");

    // Line path
    svg
      .append("path")
      .datum(filteredData)
      .attr("fill", "none")
      .attr("stroke", "steelblue")
      .attr("stroke-width", 2)
      .attr("d", line);

    // Add visible circles for hover detection
    svg.selectAll(".hover-circle")
      .data(filteredData)
      .enter()
      .append("circle")
      .attr("class", "hover-circle")
      .attr("cx", d => x(d[x_axis_key]))
      .attr("cy", d => y(+d[y_axis_key]))
      .attr("r", 4)
      .attr("fill", "steelblue")
      .attr("stroke", "white")
      .attr("stroke-width", 2)
      .style("cursor", "pointer")
      .on("mouseover", function(event, d) {
        // Show tooltip
        tooltip
          .style("visibility", "visible")
          .html(`<strong>${x_axis_label}:</strong> ${d[x_axis_key]}<br/><strong>${y_axis_label}:</strong> ${(+d[y_axis_key]).toFixed(2)}`);
        
        // Enlarge the hovered circle
        d3.select(this)
          .transition()
          .duration(100)
          .attr("r", 6);
      })
      .on("mousemove", function(event) {
        // Position tooltip near mouse
        tooltip
          .style("left", (event.pageX + 10) + "px")
          .style("top", (event.pageY - 10) + "px");
      })
      .on("mouseout", function() {
        // Hide tooltip
        tooltip.style("visibility", "hidden");
        
        // Return circle to original size
        d3.select(this)
          .transition()
          .duration(100)
          .attr("r", 4);
      });

    // Title
    svg
      .append("text")
      .attr("x", width / 2)
      .attr("y", margin.top / 2)
      .attr("text-anchor", "middle")
      .attr("font-size", "16px")
      .attr("font-weight", "bold")
      .style("font-family", "Montserrat, sans-serif")
      .text(title);


    // Cleanup function to remove tooltip when component unmounts or updates
    return () => {
      d3.select("body").selectAll(".tooltip").remove();
    };
  }, [data, x_axis_key, y_axis_key, x_axis_label, y_axis_label, title]);

  return (
    <svg 
      ref={svgRef} 
      style={{ width: "100%", height: "auto", display: "block" }} 
    />
  );
}