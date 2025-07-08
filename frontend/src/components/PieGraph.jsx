import React from "react";
import { ResponsiveContainer, PieChart, Pie, XAxis, YAxis, Label, Tooltip } from 'recharts';

function PieGraph({data, metric, category_key, title}) {
    const RADIAN = Math.PI / 180;
    const renderCustomizedLabel = ({ cx, cy, midAngle, innerRadius, outerRadius, percent, index }) => {
        const radius = innerRadius + (outerRadius - innerRadius) * 0.5;
        const x = cx + radius * Math.cos(-midAngle * RADIAN);
        const y = cy + radius * Math.sin(-midAngle * RADIAN);
      
        return (
          <text x={x} y={y} fill="white" textAnchor={x > cx ? 'start' : 'end'} dominantBaseline="central">
            {`${(percent * 100).toFixed(0)}%`}
          </text>
        );
      };

    return (
        <>
        <h2 style={{color: 'white'}}>{title}</h2>
        <ResponsiveContainer width={600} height={300} >
            <PieChart>
                <Pie data={data} cx="50%" cy="50%" labelLine={false} dataKey={metric} nameKey={category_key} fill="#82ca9d" label={renderCustomizedLabel} />
                <Tooltip />
            </PieChart>
        </ResponsiveContainer>
        </>
    )
}

export default PieGraph