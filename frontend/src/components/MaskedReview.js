import React, { useMemo, useState } from 'react';

const MaskedReview = ({ original, masked, tokens, guardType, onFinalize, onCancel, loading }) => {
  const [editedMasked, setEditedMasked] = useState(masked || '');

  // Token integrity checks: don't allow losing or altering existing tokens
  const tokenList = useMemo(() => Object.keys(tokens || {}), [tokens]);
  const foundTokens = useMemo(() => {
    const m = editedMasked.match(/<[^:<>]+:TOKEN_[^>]+>/g) || [];
    return Array.from(new Set(m));
  }, [editedMasked]);
  const missingTokens = useMemo(
    () => tokenList.filter(t => !editedMasked.includes(t)),
    [tokenList, editedMasked]
  );
  const unknownTokens = useMemo(
    () => foundTokens.filter(t => !tokenList.includes(t)),
    [tokenList, foundTokens]
  );
  const integrityOk = missingTokens.length === 0 && unknownTokens.length === 0;

  return (
    <div className="card">
      <h2>🧐 Vérifier le texte masqué</h2>
      <p style={{ color: '#666', marginTop: '-8px' }}>
        Le texte ci-dessous sera envoyé au LLM. Vous pouvez le modifier avant envoi.
      </p>

      <div className="form-group" style={{
        padding: '12px',
        background: '#fff7e6',
        border: '1px solid #ffe58f',
        borderRadius: 8,
        marginBottom: 12
      }}>
        <strong>⚠️ Attention&nbsp;:</strong> Ne modifiez pas les <em>jetons de masquage</em> (par ex. «&nbsp;{tokenList[0] || '<type:TOKEN_xxx>'}&nbsp;»). Si vous les changez ou les supprimez, la restauration de la réponse peut échouer.
        {(missingTokens.length > 0 || unknownTokens.length > 0) && (
          <div style={{ marginTop: 8, color: '#ad4e00' }}>
            {!integrityOk && (
              <>
                {missingTokens.length > 0 && (
                  <div>Jetons manquants: {missingTokens.length}</div>
                )}
                {unknownTokens.length > 0 && (
                  <div>Jetons inconnus (ajoutés/modifiés): {unknownTokens.length}</div>
                )}
              </>
            )}
          </div>
        )}
      </div>

      <div className="form-group">
        <label>Texte original</label>
        <pre style={{ background: '#f8f9fa', padding: '12px', borderRadius: 8, whiteSpace: 'pre-wrap' }}>{original}</pre>
      </div>

      <div className="form-group">
        <label>Texte masqué (éditable)</label>
        <textarea
          rows="6"
          value={editedMasked}
          onChange={(e) => setEditedMasked(e.target.value)}
          style={{ width: '100%' }}
        />
      </div>

      <div className="form-actions" style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        <button className="btn" disabled={loading || !integrityOk} onClick={() => onFinalize(editedMasked, tokens, guardType)}>
          {loading ? '🚀 Envoi...' : (integrityOk ? '🚀 Envoyer au LLM' : '🚫 Corriger les jetons')}
        </button>
        <button className="btn" style={{ background: '#eee', color: '#333' }} disabled={loading} onClick={onCancel}>
          Annuler
        </button>
        {!integrityOk && (
          <span style={{ color: '#ad4e00', fontSize: 13 }}>Les jetons doivent rester inchangés.</span>
        )}
      </div>
    </div>
  );
};

export default MaskedReview;
