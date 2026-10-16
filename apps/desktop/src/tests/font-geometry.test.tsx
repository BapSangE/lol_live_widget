import { afterEach, expect, it, vi } from 'vitest';
import { useState } from 'react';
import { act, cleanup, renderHook, waitFor } from '@testing-library/react';
import { useWindowGeometry } from '../hooks/useWindowGeometry';
import { defaults } from '../lib/policies';
import type { UserSettings } from '../types/contracts';

const native = vi.hoisted(() => ({
  workHeight: 1040,
  scaleChanged: () => {},
  position: { x: 0, y: 0 },
  size: { width: 350, height: 62 },
}));
vi.mock('../lib/native', () => ({ native: true }));
vi.mock('@tauri-apps/api/window', () => {
  const monitor = {
    name: 'screen',
    scaleFactor: 1,
    workArea: {
      position: { x: 0, y: 0 },
      size: { toLogical: () => ({ width: 1920, height: native.workHeight }) },
    },
  };
  const win = {
    setSize: async (s: { width: number; height: number }) => {
      native.size = s;
    },
    setPosition: async (p: { x: number; y: number }) => {
      native.position = p;
    },
    show: async () => {},
    onMoved: async () => () => {},
    onScaleChanged: async (callback: () => void) => {
      native.scaleChanged = callback;
      return () => {};
    },
    setAlwaysOnTop: async () => {},
  };
  return {
    getCurrentWindow: () => win,
    currentMonitor: async () => monitor,
    primaryMonitor: async () => monitor,
    availableMonitors: async () => [monitor],
  };
});
afterEach(() => {
  cleanup();
  native.workHeight = 1040;
  native.position = { x: 0, y: 0 };
  native.size = { width: 350, height: 62 };
});

it('restores an enlarged saved position without shifting it again on each launch', async () => {
  const setSettings = vi.fn();
  const report = vi.fn();
  const saved: UserSettings = {
    ...defaults,
    fontScalePercent: 140,
    widgetPosition: { monitorKey: 'screen', x: 300, y: 900, anchor: 'compact' },
  };
  const view = renderHook(
    ({ settings, loaded }) =>
      useWindowGeometry('compact', settings, loaded, setSettings, report),
    { initialProps: { settings: defaults, loaded: false } },
  );
  view.rerender({ settings: saved, loaded: true });
  await waitFor(() => expect(native.size.height).toBe(87));
  await waitFor(() => expect(native.position.y).toBe(900));
  view.rerender({ settings: { ...saved, fontScalePercent: 120 }, loaded: true });
  await waitFor(() => expect(native.size.height).toBe(75));
  await waitFor(() => expect(native.position.y).toBe(912));
  expect(report).not.toHaveBeenCalled();
});

it('persists the resized anchor so reopening uses the same position', async () => {
  const report = vi.fn();
  const saved: UserSettings = {
    ...defaults,
    widgetPosition: { monitorKey: 'screen', x: 300, y: 900, anchor: 'compact' },
  };
  const view = renderHook(() => {
    const [settings, setSettings] = useState(saved);
    useWindowGeometry('compact', settings, true, setSettings, report);
    return { settings, setSettings };
  });
  await waitFor(() => expect(native.position.y).toBe(900));
  act(() => view.result.current.setSettings((s) => ({ ...s, fontScalePercent: 140 })));
  await waitFor(() => expect(native.size.height).toBe(87));
  await waitFor(() => expect(native.position.y).toBe(875));
  await waitFor(() => expect(view.result.current.settings.widgetPosition?.y).toBe(875));
  const persisted = view.result.current.settings;
  view.unmount();
  renderHook(() => useWindowGeometry('compact', persisted, true, () => {}, report));
  await waitFor(() => expect(native.position.y).toBe(875));
});

it('reclamps the enlarged window when monitor work area changes with DPI', async () => {
  const report = vi.fn();
  const settings: UserSettings = { ...defaults, fontScalePercent: 140 };
  renderHook(() => useWindowGeometry('expanded', settings, true, () => {}, report));
  await waitFor(() => expect(native.size.height).toBe(560));
  act(() => {
    native.workHeight = 300;
    native.scaleChanged();
  });
  await waitFor(() => expect(native.size.height).toBe(300));
  expect(native.position.y).toBe(0);
});
