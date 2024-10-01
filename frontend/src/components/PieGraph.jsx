import React from "react";
import { ResponsiveContainer, PieChart, Pie, XAxis, YAxis, Label, Tooltip } from 'recharts';

function PieGraph({data, metric, category_key, title}) {
    return (
        <>
        <h2 style={{color: 'white'}}>{title}</h2>
        <ResponsiveContainer width={600} height={300} >
            <PieChart>
                <Pie data={data} dataKey={metric} nameKey={category_key} fill="#82ca9d" label />
                <Tooltip />
            </PieChart>
        </ResponsiveContainer>
        </>
    )
}

export default PieGraph