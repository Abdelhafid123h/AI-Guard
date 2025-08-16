import React, { useEffect, useState } from 'react';

const HistoryPage = () => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = () => {
    setLoading(true);
    fetch('http://127.0.0.1:8000/usage/history?limit=200')
      .then(r => r.json())
      .then(data => {
        if(!data.success){ throw new Error('Réponse invalide'); }
        setItems(data.data || []);
        setLoading(false);
      })
      .catch(e => { setError(e.message); setLoading(false); });
  };

  useEffect(() => { load(); }, []);

  // Pas de modal: affichage direct du texte masqué complet

  return (
    <div style={{padding:'2rem'}}>
      <h2>Historique d'utilisation</h2>
      <button onClick={load} style={{marginBottom:'1rem'}}>Rafraîchir</button>
      {loading && <p>Chargement...</p>}
      {error && <p style={{color:'red'}}>Erreur: {error}</p>}
      {!loading && !error && (
        <table style={{width:'100%', borderCollapse:'collapse'}}>
          <thead>
            <tr>
              <th style={th}>ID</th>
              <th style={th}>Date</th>
              <th style={th}>Type</th>
              <th style={th}>Tokens In</th>
              <th style={th}>Tokens Out</th>
              <th style={th}>Total</th>
              <th style={th}>Modèle</th>
              <th style={th}>Texte Masqué Complet</th>
            </tr>
          </thead>
          <tbody>
            {items.map(it => (
              <tr key={it.id}>
                <td style={td}>{it.id}</td>
                <td style={td}>{it.created_at}</td>
                <td style={td}>{it.guard_type}</td>
                <td style={td}>{it.prompt_tokens}</td>
                <td style={td}>{it.completion_tokens}</td>
                <td style={td}>{it.total_tokens}</td>
                <td style={td}>{it.model || ''}</td>
                <td style={{...td, whiteSpace:'pre-wrap', maxWidth:'800px'}}>{it.masked_text}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
};

const th = {border:'1px solid #444', padding:'6px', background:'#222', color:'#eee'};
const td = {border:'1px solid #444', padding:'6px', fontSize:'0.85rem'};

export default HistoryPage;
