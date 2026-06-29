import { render, screen } from '@testing-library/react';
import { DeltaIndicator } from '../DeltaIndicator';
import { MantineProvider } from '@mantine/core';

function renderWithMantine(ui: React.ReactElement) {
  return render(<MantineProvider>{ui}</MantineProvider>);
}

describe('DeltaIndicator', () => {
  it('renders N/A when delta is null', () => {
    renderWithMantine(<DeltaIndicator delta={null} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('renders N/A when delta is undefined', () => {
    renderWithMantine(<DeltaIndicator delta={undefined} />);
    expect(screen.getByText('N/A')).toBeInTheDocument();
  });

  it('renders positive delta with + sign', () => {
    renderWithMantine(<DeltaIndicator delta={0.5} />);
    expect(screen.getByText('+0.500')).toBeInTheDocument();
  });

  it('renders negative delta without + sign', () => {
    renderWithMantine(<DeltaIndicator delta={-1.234} />);
    expect(screen.getByText('-1.234')).toBeInTheDocument();
  });

  it('renders zero delta', () => {
    renderWithMantine(<DeltaIndicator delta={0} />);
    expect(screen.getByText('0.000')).toBeInTheDocument();
  });

  it('inverts color logic when invert is true', () => {
    renderWithMantine(<DeltaIndicator delta={0.5} invert />);
    expect(screen.getByText('+0.500')).toBeInTheDocument();
  });

  it('renders high-precision delta values', () => {
    renderWithMantine(<DeltaIndicator delta={-0.001} />);
    expect(screen.getByText('-0.001')).toBeInTheDocument();
  });
});
