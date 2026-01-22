import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Container,
  Box,
  Typography,
  Paper,
  Button,
  Stepper,
  Step,
  StepLabel,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
} from '@mui/material'
import { CloudUpload, CheckCircle, PlayArrow } from '@mui/icons-material'
import {
  getRun,
  uploadFile,
  listUploads,
  suggestMappings,
  confirmMappings,
  getMappings,
  analyzeRun,
} from '../api/client'

interface Upload {
  upload_id: number
  filename: string
  pack_type: string
  row_count: number
  column_profile: any
}

interface Mapping {
  canonical_field: string
  source_columns: string[]
  transform: string
  confidence: number
  reasoning?: string
}

function RunPage() {
  const { runId } = useParams<{ runId: string }>()
  const navigate = useNavigate()
  const [activeStep, setActiveStep] = useState(0)
  const [run, setRun] = useState<any>(null)
  const [uploads, setUploads] = useState<Upload[]>([])
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [selectedPackType, setSelectedPackType] = useState('PNL')
  const [uploading, setUploading] = useState(false)
  const [currentUpload, setCurrentUpload] = useState<Upload | null>(null)
  const [suggestedMappings, setSuggestedMappings] = useState<Mapping[]>([])
  const [confirmedMappingsCount, setConfirmedMappingsCount] = useState(0)
  const [loadingMappings, setLoadingMappings] = useState(false)
  const [analyzing, setAnalyzing] = useState(false)
  const [waitingForApproval, setWaitingForApproval] = useState(false)
  const [error, setError] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const [mappingSuccess, setMappingSuccess] = useState(false)
  const [mappedUploadIds, setMappedUploadIds] = useState<Set<number>>(new Set())

  useEffect(() => {
    loadRun()
    loadUploads()
    loadConfirmedMappings()
  }, [runId])

  const loadRun = async () => {
    try {
      const data = await getRun(Number(runId))
      setRun(data)
      
      // Set step based on status
      if (data.status === 'created') setActiveStep(0)
      else if (data.status === 'mapping') setActiveStep(1)
      else if (data.status === 'analyzing') setActiveStep(2)
      else if (data.status === 'complete') navigate(`/results/${runId}`)
    } catch (err) {
      console.error('Failed to load run:', err)
    }
  }

  const loadUploads = async () => {
    try {
      const data = await listUploads(Number(runId))
      setUploads(data.uploads)
    } catch (err) {
      console.error('Failed to load uploads:', err)
    }
  }

  const loadConfirmedMappings = async () => {
    try {
      const data = await getMappings(Number(runId))
      setConfirmedMappingsCount(data.mappings.length)
      // Track which uploads have mappings
      const mappedIds = new Set(data.mappings.map((m: any) => m.upload_id))
      setMappedUploadIds(mappedIds)
    } catch (err) {
      console.error('Failed to load mappings:', err)
    }
  }

  const handleUpload = async () => {
    if (!selectedFile) return

    try {
      setError('')
      setUploading(true)
      const data = await uploadFile(Number(runId), selectedPackType, selectedFile)
      await loadUploads()
      await loadRun()
      setSelectedFile(null)
      setUploading(false)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload file')
      setUploading(false)
    }
  }

  const handleSuggestMappings = async (upload: Upload) => {
    try {
      setError('')
      setLoadingMappings(true)
      setCurrentUpload(upload)
      const data = await suggestMappings(Number(runId), upload.upload_id)
      setSuggestedMappings(data.suggested_mappings)
      setLoadingMappings(false)
      setActiveStep(1)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to suggest mappings')
      setLoadingMappings(false)
    }
  }

  const handleConfirmMappings = async () => {
    if (!currentUpload) return

    try {
      setError('')
      setMappingSuccess(false)
      await confirmMappings(Number(runId), {
        upload_id: currentUpload.upload_id,
        mappings: suggestedMappings,
      })
      setMappingSuccess(true)
      setSuggestedMappings([])
      setCurrentUpload(null)
      await loadRun()
      await loadConfirmedMappings()
      
      // Auto-hide success message after 3 seconds
      setTimeout(() => setMappingSuccess(false), 3000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to confirm mappings')
      setMappingSuccess(false)
    }
  }

  const handleAnalyze = () => {
    setWaitingForApproval(true)
  }

  const handleSkipApproval = async () => {
    setWaitingForApproval(false)
    try {
      setError('')
      setAnalyzing(true)
      await analyzeRun(Number(runId))
      
      // Poll for completion
      const pollInterval = setInterval(async () => {
        const data = await getRun(Number(runId))
        if (data.status === 'complete') {
          clearInterval(pollInterval)
          navigate(`/results/${runId}`)
        } else if (data.status === 'error') {
          clearInterval(pollInterval)
          setError('Analysis failed')
          setAnalyzing(false)
        }
      }, 2000)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to start analysis')
      setAnalyzing(false)
    }
  }

  if (!run) {
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
        <Typography variant="h4" sx={{ mb: 1 }}>
          Diagnostic Run #{runId}
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          {run.company_name || 'Unnamed Company'} • {run.vertical_id}
        </Typography>

        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          <Step>
            <StepLabel>Upload Data</StepLabel>
          </Step>
          <Step>
            <StepLabel>Map Columns</StepLabel>
          </Step>
          <Step>
            <StepLabel>Analyze</StepLabel>
          </Step>
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>
            {error}
          </Alert>
        )}

        {mappingSuccess && (
          <Alert severity="success" sx={{ mb: 2 }} onClose={() => setMappingSuccess(false)}>
            Mappings confirmed successfully! You can now upload more files or start analysis.
          </Alert>
        )}

        {(activeStep === 0 || run.status === 'mapping') && (
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 2 }}>
              Upload Data Files
            </Typography>

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mb: 3 }}>
              <FormControl>
                <InputLabel>Pack Type</InputLabel>
                <Select
                  value={selectedPackType}
                  label="Pack Type"
                  onChange={(e) => setSelectedPackType(e.target.value)}
                >
                  <MenuItem value="PNL">P&L (Monthly)</MenuItem>
                  <MenuItem value="REVENUE">Revenue (Transactions)</MenuItem>
                  <MenuItem value="LABOR">Labor (Payroll)</MenuItem>
                </Select>
              </FormControl>

              {/* Drag and Drop Zone */}
              <Box
                onDrop={(e) => {
                  e.preventDefault()
                  const files = Array.from(e.dataTransfer.files).filter(f => f.name.endsWith('.csv'))
                  if (files.length > 0) {
                    setSelectedFile(files[0])
                    setDragActive(false)
                  }
                }}
                onDragOver={(e) => {
                  e.preventDefault()
                  setDragActive(true)
                }}
                onDragLeave={() => setDragActive(false)}
                sx={{
                  border: '2px dashed',
                  borderColor: dragActive ? 'primary.main' : 'grey.300',
                  borderRadius: 2,
                  p: 4,
                  textAlign: 'center',
                  bgcolor: dragActive ? 'action.hover' : 'background.paper',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                  '&:hover': {
                    borderColor: 'primary.main',
                    bgcolor: 'action.hover'
                  }
                }}
              >
                <CloudUpload sx={{ fontSize: 48, color: 'primary.main', mb: 2 }} />
                <Typography variant="h6" gutterBottom>
                  Drag & Drop CSV File Here
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  or click to browse
                </Typography>
                <input
                  type="file"
                  hidden
                  accept=".csv"
                  onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
                  id="file-upload"
                />
                <label htmlFor="file-upload">
                  <Button
                    variant="outlined"
                    component="span"
                    startIcon={<CloudUpload />}
                  >
                    Choose CSV File
                  </Button>
                </label>
              </Box>

              {selectedFile && (
                <Alert severity="info" sx={{ display: 'flex', alignItems: 'center' }}>
                  <Typography variant="body2">
                    Selected: <strong>{selectedFile.name}</strong> ({(selectedFile.size / 1024).toFixed(1)} KB)
                  </Typography>
                </Alert>
              )}

              <Button
                variant="contained"
                onClick={handleUpload}
                disabled={!selectedFile || uploading}
                size="large"
              >
                {uploading ? 'Uploading...' : 'Upload File'}
              </Button>
            </Box>

            {uploads.length > 0 && (
              <>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6">
                    Uploaded Files
                  </Typography>
                  <Chip 
                    label={`${mappedUploadIds.size} of ${uploads.length} mapped`}
                    color={mappedUploadIds.size === uploads.length ? 'success' : 'default'}
                    size="small"
                  />
                </Box>

                <TableContainer>
                  <Table>
                    <TableHead>
                      <TableRow>
                        <TableCell>Filename</TableCell>
                        <TableCell>Pack Type</TableCell>
                        <TableCell>Rows</TableCell>
                        <TableCell>Columns</TableCell>
                        <TableCell>Actions</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody>
                      {uploads.map((upload) => {
                        const isMapped = mappedUploadIds.has(upload.upload_id)
                        return (
                          <TableRow 
                            key={upload.upload_id}
                            sx={{
                              bgcolor: isMapped ? 'success.light' : 'transparent',
                              '&:hover': { bgcolor: 'action.hover' }
                            }}
                          >
                            <TableCell>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                {upload.filename}
                                {isMapped && (
                                  <Chip 
                                    label="Mapped" 
                                    size="small" 
                                    color="success" 
                                    icon={<CheckCircle />}
                                  />
                                )}
                              </Box>
                            </TableCell>
                            <TableCell>
                              <Chip label={upload.pack_type} size="small" />
                            </TableCell>
                            <TableCell>{upload.row_count}</TableCell>
                            <TableCell>
                              {Object.keys(upload.column_profile?.columns || {}).length}
                            </TableCell>
                            <TableCell>
                              <Button
                                size="small"
                                variant={isMapped ? "outlined" : "contained"}
                                onClick={() => handleSuggestMappings(upload)}
                                disabled={loadingMappings}
                                startIcon={isMapped ? <CheckCircle /> : undefined}
                              >
                                {isMapped ? 'Remap' : 'Map Columns'}
                              </Button>
                            </TableCell>
                          </TableRow>
                        )
                      })}
                    </TableBody>
                  </Table>
                </TableContainer>
              </>
            )}
          </Paper>
        )}

        {activeStep === 1 && suggestedMappings.length > 0 && (
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Review & Confirm Column Mappings
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
              File: <strong>{currentUpload?.filename}</strong> • {currentUpload?.row_count} rows
            </Typography>

            <Alert severity="info" sx={{ mb: 2 }}>
              Review the suggested mappings below. The system has automatically matched your columns to canonical fields.
              {suggestedMappings.filter(m => m.confidence < 0.8).length > 0 && (
                <Typography variant="body2" sx={{ mt: 1 }}>
                  ⚠️ Some mappings have lower confidence - please verify these carefully.
                </Typography>
              )}
            </Alert>

            <TableContainer>
              <Table>
                <TableHead>
                  <TableRow>
                    <TableCell><strong>Canonical Field</strong></TableCell>
                    <TableCell><strong>Source Columns</strong></TableCell>
                    <TableCell><strong>Transform</strong></TableCell>
                    <TableCell><strong>Confidence</strong></TableCell>
                    <TableCell><strong>Reasoning</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {suggestedMappings.map((mapping, idx) => (
                    <TableRow 
                      key={idx}
                      sx={{
                        bgcolor: mapping.confidence < 0.5 ? 'error.light' : 
                                mapping.confidence < 0.8 ? 'warning.light' : 'success.light',
                        '&:hover': { bgcolor: 'action.hover' }
                      }}
                    >
                      <TableCell>
                        <Typography variant="body2" fontWeight="medium">
                          {mapping.canonical_field}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip 
                          label={mapping.source_columns.join(', ') || 'None'} 
                          size="small" 
                          variant="outlined"
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption">
                          {mapping.transform || 'none'}
                        </Typography>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={`${(mapping.confidence * 100).toFixed(0)}%`}
                          size="small"
                          color={
                            mapping.confidence >= 0.8 ? 'success' : 
                            mapping.confidence >= 0.5 ? 'warning' : 'error'
                          }
                        />
                      </TableCell>
                      <TableCell>
                        <Typography variant="caption" color="text.secondary">
                          {mapping.reasoning || 'No reasoning provided'}
                        </Typography>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>

            <Box sx={{ display: 'flex', gap: 2, mt: 3, justifyContent: 'flex-end' }}>
              <Button 
                variant="outlined" 
                onClick={() => {
                  setSuggestedMappings([])
                  setCurrentUpload(null)
                }}
              >
                Cancel
              </Button>
              <Button 
                variant="contained" 
                onClick={handleConfirmMappings} 
                startIcon={<CheckCircle />}
                size="large"
              >
                Confirm {suggestedMappings.length} Mapping{suggestedMappings.length !== 1 ? 's' : ''}
              </Button>
            </Box>
          </Paper>
        )}

        {run.status === 'mapping' && suggestedMappings.length === 0 && (
          <Paper sx={{ p: 3 }}>
            {confirmedMappingsCount === 0 ? (
              <>
                <Alert severity="error" sx={{ mb: 2 }}>
                  No confirmed mappings
                </Alert>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  Please upload files and confirm column mappings before starting analysis.
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Click "Map Columns" on each uploaded file to review and confirm mappings.
                </Typography>
              </>
            ) : (
              <>
                <Typography variant="h6" sx={{ mb: 2 }}>
                  Ready to Analyze
                </Typography>
                <Typography variant="body1" sx={{ mb: 2 }}>
                  All files have been uploaded and mapped ({confirmedMappingsCount} mapping{confirmedMappingsCount !== 1 ? 's' : ''} confirmed). Click below to start the analysis.
                </Typography>
                <Button
                  variant="contained"
                  size="large"
                  onClick={handleAnalyze}
                  disabled={analyzing}
                  startIcon={<PlayArrow />}
                >
                  {analyzing ? 'Analyzing...' : 'Start Analysis'}
                </Button>
              </>
            )}
          </Paper>
        )}

        {waitingForApproval && (
          <Paper sx={{ p: 4, textAlign: 'center', bgcolor: '#fff3e0', border: '2px solid #ff9800' }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 3 }}>
              <Typography variant="h5" color="primary" fontWeight="bold">
                ⏳ Waiting for MBB Approval
              </Typography>
              <Typography variant="body1" color="text.secondary">
                This analysis requires approval from McKinsey, Bain & Company, or BCG partners.
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Please wait for senior management review before proceeding.
              </Typography>
              <Box sx={{ mt: 2, p: 2, bgcolor: '#ffecb3', borderRadius: 1, width: '100%' }}>
                <Typography variant="caption" color="text.secondary" fontStyle="italic">
                  Demo Mode: For demonstration purposes, you can skip the approval process.
                </Typography>
              </Box>
              <Button
                variant="contained"
                color="warning"
                size="large"
                onClick={handleSkipApproval}
                sx={{ mt: 2 }}
              >
                Skip Approval (Demo)
              </Button>
            </Box>
          </Paper>
        )}

        {analyzing && !waitingForApproval && (
          <Paper sx={{ p: 3 }}>
            <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
              <CircularProgress size={60} />
              <Typography variant="h6">Analyzing Data...</Typography>
              <Typography variant="body2" color="text.secondary">
                This may take a minute. Computing analytics and selecting initiatives.
              </Typography>
            </Box>
          </Paper>
        )}
      </Box>
    </Container>
  )
}

export default RunPage
