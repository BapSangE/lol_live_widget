use std::{process::Child, sync::Mutex};

#[cfg(feature = "macos-portable")]
use std::{
    path::Path,
    process::{Command, Stdio},
    thread,
    time::{Duration, Instant},
};

#[derive(Default)]
struct RunningServer {
    origin: Option<String>,
    child: Option<Child>,
    port_file: Option<std::path::PathBuf>,
}

/// Owns the collector process embedded in the portable macOS app bundle.
#[derive(Default)]
pub struct Collector(Mutex<RunningServer>);

impl Collector {
    #[cfg(feature = "macos-portable")]
    pub fn start(&self, resource_dir: &Path) -> std::io::Result<()> {
        let executable = resource_dir.join("LoL-Live-Widget-Server");
        if !executable.is_file() {
            return Err(std::io::Error::new(
                std::io::ErrorKind::NotFound,
                format!("Bundled collector is missing: {}", executable.display()),
            ));
        }

        let port_file = std::env::temp_dir().join(format!(
            "lol-live-widget-collector-{}.port",
            std::process::id()
        ));
        let _ = std::fs::remove_file(&port_file);
        let mut child = Command::new(executable)
            .arg("--server-only")
            .arg("--port-file")
            .arg(&port_file)
            .env_remove("LOLESPORTS_API_KEY")
            .stdin(Stdio::null())
            .stdout(Stdio::null())
            .stderr(Stdio::null())
            .spawn()?;

        let deadline = Instant::now() + Duration::from_secs(60);
        loop {
            if let Ok(origin) = std::fs::read_to_string(&port_file) {
                let origin = origin.trim().to_owned();
                if crate::portable::validate_origin(&origin).is_ok() {
                    let mut running = self.0.lock().map_err(|_| {
                        std::io::Error::other("Embedded collector state unavailable")
                    })?;
                    running.origin = Some(origin);
                    running.child = Some(child);
                    running.port_file = Some(port_file);
                    return Ok(());
                }
                let _ = child.kill();
                let _ = child.wait();
                let _ = std::fs::remove_file(&port_file);
                return Err(std::io::Error::new(
                    std::io::ErrorKind::InvalidData,
                    "Embedded collector returned an invalid loopback address",
                ));
            }
            if let Some(status) = child.try_wait()? {
                let _ = std::fs::remove_file(&port_file);
                return Err(std::io::Error::other(format!(
                    "Embedded collector exited during startup: {status}"
                )));
            }
            if Instant::now() >= deadline {
                let _ = child.kill();
                let _ = child.wait();
                let _ = std::fs::remove_file(&port_file);
                return Err(std::io::Error::new(
                    std::io::ErrorKind::TimedOut,
                    "Embedded collector startup timed out",
                ));
            }
            thread::sleep(Duration::from_millis(50));
        }
    }

    #[cfg(feature = "macos-portable")]
    pub fn origin(&self) -> Result<String, String> {
        self.0
            .lock()
            .map_err(|_| "Embedded collector state unavailable".to_owned())?
            .origin
            .clone()
            .ok_or_else(|| "Embedded collector has not started".to_owned())
    }

    pub fn stop(&self) {
        let Ok(mut running) = self.0.lock() else {
            return;
        };
        if let Some(mut child) = running.child.take() {
            let _ = child.kill();
            let _ = child.wait();
        }
        if let Some(port_file) = running.port_file.take() {
            let _ = std::fs::remove_file(port_file);
        }
        running.origin = None;
    }
}
