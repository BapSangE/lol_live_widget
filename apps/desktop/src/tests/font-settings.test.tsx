import { afterEach, expect, it } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { SettingsPanel } from '../components/SettingsPanel';
import { useSettings } from '../hooks/useSettings';

function Settings() {
  const { settings, setSettings, loaded } = useSettings();
  if (!loaded) return null;
  return (
    <SettingsPanel
      settings={settings}
      matches={[]}
      onChange={(patch) => setSettings((s) => ({ ...s, ...patch }))}
      onBack={() => {}}
    />
  );
}

afterEach(() => {
  cleanup();
  localStorage.clear();
});

it('applies and persists font size choices and restores them after reopening', async () => {
  const view = render(<Settings />);
  const select = await screen.findByRole('combobox', { name: '글자 크기' });
  expect(select).toHaveValue('100');
  fireEvent.change(select, { target: { value: '140' } });
  expect(select).toHaveValue('140');
  await waitFor(() =>
    expect(
      JSON.parse(localStorage.getItem('lol-widget-settings') || '{}').fontScalePercent,
    ).toBe(140),
  );
  view.unmount();
  render(<Settings />);
  expect(await screen.findByRole('combobox', { name: '글자 크기' })).toHaveValue('140');
});
