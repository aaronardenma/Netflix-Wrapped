import React from 'react';
import { Pie, Tooltip, PieChart } from 'recharts';
import { useLocation, useNavigate } from 'react-router-dom';
import LineGraph from '../components/LineGraph';
import BarGraph from '../components/BarGraph';
import PieGraph from '../components/PieGraph';

function Statistics() {
    const location = useLocation();
    const {graphs} = location.state || {};

    const navigate = useNavigate();

    if (!graphs) {
        return <div>No graph data available</div>; // Show a message if no data
    }

    const monthlyWatchtimeData = graphs['monthly_watchtime']
    const titleWatchtimeData = graphs['total_title_watchtime']
    const typeWatchtimeData = graphs['total_type_watchtime']
    const ratingWatchtimeData = graphs['ratings_watchtime']

    const handleBackClick = () => {
        navigate("/upload");
    };

    return (
        <>
        
            <button>Choose New User</button>
            <form action="">
                <select name="" id="" defaultValue='default'>
                    <option value="default" disable>Choose new Year:</option>
                    <option value="default" >year 1</option>
                    <option value="default" >year 2</option>
                </select>
            </form>
            <div className="graph__container">
                <div className='graph__cell'>
                    <LineGraph data={monthlyWatchtimeData} x_axis_key='month' x_axis_label='Months' y_axis_label='Watchtime (hrs)' title="Monthly Watchtime" />
                </div>
                <div className="graph__cell">
                    <BarGraph data={titleWatchtimeData} x_axis_key='title' x_axis_label='Title' y_axis_key='hrs' y_axis_label='Watchtime (hrs)' title="Top 10 Watched Content" />
                </div>
                <div className="graph__cell">
                    <PieGraph data={typeWatchtimeData} metric='hrs' category_key='type' title="Content Type Breakdown"/>
                </div>
            </div>
        <button onClick={handleBackClick}>Back</button>
        </>
    )
}

export default Statistics