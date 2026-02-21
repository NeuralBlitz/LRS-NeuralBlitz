import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts';
import { Activity, TrendingUp, Clock, Zap } from 'lucide-react';

const RealTimeMetrics = ({ systemStatus }) => {
  const [metrics, setMetrics] = useState({
    vpceHistory: [],
    driftHistory: [],
    throughputHistory: [],
    latencyHistory: []
  });

  useEffect(() => {
    const interval = setInterval(() => {
      const timestamp = new Date().toLocaleTimeString();
      
      setMetrics(prev => ({
        vpceHistory: [...prev.vpceHistory.slice(-19), {
          time: timestamp,
          value: systemStatus.vpce,
          threshold: 0.985
        }],
        driftHistory: [...prev.driftHistory.slice(-19), {
          time: timestamp,
          value: systemStatus.driftRate,
          threshold: 0.03
        }],
        throughputHistory: [...prev.throughputHistory.slice(-19), {
          time: timestamp,
          value: Math.floor(1000 + Math.random() * 500),
          ops: Math.floor(850 + Math.random() * 300)
        }],
        latencyHistory: [...prev.latencyHistory.slice(-19), {
          time: timestamp,
          p50: Math.floor(50 + Math.random() * 20),
          p95: Math.floor(120 + Math.random() * 40),
          p99: Math.floor(180 + Math.random() * 60)
        }]
      }));
    }, 2000);

    return () => clearInterval(interval);
  }, [systemStatus]);

  return (
    <div className="panel">
      <div className="panel-header">
        <h3 className="panel-title">
          <Activity size={20} />
          Real-Time System Metrics
        </h3>
        <span style={{ fontSize: '0.75rem', color: '#606070' }}>
          Last update: {new Date(systemStatus.lastUpdate).toLocaleTimeString()}
        </span>
      </div>

      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-card-title">Veritas Phase Coherence</div>
          <div className="metric-card-value" style={{ color: systemStatus.vpce >= 0.985 ? '#00ff88' : '#ffaa00' }}>
            {(systemStatus.vpce * 100).toFixed(1)}%
          </div>
          <div className="metric-card-subtitle">Target: ≥98.5%</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">MetaMind Drift Rate</div>
          <div className="metric-card-value" style={{ color: systemStatus.driftRate < 0.01 ? '#00ff88' : '#ffaa00' }}>
            {systemStatus.driftRate.toFixed(4)}
          </div>
          <div className="metric-card-subtitle">Threshold: 0.03</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">System Throughput</div>
          <div className="metric-card-value">
            {metrics.throughputHistory.length > 0 ? 
              metrics.throughputHistory[metrics.throughputHistory.length - 1].value : 0}
          </div>
          <div className="metric-card-subtitle">ops/sec</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">CK Activations</div>
          <div className="metric-card-value">
            {metrics.throughputHistory.length > 0 ? 
              metrics.throughputHistory[metrics.throughputHistory.length - 1].ops : 0}
          </div>
          <div className="metric-card-subtitle">active</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginTop: '1.5rem' }}>
        <div className="chart-container">
          <h4 style={{ fontSize: '0.75rem', color: '#a0a0b0', marginBottom: '0.5rem' }}>VPCE Trend (Veritas Phase-Coherence)</h4>
          <ResponsiveContainer width="100%" height="85%">
            <AreaChart data={metrics.vpceHistory}>
              <defs>
                <linearGradient id="vpceGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#00f5ff" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#00f5ff" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#606070" />
              <YAxis domain={[0.95, 1]} tick={{ fontSize: 10 }} stroke="#606070" />
              <Tooltip 
                contentStyle={{ background: '#1a1a25', border: '1px solid #2a2a3a', borderRadius: '4px' }}
                itemStyle={{ color: '#00f5ff' }}
              />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="#00f5ff" 
                fillOpacity={1} 
                fill="url(#vpceGradient)" 
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container">
          <h4 style={{ fontSize: '0.75rem', color: '#a0a0b0', marginBottom: '0.5rem' }}>MRDE Drift Rate (MetaMind Recursive Drift)</h4>
          <ResponsiveContainer width="100%" height="85%">
            <LineChart data={metrics.driftHistory}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#606070" />
              <YAxis domain={[0, 0.05]} tick={{ fontSize: 10 }} stroke="#606070" />
              <Tooltip 
                contentStyle={{ background: '#1a1a25', border: '1px solid #2a2a3a', borderRadius: '4px' }}
                itemStyle={{ color: '#ff00a0' }}
              />
              <Line 
                type="monotone" 
                dataKey="value" 
                stroke="#ff00a0" 
                strokeWidth={2}
                dot={false}
              />
              <Line 
                type="monotone" 
                dataKey="threshold" 
                stroke="#ff3366" 
                strokeDasharray="5 5"
                strokeWidth={1}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default RealTimeMetrics;