import React from 'react';
import { LineChart, Line, CartesianGrid, XAxis, YAxis, Tooltip, Label } from 'recharts';
import { useLocation } from 'react-router-dom';

function Statistics() {
    const location = useLocation();
    const {graphs} = location.state || {};

    if (!graphs) {
        return <div>No graph data available</div>; // Show a message if no data
    }

    const testGraphDataX = graphs['monthly_watchtime']['months'];
    const testGraphDataY = graphs['monthly_watchtime']['watchtime'];
    const months = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC'];

    const makeData = () => {
        const data = []
        for (let i=0; i < testGraphDataX.length; i++) {
            data.push({
                name: months[i],
                hrs: testGraphDataY[i]
            });
        };

        return data;
    }

    const data = makeData();

    return (
        <div className='graph__cell'>
            <h2 >Monthly Watchtime</h2>
            <LineChart width={600} height={300} data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
                <Line type="monotone" dataKey="hrs" stroke="#8884d8" />
                <CartesianGrid stroke="#ccc" strokeDasharray="5 5" />
                <XAxis dataKey="name">
                    <Label value="Months" offset={-5} position="insideBottom" /> {/* X Axis Label */}
                    </XAxis>

                <YAxis>
                    <Label value="Hours" angle={-90} position="insideLeft" style={{ textAnchor: 'middle' }} /> {/* Y Axis Label */}
                </ YAxis>
                <Tooltip />
            </LineChart>
            
        </div>
    )
}

export default Statistics