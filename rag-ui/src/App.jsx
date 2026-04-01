import { useState, useEffect } from "react";
import { Routes, Route } from "react-router-dom";
import "./App.css";

// Components
import Sidebar from "./components/Sidebar";
import TopNav from "./components/TopNav";

// Pages
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import DocumentAnalysis from "./pages/DocumentAnalysis";
import Reports from "./pages/Reports";
import Analytics from "./pages/Analytics";

function App() {
  const [currentDocId, setCurrentDocId] = useState(null);
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("ragforge-theme") || "light";
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ragforge-theme", theme);
  }, [theme]);

  const toggleTheme = () => {
    setTheme((prev) => (prev === "light" ? "dark" : "light"));
  };

  const handleUploadSuccess = (docId) => {
    setCurrentDocId(docId);
  };

  return (
    <div className="app-layout">
      {/* ===== SHARED SIDEBAR ===== */}
      <Sidebar currentDocId={currentDocId} />

      {/* ===== MAIN AREA ===== */}
      <div className="main-area">
        {/* Top Navbar */}
        <TopNav theme={theme} toggleTheme={toggleTheme} />

        {/* Content with Routing */}
        <main className="content">
          <Routes>
            <Route 
              path="/" 
              element={<Dashboard onUploadSuccess={handleUploadSuccess} />} 
            />
            <Route 
              path="/reports" 
              element={<Reports />} 
            />
            <Route 
              path="/analytics" 
              element={<Analytics />} 
            />
            <Route 
              path="/documents" 
              element={<Documents />} 
            />
            <Route 
              path="/documents/:id" 
              element={<DocumentAnalysis />} 
            />
          </Routes>
        </main>
      </div>
    </div>
  );
}

export default App;