import React, { useState, useEffect } from 'react';
import { Box, Activity, Cpu, Network, Shield, Zap } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';

const AgentMonitoring = ({ compact }) => {
  const [agents, setAgents] = useState([]);
  const [stats, setStats] = useState({
    totalAgents: 0,
    activeAgents: 0,
    avgProcessingLoad: 0,
    avgEthicalScore: 0
  });

  useEffect(() => {
    // Simulate agent data
    const generateAgents = () => {
      const tiers = ['Σ-1', 'Σ-2', 'Σ-3', 'Σ-4'];
      const statuses = ['active', 'processing', 'standby'];
      const newAgents = [];
      
      for (let i = 0; i < 12; i++) {
        newAgents.push({
          id: `AGT-${String(i + 1).padStart(4, '0')}`,
          tier: tiers[Math.floor(Math.random() * tiers.length)],
          status: statuses[Math.floor(Math.random() * statuses.length)],
          processingLoad: Math.floor(Math.random() * 100),
          ethicalScore: 0.95 + Math.random() * 0.05,
          ckActivations: Math.floor(Math.random() * 1000),
          latency: Math.floor(Math.random() * 100),
          lastActivity: new Date(Date.now() - Math.random() * 3600000).toLocaleTimeString()
        });
      }
      return newAgents;
    };

    setAgents(generateAgents());

    const interval = setInterval(() => {
      setAgents(prev => prev.map(agent => ({
        ...agent,
        processingLoad: Math.min(100, Math.max(0, agent.processingLoad + (Math.random() - 0.5) * 10)),
        ckActivations: agent.ckActivations + Math.floor(Math.random() * 10),
        latency: Math.floor(50 + Math.random() * 50)
      })));
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const totalAgents = agents.length;
    const activeAgents = agents.filter(a => a.status === 'active').length;
    const avgLoad = agents.length > 0 ? agents.reduce((sum, a) => sum + a.processingLoad, 0) / agents.length : 0;
    const avgEthical = agents.length > 0 ? agents.reduce((sum, a) => sum + a.ethicalScore, 0) / agents.length : 0;

    setStats({
      totalAgents,
      activeAgents,
      avgProcessingLoad: avgLoad,
      avgEthicalScore: avgEthical
    });
  }, [agents]);

  const tierData = [
    { name: 'Σ-1', value: agents.filter(a => a.tier === 'Σ-1').length, color: '#00f5ff' },
    { name: 'Σ-2', value: agents.filter(a => a.tier === 'Σ-2').length, color: '#7000ff' },
    { name: 'Σ-3', value: agents.filter(a => a.tier === 'Σ-3').length, color: '#ff00a0' },
    { name: 'Σ-4', value: agents.filter(a => a.tier === 'Σ-4').length, color: '#00ff88' }
  ];

  const loadData = agents.slice(0, 8).map(a => ({
    name: a.id.split('-')[1],
    load: a.processingLoad,
    ethical: a.ethicalScore * 100
  }));

  if (compact) {
    return (
      <div className="panel panel-compact">
        <div className="panel-header">
          <h3 className="panel-title">
            <Box size={20} />
            Agent Monitoring
          </h3>
          <span style={{ fontSize: '0.75rem', color: '#606070' }}>
            {stats.activeAgents}/{stats.totalAgents} Active
          </span>
        </div>
        <div className="agent-list">
          {agents.slice(0, 4).map(agent => (
            <div key={agent.id} className="agent-card">
              <div className="agent-info">
                <span className="agent-id">{agent.id}</span>
                <span className="agent-tier">Tier {agent.tier}</span>
              </div>
              <div className="agent-metrics">
                <div className="agent-metric">
                  <div className="agent-metric-value">{agent.processingLoad.toFixed(0)}%</div>
                  <div className="agent-metric-label">Load</div>
                </div>
              </div>
              <div className={`agent-status ${agent.status}`}>
                {agent.status}
              </div>
            </div>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h3 className="panel-title">
          <Box size={20} />
          Real-Time Agent Monitoring
        </h3>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          <span style={{ fontSize: '0.875rem', color: '#a0a0b0' }}>
            <span style={{ color: '#00ff88', fontWeight: 600 }}>{stats.activeAgents}</span> / {stats.totalAgents} Active Agents
          </span>
        </div>
      </div>

      <div className="metrics-grid" style={{ marginBottom: '1.5rem' }}>
        <div className="metric-card">
          <div className="metric-card-title">Total Agents</div>
          <div className="metric-card-value">{stats.totalAgents}</div>
          <div className="metric-card-subtitle">Σ-class SOI</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">Active Now</div>
          <div className="metric-card-value" style={{ color: '#00ff88' }}>{stats.activeAgents}</div>
          <div className="metric-card-subtitle">Processing</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">Avg Load</div>
          <div className="metric-card-value" style={{ 
            color: stats.avgProcessingLoad > 80 ? '#ff3366' : stats.avgProcessingLoad > 60 ? '#ffaa00' : '#00f5ff'
          }}>
            {stats.avgProcessingLoad.toFixed(1)}%
          </div>
          <div className="metric-card-subtitle">CPU/Memory</div>
        </div>
        <div className="metric-card">
          <div className="metric-card-title">Avg Ethics</div>
          <div className="metric-card-value" style={{ color: '#00ff88' }}>
            {(stats.avgEthicalScore * 100).toFixed(1)}%
          </div>
          <div className="metric-card-subtitle">CECT Score</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginBottom: '1.5rem' }}>
        <div className="chart-container" style={{ height: 250 }}>
          <h4 style={{ fontSize: '0.75rem', color: '#a0a0b0', marginBottom: '0.5rem' }}>Agent Tier Distribution</h4>
          <ResponsiveContainer width="100%" height="85%">
            <PieChart>
              <Pie
                data={tierData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {tierData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip 
                contentStyle={{ background: '#1a1a25', border: '1px solid #2a2a3a', borderRadius: '4px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="chart-container" style={{ height: 250 }}>
          <h4 style={{ fontSize: '0.75rem', color: '#a0a0b0', marginBottom: '0.5rem' }}>Processing Load by Agent</h4>
          <ResponsiveContainer width="100%" height="85%">
            <BarChart data={loadData}>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} stroke="#606070" />
              <YAxis tick={{ fontSize: 10 }} stroke="#606070" />
              <Tooltip 
                contentStyle={{ background: '#1a1a25', border: '1px solid #2a2a3a', borderRadius: '4px' }}
              />
              <Bar dataKey="load" fill="#00f5ff" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      <h4 style={{ fontSize: '0.875rem', color: '#a0a0b0', marginBottom: '0.75rem' }}>Active Agents</h4>
      <div className="agent-list">
        {agents.map(agent => (
          <div key={agent.id} className="agent-card">
            <div className="agent-info">
              <span className="agent-id">{agent.id}</span>
              <span className="agent-tier">Tier {agent.tier} • Last: {agent.lastActivity}</span>
            </div>
            <div className="agent-metrics">
              <div className="agent-metric">
                <div className="agent-metric-value" style={{ 
                  color: agent.processingLoad > 80 ? '#ff3366' : agent.processingLoad > 60 ? '#ffaa00' : '#00f5ff'
                }}>
                  {agent.processingLoad.toFixed(0)}%
                </div>
                <div className="agent-metric-label">Load</div>
              </div>
              <div className="agent-metric">
                <div className="agent-metric-value" style={{ color: '#00ff88' }}>
                  {(agent.ethicalScore * 100).toFixed(1)}%
                </div>
                <div className="agent-metric-label">Ethics</div>
              </div>
              <div className="agent-metric">
                <div className="agent-metric-value">{agent.ckActivations}</div>
                <div className="agent-metric-label">CKs</div>
              </div>
              <div className="agent-metric">
                <div className="agent-metric-value" style={{ color: agent.latency > 80 ? '#ffaa00' : '#00f5ff' }}>
                  {agent.latency}ms
                </div>
                <div className="agent-metric-label">Latency</div>
              </div>
            </div>
            <div className={`agent-status ${agent.status}`}>
              {agent.status}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AgentMonitoring;