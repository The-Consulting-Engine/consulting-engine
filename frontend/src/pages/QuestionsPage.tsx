import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Box,
  Typography,
  Paper,
  Button,
  FormControl,
  FormLabel,
  RadioGroup,
  FormControlLabel,
  Radio,
  Checkbox,
  Alert,
  CircularProgress,
  Divider,
  TextField,
  FormHelperText,
} from '@mui/material'
import { CheckCircle, ArrowBack, ArrowForward } from '@mui/icons-material'
import { getQuestions, saveResponses, getResponses } from '../api/client'

interface Question {
  question_id: string
  section: string
  prompt: string
  type: string
  options?: Array<{
    value: string
    label: string
  }>
  required: boolean
  input_type?: string
  placeholder?: string
  help_text?: string
}

function QuestionsPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [questions, setQuestions] = useState<Question[]>([])
  const [responses, setResponses] = useState<Record<string, any>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    loadQuestions()
  }, [runId])

  const loadQuestions = async () => {
    try {
      setLoading(true)
      const data = await getQuestions(Number(runId))
      setQuestions(data.questions || [])
      
      // Try to load existing responses
      try {
        const existing = await getResponses(Number(runId))
        if (existing.responses && existing.responses.length > 0) {
          const responseMap: Record<string, any> = {}
          existing.responses.forEach((r: any) => {
            responseMap[r.question_id] = r.response_value
          })
          setResponses(responseMap)
        } else {
          // Use default responses for auto-fill
          setResponses(data.default_responses || {})
        }
      } catch (err) {
        // No existing responses, use defaults
        setResponses(data.default_responses || {})
      }
      
      setLoading(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to load questions')
      setLoading(false)
    }
  }

  const handleSingleSelect = (questionId: string, value: string) => {
    setResponses(prev => ({ ...prev, [questionId]: value }))
  }

  const handleMultiSelect = (questionId: string, value: string, checked: boolean) => {
    setResponses(prev => {
      const current = prev[questionId] || []
      const currentArray = Array.isArray(current) ? current : [current]
      
      if (checked) {
        return { ...prev, [questionId]: [...currentArray, value] }
      } else {
        return { ...prev, [questionId]: currentArray.filter((v: string) => v !== value) }
      }
    })
  }

  const handleTextInput = (questionId: string, value: string) => {
    setResponses(prev => ({ ...prev, [questionId]: value }))
  }

  const handleSave = async () => {
    try {
      setError('')
      setSaving(true)
      
      // Convert responses to API format
      const responseArray = Object.entries(responses).map(([question_id, response_value]) => ({
        question_id,
        response_value
      }))
      
      await saveResponses(Number(runId), responseArray)
      setSuccess(true)
      setSaving(false)
      
      // Navigate to upload page after 1 second
      setTimeout(() => {
        navigate(`/run/${runId}`)
      }, 1000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to save responses')
      setSaving(false)
    }
  }

  const groupBySection = () => {
    const grouped: Record<string, Question[]> = {}
    questions.forEach(q => {
      if (!grouped[q.section]) {
        grouped[q.section] = []
      }
      grouped[q.section].push(q)
    })
    return grouped
  }

  if (loading) {
    return (
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    )
  }

  const grouped = groupBySection()
  const sections = Object.keys(grouped)

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Typography variant="h4">
            Intake Questions
          </Typography>
        </Box>

        <Alert severity="info" sx={{ mb: 3 }}>
          These questions help us tailor recommendations to your specific situation.
          <strong> Default answers are pre-filled</strong> - review and adjust as needed.
        </Alert>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            Responses saved! Redirecting to upload page...
          </Alert>
        )}

        {sections.map((section) => (
          <Paper key={section} sx={{ p: 3, mb: 3 }}>
            <Typography variant="h6" sx={{ mb: 2, color: 'primary.main' }}>
              {section}
            </Typography>
            <Divider sx={{ mb: 2 }} />

            {grouped[section].map((question) => (
              <Box key={question.question_id} sx={{ mb: 4 }}>
                <FormControl component="fieldset" fullWidth>
                  <FormLabel component="legend">
                    {question.prompt}
                    {question.required && <span style={{ color: 'red' }}> *</span>}
                  </FormLabel>

                  {(question.type === 'single_select' || question.type === 'yes_no') && question.options && (
                    <RadioGroup
                      value={responses[question.question_id] || ''}
                      onChange={(e) => handleSingleSelect(question.question_id, e.target.value)}
                      sx={{ mt: 1 }}
                    >
                      {question.options.map((option) => (
                        <FormControlLabel
                          key={option.value}
                          value={option.value}
                          control={<Radio />}
                          label={option.label}
                        />
                      ))}
                    </RadioGroup>
                  )}

                  {question.type === 'multi_select' && question.options && (
                    <Box sx={{ mt: 1 }}>
                      {question.options.map((option) => {
                        const currentResponses = responses[question.question_id] || []
                        const isArray = Array.isArray(currentResponses)
                        const isChecked = isArray
                          ? currentResponses.includes(option.value)
                          : currentResponses === option.value
                        
                        return (
                          <FormControlLabel
                            key={option.value}
                            control={
                              <Checkbox
                                checked={isChecked}
                                onChange={(e) =>
                                  handleMultiSelect(
                                    question.question_id,
                                    option.value,
                                    e.target.checked
                                  )
                                }
                              />
                            }
                            label={option.label}
                          />
                        )
                      })}
                    </Box>
                  )}

                  {question.type === 'text' && (
                    <Box sx={{ mt: 1 }}>
                      <TextField
                        fullWidth
                        type={question.input_type === 'number' ? 'number' : 'text'}
                        value={responses[question.question_id] || ''}
                        onChange={(e) => handleTextInput(question.question_id, e.target.value)}
                        placeholder={question.placeholder}
                        variant="outlined"
                        size="small"
                        InputProps={{
                          inputProps: question.input_type === 'number' ? { min: 0, step: 'any' } : {}
                        }}
                      />
                      {question.help_text && (
                        <FormHelperText>{question.help_text}</FormHelperText>
                      )}
                    </Box>
                  )}
                </FormControl>
              </Box>
            ))}
          </Paper>
        ))}

        <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
          <Button
            variant="contained"
            size="large"
            startIcon={saving ? <CircularProgress size={20} /> : <CheckCircle />}
            onClick={handleSave}
            disabled={saving}
          >
            {saving ? 'Saving...' : 'Save & Continue'}
          </Button>
        </Box>
      </Box>
    </Container>
  )
}

export default QuestionsPage
