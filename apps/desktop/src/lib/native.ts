import { isTauri, invoke } from '@tauri-apps/api/core';
import { defaults, validateSettings } from './policies';
import type { UserSettings } from '../types/contracts';
export const native = isTauri();
export async function readSettings(): Promise<UserSettings> {
  try {
    return validateSettings(
      native
        ? await invoke('read_settings')
        : JSON.parse(localStorage.getItem('lol-widget-settings') || 'null'),
    );
  } catch (error) {
    console.warn('Settings restored to defaults', error);
    return { ...defaults };
  }
}
export async function writeSettings(settings: UserSettings) {
  if (native) await invoke('save_settings', { settings });
  else localStorage.setItem('lol-widget-settings', JSON.stringify(settings));
}
export async function setAutostart(enabled: boolean) {
  if (!native) return;
  if (await invoke<boolean>('set_portable_autostart', { enabled })) return;
  const plugin = await import('@tauri-apps/plugin-autostart');
  if (enabled) await plugin.enable();
  else await plugin.disable();
}
