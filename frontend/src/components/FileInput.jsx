import axios from 'axios';
import React, {useState} from 'react';

function FileInput() {

    const [file, setFile] = useState(null);
    const [graph, setGraph] = useState({});
    const [usersYearsData, setUsersYearsData] = useState(null);

    const uploadFile = (e) => {
        setFile(e.target.files[0]);
        console.log("uploaded file!");
    }

    const handleSubmit = async (e) => {
        e.preventDefault();

        const csvFile = new FormData();
        csvFile.append('csv_data', file);

        try {
            const response = await axios.post('http://127.0.0.1:5000/upload', csvFile, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            console.log(response.data);
            setGraph(response.data); // Update the state if needed
        } catch (error) {
            console.error("Error uploading file", error);
        }
        
        console.log("sent!");
    }

    // const graphItems = graph.map(g => <li>{g}</li>)
    
    return (
        <>
            <div className="container">
                <form className="file__upload" action='/statistics' method="post" encType="multipart/form-data" onSubmit={handleSubmit}>
                    <input type="file" className="file__input" name = "csv_data" accept=".csv" onChange={uploadFile} />
                    <br></br>
                    <button type="submit" className="submit__btn" >Upload</button>
                </form>
            </div>
        </>
    );
}

export default FileInput