import React from 'react';
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Label, ResponsiveContainer } from 'recharts';


function LineGraph({data, x_axis_key, x_axis_label, y_axis_label, title}) {
    return (
        <>
            <h2 style={{color: 'white'}}>{title}</h2>   
            <ResponsiveContainer width={600} height={300}>
                    <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                        <Line type="monotone" dataKey="hrs" stroke="red" />
                        <CartesianGrid stroke="#ccc" strokeDasharray="5 5" />
                        <XAxis dataKey={x_axis_key}>
                            <Label value={x_axis_label} offset={-5} position="insideBottom" />
                            </XAxis>

                        <YAxis>
                            <Label value={y_axis_label} angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} />
                        </YAxis>
                        <Tooltip />
                    </LineChart>
            </ResponsiveContainer>
    </>
    )
    
}

export default LineGraph