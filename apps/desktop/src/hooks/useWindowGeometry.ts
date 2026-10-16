import { useEffect, useRef } from 'react';
import {
  getCurrentWindow,
  availableMonitors,
  currentMonitor,
  primaryMonitor,
  type Monitor,
} from '@tauri-apps/api/window';
import { PhysicalPosition, LogicalSize } from '@tauri-apps/api/dpi';
import { native } from '../lib/native';
import {
  COMPACT_HEIGHT,
  COMPACT_WIDTH,
  EXPANDED_HEIGHT,
  geometry,
} from '../lib/policies';
import type { UserSettings } from '../types/contracts';
import type { Dispatch, SetStateAction } from 'react';
function monitorKey(m: Monitor) {
  return m.name || `${m.position.x},${m.position.y}:${m.size.width}x${m.size.height}`;
}
export function useWindowGeometry(
  mode: 'compact' | 'expanded' | 'settings',
  settings: UserSettings,
  loaded: boolean,
  setSettings: Dispatch<SetStateAction<UserSettings>>,
  onError: (message: string) => void,
) {
  const anchor = useRef({ x: 0, y: 0 });
  const compactHeight = Math.ceil((COMPACT_HEIGHT * settings.fontScalePercent) / 100);
  const lastCompactHeight = useRef(compactHeight);
  const initialized = useRef(false),
    busy = useRef(false),
    lastMode = useRef(mode);
  const preferences = useRef(settings);
  preferences.current = settings;
  const chain = useRef(Promise.resolve());
  useEffect(() => {
    if (!native || !loaded) return;
    const win = getCurrentWindow();
    let disposed = false;
    const apply = async () => {
      busy.current = true;
      try {
        let monitor = (await currentMonitor()) || (await primaryMonitor());
        if (!initialized.current) {
          const monitors = await availableMonitors(),
            saved = preferences.current.widgetPosition;
          monitor = saved
            ? monitors.find((m) => monitorKey(m) === saved.monitorKey) ||
              (await primaryMonitor())
            : await primaryMonitor();
          if (!monitor) return;
          const area = monitor.workArea.size.toLogical(monitor.scaleFactor);
          anchor.current =
            saved && monitorKey(monitor) === saved.monitorKey
              ? { x: saved.x, y: saved.y }
              : {
                  x: (area.width - COMPACT_WIDTH) / 2,
                  y: area.height - compactHeight - 24,
                };
          initialized.current = true;
        }
        if (!monitor) return;
        const scale = monitor.scaleFactor,
          area = monitor.workArea.size.toLogical(scale);
        if (
          lastCompactHeight.current !== compactHeight &&
          anchor.current.y + lastCompactHeight.current >= area.height * 0.6
        ) {
          anchor.current.y += lastCompactHeight.current - compactHeight;
        }
        const bounds = { x: 0, y: 0, width: area.width, height: area.height };
        const compact = geometry(
          anchor.current,
          false,
          bounds,
          EXPANDED_HEIGHT,
          compactHeight,
        );
        anchor.current = { x: compact.x, y: compact.y };
        const rect = geometry(
          anchor.current,
          mode !== 'compact',
          bounds,
          Math.ceil(
            ((mode === 'settings' ? 300 : EXPANDED_HEIGHT) * settings.fontScalePercent) /
              100,
          ),
          compactHeight,
        );
        await win.setSize(new LogicalSize(rect.width, rect.height));
        await win.setPosition(
          new PhysicalPosition(
            Math.round(monitor.workArea.position.x + rect.x * scale),
            Math.round(monitor.workArea.position.y + rect.y * scale),
          ),
        );
        lastMode.current = mode;
        lastCompactHeight.current = compactHeight;
        if (!disposed) await win.show();
      } catch (error) {
        console.error(error);
        onError('창 위치를 적용할 수 없음');
      } finally {
        busy.current = false;
      }
    };
    chain.current = chain.current.catch(() => {}).then(apply);
    return () => {
      disposed = true;
    };
  }, [loaded, mode, onError, compactHeight, settings.fontScalePercent]);
  useEffect(() => {
    if (!native || !loaded) return;
    let disposed = false;
    const removers: Array<() => void> = [];
    const win = getCurrentWindow();
    const moved = async () => {
      if (busy.current) return;
      try {
        const monitor = await currentMonitor();
        if (!monitor) return;
        const pos = await win.outerPosition(),
          size = await win.outerSize();
        const local = {
          x: (pos.x - monitor.workArea.position.x) / monitor.scaleFactor,
          y: (pos.y - monitor.workArea.position.y) / monitor.scaleFactor,
        };
        const area = monitor.workArea.size.toLogical(monitor.scaleFactor);
        const upward = anchor.current.y + lastCompactHeight.current >= area.height * 0.6;
        anchor.current = {
          x: local.x,
          y:
            lastMode.current !== 'compact' && upward
              ? local.y + size.height / monitor.scaleFactor - lastCompactHeight.current
              : local.y,
        };
        if (!disposed)
          setSettings((s) => ({
            ...s,
            widgetPosition: {
              monitorKey: monitorKey(monitor),
              ...anchor.current,
              anchor: 'compact',
            },
          }));
      } catch (error) {
        console.warn(error);
      }
    };
    void win
      .onMoved(() => {
        void moved();
      })
      .then((off) => {
        if (disposed) off();
        else removers.push(off);
      });
    void win
      .onScaleChanged(() => {
        void moved();
      })
      .then((off) => {
        if (disposed) off();
        else removers.push(off);
      });
    return () => {
      disposed = true;
      removers.forEach((off) => off());
    };
  }, [loaded, setSettings]);
  useEffect(() => {
    if (native && loaded)
      void getCurrentWindow()
        .setAlwaysOnTop(settings.alwaysOnTop)
        .catch(() => onError('항상 위 설정을 적용할 수 없음'));
  }, [loaded, settings.alwaysOnTop, onError]);
}
