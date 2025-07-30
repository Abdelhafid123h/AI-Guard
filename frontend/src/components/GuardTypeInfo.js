import React from 'react';

const GuardTypeInfo = () => {
  const guardTypes = [
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

  return (
    <div className="guard-type-info">
      {guardTypes.map(guard => (
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
          <p style={{ 
            color: '#666', 
            fontSize: '14px', 
            marginBottom: '15px',
            fontStyle: 'italic'
          }}>
            {guard.description}
          </p>
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {guard.items.map((item, index) => (
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
