import { afterEach, it, expect, vi } from 'vitest';
import { act, cleanup, renderHook } from '@testing-library/react';
import { defaults } from '../lib/policies';
vi.mock('../lib/native', () => ({ native: true }));
vi.mock('@tauri-apps/api/core', () => ({
  invoke: async (command: string) => {
    if (command === 'opacity_backend') return 'native';
    throw new Error('Win32 alpha failure');
  },
}));
import { useOpacity } from '../hooks/useOpacity';
afterEach(cleanup);
it('preserves CSS opacity if the first native alpha application fails', async () => {
  const report = vi.fn();
  const { result } = renderHook(() => useOpacity(defaults, false, report));
  await act(async () => {
    for (let i = 0; i < 20; i++) await Promise.resolve();
  });
  expect(result.current.opacity).toBe(0.65);
  expect(report).toHaveBeenCalledWith('불투명도 조절을 적용할 수 없음');
});
