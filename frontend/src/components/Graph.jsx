import React from 'react';
import Plot from 'react-plotly.js';

function Graph({data, layout}) {
    return (
        <Plot data = {data} layout = {layout} />
    )
}

export default Graph