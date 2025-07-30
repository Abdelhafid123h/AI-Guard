import React, { useState } from 'react';

const ResultDisplay = ({ result }) => {
  const [activeTab, setActiveTab] = useState('original');

  const tabs = [
    { id: 'original', label: '📄 Texte Original', content: result.original },
    { id: 'masked', label: '🔒 Texte Masqué', content: result.masked },
    { id: 'llm_response', label: '🤖 Réponse IA', content: result.llm_response },
    { id: 'unmasked', label: '🔓 Réponse Démasquée', content: result.unmasked }
  ];

  return (
    <div className="result-section">
      <h2>📊 Résultats de l'Analyse</h2>
      
      {/* Navigation par onglets */}
      <div className="tabs" style={{
        display: 'flex',
        marginBottom: '20px',
        borderBottom: '2px solid #e1e5e9'
      }}>
        {tabs.map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`tab-button ${activeTab === tab.id ? 'active' : ''}`}
            style={{
              padding: '12px 20px',
              border: 'none',
              background: activeTab === tab.id ? '#667eea' : 'transparent',
              color: activeTab === tab.id ? 'white' : '#666',
              borderRadius: '8px 8px 0 0',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: '500',
              transition: 'all 0.3s ease'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Contenu de l'onglet actif */}
      <div className="tab-content">
        {tabs.map(tab => (
          activeTab === tab.id && (
            <div key={tab.id} className="result-item">
              <h3>{tab.label}</h3>
              <pre style={{
                background: '#f8f9fa',
                padding: '15px',
                borderRadius: '8px',
                fontSize: '14px',
                lineHeight: '1.5',
                whiteSpace: 'pre-wrap',
                wordWrap: 'break-word',
                border: '1px solid #e1e5e9'
              }}>
                {tab.content}
              </pre>
            </div>
          )
        ))}
      </div>

      {/* Statistiques */}
      <div className="stats" style={{
        marginTop: '30px',
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
        gap: '15px'
      }}>
        <div className="stat-card" style={{
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
          padding: '20px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h4 style={{ color: '#333', marginBottom: '10px' }}>📝 Longueur Originale</h4>
          <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#667eea' }}>
            {result.original.length} caractères
          </span>
        </div>

        <div className="stat-card" style={{
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
          padding: '20px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h4 style={{ color: '#333', marginBottom: '10px' }}>🔒 Entités Masquées</h4>
          <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#e74c3c' }}>
            {(result.masked.match(/<[^>]+>/g) || []).length}
          </span>
        </div>

        <div className="stat-card" style={{
          background: 'linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%)',
          padding: '20px',
          borderRadius: '8px',
          textAlign: 'center'
        }}>
          <h4 style={{ color: '#333', marginBottom: '10px' }}>🤖 Réponse IA</h4>
          <span style={{ fontSize: '24px', fontWeight: 'bold', color: '#27ae60' }}>
            {result.llm_response.length} caractères
          </span>
        </div>
      </div>

      {/* JSON complet pour développeurs */}
      <details style={{ marginTop: '30px' }}>
        <summary style={{
          cursor: 'pointer',
          padding: '10px',
          background: '#f8f9fa',
          borderRadius: '8px',
          fontWeight: '600'
        }}>
          🔧 Données JSON complètes (pour développeurs)
        </summary>
        <pre style={{
          background: '#1e1e1e',
          color: '#d4d4d4',
          padding: '20px',
          borderRadius: '8px',
          fontSize: '12px',
          overflow: 'auto',
          marginTop: '10px'
        }}>
          {JSON.stringify(result, null, 2)}
        </pre>
      </details>
    </div>
  );
};

export default ResultDisplay;
