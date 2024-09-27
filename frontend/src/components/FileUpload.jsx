import axios from 'axios';
import React, {useState} from 'react';
import Form from './Form'

function FileUpload() {
    const [file, setFile] = useState(null);
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
            const response = await axios.post('http://127.0.0.1:5000/upload', csvFile, {withCredentials: true});
            console.log(response.data);
            setUsersYearsData(response.data); // Update the state if needed
        } catch (error) {
            console.error("Error uploading file", error);
        }
        
        console.log("received user and year data!");
    }
    
    return (
        <>
            <div className="container">
                <form className="file__upload" method="post" encType="multipart/form-data" onSubmit={handleSubmit}>
                    <input type="file" className="file__input" name = "csv_data" accept=".csv" onChange={uploadFile} />
                    <br></br>
                    <button type="submit" className="submit__btn" >Upload</button>
                </form>
            </div>
            {usersYearsData != null && <Form data={usersYearsData}/>}

        </>
    );
}

export default FileUpload