import { render, screen, waitFor } from '@testing-library/vue'
import userEvent from '@testing-library/user-event'
import App from '@/App.vue'

describe('App', () => {
  let rankingRequestBody: Record<string, unknown> | null = null

  beforeEach(() => {
    rankingRequestBody = null
    if (typeof window.localStorage.removeItem === 'function') {
      window.localStorage.removeItem('rankify_anon_id')
    }

    vi.spyOn(globalThis, 'fetch').mockImplementation(
      async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input)

      if (url.endsWith('/categories')) {
        return {
          ok: true,
          status: 200,
          json: async () => [{ id: 1, slug: 'test-candy', name: 'Test Candy', item_count: 3 }],
        } as Response
      }

      if (url.endsWith('/categories/test-candy')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: 1,
            slug: 'test-candy',
            name: 'Test Candy',
            description: 'seeded',
            submission_count: 0,
            items: [
              { id: 10, name: 'A', display_order: 0 },
              { id: 11, name: 'B', display_order: 1 },
              { id: 12, name: 'C', display_order: 2 },
            ],
          }),
        } as Response
      }

      if (url.endsWith('/rankings')) {
        rankingRequestBody = init?.body ? (JSON.parse(String(init.body)) as Record<string, unknown>) : null
        return {
          ok: true,
          status: 201,
          json: async () => ({ submission_id: 99, anon_id: 'anon-1' }),
        } as Response
      }

      if (url.endsWith('/categories/test-candy/community-ranking')) {
        return {
          ok: true,
          status: 200,
          json: async () => ({
            category_id: 1,
            category_slug: 'test-candy',
            total_submissions: 1,
            items: [
              { item_id: 10, item_name: 'A', average_rank: 1, vote_count: 1 },
              { item_id: 11, item_name: 'B', average_rank: 2, vote_count: 1 },
              { item_id: 12, item_name: 'C', average_rank: 3, vote_count: 1 },
            ],
          }),
        } as Response
      }

      return {
        ok: false,
        status: 404,
        json: async () => ({}),
      } as Response
      },
    )
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('loads category, submits ranking, and shows community output', async () => {
    render(App)

    expect(screen.getByText(/Rank fast. Compare with everyone./i)).toBeInTheDocument()

    await waitFor(() => {
      expect(screen.getByText('Test Candy (3 items)')).toBeInTheDocument()
    })

    await userEvent.click(screen.getByRole('button', { name: 'Submit Ranking' }))

    await waitFor(() => {
      expect(screen.getByText(/1 total submissions/i)).toBeInTheDocument()
      expect(screen.getByText(/avg #1.00/i)).toBeInTheDocument()
    })

    expect(rankingRequestBody?.anon_id).toEqual(expect.any(String))
    expect(screen.getByRole('button', { name: 'Already Submitted' })).toBeDisabled()
    expect(screen.getByText('You already submitted this category.')).toBeInTheDocument()
  })
})
