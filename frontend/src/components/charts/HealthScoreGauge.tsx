import { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface HealthScoreGaugeProps {
  score: number | null;
  size?: number;
}

export function HealthScoreGauge({ score, size = 200 }: HealthScoreGaugeProps) {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || score === null) return;

    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();

    const width = size;
    const height = size;
    const radius = Math.min(width, height) / 2 - 20;
    const innerRadius = radius * 0.7;

    const g = svg
      .append('g')
      .attr('transform', `translate(${width / 2}, ${height / 2})`);

    // Background arc
    const backgroundArc = d3.arc<unknown>()
      .innerRadius(innerRadius)
      .outerRadius(radius)
      .startAngle(-Math.PI / 2)
      .endAngle(Math.PI / 2);

    g.append('path')
      .attr('d', backgroundArc({}) as string)
      .attr('fill', '#e5e7eb');

    // Score arc
    const scoreAngle = ((score / 100) * Math.PI) - (Math.PI / 2);
    const scoreArc = d3.arc<unknown>()
      .innerRadius(innerRadius)
      .outerRadius(radius)
      .startAngle(-Math.PI / 2)
      .endAngle(scoreAngle);

    // Color based on score
    const color = score >= 80 ? '#10b981' : score >= 60 ? '#f59e0b' : '#ef4444';

    g.append('path')
      .attr('d', scoreArc({}) as string)
      .attr('fill', color);

    // Score text
    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '0.1em')
      .attr('font-size', '2.5rem')
      .attr('font-weight', 'bold')
      .attr('fill', color)
      .text(Math.round(score));

    g.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', '2em')
      .attr('font-size', '0.875rem')
      .attr('fill', '#6b7280')
      .text('Health Score');

  }, [score, size]);

  if (score === null) {
    return (
      <div className="flex items-center justify-center" style={{ width: size, height: size }}>
        <span className="text-gray-400">No data</span>
      </div>
    );
  }

  return <svg ref={svgRef} width={size} height={size} />;
}
