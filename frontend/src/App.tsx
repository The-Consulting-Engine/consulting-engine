import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { ThemeProvider, createTheme } from '@mui/material/styles'
import CssBaseline from '@mui/material/CssBaseline'
import HomePage from './pages/HomePage'
import QuestionsPage from './pages/QuestionsPage'
import RunPage from './pages/RunPage'
import ResultsPage from './pages/ResultsPage'

const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
  },
})

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/questions/:runId" element={<QuestionsPage />} />
          <Route path="/run/:runId" element={<RunPage />} />
          <Route path="/results/:runId" element={<ResultsPage />} />
        </Routes>
      </Router>
    </ThemeProvider>
  )
}

export default App
