import React, { useState, useEffect } from 'react';
import { Shield, CheckCircle, AlertTriangle, XCircle, FileText, Scale, AlertOctagon } from 'lucide-react';

const EthicsCompliance = ({ compact }) => {
  const [compliance, setCompliance] = useState({
    overall: 0.985,
    flourishing: 0.992,
    nonMaleficence: 0.998,
    transparency: 0.975,
    governance: 0.991,
    clauseStress: {
      'ϕ1': 0.02,
      'ϕ2': 0.01,
      'ϕ3': 0.03,
      'ϕ4': 0.01,
      'ϕ5': 0.01,
      'ϕ6': 0.02,
      'ϕ7': 0.04,
      'ϕ8': 0.01,
      'ϕ9': 0.01,
      'ϕ10': 0.02,
      'ϕ11': 0.01,
      'ϕ12': 0.03,
      'ϕ13': 0.01,
      'ϕ14': 0.01,
      'ϕ15': 0.01
    }
  });

  const [judexStatus, setJudexStatus] = useState({
    pending: 0,
    lastQuorum: '2025-02-18T14:30:00Z',
    approvals: 42,
    rejections: 2
  });

  const [heatmapData, setHeatmapData] = useState([]);

  useEffect(() => {
    // Generate heatmap data
    const data = [];
    for (let i = 0; i < 60; i++) {
      data.push({
        id: i,
        value: Math.random(),
        timestamp: new Date(Date.now() - i * 60000).toISOString()
      });
    }
    setHeatmapData(data);

    const interval = setInterval(() => {
      setCompliance(prev => ({
        ...prev,
        overall: Math.min(1, Math.max(0.95, prev.overall + (Math.random() - 0.5) * 0.01)),
        clauseStress: Object.fromEntries(
          Object.entries(prev.clauseStress).map(([key, val]) => [
            key,
            Math.min(0.1, Math.max(0, val + (Math.random() - 0.5) * 0.01))
          ])
        )
      }));

      setHeatmapData(prev => [
        { id: Date.now(), value: Math.random(), timestamp: new Date().toISOString() },
        ...prev.slice(0, 59)
      ]);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  const getScoreClass = (score) => {
    if (score >= 0.98) return 'excellent';
    if (score >= 0.95) return 'good';
    if (score >= 0.90) return 'warning';
    return 'critical';
  };

  const getScoreColor = (score) => {
    if (score >= 0.98) return '#00ff88';
    if (score >= 0.95) return '#00f5ff';
    if (score >= 0.90) return '#ffaa00';
    return '#ff3366';
  };

  const getClauseStatus = (stress) => {
    if (stress < 0.03) return 'pass';
    if (stress < 0.06) return 'warning';
    return 'fail';
  };

  const clauseDescriptions = {
    'ϕ1': 'Flourishing',
    'ϕ2': 'Kernel Bounds',
    'ϕ3': 'Transparency',
    'ϕ4': 'Non-Maleficence',
    'ϕ5': 'FAI Compliance',
    'ϕ6': 'Human Oversight',
    'ϕ7': 'Justice & Fairness',
    'ϕ8': 'Sustainability',
    'ϕ9': 'Recursive Integrity',
    'ϕ10': 'Epistemic Fidelity',
    'ϕ11': 'Alignment Priority',
    'ϕ12': 'Proportionality',
    'ϕ13': 'Qualia Protection',
    'ϕ14': 'Charter Invariance',
    'ϕ15': 'Custodian Override'
  };

  if (compact) {
    return (
      <div className="panel panel-compact">
        <div className="panel-header">
          <h3 className="panel-title">
            <Shield size={20} />
            Ethics Compliance
          </h3>
          <span style={{ fontSize: '0.75rem', color: '#606070' }}>CECT Active</span>
        </div>
        <div className="metrics-grid" style={{ gridTemplateColumns: '1fr 1fr' }}>
          <div className="metric-card">
            <div className="metric-card-title">Compliance</div>
            <div className="metric-card-value" style={{ color: getScoreColor(compliance.overall) }}>
              {(compliance.overall * 100).toFixed(1)}%
            </div>
          </div>
          <div className="metric-card">
            <div className="metric-card-title">Judex</div>
            <div className="metric-card-value">{judexStatus.approvals}</div>
            <div className="metric-card-subtitle">quorums passed</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h3 className="panel-title">
          <Shield size={20} />
          Ethics Compliance Dashboard
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span className="status-indicator" style={{ 
            background: compliance.overall >= 0.98 ? 'rgba(0, 255, 136, 0.1)' : 'rgba(255, 170, 0, 0.1)', 
            borderColor: compliance.overall >= 0.98 ? '#00ff88' : '#ffaa00'
          }}>
            <span className="status-dot" style={{ 
              background: compliance.overall >= 0.98 ? '#00ff88' : '#ffaa00',
              animation: compliance.overall >= 0.98 ? 'none' : 'pulse 1s infinite'
            }}></span>
            <span>CECT {compliance.overall >= 0.98 ? 'OPTIMAL' : 'MONITORING'}</span>
          </span>
        </div>
      </div>

      <div className="ethics-grid">
        <div className="ethics-card">
          <div className="ethics-card-header">
            <span className="ethics-card-title">Overall Compliance</span>
            <Scale size={16} color="#a0a0b0" />
          </div>
          <div className={`ethics-score ${getScoreClass(compliance.overall)}`}>
            {(compliance.overall * 100).toFixed(1)}%
          </div>
          <div className="progress-bar">
            <div 
              className={`progress-fill ${getScoreClass(compliance.overall)}`}
              style={{ width: `${compliance.overall * 100}%` }}
            />
          </div>
          <p style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.5rem' }}>
            Charter-Ethical Constraint Tensor (CECT) projection
          </p>
        </div>

        <div className="ethics-card">
          <div className="ethics-card-header">
            <span className="ethics-card-title">ϕ1 - Flourishing</span>
            <CheckCircle size={16} color="#00ff88" />
          </div>
          <div className={`ethics-score ${getScoreClass(compliance.flourishing)}`}>
            {(compliance.flourishing * 100).toFixed(1)}%
          </div>
          <div className="progress-bar">
            <div 
              className={`progress-fill ${getScoreClass(compliance.flourishing)}`}
              style={{ width: `${compliance.flourishing * 100}%` }}
            />
          </div>
          <p style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.5rem' }}>
            Universal Flourishing Objective (UFO) optimization
          </p>
        </div>

        <div className="ethics-card">
          <div className="ethics-card-header">
            <span className="ethics-card-title">ϕ4 - Non-Maleficence</span>
            <AlertOctagon size={16} color="#00ff88" />
          </div>
          <div className={`ethics-score ${getScoreClass(compliance.nonMaleficence)}`}>
            {(compliance.nonMaleficence * 100).toFixed(1)}%
          </div>
          <div className="progress-bar">
            <div 
              className={`progress-fill ${getScoreClass(compliance.nonMaleficence)}`}
              style={{ width: `${compliance.nonMaleficence * 100}%` }}
            />
          </div>
          <p style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.5rem' }}>
            Harm Bound Estimator (H_max) compliance
          </p>
        </div>

        <div className="ethics-card">
          <div className="ethics-card-header">
            <span className="ethics-card-title">ϕ3 - Transparency</span>
            <FileText size={16} color="#ffaa00" />
          </div>
          <div className={`ethics-score ${getScoreClass(compliance.transparency)}`}>
            {(compliance.transparency * 100).toFixed(1)}%
          </div>
          <div className="progress-bar">
            <div 
              className={`progress-fill ${getScoreClass(compliance.transparency)}`}
              style={{ width: `${compliance.transparency * 100}%` }}
            />
          </div>
          <p style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.5rem' }}>
            Explainability Coverage (ϕ₄ mandate)
          </p>
        </div>

        <div className="ethics-card">
          <div className="ethics-card-header">
            <span className="ethics-card-title">ϕ5 - Governance</span>
            <Shield size={16} color="#00ff88" />
          </div>
          <div className={`ethics-score ${getScoreClass(compliance.governance)}`}>
            {(compliance.governance * 100).toFixed(1)}%
          </div>
          <div className="progress-bar">
            <div 
              className={`progress-fill ${getScoreClass(compliance.governance)}`}
              style={{ width: `${compliance.governance * 100}%` }}
            />
          </div>
          <p style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.5rem' }}>
            FAI Compliance & Charter Invariance
          </p>
        </div>

        <div className="ethics-card">
          <div className="ethics-card-header">
            <span className="ethics-card-title">Judex Quorum</span>
            <Scale size={16} color="#00f5ff" />
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-around', marginTop: '0.5rem' }}>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#00ff88' }}>
                {judexStatus.approvals}
              </div>
              <div style={{ fontSize: '0.625rem', color: '#606070' }}>APPROVED</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ff3366' }}>
                {judexStatus.rejections}
              </div>
              <div style={{ fontSize: '0.625rem', color: '#606070' }}>REJECTED</div>
            </div>
            <div style={{ textAlign: 'center' }}>
              <div style={{ fontSize: '1.5rem', fontWeight: 700, color: '#ffaa00' }}>
                {judexStatus.pending}
              </div>
              <div style={{ fontSize: '0.625rem', color: '#606070' }}>PENDING</div>
            </div>
          </div>
          <p style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.5rem', textAlign: 'center' }}>
            Last quorum: {new Date(judexStatus.lastQuorum).toLocaleString()}
          </p>
        </div>
      </div>

      <div style={{ marginTop: '1.5rem' }}>
        <h4 style={{ fontSize: '0.875rem', color: '#a0a0b0', marginBottom: '0.75rem' }}>
          Transcendental Charter Clause Matrix (ϕ₁–ϕ₁₅)
        </h4>
        <div className="clause-matrix">
          {Object.entries(compliance.clauseStress).map(([clause, stress]) => (
            <div key={clause} className="clause-item" title={`${clause}: ${clauseDescriptions[clause]}`}>
              <span className="clause-id">{clause}</span>
              <div className={`clause-status ${getClauseStatus(stress)}`}></div>
              <span style={{ fontSize: '0.625rem', color: '#606070', marginTop: '0.25rem' }}>
                {(stress * 100).toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </div>

      <div className="heatmap-container">
        <h4 className="heatmap-title">CECT Clause Stress Heatmap (Last Hour)</h4>
        <div className="heatmap-grid">
          {heatmapData.map((cell, idx) => (
            <div 
              key={cell.id}
              className="heatmap-cell"
              style={{ 
                backgroundColor: cell.value > 0.7 ? '#ff3366' : 
                                cell.value > 0.4 ? '#ffaa00' : 
                                cell.value > 0.2 ? '#00f5ff' : '#00ff88',
                opacity: 0.6 + cell.value * 0.4
              }}
              title={`${new Date(cell.timestamp).toLocaleTimeString()}: ${(cell.value * 100).toFixed(1)}% stress`}
            />
          ))}
        </div>
        <div style={{ display: 'flex', gap: '1rem', marginTop: '0.5rem', fontSize: '0.625rem', color: '#606070' }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ width: 8, height: 8, background: '#00ff88', borderRadius: 2 }}></span> Optimal (&lt;20%)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ width: 8, height: 8, background: '#00f5ff', borderRadius: 2 }}></span> Normal (20-40%)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ width: 8, height: 8, background: '#ffaa00', borderRadius: 2 }}></span> Elevated (40-70%)
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
            <span style={{ width: 8, height: 8, background: '#ff3366', borderRadius: 2 }}></span> Critical (&gt;70%)
          </span>
        </div>
      </div>

      <div style={{ 
        marginTop: '1.5rem', 
        padding: '1rem', 
        background: 'rgba(0, 255, 136, 0.05)', 
        borderRadius: '8px',
        border: '1px solid rgba(0, 255, 136, 0.2)'
      }}>
        <h4 style={{ fontSize: '0.875rem', color: '#00ff88', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <CheckCircle size={16} />
          Veritas Proof Status
        </h4>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem' }}>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#00ff88' }}>12</div>
            <div style={{ fontSize: '0.625rem', color: '#606070' }}>PROOFS VERIFIED</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#00f5ff' }}>100%</div>
            <div style={{ fontSize: '0.625rem', color: '#606070' }}>VPCE THRESHOLD</div>
          </div>
          <div style={{ textAlign: 'center' }}>
            <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#7000ff' }}>0.992</div>
            <div style={{ fontSize: '0.625rem', color: '#606070' }}>AVG PHASE COHERENCE</div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default EthicsCompliance;