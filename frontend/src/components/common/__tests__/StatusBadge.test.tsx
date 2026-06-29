import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../StatusBadge';
import { MantineProvider } from '@mantine/core';

function renderWithMantine(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

describe('StatusBadge', () => {
  it('renders running status', () => {
    renderWithMantine(<StatusBadge status="running" />);
    expect(screen.getByText('running')).toBeInTheDocument();
  });

  it('renders success status', () => {
    renderWithMantine(<StatusBadge status="success" />);
    expect(screen.getByText('success')).toBeInTheDocument();
  });

  it('renders failed status', () => {
    renderWithMantine(<StatusBadge status="failed" />);
    expect(screen.getByText('failed')).toBeInTheDocument();
  });

  it('renders timeout status', () => {
    renderWithMantine(<StatusBadge status="timeout" />);
    expect(screen.getByText('timeout')).toBeInTheDocument();
  });

  it('renders unknown status with gray', () => {
    renderWithMantine(<StatusBadge status="unknown" />);
    expect(screen.getByText('unknown')).toBeInTheDocument();
  });
});
