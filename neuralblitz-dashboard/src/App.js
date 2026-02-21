import React, { useState, useEffect } from 'react';
import './styles/App.css';
import AgentMonitoring from './components/AgentMonitoring';
import DimensionalComputing from './components/DimensionalComputing';
import EthicsCompliance from './components/EthicsCompliance';
import DashboardHeader from './components/DashboardHeader';
import RealTimeMetrics from './components/RealTimeMetrics';
import { Activity, Box, Shield } from 'lucide-react';

function App() {
  const [activeTab, setActiveTab] = useState('overview');
  const [systemStatus, setSystemStatus] = useState({
    status: 'ACTIVE',
    version: 'v20.0 Apical Synthesis',
    epoch: 'ΩZ',
    vpce: 0.992,
    driftRate: 0.007,
    riskLevel: 'LOW',
    entropyBudget: 0.11,
    lastUpdate: new Date().toISOString()
  });

  useEffect(() => {
    // Simulate real-time updates
    const interval = setInterval(() => {
      setSystemStatus(prev => ({
        ...prev,
        vpce: Math.min(1, Math.max(0.95, prev.vpce + (Math.random() - 0.5) * 0.01)),
        driftRate: Math.max(0, prev.driftRate + (Math.random() - 0.5) * 0.002),
        entropyBudget: Math.max(0, Math.min(1, prev.entropyBudget + (Math.random() - 0.5) * 0.05)),
        lastUpdate: new Date().toISOString()
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="app">
      <DashboardHeader systemStatus={systemStatus} />
      
      <div className="dashboard-container">
        <nav className="dashboard-nav">
          <button 
            className={`nav-btn ${activeTab === 'overview' ? 'active' : ''}`}
            onClick={() => setActiveTab('overview')}
          >
            <Activity size={20} />
            <span>Overview</span>
          </button>
          <button 
            className={`nav-btn ${activeTab === 'agents' ? 'active' : ''}`}
            onClick={() => setActiveTab('agents')}
          >
            <Box size={20} />
            <span>Agent Monitoring</span>
          </button>
          <button 
            className={`nav-btn ${activeTab === 'dimensional' ? 'active' : ''}`}
            onClick={() => setActiveTab('dimensional')}
          >
            <Box size={20} />
            <span>Dimensional Computing</span>
          </button>
          <button 
            className={`nav-btn ${activeTab === 'ethics' ? 'active' : ''}`}
            onClick={() => setActiveTab('ethics')}
          >
            <Shield size={20} />
            <span>Ethics Compliance</span>
          </button>
        </nav>

        <main className="dashboard-content">
          {activeTab === 'overview' && (
            <div className="overview-grid">
              <RealTimeMetrics systemStatus={systemStatus} />
              <AgentMonitoring compact />
              <DimensionalComputing compact />
              <EthicsCompliance compact />
            </div>
          )}
          {activeTab === 'agents' && <AgentMonitoring />}
          {activeTab === 'dimensional' && <DimensionalComputing />}
          {activeTab === 'ethics' && <EthicsCompliance />}
        </main>
      </div>
    </div>
  );
}

export default App;