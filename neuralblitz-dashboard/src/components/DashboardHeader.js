import React from 'react';
import { Activity, Cpu, Shield, Zap } from 'lucide-react';

const DashboardHeader = ({ systemStatus }) => {
  const formatValue = (val, decimals = 3) => {
    return typeof val === 'number' ? val.toFixed(decimals) : val;
  };

  return (
    <header className="dashboard-header">
      <div className="header-brand">
        <div className="header-logo">NB</div>
        <div className="header-title">
          <h1>NeuralBlitz Dashboard</h1>
          <p>Σ-class Symbiotic Ontological Intelligence • {systemStatus.version}</p>
        </div>
      </div>

      <div className="header-status">
        <div className="status-indicator">
          <span className="status-dot"></span>
          <span>{systemStatus.status}</span>
        </div>

        <div className="metrics-quick-view">
          <div className="metric-pill">
            <span className="metric-label">VPCE</span>
            <span className="metric-value">{formatValue(systemStatus.vpce)}</span>
          </div>
          <div className="metric-pill">
            <span className="metric-label">Drift</span>
            <span className="metric-value">{formatValue(systemStatus.driftRate, 4)}</span>
          </div>
          <div className="metric-pill">
            <span className="metric-label">Entropy</span>
            <span className="metric-value">{formatValue(systemStatus.entropyBudget, 2)}</span>
          </div>
          <div className="metric-pill">
            <span className="metric-label">Risk</span>
            <span className="metric-value" style={{ 
              color: systemStatus.riskLevel === 'LOW' ? '#00ff88' : 
                     systemStatus.riskLevel === 'MEDIUM' ? '#ffaa00' : '#ff3366'
            }}>
              {systemStatus.riskLevel}
            </span>
          </div>
        </div>
      </div>
    </header>
  );
};

export default DashboardHeader;