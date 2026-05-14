import { render } from '@testing-library/react';
import IconModule from './PerspectiveIcon';

const PerspectiveIcon = IconModule.default;

describe('PerspectiveIcon', () => {
  it('renders an inline SVG for console navigation branding', () => {
    const { container } = render(<PerspectiveIcon />);
    const svg = container.querySelector('svg');
    expect(svg).toBeInTheDocument();
    expect(svg).toHaveAttribute('aria-hidden', 'true');
  });
});
