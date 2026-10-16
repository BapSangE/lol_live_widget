#[cfg(all(target_os = "macos", feature = "macos-portable"))]
use tauri::Manager;

/// Accept only the local collector origin passed by the portable launcher.
pub fn validate_origin(origin: &str) -> Result<(), String> {
    let port = origin
        .strip_prefix("http://127.0.0.1:")
        .ok_or("Invalid local server origin")?;
    if port.is_empty()
        || !port.bytes().all(|c| c.is_ascii_digit())
        || port.parse::<u16>().unwrap_or(0) == 0
    {
        return Err("Invalid local server port".into());
    }
    Ok(())
}

#[tauri::command]
pub fn local_server_url(app: tauri::AppHandle) -> Result<Option<String>, String> {
    match std::env::var("LOL_WIDGET_LOCAL_SERVER_URL") {
        Ok(origin) => {
            validate_origin(&origin)?;
            Ok(Some(origin))
        }
        Err(std::env::VarError::NotPresent) => {
            #[cfg(all(target_os = "macos", feature = "macos-portable"))]
            {
                return Ok(Some(app.state::<crate::macos_server::Collector>().origin()?));
            }
            #[cfg(not(all(target_os = "macos", feature = "macos-portable")))]
            {
                let _ = app;
                Ok(None)
            }
        }
        Err(_) => Err("Invalid local server configuration".into()),
    }
}

/// Register the outer EXE rather than the UI extracted into a temporary folder.
#[tauri::command]
pub fn set_portable_autostart(enabled: bool) -> Result<bool, String> {
    let Some(path) = std::env::var_os("LOL_WIDGET_LAUNCHER_PATH") else {
        return Ok(false);
    };
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;

        let path = std::path::PathBuf::from(path);
        if !path.is_absolute() || !path.is_file() {
            return Err("Portable launcher is missing".into());
        }
        let key = r"HKCU\Software\Microsoft\Windows\CurrentVersion\Run";
        let mut command = std::process::Command::new("reg.exe");
        command.creation_flags(0x08000000);
        if enabled {
            command
                .args(["add", key, "/v", "LoLLiveWidget", "/t", "REG_SZ", "/d"])
                .arg(format!("\"{}\"", path.display()))
                .arg("/f");
        } else {
            command.args(["delete", key, "/v", "LoLLiveWidget", "/f"]);
        }
        let result = command.output().map_err(|e| e.to_string())?;
        if !result.status.success() && enabled {
            return Err("Cannot register portable autostart".into());
        }
        Ok(true)
    }
    #[cfg(not(windows))]
    {
        let _ = (enabled, path);
        Err("Portable autostart requires Windows".into())
    }
}

#[cfg(test)]
mod tests {
    use super::validate_origin;

    #[test]
    fn only_accepts_dynamic_loopback_origins() {
        assert!(validate_origin("http://127.0.0.1:49152").is_ok());
        for origin in [
            "https://example.com:80",
            "http://0.0.0.0:80",
            "http://127.0.0.1:0",
            "http://127.0.0.1:65536",
            "http://127.0.0.1:80/path",
            "http://127.0.0.1:80@evil.example",
        ] {
            assert!(validate_origin(origin).is_err(), "{origin}");
        }
    }
}
