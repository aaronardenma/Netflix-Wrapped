import {BrowserRouter, Routes, Route} from "react-router-dom"
import NavBar from "./components/NavBar"
import Home from "./pages/Home"
import Upload from "./pages/Upload"
import Contact from "./pages/Contact"
import Statistics from "./pages/Statistics"

function App() {
  return (
    <BrowserRouter>
      <NavBar />
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/upload" element={<Upload />}/>
        <Route path="/statistics" element={<Statistics />} />
        <Route path="/contact" element={<Contact />}/>
      </Routes>
    </BrowserRouter>
  )
}

export default App