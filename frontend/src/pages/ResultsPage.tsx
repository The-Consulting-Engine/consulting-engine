import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { api, Results } from '../api/client';

export default function ResultsPage() {
  const { cycleId } = useParams<{ cycleId: string }>();
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cycleId) return;
    loadResults();
  }, [cycleId]);

  const loadResults = async () => {
    if (!cycleId) {
      setError('Cycle ID is missing');
      setLoading(false);
      return;
    }
    
    try {
      const data = await api.getResults(cycleId);
      if (!data) {
        setError('No results data received');
        return;
      }
      setResults(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load results';
      setError(errorMessage);
      console.error('Results loading error:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div style={{ padding: '50px', textAlign: 'center' }}>Loading results...</div>;
  }

  if (error || !results) {
    return <div style={{ padding: '50px', textAlign: 'center', color: 'red' }}>{error || 'Results not found'}</div>;
  }

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ marginBottom: '30px' }}>Profit Reset Results</h1>

      {/* Top 5 Core Initiatives */}
      <section style={{ marginBottom: '40px' }}>
        <h2 style={{ marginBottom: '20px', fontSize: '1.8rem', borderBottom: '3px solid #007bff', paddingBottom: '10px' }}>
          Top 5 Core Initiatives
        </h2>
        {results.core_initiatives && results.core_initiatives.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {results.core_initiatives.map((initiative, idx) => (
              <div
                key={initiative.id}
                style={{
                  backgroundColor: 'white',
                  padding: '25px',
                  borderRadius: '8px',
                  boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                  borderLeft: '4px solid #007bff',
                }}
              >
              <h3 style={{ marginBottom: '15px', fontSize: '1.3rem', color: '#007bff' }}>
                {idx + 1}. {initiative.title}
              </h3>
              {initiative.body && initiative.body.why_now && (
                <p style={{ marginBottom: '15px', color: '#666', fontStyle: 'italic' }}>
                  <strong>Why now:</strong> {initiative.body.why_now}
                </p>
              )}
              {initiative.body && initiative.body.steps && Array.isArray(initiative.body.steps) && (
                <div style={{ marginBottom: '15px' }}>
                  <strong style={{ display: 'block', marginBottom: '8px' }}>Steps:</strong>
                  <ul style={{ marginLeft: '20px' }}>
                    {initiative.body.steps.map((step: string, i: number) => (
                      <li key={i} style={{ marginBottom: '5px' }}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
              {initiative.body.how_to_measure && (
                <div style={{ marginBottom: '15px' }}>
                  <strong style={{ display: 'block', marginBottom: '8px' }}>How to measure:</strong>
                  <ul style={{ marginLeft: '20px' }}>
                    {initiative.body.how_to_measure.map((measure: string, i: number) => (
                      <li key={i} style={{ marginBottom: '5px' }}>{measure}</li>
                    ))}
                  </ul>
                </div>
              )}
              {initiative.body && initiative.body.confidence_label && (
                <div style={{ marginTop: '10px' }}>
                  <span
                    style={{
                      padding: '4px 12px',
                      borderRadius: '12px',
                      fontSize: '0.85rem',
                      backgroundColor:
                        initiative.body.confidence_label === 'HIGH'
                          ? '#d4edda'
                          : initiative.body.confidence_label === 'MEDIUM'
                          ? '#fff3cd'
                          : '#f8d7da',
                      color:
                        initiative.body.confidence_label === 'HIGH'
                          ? '#155724'
                          : initiative.body.confidence_label === 'MEDIUM'
                          ? '#856404'
                          : '#721c24',
                    }}
                  >
                    {initiative.body.confidence_label} Confidence
                  </span>
                </div>
              )}
            </div>
          ))}
          </div>
        ) : (
          <p style={{ color: '#666', fontStyle: 'italic' }}>No core initiatives generated yet.</p>
        )}
      </section>

      {/* Sandbox Experiments */}
      <section style={{ marginBottom: '40px' }}>
        <h2 style={{ marginBottom: '20px', fontSize: '1.8rem', borderBottom: '3px solid #ffc107', paddingBottom: '10px' }}>
          Sandbox / Experimental
        </h2>
        {results.sandbox_initiatives && results.sandbox_initiatives.length > 0 ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {results.sandbox_initiatives.map((initiative) => (
              <div
              key={initiative.id}
              style={{
                backgroundColor: '#fff9e6',
                padding: '25px',
                borderRadius: '8px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                borderLeft: '4px solid #ffc107',
              }}
            >
              <h3 style={{ marginBottom: '15px', fontSize: '1.3rem', color: '#856404' }}>
                {initiative.title}
              </h3>
              {initiative.body && initiative.body.why_this_came_up && (
                <p style={{ marginBottom: '10px', color: '#666' }}>
                  <strong>Why this came up:</strong> {initiative.body.why_this_came_up}
                </p>
              )}
              {initiative.body && initiative.body.why_speculative && (
                <p style={{ marginBottom: '15px', color: '#856404', fontStyle: 'italic' }}>
                  <strong>Why speculative:</strong> {initiative.body.why_speculative}
                </p>
              )}
              {initiative.body && initiative.body.test_plan && Array.isArray(initiative.body.test_plan) && (
                  <div style={{ marginBottom: '15px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px' }}>Test plan:</strong>
                    <ul style={{ marginLeft: '20px' }}>
                      {initiative.body.test_plan.map((step: string, i: number) => (
                      <li key={i} style={{ marginBottom: '5px' }}>{step}</li>
                    ))}
                  </ul>
                </div>
              )}
              {initiative.body && initiative.body.stop_conditions && Array.isArray(initiative.body.stop_conditions) && (
                  <div style={{ marginBottom: '15px' }}>
                    <strong style={{ display: 'block', marginBottom: '8px' }}>Stop conditions:</strong>
                    <ul style={{ marginLeft: '20px' }}>
                      {initiative.body.stop_conditions.map((condition: string, i: number) => (
                      <li key={i} style={{ marginBottom: '5px' }}>{condition}</li>
                    ))}
                  </ul>
                </div>
              )}
              {initiative.body && initiative.body.how_to_measure && Array.isArray(initiative.body.how_to_measure) && (
                <div style={{ marginBottom: '15px' }}>
                  <strong style={{ display: 'block', marginBottom: '8px' }}>How to measure:</strong>
                  <ul style={{ marginLeft: '20px' }}>
                    {initiative.body.how_to_measure.map((measure: string, i: number) => (
                      <li key={i} style={{ marginBottom: '5px' }}>{measure}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          ))}
          </div>
        ) : (
          <p style={{ color: '#666', fontStyle: 'italic' }}>No sandbox initiatives generated yet.</p>
        )}
      </section>
    </div>
  );
}
