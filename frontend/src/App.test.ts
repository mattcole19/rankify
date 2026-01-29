import { render, screen, waitFor } from '@testing-library/vue'
import App from '@/App.vue'

describe('App', () => {
  beforeEach(() => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ status: 'healthy' }),
    } as Response)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders hero copy and fetches health', async () => {
    render(App)

    expect(
      screen.getByText(/Collect ranked opinions without the noise/i),
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent('API is online')
    })
  })
})
