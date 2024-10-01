import React from "react";
import { BarChart, Bar, XAxis, YAxis, Label, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'

function BarGraph({data, x_axis_key, y_axis_key, x_axis_label, y_axis_label, title}) {
    return (
        <>
            <h2 style={{color: 'white'}}>{title}</h2>
            <ResponsiveContainer width={600} height={300}>
                <BarChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey={x_axis_key} angle={-90}>
                        <Label value={x_axis_label} offset={-5} position="insideBottom" />
                    </XAxis>
                    <YAxis dataKey={y_axis_key} >
                        <Label value={y_axis_label} angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
                    </YAxis>
                    <Tooltip />
                    <Bar dataKey={y_axis_key} fill="red" />
                </BarChart>
            </ResponsiveContainer>
        </>
    )
}

export default BarGraph