import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 1000 * 60 * 5,
      retry: 1,
    },
  },
})

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <main className="container mx-auto px-4 py-8">
            <h1 className="text-3xl font-bold text-primary-500">
              Myome Dashboard
            </h1>
            <p className="mt-2 text-gray-600">
              Your Living Health Record
            </p>
            <Routes>
              <Route path="/" element={<div className="mt-8 p-6 bg-white rounded-lg shadow">Dashboard coming in Phase 6</div>} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
