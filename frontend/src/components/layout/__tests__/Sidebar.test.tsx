import { render, screen } from '@testing-library/react';
import { Sidebar } from '../Sidebar';
import { MantineProvider } from '@mantine/core';
import { BrowserRouter } from 'react-router-dom';

function renderSidebar() {
  return render(
    <MantineProvider>
      <BrowserRouter>
        <Sidebar />
      </BrowserRouter>
    </MantineProvider>,
  );
}

describe('Sidebar', () => {
  it('renders FCIP title', () => {
    renderSidebar();
    expect(screen.getByText('FCIP')).toBeInTheDocument();
  });

  it('renders subtitle', () => {
    renderSidebar();
    expect(screen.getByText('FPGA Compile Intelligence')).toBeInTheDocument();
  });

  it('renders all navigation links', () => {
    renderSidebar();
    expect(screen.getByText('Projects')).toBeInTheDocument();
    expect(screen.getByText('Experiments')).toBeInTheDocument();
    expect(screen.getByText('Compare')).toBeInTheDocument();
    expect(screen.getByText('Predictions')).toBeInTheDocument();
    expect(screen.getByText('Recommendations')).toBeInTheDocument();
    expect(screen.getByText('Settings')).toBeInTheDocument();
  });
});
