import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Container,
  Box,
  Typography,
  Button,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Alert,
} from '@mui/material'
import { Add as AddIcon, PlayArrow as PlayIcon, Delete as DeleteIcon } from '@mui/icons-material'
import { createRun, listRuns, listVerticals, deleteRun } from '../api/client'

interface Run {
  id: number
  vertical_id: string
  company_name?: string
  status: string
  created_at: string
}

interface Vertical {
  vertical_id: string
  vertical_name: string
}

function HomePage() {
  const navigate = useNavigate()
  const [runs, setRuns] = useState<Run[]>([])
  const [verticals, setVerticals] = useState<Vertical[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [companyName, setCompanyName] = useState('')
  const [selectedVertical, setSelectedVertical] = useState('restaurant_v1')
  const [notes, setNotes] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    loadRuns()
    loadVerticals()
  }, [])

  const loadRuns = async () => {
    try {
      const data = await listRuns()
      setRuns(data)
    } catch (err) {
      console.error('Failed to load runs:', err)
    }
  }

  const loadVerticals = async () => {
    try {
      const data = await listVerticals()
      setVerticals(data.verticals)
    } catch (err) {
      console.error('Failed to load verticals:', err)
    }
  }

  const handleCreateRun = async () => {
    try {
      setError('')
      const run = await createRun({
        vertical_id: selectedVertical,
        company_name: companyName || undefined,
        notes: notes || undefined,
      })
      // Navigate to questions page first
      navigate(`/questions/${run.id}`)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to create run')
    }
  }

  const handleDeleteRun = async (runId: number) => {
    if (!window.confirm('Are you sure you want to delete this run? This action cannot be undone.')) {
      return
    }
    
    try {
      await deleteRun(runId)
      loadRuns()
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to delete run')
    }
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h3" component="h1">
            Consulting Engine
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => setShowCreate(!showCreate)}
          >
            New Diagnostic Run
          </Button>
        </Box>

        {showCreate && (
          <Paper sx={{ p: 3, mb: 4 }}>
            <Typography variant="h5" sx={{ mb: 2 }}>
              Create New Run
            </Typography>
            
            {error && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {error}
              </Alert>
            )}

            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              <TextField
                label="Company Name"
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                fullWidth
              />

              <FormControl fullWidth>
                <InputLabel>Vertical</InputLabel>
                <Select
                  value={selectedVertical}
                  label="Vertical"
                  onChange={(e) => setSelectedVertical(e.target.value)}
                >
                  {verticals.map((v) => (
                    <MenuItem key={v.vertical_id} value={v.vertical_id}>
                      {v.vertical_name}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <TextField
                label="Notes (optional)"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                multiline
                rows={3}
                fullWidth
              />

              <Box sx={{ display: 'flex', gap: 2 }}>
                <Button variant="contained" onClick={handleCreateRun} startIcon={<PlayIcon />}>
                  Create & Start
                </Button>
                <Button variant="outlined" onClick={() => setShowCreate(false)}>
                  Cancel
                </Button>
              </Box>
            </Box>
          </Paper>
        )}

        <Typography variant="h5" sx={{ mb: 2 }}>
          Recent Runs
        </Typography>

        <TableContainer component={Paper}>
          <Table>
            <TableHead>
              <TableRow>
                <TableCell>ID</TableCell>
                <TableCell>Company</TableCell>
                <TableCell>Vertical</TableCell>
                <TableCell>Status</TableCell>
                <TableCell>Created</TableCell>
                <TableCell>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {runs.map((run) => (
                <TableRow key={run.id}>
                  <TableCell>{run.id}</TableCell>
                  <TableCell>{run.company_name || '-'}</TableCell>
                  <TableCell>{run.vertical_id}</TableCell>
                  <TableCell>{run.status}</TableCell>
                  <TableCell>{new Date(run.created_at).toLocaleDateString()}</TableCell>
                  <TableCell>
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      {run.status === 'complete' ? (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => navigate(`/results/${run.id}`)}
                        >
                          View Results
                        </Button>
                      ) : (
                        <Button
                          size="small"
                          variant="outlined"
                          onClick={() => navigate(`/run/${run.id}`)}
                        >
                          Continue
                        </Button>
                      )}
                      <Button
                        size="small"
                        variant="outlined"
                        color="error"
                        startIcon={<DeleteIcon />}
                        onClick={() => handleDeleteRun(run.id)}
                      >
                        Delete
                      </Button>
                    </Box>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Box>
    </Container>
  )
}

export default HomePage
