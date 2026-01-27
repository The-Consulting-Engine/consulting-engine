import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { api, Results, CompetitorAnalysisResponse } from '../api/client';

export default function ResultsPage() {
  const { cycleId } = useParams<{ cycleId: string }>();
  const [results, setResults] = useState<Results | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [competitors, setCompetitors] = useState<CompetitorAnalysisResponse | null>(null);
  const [competitorLoading, setCompetitorLoading] = useState(false);
  const [competitorPolling, setCompetitorPolling] = useState(false);

  useEffect(() => {
    if (!cycleId) return;
    loadResults();
    loadCompetitors();
  }, [cycleId]);

  // Poll for competitor results when running
  useEffect(() => {
    if (!competitorPolling || !cycleId) return;
    const interval = setInterval(async () => {
      try {
        const data = await api.getCompetitors(cycleId);
        setCompetitors(data);
        if (data.status === 'completed' || data.status === 'error') {
          setCompetitorPolling(false);
        }
      } catch {
        // ignore polling errors
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [competitorPolling, cycleId]);

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

  const loadCompetitors = async () => {
    if (!cycleId) return;
    setCompetitorLoading(true);
    try {
      const data = await api.getCompetitors(cycleId);
      setCompetitors(data);
      if (data.status === 'pending' || data.status === 'running') {
        setCompetitorPolling(true);
      }
    } catch {
      // No competitor analysis exists yet - that's fine
    } finally {
      setCompetitorLoading(false);
    }
  };

  const triggerCompetitorAnalysis = async () => {
    if (!cycleId) return;
    try {
      await api.enrichWithCompetitors(cycleId);
      setCompetitorPolling(true);
      loadCompetitors();
    } catch (err) {
      console.error('Failed to start competitor analysis:', err);
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

      {/* Top 4 Core Initiatives */}
      <section style={{ marginBottom: '40px' }}>
        <h2 style={{ marginBottom: '20px', fontSize: '1.8rem', borderBottom: '3px solid #007bff', paddingBottom: '10px' }}>
          Top 4 Core Initiatives
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

      {/* Competitive Intelligence */}
      <section style={{ marginBottom: '40px' }}>
        <h2 style={{ marginBottom: '20px', fontSize: '1.8rem', borderBottom: '3px solid #17a2b8', paddingBottom: '10px' }}>
          Competitive Intelligence
        </h2>

        {!competitors && !competitorLoading && (
          <div style={{ padding: '20px', backgroundColor: '#e8f4f8', borderRadius: '8px', textAlign: 'center' }}>
            <p style={{ marginBottom: '15px', color: '#666' }}>
              Run competitor analysis to get data-driven pricing and positioning insights.
            </p>
            <button
              onClick={triggerCompetitorAnalysis}
              style={{
                padding: '10px 24px',
                backgroundColor: '#17a2b8',
                color: 'white',
                border: 'none',
                borderRadius: '4px',
                cursor: 'pointer',
                fontSize: '1rem',
              }}
            >
              Start Competitor Analysis
            </button>
          </div>
        )}

        {competitors && (competitors.status === 'pending' || competitors.status === 'running') && (
          <div style={{ padding: '20px', backgroundColor: '#fff3cd', borderRadius: '8px', textAlign: 'center' }}>
            <p style={{ color: '#856404' }}>
              Competitor analysis is {competitors.status}... This may take a few minutes.
            </p>
            <div style={{ marginTop: '10px', fontSize: '0.9rem', color: '#856404' }}>
              Discovering competitors, scraping menus, analyzing prices...
            </div>
          </div>
        )}

        {competitors && competitors.status === 'error' && (
          <div style={{ padding: '20px', backgroundColor: '#f8d7da', borderRadius: '8px' }}>
            <p style={{ color: '#721c24' }}>
              <strong>Analysis failed:</strong> {competitors.error_message || 'Unknown error'}
            </p>
            <button
              onClick={triggerCompetitorAnalysis}
              style={{ marginTop: '10px', padding: '8px 16px', backgroundColor: '#17a2b8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
            >
              Retry
            </button>
          </div>
        )}

        {competitors && competitors.status === 'completed' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {/* Positioning summary */}
            {competitors.positioning && (
              <div style={{ backgroundColor: 'white', padding: '25px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', borderLeft: '4px solid #17a2b8' }}>
                <h3 style={{ marginBottom: '10px', color: '#17a2b8' }}>Market Position</h3>
                <p style={{ fontSize: '1.1rem', marginBottom: '10px' }}>
                  <strong>{(competitors.positioning.position || '').toUpperCase()}</strong>
                  {competitors.positioning.confidence != null && (
                    <span style={{ marginLeft: '10px', fontSize: '0.9rem', color: '#666' }}>
                      ({Math.round(competitors.positioning.confidence * 100)}% confidence)
                    </span>
                  )}
                </p>
                {competitors.positioning.description && (
                  <p style={{ color: '#666' }}>{competitors.positioning.description}</p>
                )}
              </div>
            )}

            {/* Premium validation */}
            {competitors.premium_validation && (
              <div style={{ backgroundColor: 'white', padding: '25px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', borderLeft: '4px solid #17a2b8' }}>
                <h3 style={{ marginBottom: '10px', color: '#17a2b8' }}>Premium Validation</h3>
                <p>
                  <strong>Status:</strong>{' '}
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: '8px',
                    fontSize: '0.85rem',
                    backgroundColor: competitors.premium_validation.validation_status === 'justified' ? '#d4edda'
                      : competitors.premium_validation.validation_status === 'misaligned' ? '#f8d7da' : '#fff3cd',
                    color: competitors.premium_validation.validation_status === 'justified' ? '#155724'
                      : competitors.premium_validation.validation_status === 'misaligned' ? '#721c24' : '#856404',
                  }}>
                    {competitors.premium_validation.validation_status}
                  </span>
                </p>
                {competitors.premium_validation.description && (
                  <p style={{ marginTop: '8px', color: '#666' }}>{competitors.premium_validation.description}</p>
                )}
              </div>
            )}

            {/* Competitive gaps */}
            {competitors.competitive_gaps && competitors.competitive_gaps.length > 0 && (
              <div style={{ backgroundColor: 'white', padding: '25px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', borderLeft: '4px solid #17a2b8' }}>
                <h3 style={{ marginBottom: '10px', color: '#17a2b8' }}>Competitive Gaps</h3>
                <ul style={{ marginLeft: '20px' }}>
                  {competitors.competitive_gaps.map((gap: any, i: number) => (
                    <li key={i} style={{ marginBottom: '8px' }}>
                      <strong>{gap.category || gap.gap_type}:</strong> {gap.description || gap.detail}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Executive summary */}
            {competitors.executive_summary && (
              <div style={{ backgroundColor: 'white', padding: '25px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', borderLeft: '4px solid #17a2b8' }}>
                <h3 style={{ marginBottom: '10px', color: '#17a2b8' }}>Executive Summary</h3>
                <pre style={{ whiteSpace: 'pre-wrap', fontFamily: 'inherit', fontSize: '0.95rem', color: '#333' }}>
                  {competitors.executive_summary}
                </pre>
              </div>
            )}

            {/* Strategic initiatives from competitor analysis */}
            {competitors.strategic_initiatives && competitors.strategic_initiatives.length > 0 && (
              <div style={{ backgroundColor: 'white', padding: '25px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', borderLeft: '4px solid #17a2b8' }}>
                <h3 style={{ marginBottom: '15px', color: '#17a2b8' }}>Data-Driven Initiatives</h3>
                {competitors.strategic_initiatives.map((init: any, i: number) => (
                  <div key={i} style={{ marginBottom: '15px', paddingBottom: '15px', borderBottom: i < competitors.strategic_initiatives!.length - 1 ? '1px solid #eee' : 'none' }}>
                    <strong>[{(init.priority || '').toUpperCase()}] {init.title}</strong>
                    {init.hypothesis && <p style={{ color: '#666', marginTop: '4px' }}>{init.hypothesis}</p>}
                    {init.evidence && <p style={{ color: '#888', marginTop: '4px', fontSize: '0.9rem' }}>Evidence: {init.evidence}</p>}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </section>
    </div>
  );
}
