import { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Questionnaire, Question, MenuItemInput } from '../api/client';

export default function QuestionsPage() {
  const { cycleId } = useParams<{ cycleId: string }>();
  const navigate = useNavigate();
  const [questionnaire, setQuestionnaire] = useState<Questionnaire | null>(null);
  const [responses, setResponses] = useState<Record<string, any>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [menuItems, setMenuItems] = useState<MenuItemInput[]>([]);
  const [menuUploaded, setMenuUploaded] = useState(false);
  const [menuUploadMsg, setMenuUploadMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

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
        "R0_1_restaurant_name": "Thai Basil Kitchen",
        "R0_2_address": "200 Crown St, New Haven, CT 06510",
        "R0_3_cuisine_type": "Thai",
        "R0_4_service_type": "Fast Casual",
        "R0_5_price_tier": "$$ ($15-30)",
        "R0_6_menu_input_method": "I'll enter items manually",
        "A0_1_concept_type": "Fast casual",
        "A0_2_order_channels_ranked": ["Walk-in / counter", "Online pickup", "Third-party delivery"],
        "A0_3_primary_dayparts": ["Lunch", "Dinner"],
        "A0_4_employee_count_per_location": "11–25",
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
      
      // Generate results (backend timeout 120s per OpenAI call; 4 steps, mock fallback on fail)
      console.log('Starting generation for cycle:', cycleId);
      const generatePromise = api.generate(cycleId);
      const timeoutMs = 150_000; // 150s; backend 120s per call
      const timeoutPromise = new Promise<never>((_, reject) =>
        setTimeout(() => reject(new Error(`Generation timed out after ${timeoutMs / 1000} seconds. Check backend logs (docker compose logs api) for [OPENAI] / [GENERATE] messages.`)), timeoutMs)
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

  const handleCsvUpload = async (file: File) => {
    if (!cycleId) return;
    try {
      setMenuUploadMsg(null);
      const result = await api.uploadMenuCsv(cycleId, file);
      setMenuUploaded(true);
      setMenuUploadMsg(`Uploaded ${result.items_added} menu items`);
    } catch (err) {
      setMenuUploadMsg(err instanceof Error ? err.message : 'Upload failed');
    }
  };

  const handleAddManualItem = () => {
    setMenuItems([...menuItems, { item_name: '', price: '', category: '', description: '' }]);
  };

  const handleMenuItemChange = (index: number, field: keyof MenuItemInput, value: string) => {
    const updated = [...menuItems];
    updated[index] = { ...updated[index], [field]: value };
    setMenuItems(updated);
  };

  const handleRemoveMenuItem = (index: number) => {
    setMenuItems(menuItems.filter((_, i) => i !== index));
  };

  const handleSaveManualMenu = async () => {
    if (!cycleId) return;
    const validItems = menuItems.filter((i) => i.item_name && i.price);
    if (validItems.length === 0) {
      setMenuUploadMsg('Add at least one item with name and price');
      return;
    }
    try {
      setMenuUploadMsg(null);
      const result = await api.addMenuItems(cycleId, validItems);
      setMenuUploaded(true);
      setMenuUploadMsg(`Saved ${result.items_added} menu items`);
    } catch (err) {
      setMenuUploadMsg(err instanceof Error ? err.message : 'Save failed');
    }
  };

  const renderMenuInput = () => {
    const method = responses['R0_6_menu_input_method'];
    if (!method || method === "Find my menu on Uber Eats (we'll scrape it)") return null;

    return (
      <div style={{ marginTop: '20px', padding: '20px', backgroundColor: '#f0f7ff', borderRadius: '8px', border: '1px solid #bee3f8' }}>
        <h3 style={{ marginBottom: '15px', fontSize: '1.2rem' }}>Menu Items</h3>

        {method === "I'll upload a CSV file" && (
          <div>
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '10px' }}>
              Upload a CSV with columns: item_name, price (required), category, description (optional)
            </p>
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (file) handleCsvUpload(file);
              }}
              style={{ marginBottom: '10px' }}
            />
          </div>
        )}

        {method === "I'll enter items manually" && (
          <div>
            {menuItems.map((item, idx) => (
              <div key={idx} style={{ display: 'flex', gap: '8px', marginBottom: '8px', alignItems: 'center' }}>
                <input
                  type="text"
                  placeholder="Item name"
                  value={item.item_name}
                  onChange={(e) => handleMenuItemChange(idx, 'item_name', e.target.value)}
                  style={{ flex: 2, padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                />
                <input
                  type="text"
                  placeholder="Price (e.g. 12.99)"
                  value={item.price}
                  onChange={(e) => handleMenuItemChange(idx, 'price', e.target.value)}
                  style={{ flex: 1, padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                />
                <input
                  type="text"
                  placeholder="Category"
                  value={item.category || ''}
                  onChange={(e) => handleMenuItemChange(idx, 'category', e.target.value)}
                  style={{ flex: 1, padding: '8px', border: '1px solid #ddd', borderRadius: '4px' }}
                />
                <button
                  type="button"
                  onClick={() => handleRemoveMenuItem(idx)}
                  style={{ padding: '8px 12px', border: '1px solid #ddd', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'white' }}
                >
                  x
                </button>
              </div>
            ))}
            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <button
                type="button"
                onClick={handleAddManualItem}
                style={{ padding: '8px 16px', border: '1px solid #007bff', borderRadius: '4px', cursor: 'pointer', backgroundColor: 'white', color: '#007bff' }}
              >
                + Add Item
              </button>
              {menuItems.length > 0 && (
                <button
                  type="button"
                  onClick={handleSaveManualMenu}
                  style={{ padding: '8px 16px', border: 'none', borderRadius: '4px', cursor: 'pointer', backgroundColor: '#007bff', color: 'white' }}
                >
                  Save Menu Items
                </button>
              )}
            </div>
          </div>
        )}

        {menuUploadMsg && (
          <div style={{ marginTop: '10px', padding: '8px 12px', borderRadius: '4px', backgroundColor: menuUploaded ? '#d4edda' : '#f8d7da', color: menuUploaded ? '#155724' : '#721c24' }}>
            {menuUploadMsg}
          </div>
        )}
      </div>
    );
  };

  const renderQuestion = (question: Question) => {
    const value = responses[question.id];

    if (question.type === 'single_select') {
      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          {question.helper_text && (
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>{question.helper_text}</p>
          )}
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

    if (question.type === 'ranking') {
      const currentRanking = Array.isArray(value) ? value : [];
      const availableOptions = question.options || [];
      const unranked = availableOptions.filter((opt) => !currentRanking.includes(opt));

      const moveItem = (fromIndex: number, toIndex: number) => {
        const newRanking = [...currentRanking];
        const [moved] = newRanking.splice(fromIndex, 1);
        newRanking.splice(toIndex, 0, moved);
        handleResponseChange(question.id, newRanking);
      };

      const addToRanking = (option: string) => {
        if (currentRanking.length < (question.ranking_max || availableOptions.length)) {
          handleResponseChange(question.id, [...currentRanking, option]);
        }
      };

      const removeFromRanking = (option: string) => {
        handleResponseChange(question.id, currentRanking.filter((v) => v !== option));
      };

      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          {question.helper_text && (
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '12px' }}>{question.helper_text}</p>
          )}
          
          {/* Ranked items */}
          <div style={{ marginBottom: '15px' }}>
            {currentRanking.map((option, index) => (
              <div
                key={option}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '10px',
                  marginBottom: '8px',
                  backgroundColor: '#f8f9fa',
                  border: '1px solid #ddd',
                  borderRadius: '4px',
                }}
              >
                <span style={{ marginRight: '12px', fontWeight: 'bold', color: '#007bff', minWidth: '30px' }}>
                  #{index + 1}
                </span>
                <span style={{ flex: 1 }}>{option}</span>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {index > 0 && (
                    <button
                      type="button"
                      onClick={() => moveItem(index, index - 1)}
                      style={{
                        padding: '4px 8px',
                        border: '1px solid #ddd',
                        backgroundColor: 'white',
                        cursor: 'pointer',
                        borderRadius: '4px',
                      }}
                      title="Move up"
                    >
                      ↑
                    </button>
                  )}
                  {index < currentRanking.length - 1 && (
                    <button
                      type="button"
                      onClick={() => moveItem(index, index + 1)}
                      style={{
                        padding: '4px 8px',
                        border: '1px solid #ddd',
                        backgroundColor: 'white',
                        cursor: 'pointer',
                        borderRadius: '4px',
                      }}
                      title="Move down"
                    >
                      ↓
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={() => removeFromRanking(option)}
                    style={{
                      padding: '4px 8px',
                      border: '1px solid #ddd',
                      backgroundColor: 'white',
                      cursor: 'pointer',
                      borderRadius: '4px',
                      marginLeft: '4px',
                    }}
                    title="Remove"
                  >
                    ×
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Unranked items */}
          {unranked.length > 0 && (
            <div>
              <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>Add to ranking:</div>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                {unranked.map((option) => (
                  <button
                    key={option}
                    type="button"
                    onClick={() => addToRanking(option)}
                    disabled={currentRanking.length >= (question.ranking_max || availableOptions.length)}
                    style={{
                      padding: '8px 12px',
                      border: '1px solid #ddd',
                      backgroundColor: 'white',
                      cursor: currentRanking.length >= (question.ranking_max || availableOptions.length) ? 'not-allowed' : 'pointer',
                      borderRadius: '4px',
                      opacity: currentRanking.length >= (question.ranking_max || availableOptions.length) ? 0.5 : 1,
                    }}
                  >
                    + {option}
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      );
    }

    if (question.type === 'short_text') {
      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          {question.helper_text && (
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>{question.helper_text}</p>
          )}
          <input
            type="text"
            value={value || ''}
            onChange={(e) => {
              const text = e.target.value;
              if (!question.max_chars || text.length <= question.max_chars) {
                handleResponseChange(question.id, text);
              }
            }}
            style={{
              width: '100%',
              padding: '10px',
              fontSize: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontFamily: 'inherit',
              boxSizing: 'border-box',
            }}
            placeholder={question.placeholder || ''}
          />
          {question.max_chars && (
            <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '4px' }}>
              {(value || '').length} / {question.max_chars} characters
            </div>
          )}
        </div>
      );
    }

    if (question.type === 'long_text') {
      return (
        <div key={question.id} style={{ marginBottom: '20px' }}>
          <label style={{ display: 'block', marginBottom: '8px', fontWeight: '500' }}>
            {question.label} {question.required && <span style={{ color: 'red' }}>*</span>}
          </label>
          {question.helper_text && (
            <p style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>{question.helper_text}</p>
          )}
          <textarea
            value={value || ''}
            onChange={(e) => {
              const text = e.target.value;
              if (!question.max_chars || text.length <= question.max_chars) {
                handleResponseChange(question.id, text);
              }
            }}
            rows={6}
            style={{
              width: '100%',
              padding: '10px',
              fontSize: '1rem',
              border: '1px solid #ddd',
              borderRadius: '4px',
              fontFamily: 'inherit',
            }}
            placeholder={question.placeholder || 'Enter your response...'}
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
            {section.description && (
              <p style={{ fontSize: '0.95rem', color: '#666', marginBottom: '20px' }}>{section.description}</p>
            )}
            {section.questions
              .filter((q) => {
                // Hide questions whose depends_on field has no value
                if (q.depends_on && !responses[q.depends_on]) return false;
                return true;
              })
              .map((q) => renderQuestion(q))}

            {/* Menu input UI after R0 section */}
            {section.id === 'R0_restaurant_identity' && renderMenuInput()}
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
          {saving ? 'Generating... (up to ~2 min per step; watch docker logs for [OPENAI])' : 'Submit & Generate Results'}
        </button>
        
        {saving && (
          <div style={{ marginTop: '15px', textAlign: 'center', color: '#666', fontSize: '0.9rem' }}>
            Generating... Run <code>docker compose logs -f api</code> to see [GENERATE] / [OPENAI] progress.
          </div>
        )}
      </div>
    </div>
  );
}
