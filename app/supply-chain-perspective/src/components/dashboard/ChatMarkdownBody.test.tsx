import { render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { ChatMarkdownBody } from './ChatMarkdownBody';

vi.mock('react-markdown', () => ({
  default: ({ children }: { children: string }) => <div data-testid="md">{children}</div>,
}));

describe('ChatMarkdownBody', () => {
  it('applies compact modifier class', () => {
    const { container } = render(<ChatMarkdownBody content="# Hi" compact />);
    expect(
      container.querySelector('.supply-chain-perspective__dashboard-chat-md--compact'),
    ).toBeTruthy();
    expect(screen.getByTestId('md')).toHaveTextContent('# Hi');
  });

  it('renders plain text while streaming without markdown', () => {
    const { container } = render(<ChatMarkdownBody content="partial" streaming />);
    expect(
      container.querySelector('.supply-chain-perspective__dashboard-chat-md-plain'),
    ).toBeTruthy();
    expect(
      container.querySelector('.supply-chain-perspective__dashboard-chat-stream-cursor'),
    ).toBeTruthy();
    expect(screen.queryByTestId('md')).toBeNull();
    expect(screen.getByText(/partial/)).toBeInTheDocument();
  });
});
