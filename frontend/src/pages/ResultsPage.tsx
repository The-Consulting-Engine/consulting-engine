import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Box,
  Typography,
  Paper,
  Button,
  Grid,
  Card,
  CardContent,
  Chip,
  Alert,
  CircularProgress,
  Divider,
  List,
  ListItem,
  ListItemText,
} from '@mui/material'
import {
  Download,
  Description,
  Slideshow,
  ArrowBack,
  TrendingUp,
  TrendingDown,
} from '@mui/icons-material'
import { getResults, generateMemo, generateDeck, listReports, downloadReport } from '../api/client'

interface Fact {
  evidence_key: string
  label: string
  value?: number
  value_text?: string
  unit?: string
  period?: string
  source?: string
}

interface Initiative {
  initiative_id: string
  title: string
  category: string
  description: string
  rank: number
  impact_low?: number
  impact_mid?: number
  impact_high?: number
  impact_unit?: string
  priority_score?: number
  explanation?: string
  assumptions?: string[]
  data_gaps?: string[]
}

interface Results {
  run_id: number
  mode: string
  confidence_score: number
  status: string
  analytics_facts: Fact[]
  initiatives: Initiative[]
}

function ResultsPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [results, setResults] = useState<Results | null>(null)
  const [reports, setReports] = useState<any[]>([])
  const [generating, setGenerating] = useState<string | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    loadResults()
    loadReports()
  }, [runId])

  const loadResults = async () => {
    try {
      const data = await getResults(Number(runId))
      setResults(data)
    } catch (err) {
      console.error('Failed to load results:', err)
    }
  }

  const loadReports = async () => {
    try {
      const data = await listReports(Number(runId))
      setReports(data.reports)
    } catch (err) {
      console.error('Failed to load reports:', err)
    }
  }

  const handleGenerateMemo = async () => {
    try {
      setError('')
      setGenerating('memo')
      await generateMemo(Number(runId))
      await loadReports()
      setGenerating(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate memo')
      setGenerating(null)
    }
  }

  const handleGenerateDeck = async () => {
    try {
      setError('')
      setGenerating('deck')
      await generateDeck(Number(runId))
      await loadReports()
      setGenerating(null)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to generate deck')
      setGenerating(null)
    }
  }

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      maximumFractionDigits: 0,
    }).format(value)
  }

  if (!results) {
    return (
      <Container>
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      </Container>
    )
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 3 }}>
          <Button startIcon={<ArrowBack />} onClick={() => navigate('/')}>
            Back
          </Button>
          <Typography variant="h4">
            Diagnostic Results
          </Typography>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {/* Mode and Confidence */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Operating Mode
              </Typography>
              <Chip
                label={results.mode}
                color="primary"
                size="large"
                sx={{ fontSize: '1rem', py: 2 }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <Typography variant="h6" gutterBottom>
                Confidence Level
              </Typography>
              <Chip
                label={`${(results.confidence_score * 100).toFixed(0)}%`}
                color={results.confidence_score > 0.7 ? 'success' : 'warning'}
                size="large"
                sx={{ fontSize: '1rem', py: 2 }}
              />
            </Grid>
          </Grid>
        </Paper>

        {/* Key Metrics */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Key Metrics
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Grid container spacing={2}>
            {results.analytics_facts.slice(0, 6).map((fact, idx) => (
              <Grid item xs={12} sm={6} md={4} key={idx}>
                <Card variant="outlined">
                  <CardContent>
                    <Typography variant="caption" color="text.secondary" gutterBottom>
                      {fact.label}
                    </Typography>
                    <Typography variant="h6">
                      {fact.unit === 'currency' && fact.value
                        ? formatCurrency(fact.value)
                        : fact.unit === 'percentage' && fact.value
                        ? `${fact.value.toFixed(1)}%`
                        : fact.value || fact.value_text || 'N/A'}
                    </Typography>
                    {fact.period && (
                      <Typography variant="caption" color="text.secondary">
                        {fact.period}
                      </Typography>
                    )}
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>
        </Paper>

        {/* Initiatives */}
        <Paper sx={{ p: 3, mb: 3 }}>
          <Typography variant="h5" gutterBottom>
            Recommended Initiatives
          </Typography>
          <Divider sx={{ mb: 2 }} />
          
          {results.initiatives.map((initiative) => (
            <Card key={initiative.initiative_id} sx={{ mb: 2 }} variant="outlined">
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2, mb: 1 }}>
                  <Chip label={`#${initiative.rank}`} color="primary" size="small" />
                  <Box sx={{ flexGrow: 1 }}>
                    <Typography variant="h6">
                      {initiative.title}
                    </Typography>
                    <Chip label={initiative.category} size="small" sx={{ mt: 0.5 }} />
                  </Box>
                  {initiative.impact_mid && (
                    <Box sx={{ textAlign: 'right' }}>
                      <Typography variant="caption" color="text.secondary">
                        Estimated Impact
                      </Typography>
                      <Typography variant="h6" color="success.main">
                        {formatCurrency(initiative.impact_low || 0)} - {formatCurrency(initiative.impact_high || 0)}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        annual
                      </Typography>
                    </Box>
                  )}
                </Box>

                {initiative.explanation && (
                  <Typography variant="body2" sx={{ mt: 2, mb: 2 }}>
                    {initiative.explanation}
                  </Typography>
                )}

                {initiative.assumptions && initiative.assumptions.length > 0 && (
                  <Box sx={{ mt: 2 }}>
                    <Typography variant="caption" color="text.secondary" fontWeight="bold">
                      Key Assumptions:
                    </Typography>
                    <List dense>
                      {initiative.assumptions.map((assumption, idx) => (
                        <ListItem key={idx} sx={{ py: 0 }}>
                          <ListItemText
                            primary={`• ${assumption}`}
                            primaryTypographyProps={{ variant: 'caption' }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}

                {initiative.data_gaps && initiative.data_gaps.length > 0 && (
                  <Box sx={{ mt: 1 }}>
                    <Typography variant="caption" color="warning.main" fontWeight="bold">
                      Data Gaps:
                    </Typography>
                    <List dense>
                      {initiative.data_gaps.map((gap, idx) => (
                        <ListItem key={idx} sx={{ py: 0 }}>
                          <ListItemText
                            primary={`• ${gap}`}
                            primaryTypographyProps={{ variant: 'caption', color: 'text.secondary' }}
                          />
                        </ListItem>
                      ))}
                    </List>
                  </Box>
                )}
              </CardContent>
            </Card>
          ))}
        </Paper>

        {/* Reports */}
        <Paper sx={{ p: 3 }}>
          <Typography variant="h5" gutterBottom>
            Reports & Downloads
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Grid container spacing={2}>
            <Grid item xs={12} sm={6}>
              <Button
                variant="outlined"
                fullWidth
                startIcon={<Description />}
                onClick={handleGenerateMemo}
                disabled={generating === 'memo'}
              >
                {generating === 'memo' ? 'Generating...' : 'Generate Executive Memo'}
              </Button>
            </Grid>
            <Grid item xs={12} sm={6}>
              <Button
                variant="outlined"
                fullWidth
                startIcon={<Slideshow />}
                onClick={handleGenerateDeck}
                disabled={generating === 'deck'}
              >
                {generating === 'deck' ? 'Generating...' : 'Generate PowerPoint Deck'}
              </Button>
            </Grid>
          </Grid>

          {reports.length > 0 && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Available Reports
              </Typography>
              <List>
                {reports.map((report) => (
                  <ListItem
                    key={report.report_id}
                    secondaryAction={
                      <Button
                        startIcon={<Download />}
                        href={downloadReport(report.report_id)}
                        target="_blank"
                      >
                        Download
                      </Button>
                    }
                  >
                    <ListItemText
                      primary={report.report_type === 'memo' ? 'Executive Memo' : 'PowerPoint Deck'}
                      secondary={new Date(report.created_at).toLocaleString()}
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}
        </Paper>
      </Box>
    </Container>
  )
}

export default ResultsPage
