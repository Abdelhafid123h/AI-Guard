import React, { useEffect, useState } from 'react';
import axios from 'axios';

const STATIC_FALLBACK = [
  {
    type: 'TypeA',
    title: '🆔 Données Personnelles Identifiantes',
    description: 'Protection des informations d\'identité personnelle',
    items: [
      'Nom et prénom',
      'Date et lieu de naissance',
      'Numéro de sécurité sociale',
      'Carte d\'identité / Passeport',
      'Permis de conduire'
    ],
    color: '#e74c3c'
  },
  {
    type: 'TypeB',
    title: '💳 Données Financières',
    description: 'Protection des informations bancaires et financières',
    items: [
      'Numéro de carte bancaire',
      'IBAN / RIB',
      'Numéro de compte bancaire',
      'Codes de sécurité',
      'Informations de paiement'
    ],
    color: '#f39c12'
  },
  {
    type: 'InfoPerso',
    title: '📍 Données de Contact',
    description: 'Protection des informations de contact et localisation',
    items: [
      'Adresse postale complète',
      'Code postal',
      'Adresse e-mail',
      'Numéro de téléphone',
      'Nom d\'entreprise',
      'Adresse IP'
    ],
    color: '#3498db'
  }
];

const GuardTypeInfo = () => {
  const [cards, setCards] = useState(STATIC_FALLBACK);

  useEffect(() => {
    let cancelled = false;
    const apiBase = process.env.REACT_APP_API_URL || 'http://localhost:8000';

    async function load() {
      try {
        const gt = await axios.get(`${apiBase}/api/config/guard-types`);
        if (!gt.data?.guard_types) return;
        const guardTypes = gt.data.guard_types;

        const fieldsByType = {};
        await Promise.all(
          guardTypes.map(async (g) => {
            try {
              const resp = await axios.get(`${apiBase}/api/config/guard-types/${g.name}/fields`);
              fieldsByType[g.name] = (resp.data?.data || []).map(f => f.display_name || f.field_name);
            } catch (_) {
              fieldsByType[g.name] = [];
            }
          })
        );

        const mapped = guardTypes.map(g => ({
          type: g.name,
          title: `${g.icon || ''} ${g.display_name}`.trim(),
          description: g.description || '',
          items: fieldsByType[g.name] || [],
          color: g.color || '#666'
        }));

        if (!cancelled && mapped.length) setCards(mapped);
      } catch (_e) {
        // keep fallback silently
      }
    }

    load();
    return () => { cancelled = true; }
  }, []);

  return (
    <div className="guard-type-info">
      {cards.map(guard => (
        <div
          key={guard.type}
          className="guard-type-card"
          style={{
            background: `linear-gradient(135deg, ${guard.color}15 0%, ${guard.color}25 100%)`,
            border: `1px solid ${guard.color}40`
          }}
        >
          <h3 style={{ color: guard.color, marginBottom: '10px' }}>
            {guard.title}
          </h3>
          {guard.description && (
            <p style={{
              color: '#666',
              fontSize: '14px',
              marginBottom: '15px',
              fontStyle: 'italic'
            }}>
              {guard.description}
            </p>
          )}
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {(guard.items || []).map((item, index) => (
              <li
                key={index}
                style={{
                  padding: '4px 0',
                  color: '#555',
                  fontSize: '14px'
                }}
              >
                <span style={{ color: guard.color, marginRight: '8px' }}>🔒</span>
                {item}
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

export default GuardTypeInfo;
