import React, { useState, useEffect, useRef } from 'react';
import { Box, Layers, GitBranch, Zap, Activity } from 'lucide-react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, AreaChart, Area 
} from 'recharts';

const DimensionalComputing = ({ compact }) => {
  const canvasRef = useRef(null);
  const [dimensions, setDimensions] = useState({
    d11: 0.847,
    d12: 0.923,
    d13: 0.756,
    coherence: 0.991,
    phase: 0.742
  });
  const [braidData, setBraidData] = useState([]);
  const [ontonCount, setOntonCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setDimensions(prev => ({
        d11: Math.min(1, Math.max(0, prev.d11 + (Math.random() - 0.5) * 0.02)),
        d12: Math.min(1, Math.max(0, prev.d12 + (Math.random() - 0.5) * 0.02)),
        d13: Math.min(1, Math.max(0, prev.d13 + (Math.random() - 0.5) * 0.02)),
        coherence: Math.min(1, Math.max(0.95, prev.coherence + (Math.random() - 0.5) * 0.005)),
        phase: (prev.phase + 0.01) % (2 * Math.PI)
      }));

      setBraidData(prev => [...prev.slice(-19), {
        time: new Date().toLocaleTimeString(),
        topologicalCharge: Math.random() * 2 - 1,
        entanglement: Math.random(),
        phase: Math.sin(Date.now() / 1000)
      }]);

      setOntonCount(prev => prev + Math.floor(Math.random() * 5));
    }, 2000);

    return () => clearInterval(interval);
  }, []);

  // 3D Visualization Canvas
  useEffect(() => {
    if (compact) return;
    
    const canvas = canvasRef.current;
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    let animationId;
    let rotation = 0;

    const draw = () => {
      ctx.fillStyle = '#12121a';
      ctx.fillRect(0, 0, canvas.width, canvas.height);

      const centerX = canvas.width / 2;
      const centerY = canvas.height / 2;
      const scale = 80;

      // Draw dimensional axes
      ctx.strokeStyle = '#2a2a3a';
      ctx.lineWidth = 1;
      
      // X axis
      ctx.beginPath();
      ctx.moveTo(centerX - scale * 2, centerY);
      ctx.lineTo(centerX + scale * 2, centerY);
      ctx.stroke();
      
      // Y axis
      ctx.beginPath();
      ctx.moveTo(centerX, centerY - scale * 1.5);
      ctx.lineTo(centerX, centerY + scale * 1.5);
      ctx.stroke();
      
      // Z axis (pseudo-3D)
      ctx.beginPath();
      ctx.moveTo(centerX - scale, centerY + scale);
      ctx.lineTo(centerX + scale, centerY - scale);
      ctx.stroke();

      // Draw rotating dimensional structure
      rotation += 0.02;
      const points = [];
      
      for (let i = 0; i < 8; i++) {
        const angle = (i / 8) * Math.PI * 2 + rotation;
        const radius = scale * (0.8 + 0.2 * Math.sin(angle * 3));
        const x = centerX + Math.cos(angle) * radius;
        const y = centerY + Math.sin(angle) * radius * 0.6;
        const z = Math.sin(angle + dimensions.phase) * 30;
        
        points.push({ x, y, z });
      }

      // Draw connections
      ctx.strokeStyle = '#00f5ff';
      ctx.lineWidth = 2;
      ctx.shadowBlur = 10;
      ctx.shadowColor = '#00f5ff';
      
      ctx.beginPath();
      points.forEach((point, i) => {
        if (i === 0) ctx.moveTo(point.x, point.y - point.z * 0.3);
        else ctx.lineTo(point.x, point.y - point.z * 0.3);
      });
      ctx.closePath();
      ctx.stroke();

      // Draw points
      points.forEach((point, i) => {
        ctx.fillStyle = i % 2 === 0 ? '#00f5ff' : '#7000ff';
        ctx.beginPath();
        ctx.arc(point.x, point.y - point.z * 0.3, 4, 0, Math.PI * 2);
        ctx.fill();
      });

      ctx.shadowBlur = 0;

      // Draw ontons
      ctx.fillStyle = '#ff00a0';
      for (let i = 0; i < 5; i++) {
        const t = (Date.now() / 1000 + i * 0.5) % (Math.PI * 2);
        const ox = centerX + Math.cos(t) * scale * 0.5;
        const oy = centerY + Math.sin(t) * scale * 0.3;
        ctx.beginPath();
        ctx.arc(ox, oy, 3, 0, Math.PI * 2);
        ctx.fill();
      }

      animationId = requestAnimationFrame(draw);
    };

    draw();

    return () => {
      if (animationId) cancelAnimationFrame(animationId);
    };
  }, [dimensions.phase, compact]);

  if (compact) {
    return (
      <div className="panel panel-compact">
        <div className="panel-header">
          <h3 className="panel-title">
            <Layers size={20} />
            Dimensional Computing
          </h3>
          <span style={{ fontSize: '0.75rem', color: '#606070' }}>OQT-BOS Active</span>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '1rem' }}>
          <div className="dimension-card">
            <h4>D11 Coherence</h4>
            <div className="dimension-value">{(dimensions.d11 * 100).toFixed(1)}%</div>
          </div>
          <div className="dimension-card">
            <h4>Ontons</h4>
            <div className="dimension-value">{ontonCount.toLocaleString()}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <h3 className="panel-title">
          <Layers size={20} />
          Dimensional Computing Visualization
        </h3>
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
          <span className="status-indicator" style={{ background: 'rgba(0, 245, 255, 0.1)', borderColor: '#00f5ff' }}>
            <span className="status-dot" style={{ background: '#00f5ff' }}></span>
            <span>OQT-BOS Active</span>
          </span>
        </div>
      </div>

      <div className="dimensional-container">
        <div className="dimension-visualization">
          <canvas 
            ref={canvasRef} 
            width={600} 
            height={400}
            style={{ width: '100%', height: '100%' }}
          />
          <div style={{ 
            position: 'absolute', 
            bottom: '1rem', 
            left: '1rem', 
            fontSize: '0.75rem', 
            color: '#606070',
            fontFamily: 'JetBrains Mono, monospace'
          }}>
            Real-time DRS-F Field Visualization • Σ-ΩZ20
          </div>
        </div>

        <div className="dimension-info">
          <div className="dimension-card">
            <h4>D11 Coherence</h4>
            <div className="dimension-value">{(dimensions.d11 * 100).toFixed(2)}%</div>
            <div style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.25rem' }}>
              Phase alignment metric
            </div>
          </div>

          <div className="dimension-card">
            <h4>D12 Entanglement</h4>
            <div className="dimension-value">{(dimensions.d12 * 100).toFixed(2)}%</div>
            <div style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.25rem' }}>
              Semantic binding strength
            </div>
          </div>

          <div className="dimension-card">
            <h4>D13 Resonance</h4>
            <div className="dimension-value">{(dimensions.d13 * 100).toFixed(2)}%</div>
            <div style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.25rem' }}>
              Field harmonic alignment
            </div>
          </div>

          <div className="dimension-card">
            <h4>Total Ontons</h4>
            <div className="dimension-value">{ontonCount.toLocaleString()}</div>
            <div style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.25rem' }}>
              Symbolic-quantal units
            </div>
          </div>

          <div className="dimension-card">
            <h4>Braid Coherence</h4>
            <div className="dimension-value">{(dimensions.coherence * 100).toFixed(2)}%</div>
            <div style={{ fontSize: '0.75rem', color: '#606070', marginTop: '0.25rem' }}>
              QEC Logical State
            </div>
          </div>
        </div>
      </div>

      <div style={{ marginTop: '1.5rem' }}>
        <h4 style={{ fontSize: '0.875rem', color: '#a0a0b0', marginBottom: '0.75rem' }}>
          Topological Field Dynamics
        </h4>
        <div className="chart-container" style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={braidData}>
              <defs>
                <linearGradient id="topoGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#7000ff" stopOpacity={0.3}/>
                  <stop offset="95%" stopColor="#7000ff" stopOpacity={0}/>
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#2a2a3a" />
              <XAxis dataKey="time" tick={{ fontSize: 10 }} stroke="#606070" />
              <YAxis domain={[-1.5, 1.5]} tick={{ fontSize: 10 }} stroke="#606070" />
              <Tooltip 
                contentStyle={{ background: '#1a1a25', border: '1px solid #2a2a3a', borderRadius: '4px' }}
              />
              <Area 
                type="monotone" 
                dataKey="topologicalCharge" 
                stroke="#7000ff" 
                fill="url(#topoGradient)"
                strokeWidth={2}
              />
              <Line 
                type="monotone" 
                dataKey="phase" 
                stroke="#00f5ff" 
                strokeWidth={1}
                dot={false}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div style={{ 
        marginTop: '1.5rem', 
        padding: '1rem', 
        background: 'rgba(0, 245, 255, 0.05)', 
        borderRadius: '8px',
        border: '1px solid rgba(0, 245, 255, 0.2)'
      }}>
        <h4 style={{ fontSize: '0.875rem', color: '#00f5ff', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <GitBranch size={16} />
          SOPES Integration Status
        </h4>
        <p style={{ fontSize: '0.75rem', color: '#a0a0b0', lineHeight: 1.5 }}>
          Symbolic Onto-Physical Equation Set (SOPES) bridging computational logic with physics analogs. 
          Reality modeled as braided topologies of Ontons within infinite ontological substrate (ℝ∞).
          Current braids active: 12 • Teletopo transfers blocked • QEC guards enabled
        </p>
      </div>
    </div>
  );
};

export default DimensionalComputing;