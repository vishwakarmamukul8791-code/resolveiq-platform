import Landing from './pages/Landing';
import SupportDashboard from './pages/SupportDashboard';
import AdminDashboard from './pages/AdminDashboard';
import NotFound from './pages/NotFound';
import { Routes, Route } from "react-router-dom";

function App() {
  
  return (
    <Routes>
    <Route path="/" element={<Landing/>} />
    <Route path="/admin" element={<AdminDashboard/>} />
    <Route path="/support" element={<SupportDashboard/>} />
    <Route path="*" element={<NotFound/>}/>
   </Routes>
    
  )
           
}

export default App
