import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Questionnaire, Question } from '../api/client';

export default function QuestionsPage() {
  const { cycleId } = useParams<{ cycleId: string }>();
  const navigate = useNavigate();
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!cycleId) return;
    loadQuestionnaire();
  }, [cycleId]);

  const loadQuestionnaire = async () => {
    if (!cycleId) return;
    try {
      const data = await api.getQuestionnaire(cycleId);
      setQuestionnaire(data);
      
      // Preload default test answers for demo
      const defaultResponses: Record<string, any> = {
        "A1_role": "Owner/operator",
        "A2_constraints": ["None of these"],
        "A3_locations_scope": "1",
        "B1_drags": ["Labor too high", "Staffing chaotic", "Too much discounting/comps"],
        "B2_suspected_leak": "Overstaffing / too many hours",
        "C1_staffing_state": "Swings wildly",
        "C2_schedule_confidence": 2,
        "C3_ops_stressors": ["Service is slow during rush", "Training is inconsistent"],
        "D1_menu_size": "Too big/complicated",
        "D2_last_price_increase": "More than 12 months ago",
        "D3_upselling": "Rare",
        "E1_channels_used": ["Google Business Profile", "Yelp", "Instagram"],
        "E2_channels_drive": ["Google Business Profile", "Word of mouth", "Yelp"],
        "E3_marketing_owner": "No one/ad hoc",
        "E4_marketing_roi_confidence": 2,
        "F1_review_frequency": "Ad hoc",
        "F2_underperformance_response": "We talk about it but follow-through is inconsistent"
      };
      setResponses(defaultResponses);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load questionnaire');
    } finally {
      setLoading(false);
    }
  };

  const handleResponseChange = (questionId: string, value: any) => {
    setResponses((prev) => ({ ...prev, [questionId]: value }));
  };

  const handleSubmit = async () => {
    if (!cycleId) {
      setError('Cycle ID is missing');
      return;
    }

    // Validate required questions
    if (!questionnaire) {
      setError('Questionnaire not loaded');
      return;
    }
    
    const missing = questionnaire.sections
      .flatMap((s) => s.questions)
      .filter((q) => q.required && !responses[q.id]);

    if (missing.length > 0) {
      setError(`Please answer all required questions (${missing.length} missing)`);
      return;
    }

    setSaving(true);
    setError(null);

    try {
      // Save questionnaire
      await api.saveQuestionnaire(cycleId, responses);
      
      // Generate results (with timeout; 4 LLM steps can take 60–90s with OpenAI)
      console.log('Starting generation for cycle:', cycleId);
      const generatePromise = api.generate(cycleId);
      const timeoutMs = 90_000;
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`Generation timed out after ${timeoutMs / 1000} seconds. Check backend logs for details.`)), timeoutMs)
      );

      const result = await Promise.race([generatePromise, timeoutPromise]);
      console.log('Generation completed:', result);
      
      // Navigate to results
      navigate(`/cycles/${cycleId}/results`);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to process questionnaire';
      setError(errorMessage);
      console.error('Questionnaire submission error:', err);
      // Ensure saving state is cleared even on error
      setSaving(false);
    } finally {
      setSaving(false);
    }
  };

  const renderQuestion = (question: Question) => {
    const value = responses[question.id];

    if (question.type === 'single_select') {
      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          <select
            value={value || ''}
            onChange={(e) => handleResponseChange(question.id, e.target.value)}
            style={{
              width: '100%',
              padding: '10px',
              fontSize: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
            }}
          >
            <option value="">Select an option</option>
            {question.options?.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        </div>
      );
    }

    if (question.type === 'multi_select') {
      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {question.options?.map((opt) => {
              const selected = Array.isArray(value) && value.includes(opt);
              return (
                <label key={opt} style={{ display: 'flex', alignItems: 'center', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={selected}
                    onChange={(e) => {
                      const current = Array.isArray(value) ? value : [];
                      if (e.target.checked) {
                        if (!question.max_selected || current.length < question.max_selected) {
                          handleResponseChange(question.id, [...current, opt]);
                        }
                      } else {
                        handleResponseChange(question.id, current.filter((v) => v !== opt));
                      }
                    }}
                    style={{ marginRight: '8px' }}
                  />
                  {opt}
                </label>
              );
            })}
          </div>
        </div>
      );
    }

    if (question.type === 'likert_1_5') {
      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
            <span style={{ fontSize: '0.9rem', color: '#666' }}>{question.min_label}</span>
            <span style={{ fontSize: '0.9rem', color: '#666' }}>{question.max_label}</span>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            {[1, 2, 3, 4, 5].map((num) => (
              <button
                key={num}
                type="button"
                onClick={() => handleResponseChange(question.id, num)}
                style={{
                  flex: 1,
                  padding: '10px',
                  border: `2px solid ${value === num ? '#007bff' : '#ddd'}`,
                  backgroundColor: value === num ? '#007bff' : 'white',
                  color: value === num ? 'white' : '#333',
                  borderRadius: '4px',
                  cursor: 'pointer',
                }}
              >
                {num}
              </button>
            ))}
          </div>
        </div>
      );
    }

    if (question.type === 'short_text' || question.type === 'long_text') {
      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          <textarea
            value={value || ''}
            onChange={(e) => {
              const text = e.target.value;
              if (!question.max_chars || text.length <= question.max_chars) {
                handleResponseChange(question.id, text);
              }
            }}
            rows={question.type === 'long_text' ? 6 : 3}
            style={{
              width: '100%',
              padding: '10px',
              fontSize: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontFamily: 'inherit',
            }}
            placeholder={question.type === 'long_text' ? 'Enter your response...' : ''}
          />
          {question.max_chars && (
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '4px' }}>
              {(value || '').length} / {question.max_chars} characters
            </div>
          )}
        </div>
      );
    }

    return null;
  };

  if (loading) {
    return <div style={{ padding: '50px', textAlign: 'center' }}>Loading questionnaire...</div>;
  }

  if (!questionnaire) {
    return <div style={{ padding: '50px', textAlign: 'center' }}>Questionnaire not found</div>;
  }

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px' }}>
      <h1 style={{ marginBottom: '10px' }}>{questionnaire.title}</h1>
      <p style={{ marginBottom: '30px', color: '#666' }}>{questionnaire.description}</p>

      <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        {questionnaire.sections.map((section) => (
          <div key={section.id} style={{ marginBottom: '40px' }}>
            <h2 style={{ marginBottom: '20px', fontSize: '1.5rem', borderBottom: '2px solid #eee', paddingBottom: '10px' }}>
              {section.title}
            </h2>
            {section.questions.map((q) => renderQuestion(q))}
          </div>
        ))}

        {error && (
          <div style={{ color: 'red', marginBottom: '20px', padding: '10px', backgroundColor: '#ffe6e6', borderRadius: '4px' }}>
            {error}
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={saving}
          style={{
            width: '100%',
            padding: '15px',
            fontSize: '1.1rem',
            backgroundColor: saving ? '#ccc' : '#28a745',
            color: 'white',
            border: 'none',
            borderRadius: '4px',
            cursor: saving ? 'not-allowed' : 'pointer',
            fontWeight: 'bold',
          }}
        >
          {saving ? 'Generating... (this may take 30-90 seconds)' : 'Submit & Generate Results'}
        </button>
        
        {saving && (
          <div style={{ marginTop: '15px', textAlign: 'center', color: '#666', fontSize: '0.9rem' }}>
            Generating initiatives... Check browser console (F12) for progress or errors.
          </div>
        )}
      </div>
    </div>
  );
}
