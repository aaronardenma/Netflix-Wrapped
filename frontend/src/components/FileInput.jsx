import axios from 'axios';
import React, {useState} from 'react';


function FileInput() {

    const [file, setFile] = useState(null);
    const [graph, setGraph] = useState([]);

    const uploadFile = (e) => {
        setFile(e.target.files[0]);
        console.log("uploaded file!");
    }

    const handleSubmit = async (e) => {
        e.preventDefault();

        const file = new FormData();
        file.append('csv_data', file);

        axios({
            method: 'post',
            url: '/upload',
            data: file,
            headers: { "Content-Type": "multipart/form-data" }
        })
        .then(function (response) {
            console.log(response);
        })
        .catch(function (error) {
            console.log(error);
        });
        
        console.log("sent!");
    }

    const graphItems = graph.map(g => <li>{g}</li>)
    
    return (
        <>
            <div className="container">
                <form className="file__upload" action="/upload" method="post" encType="multipart/form-data" onSubmit={handleSubmit}>
                    <input type="file" className="file__input" name = "csv_data" accept=".csv" onChange={uploadFile} />
                    <br></br>
                    <button type="submit" className="submit__btn">Upload</button>
                </form>
            </div>
        </>
    );
}

export default FileInput