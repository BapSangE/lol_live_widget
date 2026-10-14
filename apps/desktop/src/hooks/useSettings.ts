import { useEffect, useRef, useState } from 'react';
import { defaults } from '../lib/policies';
import { readSettings, writeSettings } from '../lib/native';
import type { UserSettings } from '../types/contracts';
export function useSettings() {
  const [settings, setSettings] = useState<UserSettings>({ ...defaults });
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const chain = useRef(Promise.resolve());
  useEffect(() => {
    let active = true;
    void readSettings().then((s) => {
      if (active) {
        setSettings(s);
        setLoaded(true);
      }
    });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!loaded) return;
    const timer = setTimeout(() => {
      chain.current = chain.current
        .catch(() => {})
        .then(() => writeSettings(settings))
        .catch(() => setError('설정을 저장할 수 없음'));
    }, 200);
    return () => clearTimeout(timer);
  }, [settings, loaded]);
  return { settings, setSettings, loaded, error, setError };
}
