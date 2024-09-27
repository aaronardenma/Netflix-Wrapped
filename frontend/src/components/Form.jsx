import axios from 'axios';
import React, {useState} from 'react';
import { useNavigate } from 'react-router-dom';

function Form({data}) {
    const [userSelected, setUserSelected] = useState("default");
    const [yearSelected, setYearSelected] = useState("default");
    const [userYears, setUserYears] = useState([]);
    const [graphs, setGraphs] = useState({});
    
    const users = Object.keys(data)
    const navigate = useNavigate();

    const handleUserChange = (e) => {
        let user = e.target.value;

        setUserSelected(user);
        setYearSelected("default");
        setUserYears(data[user]);
    }

    const handleYearChange = (e) => {
        setYearSelected(e.target.value);
    }

    const handleSubmit = async (e) => {
        e.preventDefault();
        try {
            const response = await axios.post('http://127.0.0.1:5000/statistics',
                {'user': userSelected,
                    'year': yearSelected
                }, 
                {withCredentials: true}
            );
            setGraphs(response.data);
            console.log(response.data);

            navigate("/statistics", {state: {graphs: response.data}})
        } catch (error) {
            console.error("Error sending user, year data", error);
        }
    }
    
    return (<div>
            <form action="" onSubmit={handleSubmit}>
                <select name="users" id="users__select" defaultValue="default" onChange={handleUserChange}>
                    <option value={userSelected} disabled>Select User</option>
                    {users.map(option => 
                        <option value = {option} key={option}>{option}</option>)}
                </select>
                
                {userSelected != "default" && 
                <select name="user-years" id="user-years__select" value={yearSelected} onChange={handleYearChange}>
                    <option value="default" disabled>Select Year</option>

                    {userYears.map(option => 
                        <option value = {option} key={option}>{option}</option>)}
                </select>}
                
                {yearSelected != "default" &&
                    <button type='submit' className='submit__btn'>Get Stats!</button>}
            </form>
    </div>)
}

export default Form